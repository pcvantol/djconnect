"""Single-attempt relay boundary; no bootstrap, redirects, logging or token Store."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlsplit

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .central_api import _api_base_url, _assert_safe_payload
from .surface_push_contract import SurfacePushError, require
from .surface_push_purpose import SurfacePurposeCredential

ROUTES = {name: "/v1/push/surface/" + name for name in ("register", "revoke", "event", "status")}
MAX_RESPONSE_BYTES = 8192


async def post_once(hass, runtime, action, payload, admission):
    """One durable caller intent, at most one HTTP attempt, bounded static errors.

    The caller reserves its existing operation journal before invoking this.
    Registration can never create an installation token or repair configuration.
    """
    require(type(action) is str and action in ROUTES, "surface_relay_route_invalid")
    admission.validate()
    purpose = getattr(admission, "purpose", None)
    require(type(purpose) is SurfacePurposeCredential, "surface_purpose_unavailable", 503)
    token = purpose.authorize(action, payload)
    parsed = urlsplit(_api_base_url(runtime))
    require(
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
        and parsed.path in ("", "/"),
        "surface_relay_origin_invalid",
        503,
    )
    origin = f"https://{parsed.netloc}"
    require(origin == purpose.origin, "surface_purpose_origin_mismatch", 403)
    body = dict(payload)
    _assert_safe_payload(body)
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(10):
            admission.validate()
            purpose.authorize(action, body)
            require(_api_base_url(runtime).rstrip("/") == purpose.origin,
                "surface_purpose_origin_mismatch", 403)
            async with session.post(
                f"https://{parsed.netloc}{ROUTES[action]}",
                json=body,
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                allow_redirects=False,
                timeout=10,
            ) as response:
                if not 200 <= response.status < 300:
                    return {"success": False, "error": "surface_relay_outcome_unknown"}
                raw = bytearray()
                while True:
                    chunk = await response.content.read(
                        min(2048, MAX_RESPONSE_BYTES + 1 - len(raw))
                    )
                    if not chunk:
                        break
                    raw.extend(chunk)
                    require(len(raw) <= MAX_RESPONSE_BYTES, "surface_relay_response_invalid", 502)
                admission.validate()
                purpose.authorize(action, body)
                require(_api_base_url(runtime).rstrip("/") == purpose.origin,
                    "surface_purpose_origin_mismatch", 403)
                result = json.loads(raw)
                require(type(result) is dict, "surface_relay_response_invalid", 502)
                return result
    except asyncio.CancelledError:
        raise
    except SurfacePushError:
        raise
    except Exception:
        # Do not surface upstream free text, response bodies, tokens or URLs.
        return {"success": False, "error": "surface_relay_outcome_unknown"}
