from __future__ import annotations

from typing import Any
from homeassistant.core import HomeAssistant

from .const import (
    CONF_TTS_LANGUAGE,
    DEFAULT_TTS_LANGUAGE,
)
from .pipeline import (
    _fallback_search_intent,
    correct_stt_text_with_assist,
    generate_dj_response_with_assist,
    process_text_with_assist,
)
from .memory import prompt_context_text
from .mood import enrich_payload_with_mood_zone
from .music_intent import parse_spoken_music_request
from .smart_home_context import smart_home_context, smart_home_context_text
from .spotify import play_from_intent
from .spotify_backend import SpotifyBackendError, handle_spotify_command


async def process_text_command(
    hass: HomeAssistant,
    runtime,
    user_text: str,
    play: bool = True,
    correct_stt: bool = False,
    memory_payload: dict[str, Any] | None = None,
    user_id: str | None = None,
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
    if _is_current_track_question(corrected_text):
        result = await _process_current_track_question(
            hass,
            runtime,
            corrected_text,
            user_text,
            memory_payload=memory_payload,
        )
        await _record_ask_dj_memory(
            runtime,
            corrected_text,
            result,
            memory_payload=memory_payload,
            user_id=user_id,
        )
        return result
    control = _playback_control_request(corrected_text)
    if control:
        result = await _process_playback_control_request(
            hass,
            runtime,
            corrected_text,
            user_text,
            control,
            memory_payload=memory_payload,
        )
        await _record_ask_dj_memory(
            runtime,
            corrected_text,
            result,
            memory_payload=memory_payload,
            user_id=user_id,
        )
        return result
    memory_context = await _memory_context_for_assist(
        runtime,
        memory_payload=memory_payload,
        user_id=user_id,
    )
    intent = _deterministic_playback_intent(corrected_text) or await _process_text_with_optional_memory(
        hass,
        corrected_text,
        conf,
        memory_context=memory_context,
    )
    runtime.update(last_intent=intent)
    playback = None
    if play:
        playback = await play_from_intent(hass, runtime, intent, conf)
    response_media = _with_mood_context(_dj_response_media(intent, playback), memory_payload, runtime)
    fallback_dj_text = _dj_response_text(intent, playback, conf, media=response_media)
    dj_response_debug: dict[str, Any] = {}
    dj_text = await generate_dj_response_with_assist(
        hass,
        media=response_media,
        fallback_text=fallback_dj_text,
        conf=conf,
        memory_context=_announcement_context(hass, runtime, memory_context),
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
    await _record_ask_dj_memory(
        runtime,
        corrected_text,
        result,
        memory_payload=memory_payload,
        user_id=user_id,
    )
    return result


async def _memory_context_for_assist(
    runtime: Any,
    *,
    memory_payload: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> str | None:
    memory = getattr(runtime, "memory", None)
    if memory is None:
        return None
    context_getter = getattr(memory, "async_context_for_runtime", None)
    if not callable(context_getter):
        return None
    context = await context_getter(runtime, memory_payload, user_id=user_id)
    return prompt_context_text(context)


def _deterministic_playback_intent(text: str) -> dict[str, Any]:
    """Use the local parser for clear artist playback requests to avoid stale Assist context."""
    parsed = parse_spoken_music_request(text)
    media_type = str(parsed.get("type") or "").strip().lower()
    query = str(parsed.get("query") or "").strip()
    artist = str(parsed.get("artist") or "").strip()
    if media_type != "artist" or not query:
        return {}
    if not _is_clear_artist_play_request(text, artist or query):
        return {}
    return {
        "intent": "play_music",
        "type": "artist",
        "artist": artist or query,
        "title": None,
        "playlist": None,
        "query": query,
        "spotify_search_query": query,
        "dj_announcement": "Daar gaan we. Ik zet hem voor je klaar.",
    }


def _is_clear_artist_play_request(text: str, artist: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    if not normalized.startswith(("speel ", "start ", "draai ", "zet ", "play ", "put on ")):
        return False
    artist_normalized = " ".join(str(artist or "").strip().lower().split())
    if not artist_normalized:
        return False
    return artist_normalized.startswith("dj ") or len(artist_normalized.split()) >= 2


async def _process_text_with_optional_memory(
    hass: HomeAssistant,
    corrected_text: str,
    conf: dict[str, Any],
    *,
    memory_context: str | None,
) -> dict[str, Any]:
    try:
        return await process_text_with_assist(
            hass,
            corrected_text,
            conf,
            memory_context=memory_context,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        try:
            return await process_text_with_assist(hass, corrected_text, conf)
        except Exception:
            return _fallback_search_intent(corrected_text)
    except Exception:
        return _fallback_search_intent(corrected_text)


def _with_mood_context(
    media: dict[str, Any],
    memory_payload: dict[str, Any] | None,
    runtime: Any,
) -> dict[str, Any]:
    """Attach request or latest status mood to DJ announcement media."""
    payload: dict[str, Any] = dict(memory_payload or {})
    if payload.get("mood") is None:
        status = getattr(runtime, "device_status", None)
        if isinstance(status, dict):
            payload["mood"] = status.get("mood")
    enriched = enrich_payload_with_mood_zone(payload)
    if enriched.get("mood_zone") is None:
        return media
    merged = dict(media)
    merged["mood"] = enriched["mood"]
    merged["mood_zone"] = enriched["mood_zone"]
    merged["mood_zone_prompt"] = enriched.get("mood_zone_prompt")
    return merged


async def _record_ask_dj_memory(
    runtime: Any,
    corrected_text: str,
    result: dict[str, Any],
    *,
    memory_payload: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    memory = getattr(runtime, "memory", None)
    recorder = getattr(memory, "async_update_last_ask_dj", None)
    if not callable(recorder):
        return
    await recorder(
        runtime,
        input_text=corrected_text,
        result=result,
        payload=memory_payload,
        user_id=user_id,
    )


async def _process_playback_control_request(
    hass: HomeAssistant,
    runtime,
    corrected_text: str,
    user_text: str,
    control: dict[str, Any],
    *,
    memory_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute simple DJ playback controls without running music search."""
    conf = runtime.config
    intent = {
        "intent": "playback_control",
        "type": "playback_control",
        "action": control["action"],
        "query": corrected_text,
        "spotify_search_query": "",
        "dj_announcement": "",
    }
    runtime.update(last_intent=intent)
    playback = await _execute_playback_control(hass, runtime, control)
    media = _with_mood_context(_playback_control_media(playback, intent), memory_payload, runtime)
    fallback_dj_text = _playback_control_response_text(control, playback, conf)
    dj_response_debug: dict[str, Any] = {}
    dj_text = await generate_dj_response_with_assist(
        hass,
        media=media,
        fallback_text=fallback_dj_text,
        conf=conf,
        memory_context=_announcement_context(hass, runtime),
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


async def _execute_playback_control(
    hass: HomeAssistant,
    runtime,
    control: dict[str, Any],
) -> dict[str, Any]:
    action = str(control.get("action") or "").strip()
    try:
        if action == "pause":
            response = await handle_spotify_command(hass, runtime, "pause")
        elif action == "play":
            response = await handle_spotify_command(hass, runtime, "play")
        elif action == "next":
            response = await handle_spotify_command(hass, runtime, "next")
        elif action == "previous":
            response = await handle_spotify_command(hass, runtime, "previous")
        elif action == "volume_delta":
            status = await handle_spotify_command(hass, runtime, "status")
            playback = status.get("playback") if isinstance(status, dict) else None
            current = _playback_volume(playback, runtime)
            if current is None:
                return {
                    "has_playback": False,
                    "is_playing": False,
                    "backend_available": True,
                    "volume_unknown": True,
                }
            target = max(0, min(60, current + int(control.get("delta") or 0)))
            response = await handle_spotify_command(hass, runtime, "set_volume", target)
            playback = response.get("playback") if isinstance(response, dict) else None
            if isinstance(playback, dict):
                playback = dict(playback)
                playback["requested_volume_percent"] = target
                return playback
            return {
                "has_playback": bool(playback),
                "backend_available": True,
                "requested_volume_percent": target,
            }
        else:
            raise ValueError(f"Unsupported playback control: {action}")
    except SpotifyBackendError as exc:
        return {
            "has_playback": False,
            "is_playing": False,
            "backend_available": False,
            "unknown": True,
            "message": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "has_playback": False,
            "is_playing": False,
            "backend_available": False,
            "unknown": True,
            "message": str(exc),
        }
    playback = response.get("playback") if isinstance(response, dict) else None
    if isinstance(playback, dict):
        return playback
    return {
        "has_playback": False,
        "is_playing": False,
        "backend_available": True,
    }


async def _process_current_track_question(
    hass: HomeAssistant,
    runtime,
    corrected_text: str,
    user_text: str,
    *,
    memory_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Answer which Spotify track is active without starting playback."""
    conf = runtime.config
    intent = {
        "intent": "current_track",
        "type": "current_track",
        "query": corrected_text,
        "spotify_search_query": "",
        "dj_announcement": "",
    }
    runtime.update(last_intent=intent)
    playback = await _lookup_current_playback(hass, runtime)
    media = _with_mood_context(_current_playback_media(playback), memory_payload, runtime)
    fallback_dj_text = _current_track_response_text(playback, conf)
    dj_response_debug: dict[str, Any] = {}
    dj_text = await generate_dj_response_with_assist(
        hass,
        media=media or intent,
        fallback_text=fallback_dj_text,
        conf=conf,
        memory_context=_announcement_context(hass, runtime),
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


def _announcement_context(
    hass: HomeAssistant,
    runtime,
    memory_context: str | None = None,
) -> str:
    """Return compact context for personal DJ announcement intros."""
    parts = [str(memory_context or "").strip()]
    home_context = smart_home_context(hass, runtime)
    home_text = smart_home_context_text(home_context)
    if home_text:
        parts.append(
            "Expliciet gedeelde smart-home context voor persoonlijke intro's: "
            f"{home_text}"
        )
    return "\n".join(part for part in parts if part)


async def _lookup_current_playback(
    hass: HomeAssistant,
    runtime,
) -> dict[str, Any]:
    """Fetch current Spotify playback, returning an answerable empty state on failure."""
    try:
        response = await handle_spotify_command(hass, runtime, "status")
    except SpotifyBackendError as exc:
        return {
            "has_playback": False,
            "is_playing": False,
            "backend_available": False,
            "unknown": True,
            "message": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "has_playback": False,
            "is_playing": False,
            "backend_available": False,
            "unknown": True,
            "message": str(exc),
        }
    playback = response.get("playback") if isinstance(response, dict) else None
    if isinstance(playback, dict):
        return playback
    return {
        "has_playback": False,
        "is_playing": False,
        "backend_available": True,
    }


def _is_current_track_question(text: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    normalized = normalized.strip(" ?!.")
    if not normalized:
        return False
    question_starts = (
        "welk nummer",
        "welk liedje",
        "welke track",
        "wat draait",
        "wat speelt",
        "wat is dit",
        "what song",
        "what track",
        "what is playing",
        "what's playing",
        "which song",
        "which track",
    )
    if not normalized.startswith(question_starts):
        return False
    return any(
        fragment in normalized
        for fragment in (
            "draait",
            "speelt",
            "nu",
            "playing",
            "song",
            "track",
            "dit",
        )
    )


def _playback_control_request(text: str) -> dict[str, Any] | None:
    normalized = " ".join(str(text or "").strip().lower().split())
    normalized = normalized.strip(" ?!.")
    if not normalized:
        return None
    if normalized in {
        "stop muziek",
        "stop de muziek",
        "pauzeer muziek",
        "pauzeer de muziek",
        "muziek pauzeren",
        "pause music",
        "stop music",
    }:
        return {"action": "pause"}
    if normalized in {
        "start muziek",
        "start de muziek",
        "speel muziek",
        "hervat muziek",
        "hervat de muziek",
        "ga verder",
        "play music",
        "resume music",
        "start music",
    }:
        return {"action": "play"}
    if normalized in {
        "zet harder",
        "zet de muziek harder",
        "muziek harder",
        "harder",
        "volume omhoog",
        "turn it up",
        "volume up",
        "louder",
    }:
        return {"action": "volume_delta", "delta": 10}
    if normalized in {
        "zet zachter",
        "zet de muziek zachter",
        "muziek zachter",
        "zachter",
        "volume omlaag",
        "turn it down",
        "volume down",
        "quieter",
    }:
        return {"action": "volume_delta", "delta": -10}
    if normalized in {
        "volgende nummer",
        "volgend nummer",
        "volgende track",
        "volgend liedje",
        "skip",
        "nummer overslaan",
        "next song",
        "next track",
    }:
        return {"action": "next"}
    if normalized in {
        "vorig nummer",
        "vorige nummer",
        "vorige track",
        "vorig liedje",
        "terug",
        "previous song",
        "previous track",
    }:
        return {"action": "previous"}
    return None


def _playback_control_media(
    playback: dict[str, Any] | None,
    intent: dict[str, Any],
) -> dict[str, Any]:
    media = {"type": "playback_control", "action": intent.get("action")}
    if isinstance(playback, dict):
        media.update(_current_playback_media(playback))
        media["type"] = "playback_control"
        media["action"] = intent.get("action")
        if playback.get("requested_volume_percent") is not None:
            media["requested_volume_percent"] = playback.get("requested_volume_percent")
    return media


def _playback_control_response_text(
    control: dict[str, Any],
    playback: dict[str, Any] | None,
    conf: dict[str, Any],
) -> str:
    language = str(conf.get(CONF_TTS_LANGUAGE) or DEFAULT_TTS_LANGUAGE)
    is_nl = language.lower().startswith("nl")
    if isinstance(playback, dict) and (
        playback.get("unknown") or playback.get("backend_available") is False
    ):
        return (
            "Ik kan Spotify nu niet bedienen."
            if is_nl
            else "I cannot control Spotify right now."
        )
    action = str(control.get("action") or "")
    if action == "pause":
        return "Ik zet de muziek op pauze." if is_nl else "Pausing the music."
    if action == "play":
        return "Ik start de muziek weer." if is_nl else "Starting the music again."
    if action == "volume_delta":
        if isinstance(playback, dict) and playback.get("volume_unknown"):
            return (
                "Ik kan het huidige Spotify volume nu niet bepalen."
                if is_nl
                else "I cannot determine the current Spotify volume right now."
            )
        target = playback.get("requested_volume_percent") if isinstance(playback, dict) else None
        if target is not None:
            return (
                f"Ik zet het volume op {target}."
                if is_nl
                else f"Setting the volume to {target}."
            )
        return "Ik pas het volume aan." if is_nl else "Adjusting the volume."
    if action == "next":
        return "Ik ga naar het volgende nummer." if is_nl else "Skipping to the next track."
    if action == "previous":
        return "Ik ga terug naar het vorige nummer." if is_nl else "Going back to the previous track."
    return "Ik regel het voor je." if is_nl else "I'll take care of it."


def _playback_volume(playback: Any, runtime: Any) -> int | None:
    for source in (playback, getattr(runtime, "last_playback", None)):
        if not isinstance(source, dict):
            continue
        value = source.get("volume_percent")
        if value is None:
            device = source.get("device") or {}
            value = device.get("volume_percent") if isinstance(device, dict) else None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def _current_playback_media(playback: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(playback, dict) or not playback.get("has_playback"):
        return {"type": "current_track", "has_playback": False}
    media: dict[str, Any] = {
        "type": "current_track",
        "has_playback": True,
        "is_playing": playback.get("is_playing"),
    }
    for key in (
        "track_name",
        "title",
        "artist",
        "artist_name",
        "album_name",
        "album",
        "uri",
        "media_image_url",
        "album_image_url",
    ):
        value = playback.get(key)
        if value not in (None, "", [], {}):
            media[key] = value
    if media.get("track_name") and not media.get("title"):
        media["title"] = media["track_name"]
    if media.get("title") and not media.get("track_name"):
        media["track_name"] = media["title"]
    return media


def _current_track_response_text(
    playback: dict[str, Any] | None,
    conf: dict[str, Any],
) -> str:
    language = str(conf.get(CONF_TTS_LANGUAGE) or DEFAULT_TTS_LANGUAGE)
    is_nl = language.lower().startswith("nl")
    if not isinstance(playback, dict):
        return _unknown_current_track_response(is_nl=is_nl)
    if playback.get("unknown") or playback.get("backend_available") is False:
        return _unknown_current_track_response(is_nl=is_nl)
    if not playback.get("has_playback"):
        return (
            "Er draait nu geen nummer, voor zover ik kan zien."
            if is_nl
            else "I do not see a track playing right now."
        )
    title = _first_text(playback, "track_name", "title", "name")
    artist = _first_text(playback, "artist", "artist_name")
    album = _first_text(playback, "album_name", "album")
    if title or artist:
        prefix = "Nu draait" if playback.get("is_playing") else "Nu staat klaar"
        if not is_nl:
            prefix = "Now playing" if playback.get("is_playing") else "Currently queued"
        if album and artist and title:
            return (
                f"{prefix} {title} van {artist}. Van {album}."
                if is_nl
                else f"{prefix}: {title} by {artist}, from {album}."
            )
        subject = _track_subject(title, artist, is_nl=is_nl)
        return f"{prefix} {subject}." if is_nl else f"{prefix}: {subject}."
    return _unknown_current_track_response(is_nl=is_nl)


def _unknown_current_track_response(*, is_nl: bool) -> str:
    return (
        "Ik kan nu niet zien welk nummer er draait."
        if is_nl
        else "I cannot tell which track is playing right now."
    )


def _dj_response_text(
    intent: dict[str, Any],
    playback: dict[str, Any] | None,
    conf: dict[str, Any],
    *,
    media: dict[str, Any] | None = None,
) -> str:
    """Create a concrete device DJ response from the resolved playback result."""
    media = media or _dj_response_media(intent, playback)
    media_type = str(media.get("type") or intent.get("type") or "").strip().lower()
    title = _first_text(media, "track_name", "title", "name")
    artist = _first_text(media, "artist", "artist_name")
    album = _first_text(media, "album_name", "album")
    playlist = _first_text(media, "playlist", "name")
    language = str(conf.get(CONF_TTS_LANGUAGE) or DEFAULT_TTS_LANGUAGE)
    is_nl = language.lower().startswith("nl")

    if media_type == "album" and (album or artist):
        return _album_response(
            album=album or title,
            artist=artist,
            first_track=title if title != album else "",
            is_nl=is_nl,
        )
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
    device_response_media = _device_response_media(playback)
    if intent_media and _media_context_conflicts(intent_media, resolved):
        return intent_media
    if resolved:
        return _merge_media_context(resolved, device_response_media)
    if intent_media and _media_context_conflicts(intent_media, device_response_media):
        return intent_media
    if playback.get("media_content_id"):
        return _merge_media_context(intent_media or intent, device_response_media)
    return device_response_media or intent_media or intent


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
        elif media_type == "album" and not media.get("album"):
            media["album"] = query
        elif media_type == "track" and not media.get("title"):
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


def _device_response_media(playback: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(playback, dict):
        return {}
    response = playback.get("device_response") or {}
    if not isinstance(response, dict):
        return {}
    current = response.get("playback") or response
    return current if isinstance(current, dict) else {}


def _merge_media_context(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Add current playback metadata without losing the resolved search target."""
    merged = dict(base)
    if _conflicting_artist(base, extra):
        return merged
    for key, value in extra.items():
        if value in (None, "", [], {}):
            continue
        if not merged.get(key):
            merged[key] = value
    for source, target in (("track_name", "title"), ("title", "track_name")):
        if merged.get(source) and not merged.get(target):
            merged[target] = merged[source]
    return merged


def _conflicting_artist(base: dict[str, Any], extra: dict[str, Any]) -> bool:
    base_artist = _normalized_text(_first_text(base, "artist", "artist_name"))
    extra_artist = _normalized_text(_first_text(extra, "artist", "artist_name"))
    return bool(base_artist and extra_artist and base_artist != extra_artist)


def _media_context_conflicts(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    if not expected or not actual:
        return False
    pairs = (
        (("artist", "artist_name"), ("artist", "artist_name")),
        (("title", "track", "track_name", "name"), ("title", "track", "track_name", "name")),
        (("album", "album_name"), ("album", "album_name")),
        (("playlist", "name"), ("playlist", "name")),
    )
    for expected_keys, actual_keys in pairs:
        expected_value = _normalized_text(_first_text(expected, *expected_keys))
        actual_value = _normalized_text(_first_text(actual, *actual_keys))
        if expected_value and actual_value and expected_value != actual_value:
            return True
    return False


def _normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def _track_response(
    *,
    title: str,
    artist: str,
    album: str,
    is_nl: bool,
) -> str:
    subject = _track_subject(title, artist, is_nl=is_nl)
    if album and artist and not title:
        return (
            f"Daar is {album} van {artist}."
            if is_nl
            else f"Here is {album} by {artist}."
        )
    if album and artist:
        return (
            f"Daar is {artist}, met {title}. Van {album}."
            if is_nl
            else f"Here is {title} by {artist}, from {album}."
        )
    return f"Daar is {subject}." if is_nl else f"Here is {subject}."


def _album_response(
    *,
    album: str,
    artist: str,
    first_track: str,
    is_nl: bool,
) -> str:
    if is_nl:
        if artist and album and first_track:
            return f"Je luistert naar {artist} met hun album {album}. Hier is het eerste nummer op het album, {first_track}."
        if artist and album:
            return f"Je luistert naar {artist} met hun album {album}."
        if album:
            return f"Je luistert naar het album {album}."
        return f"Je luistert naar {artist}."
    if artist and album and first_track:
        return f"You're listening to {album} by {artist}. Here's the first track on the album, {first_track}."
    if artist and album:
        return f"You're listening to {album} by {artist}."
    if album:
        return f"You're listening to the album {album}."
    return f"You're listening to {artist}."


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
