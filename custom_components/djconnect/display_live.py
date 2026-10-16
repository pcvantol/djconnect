"""One bounded writer per B principal over the existing Runtime/Broadcast owner."""
from __future__ import annotations

import asyncio
from contextlib import suppress
import json
import re

from aiohttp import WSMsgType, web
from homeassistant.components.http import HomeAssistantView

from .display_admission import DisplayAdmissionError
from .display_origin import selected_ha_origin
from .display_projection import shared_snapshot, projection_release_guard, MAX_FRAME_BYTES
from .display_transport import SECURITY_HEADERS, _object, _invalid_constant
from .display_service import DisplayAdmissionService


from .display_delivery import display_live_hub

ADMISSION_TIMEOUT_SECONDS = 5


class _Connection:
    def __init__(self, hass, hub, display, active, origin, ws, request):
        self.hass, self.hub, self.display, self.active = hass, hub, display, active
        self.origin, self.ws, self.request = origin, ws, request
        self.epoch = hub.manager._display_admission.issuer_epoch
        self.generation = display.connection_generation
        self.dirty = asyncio.Event()
        self.dirty.set()
        self.closed = False
        self.writer = None
        self.key = display.display_id + ":" + str(self.generation)

    def invalidate(self):
        self.closed = True
        self.dirty.set()
        if self.writer is not None:
            self.writer.cancel()
        # Revoke/end can occur while send_str awaits drain. Stop the transport
        # synchronously; bytes already delivered cannot be recalled.
        if self.request.transport is not None:
            self.request.transport.close()

    def current(self):
        state = self.hub.manager._display_admission
        display = self.display
        share = state._shares.get(display.share_id)
        current_active = self.hub.manager.current_active(display.owner.profile_id)
        return (not self.closed and display.owner.valid() and selected_ha_origin(self.hass) == self.origin
            and state.issuer_epoch == self.epoch and state._displays.get(display.display_id) is display
            and display.connection_generation == self.generation and display.owner.valid()
            and share is not None and share.owner.valid() and share.deadline > state._clock()
            and display.lease_deadline > state._clock()
            and current_active is not None and current_active.session_id == self.active.session_id
            and current_active.broadcast is self.active.broadcast)

    async def run(self):
        revision = None
        while self.current():
            try:
                # The same writer checks expiry/withdrawal while idle. No separate
                # poller, per-event task, catch-up frame or auto lease renewal.
                remaining = self.display.lease_deadline - self.hub.manager._display_admission._clock()
                await asyncio.wait_for(self.dirty.wait(), min(1, max(0, remaining)))
            except TimeoutError:
                pass
            self.dirty.clear()
            if not self.current():
                break
            hub = self.hub
            # Reserve before projection/serialization. One complete frame plus
            # preparation <=256KiB/display, <=4MiB globally; no queued content.
            try:
                release = hub.reserve_projection(self.display.display_id)
            except DisplayAdmissionError:
                await self.ws.close(code=1013, message=b"display_capacity")
                return
            try:
                async with hub.manager._lock:
                    if not self.current():
                        break
                    snapshot = shared_snapshot(self.active, self.display, hub.manager._display_admission)
                    content_current = projection_release_guard(self.active, self.display,
                        hub.manager._display_admission, snapshot)
                if snapshot["projection_revision"] == revision:
                    continue
                frame = json.dumps({"type": "snapshot", "contract_version": 1,
                    "connection_generation": self.generation, "snapshot": snapshot},
                    ensure_ascii=False, allow_nan=False)
                if len(frame.encode()) > MAX_FRAME_BYTES:
                    await self.ws.close(code=1013, message=b"display_capacity")
                    return
                if not self.current():
                    break
                if not content_current():
                    self.dirty.set()
                    continue
                # No preparation await between this current fence and actual
                # send. Revocation cancels this writer if drain later blocks.
                async with asyncio.timeout(5):
                    await self.ws.send_str(frame)
                revision = snapshot["projection_revision"]
            except (TimeoutError, DisplayAdmissionError):
                await self.ws.close(code=1013, message=b"display_unavailable")
                return
            finally:
                # Drop both representations before releasing their byte budget.
                snapshot = frame = None
                release()
        await self.ws.close(code=1008, message=b"display_grant_invalid")


