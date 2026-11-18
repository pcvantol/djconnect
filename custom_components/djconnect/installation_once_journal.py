"""Original local metadata once journal. No key, signer, registry or live factory.

SQLite WAL/FULL acknowledgements do not prove host power-loss/restore freshness.
All records/results are metadata DATA only, not permission or effect evidence.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
import re

from . import installation_principal_data as codec

MAX_RECORDS = 128  # Implementation ceiling; the REQUIRED owner attests actual policy.
MAX_REVISION = 9007199254740990
ZERO_HASH = "0" * 64
_SELECT_ORIGINAL = (
    "SELECT operation_id,kind,preparation_hash,context_hash,policy_hash,deadline_ms,"
    "phase,revision,result_hash,terminal_reserved,ledger_revision "
    "FROM djconnect_installation_once WHERE operation_id=?"
)


class InstallationOnceError(RuntimeError):
    """Closed input/conflict/capacity error without original values."""


class _UncertainAcknowledgement(RuntimeError):
    """A committed transaction cannot be treated as a precommit input rejection."""


def _require(value):
    if not value:
        raise InstallationOnceError("installation_once_unavailable")


def _hash(value):
    _require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None)


@dataclass(frozen=True, repr=False)
class OriginalOperation:
    operation_id: str
    kind: str
    preparation_hash: str
    context_hash: str
    policy_hash: str
    deadline_ms: int
    expected_local_revision: int | None
    records: tuple = field(repr=False)

    def coordinates(self):
        return (self.operation_id, self.kind, self.preparation_hash,
            self.context_hash, self.policy_hash, self.deadline_ms)


class InstallationOnceOwner(ABC):
    """Independent phase-specific None-or-raise ports, with NO concrete factory.

    JSON, matching hashes, a bool, ordinary pairing or subclassing alone do not
    establish actual management/custody/clock/restore authority. Implementations
    must attest original context independently, including original API intent
    acknowledgement for the bootstrap-signing preparation. No effect is executed.
    """
    @abstractmethod
    def validate_policy(self, capacity: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def validate_storage(self, persistence) -> None:
        """Original actual storage owner, independent of positive runtime grant."""
        raise NotImplementedError

    @abstractmethod
    def validate_positive(self, original: OriginalOperation) -> None:
        raise NotImplementedError

    @abstractmethod
    def validate_metadata(self, original: OriginalOperation, result_hash: str) -> None:
        """Attest the original metadata result, never assert key/sign effect."""
        raise NotImplementedError


@dataclass(frozen=True, repr=False)
class JournalData:
    row: tuple
    classification: str = field(default="LOCAL_ONCE_METADATA_ONLY", init=False)


@dataclass(frozen=True, repr=False)
class JournalOutcome:
    state: str
    data: JournalData | None = None
    original: object = None
    classification: str = field(default="LOCAL_ONCE_METADATA_ONLY", init=False)


@dataclass(eq=False, repr=False)
class _OriginalReservation:
    operation: OriginalOperation
    closed: bool = False
    metadata_attempted: bool = False
    terminal_attempted: bool = False


class InstallationOnceJournal:
    """Only acknowledged NEW reservations mint process-local bookkeeping handles.

    Existing SQL/equal rows/status/duplicate/restart can never recreate a handle.
    Negative terminal bookkeeping uses its reserved row after positive retirement;
    loss of the original actual storage owner remains UNKNOWN, never a new store.
    """
    def __init__(self, persistence, owner: InstallationOnceOwner, *, capacity: int):
        _require(isinstance(owner, InstallationOnceOwner)
            and type(capacity) is int and 1 <= capacity <= MAX_RECORDS)
        self.persistence, self.owner, self.capacity = persistence, owner, capacity
        self._provider = persistence._provider
        self._readiness = persistence.readiness
        self._attempted = {}
        self._handles = {}
        _require(owner.validate_policy(capacity) is None)
        self._storage()

    def _storage(self):
        _require(self.persistence._provider is self._provider
            and self.persistence.readiness is self._readiness and self._readiness.ready)
        _require(self.owner.validate_storage(self.persistence) is None)

    def _positive(self, original, handle=None, result_hash=None):
        self._storage()
        if handle is not None:
            self._owned(handle)
            _require(not handle.closed)
        try:
            _require(self.owner.validate_policy(self.capacity) is None)
            _require(self.owner.validate_positive(original) is None)
            if result_hash is not None:
                _require(self.owner.validate_metadata(original, result_hash) is None)
        except Exception:
            if handle is not None:
                handle.closed = True
            raise

    def _owned(self, handle):
        _require(type(handle) is _OriginalReservation
            and self._handles.get(handle.operation.operation_id) is handle)

    async def _write(self, operation, authorize):
        task = asyncio.current_task()
        def allowed():
            if task.cancelling():
                return False
            try:
                self._storage()
                authorize()
                return True
            except Exception:
                return False
        try:
            value = await self.persistence.async_in_transaction(operation,
                authorize=allowed, finalize_authorize=allowed, require_full_sync=True)
        except Exception:
            if task.cancelling():
                raise asyncio.CancelledError from None
            raise
        if task.cancelling():
            raise asyncio.CancelledError
        try:
            self._storage()
        except Exception:
            raise _UncertainAcknowledgement("installation_once_unknown") from None
        return value

    @staticmethod
    def _generation(text):
        record = codec.decode_record(text, record_type="custody_generation_preparation")
        v = record.values
        return OriginalOperation(v["custody_operation_id"], "custody_generation", record.digest,
            v["operator_admission_binding_sha256"], v["custody_policy_sha256"],
            v["original_generation_deadline_unix_ms"], v["expected_local_revision"], (record,))

    @staticmethod
    def _signing(*, intent, **chain):
        records = codec.check_bootstrap_chain(**chain)
        i = codec.decode_record(intent, record_type="original_admission_intent")
        p, t = records[-2:]
        iv, pv, tv = i.values, p.values, t.values
        # A valid DATA chain cannot legalize contradictory local once identities,
        # even when no earlier generation row is present in this SQLite store.
        _require(records[0].values["custody_operation_id"] != pv["registration_operation_id"])
        _require(iv["bootstrap_preparation_sha256"] == p.digest)
        _require(all(iv[k] == pv[k] for k in
            ("subject_sha256", "registration_operation_id", "admission_context_sha256")))
        _require(all(iv[k] == tv[k] for k in ("registration_operation_id", "challenge_id",
            "challenge_nonce_sha256", "expected_registry_revision", "original_authorization_deadline_unix_ms")))
        return OriginalOperation(pv["registration_operation_id"], "bootstrap_signing", p.digest,
            pv["admission_context_sha256"], tv["policy_sha256"],
            pv["original_signing_deadline_unix_ms"], None, (*records, i))

    async def async_reserve_generation(self, text):
        return await self._reserve(self._generation(text))

    async def async_reserve_signing(self, *, intent, **chain):
        return await self._reserve(self._signing(intent=intent, **chain))

    @staticmethod
    def _next(tx):
        row = tx.fetchone("SELECT revision FROM djconnect_installation_once_state WHERE singleton=1")
        _require(row is not None and type(row[0]) is int and 0 <= row[0] < MAX_REVISION)
        tx.execute("UPDATE djconnect_installation_once_state SET revision=? WHERE singleton=1", (row[0] + 1,))
        return row[0] + 1

    async def _reserve(self, original):
        self._positive(original)  # Required independent port, not DATA equality.
        op = original.operation_id
        if op in self._attempted:
            _require(self._attempted[op] == original.coordinates())
            return JournalOutcome("EXISTING_DATA_ONLY", await self.async_status(op))
        _require(len(self._attempted) < self.capacity)
        self._attempted[op] = original.coordinates()  # Before first await; never cleared.
        def write(tx):
            row = tx.fetchone(_SELECT_ORIGINAL, (op,))
            if row is not None:
                _require(tuple(row[:6]) == original.coordinates())
                return JournalData(tuple(row)), False
            count = tx.fetchone("SELECT count(*) FROM djconnect_installation_once")[0]
            _require(count < self.capacity and count < MAX_RECORDS)
            state = tx.fetchone("SELECT revision FROM djconnect_installation_once_state WHERE singleton=1")
            _require(state is not None and (original.expected_local_revision is None
                or state[0] == original.expected_local_revision))
            revision = self._next(tx)
            values = (*original.coordinates(), 0, 0, ZERO_HASH, 1, revision)
            tx.execute("INSERT INTO djconnect_installation_once VALUES (?,?,?,?,?,?,?,?,?,?,?)", values)
            return JournalData(values), True
        try:
            data, inserted = await self._write(write, lambda: self._positive(original))
        except InstallationOnceError:
            raise
        except Exception:
            return JournalOutcome("UNKNOWN")
        if not inserted:
            return JournalOutcome("EXISTING_DATA_ONLY", data)
        handle = _OriginalReservation(original)
        self._handles[op] = handle  # Only original NEW commit acknowledgement, no await.
        try:
            self._positive(original, handle)
        except Exception:
            handle.closed = True
            return JournalOutcome("ACKNOWLEDGED_CLOSED", data, handle)
        return JournalOutcome("ACKNOWLEDGED_METADATA_RESERVATION", data, handle)

    async def async_status(self, operation_id):
        _require(type(operation_id) is str and codec._UUID.fullmatch(operation_id) is not None)
        self._storage()
        row = await self.persistence.async_in_transaction(lambda tx: tx.fetchone(
            _SELECT_ORIGINAL, (operation_id,)))
        self._storage()
        return None if row is None else JournalData(tuple(row))

    def retire(self, handle):
        """Synchronous local fence before ANY terminal lock/storage wait."""
        self._owned(handle)
        handle.closed = True

    async def async_settle_metadata(self, handle, result_hash):
        self._owned(handle)
        _hash(result_hash)
        self._positive(handle.operation, handle, result_hash)
        _require(not handle.metadata_attempted)
        handle.metadata_attempted = True
        return await self._transition(handle, result_hash=result_hash)

    async def async_retire(self, handle):
        self.retire(handle)
        if handle.terminal_attempted:
            return JournalOutcome("EXISTING_DATA_ONLY", await self.async_status(handle.operation.operation_id))
        handle.terminal_attempted = True
        return await self._transition(handle, result_hash=None)

    async def _transition(self, handle, *, result_hash):
        original = handle.operation
        terminal = result_hash is None
        def authorize():
            self._owned(handle)
            if not terminal:
                self._positive(original, handle, result_hash)
        def write(tx):
            row = tx.fetchone(_SELECT_ORIGINAL, (original.operation_id,))
            _require(row is not None and tuple(row[:6]) == original.coordinates() and row[9] == 1)
            _require(row[6] in ((0, 1) if terminal else (0,)) and row[7] == row[6])
            revision = self._next(tx)
            values = (*row[:6], 2 if terminal else 1, row[7] + 1,
                row[8] if terminal else result_hash, 1, revision)
            tx.execute("UPDATE djconnect_installation_once SET phase=?,revision=?,result_hash=?,ledger_revision=? "
                "WHERE operation_id=?", (values[6], values[7], values[8], revision, original.operation_id))
            return JournalData(values)
        try:
            data = await self._write(write, authorize)
        except Exception:
            handle.closed = True
            return JournalOutcome("UNKNOWN")
        if not terminal:
            try:
                self._positive(original, handle, result_hash)
            except Exception:
                handle.closed = True
                return JournalOutcome("ACKNOWLEDGED_CLOSED", data)
        return JournalOutcome("ACKNOWLEDGED_TERMINAL_METADATA" if terminal else "ACKNOWLEDGED_RESULT_METADATA", data)
