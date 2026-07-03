"""Ambient Ask DJ messages triggered by backend playback context changes."""
from __future__ import annotations

import logging
from urllib.parse import quote
import secrets
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_IMAGE_PROXY_BASE, CONF_DEVICE_LANGUAGE, CONF_TTS_LANGUAGE, DEFAULT_TTS_LANGUAGE, DOMAIN
from .pipeline import _assist_context, _speech_from_response, call_conversation_process_with_agent_retry

_LOGGER = logging.getLogger(__name__)

AMBIENT_FACT_INTENT = "ambient_music_fact"
AMBIENT_FACT_ACTION = "none"
IMAGE_PROXY_KEY = "image_proxy"
_SKIP_VALUES = {"", "skip", "geen feitje", "no fact", "unknown", "onbekend"}


async def async_maybe_append_ambient_fact(
    hass: HomeAssistant,
    runtime: Any,
    playback: dict[str, Any],
) -> dict[str, Any] | None:
    """Append one text-only Ask DJ fact when Spotify moves to another artist/album."""
    if not _playback_is_active(playback):
        return None
    key = _ambient_album_artist_key(playback)
    if not key or key == getattr(runtime, "last_ambient_fact_key", None):
        return None
    request_payload = _ambient_request_payload(runtime, playback)
    history = getattr(runtime, "ask_dj_history", None)
    if history is not None:
        has_message = getattr(history, "async_has_client_message_id", None)
        if callable(has_message) and await has_message(None, request_payload["client_message_id"]):
            runtime.last_ambient_fact_key = key
            return None
    runtime.last_ambient_fact_key = key
    text = await _generate_ambient_fact(hass, runtime, playback)
    if not text:
        return None
    images, links = await _ambient_fact_media(hass, playback, _ambient_language(hass, runtime, getattr(runtime, "config", {}) or {}, _assist_context(hass, getattr(runtime, "config", {}) or {})))
    response = {
        "success": True,
        "text": text,
        "dj_text": text,
        "message": text,
        "intent": {
            "category": "informational",
            "intent": AMBIENT_FACT_INTENT,
            "action": AMBIENT_FACT_ACTION,
        },
        "action": AMBIENT_FACT_ACTION,
        "message_kind": "system",
        "origin": "spotify_playback_context",
        "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
        "links": links,
        "images": images,
        "playback_actions": [],
    }
    if history is not None:
        appender = getattr(history, "async_append_assistant_message", None)
        if callable(appender):
            await appender(None, request_payload, response)
    memory = getattr(runtime, "memory", None)
    if memory is not None:
        updater = getattr(memory, "async_update_last_ask_dj", None)
        if callable(updater):
            await updater(
                runtime,
                input_text="",
                result={"intent": response["intent"], "dj_text": text, "playback": playback},
                payload=_ambient_identity_payload(runtime),
                user_id=None,
            )
    return response


async def _generate_ambient_fact(
    hass: HomeAssistant,
    runtime: Any,
    playback: dict[str, Any],
) -> str:
    """Generate a short reliable text-only fact through HA conversation."""
    conf = getattr(runtime, "config", {}) or {}
    assist_context = _assist_context(hass, conf)
    language = _ambient_language(hass, runtime, conf, assist_context)
    prompt = _ambient_fact_prompt(playback, language)
    try:
        data = {"text": prompt, "language": language}
        if assist_context.get("agent_id"):
            data["agent_id"] = assist_context["agent_id"]
        result = await call_conversation_process_with_agent_retry(hass, data)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect ambient Ask DJ fact generation unavailable: %s", exc)
        return ""
    text = _speech_from_response((result or {}).get("response") or {}).strip()
    if _should_skip_fact(text):
        return ""
    return text


def _ambient_language(
    hass: HomeAssistant,
    runtime: Any,
    conf: dict[str, Any],
    assist_context: dict[str, Any],
) -> str:
    """Resolve the user-facing language for ambient Ask DJ system messages."""
    ha_language = str(getattr(getattr(hass, "config", None), "language", "") or "").strip()
    if ha_language.lower().startswith("nl"):
        return "nl-NL"
    language_getter = getattr(runtime, "device_language", None)
    runtime_language = str(language_getter() or "").strip() if callable(language_getter) else ""
    for value in (
        runtime_language,
        str(conf.get(CONF_DEVICE_LANGUAGE) or "").strip(),
        str(conf.get(CONF_TTS_LANGUAGE) or "").strip(),
        str(assist_context.get("language") or "").strip(),
        ha_language,
        DEFAULT_TTS_LANGUAGE,
    ):
        if value:
            return "nl-NL" if value.lower().startswith("nl") else value
    return DEFAULT_TTS_LANGUAGE


def _ambient_fact_prompt(playback: dict[str, Any], language: str) -> str:
    artist = _playback_text(playback, "artist", "artist_name") or "unknown artist"
    album = _playback_text(playback, "album_name", "album") or "unknown album"
    track = _playback_text(playback, "track_name", "title", "name") or "unknown track"
    if str(language).lower().startswith("nl"):
        return (
            "Je bent DJConnect Ask DJ. Genereer een kort, leuk en betrouwbaar muziekfeitje "
            "voor in een chatvenster, zonder audio en zonder vraag van de gebruiker. "
            "Antwoord uitsluitend in het Nederlands. "
            "Gebruik alleen breed bekende kennis over deze artiest of dit album. "
            "Als je geen betrouwbaar feitje weet, antwoord exact met SKIP. "
            "Noem geen Spotify URI's en voer geen playbackactie uit. Maximaal twee korte zinnen.\n\n"
            f"Artiest: {artist}\nAlbum: {album}\nHuidig nummer: {track}"
        )
    return (
        "You are DJConnect Ask DJ. Generate one short, fun and reliable music fact "
        "for a chat UI, with no audio and no user question. Use only broadly known "
        "knowledge about this artist or album. If you do not know a reliable fact, "
        "reply exactly with SKIP. Do not include Spotify URIs and do not control playback. "
        "Use at most two short sentences.\n\n"
        f"Artist: {artist}\nAlbum: {album}\nCurrent track: {track}"
    )


