"""Automatic ordinary-pair journal; private storage ACK, never push admission.

Only successful ordinary pairing schedules this work. GET/status/voice and
startup do not mint records. No lease, registrar, signer or native grant is
constructed here. Restart/restore qualification remains a separate gate.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import re
import uuid

from .persistence import PersistenceError, persistence_service

_MAX_ROWS = 4096  # Local retained-record resource cap, not an enrollment budget.


def _uuid(value):
    try:
        parsed = uuid.UUID(value)
        return parsed.version == 4 and str(parsed) == value
    except (ValueError, TypeError, AttributeError):
        return False


@dataclass(frozen=True, repr=False)
class LocalPairRecord:
    """Core-private acknowledgement; deliberately no affirmative authority API."""

    instance_id: str
    auth_generation: str


class PairJournal:
    def __init__(self, persistence):
        self.persistence = persistence

    async def record(self, binding, entry_id, generation, current):
        def write(tx):
            identity = tx.fetchone("SELECT instance_id FROM djconnect_surface_pair_store WHERE singleton=1")
            count = tx.fetchone("SELECT count(*) FROM djconnect_surface_pairs")[0]
            if identity is None:
                if count:
                    raise PersistenceError("Surface pair store identity missing")
                identity = (str(uuid.uuid4()),)
                tx.execute("INSERT INTO djconnect_surface_pair_store VALUES (1,?)", identity)
            if not _uuid(identity[0]):
                raise PersistenceError("Surface pair store identity invalid")
            row = tx.fetchone("SELECT entry_id,auth_generation,state FROM djconnect_surface_pairs WHERE binding=?", (binding,))
            if row is not None:
                if row[0] != entry_id or not _uuid(row[1]) or row[2] != "recorded":
                    raise PersistenceError("Surface pair record retired or invalid")
                return LocalPairRecord(identity[0], row[1])
            if count >= _MAX_ROWS:
                raise PersistenceError("Surface pair journal capacity reached")
            # A replaced actual auth binding never leaves its predecessor current.
            tx.execute("UPDATE djconnect_surface_pairs SET state='retired' WHERE entry_id=?", (entry_id,))
            tx.execute("INSERT INTO djconnect_surface_pairs VALUES (?,?,?,'recorded')", (binding, entry_id, generation))
            return LocalPairRecord(identity[0], generation)

        return await self.persistence.async_in_transaction(
            write, authorize=current, finalize_authorize=current, require_full_sync=True)

    async def retire(self, binding, entry_id, generation):
        def write(tx):
            # An early retirement may reach SQLite before the original record.
            # Preserve that tombstone; a late write must never resurrect it.
            identity = tx.fetchone("SELECT instance_id FROM djconnect_surface_pair_store WHERE singleton=1")
            if identity is None:
                if tx.fetchone("SELECT count(*) FROM djconnect_surface_pairs")[0]:
                    raise PersistenceError("Surface pair store identity missing")
                tx.execute("INSERT INTO djconnect_surface_pair_store VALUES (1,?)", (str(uuid.uuid4()),))
            elif not _uuid(identity[0]):
                raise PersistenceError("Surface pair store identity invalid")
            row = tx.fetchone("SELECT binding FROM djconnect_surface_pairs WHERE binding=?", (binding,))
            if row is None:
                count = tx.fetchone("SELECT count(*) FROM djconnect_surface_pairs")[0]
                if count >= _MAX_ROWS:
                    raise PersistenceError("Surface pair journal capacity reached")
                tx.execute("INSERT INTO djconnect_surface_pairs VALUES (?,?,?,'retired')", (binding, entry_id, generation))
            else:
                tx.execute("UPDATE djconnect_surface_pairs SET state='retired' WHERE binding=?", (binding,))
        await self.persistence.async_in_transaction(write, require_full_sync=True)


@dataclass(repr=False)
class PairRegistration:
    """One captured genuine pairing attempt, fenced before any storage await."""

    hass: object
    runtime: object
    entry: object
    coordinates: tuple
    binding: str
    journal: PairJournal
    fence: object
    fence_revision: int
    generation: str = field(default_factory=lambda: str(uuid.uuid4()))
    retired: bool = False
    phase: str = "pending"
    acknowledgement: LocalPairRecord | None = None
    tasks: set = field(default_factory=set, repr=False)
    data: object = field(init=False, repr=False)
    options: object = field(init=False, repr=False)

    def __post_init__(self):
        self.data = self.entry.data
        self.options = self.entry.options

    def current(self):
        from .client_retirement import is_retired_entry
        from .retired_provider import TRANSFER_FENCE
        from .surface_registration import _coordinates
        domain = self.hass.data.get("djconnect", {})
        return (not self.retired and not self.hass.is_stopping
                and domain.get(self.entry.entry_id) is self.runtime
                and self.runtime.entry is self.entry
                and self.entry.data is self.data and self.entry.options is self.options
                and getattr(self.runtime, "surface_pair_registration", None) is self
                and any(e is self.entry for e in self.hass.config_entries.async_entries("djconnect"))
                and self.entry.disabled_by is None and self.entry.state.value == "loaded"
                and not is_retired_entry(self.entry)
                and self.entry.entry_id not in domain.get(TRANSFER_FENCE, set())
                and _coordinates(self.runtime, self.entry) == self.coordinates
                and self.runtime.surface_registration_retirement is self.fence
                and self.fence.revision == self.fence_revision)

    def schedule(self, operation):
        try:
            task = self.hass.async_create_task(operation)
        except RuntimeError:
            operation.close()
            self.phase = "unavailable"
            return
        self.tasks.add(task)
        task.add_done_callback(self._settled)

    def _settled(self, task):
        self.tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            self.acknowledgement = None
            self.phase = "unavailable"

    def retire(self):
        if self.retired:
            return
        # No await or scheduling precedes the local delivery fence.
        self.retired = True
        self.phase = "retired"
        self.acknowledgement = None
        self.schedule(self._retire())

    async def _retire(self):
        try:
            await self.journal.retire(self.binding, self.entry.entry_id, self.generation)
        except (PersistenceError, PermissionError):
            # Local negative state remains closed. No retry/repair or new epoch.
            self.phase = "retirement_unconfirmed"

    async def reconcile(self):
        try:
            owner_task = asyncio.current_task()
            ack = await self.journal.record(self.binding, self.entry.entry_id,
                self.generation, lambda: not owner_task.cancelling() and self.current())
            if asyncio.current_task().cancelling() or not self.current():
                self.retire()
                return
            # Storage settlement is only a local record, never public authority.
            self.acknowledgement = ack
            self.phase = "recorded"
        except asyncio.CancelledError:
            self.retire()
            raise
        except (PersistenceError, PermissionError):
            self.phase = "unavailable" if not self.retired else self.phase


def schedule_pair_registration(hass, runtime):
    """Call only after actual successful pair validation/persistence scheduling.

    ConfigEntry updater return is not a disk ACK. The captured tuple must still
    be current at both SQLite admission points and after definitive settlement.
    """
    from .surface_registration import PairingRetirement, _coordinates
    entry = getattr(runtime, "entry", None)
    if entry is None or type(getattr(runtime, "surface_registration_retirement", None)) is not PairingRetirement:
        return
    coordinates = _coordinates(runtime, entry)
    device, client, token, installation, actual_token, actual_device = coordinates
    prefix = {"ios": "ios", "macos": "macos", "watchos": "watchos"}.get(client)
    if (prefix is None or type(device) is not str
            or re.fullmatch(r"djconnect-" + prefix + r"-[A-Za-z0-9]{12}", device) is None
            or type(token) is not str or not token or not token.isascii()
            or len(token) > 4096 or token != actual_token or device != actual_device
            or token != token.strip()
            or type(installation) is not str
            or re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", installation) is None
            or type(runtime.surface_registration_retirement) is not PairingRetirement):
        return
    try:
        journal = PairJournal(persistence_service(hass))
    except RuntimeError:
        return  # Ordinary pairing remains independent of push availability.
    # This is a private journal key, NOT the normative signed pair digest.
    binding = hashlib.sha256(b"DJC-LOCAL-PAIR-JOURNAL-V1\n" + json.dumps(
        [entry.entry_id, *coordinates[:4]], ensure_ascii=True,
        separators=(",", ":")).encode()).hexdigest()
    previous = getattr(runtime, "surface_pair_registration", None)
    if type(previous) is PairRegistration:
        if previous.binding == binding:
            return  # Duplicate/retry/late response cannot renew or resurrect.
        previous.retire()
    fence = runtime.surface_registration_retirement
    record = PairRegistration(hass, runtime, entry, coordinates, binding, journal,
                              fence, fence.revision)
    runtime.surface_pair_registration = record
    if not record.current():
        record.retire()
        return
    record.schedule(record.reconcile())
