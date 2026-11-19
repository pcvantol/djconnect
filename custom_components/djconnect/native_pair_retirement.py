"""Durable Core retirement evidence linked to the original PairJournal row."""

from dataclasses import dataclass, field
import hashlib
import json

from .native_widget_consent import read_widget_consent_in_transaction
from .persistence import PersistenceError
from .surface_push_contract import require
from .surface_push_wire import canonical

_MAX_ROWS = 4096
_MAX_BATCH = 32


@dataclass(frozen=True, repr=False)
class NativePairRetirement:
    event_id: str
    origin: str
    original: str = field(repr=False)

    def body(self):
        return json.loads(self.original)


class NativePairRetirementJournal:
    """The local PairJournal tombstone makes staged evidence deliverable atomically."""

    def __init__(self, persistence):
        self.persistence = persistence

    async def stage(self, pair, origin, original, consent, publisher_origin, current):
        event_id = original["operation_id"]
        body = canonical(original)
        local_binding = pair.registration.binding

        def write(tx):
            committed_consent = read_widget_consent_in_transaction(tx, pair)
            require(committed_consent == consent and consent.enabled,
                    "native_widget_consent_changed", 403)
            saved = tx.fetchone(
                "SELECT local_binding,origin,original,consent_revision,publisher_origin "
                "FROM djconnect_native_pair_retirements WHERE event_id=?",
                (event_id,),
            )
            if saved is not None:
                if tuple(saved) != (local_binding, origin, body, consent.revision, publisher_origin):
                    raise PersistenceError("Native retirement event collision")
                return
            if tx.fetchone("SELECT count(*) FROM djconnect_native_pair_retirements")[0] >= _MAX_ROWS:
                raise PersistenceError("Native retirement journal capacity reached")
            tx.execute(
                "INSERT INTO djconnect_native_pair_retirements"
                "(event_id,local_binding,origin,original,consent_revision,publisher_origin) "
                "VALUES(?,?,?,?,?,?)", (event_id, local_binding, origin, body, consent.revision, publisher_origin),
            )

        await self.persistence.async_in_transaction(
            write, authorize=current, finalize_authorize=current, require_full_sync=True)

    async def pending(self, origin):
        def read(tx):
            rows = tx.fetchall(
                "SELECT event.event_id,event.origin,event.original "
                "FROM djconnect_native_pair_retirements AS event "
                "JOIN djconnect_surface_pairs AS pair ON pair.binding=event.local_binding "
                "WHERE pair.state='retired' AND event.delivered=0 AND event.origin=? "
                "ORDER BY event.rowid LIMIT ?", (origin, _MAX_BATCH),
            )
            return [NativePairRetirement(*row) for row in rows]

        return await self.persistence.async_in_transaction(read)

    async def deliver_withdrawals(self, publisher, origin, *, guard, deadline):
        """Retry committed opt-outs until the separately authenticated publisher confirms."""
        guard()
        publisher_origin = publisher.origin

        def pending(tx):
            return tx.fetchall(
                "SELECT event_id,original,consent_revision FROM djconnect_native_pair_retirements AS event "
                "WHERE origin=? AND publisher_origin=? AND withdrawn=0 "
                "AND EXISTS (SELECT 1 FROM djconnect_native_widget_consent AS choice "
                "WHERE choice.local_binding=event.local_binding AND choice.enabled=0 "
                "AND choice.revision>event.consent_revision) ORDER BY event.rowid LIMIT ?",
                (origin, publisher_origin, _MAX_BATCH),
            )

        for event_id, original, revision in await self.persistence.async_in_transaction(pending):
            guard()
            await publisher.publish("withdraw", {
                "contract_version": 1, "pair_binding": json.loads(original)["pair_binding"],
                "consent_revision": revision,
            }, guard=guard, deadline=deadline)
            guard()
            await self.persistence.async_in_transaction(
                lambda tx: tx.execute(
                    "UPDATE djconnect_native_pair_retirements SET withdrawn=1 "
                    "WHERE event_id=? AND original=? AND consent_revision=? AND publisher_origin=?",
                    (event_id, original, revision, publisher_origin),
                ), require_full_sync=True)

    async def deliver(self, transport, *, guard, deadline):
        """Send a bounded batch. Unconfirmed events remain pending across restarts."""
        guard()
        origin = transport.origin
        events = await self.pending(origin)
        confirmed = 0
        for event in events:
            guard()
            require(transport.origin == origin, "native_retirement_authority_changed", 503)
            body = event.body()
            reply = await transport.post_retirement(body, guard=guard, deadline=deadline)
            guard()
            expected = {"contract_version": 1, "api_audience": body["api_audience"],
                        "event_id": event.event_id, "pair_binding": body["pair_binding"],
                        "event_sha256": hashlib.sha256(event.original.encode("utf-8")).hexdigest(),
                        "state": "retired"}
            require(reply.status == 200 and canonical(reply.body) == canonical(expected),
                    "native_retirement_ack_invalid", 502)
            require(await self.acknowledge(event), "native_retirement_event_changed", 503)
            confirmed += 1
        return confirmed

    async def acknowledge(self, event):
        """Call after authenticated acceptance of this exact event and origin."""
        def write(tx):
            result = tx.fetchone(
                "UPDATE djconnect_native_pair_retirements SET delivered=1 "
                "WHERE event_id=? AND origin=? AND original=? "
                "AND EXISTS (SELECT 1 FROM djconnect_surface_pairs AS pair "
                "WHERE pair.binding=local_binding AND pair.state='retired') "
                "RETURNING event_id", (event.event_id, event.origin, event.original),
            )
            return result is not None

        return await self.persistence.async_in_transaction(write, require_full_sync=True)
