"""Best-effort DJConnect push relay support for Apple clients."""
from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any

from .central_api import (
    DJConnectCentralApiError,
    async_ensure_install_token,
    async_post as async_central_post,
    central_api_configured,
    ensure_ha_install_id,
)
from .const import (
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_WATCHOS,
    CONF_CENTRAL_API_BOOTSTRAP_PROOF,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    CONF_LAST_PUSH_STATUS,
)

SUPPORTED_CLIENT_TYPES = {CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS}
SUPPORTED_ENVIRONMENTS = {"development", "production"}
RELAY_ENVIRONMENTS = {"sandbox", "production"}
ENVIRONMENT_ALIASES = {
    "sandbox": "development",
    "develop": "development",
    "dev": "development",
}
EVENT_ASK_DJ_RESPONSE = "ask_dj_response"
EVENT_ASK_DJ_CONFIRM = "ask_dj_confirm"
EVENT_MUSIC_DISCOVERY_READY = "music_discovery_ready"
EVENT_TEST_PUSH = "test_push"
EVENT_PLAYBACK_CHANGE = "playback_change"
PUSHABLE_EVENTS = {
    EVENT_ASK_DJ_RESPONSE,
    EVENT_ASK_DJ_CONFIRM,
    EVENT_MUSIC_DISCOVERY_READY,
    EVENT_TEST_PUSH,
}
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
        _log_registration_failure(runtime, payload, "invalid_push_registration")
        return {"success": False, "error": "invalid_push_registration"}
    incoming_proof = _clean_text(
        payload.get(CONF_CENTRAL_API_BOOTSTRAP_PROOF) or payload.get("bootstrap_proof"),
        4096,
    )
    _LOGGER.info(
        "DJConnect push register request: client_type=%s device_id=%s "
        "push_environment=%s app_bundle_id=%s app_version=%s locale=%s "
        "push_token_present=%s bootstrap_proof_present=%s "
        "install_token_present=%s ha_install_id_present=%s",
        cleaned.get("client_type") or "missing",
        cleaned.get("device_id") or "missing",
        cleaned.get("apns_environment") or "missing",
        cleaned.get("app_bundle_id") or "missing",
        cleaned.get("app_version") or "missing",
        cleaned.get("locale") or "missing",
        bool(cleaned.get("apns_token")),
        bool(incoming_proof),
        central_api_configured(runtime),
        bool(ensure_ha_install_id(runtime)),
    )
    _remember_registration_identity(runtime, payload)
    if not central_api_configured(runtime) and not incoming_proof:
        error = "missing_bootstrap_proof"
        response_environment = _response_environment(cleaned.get("apns_environment"))
        _remember_status(
            runtime,
            cleaned.get("device_id"),
            cleaned.get("client_type"),
            registered=False,
            environment=response_environment,
            error=error,
        )
        _persist_push_status(hass, runtime)
        _log_registration_failure(runtime, payload, error, cleaned=cleaned)
        return {
            "success": False,
            "push_supported": _push_supported(runtime, cleaned.get("client_type")),
            "push_registered": False,
            "push_environment": response_environment,
            "error": error,
            "last_push_error": error,
        }
    if incoming_proof and not central_api_configured(runtime):
        token_result = await async_ensure_install_token(
            hass,
            runtime,
            bootstrap_proof=incoming_proof,
            device_id=cleaned.get("device_id"),
            client_type=cleaned.get("client_type"),
        )
        if not token_result.get("success"):
            error = _clean_text(token_result.get("error"), 120) or "missing_install_token"
            response_environment = _response_environment(cleaned.get("apns_environment"))
            _remember_status(
                runtime,
                cleaned.get("device_id"),
                cleaned.get("client_type"),
                registered=False,
                environment=response_environment,
                error=error,
            )
            _persist_push_status(hass, runtime)
            _log_registration_failure(runtime, payload, error, cleaned=cleaned)
            return {
                "success": False,
                "push_supported": _push_supported(runtime, cleaned.get("client_type")),
                "push_registered": False,
                "push_environment": response_environment,
                "error": error,
                "last_push_error": error,
            }
    result = await _post_relay(hass, runtime, "/v1/push/register", cleaned)
    response_environment = _response_environment(cleaned.get("apns_environment"))
    if result.get("success"):
        _remember_status(
            runtime,
            cleaned.get("device_id"),
            cleaned.get("client_type"),
            registered=True,
            environment=response_environment,
            error=None,
        )
    else:
        error = _clean_text(result.get("error"), 120) or None
        _remember_status(
            runtime,
            cleaned.get("device_id"),
            cleaned.get("client_type"),
            registered=False,
            environment=response_environment,
            error=error,
        )
        _log_registration_failure(runtime, payload, error or "push_registration_failed", cleaned=cleaned)
    _persist_push_status(hass, runtime)
    return {
        "success": bool(result.get("success")),
        "push_supported": _push_supported(runtime, cleaned.get("client_type")),
        "push_registered": bool(result.get("success")),
        "push_environment": response_environment or _response_environment(result.get("push_environment")),
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
        _log_registration_failure(runtime, payload, "invalid_push_registration")
        return {"success": False, "error": "invalid_push_registration"}
    _remember_registration_identity(runtime, payload)
    result = await _post_relay(hass, runtime, "/v1/push/unregister", cleaned)
    response_environment = _response_environment(cleaned.get("apns_environment"))
    if result.get("success"):
        _remember_status(
            runtime,
            cleaned.get("device_id"),
            cleaned.get("client_type"),
            registered=False,
            environment=response_environment,
            error=None,
        )
        _persist_push_status(hass, runtime)
    return {
        "success": bool(result.get("success")),
        "push_supported": _push_supported(runtime, cleaned.get("client_type")),
        "push_registered": False,
        "push_environment": response_environment or _response_environment(result.get("apns_environment")),
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
    del user_id
    _remember_client_activity(runtime, device_id, client_type)
    status = _status_for(runtime, device_id, client_type)
    return {
        "push_supported": _push_supported(runtime, client_type),
        "push_registered": bool(status.get("push_registered")),
        "push_environment": status.get("push_environment"),
        "last_push_error": _clean_text(status.get("last_push_error"), 120) or None,
    }


async def async_bootstrap(
    hass: Any,
    runtime: Any,
    *,
    user_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Report that HA cannot mint Apple push bootstrap proofs."""
    del user_id
    cleaned = _bootstrap_payload(runtime, payload=payload)
    if not cleaned:
        _log_registration_failure(runtime, payload, "invalid_push_bootstrap")
        return {"success": False, "error": "invalid_push_bootstrap"}
    _remember_registration_identity(runtime, cleaned)
    status = _status_for(runtime, cleaned.get("device_id"), cleaned.get("client_type"))
    response_environment = _clean_text(cleaned.get("push_environment"), 32) or "sandbox"
    _remember_status(
        runtime,
        cleaned.get("device_id"),
        cleaned.get("client_type"),
        registered=False,
        environment=response_environment,
        error="bootstrap_proof_unavailable",
    )
    _persist_push_status(hass, runtime)
    _LOGGER.info(
        "DJConnect push bootstrap unavailable: client_type=%s device_id=%s "
        "push_environment=%s app_bundle_id=%s app_version=%s locale=%s "
        "bootstrap_proof_present=False install_token_present=%s "
        "ha_install_id_present=%s reason=bootstrap_proof_unavailable",
        cleaned.get("client_type") or "missing",
        cleaned.get("device_id") or "missing",
        response_environment,
        cleaned.get("app_bundle_id") or "missing",
        cleaned.get("app_version") or "missing",
        cleaned.get("locale") or "missing",
        central_api_configured(runtime),
        bool(ensure_ha_install_id(runtime)),
    )
    return {
        "success": False,
        "push_supported": _clean_client_type(cleaned.get("client_type")) in SUPPORTED_CLIENT_TYPES,
        "push_registered": bool(status.get("push_registered")),
        "push_environment": response_environment,
        "error": "bootstrap_proof_unavailable",
        "last_push_error": "bootstrap_proof_unavailable",
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
        reason = _clean_text(decision.get("reason"), 120) or None
        if reason in {"missing_bootstrap_proof", "missing_install_token"}:
            _remember_status(
                runtime,
                source_device_id,
                client_type,
                registered=False,
                error=reason,
            )
            _persist_push_status(hass, runtime)
            return {
                "success": False,
                "push_supported": relay_configured(runtime),
                "sent": 0,
                "errors": 1,
                "disabled": True,
                "error": reason,
                "last_push_error": reason,
            }
        return {
            "success": True,
            "push_supported": relay_configured(runtime),
            "sent": 0,
            "disabled": bool(decision.get("disabled")),
            "suppressed": reason,
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
    error = _clean_text(result.get("error"), 120) or None
    if result.get("success"):
        _remember_status(
            runtime,
            source_device_id,
            client_type,
            registered=True,
            error=None,
        )
        _persist_push_status(hass, runtime)
    else:
        _remember_status(
            runtime,
            source_device_id,
            client_type,
            registered=False,
            error=error,
        )
        _persist_push_status(hass, runtime)
    return {
        "success": bool(result.get("success")),
        "push_supported": relay_configured(runtime),
        "sent": int(bool(result.get("success"))),
        "errors": 0 if result.get("success") else 1,
        "disabled": bool(result.get("disabled")),
        "error": error,
        "last_push_error": error,
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
        "open_target": _open_target_for_event(event),
        "client_types": sorted(SUPPORTED_CLIENT_TYPES),
    }
    if event == EVENT_MUSIC_DISCOVERY_READY:
        payload.update(
            {
                "title": "DJConnect",
                "body": "Je nieuwe aanbevelingen staan klaar!",
                "deeplink": "djconnect://music-discovery",
                "refresh_target": "music_discovery",
            }
        )
    elif event == EVENT_TEST_PUSH:
        payload.update(
            {
                "title": "DJConnect",
                "body": "DJConnect pushberichten zijn actief.",
                "deeplink": "djconnect://ask-dj",
            }
        )
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


def _open_target_for_event(event: str) -> str:
    if event == EVENT_MUSIC_DISCOVERY_READY:
        return "music_discovery"
    return "ask_dj"


def should_send_push(
    runtime: Any,
    *,
    user_id: str | None,
    event_type: str,
    source_device_id: str | None = None,
    client_type: str | None = None,
    explicit_user_request: bool = False,
    now: float | None = None,
    consume_rate_limit: bool = True,
) -> dict[str, Any]:
    """Apply the strict DJConnect push policy before relay delivery."""
    event = _clean_text(event_type, 64)
    if event not in PUSHABLE_EVENTS:
        return {"send": False, "disabled": True, "reason": "event_not_pushable"}
    if event == EVENT_ASK_DJ_RESPONSE and not explicit_user_request:
        return {"send": False, "disabled": True, "reason": "not_explicit_user_request"}
    if not relay_configured(runtime):
        return {"send": False, "disabled": True, "reason": "missing_bootstrap_proof"}
    if _target_recently_active(runtime, source_device_id, client_type, now=now):
        return {"send": False, "disabled": True, "reason": "client_recently_active"}
    if consume_rate_limit and _rate_limited(runtime, user_id, source_device_id, client_type, now=now):
        return {"send": False, "disabled": True, "reason": "rate_limited"}
    return {"send": True}


def relay_configured(runtime: Any | None = None) -> bool:
    """Return whether the central DJConnect API is configured."""
    return central_api_configured(runtime) if runtime is not None else False


def _push_supported(runtime: Any, client_type: Any) -> bool:
    """Return whether this runtime/client type can use Apple push."""
    return relay_configured(runtime) and _clean_client_type(client_type) in SUPPORTED_CLIENT_TYPES


def _relay_ready_or_bootstrappable(runtime: Any) -> bool:
    """Return true when push has an install token."""
    return relay_configured(runtime)


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
    push_token = _clean_text(payload.get("apns_token") or payload.get("push_token"), 4096)
    push_environment = _clean_environment(payload.get("push_environment"))
    if (
        not _device_id_matches_client_type(device_id, client_type)
        or not _valid_push_token(push_token)
        or not push_environment
    ):
        return {}
    return {
        "ha_install_id": ensure_ha_install_id(runtime),
        "ha_user_hash": _hash_value(user_id),
        "device_id": device_id,
        "client_type": client_type,
        "apns_token": push_token,
        "apns_environment": _relay_environment(push_environment),
        "app_bundle_id": _clean_text(payload.get("app_bundle_id"), 200),
        "app_version": _clean_text(payload.get("app_version"), 64),
        "locale": _clean_text(payload.get("locale"), 32),
        "categories": _clean_categories(payload.get("categories") or payload.get("notification_categories")),
    }


def _bootstrap_payload(runtime: Any, *, payload: dict[str, Any]) -> dict[str, Any]:
    device_id = _clean_text(payload.get("device_id"), 160)
    client_type = _clean_client_type(payload.get("client_type"))
    push_environment = _clean_environment(payload.get("push_environment"))
    if not _device_id_matches_client_type(device_id, client_type):
        return {}
    return {
        "ha_install_id": ensure_ha_install_id(runtime),
        "device_id": device_id,
        "client_type": client_type,
        "push_environment": _relay_environment(push_environment) if push_environment else "sandbox",
        "app_bundle_id": _clean_text(payload.get("app_bundle_id"), 200),
        "app_version": _clean_text(payload.get("app_version"), 64),
        "locale": _clean_text(payload.get("locale"), 32),
    }


def _remember_registration_identity(runtime: Any, payload: dict[str, Any]) -> None:
    """Keep runtime identity aligned before central token bootstrap."""
    device_id = _clean_text(payload.get(CONF_DEVICE_ID) or payload.get("device_id"), 160)
    client_type = _clean_client_type(payload.get(CONF_CLIENT_TYPE) or payload.get("client_type"))
    if not device_id and not client_type:
        return
    status = getattr(runtime, "device_status", None)
    if not isinstance(status, dict):
        status = {}
        setattr(runtime, "device_status", status)
    if device_id:
        status[CONF_DEVICE_ID] = device_id
    if client_type:
        status[CONF_CLIENT_TYPE] = client_type


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


def _persist_push_status(hass: Any, runtime: Any) -> None:
    """Persist safe APNs registration status without APNs or install tokens."""
    entry = getattr(runtime, "entry", None)
    updater = getattr(getattr(hass, "config_entries", None), "async_update_entry", None)
    statuses = getattr(runtime, "push_status", None)
    if entry is None or not callable(updater) or not isinstance(statuses, dict):
        return
    safe_statuses = {
        str(key): {
            "push_registered": bool(item.get("push_registered")),
            "push_environment": _clean_text(item.get("push_environment"), 32) or None,
            "last_push_error": _clean_text(item.get("last_push_error"), 120) or None,
        }
        for key, item in statuses.items()
        if isinstance(item, dict)
    }
    data = dict(getattr(entry, "data", {}) or {})
    if data.get(CONF_LAST_PUSH_STATUS) == safe_statuses:
        return
    data[CONF_LAST_PUSH_STATUS] = safe_statuses
    try:
        updater(entry, data=data)
    except (KeyError, TypeError):
        try:
            setattr(entry, "data", data)
        except AttributeError:
            _LOGGER.debug("DJConnect could not persist APNs registration status")


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


def _device_id_matches_client_type(device_id: Any, client_type: Any) -> bool:
    normalized = _clean_text(device_id, 160)
    normalized_client = _clean_client_type(client_type)
    if normalized_client == CLIENT_TYPE_IOS:
        return bool(re.fullmatch(r"djconnect-ios-[A-Za-z0-9]{12}", normalized))
    if normalized_client == CLIENT_TYPE_MACOS:
        return bool(re.fullmatch(r"djconnect-macos-[A-Za-z0-9]{12}", normalized))
    if normalized_client == CLIENT_TYPE_WATCHOS:
        return bool(re.fullmatch(r"djconnect-watchos-[A-Za-z0-9]{12}", normalized))
    return False


def _valid_push_token(value: Any) -> bool:
    token = _clean_text(value, 4096)
    if not token:
        return False
    return not any(char.isspace() or char in "<>" for char in token)


def _clean_categories(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["ask_dj"]
    cleaned = {_clean_text(item, 64) for item in value}
    if "ask_dj" in cleaned or cleaned & {EVENT_ASK_DJ_RESPONSE, EVENT_ASK_DJ_CONFIRM}:
        return ["ask_dj"]
    return ["ask_dj"]


def _clean_environment(value: Any) -> str:
    environment = str(value or "").strip().lower()
    environment = ENVIRONMENT_ALIASES.get(environment, environment)
    return environment if environment in SUPPORTED_ENVIRONMENTS else ""


def _relay_environment(value: Any) -> str:
    environment = _clean_environment(value)
    if environment == "development":
        return "sandbox"
    return environment if environment in RELAY_ENVIRONMENTS else ""


def _response_environment(value: Any) -> str:
    environment = str(value or "").strip().lower()
    if environment == "sandbox":
        return "development"
    return _clean_environment(environment)


def _log_registration_failure(
    runtime: Any,
    payload: dict[str, Any],
    reason: str,
    *,
    cleaned: dict[str, Any] | None = None,
) -> None:
    """Log push registration failures without exposing APNs/proof/token values."""
    cleaned = cleaned or {}
    resolved_client_type = _clean_client_type(
        cleaned.get("client_type") or payload.get("client_type") or payload.get(CONF_CLIENT_TYPE)
    )
    resolved_device_id = _clean_text(
        cleaned.get("device_id") or payload.get("device_id") or payload.get(CONF_DEVICE_ID),
        160,
    )
    resolved_environment = _response_environment(
        cleaned.get("apns_environment") or payload.get("apns_environment") or payload.get("push_environment")
    )
    has_authorization = bool(_clean_text(payload.get("authorization") or payload.get("Authorization"), 4096))
    has_bootstrap_proof = bool(
        _clean_text(
            payload.get(CONF_CENTRAL_API_BOOTSTRAP_PROOF) or payload.get("bootstrap_proof"),
            4096,
        )
    )
    _LOGGER.info(
        "DJConnect push registration failed: client_type=%s device_id=%s "
        "push_environment=%s authorization_present=%s bootstrap_proof_present=%s reason=%s",
        resolved_client_type or "missing",
        resolved_device_id or "missing",
        resolved_environment or "missing",
        has_authorization,
        has_bootstrap_proof,
        _clean_text(reason, 120) or "unknown",
    )


def _runtime_config(runtime: Any) -> dict[str, Any]:
    config = getattr(runtime, "config", None)
    if isinstance(config, dict):
        return config
    entry = getattr(runtime, "entry", None) or getattr(runtime, "config_entry", None)
    data = dict(getattr(entry, "data", {}) or {})
    data.update(dict(getattr(entry, "options", {}) or {}))
    return data
