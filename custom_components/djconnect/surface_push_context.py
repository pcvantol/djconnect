"""Original RAM-only paired context continuations; never issuer admission.

A short submit guard is separate from the registered row's original authority.
Opaque retained tombstones cannot renew a purpose or refund an attempt budget.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import math
import secrets
import weakref

from .surface_push_contract import require, SurfacePushError
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
        require(self._contexts.get(h.handle) is h and not self.service.closed,
            'surface_context_unknown', 409)
        require(not h.closed, 'surface_context_expired' if h.closed == 'expired'
            else 'surface_context_unknown', 409)
        now, mono = self.wall(), self.monotonic()
        if (type(now) is not int or not math.isfinite(mono) or now < h.last_wall
                or mono < h.last_mono or now >= h.deadline or mono >= h.mono_deadline):
            self._retire(h, 'expired')
            raise SurfacePushError('surface_context_expired', 409)
        h.last_wall, h.last_mono = now, mono
        try:
            h.admission.validate()
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
        # No unauthenticated UUID may consume retained capacity. This real paired
        # check is synchronous; original clocks still precede every async await.
        self.service.preauthorize_context(payload, headers)
        operation = payload['operation_id']
        wall, mono = self.wall(), self.monotonic()
        created = operation_created_ms(operation)
        require(type(wall) is int and math.isfinite(mono) and created <= wall + FUTURE_SKEW_MS
            and wall < created + LIFETIME_MS, 'surface_context_expired', 409)
        require(operation not in self._pending and len(self._pending) < MAX_PENDING,
            'surface_context_capacity', 503)
        session_hash = hashlib.sha256(payload['session_id'].encode()).hexdigest()
        device_hash = hashlib.sha256(payload['device_id'].encode()).hexdigest()
        identity = (session_hash, device_hash, payload['client_type'])
        original_start = self._starts.get(operation)
        new_start = original_start is None
        if new_start:
            require(len(self._starts) < MAX_CONTEXTS
                and sum(start[2][1] == device_hash for start in self._starts.values()) < MAX_DEVICE,
                'surface_context_capacity', 503)
            self._starts[operation] = (wall, mono, identity)
        else:
            require(original_start[2] == identity, 'surface_context_conflict', 409)
            wall, mono = original_start[:2]
        # Capture weak ORIGINAL map identities before the first await. Device
        # equality alone cannot authorize cancellation across Sessions/purposes.
        pending_purposes = tuple(weakref.ref(p) for key, p in
            tuple(getattr(self.service, '_purposes', {}).items())
            if key[1] == device_hash and key[3] == payload['session_id'])
        self._pending[operation] = (asyncio.current_task(), session_hash, pending_purposes)
        created_context = None
        try:
            admission = await self.service.admission(payload, headers)
            _cancelled()
            admission.validate()
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
            expiry = admission.purpose.original_expiry_ms()
            if original is None:
                require(len(self._purposes) < MAX_CONTEXTS, 'surface_context_capacity', 503)
                original = _Purpose(weakref.ref(admission.purpose), 'djcpref_' + secrets.token_urlsafe(32), expiry)
                self._purposes.append(original)
            require(original.expiry == expiry and original.attempts < MAX_PURPOSE,
                'surface_context_capacity', 503)
            deadline = min(expiry, created + LIFETIME_MS, wall + SUBMIT_MS)
            # Retain an authenticated late first attempt BEFORE checking its
            # original deadline. A slow/lost response cannot refund or reanchor it.
            h = _Context('djcctx_' + secrets.token_urlsafe(32), operation, key, original,
                admission, deadline, mono+(deadline-wall)/1000, wall, mono)
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
        return {'success': True, 'contract_version': 2, 'available': True,
            'context_handle': h.handle, 'operation_id': h.operation_id,
            'purpose_ref': h.purpose.reference, 'expires_at_ms': h.purpose.expiry,
            'context_expires_at_ms': h.deadline, 'cache_policy': 'private,no-store'}

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
            return {**result, 'contract_version': 2, 'context_handle': h.handle,
                'operation_id': h.operation_id, 'purpose_ref': h.purpose.reference}
        except asyncio.CancelledError:
            if bound:
                self._retire(h, 'withdrawn')
            raise
        finally:
            h.task = None
