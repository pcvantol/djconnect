"""VibeCast feed support for DJConnect clients."""
from __future__ import annotations

import hashlib
import json
import logging
import re
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
from .pipeline import _assist_context, _speech_from_response, call_conversation_process_with_agent_retry
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
        _debug_disabled(hass, "not_configured", identity=identity)
        return _disabled("not_configured"), 503
    client_type = validate_required_client_type(identity)
    if client_type is None or client_type not in ALLOWED_VIBECAST_CLIENT_TYPES:
        _debug_disabled(hass, "invalid_client_type", identity=identity, client_type=client_type)
        return _disabled("invalid_client_type"), 400
    identity[CONF_CLIENT_TYPE] = client_type
    expected_client_type = str(runtime_client_type(runtime) or "").strip()
    if expected_client_type and expected_client_type != client_type:
        _LOGGER.info(
            "DJConnect VibeCast client type mismatch expected=%s received=%s",
            expected_client_type,
            client_type,
        )
        _debug_disabled(
            hass,
            "client_type_mismatch",
            identity=identity,
            client_type=client_type,
            expected_client_type=expected_client_type,
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
        _debug_disabled(hass, "unauthorized", runtime=runtime, identity=identity, client_type=client_type)
        return _disabled("unauthorized"), 401
    gate = _feature_gate(runtime)
    if gate:
        _debug_disabled(hass, gate, runtime=runtime, identity=identity, client_type=client_type)
        return _disabled(gate), 200
    try:
        status = await run_music_command(hass, runtime, "status")
    except MusicBackendCapabilityError:
        _debug_disabled(hass, "unsupported_backend", runtime=runtime, identity=identity, client_type=client_type)
        return _disabled("unsupported_backend"), 200
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug(
            "DJConnect VibeCast status lookup failed client_type=%s device_id=%s error=%s",
            client_type,
            _safe_device_id(identity.get(CONF_DEVICE_ID)),
            exc.__class__.__name__,
        )
        return _disabled("provider_unavailable"), 200
    playback = status.get("playback") if isinstance(status, dict) else {}
    if not isinstance(playback, dict):
        playback = {}
    _debug_status(hass, runtime, identity, client_type, status, playback)
    if not bool(playback.get("has_playback")):
        _debug_disabled(hass, "no_active_playback", runtime=runtime, identity=identity, client_type=client_type)
        return _disabled("no_active_playback"), 200
    if playback.get("is_playing") is False or str(playback.get("state") or "").lower() in {"paused", "stopped", "idle", "off"}:
        _debug_disabled(
            hass,
            "playback_inactive",
            runtime=runtime,
            identity=identity,
            client_type=client_type,
            playback=playback,
        )
        return _disabled("playback_inactive"), 200
    context = _context_payload(hass, runtime, playback)
    if not context.get("title") and not context.get("artist"):
        _debug_disabled(
            hass,
            "unknown_track",
            runtime=runtime,
            identity=identity,
            client_type=client_type,
            context=context,
        )
        return _disabled("unknown_track"), 200
    locale = _locale(payload)
    render_profile = _render_profile(payload)
    cache_key = _cache_key(context, locale, render_profile)
    cached = _cache(runtime).get(cache_key)
    now = time.monotonic()
    if isinstance(cached, dict) and now < float(cached.get("expires_at") or 0):
        response = dict(cached["response"])
        response["cache"] = {"hit": True}
        _LOGGER.debug(
            "DJConnect VibeCast cache hit client_type=%s device_id=%s backend=%s revision=%s locale=%s render_profile=%s item_count=%s",
            client_type,
            _safe_device_id(identity.get(CONF_DEVICE_ID)),
            context.get("music_backend"),
            response.get("revision"),
            locale,
            render_profile,
            len(response.get("items") or []),
        )
        return response, 200
    try:
        items = await _generate_items(hass, runtime, context, locale, payload)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug(
            "DJConnect VibeCast generation failed client_type=%s device_id=%s backend=%s locale=%s render_profile=%s error=%s",
            client_type,
            _safe_device_id(identity.get(CONF_DEVICE_ID)),
            context.get("music_backend"),
            locale,
            render_profile,
            exc.__class__.__name__,
        )
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
    _LOGGER.debug(
        "DJConnect VibeCast generated client_type=%s device_id=%s backend=%s backend_revision=%s revision=%s locale=%s render_profile=%s item_count=%s source_kinds=%s cache_ttl=%s",
        client_type,
        _safe_device_id(identity.get(CONF_DEVICE_ID)),
        context.get("music_backend"),
        context.get("music_backend_revision"),
        revision,
        locale,
        render_profile,
        len(response["items"]),
        _item_source_kinds(response["items"]),
        _CACHE_TTL_SECONDS,
    )
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
            text = str(value).strip()
            if header_name == "Accept-Language":
                text = text.split(",", 1)[0].strip()
            payload[payload_key] = text
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
    genres = _texts(playback.get("genres"))
    track_id = _first_text(playback, "track_id", "id", "uri", "media_content_id")
    if not track_id:
        track_id = _stable_id(title, artist, album, backend.get("music_backend"))
    return {
        "track_id": track_id,
        "title": title,
        "artist": artist,
        "album": album,
        "genres": genres[:4],
        "music_backend": backend.get("music_backend") or DEFAULT_MUSIC_BACKEND,
        "music_backend_name": backend.get("music_backend_name")
        or MUSIC_BACKEND_NAMES.get(DEFAULT_MUSIC_BACKEND, "Spotify Direct"),
        "music_backend_revision": backend.get("music_backend_revision", 0),
    }


async def _generate_items(
    hass: Any,
    runtime: Any,
    context: dict[str, Any],
    locale: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    generated = await _generate_conversation_items(hass, runtime, context, locale, payload)
    if generated:
        return generated
    return _fallback_items(context, locale, payload)


async def _generate_conversation_items(
    hass: Any,
    runtime: Any,
    context: dict[str, Any],
    locale: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    conf = getattr(runtime, "config", {}) or {}
    assist_context = _assist_context(hass, conf)
    language = "nl-NL" if locale.startswith("nl") else str(assist_context.get("language") or "en-US")
    prompt = _vibecast_prompt(context, language)
    try:
        data = {"text": prompt, "language": language}
        if assist_context.get("agent_id"):
            data["agent_id"] = assist_context["agent_id"]
        result = await call_conversation_process_with_agent_retry(hass, data)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect VibeCast conversation generation unavailable: %s", exc)
        return []
    speech = _speech_from_response((result or {}).get("response") or {})
    return _items_from_conversation_text(context, speech, payload)


def _vibecast_prompt(context: dict[str, Any], language: str) -> str:
    title = context.get("title") or "unknown track"
    artist = context.get("artist") or "unknown artist"
    album = context.get("album") or "unknown album"
    genres = ", ".join(context.get("genres") or []) or "unknown"
    if str(language).lower().startswith("nl"):
        return (
            "Je bent DJConnect VibeCast. Maak precies 3 korte Nederlandse bubble-teksten "
            "voor een live muziekscherm. Gebruik verschillende tekstvormen: een betrouwbaar "
            "trivia/feitje, een concrete luistertip en een creatieve sfeerzin. "
            "Gebruik alleen betrouwbare brede muziekkennis of de meegegeven metadata; verzin "
            "geen releasefeiten, credits of geschiedenis. Als je geen feit weet, maak dan een "
            "observatie over stijl/genre/arrangement op basis van de metadata. Max 90 tekens per tekst. "
            "Antwoord uitsluitend als JSON: "
            "{\"items\":[{\"kind\":\"track_fact\",\"text\":\"...\"},{\"kind\":\"artist_fact\",\"text\":\"...\"},{\"kind\":\"listening_tip\",\"text\":\"...\"}]}.\n\n"
            f"Track: {title}\nArtiest: {artist}\nAlbum: {album}\nGenres: {genres}"
        )
    return (
        "You are DJConnect VibeCast. Create exactly 3 short bubble texts for a live music screen. "
        "Use different forms: one reliable trivia/fact, one concrete listening tip and one creative mood line. "
        "Use only reliable broad music knowledge or the metadata below; do not invent release facts, credits or history. "
        "If you do not know a fact, make a style/genre/arrangement observation from the metadata. Max 90 characters each. "
        "Reply only as JSON: "
        "{\"items\":[{\"kind\":\"track_fact\",\"text\":\"...\"},{\"kind\":\"artist_fact\",\"text\":\"...\"},{\"kind\":\"listening_tip\",\"text\":\"...\"}]}.\n\n"
        f"Track: {title}\nArtist: {artist}\nAlbum: {album}\nGenres: {genres}"
    )


def _items_from_conversation_text(
    context: dict[str, Any],
    speech: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    data = _json_from_text(speech)
    raw_items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(raw_items, list):
        return []
    items: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    allowed = ("track_fact", "artist_fact", "listening_tip", "genre_context", "trivia", "production_note")
    for index, raw in enumerate(raw_items[:3]):
        if not isinstance(raw, dict):
            continue
        text = _clean_bubble_text(raw.get("text"))
        key = text.casefold()
        if not text or key in seen_texts:
            continue
        seen_texts.add(key)
        kind = str(raw.get("kind") or allowed[min(index, len(allowed) - 1)]).strip()
        if kind not in VIBECAST_ITEM_KINDS:
            kind = allowed[min(index, len(allowed) - 1)]
        items.append(
            _item(
                context,
                kind,
                [*_emoji_segments(kind, payload), *_segments_for_generated_text(text)],
                priority=54 - index * 6,
                source_kind="conversation",
            )
        )
    return items if len(items) >= 2 else []


def _fallback_items(context: dict[str, Any], locale: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    title = context.get("title") or "deze track"
    artist = context.get("artist") or "de artiest"
    album = context.get("album") or ""
    genres = context.get("genres") or []
    dutch = locale.startswith("nl")
    variant = _variant_index(context, 4)
    if dutch:
        track_variants = [
            [("text", f"{title} zet de spanning niet vol open, maar laat hem "), ("strong", "pulseren"), ("text", ".")],
            [("text", f"In {title} zit de beweging vooral in de "), ("strong", "ruimte tussen de slagen"), ("text", ".")],
            [("text", f"{title} voelt gebouwd voor een late set: "), ("strong", "rustig druk opbouwen"), ("text", ".")],
            [("text", f"Let op hoe {title} zijn energie doseert: "), ("strong", "kleine duw, groot effect"), ("text", ".")],
        ]
        artist_variants = [
            [("text", f"{artist} kiest hier voor "), ("accent", "glans boven geweld"), ("text", ".")],
            [("text", f"Je hoort {artist} vooral in de "), ("accent", "kleur van de details"), ("text", ".")],
            [("text", f"{artist} laat de track ademen alsof elk laagje "), ("accent", "eigen licht"), ("text", " krijgt.")],
            [("text", f"Typisch {artist}: niet alles uitleggen, maar de "), ("accent", "vibe laten klikken"), ("text", ".")],
        ]
        tip_variants = [
            [("text", "Luister naar de "), ("magnify", "laag net onder de lead"), ("text", "; daar schuift de groove.")],
            [("text", "Tip: volg de "), ("magnify", "kick en galmstaart"), ("text", " alsof ze samen ademhalen.")],
            [("text", "Focus eens op de "), ("magnify", "mini-pauzes"), ("text", "; daar wordt de spanning gemaakt.")],
            [("text", "Let op de "), ("magnify", _genre_tip(genres, True)), ("text", " die de track richting geeft.")],
        ]
        items = [
            _item(
                context,
                "track_fact",
                [
                    *_emoji_segments("track_fact", payload),
                    *track_variants[variant],
                ],
            ),
            _item(
                context,
                "artist_fact",
                [
                    *_emoji_segments("artist_fact", payload),
                    *artist_variants[_variant_index(context, 4, "artist")],
                ],
                priority=44,
            ),
            _item(
                context,
                "listening_tip",
                [
                    *_emoji_segments("listening_tip", payload),
                    *tip_variants[_variant_index(context, 4, "tip")],
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
                        ("text", f"Albumkleur: {album} geeft deze track extra context zonder het moment dicht te praten."),
                    ],
                    priority=32,
                )
            )
        return items[:3]
    track_variants = [
        [("text", f"{title} does not rush the payoff; it lets the "), ("strong", "tension breathe"), ("text", ".")],
        [("text", f"{title} moves through "), ("strong", "pulse and negative space"), ("text", ".")],
        [("text", f"{title} feels shaped for a late set: "), ("strong", "slow pressure, clean lift"), ("text", ".")],
        [("text", f"{title} gets mileage from "), ("strong", "small shifts"), ("text", " rather than big gestures.")],
    ]
    artist_variants = [
        [("text", f"{artist} gives every detail a "), ("accent", "small spotlight"), ("text", ".")],
        [("text", f"The fingerprint here is {artist}'s "), ("accent", "sense of restraint"), ("text", ".")],
        [("text", f"{artist} lets the groove feel "), ("accent", "lit from the edges"), ("text", ".")],
        [("text", f"{artist} keeps the mix expressive without crowding the "), ("accent", "center"), ("text", ".")],
    ]
    tip_variants = [
        [("text", "Listen for the "), ("magnify", "layer just under the lead"), ("text", "; it steers the groove.")],
        [("text", "Try following the "), ("magnify", "kick and reverb tail"), ("text", " as one moving shape.")],
        [("text", "Focus on the "), ("magnify", "tiny pauses"), ("text", "; that is where the tension lives.")],
        [("text", "Catch the "), ("magnify", _genre_tip(genres, False)), ("text", " giving the track its direction.")],
    ]
    items = [
        _item(
            context,
            "track_fact",
        [
            *_emoji_segments("track_fact", payload),
            *track_variants[variant],
            ],
        ),
        _item(
            context,
            "artist_fact",
        [
            *_emoji_segments("artist_fact", payload),
            *artist_variants[_variant_index(context, 4, "artist")],
            ],
            priority=44,
        ),
        _item(
            context,
            "listening_tip",
        [
            *_emoji_segments("listening_tip", payload),
            *tip_variants[_variant_index(context, 4, "tip")],
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
    source_kind: str = "generated",
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
        "source": {"kind": source_kind, "confidence": "medium"},
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


def _json_from_text(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"\s*```$", "", raw).strip()
    if not raw.startswith("{"):
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        raw = match.group(0) if match else raw
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _clean_bubble_text(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    text = re.sub(r"^[\-•\d\.\)\s]+", "", text).strip()
    text = text.strip('"“”')
    if not text or text.upper() in {"SKIP", "UNKNOWN", "ONBEKEND"}:
        return ""
    if len(text) > 120:
        text = text[:117].rstrip() + "..."
    return text


def _segments_for_generated_text(text: str) -> list[tuple[str, str]]:
    if ":" in text:
        head, tail = text.split(":", 1)
        if 2 <= len(head.strip()) <= 34 and tail.strip():
            return [("strong", head.strip()), ("text", f": {tail.strip()}")]
    words = text.split()
    if len(words) >= 7:
        highlight = " ".join(words[:2])
        rest = text[len(highlight):]
        return [("strong", highlight), ("text", rest)]
    return [("text", text)]


def _variant_index(context: dict[str, Any], modulo: int, salt: str = "") -> int:
    digest = _stable_id(
        context.get("track_id"),
        context.get("title"),
        context.get("artist"),
        context.get("album"),
        salt,
    )
    return int(digest[:8], 16) % max(1, modulo)


def _genre_tip(genres: list[str], dutch: bool) -> str:
    genre_text = " ".join(genres).lower()
    if any(term in genre_text for term in ("trance", "progressive")):
        return "opbouw en zwevende synthlaag" if dutch else "build and floating synth layer"
    if any(term in genre_text for term in ("techno", "house", "edm")):
        return "drumgroove en baspuls" if dutch else "drum groove and bass pulse"
    if any(term in genre_text for term in ("classical", "klassiek", "piano")):
        return "dynamiek tussen aanslag en stilte" if dutch else "dynamics between attack and silence"
    if any(term in genre_text for term in ("ambient", "chill", "downtempo")):
        return "textuur in de galmstaart" if dutch else "texture in the reverb tail"
    return "achtergrondlaag" if dutch else "background layer"


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


def _texts(values: Any) -> list[str]:
    if isinstance(values, str):
        return [values.strip()] if values.strip() else []
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if isinstance(value, dict):
            text = _first_text(value, "name", "genre", "title")
        else:
            text = str(value or "").strip()
        if text:
            result.append(text)
    return result


def _debug_disabled(
    hass: Any,
    reason: str,
    *,
    runtime: Any | None = None,
    identity: dict[str, Any] | None = None,
    client_type: str | None = None,
    expected_client_type: str | None = None,
    playback: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    backend = music_backend_metadata(hass, runtime) if runtime is not None else {}
    identity = identity or {}
    playback = playback or {}
    context = context or {}
    _LOGGER.debug(
        "DJConnect VibeCast disabled reason=%s client_type=%s expected_client_type=%s device_id=%s backend=%s backend_available=%s playback_state=%s has_playback=%s context_known=%s",
        reason,
        client_type or identity.get(CONF_CLIENT_TYPE),
        expected_client_type,
        _safe_device_id(identity.get(CONF_DEVICE_ID)),
        backend.get("music_backend"),
        backend.get("music_backend_available"),
        _safe_state(playback.get("state")),
        playback.get("has_playback"),
        bool(context.get("title") or context.get("artist")),
    )


def _debug_status(
    hass: Any,
    runtime: Any,
    identity: dict[str, Any],
    client_type: str,
    status: dict[str, Any] | Any,
    playback: dict[str, Any],
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    backend = music_backend_metadata(hass, runtime)
    _LOGGER.debug(
        "DJConnect VibeCast status client_type=%s device_id=%s backend=%s backend_available=%s status_success=%s has_playback=%s playback_state=%s is_playing=%s track_known=%s",
        client_type,
        _safe_device_id(identity.get(CONF_DEVICE_ID)),
        backend.get("music_backend"),
        backend.get("music_backend_available"),
        status.get("success") if isinstance(status, dict) else None,
        playback.get("has_playback"),
        _safe_state(playback.get("state")),
        playback.get("is_playing"),
        bool(_first_text(playback, "title", "track_name", "name", "media_title") or _first_text(playback, "artist", "artist_name", "media_artist")),
    )


def _item_source_kinds(items: list[dict[str, Any]]) -> list[str]:
    source_kinds: list[str] = []
    for item in items:
        source = item.get("source") if isinstance(item, dict) else None
        kind = source.get("kind") if isinstance(source, dict) else None
        text = str(kind or "").strip()
        if text and text not in source_kinds:
            source_kinds.append(text)
    return source_kinds


def _safe_device_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "***"
    return f"{text[:14]}...{text[-4:]}"


def _safe_state(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"playing", "paused", "stopped", "idle", "off"} else ""
