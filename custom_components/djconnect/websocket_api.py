from __future__ import annotations

from typing import Any

import voluptuous as vol

try:
    from homeassistant.components import websocket_api
except ImportError:  # pragma: no cover - only used by lightweight unit-test stubs.
    websocket_api = None

from .const import DOMAIN, VERSION

WS_TYPE_CAPABILITIES = "djconnect/capabilities"
WS_TYPE_ASK_DJ_MESSAGE = "djconnect/ask_dj/message"
WS_TYPE_ASK_DJ_HISTORY = "djconnect/ask_dj/history"
WS_TYPE_ASK_DJ_HISTORY_CLEAR = "djconnect/ask_dj/history/clear"
WS_TYPE_ASK_DJ_HISTORY_STATE = "djconnect/ask_dj/history/state"
WS_TYPE_ASK_DJ_IDLE_SUGGESTION = "djconnect/ask_dj/idle_suggestion"
WS_TYPE_COMMAND = "djconnect/command"
WS_TYPE_TRACK_INSIGHT = "djconnect/track_insight"
WS_TYPE_MUSIC_DNA_PROFILE = "djconnect/music_dna/profile"
WS_TYPE_MUSIC_DNA_SETTINGS = "djconnect/music_dna/settings"
WS_TYPE_MUSIC_DNA_CLEAR = "djconnect/music_dna/clear"
WS_TYPE_MUSIC_DNA_IMPORT = "djconnect/music_dna/import"
WS_TYPE_MUSIC_DNA_EXPORT = "djconnect/music_dna/export"
WS_TYPE_MUSIC_DISCOVERY_FEED = "djconnect/music_discovery/feed"
WS_TYPE_MUSIC_DISCOVERY_REFRESH = "djconnect/music_discovery/refresh"
WS_TYPE_MUSIC_DISCOVERY_PLAY = "djconnect/music_discovery/play"
WS_TYPE_MUSIC_DISCOVERY_FEEDBACK = "djconnect/music_discovery/feedback"

HTTP_FALLBACK_PATHS = {
    "ask_dj_message": "/api/djconnect/v1/ask_dj/message",
    "ask_dj_history": "/api/djconnect/v1/ask_dj/history",
    "ask_dj_history_clear": "/api/djconnect/v1/ask_dj/history/clear",
    "command": "/api/djconnect/v1/command",
    "music_dna_profile": "/api/djconnect/v1/music_dna/profile",
    "music_dna_settings": "/api/djconnect/v1/music_dna/settings",
    "music_dna_clear": "/api/djconnect/v1/music_dna/clear",
    "music_dna_import": "/api/djconnect/v1/music_dna/import",
    "music_dna_export": "/api/djconnect/v1/music_dna/export",
    "music_discovery_feed": "/api/djconnect/v1/music_discovery",
    "music_discovery_refresh": "/api/djconnect/v1/music_discovery/refresh",
    "music_discovery_play": "/api/djconnect/v1/music_discovery/play",
    "music_discovery_feedback": "/api/djconnect/v1/music_discovery/feedback",
    "track_insight": "/api/djconnect/v1/track_insight",
}

FEATURE_COMMANDS = {
    "ask_dj_chat": (WS_TYPE_ASK_DJ_MESSAGE,),
    "ask_dj_history": (WS_TYPE_ASK_DJ_HISTORY, WS_TYPE_ASK_DJ_HISTORY_CLEAR),
    "ask_dj_idle_suggestion": (WS_TYPE_ASK_DJ_IDLE_SUGGESTION,),
    "backend_commands": (WS_TYPE_COMMAND,),
    "track_insight": (WS_TYPE_TRACK_INSIGHT,),
    "music_dna": (
        WS_TYPE_MUSIC_DNA_PROFILE,
        WS_TYPE_MUSIC_DNA_SETTINGS,
        WS_TYPE_MUSIC_DNA_CLEAR,
        WS_TYPE_MUSIC_DNA_IMPORT,
        WS_TYPE_MUSIC_DNA_EXPORT,
    ),
    "music_discovery": (
        WS_TYPE_MUSIC_DISCOVERY_FEED,
        WS_TYPE_MUSIC_DISCOVERY_REFRESH,
        WS_TYPE_MUSIC_DISCOVERY_PLAY,
    ),
    "music_discovery_feedback": (WS_TYPE_MUSIC_DISCOVERY_FEEDBACK,),
}


