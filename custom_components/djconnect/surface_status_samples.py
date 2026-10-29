"""Original playback-source samples. Private DATA, never native authority.

Sample UUIDs/ordinals are not presentation or widget grant identities. No HTTP
reader, restore adoption, signing, positive factory or native effect lives here.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
import hashlib
import json
import math
import time
import uuid
import weakref

from .persistence import PersistenceError

SAFE = 9007199254740991
MAX_SCOPES = 4096


class ObservedPlayback(dict):
    """Existing JSON dictionary with private, non-serialized source metadata."""

    def __init__(self, playback, original_status):
        super().__init__(playback)
        self.original_status = original_status


def capture_command_source(hass, runtime):
    """Capture only the genuine guarded command's existing observer before GET."""
    from .ask_dj.dialogue import current_turn
    turn = current_turn.get()
    if turn is None or not turn.effect_started:
        return None
    observer = hass.data.get("djconnect", {}).get("playback_observation_manager")
    observed = getattr(observer, "_spotify_sessions", {}).get(turn.scope.removeprefix("profile:"))
    if observed is None or observed.integration_runtime is not runtime:
        return None
    return capture_source(hass, observed)


def _stamp():
    wall, mono = time.time(), time.monotonic()
    if not math.isfinite(wall) or not math.isfinite(mono) or not 0 < wall * 1000 <= SAFE:
        raise ValueError("status_sample_clock_unavailable")
    return int(wall * 1000), mono


@dataclass(frozen=True, repr=False)
class StatusRecord:
    scope: str
    sample_id: str
    ordinal: int
    observed_ms: int
    state: str | None
    ended: bool


@dataclass(frozen=True, repr=False)
class SourceWitness:
    hass: object
    domain: dict
    storage: object
    revision: int
    manager: object
    broadcast: object
    observed: object
    source: dict
    values: dict
    data: object
    options: object
    visual_source: object
    command: int
    allowed: object
    scope: str
    provider_runtime: object
    settings: tuple
    _revoked: list = field(default_factory=lambda: [False], repr=False)

    def current(self, ending=None):
        try:
            from .domain.storage import STORE_KEY
            owner, sid = self.observed.owner_profile_id, self.observed.session_id
            current = self.manager.current_active(owner)
            marker = getattr(self.broadcast, "_status_end_pending", None)
            return (not self._revoked[0] and not self.hass.is_stopping
                and self.hass.data.get("djconnect") is self.domain
                and self.domain.get(STORE_KEY) is self.storage and self.storage._loaded
                and self.storage.authority_revision == self.revision
                and self.domain.get("session_runtime_manager") is self.manager
                and current is not None and current.session_id == sid
                and current.broadcast is self.broadcast
                and _settings(current) == self.settings
                and self.manager._history_source_contexts.get(sid) is self.source
                and self.source == self.values
                and self.domain["playback_observation_manager"]._spotify_sessions.get(owner) is self.observed
                and self.observed.integration_runtime.entry.data is self.data
                and self.observed.integration_runtime.entry.options is self.options
                and self.observed.visual_source is self.visual_source
                and self.observed.command_revision == self.command
                and ((ending is None and marker is None
                      and (owner, sid) not in self.manager._visual_ending)
                     or (ending is not None and marker is ending))
                and self.allowed())
        except Exception:
            return False

def _settings(active):
    return tuple(getattr(active, key, None) for key in
                 ("settings_generation", "settings_revision", "defaults_revision"))


