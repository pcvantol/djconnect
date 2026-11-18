"""Actual seven Core host-wake routes on the original pre-body paired request."""
import asyncio
import time

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .direct_rich_http import HEADERS
from .direct_rich_wire import RichError, canonical, one_header, require
from .host_wake_proxy_attempt import HostWakeAttempt
from .host_wake_proxy_wire import BASE, BODY_BYTES, OPERATIONS, parse, public_error


class HostWakeView(HomeAssistantView):
    requires_auth = False  # The actual ordinary pair is captured before body IO.

    def __init__(self, hass, operation):
        self.hass, self.operation = hass, operation
        self.url = BASE + operation
        self.name = "api:djconnect:host_wake:" + operation.replace("/", ":")

    def register(self, hass, app, router):
        router.add_route("POST", self.url, self.post)
        router.add_route("*", self.url, self.unsupported)

    async def unsupported(self, request):
        return self.error(RichError(), extra_headers={"Allow": "POST"})

    @staticmethod
    def error(error, *, extra_headers=None):
        error = public_error(error)
        return web.Response(body=canonical({"success": False, "contract_version": 1,
            "error": error.code}), status=error.status, content_type="application/json",
            headers={**HEADERS, **(extra_headers or {})})

    async def post(self, request):
        from .host_wake_runtime import execute

        attempt, payload, raw = None, None, bytearray()
        try:
            require(request.raw_path == self.url)
            attempt = HostWakeAttempt(self.hass, request.headers)
            require(not any(key in request.headers for key in ("Origin", "Cookie", "Content-Encoding")))
            require(one_header(request.headers, "Content-Type").lower() == "application/json")
            length = request.content_length
            require(length is None or (type(length) is int and length >= 0))
            require(length is None or length <= BODY_BYTES, "rich_body_too_large", 413)
            attempt.check_body_budget()
            remaining = min(10 - (time.time() - attempt.wall),
                10 - (time.monotonic() - attempt.mono), attempt.check())
            require(remaining > 0, "rich_unavailable", 503)
            async with asyncio.timeout(remaining):
                async for chunk in request.content.iter_chunked(1024):
                    attempt.check_body_budget()
                    raw.extend(chunk)
                    require(len(raw) <= BODY_BYTES, "rich_body_too_large", 413)
            attempt.check_body_budget()
            payload = parse(self.operation, bytes(raw))
            body = await execute(attempt, self.operation, payload)
            attempt.check()
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            return web.Response(body=body, content_type="application/json", headers=HEADERS)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            return self.error(error if isinstance(error, RichError) else RichError("rich_unavailable", 503))
        finally:
            raw.clear()
            if payload is not None:
                payload.clear()
            if attempt is not None:
                attempt.close()


def host_wake_views(hass):
    return [HostWakeView(hass, operation) for operation in sorted(OPERATIONS)]
