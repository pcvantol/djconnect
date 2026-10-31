"""Closed Direct rich routes; normal setup owns the sole warm service."""
import asyncio
import time

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .direct_rich_runtime import KEY, DirectRichService
from .direct_rich_wire import BASE, REQUEST_BYTES, RichError, canonical, one_header, parse, require

HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}


class DirectRichView(HomeAssistantView):
    requires_auth = False  # Exact ordinary pair or independent role, below.

    def __init__(self, hass, operation):
        self.hass, self.operation = hass, operation
        self.url = BASE + "/" + operation
        self.name = "api:djconnect:direct_rich:" + operation

    def register(self, hass, app, router):
        router.add_route("POST", self.url, self.post)
        router.add_route("*", self.url, self.unsupported)

    async def unsupported(self, request):
        return web.Response(body=canonical({"success": False, "contract_version": 1, "error": "invalid_request"}),
            status=400, content_type="application/json", headers={**HEADERS, "Allow": "POST"})

    async def post(self, request):
        captured = (time.time(), time.monotonic())  # Before ANY body/SQL await.
        raw, payload = bytearray(), None
        try:
            require(request.raw_path == self.url)
            require(not any(name in request.headers for name in ("Origin", "Cookie", "Content-Encoding")))
            require(one_header(request.headers, "Content-Type").lower() == "application/json")
            require(request.content_length is None or request.content_length <= REQUEST_BYTES)
            async with asyncio.timeout(10):
                async for chunk in request.content.iter_chunked(1024):
                    raw.extend(chunk)
                    require(len(raw) <= REQUEST_BYTES)
            payload = parse(self.operation, bytes(raw))
            service = self.hass.data.get("djconnect", {}).get(KEY)
            require(type(service) is DirectRichService, "rich_unavailable", 503)
            if self.operation == "authorize":
                result = await service.authorize(payload, request.headers, captured, as_bytes=True)
            elif self.operation in {"status", "withdraw"}:
                result = await service.manage(payload, request.headers, withdraw=self.operation == "withdraw", as_bytes=True)
            else:
                result = service.read(payload, request.headers, asset=self.operation == "asset", as_bytes=True)
            if self.operation == "asset":
                body, mime = result
                return web.Response(body=body, content_type=mime, headers=HEADERS)
            return web.Response(body=result, content_type="application/json", headers=HEADERS)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            public = error if isinstance(error, RichError) else RichError("rich_unavailable", 503)
            return web.Response(body=canonical({"success": False, "contract_version": 1, "error": public.code}),
                status=public.status, content_type="application/json", headers=HEADERS)
        finally:
            raw.clear()
            if payload is not None:
                payload.clear()  # Release references; no secure-erasure claim.


def rich_views(hass):
    return [DirectRichView(hass, operation) for operation in ("authorize", "read", "asset", "status", "withdraw")]