def capture_source(hass, observed):
    """Capture genuine already-loaded source identity BEFORE provider/guard await."""
    try:
        from .domain.storage import STORE_KEY
        from .forecast_imagery import artist_authority
        domain = hass.data["djconnect"]
        storage, manager = domain[STORE_KEY], domain["session_runtime_manager"]
        active = manager.current_active(observed.owner_profile_id)
        source = manager._history_source_contexts[observed.session_id]
        values = dict(source)
        if (len(values) > 16 or any(type(k) is not str or type(v) is not str
                or len(k) > 64 or len(v) > 512 for k, v in values.items())):
            return None
        entry = observed.integration_runtime.entry
        private = [entry.entry_id, observed.owner_profile_id, observed.session_id, values, _settings(active)]
        scope = hashlib.sha256(b"DJC-ORIGINAL-STATUS-SOURCE-V1\n" + json.dumps(
            private, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
        witness = SourceWitness(hass, domain, storage, storage.authority_revision,
            manager, active.broadcast, observed, source, values,
            entry.data, entry.options, observed.visual_source, observed.command_revision,
            artist_authority(hass, observed.integration_runtime,
                owner_profile_id=observed.owner_profile_id, expected_source=values), scope,
            domain.get(values.get("provider_entry_id")), _settings(active))
        if not witness.current():
            return None
        _track_witness(witness)
        return witness
    except Exception:
        return None


@dataclass(frozen=True, repr=False)
class OriginalSample:
    witness: SourceWitness
    observed_ms: int
    observed_monotonic: float
    state: str | None
    ended: bool
    sample_id: str
    _consumed: list = field(default_factory=lambda: [False], repr=False)

    def consume(self):
        if self._consumed[0]:
            return False
        self._consumed[0] = True
        return True

    def current(self):
        return self.witness.current(self if self.ended else None)


def seal(witness, state):
    """Call immediately on actual backend return/readback entry, before await."""
    states = {"playing": "playing", "paused": "paused", "stopped": "stopped", "idle": "unknown"}
    if witness is None or type(state) is not str or state not in states or not witness.current():
        return None
    try:
        ms, mono = _stamp()
    except ValueError:
        return None
    return OriginalSample(witness, ms, mono, states[state], False, str(uuid.uuid4()))


def advance_own_command(sample):
    """One no-await N->N+1; retain original time/event and the same spent latch."""
    if type(sample) is not OriginalSample or not sample.current():
        return None
    witness = sample.witness
    witness.observed.command_revision += 1
    updated = replace(sample, witness=replace(witness, command=witness.command + 1))
    if not updated.current():
        return None
    _track_witness(updated.witness)
    return updated


def _track_witness(witness):
    # Negative listeners only, installed before awaits; weak values never keep
    # an old source/credential snapshot alive. No rights or admission registry.
    for runtime in (witness.observed.integration_runtime, witness.provider_runtime):
        if runtime is None:
            continue
        values = getattr(runtime, "_status_source_witnesses", None)
        if not isinstance(values, weakref.WeakValueDictionary):
            values = runtime._status_source_witnesses = weakref.WeakValueDictionary()
        values[id(witness)] = witness


class StatusJournal:
    def __init__(self, persistence):
        self.persistence = persistence

    async def record(self, sample):
        if type(sample) is not OriginalSample or not sample.consume():
            return None
        # No retry/reissue, including lost ACK/cancellation. All SQL inputs are
        # immutable scalars captured on the HA loop, never HA objects in worker.
        scope, event = sample.witness.scope, sample.sample_id
        ms, state, ended = sample.observed_ms, sample.state, sample.ended
        if (type(ms) is not int or not 0 < ms <= SAFE or type(ended) is not bool
                or (ended and state is not None)
                or (not ended and state not in {"playing", "paused", "stopped", "unknown"})):
            raise PersistenceError("status_sample_invalid")
        caller = asyncio.current_task()
        def current():
            return not caller.cancelling() and sample.current()
        def write(tx):
            row = tx.fetchone("SELECT sample_id,ordinal,observed_ms,playback_state,ended "
                "FROM djconnect_status_samples WHERE scope_hash=?", (scope,))
            if row is not None and row[0] == event:
                if (row[2], row[3], bool(row[4])) != (ms, state, ended):
                    raise PersistenceError("status_sample_identity_conflict")
                return StatusRecord(scope, *row[:4], bool(row[4]))
            if row is not None and (row[4] or ms < row[2] or row[1] >= SAFE):
                raise PersistenceError("status_sample_closed_or_clock_regressed")
            if row is None and (ended or tx.fetchone("SELECT count(*) FROM djconnect_status_samples")[0] >= MAX_SCOPES):
                raise PersistenceError("status_sample_capacity_or_missing_origin")
            ordinal = row[1] + 1 if row is not None else 1
            tx.execute("INSERT OR REPLACE INTO djconnect_status_samples VALUES (?,?,?,?,?,?)",
                (scope, event, ordinal, ms, state, int(ended)))
            return StatusRecord(scope, event, ordinal, ms, state, ended)
        try:
            result = await self.persistence.async_in_transaction(write, authorize=current,
                finalize_authorize=current, require_full_sync=True)
        except Exception:
            if caller.cancelling():
                raise asyncio.CancelledError from None
            raise
        if caller.cancelling():
            raise asyncio.CancelledError
        return result if sample.current() else None


async def publish(manager, active, sample):
    """One original sample, guarded through SQL and final no-await publication."""
    if type(sample) is not OriginalSample or (sample.witness.broadcast is not active.broadcast
            or sample.witness.observed.session_id != active.session_id):
        return
    journal = getattr(manager, "_status_samples", None)
    if journal is None:
        return
    active.broadcast.original_status_sample = None
    active.broadcast._original_status_capture = None
    try:
        try:
            result = await journal.record(sample)
        except Exception:
            return  # Ordinary playback remains independent; never export/log bodies.
        if result is not None and not asyncio.current_task().cancelling() and sample.current():
            active.broadcast.original_status_sample = result
            active.broadcast._original_status_capture = None if sample.ended else sample
            if not sample.ended and type(sample.witness) is SourceWitness:
                for runtime in (sample.witness.observed.integration_runtime, sample.witness.provider_runtime):
                    if runtime is None:
                        continue
                    targets = getattr(runtime, "_status_sample_broadcasts", None)
                    if not isinstance(targets, weakref.WeakValueDictionary):
                        targets = runtime._status_sample_broadcasts = weakref.WeakValueDictionary()
                    targets[id(active.broadcast)] = active.broadcast
    finally:
        if sample.ended:
            release_end(active, sample)


def release_end(active, sample):
    """Retain the negative fence without retaining retired source credentials."""
    if active.broadcast._status_end_pending is sample:
        active.broadcast._status_end_pending = object()


def _drop_capture(broadcast):
    broadcast.original_status_sample = None
    broadcast._original_status_capture = None
    if type(getattr(broadcast, "_status_end_pending", None)) is OriginalSample:
        broadcast._status_end_pending = object()


def retire_runtime_status(runtime):
    """Negative callback only; weak recipients cannot retain a disposed Session."""
    witnesses = getattr(runtime, "_status_source_witnesses", None)
    if isinstance(witnesses, weakref.WeakValueDictionary):
        for witness in tuple(witnesses.values()):
            witness._revoked[0] = True
        witnesses.clear()
    targets = getattr(runtime, "_status_sample_broadcasts", None)
    if not isinstance(targets, weakref.WeakValueDictionary):
        return
    for broadcast in tuple(targets.values()):
        capture = getattr(broadcast, "_original_status_capture", None)
        if capture is None:
            capture = getattr(broadcast, "_status_end_pending", None)
        if type(capture) is OriginalSample and (capture.witness.observed.integration_runtime is runtime
                or capture.witness.provider_runtime is runtime):
            _drop_capture(broadcast)
    targets.clear()


def retire_observer_status(hass, observed):
    values = getattr(observed.integration_runtime, "_status_source_witnesses", None)
    if isinstance(values, weakref.WeakValueDictionary):
        for witness in tuple(values.values()):
            if witness.observed is observed:
                witness._revoked[0] = True
    manager = hass.data.get("djconnect", {}).get("session_runtime_manager")
    active = manager.current_active(observed.owner_profile_id) if manager is not None else None
    if active is not None:
        capture = getattr(active.broadcast, "_original_status_capture", None)
        if capture is None:
            capture = getattr(active.broadcast, "_status_end_pending", None)
        if type(capture) is OriginalSample and capture.witness.observed is observed:
            _drop_capture(active.broadcast)


def capture_end(manager, owner, session_id):
    """Capture original end source/time before the manager-lock await."""
    active = manager.current_active(owner)
    if active is None or (session_id and active.session_id != session_id):
        return None
    original = getattr(active.broadcast, "_original_status_capture", None)
    if type(original) is not OriginalSample or not original.current():
        return None
    try:
        ms, mono = _stamp()
    except ValueError:
        return None
    return OriginalSample(original.witness, ms, mono, None, True, str(uuid.uuid4()))


def retire_for_end(active, sample):
    """Unconditional synchronous fence, including absence of visual listeners."""
    broadcast = active.broadcast
    if getattr(broadcast, "_status_end_pending", None) is not None:
        return None
    owns = (type(sample) is OriginalSample and sample.witness.broadcast is broadcast
            and sample.witness.observed.session_id == active.session_id and sample.witness.current())
    broadcast._status_end_pending = sample if owns else object()
    broadcast.original_status_sample = None
    broadcast._original_status_capture = None
    return sample if owns else None
