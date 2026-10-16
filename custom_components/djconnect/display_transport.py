"""Bounded HA B HTTP adapter; registered only by the completed B integration.

TLS is mandatory. No query/cookie/admin authentication, CORS, provider requests
or use of Host/forwarded headers as the selected installation's identity.
"""
from __future__ import annotations

import json

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .display_admission import DisplayAdmissionError
from .display_service import DisplayAdmissionService

SECURITY_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
                    "X-Content-Type-Options": "nosniff"}
BODY_LIMIT = 4096


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError("non-JSON number")


async def closed_body(request):
    if request.content_type != "application/json":
        raise DisplayAdmissionError("display_code_invalid", 400)
    if request.content_length is not None and request.content_length > BODY_LIMIT:
        raise DisplayAdmissionError("display_code_invalid", 413)
    raw = bytearray()
    async for chunk in request.content.iter_chunked(1024):
        if len(raw) + len(chunk) > BODY_LIMIT:
            raise DisplayAdmissionError("display_code_invalid", 413)
        raw.extend(chunk)
    try:
        body = json.loads(raw, object_pairs_hook=_object, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise DisplayAdmissionError("display_code_invalid", 400) from None
    if not isinstance(body, dict):
        raise DisplayAdmissionError("display_code_invalid", 400)
    return body


class _FencedResponse(web.Response):
    def __init__(self, result):
        self._display_release = result.release
        raw = json.dumps(result.payload, ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > 128 * 1024:
            raise DisplayAdmissionError("display_capacity", 503)
        super().__init__(body=raw, content_type="application/json", headers=SECURITY_HEADERS)

    async def write_eof(self, data=b""):
        # aiohttp may await prepare()/header drain after the handler returns.
        # Recheck immediately before body release; a stale successful HTTP status
        # must not release private claim/grant bytes. Close an already-started
        # response instead of writing an error into its successful JSON body.
        try:
            self._display_release()
        except DisplayAdmissionError:
            self.force_close()
            if self._req is not None and self._req.transport is not None:
                self._req.transport.close()
            return
        await super().write_eof(data)


class DisplayTransitionView(HomeAssistantView):
    requires_auth = False  # The service enforces ordinary paired/display auth.

    def __init__(self, hass, action):
        self.hass, self.action = hass, action
        self.url = "/api/djconnect/v1/display/" + action
        self.name = "api:djconnect:display:" + action.replace("/", ":")

    async def post(self, request):
        try:
            if request.query_string:
                raise DisplayAdmissionError("display_code_invalid", 400)
            if not request.secure:
                raise DisplayAdmissionError("display_tls_required", 426)
            if len(request.headers.getall("Authorization", [])) > 1:
                raise DisplayAdmissionError("display_code_invalid", 400)
            body = await closed_body(request)
            from .session_runtime import session_runtime_manager
            manager = session_runtime_manager(self.hass)
            peer = request.transport.get_extra_info("peername") if request.transport else None
            # Transport peer only. Trusted reverse proxies share a source budget;
            # the hard global bound remains effective. Never trust X-Forwarded-For.
            source = str(peer[0])[:128] if isinstance(peer, tuple) and peer else "unknown"
            result = await DisplayAdmissionService(self.hass, manager).post(self.action, body,
                headers=request.headers, origins=request.headers.getall("Origin", []), source=source)
            result.release()
            return _FencedResponse(result)
        except DisplayAdmissionError as error:
            return web.json_response({"success": False, "contract_version": 1, "error": error.code},
                                     status=error.status, headers=SECURITY_HEADERS)


def transition_views(hass):
    """Closed list; no catch-all route accidentally accepts owner effects."""
    return [DisplayTransitionView(hass, action) for action in (
        "owner/context", "owner/resolve", "owner/approve", "owner/revoke",
        "claim", "collect", "cancel", "renew", "leave")]
