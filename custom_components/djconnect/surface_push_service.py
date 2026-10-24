"""One HA-owned surface registry; no purpose enrolment or credential repair.

The internal widget adoption port requires a separately qualified enrolled
owner; normal startup supplies none. It is empty by default, is never read from config/Store/client JSON,
and disappears at unload/restart. HTTP cannot import a credential into it.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
import time

from .surface_push_contract import SurfacePushError, require
from .surface_push_journal import SurfaceOperationStore
from .surface_push_registry import SurfaceAdmission, SurfacePushRegistry
from .transport_operations import OperationJournal

MAX_TASKS = 8


class SurfacePushService:
    def __init__(self, hass, manager, persistence):
        self.hass, self.manager = hass, manager
        self.closed = False
        manager._surface_push_service = self
        self._purposes = {}  # Never a public client/enrolment/config ingestion route.
        from .surface_widget_adoption import WidgetPurposeAdoptions
        self._widget_adoptions = WidgetPurposeAdoptions(self, persistence)
        self._tasks = set()
        self._signals = {}
        self._unsubscribe_stop = None
        async def relay(action, request, admission):
            from .surface_push_relay import post_once
            return await post_once(hass, admission.runtime, action, request, admission)
        self.registry = SurfacePushRegistry(OperationJournal(SurfaceOperationStore(persistence)), relay)
        from .surface_push_context import SurfaceContextContinuations
        self.contexts = SurfaceContextContinuations(self, wall=self.registry.journal.now_ms, monotonic=time.monotonic)

    def begin_widget_adoption(self, lifecycle, operation_id, identity, headers):
        """Internal required-owner port; captures before caller task scheduling."""
        return self._widget_adoptions.begin(lifecycle, operation_id, identity, headers)

    async def adopt_widget(self, handle):
        return await self.run(self._widget_adoptions.acquire(handle))

    def withdraw_widget_adoption(self, handle):
        """Local irreversible fence; remote withdrawal retains its own authority."""
        self._widget_adoptions.fence(handle)

    async def run(self, coroutine):
        if self.closed or len(self._tasks) >= MAX_TASKS:
            coroutine.close()
            raise SurfacePushError("surface_unavailable", 503)
        task = self.hass.async_create_background_task(coroutine, "djconnect-surface-operation")
        self._tasks.add(task)
        try:
            return await task
        except asyncio.CancelledError:
            if self.closed:
                raise SurfacePushError("surface_unavailable", 503) from None
            raise
        finally:
            self._tasks.discard(task)

    def spawn(self, coroutine):
        """Bounded background owner, shared with foreground operation capacity."""
        if self.closed or len(self._tasks)>=MAX_TASKS:
            coroutine.close()
            return None
        task = self.hass.async_create_background_task(coroutine,"djconnect-widget-signal")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def track_registration(self, response):
        if not response.get("success"):
            return
        from .surface_push_events import WidgetSignals
        row = self.registry._entries.get((response.get("registration") or {}).get("registration_id"))
        if row is None or row.metadata["token_role"]!="widget" or row.admission.broadcast is None:
            return
        previous = self._signals.get(row.registration_id)
        if previous is not None:
            if previous.row is row and previous.current():
                return  # Replayed registration never resubscribes/rearms.
            previous.stop()
        if row.live(self.registry.journal.now_ms()):
            self._signals[row.registration_id] = WidgetSignals(self,row,row.admission.broadcast)

    def collect_signals(self):
        for key,signals in tuple(self._signals.items()):
            if not signals.current():
                signals.stop()
                self._signals.pop(key,None)

    def _context_runtime(self, payload, headers):
        from .request_auth import resolve_runtime, authorize_runtime_device_request
        identity = {key: payload[key] for key in ("device_id", "client_type")}
        runtime = resolve_runtime(self.hass, identity["device_id"], headers)
        require(runtime is not None and authorize_runtime_device_request(runtime, headers, **identity),
            "unauthorized", 401)
        return runtime

    def preauthorize_context(self, payload, headers):
        """Synchronous paired check before any bounded context reservation."""
        return self._context_runtime(payload, headers)

    async def admission(self, payload, headers):
        """Original paired/source/Session/issuer snapshot BEFORE async resolution."""
        from .const import DOMAIN
        from .domain.storage import STORE_KEY
        from .hybrid_service import PairedAuthority
        from .forecast_imagery import artist_authority
        from .passive_session import SurfaceGrant, projection
        from .surface_push_purpose import SurfacePurposeCredential
        identity = {key:payload[key] for key in ("device_id","client_type")}
        runtime = self._context_runtime(payload, headers)
        data = self.hass.data.get(DOMAIN,{})
        storage = data.get(STORE_KEY)
        require(not self.closed and data.get("surface_push_service") is self and storage is not None,
            "surface_unavailable",503)
        try:
            profile = storage.resolver().resolve_bound_device(identity["device_id"])
            active = self.manager.current_active(profile.profile_id)
        except Exception:
            raise SurfacePushError("surface_not_allowed",403) from None
        require(active is not None and active.session_id==payload["session_id"],
            "active_session_not_found",404)
        entry = runtime.entry
        original = (storage.authority_revision,entry.modified_at,active.broadcast)
        purposes = tuple(self._purposes.values())
        source_guard = artist_authority(self.hass,runtime,owner_profile_id=profile.profile_id,
            expected_source=self.manager._history_source_contexts.get(active.session_id,{}))
        authority = await PairedAuthority.resolve(self.hass,identity,headers)
        authority.validate_now()
        purpose = self._purposes.get((authority.owner,authority.device,authority.binding,active.session_id))
        require(type(purpose) is SurfacePurposeCredential and any(purpose is p for p in purposes),
            "surface_purpose_unavailable",503)
        withdrawn = False
        def current():
            nonlocal withdrawn
            try:
                latest = self.manager.current_active(profile.profile_id)
                if (withdrawn or self.closed or data.get("surface_push_service") is not self
                        or data.get("session_runtime_manager") is not self.manager
                        or data.get(STORE_KEY) is not storage
                        or storage.authority_revision!=original[0] or entry.modified_at!=original[1]
                        or latest is None or latest.session_id!=active.session_id
                        or latest.broadcast is not original[2] or latest.runtime_state.value!="active"
                        or not source_guard()
                        or self._purposes.get((authority.owner,authority.device,authority.binding,active.session_id)) is not purpose):
                    raise PermissionError
                authority.validate_now()
                return True
            except Exception:
                withdrawn = True
                purpose.withdraw()
                return False
        metadata = payload.get("consent") or {}
        grant = SurfaceGrant(purpose.capability_id,authority.binding,purpose.delegation_id,entry.entry_id,
            "widget",metadata.get("locked_display",False),current,2)
        def frame():
            latest = self.manager.current_active(profile.profile_id)
            require(current() and latest is not None,"surface_read_withdrawn",403)
            result = projection(latest,grant,registry=None,owner=profile.profile_id)
            # No ordinary image route/app bearer is exported to extensions.
            # Background images require their own exact asset-scoped route.
            result["artwork"] = []
            require(current(),"surface_read_withdrawn",403)
            return result
        result = SurfaceAdmission(authority.owner,authority.device,authority.binding,
            active.session_id,current,frame,purpose=purpose,runtime=runtime,broadcast=active.broadcast)
        result.validate()
        return result

    def invalidate_session(self, owner, session_id):
        """Latch original grants before Session teardown can yield or fail."""
        import hashlib
        owner_binding = hashlib.sha256(owner.encode()).hexdigest()
        self.contexts.invalidate(owner_binding, session_id)
        self._widget_adoptions.invalidate(owner_binding, session_id)
        for key,purpose in tuple(self._purposes.items()):
            if key[0]==owner_binding and key[3]==session_id:
                purpose.withdraw()
                self._purposes.pop(key,None)
        for row in self.registry._entries.values():
            if row.admission.owner==owner_binding and row.admission.session_id==session_id:
                row.admission.purpose.withdraw()
                row.phase,row.read_secret = "withdrawn",""

        self.collect_signals()

    def invalidate_entry(self, entry_id):
        """Entry unload conservatively withdraws all process-local surfaces.

        Do this synchronously before platform-unload awaits. A failed unload
        must not silently rearm a previously withdrawn background grant.
        """
        self.contexts.invalidate()
        self._widget_adoptions.invalidate()
        for purpose in self._purposes.values():
            purpose.withdraw()
        self._purposes.clear()
        for row in self.registry._entries.values():
            row.phase,row.read_secret = "withdrawn",""
        self.collect_signals()

    async def close(self, _event=None):
        if self.closed:
            return
        self.closed = True
        self.contexts.invalidate()
        self._widget_adoptions.invalidate()
        if getattr(self.manager,"_surface_push_service",None) is self:
            self.manager._surface_push_service = None
        if self._unsubscribe_stop is not None:
            remove,self._unsubscribe_stop = self._unsubscribe_stop,None
            if _event is None:
                remove()
        for purpose in self._purposes.values():
            purpose.withdraw()
        self._purposes.clear()
        for signals in tuple(self._signals.values()):
            signals.stop()
        self._signals.clear()
        await self.registry.close()
        tasks = tuple(task for task in self._tasks if task is not asyncio.current_task())
        for task in tasks:
            task.cancel()
        if tasks:
            with suppress(asyncio.CancelledError):
                await asyncio.gather(*tasks,return_exceptions=True)
        self._tasks.clear()


def start_surface_service(hass):
    from .const import DOMAIN
    from .persistence import persistence_service
    from .session_runtime import session_runtime_manager
    data = hass.data[DOMAIN]
    if "surface_push_service" in data:
        return
    service = SurfacePushService(hass,session_runtime_manager(hass),persistence_service(hass))
    data["surface_push_service"] = service
    service._unsubscribe_stop = hass.bus.async_listen_once("homeassistant_stop",service.close)


async def close_surface_service(hass):
    from .const import DOMAIN
    service = hass.data.get(DOMAIN,{}).pop("surface_push_service",None)
    if service is not None:
        await service.close()


def now_ms():
    return int(time.time()*1000)
