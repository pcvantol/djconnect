"""Transport-neutral DJConnect API request handlers."""
from __future__ import annotations

from typing import Any

from . import http as http_helpers
from .const import CONF_CLIENT_TYPE, CONF_LOCAL_URL, VERSION
from .http import (
    ERROR_MESSAGES,
    _backend_unavailable_payload,
    _ha_version_payload,
    _handle_ask_dj_followup_response,
    _handle_ask_dj_play_recommendation,
    _handle_ask_dj_play_recommendation_on_output,
    _handle_ask_dj_play_request_on_output,
    _handle_volume_delta_command,
    _history_manager,
    _is_command_payload,
    _looks_like_backend_capability_error,
    _major_minor,
    _persist_paired_device,
    _playlist_command_value,
    _redact_debug_payload,
    _repeat_command_value,
    _runtime_firmware_version,
    _runtime_versions_compatible,
    _safe_backend_error_message,
    _shuffle_command_value,
    _unsupported_backend_capability_payload,
    _update_memory_metadata,
    _volume_delta_command_value,
    _with_playlist_aliases,
)
from .mood import enrich_payload_with_mood_zone
from .push import EVENT_ASK_DJ_CONFIRM, EVENT_ASK_DJ_RESPONSE
from .request_auth import (
    authorize_runtime_device_request,
    identity_payload,
    payload_client_type,
    resolve_runtime,
    runtime_client_type,
    validate_required_client_type,
)
from .spotify_backend import SpotifyBackendError
from .track_insight import TrackInsightError, TrackInsightService
from .use_cases import (
    MusicBackendCapabilityError,
    music_backend_metadata,
)

_LOGGER = http_helpers._LOGGER


