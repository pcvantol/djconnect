"""TLS-only paired action adapters; ordinary owner HTTP and WS share services."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import json
import secrets
from urllib.parse import urlsplit

from aiohttp import WSMsgType, web
from homeassistant.components.http import HomeAssistantView

from .hybrid_service import OperationError, PairedAuthority, operations
from .transport_delivery import OwnerDeliveryResult
from .hybrid_contract import FRAME_LIMIT, bounded_frame

ACTION_PATH = "/api/djconnect/v1/actions/paired"
AUTH_TIMEOUT = 5
LEASE_SECONDS = 300
RECHECK_SECONDS = 1


def response(body, status=200):
    return web.json_response(
        body, status=status, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    )


def request_error(request):
    if request.query_string:
        return response({"success": False, "error": "query_not_allowed"}, 400)
    if not request.secure:
        return response({"success": False, "error": "transport_security_required"}, 426)
    origin = request.headers.get("Origin")
    if origin is not None:
        try:
            supplied = urlsplit(origin)
            expected = urlsplit("https://" + request.host)
            allowed = (
                supplied.scheme == "https"
                and not supplied.username
                and not supplied.password
                and not supplied.path
                and not supplied.query
                and not supplied.fragment
                and supplied.hostname == expected.hostname
                and (supplied.port or 443) == (expected.port or 443)
            )
        except ValueError:
            allowed = False
        if not allowed:
            return response({"success": False, "error": "origin_not_allowed"}, 403)
    return None


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
        invalid = request_error(request)
        if invalid is not None:
            return invalid
        try:
            body = await json_body(request)
            identity = body.pop("identity", None)
            authority = await PairedAuthority.resolve(self.hass, identity, request.headers)
            manager = operations(self.hass)
            if self.action == "context":
                if body != {"contract_version": 1} or type(body.get("contract_version")) is not int:
                    raise OperationError("invalid_request", 400)
                result, status = await manager.context(authority), 200
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
        invalid = request_error(request)
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
                if sum(device == authority.device for device in self.connections.values()) >= 2:
                    raise OperationError("connection_capacity", 429)
                self.connections[connection_id] = authority.device
                context = await manager.context(authority)
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
                    ],
                }
            )
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
        except (TimeoutError, ValueError, TypeError):
            failure = "invalid_auth"
        except OperationError as exc:
            failure = exc.code
        finally:
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
