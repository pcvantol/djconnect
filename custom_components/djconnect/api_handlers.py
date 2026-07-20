"""Transport-neutral DJConnect API request handlers."""
from __future__ import annotations

import logging
from typing import Any

from . import http as http_helpers
from .const import CLIENT_TYPE_ESP32, CONF_CLIENT_TYPE, CONF_LOCAL_URL, VERSION
from .http import (
    ERROR_MESSAGES,
    _backend_unavailable_payload,
    _bootstrap_metadata,
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
from .profile_context import (
    ProfilePlatformNotConfigured,
    async_apply_profile_context,
    profile_error_payload,
    profile_storage,
)
from .profile_export import (
    async_clear_profile_personal_state,
    async_export_household,
    async_export_integration,
    async_export_profile,
    async_import_household,
    async_import_profile,
    profile_export_error_payload,
)
from .request_auth import (
    authorize_runtime_device_request,
    identity_payload,
    payload_client_type,
    resolve_runtime,
    runtime_client_type,
    validate_required_client_type,
)
from .spotify_backend import SpotifyBackendError
from .session_runtime import ActiveSessionExistsError, session_runtime_manager
from .track_insight import TrackInsightError, TrackInsightService
from .use_cases import (
    MusicBackendCapabilityError,
    music_backend_metadata,
    run_music_command,
)

_LOGGER = http_helpers._LOGGER
MUSIC_DNA_PROFILE_REFRESH_SECONDS = 60 * 60


async def _session_profile_context(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None,
    user_id: str | None,
    source: str,
) -> tuple[Any | None, Any | None, dict[str, Any] | None, int | None]:
    """Authenticate a session request and resolve its owning Profile."""
    headers = headers or {}
    runtime = resolve_runtime(hass, data.get("device_id") or headers.get("X-DJConnect-Device-ID"), headers)
    if runtime is None:
        return None, None, _error_payload("not_configured"), 503
    if not authorize_runtime_device_request(runtime, headers, data.get("device_id"), payload_client_type(data)):
        return None, None, _error_payload("unauthorized"), 401
    if validate_required_client_type(data) is None:
        return None, None, _error_payload("invalid_client_type"), 400
    profile_error, profile_status = await _apply_profile_or_error(
        hass, runtime, data, user_id=user_id, source=source
    )
    if profile_error is not None:
        return None, None, profile_error, profile_status
    from .profile_context import async_resolve_request_context

    try:
        context = await async_resolve_request_context(
            hass, runtime, data, user_id=user_id, request_source=source
        )
    except Exception as exc:  # noqa: BLE001
        result, status = profile_error_payload(exc)
        return None, None, result, status
    return runtime, context, None, None


async def async_handle_session_start_payload(
    hass: Any, data: dict[str, Any], *, headers: Any | None = None, user_id: str | None = None
) -> tuple[dict[str, Any], int]:
    """Create the one active server-owned Runtime for a resolved Profile."""
    runtime, context, error, status = await _session_profile_context(
        hass, data, headers=headers, user_id=user_id, source="session_start"
    )
    if error is not None:
        return error, int(status or 400)
    if not context.backend_id:
        return _error_payload("profile_backend_missing"), 409
    try:
        session = await session_runtime_manager(hass).async_start(
            owner_profile_id=context.profile_id,
            room=str(data.get("room") or context.room_id or "").strip(),
            selected_mood=str(data.get("mood") or "").strip(),
            music_backend=context.backend_id,
        )
    except ActiveSessionExistsError:
        active = await session_runtime_manager(hass).async_get_active(context.profile_id)
        return {"success": False, "error": "active_session_exists", "active_session": active.as_dict() if active else None}, 409
    return {"success": True, "session": session.as_dict()}, 201


async def async_handle_session_end_payload(
    hass: Any, data: dict[str, Any], *, headers: Any | None = None, user_id: str | None = None
) -> tuple[dict[str, Any], int]:
    """End and dispose of the active Runtime for a resolved Profile."""
    _runtime, context, error, status = await _session_profile_context(
        hass, data, headers=headers, user_id=user_id, source="session_end"
    )
    if error is not None:
        return error, int(status or 400)
    session = await session_runtime_manager(hass).async_end(
        owner_profile_id=context.profile_id, session_id=str(data.get("session_id") or "").strip()
    )
    if session is None:
        return _error_payload("active_session_not_found"), 404
    return {"success": True, "session": session.as_dict()}, 200


async def async_handle_active_session_payload(
    hass: Any, data: dict[str, Any], *, headers: Any | None = None, user_id: str | None = None
) -> tuple[dict[str, Any], int]:
    """Return the active Runtime so a paired client can reconnect."""
    _runtime, context, error, status = await _session_profile_context(
        hass, data, headers=headers, user_id=user_id, source="active_session"
    )
    if error is not None:
        return error, int(status or 400)
    session = await session_runtime_manager(hass).async_get_active(context.profile_id)
    return {"success": True, "session": session.as_dict() if session else None}, 200


async def _apply_profile_or_error(
    hass: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None,
    source: str,
) -> tuple[dict[str, Any] | None, int | None]:
    """Apply canonical Profile context or return structured error."""
    _clear_profile_runtime_context(runtime)
    try:
        await async_apply_profile_context(
            hass,
            runtime,
            payload,
            user_id=user_id,
            request_source=source,
        )
        return None, None
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, ProfilePlatformNotConfigured):
            return None, None
        result, status = profile_error_payload(exc)
        return result, status


