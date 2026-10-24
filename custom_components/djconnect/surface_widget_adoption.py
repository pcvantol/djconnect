"""Widget-only original issuer -> HA service join; no enrolled owner at startup.

All credentials remain RAM-only. This module neither supplies a concrete signer
nor calls operator enrollment. A separately qualified owner must attest the exact
original service capture; ordinary pairing and hash equality do not grant it.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import math

from .surface_issuer_lifecycle import IssuerLifecycle
from .surface_issuer_owner import WidgetIssuerOwner
from .surface_push_contract import require
from .surface_push_purpose import SurfacePurposeCredential
from .surface_push_wire import safe_integer

MAX_HANDLES = 64
MAX_OWNER_HANDLES = 16
MAX_PENDING = 8


def _cancelled():
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise asyncio.CancelledError


@dataclass(frozen=True, repr=False)
class WidgetServiceCapture:
    service: object
    manager: object
    storage: object
    runtime: object
    active: object
    broadcast: object
    session_id: str
    owner_binding: str
    device_binding: str
    entry_id: str
    storage_revision: object
    entry_revision: object
    source_current: object = field(repr=False)
    identity: dict = field(repr=False)
    headers: dict = field(repr=False)


@dataclass(eq=False, repr=False)
class _Adoption:
    capture: WidgetServiceCapture | None
    key: tuple[str, str, str]
    lifecycle: IssuerLifecycle
    operation_id: str
    wall: int
    mono: float
    last_wall: int
    last_mono: float
    task: object = field(default=None, repr=False)
    authority: object = None
    issuer_handle: object = None
    purpose: object = field(default=None, repr=False)
    closed: bool = False
    consumed: bool = False
    adopted: bool = False


class WidgetPurposeAdoptions:
    def __init__(self, service, persistence):
        self.service, self.persistence = service, persistence
        self._handles = set()  # Retained identities: no eviction/reissue repair.
        self._latest = {}
        self._lifecycle = None

    @staticmethod
    def _key(handle):
        return handle.key

    def _retained(self, handle):
        require(type(handle) is _Adoption and handle in self._handles,
            'surface_widget_original_capture_required', 503)
        return handle

    def fence(self, handle):
        h = self._retained(handle)
        was_closed = h.closed
        h.closed = True  # Before lifecycle, map, watch cleanup or any await.
        purpose = h.purpose
        if purpose is not None:
            self.service.contexts.invalidate(purpose=purpose)
        # Replay metadata must not retain a withdrawn Session, Broadcast, paired
        # request headers, Runtime/source closure or PairedAuthority. Historical
        # issuer management uses its separate original opaque capture only.
        h.capture, h.authority, h.purpose = None, None, None
        task, h.task = h.task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
        if purpose is not None:
            purpose.withdraw()
        if was_closed and purpose is None:
            return  # Idempotent cleanup still scrubbed any late authority/task.
        if h.issuer_handle is not None:
            h.lifecycle.fence(h.issuer_handle)
        for key, original_purpose in tuple(self.service._purposes.items()):
            if original_purpose is purpose and purpose is not None:
                self.service._purposes.pop(key, None)
        for row in self.service.registry._entries.values():
            if row.admission.purpose is purpose and purpose is not None:
                row.phase, row.read_secret = 'withdrawn', ''
        self.service.collect_signals()

    def invalidate(self, owner=None, session_id=None):
        for h in tuple(self._handles):
            if owner is None or (h.key[0] == owner
                    and h.key[2] == hashlib.sha256(session_id.encode()).hexdigest()):
                self.fence(h)

    def _check(self, h):
        """Synchronous latched original checks, including every issuer await."""
        from .const import DOMAIN
        from .domain.storage import STORE_KEY
        try:
            _cancelled()
            self._retained(h)
            c, service = h.capture, self.service
            data = service.hass.data.get(DOMAIN, {})
            require(not h.closed and not service.closed and c.service is service
                and data.get('surface_push_service') is service
                and data.get('session_runtime_manager') is c.manager
                and service.manager is c.manager and data.get(STORE_KEY) is c.storage
                and c.storage.authority_revision == c.storage_revision
                and c.runtime.entry.modified_at == c.entry_revision
                and self._latest.get(self._key(h)) is h,
                'surface_widget_owner_changed', 503)
            latest = c.manager.current_active(c.active.owner_profile_id)
            require(latest is not None and latest.session_id == c.session_id
                and latest.broadcast is c.broadcast and latest.runtime_state.value == 'active'
                and c.source_current(), 'surface_widget_owner_changed', 503)
            # Exact original runtime/pairing/owner/source revisions are checked by
            # PairedAuthority as well; Runtime value replacement in a Broadcast
            # is not a replacement of the paired runtime entry.
            from .request_auth import resolve_runtime, authorize_runtime_device_request
            require(resolve_runtime(service.hass, c.identity['device_id'], c.headers) is c.runtime
                and authorize_runtime_device_request(c.runtime, c.headers, **c.identity),
                'surface_widget_owner_changed', 503)
            now, mono = h.lifecycle.wall(), h.lifecycle.monotonic()
            require(safe_integer(now, 1) and type(mono) in (int, float) and math.isfinite(mono)
                and now >= h.last_wall and mono >= h.last_mono,
                'surface_widget_clock_invalid', 503)
            h.last_wall, h.last_mono = now, mono
            require(h.adopted or (now < h.wall + 120000 and mono < h.mono + 120),
                'surface_widget_capture_expired', 503)
            if h.authority is not None:
                h.authority.validate_now()
                require((h.authority.owner, h.authority.device) ==
                    (c.owner_binding, c.device_binding), 'surface_widget_owner_changed', 503)
            if h.issuer_handle is not None:
                original = h.issuer_handle.capture
                original.comparisons()  # Explicit widget-only immutable policy.
                require(h.authority is not None and
                    (original.owner_binding, original.device_binding, original.binding_id) ==
                    (c.owner_binding, c.device_binding, h.authority.binding),
                    'surface_widget_scope_mismatch', 503)
                require(h.lifecycle.owner.validate_widget_adoption(original, c) is None,
                    'surface_widget_owner_unavailable', 503)
            _cancelled()
        except BaseException:
            self.fence(h)
            raise

    def begin(self, lifecycle, operation_id, identity, headers):
        """Internal only; capture and latch BEFORE caller scheduling/first await."""
        from .const import DOMAIN
        from .domain.storage import STORE_KEY
        from .request_auth import resolve_runtime, authorize_runtime_device_request
        from .forecast_imagery import artist_authority
        _cancelled()
        require(type(lifecycle) is IssuerLifecycle and isinstance(lifecycle.owner, WidgetIssuerOwner)
            and lifecycle.journal.store.adapter.persistence is self.persistence
            and (self._lifecycle is None or self._lifecycle is lifecycle),
            'surface_widget_owner_unavailable', 503)
        require(type(identity) is dict and set(identity) == {'device_id', 'client_type'}
            and type(identity['device_id']) is str and identity['client_type'] in {'ios', 'macos', 'watchos'}
            and type(headers) is dict, 'surface_widget_owner_unavailable', 503)
        service = self.service
        data = service.hass.data.get(DOMAIN, {})
        storage = data.get(STORE_KEY)
        runtime = resolve_runtime(service.hass, identity['device_id'], headers)
        require(not service.closed and storage is not None and runtime is not None
            and authorize_runtime_device_request(runtime, headers, **identity),
            'surface_widget_owner_unavailable', 503)
        profile = storage.resolver().resolve_bound_device(identity['device_id'])
        active = service.manager.current_active(profile.profile_id)
        require(active is not None, 'surface_widget_owner_unavailable', 503)
        owner = hashlib.sha256(profile.profile_id.encode()).hexdigest()
        device = hashlib.sha256(identity['device_id'].encode()).hexdigest()
        require(len(self._handles) < MAX_HANDLES
            and sum(not h.closed and not h.adopted for h in self._handles) < MAX_PENDING
            and sum(h.key[0] == owner for h in self._handles) < MAX_OWNER_HANDLES,
            'surface_widget_capacity', 503)
        c = WidgetServiceCapture(service, service.manager, storage, runtime, active, active.broadcast,
            active.session_id, owner, device, runtime.entry.entry_id, storage.authority_revision,
            runtime.entry.modified_at, artist_authority(service.hass, runtime, owner_profile_id=profile.profile_id,
                expected_source=service.manager._history_source_contexts.get(active.session_id, {})),
            dict(identity), dict(headers))
        now, mono = lifecycle.wall(), lifecycle.monotonic()
        require(safe_integer(now, 1) and type(mono) in (int, float) and math.isfinite(mono),
            'surface_widget_clock_invalid', 503)
        h = _Adoption(c, (owner, device, hashlib.sha256(active.session_id.encode()).hexdigest()),
            lifecycle, operation_id, now, mono, now, mono)
        previous = self._latest.get(self._key(h))
        if previous is not None:
            self.fence(previous)  # New original intent cannot be overtaken by old late ACK.
        self._handles.add(h)
        self._latest[self._key(h)] = h
        self._lifecycle = lifecycle
        self._check(h)
        return h

    async def acquire(self, handle):
        from .hybrid_service import PairedAuthority
        h = self._retained(handle)
        try:
            self._check(h)
            if h.adopted:
                require(type(h.purpose) is SurfacePurposeCredential and h.purpose.is_current(),
                    'surface_widget_purpose_withdrawn', 503)
                return h.purpose  # Same original object/budgets/expiry; zero RPC.
            require(not h.consumed, 'surface_widget_capture_consumed', 503)
            h.consumed = True
            h.task = asyncio.current_task()
            c = h.capture
            authority = await PairedAuthority.resolve(self.service.hass, c.identity, c.headers)
            self._check(h)  # Never attach a late paired response to a retired handle.
            h.authority = authority
            del authority
            self._check(h)
            h.issuer_handle = h.lifecycle.begin(h.operation_id, local_guard=lambda: self._check(h))
            self._check(h)
            purpose = await h.lifecycle.acquire(h.issuer_handle)
            h.purpose = purpose
            self._check(h)
            # No await between original provenance/deadline/cancel checks and CAS.
            require(type(purpose) is SurfacePurposeCredential
                and h.lifecycle._retained(h.issuer_handle).purpose is purpose
                and purpose.is_current(), 'surface_widget_purpose_unavailable', 503)
            policy = json.loads(purpose.policy_json)
            require(policy['token_role'] == 'widget' and policy['activity_profile'] is None
                and policy['external_content_allowed'] is False,
                'surface_widget_scope_mismatch', 503)
            _cancelled()
            self.service._purposes[(c.owner_binding, c.device_binding, h.authority.binding, c.session_id)] = purpose
            h.adopted = True
            return purpose
        except BaseException:
            self.fence(h)
            raise
        finally:
            h.task = None
