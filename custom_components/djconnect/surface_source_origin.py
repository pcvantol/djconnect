"""Original Session/source-adoption journal, private DATA, never push rights.

An origin's UUID and phase revision do not implement af201 source_revision or
native source_generation. There is no public reader, restore adoption or signer.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
import hashlib
import json
import math
import re
import secrets
import time
from types import MappingProxyType
import uuid
import weakref

from .persistence import PersistenceError

MAX_ROWS = 4096
MAX_OPERATIONS = 3 * MAX_ROWS
SAFE = 9007199254740991
_EPOCH = object()


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, repr=False)
class OriginInput:
    origin: str
    operation: str
    acceptance: str
    terminal: str
    nonce: str
    terminal_nonce: str
    scope: str
    session: str
    owner: str
    created_ms: int


@dataclass(frozen=True, repr=False)
class OriginRecord:
    origin: str
    operation: str
    acceptance: str
    scope: str
    phase: str
    revision: int


class SourceJournal:
    """Three fixed original slots per retained row; retirement needs no new slot."""

    def __init__(self, persistence):
        self.persistence = persistence

    async def _settle(self, operation, current):
        task = asyncio.current_task()
        def allowed():
            return not task.cancelling() and current()
        try:
            result = await self.persistence.async_in_transaction(operation,
                authorize=allowed, finalize_authorize=allowed, require_full_sync=True)
        except Exception:
            if task.cancelling():
                raise asyncio.CancelledError from None
            raise
        if task.cancelling():
            raise asyncio.CancelledError
        return result

    async def prepare(self, original, current):
        identities = (original.origin, original.operation, original.acceptance, original.terminal)
        try:
            valid = all(str(uuid.UUID(v)) == v and uuid.UUID(v).version == 4 for v in identities)
        except (ValueError, TypeError, AttributeError):
            valid = False
        if (not valid or len(set(identities)) != 4
                or any(type(v) is not str or re.fullmatch('[a-f0-9]{64}', v) is None
                       for v in (original.scope, original.nonce, original.terminal_nonce))
                or type(original.created_ms) is not int or not 0 < original.created_ms <= SAFE
                or any(type(v) is not str or not 0 < len(v) <= 512 for v in (original.owner, original.session))):
            raise PersistenceError("source_origin_invalid_input")
        values = (original.origin, original.operation, original.acceptance,
            original.terminal, original.nonce, original.terminal_nonce,
            original.scope, original.session, original.created_ms)
        def write(tx):
            row = tx.fetchone("SELECT origin_id,operation_id,acceptance_id,terminal_id,"
                "nonce_hash,terminal_nonce_hash,scope_hash,session_id,created_ms,phase,revision "
                "FROM djconnect_source_origins WHERE origin_id=? OR session_id=?",
                (original.origin, original.session))
            if row is not None:
                if tuple(row[:9]) != values or row[9:] != ("prepared", 0):
                    raise PersistenceError("source_origin_conflict_or_retired")
                return OriginRecord(original.origin, original.operation,
                    original.acceptance, original.scope, "prepared", 0)
            session = tx.fetchone("SELECT owner_profile_id,lifecycle_status FROM "
                "djconnect_persistent_sessions WHERE session_id=?", (original.session,))
            if session != (original.owner, "OPENING") or tx.fetchone(
                    "SELECT 1 FROM djconnect_persistent_sessions WHERE owner_profile_id=? "
                    "AND session_id<>? AND lifecycle_status IN ('OPENING','ACTIVE') LIMIT 1",
                    (original.owner, original.session)):
                raise PersistenceError("source_original_session_not_available")
            count = tx.fetchone("SELECT count(*) FROM djconnect_source_origins")[0]
            if count >= MAX_ROWS or 3 * (count + 1) > MAX_OPERATIONS:
                raise PersistenceError("source_origin_capacity")
            if tx.fetchone("SELECT 1 FROM djconnect_source_origins WHERE operation_id IN (?,?,?) "
                    "OR acceptance_id IN (?,?,?) OR terminal_id IN (?,?,?) LIMIT 1",
                    (original.operation, original.acceptance, original.terminal) * 3):
                raise PersistenceError("source_origin_operation_conflict")
            tx.execute("INSERT INTO djconnect_source_origins VALUES (?,?,?,?,?,?,?,?,?,'prepared',0)", values)
            return OriginRecord(original.origin, original.operation,
                original.acceptance, original.scope, "prepared", 0)
        return await self._settle(write, current)

    async def accept(self, original, current):
        def write(tx):
            row = tx.fetchone("SELECT operation_id,acceptance_id,scope_hash,phase,revision "
                "FROM djconnect_source_origins WHERE origin_id=? AND session_id=?",
                (original.origin, original.session))
            if row != (original.operation, original.acceptance, original.scope, "prepared", 0):
                raise PersistenceError("source_origin_not_original_preparation")
            if tx.fetchone("SELECT owner_profile_id,lifecycle_status FROM "
                    "djconnect_persistent_sessions WHERE session_id=?", (original.session,)) != (original.owner, "ACTIVE"):
                raise PersistenceError("source_original_session_not_active")
            tx.execute("UPDATE djconnect_source_origins SET phase='accepted',revision=1 WHERE origin_id=?",
                (original.origin,))
            return OriginRecord(original.origin, original.operation,
                original.acceptance, original.scope, "accepted", 1)
        return await self._settle(write, current)

    async def retire(self, original):
        def write(tx):
            row = tx.fetchone("SELECT operation_id,terminal_id,terminal_nonce_hash,scope_hash,phase,revision "
                "FROM djconnect_source_origins WHERE origin_id=? AND session_id=?",
                (original.origin, original.session))
            if row is None:
                return None  # No early tombstone or new identity/capacity allocation.
            if row[:4] != (original.operation, original.terminal, original.terminal_nonce, original.scope):
                raise PersistenceError("source_terminal_identity_conflict")
            if row[4] != "retired":
                tx.execute("UPDATE djconnect_source_origins SET phase='retired',revision=? WHERE origin_id=?",
                    (row[5] + 1, original.origin))
            return original.terminal
        return await self._settle(write, lambda: True)


def _settings(active):
    return tuple(getattr(active, k, None) for k in
        ("settings_generation", "settings_revision", "defaults_revision",
         "mood_revision", "persona_revision", "presence_revision"))


class SourceAdoption:
    """Only the actual start continuation can bind/prepare/accept this original."""

    def __init__(self, hass, runtime, manager, committed, owner, source, provider, allowed, installation):
        self.hass, self.runtime, self.manager = hass, runtime, manager
        self.committed, self.owner, self.source = committed, owner, MappingProxyType(dict(source))
        self.provider, self.allowed = provider, allowed
        self.entry_data, self.entry_options = runtime.entry.data, runtime.entry.options
        from .surface_registration import _coordinates
        self.pair_fence = runtime.surface_registration_retirement
        self.pair_revision = self.pair_fence.revision
        self.pair_digest = _digest(_coordinates(runtime, runtime.entry))
        self.provider_data, self.provider_options = provider.entry.data, provider.entry.options
        self.epoch = _EPOCH
        self.origin, self.operation, self.acceptance, self.terminal = [str(uuid.uuid4()) for _ in range(4)]
        self.nonce, self.terminal_nonce = [hashlib.sha256(secrets.token_bytes(32)).hexdigest() for _ in range(2)]
        self.created_ms = int(time.time() * 1000)
        self.created_monotonic = time.monotonic()
        self.scope = _digest(["DJC-ORIGINAL-SOURCE-ADOPTION-V1", installation,
            runtime.entry.entry_id, owner, source])
        self.session = ""
        self.original = None
        self.broadcast = None
        self._planned_broadcast = None
        self.settings = None
        self.observer = None
        self.record = None
        self.phase = "captured"
        self.retired = False
        self.journal = SourceJournal(manager._persistent_sessions._persistence)
        self._terminal_task = None
        self._prepare_spent = self._accept_spent = False
        creator = asyncio.current_task()
        self._creator_ref = weakref.ref(creator) if creator is not None else None
        self._creator_done = False
        reference = weakref.ref(self)
        def finished(task):
            original = reference()
            if original is not None:
                if task.cancelling() or task.cancelled() or original.phase != "accepted":
                    original.retire()
                original._creator_done = True
                original._creator_ref = None
        if creator is not None:
            creator.add_done_callback(finished)

    def current(self):
        if self.retired:
            return False
        if self.epoch is not _EPOCH or self.committed is None:
            self.retire()
            return False
        creator = self._creator_ref() if self._creator_ref is not None else None
        if not self._creator_done and (creator is None or creator.cancelling()):
            self.retire()
            return False
        try:
            runtime, provider = self.runtime, self.provider
            from .surface_registration import _coordinates
            valid = (not self.hass.is_stopping and self.committed.current()
                and runtime.entry.data is self.entry_data and runtime.entry.options is self.entry_options
                and provider.entry.data is self.provider_data and provider.entry.options is self.provider_options
                and runtime.surface_registration_retirement is self.pair_fence
                and self.pair_fence.revision == self.pair_revision
                and _digest(_coordinates(runtime, runtime.entry)) == self.pair_digest
                and self.allowed())
            if self.broadcast is not None:
                active = self.manager.current_active(self.owner)
                valid = (valid and active is not None and active.session_id == self.session
                    and active.broadcast is self.broadcast and _settings(active) == self.settings
                    and self.manager._history_source_contexts.get(self.session) == self.source)
            if self.observer is not None:
                observed = self.hass.data["djconnect"]["playback_observation_manager"]
                valid = (valid and observed._spotify_sessions.get(self.owner) is self.observer
                    and self.observer.integration_runtime is self.runtime
                    and self.observer.owner_profile_id == self.owner
                    and self.observer.session_id == self.session)
            if not valid:
                self.retire()
            return bool(valid)
        except Exception:
            self.retire()
            return False

    def bind(self, session):
        creator = self._creator_ref() if self._creator_ref is not None else None
        if (self.session or creator is None or self._creator_done
                or creator is not asyncio.current_task() or not self.current()):
            return False
        self.session = session
        self.scope = _digest(["DJC-ORIGINAL-SOURCE-SESSION-V1", self.scope, session])
        self.original = OriginInput(self.origin, self.operation, self.acceptance,
            self.terminal, self.nonce, self.terminal_nonce, self.scope, session,
            self.owner, self.created_ms)
        return True

    async def prepare(self, active):
        if self._prepare_spent or self.original is None or not self.current():
            return
        self._prepare_spent = True
        self.settings, self._planned_broadcast = _settings(active), active.broadcast
        self.scope = _digest(["DJC-ORIGINAL-SOURCE-SETTINGS-V1", self.scope, self.settings])
        self.original = replace(self.original, scope=self.scope)
        self.phase = "preparing"
        try:
            result = await self.journal.prepare(self.original, self.current)
            if not self.current():
                self.retire()
                return
            self.record, self.phase = result, "prepared"
        except asyncio.CancelledError:
            self.retire()
            raise
        except Exception:
            self.retire()

    async def accept(self, active):
        if self._accept_spent or self.phase != "prepared" or not self.current():
            return
        self._accept_spent = True
        if active.broadcast is not self._planned_broadcast or _settings(active) != self.settings:
            self.retire()
            return
        self.broadcast = active.broadcast
        try:
            result = await self.journal.accept(self.original, self.current)
            if not self.current():
                self.retire()
                return
            self.record, self.phase = result, "accepted"
            self.manager._source_origins[self.session] = self
        except asyncio.CancelledError:
            self.retire()
            raise
        except Exception:
            self.retire()

    def validate_original_capture(self):
        if self.phase != "accepted" or self.observer is None or not self.current():
            raise PermissionError("source_origin_unavailable")
        return self.record  # Private source DATA, never a permission DTO.

    def retire(self):
        if self.retired:
            return
        self.retired, self.phase = True, "retired"
        if self.manager._source_origins.get(self.session) is self:
            self.manager._source_origins.pop(self.session, None)
        # Drop original source/credential snapshots before any scheduling.
        self.committed = self.runtime = self.provider = self.allowed = None
        self.entry_data = self.entry_options = self.provider_data = self.provider_options = None
        self.broadcast = self._planned_broadcast = self.observer = None
        self.pair_fence = None
        if self.original is not None and self._prepare_spent and not self.hass.is_stopping:
            journal, original = self.journal, self.original
            async def terminal():
                try:
                    return ("SETTLED", await journal.retire(original))
                except Exception:
                    return ("UNKNOWN", None)  # No retry or terminal/native success claim.
            self._terminal_task = self.hass.async_create_task(terminal())

    def finish_start(self):
        if self.phase != "accepted":
            self.retire()


def capture_session_source(hass, runtime, context):
    """Original bound source capture before discovery; no cold load or fallback."""
    try:
        from .profile_observation import capture_source_committed
        from .profile_backend import profile_backend_runtime
        from .forecast_imagery import artist_authority
        from .session_runtime import session_runtime_manager
        from .surface_registration import PairingRetirement, _coordinates
        committed = capture_source_committed(hass)
        manager = session_runtime_manager(hass)
        if committed is None or manager._persistent_sessions is None:
            return None
        fence = getattr(runtime, "surface_registration_retirement", None)
        coordinates = _coordinates(runtime, runtime.entry)
        # The old public-role fence stays retired after ordinary pairing. A
        # genuinely new source DATA event does not rearm or borrow that role.
        # Its own original negative latch and exact auth tuple are independent.
        if (type(fence) is not PairingRetirement
            or not coordinates[2] or coordinates[2] != coordinates[4] or coordinates[0] != coordinates[5]):
            return None
        household = committed.household
        profile = household.profiles.get(context.profile_id)
        account = household.music_accounts.get(context.music_account_id)
        if profile is not context.profile or account is None:
            return None
        provider = profile_backend_runtime(hass, runtime, provider_only=True)
        source = {"backend_id": context.backend_id, "music_account_id": account.account_id,
            "provider_account_id": account.provider_account_id, "provider_entry_id": provider.entry.entry_id}
        installation = {**runtime.entry.data, **runtime.entry.options}.get("ha_install_id")
        if (type(installation) is not str or not 0 < len(installation) <= 256
            or any(type(v) is not str or len(v) > 512 for v in source.values())):
            return None
        allowed = artist_authority(hass, runtime, owner_profile_id=context.profile_id, expected_source=source)
        original = SourceAdoption(hass, runtime, manager, committed, context.profile_id,
            source, provider, allowed, installation)
        if (not 0 < original.created_ms <= SAFE or not math.isfinite(original.created_monotonic)
                or not original.current()):
            return None
        manager._source_origin_intents[id(original)] = original
        for entry_runtime in (runtime, provider):
            values = getattr(entry_runtime, "_source_origin_intents", None)
            if not isinstance(values, weakref.WeakValueDictionary):
                values = entry_runtime._source_origin_intents = weakref.WeakValueDictionary()
            values[id(original)] = original
        return original
    except Exception:
        return None


def retire_sources(manager, owner=None, session=None):
    for original in list(getattr(manager, "_source_origin_intents", {}).values()):
        if (owner is None or original.owner == owner) and (not session or original.session == session):
            original.retire()


def retire_runtime_sources(runtime):
    for original in list(getattr(runtime, "_source_origin_intents", {}).values()):
        original.retire()


def retire_settings_sources(manager, owner, session=None, authorize=None):
    values = list(getattr(manager, "_source_origin_intents", {}).values())
    if any(not v.retired and v.owner == owner and (not session or v.session == session) for v in values):
        if authorize is None or authorize():
            retire_sources(manager, owner, session)


def attach_observer(manager, observed):
    original = getattr(manager, "_source_origins", {}).get(observed.session_id)
    if original is None:
        return
    creator = original._creator_ref() if original._creator_ref is not None else None
    if (creator is not None and not original._creator_done
            and creator is asyncio.current_task() and original.phase == "accepted"
            and original.observer is None
            and observed.integration_runtime is original.runtime
            and observed.owner_profile_id == original.owner
            and observed.session_id == original.session and original.current()):
        original.observer = observed
