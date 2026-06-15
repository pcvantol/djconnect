from __future__ import annotations

from typing import Any
from homeassistant.core import HomeAssistant

from .const import (
    CONF_TTS_LANGUAGE,
    DEFAULT_TTS_LANGUAGE,
)
from .pipeline import (
    correct_stt_text_with_assist,
    generate_dj_response_with_assist,
    process_text_with_assist,
)
from .spotify import play_from_intent


async def process_text_command(
    hass: HomeAssistant,
    runtime,
    user_text: str,
    play: bool = True,
    correct_stt: bool = False,
) -> dict[str, Any]:
    conf = runtime.config
    corrected_text = (
        await correct_stt_text_with_assist(hass, user_text, conf)
        if correct_stt
        else user_text
    )
    runtime.update(
        last_text=corrected_text,
        last_stt_text=user_text,
        last_corrected_text=corrected_text if corrected_text != user_text else None,
        last_error=None,
    )
    intent = await process_text_with_assist(hass, corrected_text, conf)
    runtime.update(last_intent=intent)
    playback = None
    if play:
        playback = await play_from_intent(hass, runtime, intent, conf)
    response_media = _dj_response_media(intent, playback)
    fallback_dj_text = _dj_response_text(intent, playback, conf, media=response_media)
    dj_response_debug: dict[str, Any] = {}
    dj_text = await generate_dj_response_with_assist(
        hass,
        media=response_media,
        fallback_text=fallback_dj_text,
        conf=conf,
        debug=dj_response_debug,
    )
    result = {
        "text": corrected_text,
        "stt_text": user_text,
        "corrected_text": corrected_text if corrected_text != user_text else None,
        "intent": intent,
        "playback": playback,
        "dj_text": dj_text,
    }
    runtime.update(
        last_intent=intent,
        last_dj_text=dj_text,
        last_dj_response_debug=dj_response_debug,
        last_playback=playback,
        last_error=None,
    )
    return result


def _dj_response_text(
    intent: dict[str, Any],
    playback: dict[str, Any] | None,
    conf: dict[str, Any],
    *,
    media: dict[str, Any] | None = None,
) -> str:
    """Create a concrete device DJ response from the resolved playback result."""
    media = media or _dj_response_media(intent, playback)
    title = _first_text(media, "track_name", "title", "name")
    artist = _first_text(media, "artist", "artist_name")
    album = _first_text(media, "album_name", "album")
    playlist = _first_text(media, "playlist", "name")
    language = str(conf.get(CONF_TTS_LANGUAGE) or DEFAULT_TTS_LANGUAGE)
    is_nl = language.lower().startswith("nl")

    if title or artist:
        return _track_response(
            title=title,
            artist=artist,
            album=album,
            is_nl=is_nl,
        )
    if playlist:
        return _playlist_response(playlist, is_nl=is_nl)

    announcement = str(intent.get("dj_announcement") or "").strip()
    if announcement and not _is_generic_announcement(announcement):
        return announcement
    return "Daar gaan we. Ik zet hem voor je klaar." if is_nl else "Here we go. I'll start it for you."


def _dj_response_media(
    intent: dict[str, Any],
    playback: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return media metadata for the spoken DJ response without reusing stale playback."""
    intent_media = _intent_media_context(intent)
    if not isinstance(playback, dict):
        return intent_media or intent
    resolved = _resolved_media(playback, allow_device_response=False)
    if resolved:
        return resolved
    if playback.get("media_content_id"):
        return intent_media or intent
    return _resolved_media(playback, allow_device_response=True) or intent_media or intent


def _intent_media_context(intent: dict[str, Any]) -> dict[str, Any]:
    """Return concrete parsed media fields from the user intent."""
    media_type = str(intent.get("type") or "").strip()
    media: dict[str, Any] = {"type": media_type} if media_type else {}
    for key in ("artist", "title", "track", "album", "playlist", "name"):
        value = intent.get(key)
        if value not in (None, ""):
            media[key] = value
    query = str(intent.get("spotify_search_query") or intent.get("query") or "").strip()
    if query:
        if media_type == "artist" and not media.get("artist"):
            media["artist"] = query
        elif media_type == "playlist" and not media.get("playlist"):
            media["playlist"] = query
        elif media_type in {"track", "album"} and not media.get("title") and not media.get("album"):
            media["title"] = query
    return media


def _resolved_media(
    playback: dict[str, Any] | None,
    *,
    allow_device_response: bool = True,
) -> dict[str, Any]:
    if not isinstance(playback, dict):
        return {}
    resolved = playback.get("resolved_media")
    if isinstance(resolved, dict) and any(resolved.get(key) for key in ("title", "track_name", "artist")):
        return resolved
    if not allow_device_response:
        return {}
    response = playback.get("device_response") or {}
    if isinstance(response, dict):
        current = response.get("playback") or response
        if isinstance(current, dict):
            return current
    return {}


def _track_response(
    *,
    title: str,
    artist: str,
    album: str,
    is_nl: bool,
) -> str:
    subject = _track_subject(title, artist, is_nl=is_nl)
    if album and artist:
        return f"Daar is {artist}, met {title}. Van {album}." if is_nl else f"Here is {title} by {artist}, from {album}."
    return f"Daar is {subject}." if is_nl else f"Here is {subject}."


def _playlist_response(playlist: str, *, is_nl: bool) -> str:
    return f"Ik zet {playlist} voor je klaar." if is_nl else f"I'll start {playlist} for you."


def _track_subject(title: str, artist: str, *, is_nl: bool) -> str:
    if title and artist:
        return f"{title} van {artist}" if is_nl else f"{title} by {artist}"
    return title or artist


def _first_text(source: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(source.get(key) or "").strip()
        if value:
            return value
    return ""


def _is_generic_announcement(value: str) -> bool:
    normalized = " ".join(value.lower().split())
    return normalized in {
        "daar gaan we.",
        "daar gaan we",
        "daar gaan we. ik zet hem voor je klaar.",
        "ik zet hem voor je klaar.",
        "here we go.",
        "here we go",
        "here we go. i'll start it for you.",
    }