class DisplayLiveView(HomeAssistantView):
    url = "/api/djconnect/v1/display/live"
    name = "api:djconnect:display:live"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        from .session_runtime import session_runtime_manager
        manager = session_runtime_manager(self.hass)
        hub = display_live_hub(manager)
        origin = selected_ha_origin(self.hass)
        if (request.query_string or not request.secure or origin is None
                or tuple(request.headers.getall("Origin", [])) != (origin,)):
            return web.json_response({"success": False, "error": "display_origin_denied"},
                                     status=403, headers=SECURITY_HEADERS)
        peer = request.transport.get_extra_info("peername") if request.transport else None
        source = str(peer[0])[:128] if isinstance(peer, tuple) and peer else "unknown"
        try:
            hub.reserve_preauth(source)
        except DisplayAdmissionError as error:
            return web.json_response({"success": False, "error": error.code},
                                     status=error.status, headers=SECURITY_HEADERS)
        ws = web.WebSocketResponse(max_msg_size=4096, heartbeat=20, compress=False)
        ws.headers.update(SECURITY_HEADERS)
        connection = None
        reserved = True
        admission_deadline = asyncio.get_running_loop().time() + ADMISSION_TIMEOUT_SECONDS
        try:
            async with asyncio.timeout_at(admission_deadline):
                await ws.prepare(request)
                message = await ws.receive()
                if message.type != WSMsgType.TEXT or len(message.data.encode()) > 4096:
                    raise DisplayAdmissionError("display_grant_invalid", 401)
                try:
                    frame = json.loads(message.data, object_pairs_hook=_object, parse_constant=_invalid_constant)
                except (ValueError, RecursionError):
                    raise DisplayAdmissionError("display_code_invalid", 400) from None
                if (not isinstance(frame, dict) or set(frame) != {"type", "contract_version", "grant_token",
                        "issuer_epoch", "display_id", "connection_nonce"}
                        or frame.get("type") != "authenticate" or type(frame.get("contract_version")) is not int
                        or frame["contract_version"] != 1 or any(not isinstance(frame[key], str)
                            or re.fullmatch(r"[A-Za-z0-9_-]{43}", frame[key]) is None
                            for key in ("issuer_epoch", "display_id", "connection_nonce"))):
                    raise DisplayAdmissionError("display_code_invalid", 400)
                async with manager._lock:
                    current_origin = selected_ha_origin(self.hass)
                    if current_origin != origin:
                        raise DisplayAdmissionError("display_context_changed", 409)
                    DisplayAdmissionService(self.hass, manager)._sync_origin(current_origin)
                    state = manager._display_admission
                    if state.selected_origin != origin:
                        raise DisplayAdmissionError("display_context_changed", 409)
                    display = state.authorize(token=frame["grant_token"], display_id=frame["display_id"],
                                              issuer_epoch=frame["issuer_epoch"])
                    active = manager.current_active(display.owner.profile_id)
                    if active is None:
                        raise DisplayAdmissionError("display_grant_invalid", 401)
                    previous = hub.connections.get(display.display_id)
                    if previous is not None:
                        previous.invalidate()
                        previous.active.broadcast.unregister_display_invalidation(previous.key)
                    display.connection_generation += 1
                    connection = _Connection(self.hass, hub, display, active, origin, ws, request)
                    hub.connections[display.display_id] = connection
                    display.invalidated = connection.invalidate
                    active.broadcast.register_display_invalidation(connection.key, connection.dirty.set)
            # No plaintext grant is retained by the connection/writer.
            frame.clear()
            message = None
            hub.release_preauth(source)
            reserved = False
            connection.writer = asyncio.create_task(connection.run())
            async for message in ws:
                if message.type in {WSMsgType.TEXT, WSMsgType.BINARY}:
                    await ws.close(code=1008, message=b"display_read_only")
                    break
        except (TimeoutError, DisplayAdmissionError):
            # No unbounded close handshake may retain an unauthenticated slot.
            if ws.prepared:
                with suppress(TimeoutError, ConnectionError):
                    async with asyncio.timeout_at(admission_deadline):
                        await ws.close(code=1008, message=b"display_grant_invalid")
            if request.transport is not None:
                request.transport.close()
        finally:
            if reserved:
                hub.release_preauth(source)
                if request.transport is not None:
                    request.transport.close()
            if connection is not None:
                connection.closed = True
                if connection.writer is not None:
                    connection.writer.cancel()
                    with suppress(asyncio.CancelledError, ConnectionError):
                        await connection.writer
                connection.active.broadcast.unregister_display_invalidation(connection.key)
                if hub.connections.get(connection.display.display_id) is connection:
                    hub.connections.pop(connection.display.display_id, None)
                    connection.display.invalidated = None
        return ws
