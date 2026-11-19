"""Dedicated native VibeScape transport; no generic conversation fallback."""

from __future__ import annotations

import asyncio
import json

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .visual_director import (
    BODY_LIMIT,
    HEADERS,
    VERSION,
    VisualDirectorError,
    parse_body,
    validate_request,
)
from .visual_director_runtime import handle


class _VisualView(HomeAssistantView):
    requires_auth = False  # Exact existing device bearer is checked by handle.
    kind = ""

    def __init__(self, hass):
        self.hass = hass

    def register(self, hass, app, router):
        # Own all methods of these three static native-only routes. In
        # particular 405 and shutdown errors keep the same no-store boundary;
        # the general HA wrapper's early stopping response cannot bypass it.
        router.add_route("POST", self.url, self.post)
        router.add_route("*", self.url, self.unsupported)

    @staticmethod
    def response(payload, status=200, *, extra=None):
        return web.Response(
            text=json.dumps({"schema_version": VERSION, **payload}, allow_nan=False),
            status=status,
            content_type="application/json",
            headers={**HEADERS, "X-Content-Type-Options": "nosniff", **(extra or {})},
        )

    async def unsupported(self, request):
        return self.response(
            {"success": False, "schema_version": VERSION, "error": "method_not_allowed"},
            405,
            extra={"Allow": "POST"},
        )

    async def post(self, request):
        raw = b""
        data = None
        try:
            if getattr(self.hass, "is_stopping", False):
                return self.response({"success": False, "error": "visual_unavailable"}, 503)
            if request.query_string:
                return self.response({"success": False, "error": "invalid_request"}, 400)
            if (
                request.content_type != "application/json"
                or (request.charset or "utf-8").lower() not in ("utf-8", "utf8")
                or request.headers.get("Content-Encoding", "identity").lower() != "identity"
            ):
                return self.response({"success": False, "error": "unsupported_media_type"}, 415)
            if request.content_length is not None and request.content_length > BODY_LIMIT:
                return self.response({"success": False, "error": "request_too_large"}, 413)
            # StreamReader.read may return partial chunks. Never use Request.read
            # or Request.json, which retain a body cache on the request object.
            async with asyncio.timeout(5):
                while len(raw) <= BODY_LIMIT:
                    chunk = await request.content.read(min(2048, BODY_LIMIT + 1 - len(raw)))
                    if not chunk:
                        break
                    raw += chunk
                    chunk = b""
            if len(raw) > BODY_LIMIT:
                return self.response({"success": False, "error": "request_too_large"}, 413)
            data = parse_body(raw)
            raw = b""
            validate_request(self.kind, data)
            result, status = await handle(self.hass, self.kind, data, headers=request.headers)
            return self.response(result, status)
        except VisualDirectorError as error:
            return self.response(
                {"success": False, "schema_version": VERSION, "error": error.code}, error.status
            )
        except Exception:
            # No logger, traceback text, input reflection, tools or alternate path.
            return self.response(
                {"success": False, "schema_version": VERSION, "error": "visual_unavailable"}, 503
            )
        finally:
            raw = b""
            if data is not None:
                data.clear()  # Drop our transient references; no secure-erasure claim.


class VibeScapeContextView(_VisualView):
    url = "/api/djconnect/v1/vibescape/context"
    name = "api:djconnect:vibescape:context"
    kind = "context"


class VibeScapeInterpretView(_VisualView):
    url = "/api/djconnect/v1/vibescape/interpret"
    name = "api:djconnect:vibescape:interpret"
    kind = "interpret"


class VibeScapeRevokeView(_VisualView):
    url = "/api/djconnect/v1/vibescape/revoke"
    name = "api:djconnect:vibescape:revoke"
    kind = "revoke"
