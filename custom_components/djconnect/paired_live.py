"""Paired owner Broadcast adapter; never mints or accepts an HA access token."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from aiohttp import WSMsgType, web
from homeassistant.components.http import HomeAssistantView

from .api_handlers import (
    async_handle_session_broadcast_recovery_payload,
    async_handle_session_broadcast_subscribe_payload,
)
from .const import DOMAIN
from .profile_context import async_resolve_device_bound_request_context
from .request_auth import authorize_runtime_device_request, resolve_runtime, runtime_matches_device

from .paired_live_contract import (
    PAIRED_LIVE_PATH,
    PAIRED_LIVE_VERSION,
    AUTH_TIMEOUT_SECONDS,
    LEASE_SECONDS,
    RECHECK_SECONDS,
    COMMANDS,
)


class DJConnectPairedLiveView(HomeAssistantView):
    """Expose only paired owner subscribe/recover with server-owned identity."""

    url = PAIRED_LIVE_PATH
    name = "api:djconnect:paired-live"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        # Credentials and private identifiers are never accepted in a URL.
        if request.query_string:
            return self.json({"success": False, "error": "query_not_allowed"}, status_code=400)
        ws = web.WebSocketResponse(max_msg_size=16384, heartbeat=30)
        await ws.prepare(request)
        cleanup = None
        try:
            await ws.send_json({"type": "auth_required", "protocol_version": PAIRED_LIVE_VERSION})
            try:
                message = await asyncio.wait_for(ws.receive(), AUTH_TIMEOUT_SECONDS)
                frame = message.json() if message.type == WSMsgType.TEXT else None
            except (TimeoutError, ValueError, TypeError):
                frame = None
            if (
                not isinstance(frame, dict)
                or set(frame)
                != {"type", "protocol_version", "device_id", "client_type", "device_token"}
                or frame.get("type") != "auth"
                or type(frame.get("protocol_version")) is not int
                or frame.get("protocol_version") != PAIRED_LIVE_VERSION
            ):
                await ws.send_json({"type": "auth_invalid", "code": "invalid_auth"})
                return ws
            identity = {key: frame[key] for key in ("device_id", "client_type")}
            if any(
                not isinstance(value, str) or not value for value in identity.values()
            ) or identity["client_type"] not in {"ios", "macos", "watchos"}:
                await ws.send_json({"type": "auth_invalid", "code": "invalid_identity"})
                return ws
            token = frame["device_token"]
            if not isinstance(token, str) or not token:
                await ws.send_json({"type": "auth_invalid", "code": "unauthorized"})
                return ws
            headers = {
                "Authorization": "Bearer " + token,
                "X-DJConnect-Device-ID": identity["device_id"],
            }
            runtime = resolve_runtime(self.hass, identity["device_id"], headers)
            if (
                runtime is None
                or not runtime_matches_device(runtime, identity["device_id"])
                or not authorize_runtime_device_request(runtime, headers, **identity)
            ):
                await ws.send_json({"type": "auth_invalid", "code": "unauthorized"})
                return ws
            try:
                context = await asyncio.wait_for(
                    async_resolve_device_bound_request_context(
                        self.hass, runtime, identity, request_source="paired_live_auth"
                    ),
                    AUTH_TIMEOUT_SECONDS,
                )
            except Exception:  # Fail closed; no private resolver details in transport.
                await ws.send_json({"type": "auth_invalid", "code": "profile_unavailable"})
                return ws
            profile_id = context.profile_id
            entry_id = runtime.entry.entry_id
            generation = getattr(runtime, "_receiver_end_generation", 0)
            deadline = asyncio.get_running_loop().time() + LEASE_SECONDS

            try:
                async with asyncio.timeout_at(deadline):

                    def immediate_authority() -> str | None:
                        if asyncio.get_running_loop().time() >= deadline:
                            return "auth_expired"
                        if self.hass.data.get(DOMAIN, {}).get(entry_id) is not runtime:
                            return "pairing_revoked"
                        if not runtime_matches_device(
                            runtime, identity["device_id"]
                        ) or not authorize_runtime_device_request(runtime, headers, **identity):
                            return "pairing_revoked"
                        if getattr(runtime, "_receiver_end_generation", 0) != generation:
                            return "pairing_revoked"
                        manager = self.hass.data.get(DOMAIN, {}).get("session_runtime_manager")
                        if (
                            manager is not None
                            and manager.receiver_entry_generation(entry_id) != generation
                        ):
                            return "pairing_revoked"
                        return None

                    async def authority() -> str | None:
                        revoked = immediate_authority()
                        if revoked:
                            return revoked
                        try:
                            current = await async_resolve_device_bound_request_context(
                                self.hass,
                                runtime,
                                identity,
                                request_source="paired_live_revalidate",
                            )
                        except Exception:
                            return "profile_unavailable"
                        return immediate_authority() or (
                            None if current.profile_id == profile_id else "profile_changed"
                        )

                    revoked = await authority()
                    if revoked:
                        await ws.send_json({"type": "auth_invalid", "code": revoked})
                        return ws
                    await ws.send_json(
                        {
                            "type": "auth_ok",
                            "protocol_version": PAIRED_LIVE_VERSION,
                            "lease_seconds": LEASE_SECONDS,
                            "audience": "active_owner_broadcast",
                            "commands": list(COMMANDS),
                        }
                    )
                    events: asyncio.Queue = asyncio.Queue(maxsize=64)
                    overflow = False

                    def publish(event):
                        nonlocal overflow
                        try:
                            events.put_nowait(event)
                        except asyncio.QueueFull:
                            overflow = True

                    # One reader task; event and authority checks continue while input is idle.
                    receive = asyncio.create_task(ws.receive())
                    try:
                        while not ws.closed:
                            revoked = await authority()
                            if revoked or overflow:
                                await ws.send_json(
                                    {"type": "auth_invalid", "code": revoked or "slow_consumer"}
                                )
                                break
                            while not events.empty():
                                event = events.get_nowait()
                                revoked = await authority()
                                if revoked or overflow:
                                    await ws.send_json(
                                        {"type": "auth_invalid", "code": revoked or "slow_consumer"}
                                    )
                                    return ws
                                await ws.send_json(
                                    {
                                        "type": "event",
                                        "event_type": "djconnect/session/broadcast",
                                        "data": event,
                                    }
                                )
                            done, _ = await asyncio.wait(
                                {receive},
                                timeout=min(
                                    RECHECK_SECONDS,
                                    max(0, deadline - asyncio.get_running_loop().time()),
                                ),
                            )
                            if not done:
                                continue
                            message = receive.result()
                            if message.type != WSMsgType.TEXT:
                                break
                            try:
                                command = message.json()
                            except (ValueError, TypeError):
                                break
                            if not isinstance(command, dict):
                                break
                            command_id = command.get("id")
                            kind = command.get("type")
                            allowed = {"id", "type", "session_id"}
                            if kind == "djconnect/session/broadcast/recover":
                                allowed.add("recovery_cursor")
                            error = None
                            if type(command_id) is not int or command_id < 1:
                                break
                            if not isinstance(kind, str) or kind not in COMMANDS:
                                error = "unsupported_command"
                            elif set(command) - allowed:
                                error = "invalid_command"
                            elif cleanup is not None:
                                error = "already_subscribed"
                            elif (
                                not isinstance(command.get("session_id"), str)
                                or not command["session_id"]
                            ):
                                error = "session_id_required"
                            elif kind.endswith("/recover") and not isinstance(
                                command.get("recovery_cursor"), str
                            ):
                                error = "recovery_cursor_required"
                            if error:
                                await ws.send_json(
                                    {
                                        "id": command_id,
                                        "type": "result",
                                        "success": False,
                                        "error": {"code": error},
                                    }
                                )
                            else:
                                payload = {
                                    **identity,
                                    **{
                                        key: command[key]
                                        for key in ("session_id", "recovery_cursor")
                                        if key in command
                                    },
                                }
                                handler = (
                                    async_handle_session_broadcast_recovery_payload
                                    if kind.endswith("/recover")
                                    else async_handle_session_broadcast_subscribe_payload
                                )
                                result, status, activate, pending_cleanup = await handler(
                                    self.hass, payload, callback=publish, headers=headers
                                )
                                cleanup = pending_cleanup
                                revoked = await authority()
                                if revoked or overflow:
                                    await ws.send_json(
                                        {"type": "auth_invalid", "code": revoked or "slow_consumer"}
                                    )
                                    break
                                await ws.send_json(
                                    {
                                        "id": command_id,
                                        "type": "result",
                                        "success": 200 <= status < 300,
                                        **(
                                            {"result": result}
                                            if 200 <= status < 300
                                            else {
                                                "error": {
                                                    "code": result.get("error", "request_failed")
                                                }
                                            }
                                        ),
                                    }
                                )
                                if activate:
                                    await activate()
                            receive = asyncio.create_task(ws.receive())
                    finally:
                        receive.cancel()
                        with suppress(asyncio.CancelledError):
                            await receive
            except TimeoutError:
                with suppress(TimeoutError, ConnectionError):
                    await asyncio.wait_for(
                        ws.send_json({"type": "auth_invalid", "code": "auth_expired"}), 1
                    )
        finally:
            try:
                if cleanup:
                    await cleanup()
            finally:
                with suppress(TimeoutError, ConnectionError):
                    await asyncio.wait_for(ws.close(), 1)
        return ws
