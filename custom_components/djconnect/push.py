"""Best-effort DJConnect push relay support for Apple clients."""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from .central_api import (
    DJConnectCentralApiError,
    async_post as async_central_post,
    central_api_configured,
    ensure_ha_install_id,
)
from .const import (
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_WATCHOS,
    CONF_CENTRAL_API_BOOTSTRAP_PROOF,
    CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
)

SUPPORTED_CLIENT_TYPES = {CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS}
SUPPORTED_ENVIRONMENTS = {"sandbox", "production"}
EVENT_ASK_DJ_RESPONSE = "ask_dj_response"
EVENT_ASK_DJ_CONFIRM = "ask_dj_confirm"
EVENT_PLAYBACK_CHANGE = "playback_change"
PUSHABLE_EVENTS = {EVENT_ASK_DJ_RESPONSE, EVENT_ASK_DJ_CONFIRM}
RATE_LIMIT_WINDOW_SECONDS = 30
RATE_LIMIT_BURST_SECONDS = 10 * 60
RATE_LIMIT_BURST_MAX = 5
RECENT_ACTIVE_SECONDS = 30
_LOGGER = logging.getLogger(__name__)


async def async_register(
    hass: Any,
    runtime: Any,
    *,
    user_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Forward an Apple push token registration to the central DJConnect relay."""
    cleaned = _registration_payload(runtime, user_id=user_id, payload=payload)
    if not cleaned:
        return {"success": False, "error": "invalid_push_registration"}
    _remember_bootstrap_proof(runtime, payload)
    result = await _post_relay(hass, runtime, "/v1/push/register", cleaned)
    if result.get("success"):
        _remember_status(
            runtime,
            cleaned.get("device_id"),
            cleaned.get("client_type"),
            registered=True,
            environment=cleaned.get("push_environment"),
            error=None,
        )
    else:
        _remember_status(
            runtime,
            cleaned.get("device_id"),
            cleaned.get("client_type"),
            registered=False,
            environment=cleaned.get("push_environment"),
            error=result.get("error"),
        )
    return {
        "success": bool(result.get("success")),
        "push_supported": relay_configured(runtime),
        "push_registered": bool(result.get("success")),
        "push_environment": result.get("push_environment") or cleaned.get("push_environment"),
        "last_push_error": _clean_text(result.get("error"), 120) or None,
    }


async def async_unregister(
    hass: Any,
    runtime: Any,
    *,
    user_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Forward an Apple push token unregister request to the central relay."""
    cleaned = _registration_payload(runtime, user_id=user_id, payload=payload)
    if not cleaned:
        return {"success": False, "error": "invalid_push_registration"}
    result = await _post_relay(hass, runtime, "/v1/push/unregister", cleaned)
    if result.get("success"):
        _remember_status(
            runtime,
            cleaned.get("device_id"),
            cleaned.get("client_type"),
            registered=False,
            environment=cleaned.get("push_environment"),
            error=None,
        )
    return {
        "success": bool(result.get("success")),
        "push_supported": relay_configured(runtime),
        "push_registered": False,
        "push_environment": result.get("push_environment") or cleaned.get("push_environment"),
        "last_push_error": _clean_text(result.get("error"), 120) or None,
    }


async def async_status(
    hass: Any,
    runtime: Any,
    *,
    user_id: str | None,
    device_id: str | None,
    client_type: str | None,
) -> dict[str, Any]:
    """Return local relay capability/status without storing APNs tokens in HA."""
    del hass, user_id
    _remember_client_activity(runtime, device_id, client_type)
    status = _status_for(runtime, device_id, client_type)
    return {
        "push_supported": relay_configured(runtime) and _clean_client_type(client_type) in SUPPORTED_CLIENT_TYPES,
        "push_registered": bool(status.get("push_registered")),
        "push_environment": status.get("push_environment"),
        "last_push_error": _clean_text(status.get("last_push_error"), 120) or None,
    }


async def async_send_event(
    hass: Any,
    runtime: Any,
    *,
    user_id: str | None,
    event_type: str,
    history_revision: int | None = None,
    client_message_id: str | None = None,
    source_device_id: str | None = None,
    client_type: str | None = None,
    explicit_user_request: bool = False,
) -> dict[str, Any]:
    """Send a privacy-safe wake/sync event to the central push relay."""
    decision = should_send_push(
        runtime,
        user_id=user_id,
        event_type=event_type,
        source_device_id=source_device_id,
        client_type=client_type,
        explicit_user_request=explicit_user_request,
    )
    if not decision.get("send"):
        return {
            "success": True,
            "push_supported": relay_configured(runtime),
            "sent": 0,
            "disabled": bool(decision.get("disabled")),
            "suppressed": decision.get("reason"),
        }
    payload = build_relay_event_payload(
        runtime,
        user_id=user_id,
        event_type=event_type,
        history_revision=history_revision,
        client_message_id=client_message_id,
    )
    if not payload:
        return {"success": True, "push_supported": relay_configured(runtime), "sent": 0, "disabled": True}
    result = await _post_relay(hass, runtime, "/v1/push/event", payload)
    return {
        "success": True,
        "push_supported": relay_configured(runtime),
        "sent": int(bool(result.get("success"))),
        "errors": 0 if result.get("success") else 1,
        "disabled": bool(result.get("disabled")),
    }


def build_relay_event_payload(
    runtime: Any,
    *,
    user_id: str | None,
    event_type: str,
    history_revision: int | None = None,
    client_message_id: str | None = None,
) -> dict[str, Any]:
    """Build the small relay event payload; no prompts, responses or tokens."""
    event = _clean_text(event_type, 64)
    if event not in PUSHABLE_EVENTS:
        return {}
    payload: dict[str, Any] = {
        "ha_install_id": ensure_ha_install_id(runtime),
        "ha_user_hash": _hash_value(user_id) if user_id else None,
        "event_type": event,
        "open_target": "ask_dj",
        "client_types": sorted(SUPPORTED_CLIENT_TYPES),
    }
    if payload["ha_user_hash"] is None:
        payload.pop("ha_user_hash")
    if client_message_id:
        payload["client_message_id"] = _clean_text(client_message_id, 120)
    if history_revision is not None:
        try:
            payload["history_revision"] = int(history_revision)
        except (TypeError, ValueError):
            pass
    return payload


def should_send_push(
    runtime: Any,
    *,
    user_id: str | None,
    event_type: str,
    source_device_id: str | None = None,
    client_type: str | None = None,
    explicit_user_request: bool = False,
    now: float | None = None,
) -> dict[str, Any]:
    """Apply the strict DJConnect Ask DJ push policy before relay delivery."""
    event = _clean_text(event_type, 64)
    if event not in PUSHABLE_EVENTS:
        return {"send": False, "disabled": True, "reason": "event_not_pushable"}
    if event == EVENT_ASK_DJ_RESPONSE and not explicit_user_request:
        return {"send": False, "disabled": True, "reason": "not_explicit_user_request"}
    if _target_recently_active(runtime, source_device_id, client_type, now=now):
        return {"send": False, "disabled": True, "reason": "client_recently_active"}
    if _rate_limited(runtime, user_id, source_device_id, client_type, now=now):
        return {"send": False, "disabled": True, "reason": "rate_limited"}
    return {"send": True}


def relay_configured(runtime: Any | None = None) -> bool:
    """Return whether the central DJConnect API is configured."""
    return central_api_configured(runtime) if runtime is not None else False


def redact_push_token(value: Any) -> str:
    token = str(value or "")
    if len(token) <= 10:
        return "<redacted>"
    return f"{token[:4]}...{token[-4:]}"


async def _post_relay(
    hass: Any,
    runtime: Any,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        return await async_central_post(hass, runtime, path, payload)
    except DJConnectCentralApiError as exc:
        return {"success": False, "disabled": True, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect push relay request failed best-effort: %s", exc.__class__.__name__)
        return {"success": False, "error": "push_relay_unavailable"}


def _registration_payload(runtime: Any, *, user_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    device_id = _clean_text(payload.get("device_id"), 160)
    client_type = _clean_client_type(payload.get("client_type"))
    push_token = _clean_text(payload.get("push_token"), 4096)
    if not device_id or client_type not in SUPPORTED_CLIENT_TYPES or not push_token:
        return {}
    return {
        "ha_install_id": ensure_ha_install_id(runtime),
        "ha_user_hash": _hash_value(user_id),
        "device_id": device_id,
        "client_type": client_type,
        "push_token": push_token,
        "push_environment": _normalize_environment(payload.get("push_environment")),
        "app_bundle_id": _clean_text(payload.get("app_bundle_id"), 200),
        "app_version": _clean_text(payload.get("app_version"), 64),
        "locale": _clean_text(payload.get("locale"), 32),
        "notification_categories": _clean_categories(payload.get("notification_categories")),
    }


def _remember_bootstrap_proof(runtime: Any, payload: dict[str, Any]) -> None:
    proof = _clean_text(
        payload.get(CONF_CENTRAL_API_BOOTSTRAP_PROOF) or payload.get("bootstrap_proof"),
        4096,
    )
    if not proof:
        return
    status = getattr(runtime, "device_status", None)
    if not isinstance(status, dict):
        status = {}
        setattr(runtime, "device_status", status)
    status[CONF_CENTRAL_API_BOOTSTRAP_PROOF] = proof
    device_id = _clean_text(payload.get(CONF_DEVICE_ID) or payload.get("device_id"), 160)
    client_type = _clean_client_type(payload.get(CONF_CLIENT_TYPE) or payload.get("client_type"))
    if device_id:
        status[CONF_DEVICE_ID] = device_id
    if client_type:
        status[CONF_CLIENT_TYPE] = client_type
    expires_at = _clean_text(
        payload.get(CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT)
        or payload.get("bootstrap_proof_expires_at"),
        120,
    )
    if expires_at:
        status[CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT] = expires_at


def _remember_status(
    runtime: Any,
    device_id: Any,
    client_type: Any,
    *,
    registered: bool,
    environment: Any = None,
    error: Any = None,
) -> None:
    statuses = getattr(runtime, "push_status", None)
    if not isinstance(statuses, dict):
        statuses = {}
        setattr(runtime, "push_status", statuses)
    key = _status_key(device_id, client_type)
    statuses[key] = {
        "push_registered": bool(registered),
        "push_environment": _clean_text(environment, 32) or None,
        "last_push_error": _clean_text(error, 120) or None,
    }


def _remember_client_activity(runtime: Any, device_id: Any, client_type: Any) -> None:
    if not _clean_text(device_id, 160) or _clean_client_type(client_type) not in SUPPORTED_CLIENT_TYPES:
        return
    status = getattr(runtime, "device_status", None)
    if not isinstance(status, dict):
        status = {}
    active = _status_indicates_foreground(status)
    if not active and not any(key in status for key in _ACTIVITY_STATE_KEYS):
        return
    activity = getattr(runtime, "push_client_activity", None)
    if not isinstance(activity, dict):
        activity = {}
        setattr(runtime, "push_client_activity", activity)
    activity[_status_key(device_id, client_type)] = {
        "active": active,
        "updated_at": _now_monotonic(),
    }


_ACTIVITY_STATE_KEYS = {
    "foreground",
    "is_foreground",
    "app_foreground",
    "app_active",
    "client_active",
    "screen_active",
    "app_state",
    "scene_phase",
    "lifecycle_state",
}


def _status_indicates_foreground(status: dict[str, Any]) -> bool:
    for key in ("foreground", "is_foreground", "app_foreground", "app_active", "client_active", "screen_active"):
        if _boolish(status.get(key)):
            return True
    for key in ("app_state", "scene_phase", "lifecycle_state"):
        if str(status.get(key) or "").strip().lower() in {"active", "foreground", "visible", "resumed"}:
            return True
    return False


def _target_recently_active(
    runtime: Any,
    device_id: Any,
    client_type: Any,
    *,
    now: float | None = None,
) -> bool:
    activity = getattr(runtime, "push_client_activity", None)
    if not isinstance(activity, dict):
        return False
    item = activity.get(_status_key(device_id, client_type))
    if not isinstance(item, dict) or not item.get("active"):
        return False
    return (_now_monotonic(now) - float(item.get("updated_at") or 0)) <= RECENT_ACTIVE_SECONDS


def _rate_limited(runtime: Any, user_id: str | None, device_id: Any, client_type: Any, *, now: float | None = None) -> bool:
    timestamp = _now_monotonic(now)
    limits = getattr(runtime, "push_rate_limits", None)
    if not isinstance(limits, dict):
        limits = {}
        setattr(runtime, "push_rate_limits", limits)
    key = "|".join((_hash_value(user_id), _status_key(device_id, client_type)))
    recent = [item for item in limits.get(key, []) if timestamp - float(item) <= RATE_LIMIT_BURST_SECONDS]
    if recent and timestamp - recent[-1] < RATE_LIMIT_WINDOW_SECONDS:
        limits[key] = recent
        return True
    if len(recent) >= RATE_LIMIT_BURST_MAX:
        limits[key] = recent
        return True
    recent.append(timestamp)
    limits[key] = recent
    return False


def _status_for(runtime: Any, device_id: Any, client_type: Any) -> dict[str, Any]:
    statuses = getattr(runtime, "push_status", None)
    if not isinstance(statuses, dict):
        return {}
    return statuses.get(_status_key(device_id, client_type), {})


def _status_key(device_id: Any, client_type: Any) -> str:
    return f"{_clean_text(device_id, 160)}|{_clean_client_type(client_type)}"


def _hash_value(value: Any) -> str:
    return hashlib.sha256(str(value or "anonymous").encode()).hexdigest()


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "active", "foreground"}


def _now_monotonic(value: float | None = None) -> float:
    return float(value if value is not None else time.monotonic())


def _clean_client_type(value: Any) -> str:
    return _clean_text(value, 32).lower()


def _clean_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _clean_categories(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed = {EVENT_ASK_DJ_RESPONSE, EVENT_ASK_DJ_CONFIRM, EVENT_PLAYBACK_CHANGE}
    return sorted({_clean_text(item, 64) for item in value if _clean_text(item, 64) in allowed})


def _normalize_environment(value: Any) -> str:
    environment = str(value or "sandbox").strip().lower()
    return environment if environment in SUPPORTED_ENVIRONMENTS else "sandbox"