async def async_handle_command_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Handle a DJConnect command payload for HTTP and HA websocket transports."""
    headers = headers or {}
    if not isinstance(data, dict):
        return _error_payload("invalid_json"), 400
    runtime = resolve_runtime(
        hass,
        data.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        return _error_payload("not_configured"), 503
    if not authorize_runtime_device_request(
        runtime,
        headers,
        data.get("device_id"),
        payload_client_type(data),
    ):
        return _error_payload("unauthorized"), 401
    client_type = validate_required_client_type(data)
    if client_type is None:
        return _error_payload("invalid_client_type"), 400
    if _is_command_payload(data):
        _LOGGER.debug("Ignoring command payload for device sensor update")
    runtime.device_status[CONF_CLIENT_TYPE] = client_type
    music_dna_key = await _update_memory_metadata(
        runtime,
        data,
        user_id=user_id,
    )
    if not _runtime_versions_compatible(runtime):
        return _version_mismatch_payload(runtime), 426
    header_device = headers.get("X-DJConnect-Device-ID")
    real_device_id = data.get("device_id") or header_device
    if real_device_id and getattr(runtime, "device_token", None):
        _persist_paired_device(
            hass,
            runtime,
            real_device_id,
            getattr(runtime, "device_status", {}).get(CONF_LOCAL_URL),
            runtime.device_token,
            getattr(runtime, "device_status", {}).get(CONF_CLIENT_TYPE),
        )
    command = str(data.get("command") or "").strip()
    if not command:
        return _error_payload("invalid_command"), 400
    _LOGGER.debug(
        "DJConnect backend command from %s client_type=%s command=%s",
        data.get("device_id"),
        client_type,
        command,
    )
    command_value = data.get("value")
    normalized_command = command.lower()
    if normalized_command == "set_repeat":
        command_value = _repeat_command_value(data)
    elif normalized_command == "set_shuffle":
        command_value = _shuffle_command_value(data)
    elif normalized_command == "volume_delta":
        command_value = _volume_delta_command_value(data)
    if normalized_command in {"status", "devices", "queue", "playlists"}:
        _LOGGER.debug(
            "DJConnect command request payload=%s",
            _redact_debug_payload(data),
        )
    if normalized_command == "playlists":
        command_value = _playlist_command_value(data, client_type)
        _LOGGER.debug(
            "DJConnect playlists request device_id=%s client_type=%s limit=%s",
            data.get("device_id"),
            client_type,
            command_value.get("limit"),
        )
    if normalized_command == "ask_dj_message":
        message_value = command_value if isinstance(command_value, dict) else {"text": command_value}
        text_value = str(
            message_value.get("text")
            or message_value.get("prompt")
            or data.get("text")
            or data.get("prompt")
            or data.get("label")
            or data.get("button_label")
            or data.get("title")
            or ""
        ).strip()
        if not text_value:
            return _error_payload("missing_ask_dj_text", "missing_ask_dj_text"), 400
        ask_payload = {
            **data,
            **message_value,
            "text": text_value,
            "client_type": client_type,
        }
        result = await http_helpers.async_handle_ask_dj(
            hass,
            runtime,
            ask_payload,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        return result, 200 if result.get("success") else 400
    if normalized_command == "ask_dj_play_recommendation":
        result = await _handle_ask_dj_play_recommendation(
            hass,
            runtime,
            command_value,
            data,
            user_id=user_id,
        )
        if isinstance(command_value, dict) and command_value.get("music_dna_key"):
            result["music_dna_key"] = str(command_value.get("music_dna_key") or "").strip()
        _decorate_command_result(hass, runtime, result, music_dna_key)
        return result, 200 if result.get("success") else 400
    if normalized_command == "ask_dj_play_recommendation_on_output":
        result = await _handle_ask_dj_play_recommendation_on_output(
            hass,
            runtime,
            command_value,
            data,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        return result, 200 if result.get("success") else 400
    if normalized_command == "ask_dj_play_request_on_output":
        result = await _handle_ask_dj_play_request_on_output(
            hass,
            runtime,
            command_value,
            data,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        return result, 200 if result.get("success") else 400
    if normalized_command == "ask_dj_followup_response":
        result = await _handle_ask_dj_followup_response(
            hass,
            runtime,
            command_value,
            data,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        return result, 200 if result.get("success") else 400
    if normalized_command == "volume_delta":
        result = await _handle_volume_delta_command(hass, runtime, command_value)
        _decorate_command_result(hass, runtime, result, music_dna_key)
        return result, 200 if result.get("success") else 400
    try:
        result = await http_helpers.run_music_command(
            hass,
            runtime,
            command,
            command_value,
            play=bool(data.get("play", False)),
        )
        runtime.update(last_error=None)
        if result.get("success"):
            result.setdefault("backend_available", True)
            runtime.device_status["backend_available"] = True
        _decorate_command_result(hass, runtime, result, music_dna_key)
        if normalized_command == "playlists":
            _with_playlist_aliases(result)
            _LOGGER.debug(
                "DJConnect playlists response device_id=%s client_type=%s count=%s",
                data.get("device_id"),
                client_type,
                result.get("count"),
            )
        if normalized_command in {"status", "devices", "queue", "playlists"}:
            _LOGGER.debug(
                "DJConnect command response payload=%s",
                _redact_debug_payload(result),
            )
        return result, 200
    except ValueError as exc:
        return _error_payload("invalid_command", str(exc)), 400
    except MusicBackendCapabilityError as exc:
        runtime.update(last_error=_safe_backend_error_message(exc))
        return _unsupported_backend_capability_payload(hass, runtime, exc), 400
    except SpotifyBackendError as exc:
        runtime.update(last_error=_safe_backend_error_message(exc))
        runtime.device_status["backend_available"] = False
        if normalized_command == "playlists":
            _LOGGER.debug(
                "DJConnect playlists backend unavailable device_id=%s client_type=%s reason=%s",
                data.get("device_id"),
                client_type,
                _safe_backend_error_message(exc),
            )
        return _backend_unavailable_payload(command, runtime, exc), 200
    except Exception as exc:  # noqa: BLE001
        if _looks_like_backend_capability_error(exc):
            runtime.update(last_error=_safe_backend_error_message(exc))
            return _unsupported_backend_capability_payload(hass, runtime, exc), 400
        _LOGGER.warning("DJConnect backend command failed: %s", _safe_backend_error_message(exc))
        runtime.update(last_error=_safe_backend_error_message(exc))
        runtime.device_status["backend_available"] = False
        if normalized_command == "playlists":
            _LOGGER.debug(
                "DJConnect playlists backend unavailable device_id=%s client_type=%s reason=%s",
                data.get("device_id"),
                client_type,
                _safe_backend_error_message(exc),
            )
        return _backend_unavailable_payload(command, runtime, exc), 200


async def async_handle_ask_dj_message_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Handle Ask DJ chat messages for HTTP and HA websocket transports."""
    headers = headers or {}
    if not isinstance(data, dict):
        return _error_payload("invalid_json"), 400
    identity = identity_payload(data)
    runtime = resolve_runtime(
        hass,
        identity.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        return _error_payload("not_configured"), 503
    client_type = validate_required_client_type(identity)
    if client_type is None:
        return _error_payload("invalid_client_type"), 400
    identity[CONF_CLIENT_TYPE] = client_type
    if not authorize_runtime_device_request(
        runtime,
        headers,
        identity.get("device_id"),
        client_type,
    ):
        return _error_payload("unauthorized"), 401
    payload = dict(data)
    payload.update({key: value for key, value in identity.items() if value is not None})
    payload = enrich_payload_with_mood_zone(payload)
    result = await http_helpers.async_handle_ask_dj(hass, runtime, payload, user_id=user_id)
    if not result.get("success"):
        return result, 500
    sync = await _history_manager(hass, runtime).async_append_exchange(
        user_id,
        payload,
        result,
    )
    event_type = (
        EVENT_ASK_DJ_CONFIRM
        if result.get("confirmation_actions")
        else EVENT_ASK_DJ_RESPONSE
    )
    await http_helpers.async_send_push_event(
        hass,
        runtime,
        user_id=user_id,
        event_type=event_type,
        history_revision=sync.get("history_revision"),
        client_message_id=payload.get("client_message_id"),
        source_device_id=identity.get("device_id"),
        client_type=identity.get("client_type"),
        explicit_user_request=True,
    )
    return {**result, **sync}, 200


async def async_handle_track_insight_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    source: str = "http",
) -> tuple[dict[str, Any], int]:
    """Handle Track Insight requests for HTTP and HA websocket transports."""
    headers = headers or {}
    if not isinstance(data, dict):
        return _error_payload("invalid_json"), 400
    identity = identity_payload(data)
    runtime = resolve_runtime(
        hass,
        identity.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        return _error_payload("not_configured"), 503
    try:
        result = await TrackInsightService().async_analyze(
            hass,
            runtime,
            data,
            source=source,
        )
    except TrackInsightError as exc:
        return exc.as_dict(), exc.status
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Track Insight %s failed: %s", source, exc)
        return _error_payload("track_insight_failed"), 500
    return result, 200


async def async_handle_ask_dj_history_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Return Ask DJ history for HTTP and HA websocket transports."""
    headers = headers or {}
    if not isinstance(data, dict):
        return _error_payload("invalid_json"), 400
    runtime, _identity, error, status = _authorized_history_runtime(hass, data, headers)
    if error:
        return _error_payload(error), status
    result = await _history_manager(hass, runtime).async_history(
        user_id,
        since_revision=_int_or_none(data.get("since_revision")),
    )
    return result, 200


async def async_handle_ask_dj_history_clear_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Clear Ask DJ history for HTTP and HA websocket transports."""
    headers = headers or {}
    if not isinstance(data, dict):
        return _error_payload("invalid_json"), 400
    runtime, _identity, error, status = _authorized_history_runtime(
        hass,
        data,
        headers,
        require_client_type=True,
    )
    if error:
        return _error_payload(error), status
    result = await _history_manager(hass, runtime).async_clear(user_id)
    return result, 200


async def async_handle_ask_dj_history_state_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Return compact Ask DJ history sync state for HTTP and HA websocket."""
    headers = headers or {}
    if not isinstance(data, dict):
        return _error_payload("invalid_json"), 400
    runtime, _identity, error, status = _authorized_history_runtime(
        hass,
        data,
        headers,
        require_client_type=True,
    )
    if error:
        return _error_payload(error), status
    result = await _history_manager(hass, runtime).async_history(
        user_id,
        since_revision=_int_or_none(data.get("since_revision")),
    )
    clear_revision = int(result.get("clear_revision") or 0)
    client_clear_revision = _int_or_none(data.get("clear_revision")) or 0
    return (
        {
            "success": True,
            "user_id": result.get("user_id"),
            "history_revision": result.get("history_revision"),
            "clear_revision": clear_revision,
            "history_limit": result.get("history_limit"),
            "history_trimmed_before": result.get("history_trimmed_before"),
            "history_trimmed_count": result.get("history_trimmed_count"),
            "ask_dj_clear_required": client_clear_revision < clear_revision,
            "server_time": result.get("server_time"),
        },
        200,
    )


def _decorate_command_result(
    hass: Any,
    runtime: Any,
    result: dict[str, Any],
    music_dna_key: str | None,
) -> None:
    if music_dna_key:
        result.setdefault("music_dna_key", music_dna_key)
    result.update(_ha_version_payload())
    result.update(music_backend_metadata(hass, runtime))


def _error_payload(error: str, message: str | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": error,
        "message": message or ERROR_MESSAGES.get(error, error),
    }


def _version_mismatch_payload(runtime: Any) -> dict[str, Any]:
    firmware_version = _runtime_firmware_version(runtime)
    return {
        "success": False,
        "error": "version_mismatch",
        "message": (
            "DJConnect Home Assistant integration and device firmware "
            "major.minor versions must match."
        ),
        "ha_version": VERSION,
        "ha_major_minor": _major_minor(VERSION),
        "firmware": firmware_version,
        "firmware_major_minor": _major_minor(firmware_version),
    }


def _authorized_history_runtime(
    hass: Any,
    data: dict[str, Any],
    headers: Any,
    *,
    require_client_type: bool = False,
) -> tuple[Any | None, dict[str, Any], str | None, int]:
    identity = identity_payload(data)
    runtime = resolve_runtime(
        hass,
        identity.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        return None, identity, "not_configured", 503
    if require_client_type:
        client_type = validate_required_client_type(identity)
        if client_type is None:
            return runtime, identity, "invalid_client_type", 400
    else:
        client_type = (
            identity.get("client_type")
            or headers.get("X-DJConnect-Client-Type")
            or runtime_client_type(runtime)
        )
    if not authorize_runtime_device_request(
        runtime,
        headers,
        identity.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        client_type,
    ):
        return runtime, identity, "unauthorized", 401
    return runtime, identity, None, 200


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
