"""DJConnect central API client for per-install relay calls."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import secrets
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_BASE_URL,
    CONF_CENTRAL_API_BOOTSTRAP_PROOF,
    CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT,
    CONF_CLIENT_TYPE,
    CONF_DJCONNECT_INSTALL_TOKEN,
    CONF_DEVICE_ID,
    CONF_HA_INSTALL_ID,
    DEFAULT_API_BASE_URL,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)
TOKEN_PREFIX = "djci_"
DEFAULT_TIMEOUT_SECONDS = 10
MAX_ATTEMPTS = 2
SECRET_KEY_PARTS = (
    "token",
    "password",
    "secret",
    "proof",
    "authorization",
    "prompt",
    "response",
    "history",
    "memory",
)


class DJConnectCentralApiError(Exception):
    """Raised when the central API cannot be called safely."""


def ensure_ha_install_id(runtime: Any) -> str:
    """Return a stable HA install id, generating one for old config entries."""
    config = _runtime_config(runtime)
    current = _clean(config.get(CONF_HA_INSTALL_ID), 160)
    if current:
        return current
    return f"ha_{secrets.token_urlsafe(24)}"


def central_api_configured(runtime: Any) -> bool:
    """Return true when a valid per-install API token is configured."""
    return bool(_install_token(runtime))


async def async_ensure_install_token(hass: Any, runtime: Any) -> dict[str, Any]:
    """Ensure this HA installation has a central API install token."""
    existing = _install_token(runtime)
    if existing:
        return {"success": True, "created": False}
    install_id = ensure_ha_install_id(runtime)
    proof = _bootstrap_proof(runtime)
    if not proof:
        return {"success": False, "error": "missing_bootstrap_proof"}
    if _bootstrap_proof_expired(runtime):
        return {"success": False, "error": "invalid_bootstrap_proof"}
    payload = {
        "ha_install_id": install_id,
        "integration": "djconnect_hacs",
        "integration_version": VERSION,
        "bootstrap_proof": proof,
    }
    device_id = _device_id(runtime)
    client_type = _client_type(runtime)
    if device_id:
        payload[CONF_DEVICE_ID] = device_id
    if client_type:
        payload[CONF_CLIENT_TYPE] = client_type
    expires_at = _bootstrap_proof_expires_at(runtime)
    if expires_at:
        payload[CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT] = expires_at
    result = await _post_json(
        hass,
        runtime,
        "/v1/install/token",
        payload,
        token=None,
    )
    new_token = _clean(result.get("install_token") or result.get(CONF_DJCONNECT_INSTALL_TOKEN), 4096)
    if not result.get("success") or not _valid_install_token(new_token):
        return {"success": False, "error": _clean(result.get("error"), 120) or "missing_install_token"}
    _persist_install_settings(hass, runtime, install_id=install_id, token=new_token)
    return {"success": True, "created": True}


async def async_post(
    hass: Any,
    runtime: Any,
    path: str,
    payload: dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST a sanitized JSON payload to the central DJConnect API."""
    token = _install_token(runtime)
    if not token:
        ensured = await async_ensure_install_token(hass, runtime)
        if not ensured.get("success"):
            raise DJConnectCentralApiError(_clean(ensured.get("error"), 120) or "missing_install_token")
        token = _install_token(runtime)
    if not token:
        raise DJConnectCentralApiError("missing_install_token")
    install_id = ensure_ha_install_id(runtime)
    body = dict(payload)
    body["ha_install_id"] = install_id
    _assert_safe_payload(body)
    return await _post_json(hass, runtime, path, body, token=token, timeout=timeout)


