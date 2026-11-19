"""Uncomposed hash-only bootstrap once journal; no owner or signing authority.

This primitive records ordering, not permission. No shipping caller or concrete
store is supplied. Ordinary SQLite NORMAL commits are NOT a qualified
power-loss-durable reservation. A future production adapter needs separate
schema, durability, original clock and authenticated owner qualification.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
import re

MAX_RECORDS = 64

class BootstrapOnceError(RuntimeError):
    """Closed local conflict/unavailable outcome; never a retry instruction."""


def _require(condition):
    if not condition:
        raise BootstrapOnceError('bootstrap_once_unavailable')


def _hash(value):
    _require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None)


@dataclass(frozen=True, repr=False)
class OnceRow:
    """Only immutable comparison digests and stage metadata, never credentials."""
    identity: str
    binding: str
    revision: int
    phase: str
    action: str

    def validate(self):
        for value in (self.identity, self.binding, self.action):
            _hash(value)
        _require(type(self.revision) is int and 0 <= self.revision < 9007199254740991)
        _require(type(self.phase) is str and self.phase in {'candidate', 'view_reserved', 'approval_recorded',
            'claim_reserved', 'retired'})


class BootstrapOnceStore(ABC):
    """Required CAS port, no default and no durability/authority Boolean.

    insert must atomically enforce unique original identity AND bounded retained
    capacity. compare_and_swap must compare ALL original fields in one database
    transaction. Neither method deletes tombstones or returns cached secrets.
    A committed but unacknowledged operation remains consumed. An implementation
    is not qualified for production by subclassing this interface.
    """
    def __init__(self):
        self._claimed = False

    def claim(self):
        _require(not self._claimed)
        self._claimed = True

    @abstractmethod
    async def insert(self, row: OnceRow) -> None:
        raise NotImplementedError

    @abstractmethod
    async def compare_and_swap(self, original: OnceRow, successor: OnceRow) -> None:
        raise NotImplementedError


@dataclass(eq=False, repr=False)
class _Pending:
    row: OnceRow
    busy: bool = True
    retired: bool = False
    poisoned: bool = False
    committed: bool = False
    owner: object = field(default_factory=object)


class BootstrapOnceJournal:
    """Original-process handles only; restart has no recoverable live receipt.

    Recorded approval is just DATA, not a HA-owner attestation. No handle here
    may instruct native SDK work or a management request. Future composition
    must independently validate original authority/clock before and after each
    await. This class does not accept a callback that fabricates that authority.
    """
    def __init__(self, store: BootstrapOnceStore):
        _require(isinstance(store, BootstrapOnceStore))
        store.claim()
        self._store = store
        self._records = {}
        self._owner = object()

    def begin(self, identity: str, binding: str, action: str):
        """Reserve RAM synchronously before any scheduling or awaited commit."""
        row = OnceRow(identity, binding, 0, 'candidate', action)
        row.validate()
        _require(identity not in self._records and len(self._records) < MAX_RECORDS)
        pending = _Pending(row, owner=self._owner)
        self._records[identity] = pending
        return pending

    def _owned(self, pending):
        _require(type(pending) is _Pending and pending.owner is self._owner
            and self._records.get(pending.row.identity) is pending)

    def retire(self, pending):
        """Immediate terminal RAM fence, even while a database commit is pending."""
        self._owned(pending)
        pending.retired = True

    def _after_commit(self, pending):
        task = asyncio.current_task()
        if task is not None and task.cancelling():
            raise asyncio.CancelledError
        _require(not pending.retired and not pending.poisoned)

    async def commit_candidate(self, pending):
        self._owned(pending)
        _require(pending.busy and not pending.committed and not pending.retired
            and not pending.poisoned)
        # Consume this call BEFORE its first await; a second caller cannot insert.
        pending.committed = True
        try:
            await self._store.insert(pending.row)
            self._after_commit(pending)
            pending.busy = False
        except BaseException:
            pending.poisoned = True
            raise

    async def advance(self, pending, phase: str, action: str):
        self._owned(pending)
        _hash(action)
        transitions = {'candidate': 'view_reserved', 'view_reserved': 'approval_recorded',
            'approval_recorded': 'claim_reserved'}
        _require(pending.committed and not pending.busy and not pending.poisoned
            and not pending.retired and transitions.get(pending.row.phase) == phase)
        original = pending.row
        successor = OnceRow(original.identity, original.binding, original.revision + 1, phase, action)
        successor.validate()
        pending.busy = True  # Before first await; duplicate phase cannot race us.
        try:
            await self._store.compare_and_swap(original, successor)
            pending.row = successor  # Commit remains true even if response is lost.
            self._after_commit(pending)
            pending.busy = False
        except BaseException:
            pending.poisoned = True
            raise

    async def persist_retirement(self, pending, action: str):
        """Separate bookkeeping after the synchronous fence; no remote claim."""
        self.retire(pending)
        _hash(action)
        _require(pending.committed and not pending.busy and not pending.poisoned
            and pending.row.phase != 'retired')
        original = pending.row
        successor = OnceRow(original.identity, original.binding, original.revision + 1, 'retired', action)
        successor.validate()
        pending.busy = True
        try:
            await self._store.compare_and_swap(original, successor)
            pending.row = successor
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise asyncio.CancelledError
            pending.busy = False
        except BaseException:
            pending.poisoned = True
            raise
