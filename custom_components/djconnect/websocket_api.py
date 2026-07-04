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
WS_TYPE_MUSIC_DISCOVERY_FEED = "djconnect/music_discovery/feed"
WS_TYPE_MUSIC_DISCOVERY_REFRESH = "djconnect/music_discovery/refresh"
WS_TYPE_MUSIC_DISCOVERY_PLAY = "djconnect/music_discovery/play"


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


async def async_handle_music_discovery_feed_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_discovery_feed_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_discovery_refresh_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_discovery_refresh_payload as handler

    return await handler(*args, **kwargs)


async def async_handle_music_discovery_play_payload(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], int]:
    from .api_handlers import async_handle_music_discovery_play_payload as handler

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
    websocket_api.async_register_command(hass, websocket_music_discovery_feed)
    websocket_api.async_register_command(hass, websocket_music_discovery_refresh)
    websocket_api.async_register_command(hass, websocket_music_discovery_play)
    domain_data["websocket_registered"] = True


@_websocket_command(
    {
        vol.Required("type"): WS_TYPE_CAPABILITIES,
    }
)
@_async_response
async def websocket_capabilities(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    """Return optional websocket transport capabilities for DJConnect clients."""
    connection.send_result(
        msg["id"],
        {
            "success": True,
            "domain": DOMAIN,
            "ha_version": VERSION,
            "websocket_supported": True,
            "commands": [
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
                WS_TYPE_MUSIC_DISCOVERY_FEED,
                WS_TYPE_MUSIC_DISCOVERY_REFRESH,
                WS_TYPE_MUSIC_DISCOVERY_PLAY,
            ],
            "transports": {
                "http": True,
                "websocket": True,
            },
        },
    )


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
