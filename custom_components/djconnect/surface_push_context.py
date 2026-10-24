"""Original RAM-only paired context continuations; never issuer admission.

A short submit guard is separate from the registered row's original authority.
Opaque retained tombstones cannot renew a purpose or refund an attempt budget.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
import math
import secrets
import weakref

from .surface_push_contract import require, SurfacePushError
from .surface_push_purpose import SurfacePurposeCredential
from .surface_push_wire import safe_integer
from .transport_operations import operation_created_ms, LIFETIME_MS, FUTURE_SKEW_MS

MAX_CONTEXTS = 64
MAX_OWNER = 16
MAX_DEVICE = 8
MAX_PURPOSE = 8
MAX_PENDING = 8
SUBMIT_MS = 30000


def _cancelled():
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise asyncio.CancelledError


def _finite_clock(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _deadline(original, milliseconds):
    """Round the complete represented sum downward, including its addition."""
    exact = Fraction(original) + Fraction(milliseconds, 1000)
    try:
        result = float(exact)
    except (ValueError, OverflowError):
        raise SurfacePushError('surface_context_expired', 409) from None
    require(math.isfinite(result), 'surface_context_expired', 409)
    if Fraction(result) > exact:
        result = math.nextafter(result, -math.inf)
    require(result > original, 'surface_context_expired', 409)
    return result


def _facts(purpose):
    return (purpose.original_wall_ms, purpose.original_monotonic,
        purpose.owner_binding, purpose.device_binding, purpose.binding_id,
        purpose.grant_binding, purpose.source_binding, purpose.scope_digest,
        purpose.delegation_revision,
        hashlib.sha256(purpose.policy_json.encode()).hexdigest())


@dataclass(frozen=True, repr=False)
class _Root:
    original: object
    key: tuple
    facts: tuple
    expiry: object
    clock: object


@dataclass(frozen=True, repr=False)
class _Start:
    wall: object
    mono: object
    identity: tuple
    roots: tuple
    runtime: object
    wall_clock: object
    mono_clock: object


@dataclass(eq=False, repr=False)
class _Purpose:
    original: object
    reference: str
    expiry: int
    attempts: int = 0


@dataclass(eq=False, repr=False)
class _Context:
    handle: str
    operation_id: str
    key: tuple[str, str, str, str]
    purpose: _Purpose
    admission: object = field(repr=False)
    deadline: int
    mono_deadline: float
    last_wall: int
    last_mono: float
    start: _Start
    purpose_budget_ms: int
    submit_budget_ms: int
    version: int = field(default=3, init=False)
    digest: str | None = None
    task: object = field(default=None, repr=False)
    closed: str | None = None


class SurfaceContextContinuations:
    def __init__(self, service, *, wall, monotonic):
        self.service, self.wall, self.monotonic = service, wall, monotonic
        self._contexts = {}
        self._operations = {}
        self._purposes = []  # Weak original identities; never hash mutable bearer bytes.
        self._pending = {}
        self._starts = {}  # Original pre-await clocks survive cancellation/lost context replies.

    def _roots(self, device, session):
        roots = []
        for key, purpose in tuple(getattr(self.service, '_purposes', {}).items()):
            if (type(key) is not tuple or len(key) != 4 or key[1] != device
                    or key[3] != session or type(purpose) is not SurfacePurposeCredential):
                continue
            try:
                facts = _facts(purpose)
                expiry = json.loads(purpose.policy_json)['original_grant_expires_at_ms']
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                facts, expiry = (), None  # Retain an invalid original; never recapture it.
            roots.append(_Root(weakref.ref(purpose),
                (*key[:3], hashlib.sha256(session.encode()).hexdigest()),
                facts, expiry, purpose.monotonic))
        require(len(roots) <= MAX_CONTEXTS, 'surface_context_capacity', 503)
        return tuple(roots)

    def _root(self, start, admission):
        require(start.wall_clock is self.wall and start.mono_clock is self.monotonic,
            'surface_context_expired', 409)
        runtime = start.runtime() if start.runtime is not None else None
        require(runtime is admission.runtime and
            (start.runtime is None or runtime is not None), 'surface_context_conflict', 409)
        purpose = admission.purpose
        root = next((r for r in start.roots if r.original() is purpose), None)
        require(root is not None and root.key == self._key(admission)
            and bool(root.facts) and root.facts == _facts(purpose)
            and root.clock is purpose.monotonic and root.clock is self.monotonic,
            'surface_context_conflict', 409)
        return root

    @staticmethod
    def _budgets(start, root, created):
        wall, origin = root.facts[:2]
        require(safe_integer(wall, 1) and safe_integer(root.expiry, 1)
            and 0 < root.expiry - wall <= 28_800_000 and _finite_clock(origin)
            and safe_integer(start.wall, 1) and _finite_clock(start.mono)
            and start.wall >= wall and start.mono >= origin,
            'surface_context_expired', 409)
        mono = math.floor(Fraction(root.expiry - wall)
            + 1000 * (Fraction(origin) - Fraction(start.mono)))
        purpose = min(mono, root.expiry - start.wall)
        submit = min(SUBMIT_MS, purpose, created + LIFETIME_MS - start.wall)
        require(safe_integer(purpose, 1) and purpose <= 28_800_000
            and safe_integer(submit, 1) and submit <= SUBMIT_MS,
            'surface_context_expired', 409)
        return purpose, submit

    @staticmethod
    def _key(admission):
        return (admission.owner, admission.device, admission.binding,
            hashlib.sha256(admission.session_id.encode()).hexdigest())

    def _retire(self, h, reason):
        h.closed = h.closed or reason
        h.admission = None
        task, h.task = h.task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    def invalidate(self, owner=None, session_id=None, purpose=None):
        session = hashlib.sha256(session_id.encode()).hexdigest() if session_id is not None else None
        for h in self._contexts.values():
            if ((owner is None or h.key[0] == owner) and (session is None or h.key[3] == session)
                    and (purpose is None or h.purpose.original() is purpose)):
                self._retire(h, 'withdrawn')
        # Pending captures may not have returned paired authority yet. Conservatively
        # cancel them before Session/unload/withdrawal can yield; no rearm on failure.
        for task, pending_session, pending_purposes in tuple(self._pending.values()):
            if session is not None and pending_session != session:
                continue
            if purpose is not None and not any(ref() is purpose for ref in pending_purposes):
                continue
            if task is not asyncio.current_task():
                task.cancel()

    def _collect(self):
        now, mono = self.wall(), self.monotonic()
        for h in self._contexts.values():
            if not h.closed and (now >= h.deadline or mono >= h.mono_deadline):
                self._retire(h, 'expired')

    def _check(self, h, fresh=None):
        _cancelled()
        require(self._contexts.get(h.handle) is h and h.version == 3
            and self._starts.get(h.operation_id) is h.start and not self.service.closed,
            'surface_context_unknown', 409)
        require(not h.closed, 'surface_context_expired' if h.closed == 'expired'
            else 'surface_context_unknown', 409)
        now, mono = self.wall(), self.monotonic()
        if (not safe_integer(now, 1) or not _finite_clock(mono) or now < h.last_wall
                or mono < h.last_mono or now >= h.deadline or mono >= h.mono_deadline):
            self._retire(h, 'expired')
            raise SurfacePushError('surface_context_expired', 409)
        h.last_wall, h.last_mono = now, mono
        try:
            h.admission.validate()
            self._root(h.start, h.admission)
            require(h.purpose.original() is h.admission.purpose,
                'surface_context_conflict', 409)
        except BaseException:
            self._retire(h, 'withdrawn')
            raise
        if fresh is not None:
            fresh.validate()
            # A different authenticated caller cannot poison or retire the
            # original caller's handle merely by submitting its coordinates.
            require(self._key(fresh) == h.key and fresh.purpose is h.admission.purpose
                and fresh.runtime is h.admission.runtime and fresh.broadcast is h.admission.broadcast,
                'surface_context_conflict', 409)
        return True

    async def acquire(self, payload, headers):
        _cancelled()
        require(type(payload.get('contract_version')) is int
            and payload['contract_version'] == 3, 'surface_context_required', 409)
        # No unauthenticated UUID may consume retained capacity. This real paired
        # check is synchronous; original clocks still precede every async await.
        runtime = self.service.preauthorize_context(payload, headers)
        operation = payload['operation_id']
        wall, mono = self.wall(), self.monotonic()
        created = operation_created_ms(operation)
        require(operation not in self._pending and len(self._pending) < MAX_PENDING,
            'surface_context_capacity', 503)
        session_hash = hashlib.sha256(payload['session_id'].encode()).hexdigest()
        device_hash = hashlib.sha256(payload['device_id'].encode()).hexdigest()
        identity = (session_hash, device_hash, payload['client_type'])
        original_start = self._starts.get(operation)
        new_start = original_start is None
        if new_start:
            require(len(self._starts) < MAX_CONTEXTS
                and sum(start.identity[1] == device_hash for start in self._starts.values()) < MAX_DEVICE,
                'surface_context_capacity', 503)
            original_start = _Start(wall, mono, identity,
                self._roots(device_hash, payload['session_id']),
                weakref.ref(runtime) if runtime is not None else None,
                self.wall, self.monotonic)
            self._starts[operation] = original_start
        else:
            require(original_start.identity == identity, 'surface_context_conflict', 409)
        wall, mono = original_start.wall, original_start.mono
        require(safe_integer(wall, 1) and _finite_clock(mono)
            and created <= wall + FUTURE_SKEW_MS and wall < created + LIFETIME_MS,
            'surface_context_expired', 409)
        # Capture weak ORIGINAL map identities before the first await. Device
        # equality alone cannot authorize cancellation across Sessions/purposes.
        pending_purposes = tuple(root.original for root in original_start.roots)
        self._pending[operation] = (asyncio.current_task(), session_hash, pending_purposes)
        created_context = None
        try:
            admission = await self.service.admission(payload, headers)
            _cancelled()
            admission.validate()
            root = self._root(original_start, admission)
            require(not self.service.closed, 'surface_context_unknown', 409)
            self._collect()
            previous = self._operations.get(operation)
            if previous is not None:
                self._check(previous, admission)
                return self._reply(previous)
            key = self._key(admission)
            require(len(self._contexts) < MAX_CONTEXTS
                and sum(h.key[0] == key[0] for h in self._contexts.values()) < MAX_OWNER
                and sum(h.key[1] == key[1] for h in self._contexts.values()) < MAX_DEVICE,
                'surface_context_capacity', 503)
            original = next((p for p in self._purposes if p.original() is admission.purpose), None)
            expiry = root.expiry
            purpose_ms, submit_ms = self._budgets(original_start, root, created)
            if original is None:
                require(len(self._purposes) < MAX_CONTEXTS, 'surface_context_capacity', 503)
                original = _Purpose(weakref.ref(admission.purpose), 'djcpref_' + secrets.token_urlsafe(32), expiry)
                self._purposes.append(original)
            require(original.expiry == expiry and original.attempts < MAX_PURPOSE,
                'surface_context_capacity', 503)
            deadline = wall + submit_ms
            # Retain an authenticated late first attempt BEFORE checking its
            # original deadline. A slow/lost response cannot refund or reanchor it.
            h = _Context('djcctx_' + secrets.token_urlsafe(32), operation, key, original,
                admission, deadline, _deadline(mono, submit_ms), wall, mono,
                original_start, purpose_ms, submit_ms)
            self._contexts[h.handle] = h
            created_context = h
            self._operations[operation] = h
            original.attempts += 1
            self._check(h)  # Final no-await fence before returning the original handle.
            return self._reply(h)
        except asyncio.CancelledError:
            if created_context is not None:
                self._retire(created_context, 'withdrawn')
            # Cancellation while the original paired resolver is pending cannot
            # give a later same-UUID request fresh pre-await clocks.
            raise
        except BaseException:
            if created_context is not None:
                self._retire(created_context, 'withdrawn')
            # Any late error may follow successful paired authentication. Keep
            # the bounded original start rather than refund/reanchor unknown work.
            raise
        finally:
            self._pending.pop(operation, None)

    @staticmethod
    def _reply(h):
        return {'success': True, 'contract_version': 3, 'available': True,
            'context_handle': h.handle, 'operation_id': h.operation_id,
            'purpose_ref': h.purpose.reference, 'expires_at_ms': h.purpose.expiry,
            'context_expires_at_ms': h.deadline,
            'purpose_remaining_at_original_start_ms': h.purpose_budget_ms,
            'context_remaining_at_original_start_ms': h.submit_budget_ms,
            'cache_policy': 'private,no-store'}

    async def register(self, handle, intent, headers):
        _cancelled()
        require(type(handle) is str and handle in self._contexts, 'surface_context_unknown', 409)
        h = self._contexts[handle]
        self._check(h)
        require(intent.metadata()['operation_id'] == h.operation_id, 'surface_context_conflict', 409)
        require(h.task is None, 'surface_context_conflict', 409)
        require(h.digest is None or h.digest == intent.fingerprint, 'surface_context_conflict', 409)
        h.task = asyncio.current_task()  # Pending latch before paired resolution.
        bound = False
        try:
            fresh = await self.service.admission(intent.metadata(), headers)
            self._check(h, fresh)
            bound = True
            h.digest = intent.fingerprint  # Before the FIRST journal/effect await.
            # The guard is ONLY for this operation. Registry keeps the original
            # stable admission for the row's longer-lived background authority.
            result = await self.service.registry.register(intent, fresh, guard=lambda: self._check(h, fresh))
            self._check(h, fresh)
            self.service.track_registration(result)
            return {**result, 'contract_version': 3, 'context_handle': h.handle,
                'operation_id': h.operation_id, 'purpose_ref': h.purpose.reference}
        except asyncio.CancelledError:
            if bound:
                self._retire(h, 'withdrawn')
            raise
        finally:
            h.task = None