async def _post_json(
    hass: Any,
    runtime: Any,
    path: str,
    payload: dict[str, Any],
    *,
    token: str | None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST JSON to the central API with optional bearer auth."""
    _assert_safe_payload(payload)
    url = f"{_api_base_url(runtime).rstrip('/')}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    session = async_get_clientsession(hass)
    last_error = "central_api_unavailable"
    for attempt in range(MAX_ATTEMPTS):
        try:
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                data = await _response_json(response)
                success = 200 <= int(getattr(response, "status", 0)) < 300 and data.get("success", True)
                if success:
                    return {"success": True, **data}
                last_error = _clean(data.get("error") or getattr(response, "status", ""), 120)
                if int(getattr(response, "status", 0)) < 500:
                    break
        except (TimeoutError, asyncio.TimeoutError):
            last_error = "central_api_timeout"
        except Exception as exc:  # noqa: BLE001
            last_error = "central_api_unavailable"
            _LOGGER.debug(
                "DJConnect central API request failed: path=%s error=%s",
                path,
                exc.__class__.__name__,
            )
        if attempt + 1 < MAX_ATTEMPTS:
            await asyncio.sleep(0.25)
    return {"success": False, "error": last_error}


async def async_rotate_install_token(hass: Any, runtime: Any) -> dict[str, Any]:
    """Rotate the central API install token and persist only after success."""
    result = await async_post(hass, runtime, "/v1/install/rotate", {})
    new_token = _clean(result.get("install_token") or result.get(CONF_DJCONNECT_INSTALL_TOKEN), 4096)
    if not result.get("success") or not _valid_install_token(new_token):
        return {"success": False, "error": _clean(result.get("error"), 120) or "invalid_install_token"}
    _persist_install_settings(hass, runtime, install_id=ensure_ha_install_id(runtime), token=new_token)
    return {"success": True, CONF_DJCONNECT_INSTALL_TOKEN: new_token}


def _persist_install_settings(hass: Any, runtime: Any, *, install_id: str, token: str) -> None:
    """Persist central API settings in the config entry options."""
    entry = getattr(runtime, "entry", None) or getattr(runtime, "config_entry", None)
    if entry is None:
        return
    options = dict(getattr(entry, "options", {}) or {})
    options.setdefault(CONF_API_BASE_URL, _api_base_url(runtime))
    options[CONF_HA_INSTALL_ID] = install_id
    options[CONF_DJCONNECT_INSTALL_TOKEN] = token
    if hasattr(getattr(hass, "config_entries", None), "async_update_entry"):
        hass.config_entries.async_update_entry(entry, options=options)
    else:
        setattr(entry, "options", options)


def redacted(value: Any) -> Any:
    """Return a copy safe for debug logs."""
    if isinstance(value, dict):
        return {
            key: "<redacted>" if _sensitive_key(key) else redacted(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redacted(item) for item in value]
    return value


async def _response_json(response: Any) -> dict[str, Any]:
    try:
        data = await response.json()
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _api_base_url(runtime: Any) -> str:
    config = _runtime_config(runtime)
    return _clean(config.get(CONF_API_BASE_URL), 500) or DEFAULT_API_BASE_URL


def _install_token(runtime: Any) -> str:
    config = _runtime_config(runtime)
    token = _clean(config.get(CONF_DJCONNECT_INSTALL_TOKEN), 4096)
    return token if _valid_install_token(token) else ""


def _bootstrap_proof(runtime: Any) -> str:
    return _clean(
        _runtime_value(runtime, CONF_CENTRAL_API_BOOTSTRAP_PROOF, "bootstrap_proof"),
        4096,
    )


def _bootstrap_proof_expires_at(runtime: Any) -> str:
    return _clean(
        _runtime_value(
            runtime,
            CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT,
            "bootstrap_proof_expires_at",
        ),
        120,
    )


def _bootstrap_proof_expired(runtime: Any) -> bool:
    value = _bootstrap_proof_expires_at(runtime)
    if not value:
        return False
    try:
        expires = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return expires <= datetime.now(timezone.utc)


def _device_id(runtime: Any) -> str:
    return _clean(_runtime_value(runtime, CONF_DEVICE_ID, "device_id"), 160)


def _client_type(runtime: Any) -> str:
    getter = getattr(runtime, "client_type", None)
    if callable(getter):
        try:
            value = getter()
            if value:
                return _clean(value, 80)
        except Exception:  # noqa: BLE001
            pass
    return _clean(_runtime_value(runtime, CONF_CLIENT_TYPE, "client_type"), 80)


def _runtime_value(runtime: Any, *keys: str) -> Any:
    status = getattr(runtime, "device_status", None)
    if isinstance(status, dict):
        for key in keys:
            value = status.get(key)
            if value not in (None, ""):
                return value
    config = _runtime_config(runtime)
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            return value
    return ""


def _runtime_config(runtime: Any) -> dict[str, Any]:
    config = getattr(runtime, "config", None)
    if isinstance(config, dict):
        return config
    entry = getattr(runtime, "entry", None) or getattr(runtime, "config_entry", None)
    data = dict(getattr(entry, "data", {}) or {})
    data.update(dict(getattr(entry, "options", {}) or {}))
    return data


def _valid_install_token(value: Any) -> bool:
    token = str(value or "").strip()
    return token.startswith(TOKEN_PREFIX) and len(token) > len(TOKEN_PREFIX)


def _assert_safe_payload(payload: dict[str, Any]) -> None:
    rendered = str(redacted(payload)).lower()
    forbidden = ("spotify_refresh_token", "ha_token", "assistant_response", "raw_prompt", "full_history")
    if any(item in rendered for item in forbidden):
        raise DJConnectCentralApiError("unsafe_central_api_payload")


def _sensitive_key(key: Any) -> bool:
    normalized = str(key).lower()
    return any(part in normalized for part in SECRET_KEY_PARTS)


def _clean(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]