async def _ambient_fact_media(
    hass: HomeAssistant,
    playback: dict[str, Any],
    language: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Fetch one artist image/source link for an ambient fact."""
    artist = _playback_text(playback, "artist", "artist_name")
    if not artist:
        return [], []
    summary = await _wikipedia_summary(hass, artist, language)
    if not summary:
        return [], []
    image_url = str(
        ((summary.get("thumbnail") or {}).get("source"))
        or ((summary.get("originalimage") or {}).get("source"))
        or ""
    ).strip()
    page_url = str(((summary.get("content_urls") or {}).get("desktop") or {}).get("page") or "").strip()
    title = str(summary.get("title") or artist).strip()
    description = str(summary.get("description") or "").strip()
    images: list[dict[str, str]] = []
    if image_url.startswith(("http://", "https://")):
        proxy_url = _register_image_proxy_url(hass, image_url)
        images.append(
            {
                "url": proxy_url,
                "thumbnail_url": proxy_url,
                "title": title,
                "subtitle": description,
                "kind": "artist_image",
                "source": "wikipedia",
            }
        )
    links: list[dict[str, str]] = []
    if page_url.startswith(("http://", "https://")):
        links.append(
            {
                "url": page_url,
                "title": title,
                "subtitle": description,
                "kind": "source",
                "source": "wikipedia",
            }
        )
    return images, links


async def _wikipedia_summary(
    hass: HomeAssistant,
    artist: str,
    language: str,
) -> dict[str, Any]:
    """Return a compact Wikipedia summary for an artist when available."""
    languages = ["nl", "en"] if str(language).lower().startswith("nl") else ["en"]
    session = async_get_clientsession(hass)
    for wiki_language in languages:
        url = f"https://{wiki_language}.wikipedia.org/api/rest_v1/page/summary/{quote(artist.replace(' ', '_'))}"
        try:
            async with session.get(url, headers={"Accept": "application/json"}) as response:
                if getattr(response, "status", 0) != 200:
                    continue
                data = await response.json(content_type=None)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect ambient image lookup unavailable: %s", exc)
            continue
        if isinstance(data, dict) and (((data.get("thumbnail") or {}).get("source")) or ((data.get("originalimage") or {}).get("source"))):
            return data
    return {}


def _register_image_proxy_url(hass: HomeAssistant, external_url: str) -> str:
    """Register an external image URL and return a Home Assistant proxy URL."""
    token = secrets.token_urlsafe(18)
    hass.data.setdefault(DOMAIN, {}).setdefault(IMAGE_PROXY_KEY, {})[token] = external_url
    return f"{API_IMAGE_PROXY_BASE}/{token}"


def _should_skip_fact(text: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    if normalized in _SKIP_VALUES:
        return True
    if "spotify:" in normalized or normalized.startswith(("{", "[")):
        return True
    prompt_leak = (
        "gebruik alleen breed bekende kennis",
        "antwoord exact met skip",
        "noem geen spotify",
        "voer geen playbackactie uit",
        "maximaal twee korte zinnen",
        "use only broadly known",
        "reply exactly with skip",
        "do not include spotify",
        "do not control playback",
        "use at most two short sentences",
        "je bent djconnect ask dj",
        "you are djconnect ask dj",
        "huidig nummer:",
        "current track:",
    )
    if any(phrase in normalized for phrase in prompt_leak):
        return True
    uncertain = (
        "ik heb niet genoeg",
        "niet genoeg betrouwbare",
        "i do not have enough",
        "i don't have enough",
        "cannot provide",
    )
    return any(phrase in normalized for phrase in uncertain)


def _playback_is_active(playback: dict[str, Any]) -> bool:
    return bool(playback.get("has_playback") and playback.get("is_playing"))


def _ambient_album_artist_key(playback: dict[str, Any]) -> str:
    artist = _normalize_key(_playback_text(playback, "artist", "artist_name"))
    album = _normalize_key(_playback_text(playback, "album_name", "album"))
    if not artist and not album:
        return ""
    return f"{artist}|{album}"


def _ambient_request_payload(runtime: Any, playback: dict[str, Any]) -> dict[str, Any]:
    identity = _ambient_identity_payload(runtime)
    return {
        **identity,
        "text": "",
        "message": "",
        "client_message_id": f"ambient:{_ambient_album_artist_key(playback)}",
    }


def _ambient_identity_payload(runtime: Any) -> dict[str, Any]:
    status = getattr(runtime, "device_status", {}) or {}
    client_type = ""
    getter = getattr(runtime, "client_type", None)
    if callable(getter):
        client_type = str(getter() or "").strip()
    return {
        "device_id": status.get("device_id") or getattr(runtime, "pairing_device_id", ""),
        "client_type": client_type or status.get("client_type") or "",
        "device_name": status.get("device_name") or "",
    }


def _playback_text(playback: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(playback.get(key) or "").strip()
        if value:
            return value
    track = playback.get("track")
    if isinstance(track, dict):
        for key in keys:
            value = str(track.get(key) or "").strip()
            if value:
                return value
    return ""


def _normalize_key(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())
