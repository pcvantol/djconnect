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
import weakref

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


# These are private in-process witnesses, never serialized FlowResult fields.
_FLOW_OWNER = "_surface_pair_flow_owner"
_PENDING_ORIGIN = "_surface_pair_original_validation"
_PENDING_CONTEXTS = "config_flow_app_pairing_pending"


def _pair_tuple(data):
    return (data.get("device_id"), data.get("client_type"), data.get("device_token"))


def _flow_owner(context):
    reference = context.get(_FLOW_OWNER)
    return reference() if isinstance(reference, weakref.ReferenceType) else None


@dataclass(repr=False)
class PendingPairOrigin:
    """Original successful pending POST, transferred by its actual native flow."""

    context: dict
    received: dict
    owner: object
    flow_id: str
    pair_code: str
    coordinates: tuple
    prior_entries: tuple
    phase: str = "pending"
    pairing: object = None

    def retire(self):
        if self.phase != "consumed":
            self.phase = "retired"

    def pending_current(self, flow):
        pending = flow.hass.data.get("djconnect", {}).get(_PENDING_CONTEXTS, {})
        return (self.phase == "pending" and self.owner() is flow
                and flow.flow_id == self.flow_id
                and pending.get(self.pair_code) is self.context
                and _flow_owner(self.context) is flow
                and self.context.get("flow_id") == self.flow_id
                and self.context.get(_PENDING_ORIGIN) is self
                and self.context.get("pairing_received") is self.received
                and _pair_tuple(self.received) == self.coordinates)

    def handoff(self, flow):
        if not self.pending_current(flow) or _pair_tuple(flow._pairing) != self.coordinates:
            self.retire()
            return False
        self.pairing = flow._pairing
        self.phase = "handoff"
        return True

    def consume_created(self, flow, entry):
        # Consume before any subsequent scheduling/await, including on failure.
        valid = (self.phase == "handoff" and self.owner() is flow
                 and flow.flow_id == self.flow_id and flow._pairing is self.pairing
                 and _pair_tuple(flow._pairing) == self.coordinates)
        self.phase = "consumed"
        task = asyncio.current_task()
        if (not valid or entry is None or (task is not None and task.cancelling())
                or flow.hass.is_stopping or entry.disabled_by is not None
                or entry.state.value != "loaded"
                or any(entry is old for old in self.prior_entries)):
            return None
        if _pair_tuple({**entry.data, **entry.options}) != self.coordinates:
            return None
        runtime = flow.hass.data.get("djconnect", {}).get(entry.entry_id)
        if runtime is None or runtime.entry is not entry:
            return None
        # The existing scheduler independently requires the exact loaded entry,
        # runtime/auth/data/fence, then checks them across FULL SQL settlement.
        return runtime


def pending_context_for_flow(flow, pending, pair_code):
    """Do not carry a previous flow's token/receipt across pair-code reuse."""
    context = pending.get(pair_code)
    owner = _flow_owner(context) if type(context) is dict else None
    if (type(context) is not dict or context.get("flow_id") != flow.flow_id
            or (owner is not None and owner is not flow)):
        if type(context) is dict:
            old = context.get(_PENDING_ORIGIN)
            if type(old) is PendingPairOrigin:
                old.retire()
        context = {}
        pending[pair_code] = context
    transferred = getattr(flow, "_surface_pending_origin", None)
    if (type(transferred) is PendingPairOrigin and transferred.phase == "handoff"
            and context is not transferred.context):
        transferred.retire()
        flow._surface_pending_origin = None
    # Untagged legacy RAM input may still finish ordinary pairing, but never
    # acquires an origin by being read. Only a new validated POST creates one.
    context[_FLOW_OWNER] = weakref.ref(flow)
    return context


def note_pending_pair(hass, context, received):
    """Call only after actual pending PairView code/type/device validation."""
    flow = _flow_owner(context)
    if flow is None or flow.hass is not hass or flow.flow_id != context.get("flow_id"):
        return received
    previous = context.get(_PENDING_ORIGIN)
    if type(previous) is PendingPairOrigin:
        if (previous.pending_current(flow)
                and previous.coordinates == _pair_tuple(received)):
            # Keep the same original object on a duplicate; optional ordinary
            # metadata may change without renewing the original validation.
            previous.received.update(received)
            return previous.received
        previous.retire()
        return received  # No replacement marker after conflict/unknown outcome.
    entries = getattr(getattr(hass, "config_entries", None), "async_entries", None)
    if not callable(entries):
        return received
    context["pairing_received"] = received
    context[_PENDING_ORIGIN] = PendingPairOrigin(context, received, weakref.ref(flow),
        flow.flow_id, context["pair_code"], _pair_tuple(received), tuple(entries("djconnect")))
    return received


def capture_pending_origin(flow, pair_code):
    """Capture the original object before async_set_unique_id, never its copy."""
    context = flow.hass.data.get("djconnect", {}).get(_PENDING_CONTEXTS, {}).get(pair_code)
    origin = context.get(_PENDING_ORIGIN) if type(context) is dict else None
    previous = getattr(flow, "_surface_pending_origin", None)
    if type(previous) is PendingPairOrigin and previous is not origin:
        previous.retire()
    if type(origin) is not PendingPairOrigin or not origin.pending_current(flow):
        return None
    return origin


def clear_pending_context(flow, pair_code):
    pending = flow.hass.data.get("djconnect", {}).get(_PENDING_CONTEXTS, {})
    context = pending.get(pair_code)
    owner = _flow_owner(context) if type(context) is dict else None
    if (type(context) is not dict or context.get("flow_id") != flow.flow_id
            or (owner is not None and owner is not flow)):
        return
    origin = context.get(_PENDING_ORIGIN)
    if type(origin) is PendingPairOrigin and origin.phase != "handoff":
        origin.retire()
    pending.pop(pair_code, None)


def abandon_pending_flow(flow):
    """Native flow removal retires untransferred work synchronously."""
    origin = getattr(flow, "_surface_pending_origin", None)
    if type(origin) is PendingPairOrigin:
        origin.retire()
    flow._surface_pending_origin = None
    pending = flow.hass.data.get("djconnect", {}).get(_PENDING_CONTEXTS, {})
    for code, context in tuple(pending.items()):
        if type(context) is dict and _flow_owner(context) is flow:
            original = context.get(_PENDING_ORIGIN)
            if type(original) is PendingPairOrigin:
                original.retire()
            pending.pop(code, None)
