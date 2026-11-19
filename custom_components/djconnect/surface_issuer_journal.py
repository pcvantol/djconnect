"""Hash-only issuer stages; no key, enrolment, request or credential persistence.

The same original operation has separate challenge and issue reservations.
Restart cannot recreate the RAM stage receipt or resend either consumed phase.
Only normal persistence migration15 creates the table; no request-time repair.
These fences confer no operator, signer, source or remote-effect authority.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
import json
import re
import threading

from .surface_push_contract import require
from .surface_push_wire import canonical, safe_integer

MAX_IDENTITIES = 64
PHASES = frozenset({'challenge_reserved', 'nonce_held', 'challenge_unknown',
    'issue_reserved', 'credential_held', 'issue_unknown', 'withdrawn', 'expired'})


def _hash(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value),
        'surface_issuer_journal_invalid', 503)


def _snapshot(value):
    data = deepcopy(value)
    require(type(data) is dict and set(data) == {'version', 'high_water_ms', 'records'}
        and type(data['version']) is int and data['version'] == 1
        and safe_integer(data['high_water_ms'], 0) and type(data['records']) is dict
        and len(data['records']) <= MAX_IDENTITIES, 'surface_issuer_journal_invalid', 503)
    for identity, row in data['records'].items():
        _hash(identity)
        require(type(row) is dict and set(row) == {'binding', 'operation', 'challenge',
            'issue', 'terminal', 'phase'}, 'surface_issuer_journal_invalid', 503)
        for key in ('binding', 'operation', 'challenge'):
            _hash(row[key])
        for key in ('issue', 'terminal'):
            if row[key] is not None:
                _hash(row[key])
        require(type(row['phase']) is str and row['phase'] in PHASES
            and (row['phase'] not in {'challenge_reserved', 'nonce_held', 'challenge_unknown'}
                or row['issue'] is None)
            and (row['phase'] not in {'issue_reserved', 'credential_held', 'issue_unknown'}
                or row['issue'] is not None)
            and ((row['phase'] in {'withdrawn', 'expired'}) == (row['terminal'] is not None)),
            'surface_issuer_journal_invalid', 503)
    encoded = canonical(data)
    require(len(encoded.encode()) <= 65536, 'surface_issuer_journal_invalid', 503)
    return data, encoded


def _cancelled():
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise asyncio.CancelledError


class IssuerStageStore:
    """One adapter per journal; cross-instance SQLite revision CAS is mandatory."""
    def __init__(self, persistence):
        self.persistence = persistence
        self._revision = None
        self._lock = asyncio.Lock()
        self._claim_lock = threading.Lock()
        self._journal_owner = None

    def claim(self, owner):
        """Bind one immutable journal view; never recycle a used adapter."""
        with self._claim_lock:
            require(owner is not None and self._journal_owner is None,
                'surface_issuer_journal_owner_changed', 503)
            self._journal_owner = owner
        return _OwnedIssuerStageStore(self, owner)

    def _check_owner(self, owner):
        require(owner is not None and owner is self._journal_owner,
            'surface_issuer_journal_owner_changed', 503)

    async def _load(self, owner):
        self._check_owner(owner)
        async with self._lock:
            row = await self.persistence.async_in_transaction(lambda tx: tx.fetchone(
                'SELECT revision,high_water_ms,body FROM djconnect_surface_issuer_journal WHERE singleton=1'))
            require(row is not None and safe_integer(row[0], 0)
                and safe_integer(row[1], 0)
                and (self._revision is None or self._revision == row[0]),
                'surface_issuer_journal_unavailable', 503)
            require(type(row[2]) is str, 'surface_issuer_journal_invalid', 503)
            data, encoded = _snapshot(json.loads(row[2]))
            require(data['high_water_ms'] == row[1] and row[2] == encoded,
                'surface_issuer_journal_invalid', 503)
            self._revision = row[0]
            _cancelled()
            return data

    async def _save(self, value, owner):
        self._check_owner(owner)
        data, encoded = _snapshot(value)  # Freeze before the first await.
        async with self._lock:
            expected = self._revision
            require(safe_integer(expected, 0) and expected < 9007199254740991,
                'surface_issuer_journal_unavailable', 503)
            def save(tx):
                row = tx.fetchone('SELECT revision,high_water_ms FROM djconnect_surface_issuer_journal WHERE singleton=1')
                require(row is not None and row[0] == expected and row[1] <= data['high_water_ms'],
                    'surface_issuer_journal_owner_changed', 503)
                tx.execute('UPDATE djconnect_surface_issuer_journal SET revision=?,high_water_ms=?,body=? WHERE singleton=1',
                    (expected + 1, data['high_water_ms'], encoded))
            await self.persistence.async_in_transaction(save)
            self._revision = expected + 1  # Definitive commit, never a queued write ACK.
            _cancelled()  # SQLite can consume cancellation delivery while retaining its count.


@dataclass(frozen=True, repr=False)
class _OwnedIssuerStageStore:
    adapter: IssuerStageStore = field(repr=False)
    owner: object = field(repr=False)

    async def async_load(self):
        return await self.adapter._load(self.owner)

    async def async_save(self, value):
        return await self.adapter._save(value, self.owner)


@dataclass(frozen=True, repr=False)
class IssuerStageReceipt:
    identity: str
    binding: str
    operation: str
    owner: object = field(repr=False)


class IssuerStageJournal:
    """Bounded original identities, never LRU-evicted to permit reissue.

    The lifecycle must hash original origin/install/delegation/revision for the
    identity, and ALL immutable key/scope/source/owner/grant fields for binding.
    Hashes cannot recover raw IDs after restart: no automatic status/reissue.
    """
    def __init__(self, store):
        self._owner = object()
        require(type(store) is IssuerStageStore, 'surface_issuer_journal_unavailable', 503)
        self.store = store.claim(self._owner)
        self._state = None
        self._failed = False
        self._live = {}
        self._withdrawn = set()
        self._lock = asyncio.Lock()

    async def initialize(self):
        async with self._lock:
            if self._state is None and not self._failed:
                try:
                    self._state, _ = _snapshot(await self.store.async_load())
                except BaseException:
                    self._failed = True
                    raise
            self._ready()

    def _ready(self):
        _cancelled()
        require(not self._failed and self._state is not None,
            'surface_issuer_journal_unavailable', 503)

    def _clock(self, now):
        self._ready()
        if not safe_integer(now, 1) or now < self._state['high_water_ms']:
            self._failed = True
            require(False, 'surface_issuer_clock_quarantined', 503)
        self._state['high_water_ms'] = now

    async def _save(self):
        try:
            await self.store.async_save(self._state)
            _cancelled()
        except BaseException:
            self._failed = True
            self._live.clear()
            raise

    def _receipt(self, receipt, phase):
        self._ready()
        require(type(receipt) is IssuerStageReceipt and receipt.owner is self._owner
            and self._live.get(receipt.identity) is receipt and receipt.identity not in self._withdrawn,
            'surface_issuer_stage_withdrawn', 503)
        row = self._state['records'].get(receipt.identity)
        require(row is not None and row['binding'] == receipt.binding
            and row['operation'] == receipt.operation and row['phase'] == phase,
            'surface_issuer_stage_consumed', 503)
        return row

    async def reserve_challenge(self, identity, binding, operation, digest, *, now):
        for value in (identity, binding, operation, digest):
            _hash(value)
        async with self._lock:
            self._clock(now)
            require(identity not in self._state['records'] and identity not in self._withdrawn
                and len(self._state['records']) < MAX_IDENTITIES,
                'surface_issuer_stage_consumed', 503)
            receipt = IssuerStageReceipt(identity, binding, operation, self._owner)
            self._live[identity] = receipt
            self._state['records'][identity] = {'binding': binding, 'operation': operation,
                'challenge': digest, 'issue': None, 'terminal': None, 'phase': 'challenge_reserved'}
            await self._save()
            self._receipt(receipt, 'challenge_reserved')
            return receipt

    async def complete_challenge(self, receipt, *, accepted, now):
        require(type(accepted) is bool, 'surface_issuer_journal_invalid', 503)
        async with self._lock:
            self._clock(now)
            row = self._receipt(receipt, 'challenge_reserved')
            row['phase'] = 'nonce_held' if accepted else 'challenge_unknown'
            await self._save()
            self._receipt(receipt, row['phase'])
            if not accepted:
                self._live.pop(receipt.identity, None)

    async def reserve_issue(self, receipt, digest, *, now):
        _hash(digest)
        async with self._lock:
            self._clock(now)
            row = self._receipt(receipt, 'nonce_held')
            require(row['issue'] is None and digest != row['challenge'],
                'surface_issuer_journal_invalid', 503)
            row['issue'], row['phase'] = digest, 'issue_reserved'
            await self._save()
            self._receipt(receipt, 'issue_reserved')

    async def complete_issue(self, receipt, *, accepted, now):
        require(type(accepted) is bool, 'surface_issuer_journal_invalid', 503)
        async with self._lock:
            self._clock(now)
            row = self._receipt(receipt, 'issue_reserved')
            row['phase'] = 'credential_held' if accepted else 'issue_unknown'
            await self._save()
            self._receipt(receipt, row['phase'])
            self._live.pop(receipt.identity, None)

    async def terminal(self, identity, binding, operation, digest, *, now, expired=False):
        for value in (identity, binding, operation, digest):
            _hash(value)
        require(type(expired) is bool, 'surface_issuer_journal_invalid', 503)
        # Fence any in-flight RAM receipt BEFORE waiting for lock or persistence.
        require(not self._failed and self._state is not None,
            'surface_issuer_journal_unavailable', 503)
        require(identity in self._withdrawn or len(self._withdrawn) < MAX_IDENTITIES,
            'surface_issuer_journal_unavailable', 503)
        self._withdrawn.add(identity)
        self._live.pop(identity, None)
        async with self._lock:
            self._clock(now)
            row = self._state['records'].get(identity)
            if row is None:
                require(len(self._state['records']) < MAX_IDENTITIES,
                    'surface_issuer_journal_unavailable', 503)
                row = {'binding': binding, 'operation': operation, 'challenge': digest,
                    'issue': None, 'terminal': None, 'phase': 'challenge_unknown'}
                self._state['records'][identity] = row
            require(row['binding'] == binding and row['operation'] == operation,
                'surface_issuer_journal_owner_changed', 503)
            require(row['terminal'] is None, 'surface_issuer_stage_consumed', 503)
            row['terminal'], row['phase'] = digest, 'expired' if expired else 'withdrawn'
            await self._save()
