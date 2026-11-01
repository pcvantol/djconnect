"""Unused closed custody orchestration; no key provider, signer or factory.

Required independent ports are NOT supplied by DATA, pairing, or this module.
Only synchronous invocation is supported. Executor/async providers need their
own actual boundary qualification. Outcomes attest metadata, never key effects.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
import inspect
import re

from .installation_once_journal import InstallationOnceJournal, OriginalOperation


class CustodyUnavailable(RuntimeError):
    """Closed error without original data or provider exception values."""


def _require(ok):
    if not ok:
        raise CustodyUnavailable("installation_custody_unavailable")


class CustodyEffectPort(ABC):
    """Two fixed synchronous ports; no concrete implementation or default.

    Return only the public result's digest. Never return private material, a
    callable, coroutine or task. A digest does not prove that an effect happened.
    """

    @abstractmethod
    def generate_once(self, original: OriginalOperation) -> str:
        raise NotImplementedError

    @abstractmethod
    def bootstrap_possession_once(self, original: OriginalOperation) -> str:
        raise NotImplementedError


class CustodyOperationOwner(ABC):
    """Independent original authority, NOT a production admission implementation.

    All methods return None or raise. Before every positive continuation attest
    exact composition, management/install/custody/policy/restore/withdrawal and
    original wall+monotonic validity. Bootstrap possession additionally needs
    the genuinely accepted original API intent/challenge/withdrawal reserve;
    active registry epoch is NOT a bootstrap prerequisite. Operational signing
    is excluded. Actual providers require separate execution-boundary review.
    """

    @abstractmethod
    def validate_composition(self, journal: InstallationOnceJournal, port: CustodyEffectPort) -> None:
        raise NotImplementedError

    @abstractmethod
    def validate_attempt(self, original: OriginalOperation, port: CustodyEffectPort) -> None:
        raise NotImplementedError

    @abstractmethod
    def validate_result(self, original: OriginalOperation, result_hash: str) -> None:
        """Independently attest this original public result, not digest equality."""
        raise NotImplementedError


@dataclass(frozen=True, repr=False)
class CustodyOutcome:
    state: str
    metadata: object = field(default=None, repr=False)
    classification: str = field(default="CLOSED_CUSTODY_METADATA_ONLY", init=False)


@dataclass(eq=False, repr=False)
class _Attempt:
    original: OriginalOperation
    task: object = field(repr=False)
    reservation: object = field(default=None, repr=False)
    closed: bool = False
    attempted: bool = False


class InstallationCustodyOnce:
    """Unused composition over the original SQL19 journal, without a live owner.

    Pending slots precede awaits; spent slots survive UNKNOWN/withdrawal. A
    NEW acknowledged reservation is necessary, never sufficient authority.
    Status/equal rows/restart never recreate an effect invocation capability.
    """

    def __init__(self, journal: InstallationOnceJournal, owner: CustodyOperationOwner,
                 port: CustodyEffectPort):
        _require(type(journal) is InstallationOnceJournal
            and isinstance(owner, CustodyOperationOwner) and isinstance(port, CustodyEffectPort))
        self._journal, self._owner, self._port = journal, owner, port
        self._journal_owner, self._capacity = journal.owner, journal.capacity
        self._binding = (journal, owner, port, journal.owner, journal.capacity)
        self._attempts = {}
        try:
            self._composition()
        except Exception:
            raise CustodyUnavailable("installation_custody_unavailable") from None

    def _composition(self):
        self._identities()
        _require(self._owner.validate_composition(self._journal, self._port) is None)
        self._identities()

    def _identities(self):
        journal, owner, port, journal_owner, capacity = self._binding
        _require(self._journal is journal and self._owner is owner and self._port is port
            and self._journal_owner is journal_owner and journal.owner is journal_owner
            and self._capacity == capacity and journal.capacity == capacity)

    def _fence(self, slot):
        self._identities()
        task = asyncio.current_task()
        _require(task is slot.task and not task.cancelling()
            and self._attempts.get(slot.original.operation_id) is slot and not slot.closed)
        if slot.reservation is not None:
            self._journal._owned(slot.reservation)
            _require(slot.reservation.operation is slot.original and not slot.reservation.closed)

    def _positive(self, slot, result_hash=None):
        self._fence(slot)
        self._composition()
        self._fence(slot)
        self._journal._positive(slot.original, slot.reservation)
        self._fence(slot)
        _require(self._owner.validate_attempt(slot.original, self._port) is None)
        self._fence(slot)
        if result_hash is not None:
            _require(self._owner.validate_result(slot.original, result_hash) is None)
            self._fence(slot)

    def _close(self, slot):
        slot.closed = True  # Synchronous fence even before SQL acknowledgement.
        if slot.reservation is not None:
            self._journal.retire(slot.reservation)

    def retire(self, operation_id):
        """Synchronous local withdrawal; absence is not proof of no effect."""
        slot = self._attempts.get(operation_id)
        if slot is not None:
            self._close(slot)

    async def async_retire_metadata(self, operation_id):
        """Separate negative metadata; cannot prove no effect or free capacity."""
        self.retire(operation_id)
        slot = self._attempts.get(operation_id)
        if slot is None or slot.reservation is None:
            return CustodyOutcome("UNKNOWN")
        try:
            result = await self._journal.async_retire(slot.reservation)
            return CustodyOutcome(result.state, result.data)
        except asyncio.CancelledError:
            raise
        except Exception:
            return CustodyOutcome("UNKNOWN")

    async def async_generate(self, text):
        return await self._run(self._journal._generation(text))

    async def async_bootstrap_possession(self, *, intent, **chain):
        return await self._run(self._journal._signing(intent=intent, **chain))

    async def _run(self, original):
        _require(type(original) is OriginalOperation
            and original.kind in ("custody_generation", "bootstrap_signing"))
        op = original.operation_id
        _require(op not in self._attempts and len(self._attempts) < self._capacity)
        slot = _Attempt(original, asyncio.current_task())
        self._attempts[op] = slot  # Original pending latch BEFORE first await.
        try:
            self._positive(slot)
            result = await self._journal._reserve(original)
            if result.state in ("ACKNOWLEDGED_METADATA_RESERVATION", "ACKNOWLEDGED_CLOSED"):
                slot.reservation = result.original
            if result.state != "ACKNOWLEDGED_METADATA_RESERVATION":
                self._close(slot)
                return CustodyOutcome(result.state, result.data)
            if slot.closed:
                self._close(slot)  # Late ACK can never restore pending authority.
                return CustodyOutcome("ACKNOWLEDGED_CLOSED", result.data)
            _require(slot.reservation is not None)
            _require(not slot.attempted)
            slot.attempted = True  # Consumed BEFORE reentrant validation/call.
            self._positive(slot)
            # No await, task creation or executor hop between guard and call.
            value = (self._port.generate_once(original) if original.kind == "custody_generation"
                else self._port.bootstrap_possession_once(original))
            if inspect.iscoroutine(value) and inspect.getcoroutinestate(value) == inspect.CORO_CREATED:
                value.close()  # Dispose an unstarted coroutine WITHOUT running it.
            _require(not inspect.isawaitable(value) and type(value) is str
                and re.fullmatch(r"[a-f0-9]{64}", value) is not None)
            self._positive(slot, value)
            result = await self._journal.async_settle_metadata(slot.reservation, value)
            self._positive(slot, value)
            if result.state != "ACKNOWLEDGED_RESULT_METADATA":
                self._close(slot)
            return CustodyOutcome(result.state, result.data)
        except asyncio.CancelledError:
            self._close(slot)
            raise
        except Exception:
            self._close(slot)
            return CustodyOutcome("UNKNOWN")
