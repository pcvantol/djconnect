"""Transport-neutral request identity and auth helpers."""
from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any

from .const import (
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    DEFAULT_CLIENT_TYPE,
    DOMAIN,
    CLIENT_TYPES,
)

_LOGGER = logging.getLogger("custom_components.djconnect.http")
_STALE_AUTH_LOG_THROTTLE_SECONDS = 300
_last_stale_auth_log: dict[str, float] = {}


def request_token(headers: Any) -> str:
    """Return bearer token from transport headers."""
    auth = str(headers.get("Authorization", "") or "").strip()
    return auth.removeprefix("Bearer ").strip()


def resolve_runtime(
    hass: Any,
    device_id: str | None = None,
    headers: Any | None = None,
) -> Any:
    """Resolve the DJConnect runtime for a request."""
    data = hass.data.get(DOMAIN, {})
    runtimes = [
        runtime
        for key, runtime in data.items()
        if key != "runtime" and hasattr(runtime, "authorize_device_request")
    ]
    device_id = str(device_id or "").strip()
    token = request_token(headers or {})
    active_runtime = data.get("runtime")
    if not runtimes and active_runtime is not None:
        return active_runtime
    if device_id:
        matches = [runtime for runtime in runtimes if runtime_matches_device(runtime, device_id)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            _LOGGER.warning(
                "DJConnect found multiple runtimes for device_id=%s; using active runtime",
                device_id,
            )
    if token:
        token_matches = [
            runtime
            for runtime in runtimes
            if getattr(runtime, "device_token", None) == token
        ]
        if len(token_matches) == 1:
            return token_matches[0]
        if len(token_matches) > 1:
            _LOGGER.warning(
                "DJConnect found multiple runtimes with matching device token; using active runtime"
            )
        else:
            _log_stale_auth_warning(
                f"bearer_token:{_token_fingerprint(token)}",
                "DJConnect no runtime matched bearer token; rejecting stale client request",
            )
            return None
    if device_id:
        _LOGGER.warning(
            "DJConnect no runtime matched device_id=%s; rejecting stale client request",
            device_id,
        )
        return None
    return data.get("runtime")


def runtime_matches_device(runtime: Any, device_id: str) -> bool:
    """Return whether a runtime matches a request device id."""
    known = str(
        getattr(runtime, "device_status", {}).get("device_id")
        or getattr(runtime, "pairing_device_id", "")
        or getattr(runtime, "config", {}).get(CONF_DEVICE_ID, "")
        or ""
    ).strip()
    if not known or not device_id:
        return False
    if known == device_id:
        return True
    return bool(
        re.fullmatch(r"djconnect-\d{6}", known)
        and is_real_device_id(device_id)
    )


def is_real_device_id(device_id: str) -> bool:
    """Return true for canonical DJConnect device/client IDs."""
    return bool(
        re.fullmatch(
            r"djconnect-(?:lilygo-t-embed-s3|esp32-s3-box-3|lilygo)-[0-9A-Fa-f]{12}"
            r"|djconnect-(?:ios|macos|watchos|raspberry-pi|windows)-[A-Za-z0-9]{12}",
            str(device_id or ""),
        )
    )


def identity_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Merge top-level and nested identity payloads."""
    identity = data.get("identity") if isinstance(data.get("identity"), dict) else {}
    merged = dict(identity)
    merged.update({key: value for key, value in data.items() if key not in {"identity"}})
    return merged


def payload_client_type(data: dict[str, Any]) -> str:
    """Return normalized client_type from a payload."""
    return str(data.get(CONF_CLIENT_TYPE) or "").strip().lower()


def validate_required_client_type(data: dict[str, Any]) -> str | None:
    """Return valid client_type or None."""
    client_type = payload_client_type(data)
    if not client_type or client_type not in CLIENT_TYPES:
        return None
    return client_type


def runtime_client_type(runtime: Any) -> str:
    """Return configured/runtime client_type fallback."""
    getter = getattr(runtime, "client_type", None)
    if callable(getter):
        return str(getter() or DEFAULT_CLIENT_TYPE)
    status = getattr(runtime, "device_status", {}) or {}
    conf = getattr(runtime, "config", {}) or {}
    return str(
        status.get(CONF_CLIENT_TYPE)
        or conf.get(CONF_CLIENT_TYPE)
        or DEFAULT_CLIENT_TYPE
    )


def authorize_runtime_device_request(
    runtime: Any,
    headers: Any,
    device_id: str | None,
    client_type: str | None,
) -> bool:
    """Authorize a request while keeping lightweight test doubles compatible."""
    authorize = getattr(runtime, "authorize_device_request")
    try:
        return bool(authorize(headers, device_id, client_type))
    except TypeError:
        return bool(authorize(headers, device_id))


def _log_stale_auth_warning(key: str, message: str, *args: Any) -> None:
    now = time.monotonic()
    last = _last_stale_auth_log.get(key, 0)
    if now - last < _STALE_AUTH_LOG_THROTTLE_SECONDS:
        _LOGGER.debug(message, *args)
        return
    _last_stale_auth_log[key] = now
    _LOGGER.warning(message, *args)


def _token_fingerprint(token: str) -> str:
    """Return a non-secret token fingerprint for internal warning throttling."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