def _clear_profile_runtime_context(runtime: Any) -> None:
    """Clear transient profile routing hints before resolving a request."""
    setattr(runtime, "profile_context_profile_id", "")
    setattr(runtime, "profile_context_backend_id", "")
    setattr(runtime, "profile_context_music_account_id", "")
    setattr(runtime, "profile_context_playback_zone_id", "")
    setattr(runtime, "profile_context_resolution_reason", "")


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
        _debug_playback_error("command", {}, (_error_payload("invalid_json"), 400))
        return _error_payload("invalid_json"), 400
    runtime = resolve_runtime(
        hass,
        data.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        _debug_playback_error("command", data, (_error_payload("not_configured"), 503))
        return _error_payload("not_configured"), 503
    if not authorize_runtime_device_request(
        runtime,
        headers,
        data.get("device_id"),
        payload_client_type(data),
    ):
        _debug_playback_error("command", data, (_error_payload("unauthorized"), 401))
        return _error_payload("unauthorized"), 401
    client_type = validate_required_client_type(data)
    if client_type is None:
        _debug_playback_error("command", data, (_error_payload("invalid_client_type"), 400), runtime=runtime)
        return _error_payload("invalid_client_type"), 400
    if _is_command_payload(data):
        _LOGGER.debug("Ignoring command payload for device sensor update")
    runtime.device_status[CONF_CLIENT_TYPE] = client_type
    _refresh_authenticated_client_version(runtime, data)
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        data,
        user_id=user_id,
        source="command",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    privacy_policy = getattr(runtime, "profile_context_privacy_policy", None)
    if getattr(privacy_policy, "allow_music_dna_persistence", True):
        music_dna_key = await _update_memory_metadata(
            runtime,
            data,
            user_id=user_id,
        )
    else:
        music_dna_key = str(data.get("music_dna_key") or "").strip() or None
    if not _runtime_versions_compatible(runtime):
        result = _version_mismatch_payload(runtime)
        _debug_playback_result("command", result, 426, runtime=runtime, command="version_mismatch")
        return result, 426
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
        _debug_playback_error("command", data, (_error_payload("invalid_command"), 400), runtime=runtime)
        return _error_payload("invalid_command"), 400
    _LOGGER.debug(
        "DJConnect backend command from %s client_type=%s command=%s",
        _safe_debug_identifier(data.get("device_id")),
        client_type,
        command,
    )
    command_value = data.get("value")
    normalized_command = command.lower()
    _debug_playback_request(runtime, data, command=normalized_command)
    if normalized_command == "queue":
        _debug_queue_request(runtime, data)
    if normalized_command in {"help", "hulp", "commands", "show_help", "show_commands"}:
        ask_payload = {
            **data,
            "text": command,
            "client_type": client_type,
        }
        result = await http_helpers.async_handle_ask_dj(
            hass,
            runtime,
            ask_payload,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        status = 200 if result.get("success") else 400
        _debug_playback_result("command", result, status, runtime=runtime, command=normalized_command)
        return result, status
    if normalized_command == "set_repeat":
        command_value = _repeat_command_value(data)
    elif normalized_command == "set_shuffle":
        command_value = _shuffle_command_value(data)
    elif normalized_command == "volume_delta":
        command_value = _volume_delta_command_value(data)
    if normalized_command == "playlists":
        command_value = _playlist_command_value(data, client_type)
        _debug_playlists_request(runtime, data, command_value)
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
            _debug_playback_error("command", data, (_error_payload("missing_ask_dj_text", "missing_ask_dj_text"), 400), runtime=runtime)
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
        status = 200 if result.get("success") else 400
        _debug_playback_result("command", result, status, runtime=runtime, command=normalized_command)
        return result, status
    current_track_text = _current_track_question_text(data, command, command_value)
    if current_track_text:
        ask_payload = {
            **data,
            "text": current_track_text,
            "client_type": client_type,
            "audio_response": data.get("audio_response") or "auto",
        }
        result = await http_helpers.async_handle_ask_dj(
            hass,
            runtime,
            ask_payload,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        status = 200 if result.get("success") else 400
        _debug_playback_result("command", result, status, runtime=runtime, command="current_track_question")
        return result, status
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
        status = 200 if result.get("success") else 400
        _debug_playback_result("command", result, status, runtime=runtime, command=normalized_command)
        return result, status
    if normalized_command == "ask_dj_play_recommendation_on_output":
        result = await _handle_ask_dj_play_recommendation_on_output(
            hass,
            runtime,
            command_value,
            data,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        status = 200 if result.get("success") else 400
        _debug_playback_result("command", result, status, runtime=runtime, command=normalized_command)
        return result, status
    if normalized_command == "ask_dj_play_request_on_output":
        result = await _handle_ask_dj_play_request_on_output(
            hass,
            runtime,
            command_value,
            data,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        status = 200 if result.get("success") else 400
        _debug_playback_result("command", result, status, runtime=runtime, command=normalized_command)
        return result, status
    if normalized_command == "ask_dj_followup_response":
        result = await _handle_ask_dj_followup_response(
            hass,
            runtime,
            command_value,
            data,
            user_id=user_id,
        )
        _decorate_command_result(hass, runtime, result, music_dna_key)
        status = 200 if result.get("success") else 400
        _debug_playback_result("command", result, status, runtime=runtime, command=normalized_command)
        return result, status
    if normalized_command == "volume_delta":
        result = await _handle_volume_delta_command(hass, runtime, command_value)
        _decorate_command_result(hass, runtime, result, music_dna_key)
        status = 200 if result.get("success") else 400
        _debug_playback_result("command", result, status, runtime=runtime, command=normalized_command)
        return result, status
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
        if normalized_command in {"set_current_track_favorite", "toggle_current_track_favorite"}:
            await _record_removed_favorite_in_music_dna(runtime, result, data, user_id=user_id)
        _decorate_command_result(hass, runtime, result, music_dna_key)
        if normalized_command == "playlists":
            if client_type == CLIENT_TYPE_ESP32:
                _with_esp32_playlist_aliases(result)
            else:
                _with_playlist_aliases(result)
            _debug_playlists_result(result, 200, runtime=runtime)
        if normalized_command == "queue":
            _debug_queue_result(result, 200, runtime=runtime)
        _debug_playback_result("command", result, 200, runtime=runtime, command=normalized_command)
        return result, 200

    except ValueError as exc:
        result = _error_payload("invalid_command", str(exc))
        if normalized_command == "playlists":
            _debug_playlists_result(result, 400, runtime=runtime)
        if normalized_command == "queue":
            _debug_queue_result(result, 400, runtime=runtime)
        _debug_playback_result("command", result, 400, runtime=runtime, command=normalized_command)
        return result, 400
    except MusicBackendCapabilityError as exc:
        runtime.update(last_error=_safe_backend_error_message(exc))
        result = _unsupported_backend_capability_payload(hass, runtime, exc)
        if normalized_command == "playlists":
            _debug_playlists_result(result, 400, runtime=runtime)
        if normalized_command == "queue":
            _debug_queue_result(result, 400, runtime=runtime)
        _debug_playback_result("command", result, 400, runtime=runtime, command=normalized_command)
        return result, 400
    except SpotifyBackendError as exc:
        runtime.update(last_error=_safe_backend_error_message(exc))
        runtime.device_status["backend_available"] = False
        if normalized_command == "playlists":
            _debug_playlists_backend_error(data, exc, runtime=runtime)
        result = _backend_unavailable_payload(command, runtime, exc)
        if normalized_command == "playlists":
            _debug_playlists_result(result, 200, runtime=runtime)
        if normalized_command == "queue":
            _debug_queue_result(result, 200, runtime=runtime)
        _debug_playback_result("command", result, 200, runtime=runtime, command=normalized_command)
        return result, 200
    except Exception as exc:  # noqa: BLE001
        if _looks_like_backend_capability_error(exc):
            runtime.update(last_error=_safe_backend_error_message(exc))
            result = _unsupported_backend_capability_payload(hass, runtime, exc)
            if normalized_command == "playlists":
                _debug_playlists_result(result, 400, runtime=runtime)
            if normalized_command == "queue":
                _debug_queue_result(result, 400, runtime=runtime)
            _debug_playback_result("command", result, 400, runtime=runtime, command=normalized_command)
            return result, 400
        _LOGGER.warning("DJConnect backend command failed: %s", _safe_backend_error_message(exc))
        runtime.update(last_error=_safe_backend_error_message(exc))
        runtime.device_status["backend_available"] = False
        if normalized_command == "playlists":
            _debug_playlists_backend_error(data, exc, runtime=runtime)
        result = _backend_unavailable_payload(command, runtime, exc)
        if normalized_command == "playlists":
            _debug_playlists_result(result, 200, runtime=runtime)
        if normalized_command == "queue":
            _debug_queue_result(result, 200, runtime=runtime)
        _debug_playback_result("command", result, 200, runtime=runtime, command=normalized_command)
        return result, 200


def _with_esp32_playlist_aliases(result: dict[str, Any]) -> dict[str, Any]:
    """Expose playlist aliases for firmware without duplicating large payloads."""
    playlists = [
        _esp32_playlist_item(item)
        for item in http_helpers._playlist_items_from_result(result)
        if isinstance(item, dict)
    ]
    result["playlists"] = playlists
    result["items"] = playlists
    result["count"] = len(playlists)
    for key in ("data", "result"):
        container = result.get(key)
        if isinstance(container, dict) and not any(
            nested in container for nested in ("items", "playlists")
        ):
            continue
        result.pop(key, None)
    return result


def _esp32_playlist_item(item: dict[str, Any]) -> dict[str, Any]:
    """Return the compact playlist fields the ESP firmware reads."""
    name = str(
        item.get("name")
        or item.get("title")
        or item.get("display_title")
        or item.get("displayTitle")
        or ""
    ).strip()
    owner = str(
        item.get("owner")
        or item.get("owner_name")
        or item.get("subtitle")
        or item.get("creator")
        or ""
    ).strip()
    uri = str(
        item.get("uri")
        or item.get("playlist_uri")
        or item.get("playlistUri")
        or item.get("media_content_id")
        or item.get("mediaContentId")
        or item.get("value")
        or item.get("id")
        or ""
    ).strip()
    image_url = str(
        item.get("image_url")
        or item.get("imageUrl")
        or item.get("album_image_url")
        or item.get("albumImageUrl")
        or item.get("entity_picture")
        or item.get("thumbnail_url")
        or ""
    ).strip()
    compact = {
        "name": name,
        "owner": owner,
        "uri": uri,
    }
    if image_url:
        compact["image_url"] = image_url
    return compact


def _current_track_question_text(data: dict[str, Any], command: str, value: Any) -> str:
    for candidate in (
        command,
        data.get("text"),
        data.get("prompt"),
        data.get("query"),
        data.get("title"),
        value,
    ):
        text = _text_candidate(candidate)
        if text and _is_current_track_question_text(text):
            return text
    if isinstance(value, dict):
        for key in ("text", "prompt", "query", "title"):
            text = _text_candidate(value.get(key))
            if text and _is_current_track_question_text(text):
                return text
    return ""


def _text_candidate(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or value.get("prompt") or value.get("query") or value.get("title") or "").strip()
    return str(value or "").strip()


def _is_current_track_question_text(value: str) -> bool:
    normalized = " ".join(str(value or "").lower().strip(" ?.!'\"").split())
    return normalized in {
        "wat speelt er",
        "wat speelt er nu",
        "wat speelt nu",
        "wat draait er",
        "wat draait er nu",
        "hoe heet dit nummer",
        "welk liedje is dit",
        "welk nummer speelt er",
        "welk nummer speelt nu",
        "welke track speelt er",
        "welke track hoor ik",
        "what is playing",
        "what's playing",
        "whats playing",
        "what song is playing",
        "what track is playing",
        "current song",
        "current track",
    }


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
        _debug_ask_dj_error("message", {}, (_error_payload("invalid_json"), 400))
        return _error_payload("invalid_json"), 400
    identity = identity_payload(data)
    runtime = resolve_runtime(
        hass,
        identity.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        _debug_ask_dj_error("message", data, (_error_payload("not_configured"), 503))
        return _error_payload("not_configured"), 503
    client_type = validate_required_client_type(identity)
    if client_type is None:
        _debug_ask_dj_error("message", data, (_error_payload("invalid_client_type"), 400), runtime=runtime)
        return _error_payload("invalid_client_type"), 400
    identity[CONF_CLIENT_TYPE] = client_type
    if not authorize_runtime_device_request(
        runtime,
        headers,
        identity.get("device_id"),
        client_type,
    ):
        _debug_ask_dj_error("message", data, (_error_payload("unauthorized"), 401), runtime=runtime)
        return _error_payload("unauthorized"), 401
    payload = dict(data)
    payload.update({key: value for key, value in identity.items() if value is not None})
    payload = enrich_payload_with_mood_zone(payload)
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="ask_dj_message",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_ask_dj_request("message", runtime, payload, user_id=user_id)
    result = await http_helpers.async_handle_ask_dj(hass, runtime, payload, user_id=user_id)
    if not result.get("success"):
        _debug_ask_dj_result("message", result, 500, runtime=runtime)
        return result, 500
    privacy_policy = getattr(runtime, "profile_context_privacy_policy", None)
    if getattr(privacy_policy, "allow_history_persistence", True):
        sync = await _history_manager(hass, runtime).async_append_exchange(
            user_id,
            payload,
            result,
        )
    else:
        sync = {
            "success": True,
            "history_revision": None,
            "clear_revision": None,
            "messages": [],
            "history_persisted": False,
            "privacy_mode": str(payload.get("profile_privacy_mode") or ""),
        }
    event_type = (
        EVENT_ASK_DJ_CONFIRM
        if result.get("confirmation_actions")
        else EVENT_ASK_DJ_RESPONSE
    )
    if sync.get("history_persisted", True):
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
            announcement=result.get("announcement") if isinstance(result, dict) else None,
        )
    response = {**result, **sync}
    _debug_ask_dj_result("message", response, 200, runtime=runtime)
    return response, 200


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
        _debug_track_insight_error("request", {}, (_error_payload("invalid_json"), 400), source=source)
        return _error_payload("invalid_json"), 400
    identity = identity_payload(data)
    runtime = resolve_runtime(
        hass,
        identity.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        _debug_track_insight_error("request", data, (_error_payload("not_configured"), 503), source=source)
        return _error_payload("not_configured"), 503
    client_type = validate_required_client_type(identity)
    if client_type is None:
        _debug_track_insight_error("request", data, (_error_payload("invalid_client_type"), 400), runtime=runtime, source=source)
        return _error_payload("invalid_client_type"), 400
    identity[CONF_CLIENT_TYPE] = client_type
    if not authorize_runtime_device_request(
        runtime,
        headers,
        identity.get("device_id"),
        client_type,
    ):
        _debug_track_insight_error("request", data, (_error_payload("unauthorized"), 401), runtime=runtime, source=source)
        return _error_payload("unauthorized"), 401
    payload = dict(data)
    payload.update({key: value for key, value in identity.items() if value is not None})
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=None,
        source=f"track_insight:{source}",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    for header_name, payload_key in (
        ("X-DJConnect-Language", "language"),
        ("X-DJConnect-Locale", "locale"),
        ("Accept-Language", "locale"),
        ("X-DJConnect-Mood", "mood"),
    ):
        value = headers.get(header_name) if hasattr(headers, "get") else None
        if value and not payload.get(payload_key):
            payload[payload_key] = str(value).split(",", 1)[0].strip()
    _debug_track_insight_request(runtime, payload, source=source)
    try:
        result = await TrackInsightService().async_analyze(
            hass,
            runtime,
            payload,
            source=source,
        )
    except TrackInsightError as exc:
        _debug_track_insight_error("result", payload, (exc.as_dict(), exc.status), runtime=runtime, source=source)
        return exc.as_dict(), exc.status
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug(
            "DJConnect Track Insight %s failed client_type=%s device_id=%s error=%s",
            source,
            payload_client_type(payload) or runtime_client_type(runtime),
            _safe_debug_identifier(payload.get("device_id")),
            exc.__class__.__name__,
        )
        return _error_payload("track_insight_failed"), 500
    _debug_track_insight_result(result, 200, runtime=runtime, source=source)
    return result, 200


async def async_handle_ask_dj_idle_suggestion_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Return and append an Ask DJ idle suggestion for HTTP and websocket transports."""
    headers = headers or {}
    if not isinstance(data, dict):
        return _error_payload("invalid_json"), 400
    runtime = resolve_runtime(
        hass,
        data.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        _debug_ask_dj_error("idle_suggestion", data, (_error_payload("not_configured"), 503))
        return _error_payload("not_configured"), 503
    client_type = validate_required_client_type(identity_payload(data))
    if client_type is None:
        _debug_ask_dj_error("idle_suggestion", data, (_error_payload("invalid_client_type"), 400), runtime=runtime)
        return _error_payload("invalid_client_type"), 400
    if not authorize_runtime_device_request(
        runtime,
        headers,
        data.get("device_id"),
        client_type,
    ):
        _debug_ask_dj_error("idle_suggestion", data, (_error_payload("unauthorized"), 401), runtime=runtime)
        return _error_payload("unauthorized"), 401
    payload = dict(data)
    payload[CONF_CLIENT_TYPE] = client_type
    payload = enrich_payload_with_mood_zone(payload)
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="ask_dj_idle_suggestion",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_ask_dj_request("idle_suggestion", runtime, payload, user_id=user_id)
    result = await http_helpers.async_idle_suggestion(
        hass,
        runtime,
        payload,
        user_id=user_id,
    )
    if not result.get("success"):
        _debug_ask_dj_result("idle_suggestion", result, 500, runtime=runtime)
        return result, 500
    sync = await _history_manager(hass, runtime).async_append_assistant_message(
        user_id,
        payload,
        result,
    )
    response = {**result, **sync}
    _debug_ask_dj_result("idle_suggestion", response, 200, runtime=runtime)
    return response, 200


async def async_handle_music_dna_profile_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Return the structured Music DNA profile for a client/user."""
    runtime, payload, error = _music_dna_runtime_payload(hass, data, headers)
    if error is not None:
        _debug_music_dna_error("profile", data, error)
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_dna_profile",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_music_dna_request("profile", runtime, payload, user_id=user_id)
    privacy_policy = getattr(runtime, "profile_context_privacy_policy", None)
    if not getattr(privacy_policy, "allow_personal_read", True):
        return {
            "success": True,
            "music_dna_key": payload.get("music_dna_key"),
            "enabled": False,
            "generation": 0,
            "profile": {},
            "redacted": True,
            "privacy_mode": payload.get("profile_privacy_mode"),
        }, 200
    memory = getattr(runtime, "memory", None)
    profile_getter = getattr(memory, "async_profile", None)
    if not callable(profile_getter):
        _debug_music_dna_error("profile", payload, (_error_payload("music_dna_unavailable"), 503), runtime=runtime)
        return _error_payload("music_dna_unavailable"), 503
    result = await profile_getter(runtime, payload, user_id=user_id)
    if result.get("enabled") and await _refresh_music_dna_profile_if_stale(
        hass,
        runtime,
        payload,
        user_id=user_id,
    ):
        result = await profile_getter(runtime, payload, user_id=user_id)
    _debug_music_dna_result("profile", result, 200, runtime=runtime)
    return result, 200


async def async_handle_music_dna_settings_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Update the Music DNA opt-in setting for a client/user."""
    runtime, payload, error = _music_dna_runtime_payload(hass, data, headers)
    if error is not None:
        _debug_music_dna_error("settings", data, error)
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_dna_settings",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_music_dna_request("settings", runtime, payload, user_id=user_id)
    privacy_policy = getattr(runtime, "profile_context_privacy_policy", None)
    if not getattr(privacy_policy, "allow_music_dna_persistence", True):
        return {
            "success": False,
            "error": "profile_privacy_blocks_persistence",
            "message": "Profile privacy mode blocks Music DNA persistence.",
        }, 403
    if "enabled" not in payload:
        _debug_music_dna_error("settings", payload, (_error_payload("missing_enabled"), 400), runtime=runtime)
        return _error_payload("missing_enabled"), 400
    memory = getattr(runtime, "memory", None)
    setter = getattr(memory, "async_set_enabled", None)
    if not callable(setter):
        _debug_music_dna_error("settings", payload, (_error_payload("music_dna_unavailable"), 503), runtime=runtime)
        return _error_payload("music_dna_unavailable"), 503
    result = await setter(runtime, bool(payload.get("enabled")), payload, user_id=user_id)
    _debug_music_dna_result("settings", result, 200, runtime=runtime)
    return result, 200


async def async_handle_music_dna_clear_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Clear Music DNA knowledge while preserving the current opt-in setting."""
    runtime, payload, error = _music_dna_runtime_payload(hass, data, headers)
    if error is not None:
        _debug_music_dna_error("clear", data, error)
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_dna_clear",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_music_dna_request("clear", runtime, payload, user_id=user_id)
    memory = getattr(runtime, "memory", None)
    if memory is None or not callable(getattr(memory, "async_context_for_runtime", None)):
        _debug_music_dna_error("clear", payload, (_error_payload("music_dna_unavailable"), 503), runtime=runtime)
        return _error_payload("music_dna_unavailable"), 503
    context = await memory.async_context_for_runtime(runtime, payload, user_id=user_id)
    key = context.get("music_dna_key") or payload.get("music_dna_key")
    await memory.async_clear(str(key) if key else None)
    result = await memory.async_profile(runtime, payload, user_id=user_id)
    _debug_music_dna_result("clear", result, 200, runtime=runtime)
    return result, 200


async def async_handle_music_dna_import_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Import and overwrite Music DNA profile data for a client/user."""
    runtime, payload, error = _music_dna_runtime_payload(hass, data, headers)
    if error is not None:
        _debug_music_dna_error("import", data, error)
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_dna_import",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_music_dna_request("import", runtime, payload, user_id=user_id)
    memory = getattr(runtime, "memory", None)
    importer = getattr(memory, "async_import_profile", None)
    if not callable(importer):
        _debug_music_dna_error("import", payload, (_error_payload("music_dna_unavailable"), 503), runtime=runtime)
        return _error_payload("music_dna_unavailable"), 503
    result, status = await importer(runtime, payload, user_id=user_id)
    _debug_music_dna_result("import", result, status, runtime=runtime)
    return result, status


async def async_handle_music_dna_export_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Export Music DNA profile data for a client/user."""
    runtime, payload, error = _music_dna_runtime_payload(hass, data, headers)
    if error is not None:
        _debug_music_dna_error("export", data, error)
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_dna_export",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_music_dna_request("export", runtime, payload, user_id=user_id)
    memory = getattr(runtime, "memory", None)
    exporter = getattr(memory, "async_export_profile", None)
    if not callable(exporter):
        _debug_music_dna_error("export", payload, (_error_payload("music_dna_unavailable"), 503), runtime=runtime)
        return _error_payload("music_dna_unavailable"), 503
    result = await exporter(runtime, payload, user_id=user_id)
    _debug_music_dna_result("export", result, 200, runtime=runtime)
    return result, 200


def _music_dna_runtime_payload(
    hass: Any,
    data: dict[str, Any],
    headers: Any | None,
) -> tuple[Any | None, dict[str, Any], tuple[dict[str, Any], int] | None]:
    headers = headers or {}
    if not isinstance(data, dict):
        return None, {}, (_error_payload("invalid_json"), 400)
    payload = dict(data)
    identity = identity_payload(payload)
    device_id = identity.get("device_id") or headers.get("X-DJConnect-Device-ID")
    runtime = resolve_runtime(hass, device_id, headers)
    if runtime is None:
        return None, payload, (_error_payload("not_configured"), 503)
    if not authorize_runtime_device_request(
        runtime,
        headers,
        identity.get("device_id"),
        payload_client_type(identity),
    ):
        return None, payload, (_error_payload("unauthorized"), 401)
    payload.update({key: value for key, value in identity.items() if value})
    return runtime, payload, None


def _discovery_runtime_payload(
    hass: Any,
    data: dict[str, Any],
    headers: Any | None,
) -> tuple[Any | None, dict[str, Any], tuple[dict[str, Any], int] | None]:
    """Resolve and authorize a music discovery runtime payload."""
    return _music_dna_runtime_payload(hass, data, headers)


async def _refresh_music_dna_profile_if_stale(
    hass: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None,
) -> bool:
    memory = getattr(runtime, "memory", None)
    freshness = getattr(memory, "async_listening_profile_is_fresh", None)
    updater = getattr(memory, "async_update_listening_profile", None)
    if not callable(freshness) or not callable(updater):
        return False
    try:
        if await freshness(
            runtime,
            payload,
            user_id=user_id,
            ttl_seconds=MUSIC_DNA_PROFILE_REFRESH_SECONDS,
        ):
            return False
        result = await run_music_command(
            hass,
            runtime,
            "listening_profile",
        )
        profile = result.get("profile") if isinstance(result, dict) else {}
        if not isinstance(profile, dict) or not profile:
            return False
        await updater(runtime, profile, payload, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug(
            "DJConnect Music DNA profile refresh skipped: %s",
            exc.__class__.__name__,
        )
        return False
    _LOGGER.debug(
        "DJConnect Music DNA profile refreshed from backend listening profile client_type=%s device_id=%s",
        payload.get(CONF_CLIENT_TYPE),
        payload.get("device_id"),
    )
    return True


def _debug_music_dna_request(
    endpoint: str,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    _LOGGER.debug(
        "DJConnect Music DNA %s request client_type=%s device_id=%s music_dna_key=%s user_id=%s enabled_requested=%s import_format=%s profile_keys=%s",
        endpoint,
        payload_client_type(payload) or runtime_client_type(runtime),
        _safe_debug_identifier(payload.get("device_id") or getattr(runtime, "device_status", {}).get("device_id")),
        _safe_debug_identifier(payload.get("music_dna_key")),
        _safe_debug_identifier(user_id),
        payload.get("enabled") if endpoint == "settings" else None,
        _safe_import_format(payload),
        _safe_profile_keys(payload) if endpoint == "import" else [],
    )


def _debug_music_dna_result(
    endpoint: str,
    result: dict[str, Any],
    status: int,
    *,
    runtime: Any | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    profile = _music_dna_profile_from_result(endpoint, result)
    _LOGGER.debug(
        "DJConnect Music DNA %s result status=%s success=%s enabled=%s generation=%s music_dna_key=%s client_type=%s profile_summary=%s error=%s",
        endpoint,
        status,
        result.get("success") if isinstance(result, dict) else None,
        _music_dna_enabled_from_result(endpoint, result),
        _music_dna_generation_from_result(endpoint, result),
        _safe_debug_identifier(_music_dna_key_from_result(endpoint, result)),
        runtime_client_type(runtime) if runtime is not None else None,
        _profile_debug_summary(profile),
        result.get("error") if isinstance(result, dict) else None,
    )


def _debug_music_dna_error(
    endpoint: str,
    payload: dict[str, Any] | Any,
    error: tuple[dict[str, Any], int],
    *,
    runtime: Any | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    body, status = error
    data = payload if isinstance(payload, dict) else {}
    _LOGGER.debug(
        "DJConnect Music DNA %s rejected status=%s error=%s client_type=%s device_id=%s music_dna_key=%s",
        endpoint,
        status,
        body.get("error") if isinstance(body, dict) else None,
        payload_client_type(data) or (runtime_client_type(runtime) if runtime is not None else None),
        _safe_debug_identifier(data.get("device_id")),
        _safe_debug_identifier(data.get("music_dna_key")),
    )


def _music_dna_profile_from_result(endpoint: str, result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    if endpoint == "export":
        exported = result.get("profile")
        return exported.get("profile") if isinstance(exported, dict) and isinstance(exported.get("profile"), dict) else {}
    profile = result.get("profile")
    return profile if isinstance(profile, dict) else {}


def _music_dna_enabled_from_result(endpoint: str, result: dict[str, Any]) -> bool | None:
    if not isinstance(result, dict):
        return None
    if endpoint == "export":
        profile = result.get("profile")
        return profile.get("enabled") if isinstance(profile, dict) else None
    return result.get("enabled")


def _music_dna_generation_from_result(endpoint: str, result: dict[str, Any]) -> Any:
    if not isinstance(result, dict):
        return None
    if endpoint == "export":
        profile = result.get("profile")
        return profile.get("generation") if isinstance(profile, dict) else None
    return result.get("generation")


def _music_dna_key_from_result(endpoint: str, result: dict[str, Any]) -> Any:
    if not isinstance(result, dict):
        return None
    if endpoint == "export":
        profile = result.get("profile")
        return profile.get("music_dna_key") if isinstance(profile, dict) else None
    return result.get("music_dna_key")


def _profile_debug_summary(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict) or not profile:
        return {}
    summary: dict[str, Any] = {"keys": sorted(str(key) for key in profile.keys())[:12]}
    for key in (
        "recent_tracks",
        "favorite_artists",
        "favorite_tracks",
        "top_artists",
        "top_tracks",
        "moods",
        "genres",
        "listening_contexts",
    ):
        value = profile.get(key)
        if isinstance(value, (list, tuple, set, dict)):
            summary[f"{key}_count"] = len(value)
    return summary


def _safe_profile_keys(payload: dict[str, Any]) -> list[str]:
    profile = payload.get("profile")
    if isinstance(profile, dict) and profile.get("format") == "djconnect.music_dna.export":
        profile = profile.get("profile")
    if isinstance(profile, dict) and isinstance(profile.get("profile"), dict):
        profile = profile.get("profile")
    if not isinstance(profile, dict):
        return []
    return sorted(str(key) for key in profile.keys())[:12]


def _safe_import_format(payload: dict[str, Any]) -> str:
    profile = payload.get("profile")
    if isinstance(profile, dict):
        return str(profile.get("format") or "").strip()[:64]
    return ""


def _safe_debug_identifier(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "***"
    return f"{text[:8]}...{text[-4:]}"


def _debug_ask_dj_request(
    endpoint: str,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    text = str(payload.get("text") or payload.get("prompt") or payload.get("query") or "").strip()
    _LOGGER.debug(
        "DJConnect Ask DJ %s request client_type=%s device_id=%s user_id=%s client_message_id=%s text_length=%s input_type=%s audio_response=%s mood_zone=%s since_revision=%s clear_revision=%s",
        endpoint,
        payload_client_type(payload) or runtime_client_type(runtime),
        _safe_debug_identifier(payload.get("device_id") or getattr(runtime, "device_status", {}).get("device_id")),
        _safe_debug_identifier(user_id),
        _safe_debug_identifier(payload.get("client_message_id")),
        len(text),
        str(payload.get("input_type") or "").strip()[:24],
        str(payload.get("audio_response") or "").strip()[:24],
        str(payload.get("mood_zone") or "").strip()[:24],
        _int_or_none(payload.get("since_revision")),
        _int_or_none(payload.get("clear_revision")),
    )


def _debug_ask_dj_result(
    endpoint: str,
    result: dict[str, Any],
    status: int,
    *,
    runtime: Any | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    _LOGGER.debug(
        "DJConnect Ask DJ %s result status=%s success=%s intent=%s action=%s audio=%s images=%s links=%s sources=%s playback_actions=%s confirmation_actions=%s messages=%s items=%s history_revision=%s clear_revision=%s trimmed_count=%s error=%s client_type=%s",
        endpoint,
        status,
        result.get("success") if isinstance(result, dict) else None,
        _intent_name(result.get("intent") if isinstance(result, dict) else None),
        str(result.get("action") or "").strip()[:48] if isinstance(result, dict) else "",
        bool((result or {}).get("audio_url") or _assistant_message_value(result, "audio_url")),
        _count(result.get("images")) if isinstance(result, dict) else 0,
        _count(result.get("links")) if isinstance(result, dict) else 0,
        _count(result.get("sources")) if isinstance(result, dict) else 0,
        _count(result.get("playback_actions")) if isinstance(result, dict) else 0,
        _count(result.get("confirmation_actions")) if isinstance(result, dict) else 0,
        _count(result.get("messages")) if isinstance(result, dict) else 0,
        _count(result.get("items")) if isinstance(result, dict) else 0,
        result.get("history_revision") if isinstance(result, dict) else None,
        result.get("clear_revision") if isinstance(result, dict) else None,
        result.get("history_trimmed_count") if isinstance(result, dict) else None,
        result.get("error") if isinstance(result, dict) else None,
        runtime_client_type(runtime) if runtime is not None else None,
    )


def _debug_ask_dj_error(
    endpoint: str,
    payload: dict[str, Any] | Any,
    error: tuple[dict[str, Any], int],
    *,
    runtime: Any | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    body, status = error
    data = payload if isinstance(payload, dict) else {}
    _LOGGER.debug(
        "DJConnect Ask DJ %s rejected status=%s error=%s client_type=%s device_id=%s client_message_id=%s",
        endpoint,
        status,
        body.get("error") if isinstance(body, dict) else None,
        payload_client_type(data) or (runtime_client_type(runtime) if runtime is not None else None),
        _safe_debug_identifier(data.get("device_id")),
        _safe_debug_identifier(data.get("client_message_id")),
    )


def _intent_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("intent") or value.get("name") or "").strip()[:64]
    return str(value or "").strip()[:64]


def _assistant_message_value(result: dict[str, Any] | Any, key: str) -> Any:
    if not isinstance(result, dict):
        return None
    message = result.get("assistant_message")
    return message.get(key) if isinstance(message, dict) else None


def _count(value: Any) -> int:
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return 0


def _debug_track_insight_request(
    runtime: Any,
    payload: dict[str, Any],
    *,
    source: str,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    _LOGGER.debug(
        "DJConnect Track Insight %s request client_type=%s device_id=%s source=%s title_present=%s artist_present=%s entity_present=%s force_refresh=%s locale=%s mood_zone=%s include_visual_profile=%s include_raw_response=%s",
        source,
        payload_client_type(payload) or runtime_client_type(runtime),
        _safe_debug_identifier(payload.get("device_id") or getattr(runtime, "device_status", {}).get("device_id")),
        str(payload.get("source") or source or "").strip()[:32],
        bool(str(payload.get("title") or "").strip()),
        bool(str(payload.get("artist") or "").strip()),
        bool(str(payload.get("entity_id") or payload.get("player_id") or "").strip()),
        bool(payload.get("force_refresh")),
        str(payload.get("locale") or payload.get("language") or "").strip()[:24],
        str(payload.get("mood_zone") or "").strip()[:24],
        payload.get("include_visual_profile"),
        payload.get("include_raw_response"),
    )


def _debug_track_insight_result(
    result: dict[str, Any],
    status: int,
    *,
    runtime: Any | None = None,
    source: str,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    track = result.get("track") if isinstance(result, dict) else {}
    analysis = result.get("analysis") if isinstance(result, dict) else {}
    cache = result.get("cache") if isinstance(result, dict) else {}
    visual = result.get("visual_profile") if isinstance(result, dict) else None
    _LOGGER.debug(
        "DJConnect Track Insight %s result status=%s success=%s backend=%s language=%s cache_hit=%s cache_key=%s analysis_keys=%s visual_profile=%s genre_present=%s production_notes=%s listening_cues=%s similar_tracks=%s error=%s client_type=%s",
        source,
        status,
        result.get("success", True) if isinstance(result, dict) else None,
        track.get("backend") if isinstance(track, dict) else None,
        result.get("language") if isinstance(result, dict) else None,
        cache.get("hit") if isinstance(cache, dict) else None,
        _safe_debug_identifier(cache.get("key") if isinstance(cache, dict) else None),
        sorted(str(key) for key in analysis.keys())[:16] if isinstance(analysis, dict) else [],
        isinstance(visual, dict),
        bool(analysis.get("genre") or analysis.get("subgenre")) if isinstance(analysis, dict) else False,
        _count(analysis.get("production_notes")) if isinstance(analysis, dict) else 0,
        _count(analysis.get("listening_cues")) if isinstance(analysis, dict) else 0,
        _count(analysis.get("similar_tracks")) if isinstance(analysis, dict) else 0,
        result.get("error") if isinstance(result, dict) else None,
        runtime_client_type(runtime) if runtime is not None else None,
    )


def _debug_track_insight_error(
    phase: str,
    payload: dict[str, Any] | Any,
    error: tuple[dict[str, Any], int],
    *,
    runtime: Any | None = None,
    source: str,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    body, status = error
    data = payload if isinstance(payload, dict) else {}
    _LOGGER.debug(
        "DJConnect Track Insight %s rejected phase=%s status=%s error=%s client_type=%s device_id=%s title_present=%s artist_present=%s",
        source,
        phase,
        status,
        body.get("error") if isinstance(body, dict) else None,
        payload_client_type(data) or (runtime_client_type(runtime) if runtime is not None else None),
        _safe_debug_identifier(data.get("device_id")),
        bool(str(data.get("title") or "").strip()),
        bool(str(data.get("artist") or "").strip()),
    )


def _debug_playback_request(
    runtime: Any,
    payload: dict[str, Any],
    *,
    command: str,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    backend = music_backend_metadata(None, runtime)
    _LOGGER.debug(
        "DJConnect playback command request command=%s client_type=%s device_id=%s backend=%s backend_available=%s play=%s value_shape=%s output_requested=%s mood_zone=%s",
        command,
        payload_client_type(payload) or runtime_client_type(runtime),
        _safe_debug_identifier(payload.get("device_id") or getattr(runtime, "device_status", {}).get("device_id")),
        backend.get("music_backend"),
        backend.get("music_backend_available"),
        bool(payload.get("play", False)),
        _playback_value_shape(payload.get("value")),
        _has_output_selection(payload.get("value")),
        str(payload.get("mood_zone") or "").strip()[:24],
    )


def _debug_playback_result(
    endpoint: str,
    result: dict[str, Any],
    status: int,
    *,
    runtime: Any | None = None,
    command: str,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    playback = result.get("playback") if isinstance(result, dict) else {}
    backend = music_backend_metadata(None, runtime) if runtime is not None else {}
    _LOGGER.debug(
        "DJConnect playback %s result command=%s status=%s success=%s backend=%s backend_available=%s playback_state=%s has_playback=%s is_playing=%s devices=%s queue_items=%s playlists=%s playback_actions=%s error=%s client_type=%s",
        endpoint,
        command,
        status,
        result.get("success") if isinstance(result, dict) else None,
        (result.get("music_backend") or backend.get("music_backend")) if isinstance(result, dict) else backend.get("music_backend"),
        result.get("backend_available") if isinstance(result, dict) else backend.get("music_backend_available"),
        _safe_playback_state(playback.get("state") if isinstance(playback, dict) else None),
        playback.get("has_playback") if isinstance(playback, dict) else None,
        playback.get("is_playing") if isinstance(playback, dict) else None,
        _count(result.get("devices")) if isinstance(result, dict) else 0,
        _queue_count(result),
        _playlist_count(result),
        _count(result.get("playback_actions")) if isinstance(result, dict) else 0,
        result.get("error") if isinstance(result, dict) else None,
        runtime_client_type(runtime) if runtime is not None else None,
    )


def _debug_playback_error(
    endpoint: str,
    payload: dict[str, Any] | Any,
    error: tuple[dict[str, Any], int],
    *,
    runtime: Any | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    body, status = error
    data = payload if isinstance(payload, dict) else {}
    _LOGGER.debug(
        "DJConnect playback %s rejected status=%s error=%s command=%s client_type=%s device_id=%s",
        endpoint,
        status,
        body.get("error") if isinstance(body, dict) else None,
        str(data.get("command") or "").strip()[:48],
        payload_client_type(data) or (runtime_client_type(runtime) if runtime is not None else None),
        _safe_debug_identifier(data.get("device_id")),
    )


def _debug_queue_request(runtime: Any, payload: dict[str, Any]) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    backend = music_backend_metadata(None, runtime)
    _LOGGER.debug(
        "DJConnect queue endpoint request client_type=%s device_id=%s backend=%s backend_available=%s value_shape=%s",
        payload_client_type(payload) or runtime_client_type(runtime),
        _safe_debug_identifier(payload.get("device_id") or getattr(runtime, "device_status", {}).get("device_id")),
        backend.get("music_backend"),
        backend.get("music_backend_available"),
        _playback_value_shape(payload.get("value")),
    )


def _debug_queue_result(
    result: dict[str, Any],
    status: int,
    *,
    runtime: Any | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    queue = _queue_payload(result)
    playback = result.get("playback") if isinstance(result, dict) else {}
    backend = music_backend_metadata(None, runtime) if runtime is not None else {}
    _LOGGER.debug(
        "DJConnect queue endpoint result status=%s success=%s backend=%s backend_available=%s queue_items=%s context_present=%s current_present=%s playback_state=%s error=%s client_type=%s",
        status,
        result.get("success") if isinstance(result, dict) else None,
        (result.get("music_backend") or backend.get("music_backend")) if isinstance(result, dict) else backend.get("music_backend"),
        result.get("backend_available") if isinstance(result, dict) else backend.get("music_backend_available"),
        _queue_count(result),
        _queue_context_present(result, queue),
        _queue_current_present(queue),
        _safe_playback_state(playback.get("state") if isinstance(playback, dict) else None),
        result.get("error") if isinstance(result, dict) else None,
        runtime_client_type(runtime) if runtime is not None else None,
    )


def _debug_playlists_request(
    runtime: Any,
    payload: dict[str, Any],
    command_value: dict[str, Any],
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    backend = music_backend_metadata(None, runtime)
    _LOGGER.debug(
        "DJConnect playlists endpoint request client_type=%s device_id=%s backend=%s backend_available=%s limit=%s has_client_context=%s value_shape=%s",
        payload_client_type(payload) or runtime_client_type(runtime),
        _safe_debug_identifier(payload.get("device_id") or getattr(runtime, "device_status", {}).get("device_id")),
        backend.get("music_backend"),
        backend.get("music_backend_available"),
        _safe_int(command_value.get("limit")),
        _playlist_client_context_present(command_value),
        _playback_value_shape(payload.get("value")),
    )


def _debug_playlists_result(
    result: dict[str, Any],
    status: int,
    *,
    runtime: Any | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    backend = music_backend_metadata(None, runtime) if runtime is not None else {}
    _LOGGER.debug(
        "DJConnect playlists endpoint result status=%s success=%s backend=%s backend_available=%s playlists=%s count=%s aliases_present=%s error=%s client_type=%s",
        status,
        result.get("success") if isinstance(result, dict) else None,
        (result.get("music_backend") or backend.get("music_backend")) if isinstance(result, dict) else backend.get("music_backend"),
        result.get("backend_available") if isinstance(result, dict) else backend.get("music_backend_available"),
        _playlist_count(result),
        _safe_int(result.get("count")) if isinstance(result, dict) else None,
        _playlist_aliases_present(result),
        result.get("error") if isinstance(result, dict) else None,
        runtime_client_type(runtime) if runtime is not None else None,
    )


def _debug_playlists_backend_error(
    payload: dict[str, Any],
    exc: Exception,
    *,
    runtime: Any | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    _LOGGER.debug(
        "DJConnect playlists endpoint backend unavailable client_type=%s device_id=%s reason=%s",
        payload_client_type(payload) or (runtime_client_type(runtime) if runtime is not None else None),
        _safe_debug_identifier(payload.get("device_id")),
        _safe_backend_error_message(exc),
    )


def _playback_value_shape(value: Any) -> str:
    if isinstance(value, dict):
        unsafe_fragments = (
            "token",
            "secret",
            "password",
            "authorization",
            "uri",
            "url",
            "text",
            "prompt",
            "query",
            "title",
            "artist",
            "album",
            "name",
            "label",
            "subtitle",
        )
        safe_keys = [
            key
            for key in sorted(str(key) for key in value.keys())
            if not any(fragment in key.lower() for fragment in unsafe_fragments)
        ]
        return "dict:" + ",".join(safe_keys[:10])
    if isinstance(value, list):
        return f"list:{len(value)}"
    if value in (None, ""):
        return "empty"
    return type(value).__name__


def _has_output_selection(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(str(value.get(key) or "").strip() for key in ("device_id", "device_name", "output_id", "output_name", "target_player_id"))


def _safe_playback_state(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"playing", "paused", "stopped", "idle", "off"} else ""


def _queue_count(result: dict[str, Any] | Any) -> int:
    if not isinstance(result, dict):
        return 0
    for key in ("queue", "items", "tracks"):
        value = result.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for nested_key in ("items", "queue", "tracks"):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return len(nested)
    return 0


def _queue_payload(result: dict[str, Any] | Any) -> Any:
    if not isinstance(result, dict):
        return None
    value = result.get("queue")
    if isinstance(value, dict):
        return value
    status = result.get("status")
    if isinstance(status, dict) and isinstance(status.get("queue"), dict):
        return status["queue"]
    return value


def _queue_context_present(result: dict[str, Any] | Any, queue: Any) -> bool:
    if isinstance(queue, dict):
        for key in ("context", "queue_context", "context_uri", "contextUri"):
            if str(queue.get(key) or "").strip():
                return True
    if isinstance(result, dict):
        for key in ("context", "queue_context", "context_uri", "contextUri"):
            if str(result.get(key) or "").strip():
                return True
    return False


def _queue_current_present(queue: Any) -> bool:
    if isinstance(queue, dict):
        return bool(queue.get("currently_playing") or queue.get("current"))
    return False


def _playlist_count(result: dict[str, Any] | Any) -> int:
    if not isinstance(result, dict):
        return 0
    if isinstance(result.get("playlists"), list):
        return len(result["playlists"])
    if isinstance(result.get("playlists"), dict):
        playlists = result["playlists"]
        for key in ("items", "playlists"):
            value = playlists.get(key)
            if isinstance(value, list):
                return len(value)
    for key in ("items",):
        value = result.get(key)
        if isinstance(value, list):
            return len(value)
    for container_key in ("data", "result"):
        container = result.get(container_key)
        if isinstance(container, dict):
            count = _playlist_count(container)
            if count:
                return count
    count = result.get("count")
    try:
        return int(count) if count is not None else 0
    except (TypeError, ValueError):
        return 0


def _playlist_aliases_present(result: dict[str, Any] | Any) -> bool:
    if not isinstance(result, dict):
        return False
    return any(key in result for key in ("playlists", "items", "data", "result"))


def _playlist_client_context_present(value: dict[str, Any] | Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(
        str(value.get(key) or "").strip()
        for key in ("client_type", "device_id", "market", "locale")
    )


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


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
        _debug_ask_dj_error("history", {}, (_error_payload("invalid_json"), 400))
        return _error_payload("invalid_json"), 400
    runtime, identity, error, status = _authorized_history_runtime(hass, data, headers)
    if error:
        _debug_ask_dj_error("history", data, (_error_payload(error), status), runtime=runtime)
        return _error_payload(error), status
    payload = {**data, **identity}
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="ask_dj_history",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_ask_dj_request("history", runtime, payload, user_id=user_id)
    result = await _history_manager(hass, runtime).async_history(
        user_id,
        since_revision=_int_or_none(payload.get("since_revision")),
    )
    _decorate_profile_response(result, payload)
    _debug_ask_dj_result("history", result, 200, runtime=runtime)
    return result, 200


async def async_handle_ask_dj_history_export_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Export Ask DJ history for HTTP client downloads."""
    headers = headers or {}
    if not isinstance(data, dict):
        _debug_ask_dj_error("history_export", {}, (_error_payload("invalid_json"), 400))
        return _error_payload("invalid_json"), 400
    runtime, identity, error, status = _authorized_history_runtime(hass, data, headers)
    if error:
        _debug_ask_dj_error("history_export", data, (_error_payload(error), status), runtime=runtime)
        return _error_payload(error), status
    payload = {**data, **identity}
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="ask_dj_history_export",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_ask_dj_request("history_export", runtime, payload, user_id=user_id)
    history = await _history_manager(hass, runtime).async_history(user_id)
    response = {
        "success": True,
        "format": "djconnect.ask_dj.history.export",
        "schema_version": 1,
        "exported_at": history.get("server_time"),
        "exported_by_client_type": (
            identity.get("client_type")
            or headers.get("X-DJConnect-Client-Type")
            or runtime_client_type(runtime)
        ),
        "app_version": payload.get("app_version")
        or payload.get("version")
        or headers.get("X-DJConnect-App-Version"),
        **history,
    }
    _decorate_profile_response(response, payload)
    _debug_ask_dj_result("history_export", response, 200, runtime=runtime)
    return response, 200


async def async_handle_music_discovery_feed_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Return Music Discovery feed for HTTP and websocket transports."""
    from .music_discovery import async_handle_music_discovery_feed_payload as handler
    runtime, payload, error = _discovery_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_discovery_feed",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    return await handler(hass, payload, headers=headers, user_id=user_id)


async def async_handle_music_discovery_refresh_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Refresh Music Discovery feed for HTTP and websocket transports."""
    from .music_discovery import async_handle_music_discovery_refresh_payload as handler
    runtime, payload, error = _discovery_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_discovery_refresh",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    return await handler(hass, payload, headers=headers, user_id=user_id)


async def async_handle_music_discovery_play_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Play Music Discovery item for HTTP and websocket transports."""
    from .music_discovery import async_handle_music_discovery_play_payload as handler
    runtime, payload, error = _discovery_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_discovery_play",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    return await handler(hass, payload, headers=headers, user_id=user_id)


async def async_handle_music_discovery_feedback_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Record Music Discovery feedback for HTTP and websocket transports."""
    from .music_discovery import async_handle_music_discovery_feedback_payload as handler
    runtime, payload, error = _discovery_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="music_discovery_feedback",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    return await handler(hass, payload, headers=headers, user_id=user_id)


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
        _debug_ask_dj_error("history_clear", {}, (_error_payload("invalid_json"), 400))
        return _error_payload("invalid_json"), 400
    runtime, identity, error, status = _authorized_history_runtime(
        hass,
        data,
        headers,
        require_client_type=True,
    )
    if error:
        _debug_ask_dj_error("history_clear", data, (_error_payload(error), status), runtime=runtime)
        return _error_payload(error), status
    payload = {**data, **identity}
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="ask_dj_history_clear",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_ask_dj_request("history_clear", runtime, payload, user_id=user_id)
    result = await _history_manager(hass, runtime).async_clear(user_id)
    _decorate_profile_response(result, payload)
    _debug_ask_dj_result("history_clear", result, 200, runtime=runtime)
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
        _debug_ask_dj_error("history_state", {}, (_error_payload("invalid_json"), 400))
        return _error_payload("invalid_json"), 400
    runtime, identity, error, status = _authorized_history_runtime(
        hass,
        data,
        headers,
        require_client_type=True,
    )
    if error:
        _debug_ask_dj_error("history_state", data, (_error_payload(error), status), runtime=runtime)
        return _error_payload(error), status
    payload = {**data, **identity}
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="ask_dj_history_state",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    _debug_ask_dj_request("history_state", runtime, payload, user_id=user_id)
    result = await _history_manager(hass, runtime).async_history(
        user_id,
        since_revision=_int_or_none(payload.get("since_revision")),
    )
    clear_revision = int(result.get("clear_revision") or 0)
    client_clear_revision = _int_or_none(payload.get("clear_revision")) or 0
    response = {
        "success": True,
        "user_id": result.get("user_id"),
        "history_revision": result.get("history_revision"),
        "clear_revision": clear_revision,
        "history_limit": result.get("history_limit"),
        "history_trimmed_before": result.get("history_trimmed_before"),
        "history_trimmed_count": result.get("history_trimmed_count"),
        "ask_dj_clear_required": client_clear_revision < clear_revision,
        "server_time": result.get("server_time"),
    }
    _decorate_profile_response(response, payload)
    _debug_ask_dj_result("history_state", response, 200, runtime=runtime)
    return response, 200


def _decorate_profile_response(result: dict[str, Any], payload: dict[str, Any]) -> None:
    """Attach resolved Profile metadata to an existing response payload."""
    profile_id = str(payload.get("profile_id") or "").strip()
    if profile_id:
        result.setdefault("profile_id", profile_id)
    music_dna_key = str(payload.get("music_dna_key") or "").strip()
    if music_dna_key:
        result.setdefault("music_dna_key", music_dna_key)


async def async_handle_profile_export_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Export a single resolved Profile without secrets."""
    runtime, payload, error = _profile_operation_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="profile_export",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    try:
        result = await async_export_profile(
            profile_storage(hass),
            str(payload.get("profile_id") or ""),
            include_personal_data=bool(payload.get("include_personal_data", True)),
        )
        _decorate_profile_response(result, payload)
        return result, 200
    except Exception as exc:  # noqa: BLE001
        return profile_export_error_payload(exc)


async def async_handle_household_export_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Export household Profile Platform metadata without secrets."""
    runtime, payload, error = _profile_operation_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="household_export",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    try:
        result = await async_export_household(profile_storage(hass))
        _decorate_profile_response(result, payload)
        return result, 200
    except Exception as exc:  # noqa: BLE001
        return profile_export_error_payload(exc)


async def async_handle_integration_export_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Export a full non-secret DJConnect integration envelope."""
    runtime, payload, error = _profile_operation_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="integration_export",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    try:
        result = await async_export_integration(
            profile_storage(hass),
            non_secret_config=getattr(runtime, "config", {}),
        )
        _decorate_profile_response(result, payload)
        return result, 200
    except Exception as exc:  # noqa: BLE001
        return profile_export_error_payload(exc)


async def async_handle_profile_import_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Import a Profile export envelope."""
    _runtime, payload, error = _profile_operation_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    try:
        result = await async_import_profile(
            profile_storage(hass),
            payload.get("export") if isinstance(payload.get("export"), dict) else payload,
            overwrite=bool(payload.get("overwrite", False)),
            reassign_id=bool(payload.get("reassign_id", False)),
        )
        return result, 200
    except Exception as exc:  # noqa: BLE001
        return profile_export_error_payload(exc)


async def async_handle_household_import_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Import a household or full integration export envelope."""
    _runtime, payload, error = _profile_operation_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    try:
        result = await async_import_household(
            profile_storage(hass),
            payload.get("export") if isinstance(payload.get("export"), dict) else payload,
            overwrite=bool(payload.get("overwrite", False)),
        )
        return result, 200
    except Exception as exc:  # noqa: BLE001
        return profile_export_error_payload(exc)


async def async_handle_profile_clear_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Clear resolved Profile personal state without deleting the Profile."""
    runtime, payload, error = _profile_operation_runtime_payload(hass, data, headers)
    if error is not None:
        return error
    profile_error, profile_status = await _apply_profile_or_error(
        hass,
        runtime,
        payload,
        user_id=user_id,
        source="profile_clear",
    )
    if profile_error is not None:
        return profile_error, int(profile_status or 400)
    try:
        profile_id = str(payload.get("profile_id") or "")
        cleared_profile = await async_clear_profile_personal_state(
            profile_storage(hass),
            profile_id,
            ask_dj=bool(payload.get("ask_dj", False)),
            music_dna=bool(payload.get("music_dna", False)),
            recommendations=bool(payload.get("recommendations", False)),
            mood=bool(payload.get("mood", False)),
            all_state=bool(payload.get("all", False)),
        )
        if payload.get("ask_dj") or payload.get("all"):
            await _history_manager(hass, runtime).async_clear(user_id)
        if payload.get("music_dna") or payload.get("all"):
            memory = getattr(runtime, "memory", None)
            if memory is not None and callable(getattr(memory, "async_clear", None)):
                await memory.async_clear(str(payload.get("music_dna_key") or ""))
        return {
            "success": True,
            "cleared": True,
            "profile_id": cleared_profile.profile_id,
            "deleted": False,
        }, 200
    except Exception as exc:  # noqa: BLE001
        return profile_export_error_payload(exc)


def _profile_operation_runtime_payload(
    hass: Any,
    data: dict[str, Any],
    headers: Any | None,
) -> tuple[Any | None, dict[str, Any], tuple[dict[str, Any], int] | None]:
    headers = headers or {}
    if not isinstance(data, dict):
        return None, {}, (_error_payload("invalid_json"), 400)
    identity = identity_payload(data)
    runtime = resolve_runtime(
        hass,
        identity.get("device_id") or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        return None, {}, (_error_payload("not_configured"), 503)
    payload = dict(data)
    payload.update({key: value for key, value in identity.items() if value is not None})
    return runtime, payload, None


def _decorate_command_result(
    hass: Any,
    runtime: Any,
    result: dict[str, Any],
    music_dna_key: str | None,
) -> None:
    if music_dna_key:
        result.setdefault("music_dna_key", music_dna_key)
    result.update(_bootstrap_metadata(hass, runtime))
    result.update(_ha_version_payload())
    result.update(music_backend_metadata(hass, runtime))


async def _record_removed_favorite_in_music_dna(
    runtime: Any,
    result: dict[str, Any],
    payload: dict[str, Any],
    *,
    user_id: str | None,
) -> None:
    playback = result.get("playback") if isinstance(result, dict) else {}
    if not isinstance(playback, dict) or _playback_favorite_status(playback) is not False:
        return
    memory = getattr(runtime, "memory", None)
    recorder = getattr(memory, "async_record_blocked_music_preference", None)
    if not callable(recorder):
        return
    try:
        await recorder(
            runtime,
            _favorite_removed_preference(playback),
            payload,
            user_id=user_id,
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect could not record removed favorite in Music DNA: %s", exc)


def _playback_favorite_status(playback: dict[str, Any]) -> bool | None:
    for key in ("is_liked", "favorite_status", "liked", "is_favorite"):
        if key in playback:
            value = playback.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"true", "1", "yes", "ja", "on"}:
                    return True
                if normalized in {"false", "0", "no", "nee", "off"}:
                    return False
    return None


def _favorite_removed_preference(playback: dict[str, Any]) -> dict[str, str]:
    title = _text_value(playback, "track_name", "title", "name")
    artist = _text_value(playback, "artist", "artist_name")
    uri = _text_value(playback, "uri", "current_uri")
    name = " - ".join(value for value in (artist, title) if value) or title or uri
    return {
        "kind": "track",
        "name": name,
        "title": title or name,
        "artist": artist,
        "uri": uri,
        "reason": "removed_from_favorites",
    }


def _text_value(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(data.get(key) or "").strip()
        if value:
            return value
    return ""


def _refresh_authenticated_client_version(runtime: Any, data: dict[str, Any]) -> None:
    """Refresh version metadata before validating an authenticated command.

    Clients issue a command-status request as their first request after an
    upgrade.  Commands intentionally do not merge sensor data, but rejecting
    that request against the cached pre-upgrade version prevents the client
    from ever reaching its following full status update.
    """
    version = _text_value(data, "app_version", "version", "firmware", "firmware_version")
    if version:
        runtime.device_status["app_version"] = version


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
