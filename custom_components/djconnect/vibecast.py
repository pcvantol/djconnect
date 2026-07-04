"""VibeCast feed support for DJConnect clients."""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from .const import (
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_WATCHOS,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    DEFAULT_MUSIC_BACKEND,
    MUSIC_BACKEND_NAMES,
)
from .request_auth import (
    authorize_runtime_device_request,
    identity_payload,
    resolve_runtime,
    runtime_client_type,
    validate_required_client_type,
)
from .use_cases import MusicBackendCapabilityError, music_backend_metadata, run_music_command

_LOGGER = logging.getLogger(__name__)

ALLOWED_VIBECAST_CLIENT_TYPES = {CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS}
ALLOWED_TEXT_SEGMENT_TYPES = {"text", "strong", "emphasis", "magnify", "accent", "emoji", "line_break"}
VIBECAST_ITEM_KINDS = {
    "track_fact",
    "artist_fact",
    "album_fact",
    "genre_context",
    "trivia",
    "listening_tip",
    "mood_context",
    "production_note",
    "history_note",
    "system",
}
_CACHE_TTL_SECONDS = 45
_POLL_AFTER_SECONDS = 20


async def async_handle_vibecast_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
) -> tuple[dict[str, Any], int]:
    """Return a small VibeCast feed for the current playback context."""
    headers = headers or {}
    if not isinstance(data, dict):
        data = {}
    payload = _metadata_payload(data, headers)
    identity = identity_payload(payload)
    runtime = resolve_runtime(
        hass,
        identity.get(CONF_DEVICE_ID) or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        return _disabled("not_configured"), 503
    client_type = validate_required_client_type(identity)
    if client_type is None or client_type not in ALLOWED_VIBECAST_CLIENT_TYPES:
        return _disabled("invalid_client_type"), 400
    identity[CONF_CLIENT_TYPE] = client_type
    expected_client_type = str(runtime_client_type(runtime) or "").strip()
    if expected_client_type and expected_client_type != client_type:
        _LOGGER.info(
            "DJConnect VibeCast client type mismatch expected=%s received=%s",
            expected_client_type,
            client_type,
        )
        return _disabled(
            "client_type_mismatch",
            expected_client_type=expected_client_type,
            received_client_type=client_type,
        ), 400
    if not authorize_runtime_device_request(
        runtime,
        headers,
        identity.get(CONF_DEVICE_ID),
        client_type,
    ):
        return _disabled("unauthorized"), 401
    gate = _feature_gate(runtime)
    if gate:
        return _disabled(gate), 200
    try:
        status = await run_music_command(hass, runtime, "status")
    except MusicBackendCapabilityError:
        return _disabled("unsupported_backend"), 200
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect VibeCast status lookup failed: %s", exc)
        return _disabled("provider_unavailable"), 200
    playback = status.get("playback") if isinstance(status, dict) else {}
    if not isinstance(playback, dict):
        playback = {}
    if not bool(playback.get("has_playback")):
        return _disabled("no_active_playback"), 200
    if playback.get("is_playing") is False or str(playback.get("state") or "").lower() in {"paused", "stopped", "idle", "off"}:
        return _disabled("playback_inactive"), 200
    context = _context_payload(hass, runtime, playback)
    if not context.get("title") and not context.get("artist"):
        return _disabled("unknown_track"), 200
    locale = _locale(payload)
    render_profile = _render_profile(payload)
    cache_key = _cache_key(context, locale, render_profile)
    cached = _cache(runtime).get(cache_key)
    now = time.monotonic()
    if isinstance(cached, dict) and now < float(cached.get("expires_at") or 0):
        response = dict(cached["response"])
        response["cache"] = {"hit": True}
        return response, 200
    try:
        items = _generate_items(context, locale, payload)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect VibeCast generation failed: %s", exc)
        return _disabled("generative_provider_unavailable"), 200
    revision = _next_revision(runtime)
    response = {
        "success": True,
        "enabled": True,
        "revision": revision,
        "ttl_seconds": _CACHE_TTL_SECONDS,
        "poll_after_seconds": _POLL_AFTER_SECONDS,
        "context": context,
        "items": [_sanitize_item(item) for item in items],
        "cache": {"hit": False},
    }
    _cache(runtime)[cache_key] = {
        "expires_at": now + _CACHE_TTL_SECONDS,
        "response": response,
    }
    return response, 200


def _metadata_payload(data: dict[str, Any], headers: Any) -> dict[str, Any]:
    payload = dict(data)
    for header_name, payload_key in (
        ("X-DJConnect-Device-ID", CONF_DEVICE_ID),
        ("X-DJConnect-Client-Type", CONF_CLIENT_TYPE),
        ("X-DJConnect-Client-ID", "client_id"),
        ("X-DJConnect-Device-Name", "device_name"),
        ("X-DJConnect-App-Version", "app_version"),
        ("X-DJConnect-App-Build", "app_build"),
        ("X-DJConnect-Language", "language"),
        ("X-DJConnect-Locale", "locale"),
        ("Accept-Language", "locale"),
        ("X-DJConnect-Timezone", "timezone"),
        ("X-DJConnect-Render-Capabilities", "render_capabilities"),
    ):
        value = headers.get(header_name) if hasattr(headers, "get") else None
        if value and not payload.get(payload_key):
            payload[payload_key] = str(value).split(",", 1)[0].strip()
    return payload


def _feature_gate(runtime: Any) -> str | None:
    config = getattr(runtime, "config", {}) or {}
    status = getattr(runtime, "device_status", {}) or {}
    if config.get("vibecast_enabled") is False or status.get("vibecast_enabled") is False:
        return "feature_disabled"
    if status.get("vibecast_privacy_enabled") is False:
        return "privacy_disabled"
    if status.get("vibecast_entitled") is False or config.get("vibecast_entitled") is False:
        return "premium_unavailable"
    return None


def _context_payload(hass: Any, runtime: Any, playback: dict[str, Any]) -> dict[str, Any]:
    backend = music_backend_metadata(hass, runtime)
    title = _first_text(playback, "title", "track_name", "name", "media_title")
    artist = _first_text(playback, "artist", "artist_name", "media_artist")
    album = _first_text(playback, "album", "album_name", "media_album_name")
    track_id = _first_text(playback, "track_id", "id", "uri", "media_content_id")
    if not track_id:
        track_id = _stable_id(title, artist, album, backend.get("music_backend"))
    return {
        "track_id": track_id,
        "title": title,
        "artist": artist,
        "album": album,
        "music_backend": backend.get("music_backend") or DEFAULT_MUSIC_BACKEND,
        "music_backend_name": backend.get("music_backend_name")
        or MUSIC_BACKEND_NAMES.get(DEFAULT_MUSIC_BACKEND, "Spotify Direct"),
        "music_backend_revision": backend.get("music_backend_revision", 0),
    }


def _generate_items(context: dict[str, Any], locale: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    title = context.get("title") or "deze track"
    artist = context.get("artist") or "de artiest"
    album = context.get("album") or ""
    dutch = locale.startswith("nl")
    if dutch:
        items = [
            _item(
                context,
                "track_fact",
                [
                    *_emoji_segments("track_fact", payload),
                    ("text", "Deze track leunt op "),
                    ("strong", "ritme en ruimte"),
                    ("text", f": luister hoe {title} steeds net genoeg openlaat."),
                ],
            ),
            _item(
                context,
                "artist_fact",
                [
                    *_emoji_segments("artist_fact", payload),
                    ("text", f"{artist} klinkt hier alsof elk detail een "),
                    ("accent", "kleine lichtflits"),
                    ("text", " in de mix mag zijn."),
                ],
                priority=44,
            ),
            _item(
                context,
                "listening_tip",
                [
                    *_emoji_segments("listening_tip", payload),
                    ("text", "Tip: focus eens op de "),
                    ("magnify", "achtergrondlaag"),
                    ("text", " vlak voor het refrein of de drop."),
                ],
                priority=38,
            ),
        ]
        if album:
            items.append(
                _item(
                    context,
                    "album_fact",
                    [
                        *_emoji_segments("album_fact", payload),
                        ("text", f"Albumcontext: {album} geeft deze track extra kleur zonder dat VibeCast harde claims hoeft te maken."),
                    ],
                    priority=32,
                )
            )
        return items[:3]
    items = [
        _item(
            context,
            "track_fact",
        [
            *_emoji_segments("track_fact", payload),
            ("text", "This track rides on "),
            ("strong", "space and pulse"),
            ("text", f": {title} leaves just enough air around the groove."),
            ],
        ),
        _item(
            context,
            "artist_fact",
        [
            *_emoji_segments("artist_fact", payload),
            ("text", f"{artist} makes the mix feel like every detail gets a "),
            ("accent", "tiny spotlight"),
            ("text", "."),
            ],
            priority=44,
        ),
        _item(
            context,
            "listening_tip",
        [
            *_emoji_segments("listening_tip", payload),
            ("text", "Try listening for the "),
            ("magnify", "background layer"),
            ("text", " right before the hook or drop."),
            ],
            priority=38,
        ),
    ]
    return items


def _item(
    context: dict[str, Any],
    kind: str,
    text: list[tuple[str, str]],
    *,
    priority: int = 50,
) -> dict[str, Any]:
    seed = "|".join(
        str(value or "")
        for value in (
            context.get("track_id"),
            context.get("title"),
            context.get("artist"),
            kind,
        )
    )
    return {
        "id": _stable_id(seed)[:24],
        "kind": kind,
        "tone": "playful",
        "priority": priority,
        "display_seconds": 8,
        "placement_hint": "side",
        "text": [{"type": segment_type, "value": value} for segment_type, value in text],
        "source": {"kind": "generated", "confidence": "medium"},
    }


def _emoji_segments(kind: str, payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Return a tiny decorative emoji prefix when the client opts in."""
    if not _emoji_safe(payload):
        return []
    emojis_by_kind = {
        "track_fact": "♪ ♫",
        "artist_fact": "✨",
        "album_fact": "💿",
        "genre_context": "🎚️",
        "trivia": "🎵",
        "listening_tip": "🎧",
        "mood_context": "🌙",
        "production_note": "🎛️",
        "history_note": "🕰️",
    }
    value = emojis_by_kind.get(kind, "♪")
    return [("emoji", f"{value} ")]


def _emoji_safe(payload: dict[str, Any]) -> bool:
    return "emoji_safe" in _render_capabilities(payload)


def _render_capabilities(payload: dict[str, Any]) -> set[str]:
    raw = str(payload.get("render_capabilities") or "").strip().lower()
    return {part.strip() for part in raw.split(",") if part.strip()}


def _render_profile(payload: dict[str, Any]) -> str:
    return "emoji_safe" if _emoji_safe(payload) else "text_only"


def _sanitize_item(item: dict[str, Any]) -> dict[str, Any]:
    clean = dict(item)
    kind = str(clean.get("kind") or "system").strip()
    clean["kind"] = kind if kind in VIBECAST_ITEM_KINDS else "system"
    clean["text"] = _sanitize_text(clean.get("text"))
    clean.setdefault("source", {"kind": "generated", "confidence": "medium"})
    return clean


def _sanitize_text(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    segments: list[dict[str, str]] = []
    for segment in value:
        if not isinstance(segment, dict):
            continue
        segment_type = str(segment.get("type") or "text").strip()
        if segment_type not in ALLOWED_TEXT_SEGMENT_TYPES:
            segment_type = "text"
        text_value = str(segment.get("value") or "")
        if "<" in text_value or ">" in text_value:
            text_value = text_value.replace("<", "").replace(">", "")
        segments.append({"type": segment_type, "value": text_value})
    return segments


def _disabled(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "success": reason not in {"unauthorized", "invalid_client_type", "client_type_mismatch", "not_configured"},
        "enabled": False,
        "reason": reason,
        "ttl_seconds": 30,
        "poll_after_seconds": 30,
        "items": [],
        **{key: value for key, value in extra.items() if value not in ("", None)},
    }


def _cache(runtime: Any) -> dict[str, Any]:
    cache = getattr(runtime, "vibecast_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(runtime, "vibecast_cache", cache)
    return cache


def _next_revision(runtime: Any) -> int:
    revision = int(getattr(runtime, "vibecast_revision", 0) or 0) + 1
    setattr(runtime, "vibecast_revision", revision)
    return revision


def _cache_key(context: dict[str, Any], locale: str, render_profile: str = "text_only") -> str:
    return _stable_id(
        context.get("track_id"),
        context.get("title"),
        context.get("artist"),
        context.get("album"),
        context.get("music_backend"),
        context.get("music_backend_revision"),
        locale,
        render_profile,
    )


def _stable_id(*parts: Any) -> str:
    text = "|".join(str(part or "") for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _locale(payload: dict[str, Any]) -> str:
    return str(payload.get("locale") or payload.get("language") or "en").strip().lower()


def _first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""
