"""Qualified TLS/direct-local paired adapters; HTTP and WS share domain services."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import json
import secrets

from aiohttp import WSMsgType, web
from homeassistant.components.http import HomeAssistantView

from .hybrid_service import OperationError, PairedAuthority, operations
from .transport_delivery import OwnerDeliveryResult
from .hybrid_contract import FRAME_LIMIT, bounded_frame
from .hybrid_local_policy import same_origin, transport_security_policy
from .hybrid_ingress_qualification import read_qualification, qualify, qualification_current_now

ACTION_PATH = "/api/djconnect/v1/actions/paired"
AUTH_TIMEOUT = 5
LEASE_SECONDS = 300
RECHECK_SECONDS = 1


def response(body, status=200):
    return web.json_response(
        body, status=status, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    )


async def local_qualification(hass, peer, host, header_names):
    from homeassistant.components.network import async_get_adapters
    from homeassistant.helpers.network import NoURLAvailableError, get_url
    from .const import CONF_HA_INSTALL_ID, DOMAIN

    try:
        internal_url = get_url(hass, allow_external=False, allow_cloud=False)
    except NoURLAvailableError:
        return None
    adapters = await async_get_adapters(hass)
    install_ids = {
        runtime.config.get(CONF_HA_INSTALL_ID)
        for runtime in hass.data.get(DOMAIN, {}).values()
        if isinstance(getattr(runtime, "config", None), dict)
        and isinstance(runtime.config.get(CONF_HA_INSTALL_ID), str)
        and runtime.config.get(CONF_HA_INSTALL_ID)
    }
    snapshot = await hass.async_add_executor_job(read_qualification, hass.config.config_dir)
    return qualify(snapshot, peer, adapters, internal_url, host, header_names, install_ids)


async def request_error(hass, request):
    if request.query_string:
        return response({"success": False, "error": "query_not_allowed"}, 400)
    if not request.secure:
        peer = request.transport.get_extra_info("peername") if request.transport else None
        qualification = await local_qualification(hass, peer, request.host, tuple(request.headers))
        if qualification is None:
            return response({"success": False, "error": "transport_security_required"}, 426)
        request["djconnect_local_qualification"] = qualification
    if not same_origin(request.headers.getall("Origin", []), request.scheme, request.host):
        return response({"success": False, "error": "origin_not_allowed"}, 403)
    return None


def bind_ingress_guard(hass, authority, request):
    if request.secure:
        return
    from .const import CONF_HA_INSTALL_ID

    original = request["djconnect_local_qualification"]
    config_dir = hass.config.config_dir
    revoked = False
    peer = request.transport.get_extra_info("peername")
    host, header_names = request.host, tuple(request.headers)

    def validate_now():
        nonlocal revoked
        if revoked or not qualification_current_now(config_dir, original):
            revoked = True
            raise OperationError("transport_security_required", 426)

    async def validate():
        nonlocal revoked
        validate_now()
        current = await local_qualification(hass, peer, host, header_names)
        if (
            current is None
            or current["fingerprint"] != original["fingerprint"]
            or current["stamp"] != original["stamp"]
            or current["ha_install_id"] != authority.runtime.config.get(CONF_HA_INSTALL_ID)
        ):
            revoked = True
            raise OperationError("transport_security_required", 426)
        validate_now()

    authority.transport_guard = validate
    authority.transport_guard_now = validate_now


def transport_context(result, request):
    return {
        **result,
        "requires_authenticated_tls": bool(request.secure),
        "transport_security": {
            **transport_security_policy(),
            "mode": "authenticated_tls" if request.secure else "qualified_direct_http",
        },
    }


async def json_body(request):
    body = bytearray()
    async for chunk in request.content.iter_chunked(8192):
        body.extend(chunk)
        if len(body) > FRAME_LIMIT:
            raise OperationError("request_too_large", 413)
    try:
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, TypeError, UnicodeDecodeError):
        raise OperationError("invalid_json", 400) from None


class _HybridHTTP(HomeAssistantView):
    requires_auth = False
    action = ""

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        invalid = await request_error(self.hass, request)
        if invalid is not None:
            return invalid
        try:
            body = await json_body(request)
            identity = body.pop("identity", None)
            authority = await PairedAuthority.resolve(self.hass, identity, request.headers)
            bind_ingress_guard(self.hass, authority, request)
            manager = operations(self.hass)
            if self.action == "context":
                if body != {"contract_version": 1} or type(body.get("contract_version")) is not int:
                    raise OperationError("invalid_request", 400)
                result, status = transport_context(await manager.context(authority), request), 200
            elif self.action == "execute":
                result, status = await manager.execute(authority, body, transport="http")
            elif self.action == "status":
                result, status = await manager.status(authority, body)
            else:
                if (
                    set(body) != {"contract_version", "session_id", "recovery_cursor"}
                    or type(body.get("contract_version")) is not int
                    or body["contract_version"] != 1
                ):
                    raise OperationError("invalid_request", 400)
                result, status = await manager.read(authority, "session/broadcast/recover", body)
            await authority.validate()
            if isinstance(result, OwnerDeliveryResult):
                result = await result.admitted_body()
            await authority.validate()
            authority.validate_now()
            return response(result, status)
        except OperationError as exc:
            return response({"success": False, "error": exc.code}, exc.status)


class HybridContextView(_HybridHTTP):
    url = "/api/djconnect/v1/transport/context"
    name = "api:djconnect:hybrid-context"
    action = "context"


class HybridOperationView(_HybridHTTP):
    url = "/api/djconnect/v1/transport/operation"
    name = "api:djconnect:hybrid-operation"
    action = "execute"


class HybridOperationStatusView(_HybridHTTP):
    url = "/api/djconnect/v1/transport/operation/status"
    name = "api:djconnect:hybrid-operation-status"
    action = "status"


class HybridRecoveryView(_HybridHTTP):
    url = "/api/djconnect/v1/session/broadcast/recovery"
    name = "api:djconnect:hybrid-recovery"
    action = "recover"


class HybridActionsView(HomeAssistantView):
    url = ACTION_PATH
    name = "api:djconnect:paired-actions"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass
        self.connections = {}

    async def get(self, request):
        invalid = await request_error(self.hass, request)
        if invalid is not None:
            return invalid
        if len(self.connections) >= 16:
            return response({"success": False, "error": "connection_capacity"}, 429)
        connection_id = secrets.token_hex(16)
        self.connections[connection_id] = None
        try:
            return await self._serve(request, connection_id)
        finally:
            self.connections.pop(connection_id, None)

    async def _serve(self, request, connection_id):
        ws = web.WebSocketResponse(max_msg_size=FRAME_LIMIT, heartbeat=15)
        await ws.prepare(request)
        workers = {}
        writer = None
        reader = None
        failure = None
        authenticated = False
        remove_settings_listener = None
        try:
            auth_deadline = asyncio.get_running_loop().time() + AUTH_TIMEOUT
            await ws.send_json(
                {"type": "auth_required", "protocol_version": 1, "audience": "paired_owner_actions"}
            )
            message = await asyncio.wait_for(ws.receive(), AUTH_TIMEOUT)
            frame = message.json() if message.type == WSMsgType.TEXT else None
            if (
                not isinstance(frame, dict)
                or set(frame)
                != {
                    "type",
                    "protocol_version",
                    "audience",
                    "device_id",
                    "client_type",
                    "device_token",
                }
                or frame.get("type") != "auth"
                or type(frame.get("protocol_version")) is not int
                or frame["protocol_version"] != 1
                or frame.get("audience") != "paired_owner_actions"
                or not isinstance(frame.get("device_token"), str)
                or not frame["device_token"]
            ):
                raise OperationError("invalid_auth", 401)
            identity = {k: frame[k] for k in ("device_id", "client_type")}
            headers = {
                "Authorization": "Bearer " + frame["device_token"],
                "X-DJConnect-Device-ID": identity["device_id"],
            }
            manager = operations(self.hass)
            async with asyncio.timeout_at(auth_deadline):
                authority = await PairedAuthority.resolve(self.hass, identity, headers)
                bind_ingress_guard(self.hass, authority, request)
                if sum(device == authority.device for device in self.connections.values()) >= 2:
                    raise OperationError("connection_capacity", 429)
                self.connections[connection_id] = authority.device
                context = transport_context(await manager.context(authority), request)
            await ws.send_json(
                {
                    **context,
                    "type": "auth_ok",
                    "protocol_version": 1,
                    "audience": "paired_owner_actions",
                    "lease_seconds": LEASE_SECONDS,
                    "connection_id": connection_id,
                    "commands": [
                        "djconnect/read",
                        "djconnect/operation/execute",
                        "djconnect/operation/status",
                        'djconnect/profile/settings/update',
                        'djconnect/profile/settings/subscribe',
                    ],
                }
            )
            authenticated = True
            queue = asyncio.Queue(maxsize=64)
            overflow = False
            deadline = asyncio.get_running_loop().time() + LEASE_SECONDS

            async def send():
                while not ws.closed:
                    item = await queue.get()
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        raise OperationError("auth_expired", 401)
                    async with asyncio.timeout(min(5, remaining)):
                        await authority.validate()
                        read = item.pop("_read", None)
                        if read is not None:
                            try:
                                result, status = await manager.read(authority, *read)
                                item.update(
                                    result=result,
                                    status=status,
                                    success=status < 400 and result.get("success") is not False,
                                )
                            except OperationError as exc:
                                item.update(
                                    success=False, status=exc.status, error={"code": exc.code}
                                )
                        elif isinstance(item.get("result"), OwnerDeliveryResult):
                            item["result"] = await item["result"].admitted_body()
                        await authority.validate()
                        authority.validate_now()
                        await ws.send_str(bounded_frame(item))

            writer = asyncio.create_task(send())
            seen = set()

            def enqueue(item):
                nonlocal overflow
                try:
                    queue.put_nowait(item)
                except asyncio.QueueFull:
                    overflow = True

            async def run_command(command):
                nonlocal remove_settings_listener
                rid = command["id"]
                base = {"id": rid, "connection_id": connection_id, "type": "result"}
                try:
                    data = {k: v for k, v in command.items() if k not in {"id", "type"}}
                    if command["type"] == "djconnect/read":
                        if set(data) != {"operation", "payload"}:
                            raise OperationError("invalid_command", 400)
                        # Project through the existing read owner at actual send,
                        # rather than holding a private snapshot in a slow queue.
                        enqueue({**base, "_read": (data["operation"], data["payload"])})
                        return
                    elif command["type"] == "djconnect/operation/execute":
                        result, status = await manager.execute(
                            authority, data, transport="websocket"
                        )
                    elif command["type"] == "djconnect/operation/status":
                        result, status = await manager.status(authority, data)
                    elif command['type'] == 'djconnect/profile/settings/update':
                        if set(data) != {'payload'}:
                            raise OperationError('invalid_command', 400)
                        from .profile_settings import async_handle_settings
                        await authority.validate()
                        result, status = await async_handle_settings(self.hass, authority.payload(data['payload']),
                            headers=authority.headers, write=True, validate_ingress=authority.validate_now)
                    elif command['type'] == 'djconnect/profile/settings/subscribe':
                        if (set(data) != {'contract_version', 'enabled'}
                                or type(data['contract_version']) is not int or data['contract_version'] != 3
                                or type(data['enabled']) is not bool):
                            raise OperationError('invalid_command', 400)
                        await authority.validate()
                        if remove_settings_listener is not None:
                            remove_settings_listener()
                            remove_settings_listener = None
                        if data['enabled']:
                            from .profile_settings import CHANGE_EVENT
                            def changed(event):
                                if event.data.get('owner') == authority.owner:
                                    enqueue({'id': 0, 'connection_id': connection_id, 'type': 'event',
                                             'event': 'profile/settings/changed', 'contract_version': 3})
                            remove_settings_listener = self.hass.bus.async_listen(CHANGE_EVENT, changed)
                        result, status = {'success': True, 'subscribed': data['enabled'], 'contract_version': 3}, 200
                    else:
                        raise OperationError("unsupported_command", 400)
                    await authority.validate()
                    enqueue(
                        {
                            **base,
                            "success": status < 400 and result.get("success") is not False,
                            "status": status,
                            "result": result,
                        }
                    )
                except OperationError as exc:
                    enqueue(
                        {
                            **base,
                            "success": False,
                            "status": exc.status,
                            "error": {"code": exc.code},
                        }
                    )
                except Exception:
                    enqueue(
                        {
                            **base,
                            "success": False,
                            "status": 503,
                            "error": {"code": "operation_unavailable"},
                        }
                    )
                finally:
                    workers.pop(rid, None)

            reader = asyncio.create_task(ws.receive())
            while not ws.closed:
                await authority.validate()
                if overflow:
                    raise OperationError("slow_consumer", 429)
                if writer.done():
                    writer.result()
                    break
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise OperationError("auth_expired", 401)
                done, _ = await asyncio.wait(
                    {reader, writer},
                    timeout=min(RECHECK_SECONDS, remaining),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if writer in done:
                    writer.result()
                    break
                if reader not in done:
                    continue
                message = reader.result()
                if message.type != WSMsgType.TEXT:
                    break
                try:
                    command = message.json()
                except (ValueError, TypeError):
                    raise OperationError("invalid_command", 400) from None
                if not isinstance(command, dict):
                    raise OperationError("invalid_command", 400)
                rid = command.get("id")
                if type(rid) is not int or not 0 < rid < 2**31 or rid in seen or len(seen) >= 256:
                    raise OperationError("invalid_request_id", 400)
                seen.add(rid)
                if len(workers) >= 8:
                    enqueue(
                        {
                            "id": rid,
                            "connection_id": connection_id,
                            "type": "result",
                            "success": False,
                            "status": 429,
                            "error": {"code": "operation_capacity"},
                        }
                    )
                else:
                    workers[rid] = asyncio.create_task(run_command(command))
                reader = asyncio.create_task(ws.receive())
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            failure = "slow_consumer" if authenticated else "auth_timeout"
        except (ValueError, TypeError):
            failure = "invalid_projection" if authenticated else "invalid_auth"
        except OperationError as exc:
            failure = exc.code
        finally:
            if remove_settings_listener is not None:
                remove_settings_listener()
            tasks = tuple(workers.values()) + tuple(t for t in (reader, writer) if t is not None)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if failure and not ws.closed:
                with suppress(ConnectionError, RuntimeError, TimeoutError):
                    async with asyncio.timeout(2):
                        await ws.send_json({"type": "auth_invalid", "code": failure})
            await ws.close()
        return ws
