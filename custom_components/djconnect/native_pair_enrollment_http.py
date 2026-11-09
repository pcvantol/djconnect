"""Authenticated entry points for a selected native enrollment service."""

import asyncio
import json

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import API_BASE, DOMAIN
from .direct_rich_wire import RichError, canonical, one_header
from .native_pair_enrollment import KEY, NativePairEnrollment
from .surface_push_contract import SurfacePushError, require

_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff"}


def _response(payload, status=200):
    return web.Response(body=canonical(payload), status=status,
                        content_type="application/json", headers=_HEADERS)


def _unique_object(items):
    result = {}
    for key, value in items:
        require(key not in result, "invalid_request")
        result[key] = value
    return result


def _selected_service(hass):
    service = hass.data.get(DOMAIN, {}).get(KEY)
    require(type(service) is NativePairEnrollment, "native_pair_enrollment_unavailable", 503)
    return service


def _request_headers(request, path):
    require(request.raw_path == path
            and not any(name in request.headers for name in ("Origin", "Cookie", "Content-Encoding")),
            "invalid_request")


async def _payload(request, *, limit, fields):
    require(one_header(request.headers, "Content-Type").lower() == "application/json", "invalid_request")
    require(request.content_length is None or request.content_length <= limit, "payload_too_large", 413)
    raw = bytearray()
    async with asyncio.timeout(10):
        async for chunk in request.content.iter_chunked(2048):
            raw.extend(chunk)
            require(len(raw) <= limit, "payload_too_large", 413)
    payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    require(type(payload) is dict and set(payload) == fields | {"contract_version"}
            and type(payload["contract_version"]) is int
            and payload["contract_version"] == 1, "invalid_request")
    del payload["contract_version"]
    return payload


def _failed(error):
    if isinstance(error, (SurfacePushError, RichError)):
        return _response({"error": error.code}, error.status)
    if isinstance(error, (ValueError, RecursionError)):
        return _response({"error": "invalid_request"}, 400)
    # Never expose upstream input, credentials, or proofs.
    return _response({"error": "native_pair_enrollment_unavailable"}, 503)


class NativePairEnrollmentView(HomeAssistantView):
    requires_auth = False  # The service authenticates the exact ordinary pair.

    def __init__(self, hass, operation):
        self.hass = hass
        self.operation = operation
        self.url = API_BASE + "/push/native/pair-witness/" + operation
        self.name = "api:djconnect:native-pair-witness:" + operation

    async def post(self, request):
        try:
            service = _selected_service(self.hass)
            _request_headers(request, self.url)
            fields = {"device_id", "client_type"}
            if self.operation in ("register", "status"):
                fields.add("operation_id")
            if self.operation == "register":
                fields.add("apple_proof")
            payload = await _payload(request, limit=32_768 if self.operation == "register" else 1024, fields=fields)
            result = await getattr(service, self.operation)(request.headers, **payload)
            return _response(result)
        except Exception as error:
            return _failed(error)


class NativeWidgetConsentView(HomeAssistantView):
    requires_auth = False  # The service authenticates the exact ordinary pair.
    url = API_BASE + "/push/native/consent/widgetkit"
    name = "api:djconnect:native-consent:widgetkit"

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        try:
            service = _selected_service(self.hass)
            _request_headers(request, self.url)
            require(not request.can_read_body, "invalid_request")
            return _response(await service.consent(request.headers))
        except Exception as error:
            return _failed(error)

    async def post(self, request):
        try:
            service = _selected_service(self.hass)
            _request_headers(request, self.url)
            payload = await _payload(request, limit=1024, fields={"enabled", "operation_id", "expected_revision"})
            require(type(payload["operation_id"]) is str, "invalid_request")
            return _response(await service.consent(request.headers, **payload))
        except Exception as error:
            return _failed(error)


def native_pair_enrollment_views(hass):
    return [
        *(NativePairEnrollmentView(hass, operation) for operation in ("bootstrap", "challenge", "register", "status")),
        NativeWidgetConsentView(hass),
    ]