async def async_handle_command_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_command_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_ask_dj_message_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_ask_dj_message_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_ask_dj_history_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_ask_dj_history_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_ask_dj_history_clear_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_ask_dj_history_clear_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_ask_dj_history_state_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_ask_dj_history_state_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_ask_dj_idle_suggestion_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_ask_dj_idle_suggestion_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_track_insight_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_track_insight_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_dna_profile_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_dna_profile_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_dna_settings_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_dna_settings_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_dna_clear_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_dna_clear_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_dna_import_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_dna_import_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_dna_export_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_dna_export_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_discovery_feed_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_discovery_feed_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_discovery_refresh_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_discovery_refresh_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_discovery_play_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_discovery_play_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_discovery_feedback_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_discovery_feedback_payload as handler

    return await handler(*args, **kwargs)


def _websocket_command(schema: dict[Any, Any]) -> Any:
    if websocket_api is None:
        return lambda func: func
    return websocket_api.websocket_command(schema)


def _async_response(func: Any) -> Any:
    if websocket_api is None:
        return func
    return websocket_api.async_response(func)


def async_register(hass: Any) -> None:
    """Register DJConnect commands on Home Assistant's native websocket API."""
    if websocket_api is None:
        return
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("websocket_registered"):
        return
    websocket_api.async_register_command(hass, websocket_capabilities)
    websocket_api.async_register_command(hass, websocket_command)
    websocket_api.async_register_command(hass, websocket_ask_dj_message)
    websocket_api.async_register_command(hass, websocket_ask_dj_history)
    websocket_api.async_register_command(hass, websocket_ask_dj_history_clear)
    websocket_api.async_register_command(hass, websocket_ask_dj_history_state)
    websocket_api.async_register_command(hass, websocket_ask_dj_idle_suggestion)
    websocket_api.async_register_command(hass, websocket_track_insight)
    websocket_api.async_register_command(hass, websocket_music_dna_profile)
    websocket_api.async_register_command(hass, websocket_music_dna_settings)
    websocket_api.async_register_command(hass, websocket_music_dna_clear)
    websocket_api.async_register_command(hass, websocket_music_dna_import)
    websocket_api.async_register_command(hass, websocket_music_dna_export)
    websocket_api.async_register_command(hass, websocket_music_discovery_feed)
    websocket_api.async_register_command(hass, websocket_music_discovery_refresh)
    websocket_api.async_register_command(hass, websocket_music_discovery_play)
    websocket_api.async_register_command(hass, websocket_music_discovery_feedback)
    domain_data["websocket_registered"] = True


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_CAPABILITIES,
    }
)
@_async_response
async def websocket_capabilities(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Return optional websocket transport capabilities for DJConnect clients."""
    commands = _supported_websocket_commands()
    connection.send_result(
        msg["id"],
        {
            "success": True,
            "domain": DOMAIN,
            "ha_version": VERSION,
            "websocket_supported": True,
            "commands": commands,
            "features": _feature_capabilities(commands),
            "fallbacks": _capability_fallbacks(commands),
            "transports": {
                "http": True,
                "websocket": True,
            },
        },
    )


def _supported_websocket_commands() -> list[str]:
    """Return supported DJConnect websocket command types in stable order."""
    return [
        WS_TYPE_COMMAND,
        WS_TYPE_ASK_DJ_MESSAGE,
        WS_TYPE_ASK_DJ_HISTORY,
        WS_TYPE_ASK_DJ_HISTORY_CLEAR,
        WS_TYPE_ASK_DJ_HISTORY_STATE,
        WS_TYPE_ASK_DJ_IDLE_SUGGESTION,
        WS_TYPE_TRACK_INSIGHT,
        WS_TYPE_MUSIC_DNA_PROFILE,
        WS_TYPE_MUSIC_DNA_SETTINGS,
        WS_TYPE_MUSIC_DNA_CLEAR,
        WS_TYPE_MUSIC_DNA_IMPORT,
        WS_TYPE_MUSIC_DNA_EXPORT,
        WS_TYPE_MUSIC_DISCOVERY_FEED,
        WS_TYPE_MUSIC_DISCOVERY_REFRESH,
        WS_TYPE_MUSIC_DISCOVERY_PLAY,
        WS_TYPE_MUSIC_DISCOVERY_FEEDBACK,
    ]


def _feature_capabilities(commands: list[str]) -> dict[str, bool]:
    """Return coarse feature flags so clients can degrade without version parsing."""
    available = set(commands)
    return {
        feature: all(command in available for command in required)
        for feature, required in FEATURE_COMMANDS.items()
    }


def _capability_fallbacks(commands: list[str]) -> dict[str, dict[str, Any]]:
    """Return client fallback hints for each backend-facing feature."""
    features = _feature_capabilities(commands)
    return {
        "ask_dj_chat": {
            "available": features["ask_dj_chat"],
            "preferred_transport": "websocket" if features["ask_dj_chat"] else "http",
            "http_path": HTTP_FALLBACK_PATHS["ask_dj_message"],
            "missing_behavior": "use_http",
        },
        "ask_dj_history": {
            "available": features["ask_dj_history"],
            "preferred_transport": "websocket" if features["ask_dj_history"] else "http",
            "http_paths": {
                "history": HTTP_FALLBACK_PATHS["ask_dj_history"],
                "clear": HTTP_FALLBACK_PATHS["ask_dj_history_clear"],
            },
            "missing_behavior": "use_http",
        },
        "backend_commands": {
            "available": features["backend_commands"],
            "preferred_transport": "websocket" if features["backend_commands"] else "http",
            "http_path": HTTP_FALLBACK_PATHS["command"],
            "missing_behavior": "use_http",
        },
        "track_insight": {
            "available": features["track_insight"],
            "preferred_transport": "websocket" if features["track_insight"] else "http",
            "http_path": HTTP_FALLBACK_PATHS["track_insight"],
            "missing_behavior": "use_http",
        },
        "music_dna": {
            "available": features["music_dna"],
            "preferred_transport": "websocket" if features["music_dna"] else "http",
            "http_paths": {
                "profile": HTTP_FALLBACK_PATHS["music_dna_profile"],
                "settings": HTTP_FALLBACK_PATHS["music_dna_settings"],
                "clear": HTTP_FALLBACK_PATHS["music_dna_clear"],
                "import": HTTP_FALLBACK_PATHS["music_dna_import"],
                "export": HTTP_FALLBACK_PATHS["music_dna_export"],
            },
            "missing_behavior": "use_http_or_hide_feature",
        },
        "music_discovery": {
            "available": features["music_discovery"],
            "preferred_transport": "websocket" if features["music_discovery"] else "http",
            "http_paths": {
                "feed": HTTP_FALLBACK_PATHS["music_discovery_feed"],
                "refresh": HTTP_FALLBACK_PATHS["music_discovery_refresh"],
                "play": HTTP_FALLBACK_PATHS["music_discovery_play"],
            },
            "missing_behavior": "use_http_or_hide_feature",
        },
        "music_discovery_feedback": {
            "available": features["music_discovery_feedback"],
            "preferred_transport": "websocket" if features["music_discovery_feedback"] else "http",
            "http_path": HTTP_FALLBACK_PATHS["music_discovery_feedback"],
            "missing_behavior": "hide_negative_feedback_controls",
        },
    }


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_COMMAND,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("command"): str,
        vol.Optional("value"): object,
        vol.Optional("play"): bool,
    }
)
@_async_response
async def websocket_command(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Handle a DJConnect command over HA websocket with HTTP-equivalent auth."""
    payload = dict(msg.get("payload") or {})
    for key in (
        "device_id",
        "client_type",
        "client_id",
        "device_name",
        "command",
        "value",
        "play",
    ):
        if key in msg and key not in payload:
            payload[key] = msg[key]
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_command_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_ASK_DJ_MESSAGE,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("client_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("identity"): dict,
        vol.Optional("client_message_id"): str,
        vol.Optional("text"): str,
        vol.Optional("audio_response"): str,
        vol.Optional("mood"): object,
        vol.Optional("music_dna_key"): str,
    }
)
@_async_response
async def websocket_ask_dj_message(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Handle Ask DJ chat over HA websocket with canonical history sync."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "client_id",
            "device_name",
            "identity",
            "client_message_id",
            "text",
            "audio_response",
            "mood",
            "music_dna_key",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_ask_dj_message_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_ASK_DJ_HISTORY,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("device_token"): str,
        vol.Optional("client_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("identity"): dict,
        vol.Optional("since_revision"): object,
    }
)
@_async_response
async def websocket_ask_dj_history(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Return Ask DJ history over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "identity",
            "since_revision",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_ask_dj_history_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_ASK_DJ_HISTORY_CLEAR,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("client_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("identity"): dict,
    }
)
@_async_response
async def websocket_ask_dj_history_clear(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Clear Ask DJ history over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "client_id",
            "device_name",
            "identity",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_ask_dj_history_clear_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_ASK_DJ_HISTORY_STATE,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("device_token"): str,
        vol.Optional("client_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("identity"): dict,
        vol.Optional("since_revision"): object,
        vol.Optional("clear_revision"): object,
    }
)
@_async_response
async def websocket_ask_dj_history_state(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Return compact Ask DJ history state over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "identity",
            "since_revision",
            "clear_revision",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_ask_dj_history_state_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_ASK_DJ_IDLE_SUGGESTION,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("client_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("identity"): dict,
        vol.Optional("music_dna_key"): str,
        vol.Optional("mood"): object,
    }
)
@_async_response
async def websocket_ask_dj_idle_suggestion(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Return an Ask DJ idle suggestion over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "client_id",
            "device_name",
            "identity",
            "music_dna_key",
            "mood",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_ask_dj_idle_suggestion_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_TRACK_INSIGHT,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("client_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("identity"): dict,
        vol.Optional("title"): str,
        vol.Optional("artist"): str,
        vol.Optional("album"): str,
        vol.Optional("force_refresh"): bool,
        vol.Optional("include_visual_profile"): bool,
    }
)
@_async_response
async def websocket_track_insight(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Handle Track Insight over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "client_id",
            "device_name",
            "identity",
            "title",
            "track_name",
            "media_title",
            "artist",
            "artist_name",
            "media_artist",
            "artists",
            "album",
            "album_name",
            "media_album_name",
            "media_album",
            "artwork_url",
            "image_url",
            "entity_picture",
            "album_image_url",
            "duration_ms",
            "duration",
            "progress_ms",
            "position_ms",
            "progress",
            "entity_id",
            "player_id",
            "music_backend",
            "backend",
            "provider",
            "track",
            "playback",
            "media",
            "force_refresh",
            "include_visual_profile",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_track_insight_payload(
        hass,
        payload,
        headers=headers,
        source="websocket",
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DNA_PROFILE,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
    }
)
@_async_response
async def websocket_music_dna_profile(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Return Music DNA profile over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "music_dna_key",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_dna_profile_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DNA_SETTINGS,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
        vol.Optional("enabled"): bool,
    }
)
@_async_response
async def websocket_music_dna_settings(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Update Music DNA opt-in over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "music_dna_key",
            "enabled",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_dna_settings_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DNA_CLEAR,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
    }
)
@_async_response
async def websocket_music_dna_clear(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Clear Music DNA over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "music_dna_key",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_dna_clear_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DNA_IMPORT,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
        vol.Optional("profile"): dict,
        vol.Optional("import_mode"): str,
    }
)
@_async_response
async def websocket_music_dna_import(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Import Music DNA over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "music_dna_key",
            "profile",
            "import_mode",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_dna_import_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DNA_EXPORT,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
    }
)
@_async_response
async def websocket_music_dna_export(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Export Music DNA over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "music_dna_key",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_dna_export_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DISCOVERY_FEED,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
    }
)
@_async_response
async def websocket_music_discovery_feed(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Return Music Discovery feed over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "client_id",
            "device_name",
            "music_dna_key",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_discovery_feed_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DISCOVERY_REFRESH,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
    }
)
@_async_response
async def websocket_music_discovery_refresh(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Refresh Music Discovery feed over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "client_id",
            "device_name",
            "music_dna_key",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_discovery_refresh_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DISCOVERY_PLAY,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
        vol.Optional("discovery_item_id"): str,
        vol.Optional("section_id"): str,
    }
)
@_async_response
async def websocket_music_discovery_play(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Play Music Discovery item over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "client_id",
            "device_name",
            "music_dna_key",
            "discovery_item_id",
            "section_id",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_discovery_play_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_MUSIC_DISCOVERY_FEEDBACK,
        vol.Optional("payload", default={}): dict,
        vol.Optional("device_id"): str,
        vol.Optional("client_type"): str,
        vol.Optional("client_id"): str,
        vol.Optional("device_name"): str,
        vol.Optional("device_token"): str,
        vol.Optional("authorization"): str,
        vol.Optional("music_dna_key"): str,
        vol.Optional("discovery_item_id"): str,
        vol.Optional("section_id"): str,
        vol.Optional("feedback"): str,
        vol.Optional("action"): str,
    }
)
@_async_response
async def websocket_music_discovery_feedback(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Record Music Discovery feedback over HA websocket."""
    payload = _payload_from_message(
        msg,
        (
            "device_id",
            "client_type",
            "client_id",
            "device_name",
            "music_dna_key",
            "discovery_item_id",
            "section_id",
            "feedback",
            "action",
        ),
    )
    headers = _headers_from_message(payload, msg)
    result, status_code = await async_handle_music_discovery_feedback_payload(
        hass,
        payload,
        headers=headers,
        user_id=_connection_user_id(connection),
    )
    if 200 <= status_code < 300:
        connection.send_result(msg["id"], result)
        return
    _send_error(connection, msg, result)


def _payload_from_message(msg: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    payload = dict(msg.get("payload") or {})
    for key in keys:
        if key in msg and key not in payload:
            payload[key] = msg[key]
    return payload


def _send_error(connection: Any, msg: dict[str, Any], result: dict[str, Any]) -> None:
    connection.send_error(
        msg["id"],
        str(result.get("error") or "djconnect_error"),
        str(result.get("message") or result.get("error") or "DJConnect request failed."),
    )


def _headers_from_message(payload: dict[str, Any], msg: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    payload_identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    msg_identity = msg.get("identity") if isinstance(msg.get("identity"), dict) else {}
    identity = {**msg_identity, **payload_identity}
    device_id = str(
        payload.get("device_id")
        or msg.get("device_id")
        or identity.get("device_id")
        or identity.get("client_id")
        or ""
    ).strip()
    if device_id:
        headers["X-DJConnect-Device-ID"] = device_id
    token = str(
        msg.get("device_token")
        or msg.get("client_token")
        or payload.get("device_token")
        or payload.get("client_token")
        or identity.get("device_token")
        or identity.get("client_token")
        or identity.get("token")
        or identity.get("bearer_token")
        or ""
    ).strip()
    authorization = str(
        msg.get("authorization")
        or payload.get("authorization")
        or identity.get("authorization")
        or ""
    ).strip()
    if authorization:
        headers["Authorization"] = (
            authorization if authorization.lower().startswith("bearer ") else f"Bearer {authorization}"
        )
    elif token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _connection_user_id(connection: Any) -> str | None:
    user = getattr(connection, "user", None)
    user_id = getattr(user, "id", None)
    return str(user_id) if user_id else None
