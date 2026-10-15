"""Paired transport authority and one bounded operation owner over existing services."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from contextvars import ContextVar
import hashlib
import json
import re
import time

from .const import DOMAIN
from .transport_operations import OperationError, OperationJournal
from .transport_delivery import (
    capture_delivery_admissions,
    register_delivery_admission,
    OwnerDeliveryResult,
)

ACTION_OPERATIONS = frozenset(
    {"command", "ask_dj/message", "track_insight", "session/mood", "session/presence"}
)
HTTP_OPERATIONS = ACTION_OPERATIONS | {"session/start", "session/end"}
READ_OPERATIONS = frozenset(
    {
        "session/active",
        "session/broadcast/snapshot",
        "session/broadcast/recover",
        "session/forecast",
    }
)
# No arbitrary HA service, device firmware, administrative or retired-client action.
COMMANDS = frozenset(
    {
        "devices",
        "set_output",
        "queue",
        "playlists",
        "search_playlists",
        "search_tracks",
        "search_albums",
        "search_media",
        "status",
        "play",
        "play_uris",
        "pause",
        "next",
        "previous",
        "set_volume",
        "volume_delta",
        "save_current_track",
        "set_current_track_favorite",
        "toggle_current_track_favorite",
        "recently_played",
        "artist_recommendations",
        "listening_profile",
        "set_shuffle",
        "set_repeat",
        "seek_relative",
        "ask_dj_play_recommendation",
        "ask_dj_play_recommendation_on_output",
        "ask_dj_play_request_on_output",
        "ask_dj_followup_response",
        "ask_dj_message",
    }
)
_current_operation: ContextVar = ContextVar("djconnect_transport_operation", default=None)


def digest(value):
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    except (ValueError, TypeError):
        raise OperationError("invalid_request", 400) from None
    if len(raw) > 60_000:
        raise OperationError("request_too_large", 413)
    return hashlib.sha256(raw).hexdigest()


class PairedAuthority:
    """Resolved server binding; never accepts a client-selected Profile or account."""

    def __init__(self, hass, identity, headers, runtime, context, binding):
        self.hass, self.identity, self.headers = hass, identity, headers
        self.runtime, self.context, self.binding = runtime, context, binding
        self.transport_guard = None
        self.transport_guard_now = None
        self.owner = hashlib.sha256(context.profile_id.encode()).hexdigest()
        self.device = hashlib.sha256(identity["device_id"].encode()).hexdigest()

    @classmethod
    async def resolve(cls, hass, identity, headers):
        from .request_auth import (
            resolve_runtime,
            authorize_runtime_device_request,
            runtime_matches_device,
        )
        from .profile_context import async_resolve_device_bound_request_context
        from .session_conversation import async_history_grant_revision
        from .ask_dj.dialogue import source_scope

        if (
            not isinstance(identity, dict)
            or set(identity) != {"device_id", "client_type"}
            or not isinstance(identity.get("client_type"), str)
            or identity.get("client_type") not in {"ios", "macos", "watchos"}
            or not isinstance(identity.get("device_id"), str)
        ):
            raise OperationError("invalid_identity", 400)
        runtime = resolve_runtime(hass, identity["device_id"], headers)
        if (
            runtime is None
            or not runtime_matches_device(runtime, identity["device_id"])
            or not authorize_runtime_device_request(runtime, headers, **identity)
        ):
            raise OperationError("unauthorized", 401)
        try:
            context = await async_resolve_device_bound_request_context(
                hass, runtime, identity, request_source="hybrid_transport"
            )
            grant = await async_history_grant_revision(hass, context.profile_id)
        except Exception:
            raise OperationError("profile_unavailable", 403) from None
        entry_id = runtime.entry.entry_id
        if hass.data.get(DOMAIN, {}).get(entry_id) is not runtime:
            raise OperationError("pairing_revoked", 401)
        manager = hass.data.get(DOMAIN, {}).get("session_runtime_manager")
        generation = getattr(runtime, "_receiver_end_generation", 0)
        if manager and manager.receiver_entry_generation(entry_id) != generation:
            raise OperationError("pairing_revoked", 401)
        binding = digest(
            {
                "device": identity,
                "entry": entry_id,
                "generation": generation,
                "pairing": hashlib.sha256(
                    str(getattr(runtime, "device_token", "")).encode()
                ).hexdigest(),
                "profile": context.profile_id,
                "source": source_scope(context.profile),
                "backend": context.backend_id,
                "account": context.music_account_id,
                "privacy": str(context.privacy_mode),
                "grant": grant,
            }
        )
        return cls(hass, dict(identity), dict(headers), runtime, context, binding)

    async def validate(self):
        current = await self.resolve(self.hass, self.identity, self.headers)
        if current.runtime is not self.runtime or current.binding != self.binding:
            raise OperationError("operation_context_changed", 403)
        if self.transport_guard is not None:
            await self.transport_guard()
        self.validate_now()

    def validate_now(self):
        if self.transport_guard_now is not None:
            self.transport_guard_now()

    def payload(self, value):
        if not isinstance(value, dict):
            raise OperationError("invalid_request", 400)
        forbidden = (
            "device_token",
            "authorization",
            "ha_user_id",
            "user_id",
            "_ha_service_runtime",
        )
        sources = [value]
        if "identity" in value:
            sources.append(value["identity"])
        if value.get("command") == "ask_dj_message" and isinstance(value.get("value"), dict):
            # The existing compatibility adapter flattens this command value
            # into the shared Ask DJ request. Fence that exact normalization.
            sources.append(value["value"])
        for source in sources:
            if not isinstance(source, dict):
                raise OperationError("invalid_identity", 400)
            if any(key in source for key in forbidden):
                raise OperationError("invalid_request", 400)
            for key, expected in {
                **self.identity,
                "profile_id": self.context.profile_id,
                "explicit_profile_id": self.context.profile_id,
            }.items():
                if key in source and source[key] != expected:
                    raise OperationError("profile_device_mismatch", 403)
        return {**value, **self.identity}


async def invoke(hass, authority, operation, payload):
    """Closed normalization only; all domain behavior stays in its existing owner."""
    from . import api_handlers

    if operation == "command":
        if not isinstance(payload.get("command"), str) or payload["command"] not in COMMANDS:
            raise OperationError("unsupported_command", 400)
        handler = api_handlers.async_handle_command_payload
    else:
        handler = {
            "ask_dj/message": api_handlers.async_handle_ask_dj_message_payload,
            "track_insight": api_handlers.async_handle_track_insight_payload,
            "session/start": api_handlers.async_handle_session_start_payload,
            "session/end": api_handlers.async_handle_session_end_payload,
            "session/active": api_handlers.async_handle_active_session_payload,
            "session/broadcast/snapshot": api_handlers.async_handle_session_broadcast_snapshot_payload,
            "session/broadcast/recover": api_handlers.async_handle_session_broadcast_recovery_read_payload,
        }.get(operation)
    if handler is not None:
        result = await handler(hass, payload, headers=authority.headers)
        if operation == "command":
            # Reuse the existing synchronous paired/Profile/source owner fence.
            # This bounds in-flight snapshots, without refreshing a command or
            # reconstructing source/artwork rights in the transport layer.
            manager = hass.data.get(DOMAIN, {}).get("session_runtime_manager")
            active = manager.current_active(authority.context.profile_id) if manager else None
            captured_session = active.session_id if active else None
            captured_item = active.broadcast.state.playback.item_id if active else None
            deadline = time.monotonic() + 5

            def command_delivery():
                api_handlers._conversation_profile_fence(
                    hass,
                    authority.runtime,
                    authority.identity,
                    authority.headers,
                    authority.context,
                )
                current_manager = hass.data.get(DOMAIN, {}).get("session_runtime_manager")
                current = (
                    current_manager.current_active(authority.context.profile_id)
                    if current_manager
                    else None
                )
                if (
                    time.monotonic() >= deadline
                    or current_manager is not manager
                    or (current.session_id if current else None) != captured_session
                    or (current.broadcast.state.playback.item_id if current else None)
                    != captured_item
                ):
                    raise OperationError("command_result_withdrawn", 409)

            register_delivery_admission(command_delivery)
        return result
    if operation in {"session/mood", "session/presence"}:
        from .session_mood import async_handle_owner_setting

        return await async_handle_owner_setting(
            hass, payload, headers=authority.headers, setting=operation.split("/")[1]
        )
    if operation == "session/forecast":
        from .session_forecast_transport import async_handle_forecast

        return await async_handle_forecast(hass, payload, headers=authority.headers)
    raise OperationError("unsupported_operation", 400)


class HybridOperations:
    """One Store journal and bounded task owner shared by HTTP and paired WS."""

    def __init__(self, hass, store):
        self.hass = hass
        self.journal = OperationJournal(store)
        self.tasks = {}
        self._closed = False
        self._unsubscribe_stop = None
        self._sweep_task = asyncio.create_task(self._sweep())

    async def _sweep(self):
        try:
            while True:
                await asyncio.sleep(30)
                await self.journal.collect_expired()
        except (asyncio.CancelledError, OperationError):
            return

    async def close(self, _event=None):
        self._closed = True
        if self._unsubscribe_stop is not None:
            remove, self._unsubscribe_stop = self._unsubscribe_stop, None
            remove()
        self._sweep_task.cancel()
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(self._sweep_task, *tuple(self.tasks.values()), return_exceptions=True)

    def _require_open(self):
        if self._closed:
            raise OperationError("operation_unavailable", 503)

    async def context(self, authority):
        from .const import CONF_HA_INSTALL_ID

        self._require_open()
        await authority.validate()
        async with self.journal._lock:
            await self.journal._load()
            clock = self.journal.now_ms()
        install_id = authority.runtime.config.get(CONF_HA_INSTALL_ID)
        if not isinstance(install_id, str) or not install_id:
            raise OperationError("installation_identity_unavailable", 409)
        return {
            "success": True,
            "contract_version": 1,
            "ha_install_id": install_id,
            "operation_epoch": self.journal.epoch,
            "server_time_ms": clock,
            "operation_lifetime_ms": 300_000,
            "requires_authenticated_tls": True,
            "action_operations": sorted(ACTION_OPERATIONS),
            "http_operations": sorted(HTTP_OPERATIONS),
            "read_operations": sorted(READ_OPERATIONS),
        }

    async def read(self, authority, operation, payload):
        self._require_open()
        if not isinstance(operation, str) or operation not in READ_OPERATIONS:
            raise OperationError("unsupported_read", 400)
        await authority.validate()
        result = await invoke(self.hass, authority, operation, authority.payload(payload))
        await authority.validate()
        return result

    async def status(self, authority, request):
        self._require_open()
        self._envelope(request, status=True)
        await authority.validate()
        receipt = await self.journal.status(
            owner=authority.owner,
            device=authority.device,
            binding=authority.binding,
            identifier=request["operation_id"],
            epoch=request["operation_epoch"],
        )
        await authority.validate()
        return self._status_result(receipt)

    @staticmethod
    def _envelope(request, *, status=False):
        fields = {"contract_version", "operation_id", "operation_epoch"}
        if not status:
            fields |= {"operation", "payload"}
        if (
            not isinstance(request, dict)
            or set(request) != fields
            or type(request.get("contract_version")) is not int
            or request["contract_version"] != 1
            or not isinstance(request.get("operation_epoch"), str)
        ):
            raise OperationError("invalid_request", 400)

    @staticmethod
    def _status_result(receipt):
        phase = receipt["phase"]
        result = {
            "success": phase not in {"unknown", "rejected", "cancelled"},
            "operation_receipt": receipt,
            "result_available": False,
        }
        if phase in {"accepted", "sent_unknown"}:
            return result, 202
        if phase != "confirmed":
            result["error"] = receipt.get("error") or "operation_" + phase
            return result, receipt.get("response_status") or 409
        return result, 200

    async def execute(self, authority, request, *, transport):
        self._require_open()
        self._envelope(request)
        operation = request["operation"]
        if not isinstance(operation, str) or operation not in (
            ACTION_OPERATIONS if transport == "websocket" else HTTP_OPERATIONS
        ):
            raise OperationError("unsupported_operation", 400)
        payload = authority.payload(request["payload"])
        await authority.validate()
        key, receipt, created = await self.journal.reserve(
            owner=authority.owner,
            device=authority.device,
            binding=authority.binding,
            identifier=request["operation_id"],
            epoch=request["operation_epoch"],
            operation=operation,
            digest=digest(payload),
        )
        if not created:
            await authority.validate()
            return self._status_result(receipt)
        if self._closed:
            try:
                await self.journal.transition(
                    key, "rejected", response_status=503, error="operation_unavailable"
                )
            finally:
                self.journal.release(key)
            raise OperationError("operation_unavailable", 503)
        task = asyncio.create_task(self._run(key, authority, operation, payload))
        self.tasks[key] = task

        # Retain the task even after caller/socket cancellation. Its callback consumes
        # unexpected exceptions without logging private request/response content.
        def done(future):
            self.tasks.pop(key, None)
            with suppress(asyncio.CancelledError):
                future.exception()

        task.add_done_callback(done)
        result = await asyncio.shield(task)
        await authority.validate()
        return result

    async def _run(self, key, authority, operation, payload):
        scope = [self, key, authority]
        token = _current_operation.set(scope)
        invoked = False
        try:
            await authority.validate()
            remaining = (
                self.journal._state["records"][key]["expires_ms"] - self.journal.now_ms()
            ) / 1000
            with capture_delivery_admissions() as admissions:
                async with asyncio.timeout(max(0, min(300, remaining))):
                    invoked = True
                    result, status = await invoke(self.hass, authority, operation, payload)
            successful = status < 400 and result.get("success") is not False
            code = result.get("error")
            code = (
                code
                if isinstance(code, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", code)
                else None
            )
            # Existing setting owners reject stale CAS before any write. This
            # narrow qualified error is not a generic HTTP-code assumption.
            rejected = (
                operation in {"session/mood", "session/presence"}
                and status == 409
                and code == operation.split("/")[1] + "_revision_conflict"
                and self.journal._state["records"][key]["phase"] == "accepted"
            )
            receipt = await self.journal.transition(
                key,
                "confirmed" if successful else "rejected" if rejected else "unknown",
                response_status=status,
                error=code,
            )
            await authority.validate()
            return OwnerDeliveryResult({**result, "operation_receipt": receipt}, admissions), status
        except asyncio.CancelledError:
            with suppress(OperationError):
                await self.journal.transition(key, "unknown", error="operation_unknown")
            raise
        except Exception as exc:
            code = exc.code if isinstance(exc, OperationError) else "operation_unknown"
            with suppress(OperationError):
                await self.journal.transition(
                    key,
                    "rejected" if not invoked and isinstance(exc, OperationError) else "unknown",
                    response_status=getattr(exc, "status", 503),
                    error=code,
                )
            raise OperationError(code, getattr(exc, "status", 503)) from None
        finally:
            # Detached tasks must not retain pairing headers or a live execution
            # grant through an inherited ContextVar after this operation ends.
            scope.clear()
            _current_operation.reset(token)
            self.journal.release(key)


async def guard_transport_effect():
    """Existing provider adapters call this through their established send guard."""
    current = _current_operation.get()
    if current is not None:
        if not current:
            raise OperationError("operation_context_changed", 409)
        manager, key, authority = current
        await authority.validate()
        manager.journal._validate_time(manager.journal._state["records"][key]["operation_id"])
        await manager.journal.transition(key, "sent_unknown")
        await authority.validate()
        validate_transport_effect_now()


def validate_transport_effect_now():
    """Final non-yielding fence after every Ask DJ/domain owner await."""
    current = _current_operation.get()
    if current is not None:
        if not current:
            raise OperationError("operation_context_changed", 409)
        manager, key, authority = current
        final_guard = getattr(authority, "validate_now", None)
        if final_guard is not None:
            final_guard()
        if manager.journal._failed:
            raise OperationError("operation_unavailable", 503)
        manager.journal._validate_time(manager.journal._state["records"][key]["operation_id"])


def operations(hass):
    data = hass.data.setdefault(DOMAIN, {})
    manager = data.get("hybrid_operation_manager")
    if manager is None:
        from homeassistant.helpers.storage import Store

        manager = HybridOperations(hass, Store(hass, 1, "djconnect_transport_operations"))
        data["hybrid_operation_manager"] = manager
        bus = getattr(hass, "bus", None)
        if bus is not None:
            manager._unsubscribe_stop = bus.async_listen_once("homeassistant_stop", manager.close)
    return manager
