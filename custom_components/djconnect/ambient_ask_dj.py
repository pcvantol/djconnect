"""Ambient Ask DJ messages triggered by backend playback context changes."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DEFAULT_TTS_LANGUAGE
from .pipeline import _assist_context, _speech_from_response

_LOGGER = logging.getLogger(__name__)

AMBIENT_FACT_INTENT = "ambient_music_fact"
AMBIENT_FACT_ACTION = "none"
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
    runtime.last_ambient_fact_key = key
    text = await _generate_ambient_fact(hass, runtime, playback)
    if not text:
        return None
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
        "links": [],
        "images": [],
        "playback_actions": [],
    }
    history = getattr(runtime, "ask_dj_history", None)
    if history is not None:
        appender = getattr(history, "async_append_assistant_message", None)
        if callable(appender):
            await appender(None, _ambient_request_payload(runtime, playback), response)
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
    language = assist_context.get("language") or conf.get("tts_language") or DEFAULT_TTS_LANGUAGE
    prompt = _ambient_fact_prompt(playback, language)
    try:
        data = {"text": prompt, "language": language}
        if assist_context.get("agent_id"):
            data["agent_id"] = assist_context["agent_id"]
        result = await hass.services.async_call(
            "conversation",
            "process",
            data,
            blocking=True,
            return_response=True,
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect ambient Ask DJ fact generation unavailable: %s", exc)
        return ""
    text = _speech_from_response((result or {}).get("response") or {}).strip()
    if _should_skip_fact(text):
        return ""
    return text


def _ambient_fact_prompt(playback: dict[str, Any], language: str) -> str:
    artist = _playback_text(playback, "artist", "artist_name") or "unknown artist"
    album = _playback_text(playback, "album_name", "album") or "unknown album"
    track = _playback_text(playback, "track_name", "title", "name") or "unknown track"
    if str(language).lower().startswith("nl"):
        return (
            "Je bent DJConnect Ask DJ. Genereer een kort, leuk en betrouwbaar muziekfeitje "
            "voor in een chatvenster, zonder audio en zonder vraag van de gebruiker. "
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


def _should_skip_fact(text: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    if normalized in _SKIP_VALUES:
        return True
    if "spotify:" in normalized or normalized.startswith(("{", "[")):
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
