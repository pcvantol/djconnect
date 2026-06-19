"""Ask DJ backend support."""
from __future__ import annotations

from dataclasses import dataclass
import logging
import secrets
from typing import Any
from urllib.parse import urlsplit

from homeassistant.core import HomeAssistant

from .const import (
    API_IMAGE_PROXY_BASE,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    DEFAULT_TTS_LANGUAGE,
    DOMAIN,
)
from .dj_response import async_send_dj_response_best_effort
from .memory import prompt_context_text
from .pipeline import _assist_context, _speech_from_response
from .processor import process_text_command
from .spotify_backend import handle_spotify_command

_LOGGER = logging.getLogger(__name__)

IMAGE_PROXY_KEY = "image_proxy"


@dataclass(frozen=True)
class AskDjIntent:
    """Classified Ask DJ intent."""

    category: str
    intent: str
    action: str | None = None
    value: Any | None = None
    play: bool = False


async def async_handle_ask_dj(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Handle a text Ask DJ request and return the client response shape."""
    text = str(payload.get("text") or payload.get("message") or "").strip()
    if not text:
        return _error_response("missing_text", "Ask DJ needs text to answer.")

    identity_payload = _identity_payload(runtime, payload)
    memory = getattr(runtime, "memory", None)
    memory_context: dict[str, Any] = {}
    memory_key = str(payload.get("memory_key") or "").strip() or None
    if memory is not None:
        memory_context = await memory.async_context_for_runtime(
            runtime,
            identity_payload,
            user_id=user_id,
        )
        memory_key = memory_context.get("memory_key") or memory_key
    history = getattr(runtime, "ask_dj_history", None)
    if history is not None:
        loader = getattr(history, "async_load", None)
        if callable(loader):
            await loader()
        recent = history.recent_messages_for_prompt(user_id)
        if recent:
            memory_context["server_history"] = recent

    classification = classify_ask_dj(text)
    if (
        _is_voice_input(payload)
        and classification.category == "informational"
        and classification.intent == "ask_music_info"
        and _looks_like_bare_voice_music_request(text)
    ):
        classification = AskDjIntent("hybrid", "play_music", "play_music", play=True)
    playback_context = await _playback_context(hass, runtime)
    output_devices = await _output_devices(hass, runtime, classification)

    try:
        if classification.category == "action":
            result = await _handle_action(hass, runtime, text, classification)
        elif classification.category == "hybrid":
            result = await _handle_hybrid(hass, runtime, text, classification, payload)
        else:
            result = await _handle_informational(
                hass,
                runtime,
                text,
                payload,
                memory_context,
                playback_context,
                output_devices,
            )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("DJConnect Ask DJ failed: %s", exc)
        return _error_response(
            "ask_dj_unavailable",
            "Ask DJ is nu niet bereikbaar.",
            memory_key=memory_key,
        )

    response = _normalize_ask_dj_response(
        hass,
        runtime,
        result,
        classification,
        memory_key=memory_key,
        playback_context=playback_context,
    )

    if memory is not None:
        await memory.async_update_last_ask_dj(
            runtime,
            input_text=text,
            result={
                "intent": response.get("intent") or {},
                "dj_text": response.get("dj_text") or response.get("text"),
                "playback": response.get("playback") or playback_context,
            },
            payload=identity_payload,
            user_id=user_id,
        )

    if response.get("dj_text") and _should_generate_audio_response(payload, classification):
        try:
            dj_response = await async_send_dj_response_best_effort(
                hass,
                runtime,
                str(response.get("dj_text") or ""),
            )
            audio_url = dj_response.get("audio_url_value")
            if audio_url:
                response["audio_url"] = audio_url
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect Ask DJ audio response unavailable: %s", exc)
    response.pop("playback", None)
    return response


def _should_generate_audio_response(
    payload: dict[str, Any],
    classification: AskDjIntent,
) -> bool:
    mode = str(payload.get("audio_response") or "auto").strip().lower()
    if mode in {"always", "true", "1", "yes"}:
        return True
    if mode in {"never", "false", "0", "no", "none", "text_only"}:
        return False
    input_type = str(payload.get("input_type") or "").strip().lower()
    if input_type in {"voice", "ptt", "audio"}:
        return True
    return classification.category in {"action", "hybrid"}


def _is_voice_input(payload: dict[str, Any]) -> bool:
    return str(payload.get("input_type") or "").strip().lower() in {"voice", "ptt", "audio"}


def _looks_like_bare_voice_music_request(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False
    if any(
        normalized.startswith(prefix)
        for prefix in (
            "waarom",
            "wat ",
            "wie ",
            "welke ",
            "wanneer",
            "hoe ",
            "vertel",
            "analyseer",
            "omschrijf",
            "maak een profiel",
        )
    ):
        return False
    if any(token in normalized for token in ("?", "playlist", "volume", "harder", "zachter", "shuffle", "repeat")):
        return False
    words = normalized.split()
    return 1 <= len(words) <= 8


def classify_ask_dj(text: str) -> AskDjIntent:
    """Classify Ask DJ text into informational, action or hybrid buckets."""
    normalized = _normalize(text)
    if _is_personal_music_profile_request(normalized):
        return AskDjIntent(
            "informational",
            "personal_music_profile_analysis",
            "profile_analysis",
        )
    if _is_personal_recommendation_request(normalized):
        return AskDjIntent(
            "informational",
            "personal_music_recommendations",
            "none",
        )
    if any(phrase in normalized for phrase in ("waarom koos", "waarom heb je", "vertel iets", "wanneer speelt", "analyseer", "welke albums", "album art", "cover")):
        return AskDjIntent("informational", "ask_music_info")
    if any(phrase in normalized for phrase in ("aankondiging", "dj intro", "intro voor", "wat nu speelt")):
        return AskDjIntent("hybrid", "dj_announcement", "announce", play=False)
    if any(word in normalized for word in ("pauzeer", "stop muziek", "stop de muziek")):
        return AskDjIntent("action", "playback_control", "pause")
    if any(phrase in normalized for phrase in ("start muziek", "speel verder", "resume")):
        return AskDjIntent("action", "playback_control", "play")
    if "volgende" in normalized:
        return AskDjIntent("action", "playback_control", "next")
    if "vorige" in normalized or "vorig nummer" in normalized:
        return AskDjIntent("action", "playback_control", "previous")
    if "harder" in normalized:
        return AskDjIntent("action", "playback_control", "volume_delta", 10)
    if "zachter" in normalized:
        return AskDjIntent("action", "playback_control", "volume_delta", -10)
    if "shuffle" in normalized:
        return AskDjIntent("action", "playback_control", "set_shuffle", "uit" not in normalized)
    if "repeat" in normalized or "herhaal" in normalized:
        return AskDjIntent(
            "action",
            "playback_control",
            "set_repeat",
            "off" if "uit" in normalized else "context",
        )
    if "welke speakers" in normalized or "welke apparaten" in normalized:
        return AskDjIntent("informational", "list_outputs", "devices")
    if "waarop" in normalized and "muziek" in normalized:
        return AskDjIntent("informational", "current_output", "status")
    if any(word in normalized for word in ("speel", "draai", "zet")):
        return AskDjIntent("hybrid", "play_music", "play_music", play=True)
    return AskDjIntent("informational", "ask_music_info")


async def _handle_action(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    classification: AskDjIntent,
) -> dict[str, Any]:
    action = classification.action or ""
    if action == "volume_delta":
        status = await handle_spotify_command(hass, runtime, "status")
        playback = status.get("playback") if isinstance(status, dict) else {}
        current = _playback_volume(playback, runtime)
        if current is None:
            return {
                "success": False,
                "text": "Ik kan het huidige volume nu niet bepalen.",
                "error": "playback_unavailable",
            }
        target = max(0, min(60, current + int(classification.value or 0)))
        result = await handle_spotify_command(hass, runtime, "set_volume", target)
        return {
            "success": True,
            "text": "Ik heb het volume aangepast.",
            "dj_text": "Ik heb het volume aangepast.",
            "playback": result.get("playback") if isinstance(result, dict) else {},
        }
    if action in {"pause", "play", "next", "previous"}:
        result = await handle_spotify_command(hass, runtime, action)
        text_response = _action_text(action)
        return {
            "success": True,
            "text": text_response,
            "dj_text": text_response,
            "playback": result.get("playback") if isinstance(result, dict) else {},
        }
    if action == "set_shuffle":
        await handle_spotify_command(hass, runtime, "set_shuffle", classification.value)
        text_response = "Shuffle staat aan." if classification.value else "Shuffle staat uit."
        return {"success": True, "text": text_response, "dj_text": text_response}
    if action == "set_repeat":
        await handle_spotify_command(hass, runtime, "set_repeat", classification.value)
        return {"success": True, "text": "Repeat is aangepast.", "dj_text": "Repeat is aangepast."}
    raise ValueError(f"Unsupported Ask DJ action: {action}")


async def _handle_hybrid(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    classification: AskDjIntent,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        result = await process_text_command(
            hass,
            runtime,
            text,
            play=classification.play,
            correct_stt=_is_voice_input(payload or {}),
        )
        return {"success": True, **result}
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("DJConnect Ask DJ playback request failed: %s", exc)
        dj_text = _playback_failed_text(runtime)
        updater = getattr(runtime, "update", None)
        if callable(updater):
            updater(last_error=str(exc), last_dj_text=dj_text)
        return {
            "success": True,
            "error": "playback_failed",
            "message": str(exc),
            "text": dj_text,
            "dj_text": dj_text,
            "intent": {
                "category": classification.category,
                "intent": classification.intent,
                "action": classification.action,
            },
            "action": classification.action,
        }


async def _handle_informational(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    output_devices: list[dict[str, Any]],
) -> dict[str, Any]:
    if classify_ask_dj(text).action == "devices":
        message = _devices_text(output_devices)
        return {"success": True, "text": message, "dj_text": message}
    if classify_ask_dj(text).action == "status":
        message = _current_output_text(playback_context)
        return {"success": True, "text": message, "dj_text": message}
    if classify_ask_dj(text).intent == "personal_music_profile_analysis":
        spotify_profile = await _listening_profile_context(
            hass,
            runtime,
            payload,
            memory_context,
        )
        message = _personal_music_profile_text(
            text,
            memory_context,
            playback_context,
            spotify_profile,
        )
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "profile_analysis",
            "sources": _profile_sources(memory_context, spotify_profile),
        }
    if classify_ask_dj(text).intent == "personal_music_recommendations":
        spotify_profile = await _listening_profile_context(
            hass,
            runtime,
            payload,
            memory_context,
        )
        actions = _recommendation_playback_actions(
            hass,
            memory_context,
            playback_context,
            spotify_profile,
        )
        if actions:
            message = (
                "Ik denk dat deze goed passen bij je recente luisterprofiel. "
                "Ik start nog niets; tik op Play Now als je er eentje wilt horen."
            )
        else:
            message = (
                "Ik heb nog te weinig concrete speelbare Spotify-aanbevelingen om "
                "een Play Now lijst te maken."
            )
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "playback_actions": actions,
            "sources": _profile_sources(memory_context, spotify_profile),
        }

    prompt = _informational_prompt(
        text,
        payload,
        memory_context,
        playback_context,
        output_devices,
    )
    try:
        assist_context = _assist_context(hass, getattr(runtime, "config", {}) or {})
        language = assist_context.get("language") or payload.get("language") or DEFAULT_TTS_LANGUAGE
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
        message = _speech_from_response((result or {}).get("response") or {})
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Ask DJ informational Assist answer failed: %s", exc)
        message = ""
    if not message:
        message = _fallback_info_text(text, memory_context, playback_context)
    return {"success": True, "text": message, "dj_text": message}


def _normalize_ask_dj_response(
    hass: HomeAssistant,
    runtime: Any,
    result: dict[str, Any],
    classification: AskDjIntent,
    *,
    memory_key: str | None,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    text = str(result.get("dj_text") or result.get("text") or result.get("message") or "").strip()
    if not text:
        text = "Home Assistant gaf geen antwoord."
    images = _images_from_context(hass, result, playback_context)
    links = _links_from_context(result, playback_context, classification)
    sources = _sources_from_context(result, links)
    return {
        "success": bool(result.get("success", True)),
        "text": text,
        "dj_text": text,
        "message": text,
        "images": images,
        "links": links,
        "sources": sources,
        "playback_actions": result.get("playback_actions") or [],
        "error": result.get("error"),
        "intent": {
            "category": classification.category,
            "intent": classification.intent,
        },
        "action": result.get("action") or classification.action,
        "memory_key": memory_key,
        "playback": result.get("playback") or playback_context,
    }


def _is_personal_music_profile_request(normalized: str) -> bool:
    """Return true for personal listening-profile analysis requests."""
    profile_terms = (
        "luisterde",
        "luister ik",
        "geluisterd",
        "luistergedrag",
        "muzieksmaak",
        "muziek smaak",
        "music taste",
        "listening to",
        "been listening",
        "listening habits",
        "music profile",
        "genres",
        "stemming",
        "mood",
    )
    analysis_terms = (
        "omschrijf",
        "beschrijf",
        "profiel",
        "analyse",
        "analyseer",
        "wat zegt",
        "welke genres",
        "describe",
        "profile",
        "make a profile",
        "what does",
        "which genres",
    )
    period_terms = (
        "vandaag",
        "deze week",
        "afgelopen week",
        "afgelopen twee weken",
        "afgelopen maand",
        "laatste 30 dagen",
        "laatste 90 dagen",
        "dit jaar",
        "today",
        "this week",
        "last week",
        "last two weeks",
        "last month",
        "last 30 days",
        "last 90 days",
        "this year",
        "lately",
        "recent",
    )
    return (
        any(term in normalized for term in profile_terms)
        and (
            any(term in normalized for term in analysis_terms)
            or any(term in normalized for term in period_terms)
        )
    )


def _is_personal_recommendation_request(normalized: str) -> bool:
    recommendation_terms = (
        "raad aan",
        "raad je",
        "aanbevel",
        "aanrader",
        "recommend",
        "recommendation",
        "suggest",
        "suggestion",
        "wat past bij mij",
        "iets dat bij mij past",
        "muziekadvies",
    )
    music_terms = (
        "muziek",
        "nummer",
        "track",
        "album",
        "playlist",
        "artist",
        "artiest",
        "song",
    )
    return any(term in normalized for term in recommendation_terms) and any(
        term in normalized for term in music_terms
    )


def _personal_music_profile_text(
    text: str,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    spotify_profile: dict[str, Any] | None = None,
) -> str:
    period = _profile_period_label(text)
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    session = memory_context.get("session") if isinstance(memory_context, dict) else []
    spotify_profile = spotify_profile if isinstance(spotify_profile, dict) else {}
    tracks = _profile_tracks(memory, playback_context, spotify_profile)
    artists = _profile_artists(memory, tracks, spotify_profile)
    albums = _top_values(tracks, ("album", "album_name"))
    genres = _profile_genres(memory, spotify_profile)
    mood = _profile_mood(memory)
    energy = _profile_energy(tracks, memory)
    examples = _profile_examples(tracks)
    last_ask = memory.get("last_ask_dj") if isinstance(memory, dict) else {}

    if not tracks and not genres and not artists:
        known = []
        if isinstance(last_ask, dict) and last_ask.get("input"):
            known.append(f"je laatste Ask DJ vraag was: {last_ask['input']}")
        if session:
            known.append("er is wel recente Ask DJ chatcontext")
        detail = " Ik zie " + " en ".join(known) + "." if known else ""
        spotify_hint = " Spotify gaf ook nog geen bruikbare recently-played of top-items terug." if spotify_profile else ""
        return (
            f"Ik heb nog te weinig luistergeschiedenis om je muzieksmaak over {period} eerlijk te analyseren."
            f"{detail}{spotify_hint} Zodra er meer recente Spotify snapshots of DJ Memory data staat, kan ik daar een veel scherper profiel van maken."
        )

    lines = [f"Voor {period} zie ik dit profiel op basis van de DJConnect context die ik nu heb."]
    if spotify_profile:
        lines.append("Ik combineer hierbij Spotify recent/top-data met DJConnect Memory.")
    if genres:
        lines.append("Harde observatie: je genres neigen naar " + _join_examples(genres, limit=4) + ".")
    elif artists:
        lines.append("Harde observatie: ik zie vooral terugkerende artiesten zoals " + _join_examples(artists, limit=4) + ".")
    if albums:
        lines.append("Albums/contexts die eruit springen: " + _join_examples(albums, limit=3) + ".")
    vibe = _profile_vibe(genres, energy, mood)
    lines.append(
        "Interpretatie: je profiel lijkt "
        + vibe
        + "; dat is een voorzichtige duiding, geen harde diagnose."
    )
    if mood is not None:
        lines.append(f"Je laatste mood/energy waarde in DJ Memory is {mood}/100.")
    if examples:
        lines.append("Concrete voorbeelden: " + _join_examples(examples, limit=6) + ".")
    if spotify_profile and _profile_limited(spotify_profile):
        lines.append("Let op: Spotify geeft geen onbeperkte ruwe luistergeschiedenis, dus dit blijft een profielschets op basis van recente en top-item snapshots.")
    if isinstance(last_ask, dict) and last_ask.get("input"):
        lines.append(f"Recente Ask DJ context: je vroeg eerder '{last_ask['input']}'.")
    return " ".join(lines)


def _profile_period_label(text: str) -> str:
    normalized = _normalize(text)
    checks = (
        (("vandaag", "today"), "vandaag"),
        (("deze week", "this week"), "deze week"),
        (("afgelopen week", "last week"), "afgelopen week"),
        (("afgelopen twee weken", "laatste twee weken", "last two weeks"), "de afgelopen twee weken"),
        (("afgelopen maand", "last month"), "de afgelopen maand"),
        (("laatste 90 dagen", "last 90 days"), "de laatste 90 dagen"),
        (("laatste 30 dagen", "last 30 days"), "de laatste 30 dagen"),
        (("dit jaar", "this year"), "dit jaar"),
    )
    for needles, label in checks:
        if any(needle in normalized for needle in needles):
            return label
    return "de laatste 30 dagen"


async def _listening_profile_context(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
) -> dict[str, Any]:
    memory = getattr(runtime, "memory", None)
    stored = {}
    if isinstance(memory_context, dict):
        memory_data = memory_context.get("memory")
        if isinstance(memory_data, dict):
            stored = memory_data.get("listening_profile") if isinstance(memory_data.get("listening_profile"), dict) else {}
    fresh = False
    if memory is not None:
        try:
            fresh = await memory.async_listening_profile_is_fresh(runtime, payload)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect listening profile freshness check failed: %s", exc)
    if fresh and stored:
        return stored
    try:
        result = await handle_spotify_command(hass, runtime, "listening_profile")
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify listening profile unavailable: %s", exc)
        return stored if isinstance(stored, dict) else {}
    profile = result.get("profile") if isinstance(result, dict) else {}
    if isinstance(profile, dict) and profile:
        profile["last_profile_refresh"] = profile.get("last_profile_refresh") or _now_iso()
        if memory is not None:
            try:
                await memory.async_update_listening_profile(runtime, profile, payload)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("DJConnect listening profile memory update failed: %s", exc)
        return profile
    return stored if isinstance(stored, dict) else {}


def _profile_tracks(
    memory: Any,
    playback_context: dict[str, Any],
    spotify_profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    if isinstance(memory, dict):
        recent = memory.get("recent_tracks")
        if isinstance(recent, list):
            tracks.extend(item for item in recent if isinstance(item, dict))
        last = memory.get("last_ask_dj")
        if isinstance(last, dict) and isinstance(last.get("track"), dict):
            tracks.append(last["track"])
        profile = memory.get("listening_profile")
        if isinstance(profile, dict) and isinstance(profile.get("recent_tracks"), list):
            tracks.extend(item for item in profile["recent_tracks"] if isinstance(item, dict))
    if isinstance(spotify_profile, dict):
        recent = spotify_profile.get("recent_tracks")
        if isinstance(recent, list):
            tracks.extend(item for item in recent if isinstance(item, dict))
        top_tracks = spotify_profile.get("top_tracks_by_range")
        if isinstance(top_tracks, dict):
            for range_name in ("short_term", "medium_term", "long_term"):
                items = top_tracks.get(range_name)
                if isinstance(items, list):
                    tracks.extend(item for item in items[:10] if isinstance(item, dict))
    if playback_context:
        tracks.append(playback_context)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for track in tracks:
        key = _track_label(track) or str(track.get("uri") or track.get("id") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(track)
    return deduped


def _top_values(tracks: list[dict[str, Any]], keys: tuple[str, ...]) -> list[str]:
    counts: dict[str, int] = {}
    for track in tracks:
        for key in keys:
            value = track.get(key)
            if value:
                counts[str(value)] = counts.get(str(value), 0) + 1
                break
    return [
        value
        for value, _count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )
    ]


def _profile_artists(
    memory: Any,
    tracks: list[dict[str, Any]],
    spotify_profile: dict[str, Any],
) -> list[str]:
    artists = _top_values(tracks, ("artist", "artist_name"))
    for source in (spotify_profile, memory.get("listening_profile") if isinstance(memory, dict) else {}):
        if not isinstance(source, dict):
            continue
        recent = source.get("recent_artists")
        if isinstance(recent, list):
            artists.extend(str(item) for item in recent if item)
        top = source.get("top_artists_by_range")
        if isinstance(top, dict):
            for range_name in ("short_term", "medium_term", "long_term"):
                items = top.get(range_name)
                if isinstance(items, list):
                    artists.extend(
                        str(item.get("name") or item.get("artist") or item.get("artist_name"))
                        for item in items[:10]
                        if isinstance(item, dict) and (item.get("name") or item.get("artist") or item.get("artist_name"))
                    )
    return _unique_ordered(artists)


def _profile_genres(memory: Any, spotify_profile: dict[str, Any]) -> list[str]:
    if not isinstance(memory, dict):
        memory = {}
    genres = memory.get("favorite_genres") or memory.get("genres")
    result = [str(item) for item in genres if item] if isinstance(genres, list) else []
    for source in (spotify_profile, memory.get("listening_profile")):
        if isinstance(source, dict) and isinstance(source.get("inferred_genres"), list):
            result.extend(str(item) for item in source["inferred_genres"] if item)
    return _unique_ordered(result)[:12]


def _profile_mood(memory: Any) -> int | None:
    if not isinstance(memory, dict):
        return None
    try:
        value = memory.get("mood")
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _profile_energy(tracks: list[dict[str, Any]], memory: Any) -> str:
    mood = _profile_mood(memory)
    if mood is not None:
        if mood < 35:
            return "chill"
        if mood > 70:
            return "energiek"
    text = " ".join(str(track).lower() for track in tracks)
    if any(word in text for word in ("ambient", "acoustic", "chill", "sleep", "rustig")):
        return "chill"
    if any(word in text for word in ("dance", "party", "workout", "hard", "rock")):
        return "intens"
    return "mellow"


def _profile_vibe(genres: list[str], energy: str, mood: int | None) -> str:
    genre_text = " ".join(genres).lower()
    if mood is not None and mood < 35:
        return "rustig, gevoelig en wat naar ontspanning gericht"
    if mood is not None and mood > 70:
        return "energiek en naar beweging of momentum gericht"
    if any(word in genre_text for word in ("jazz", "ambient", "classical", "acoustic")):
        return "ontspannen en geconcentreerd"
    if any(word in genre_text for word in ("rock", "metal", "punk")):
        return "intens en expressief"
    if any(word in genre_text for word in ("dance", "house", "techno", "pop")):
        return "ritmisch en opgewekt"
    return f"{energy} en licht eclectisch"


def _profile_examples(tracks: list[dict[str, Any]]) -> list[str]:
    examples = []
    for track in tracks:
        label = _track_label(track)
        if label:
            examples.append(label)
        elif track.get("artist") or track.get("artist_name"):
            examples.append(str(track.get("artist") or track.get("artist_name")))
    return examples


def _join_examples(values: list[str], *, limit: int) -> str:
    selected = [str(value) for value in values if value][:limit]
    if len(selected) <= 1:
        return selected[0] if selected else ""
    return ", ".join(selected[:-1]) + " en " + selected[-1]


def _profile_sources(
    memory_context: dict[str, Any],
    spotify_profile: dict[str, Any],
) -> list[dict[str, str]]:
    sources = [{"source": "djconnect_memory", "kind": "source", "title": "DJConnect Memory"}]
    spotify_sources = spotify_profile.get("sources") if isinstance(spotify_profile, dict) else []
    for source in spotify_sources or []:
        text = str(source or "").strip()
        if text:
            sources.append({"source": text, "kind": "source", "title": text.replace("_", " ")})
    if isinstance(memory_context, dict) and memory_context.get("session"):
        sources.append({"source": "ask_dj_session", "kind": "source", "title": "Ask DJ session"})
    return sources


def _recommendation_playback_actions(
    hass: HomeAssistant,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    spotify_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    top_tracks = spotify_profile.get("top_tracks_by_range") if isinstance(spotify_profile, dict) else {}
    if isinstance(top_tracks, dict):
        for range_name in ("short_term", "medium_term", "long_term"):
            items = top_tracks.get(range_name)
            if isinstance(items, list):
                candidates.extend(item for item in items if isinstance(item, dict))
    recent = spotify_profile.get("recent_tracks") if isinstance(spotify_profile, dict) else []
    if isinstance(recent, list):
        candidates.extend(item for item in recent if isinstance(item, dict))
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    if isinstance(memory, dict):
        recent_memory = memory.get("recent_tracks")
        if isinstance(recent_memory, list):
            candidates.extend(item for item in recent_memory if isinstance(item, dict))
    if playback_context:
        candidates.append(playback_context)

    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        uri = str(item.get("uri") or item.get("current_uri") or "").strip()
        kind = _spotify_uri_kind(uri)
        if kind not in {"track", "album", "artist", "playlist"} or uri in seen:
            continue
        seen.add(uri)
        image_url = str(
            item.get("album_image_url")
            or item.get("image_url")
            or item.get("thumbnail_url")
            or ""
        ).strip()
        proxy_image = register_image_proxy_url(hass, image_url) if image_url.startswith(("http://", "https://")) else image_url
        title = str(item.get("track_name") or item.get("title") or item.get("name") or uri).strip()
        subtitle = str(item.get("artist") or item.get("artist_name") or item.get("album_name") or "").strip()
        action = {
            "id": uri,
            "title": title,
            "subtitle": subtitle,
            "uri": uri,
            "kind": kind,
            "image_url": proxy_image,
            "reason": "Past bij je recente luisterprofiel.",
        }
        if kind == "track":
            context_uri = str(item.get("context_uri") or "").strip()
            if context_uri:
                action["context_uri"] = context_uri
                action["offset_uri"] = uri
        actions.append({key: value for key, value in action.items() if value not in ("", None)})
        if len(actions) >= 6:
            break
    return actions


def _spotify_uri_kind(uri: str) -> str:
    if uri.startswith("spotify:track:"):
        return "track"
    if uri.startswith("spotify:album:"):
        return "album"
    if uri.startswith("spotify:artist:"):
        return "artist"
    if uri.startswith("spotify:playlist:"):
        return "playlist"
    return ""


def _sources_from_context(result: dict[str, Any], links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    provided = result.get("sources")
    sources: list[dict[str, Any]] = []
    if isinstance(provided, list):
        for item in provided:
            if isinstance(item, dict):
                sources.append(
                    {
                        "source": str(item.get("source") or item.get("title") or "source"),
                        "title": str(item.get("title") or item.get("source") or "Source"),
                        "kind": str(item.get("kind") or "source"),
                    }
                )
            elif item:
                sources.append({"source": str(item), "title": str(item), "kind": "source"})
    for link in links:
        if isinstance(link, dict) and (link.get("kind") == "source" or link.get("source") == "source"):
            sources.append(
                {
                    "source": str(link.get("source") or link.get("title") or "source"),
                    "title": str(link.get("title") or link.get("source") or "Source"),
                    "kind": "source",
                }
            )
    return sources


def _profile_limited(spotify_profile: dict[str, Any]) -> bool:
    recent = spotify_profile.get("recent_tracks")
    top_tracks = spotify_profile.get("top_tracks_by_range")
    top_artists = spotify_profile.get("top_artists_by_range")
    count = len(recent) if isinstance(recent, list) else 0
    for group in (top_tracks, top_artists):
        if isinstance(group, dict):
            count += sum(len(items) for items in group.values() if isinstance(items, list))
    return count < 10


def _unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        normalized = text.lower()
        if text and normalized not in seen:
            seen.add(normalized)
            result.append(text)
    return result


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _identity_payload(runtime: Any, payload: dict[str, Any]) -> dict[str, Any]:
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    status = getattr(runtime, "device_status", {}) or {}
    return {
        CONF_DEVICE_ID: payload.get(CONF_DEVICE_ID) or identity.get(CONF_DEVICE_ID) or status.get(CONF_DEVICE_ID),
        CONF_CLIENT_TYPE: payload.get(CONF_CLIENT_TYPE) or identity.get(CONF_CLIENT_TYPE) or status.get(CONF_CLIENT_TYPE),
        CONF_DEVICE_NAME: payload.get(CONF_DEVICE_NAME) or identity.get(CONF_DEVICE_NAME) or status.get(CONF_DEVICE_NAME),
        "memory_key": payload.get("memory_key") or identity.get("memory_key"),
        "mood": payload.get("mood") if payload.get("mood") is not None else payload.get("energy"),
        "dj_style": payload.get("dj_style"),
        "preferred_device_id": payload.get("preferred_device_id"),
    }


async def _playback_context(hass: HomeAssistant, runtime: Any) -> dict[str, Any]:
    try:
        result = await handle_spotify_command(hass, runtime, "status")
        playback = result.get("playback") if isinstance(result, dict) else {}
        return playback if isinstance(playback, dict) else {}
    except Exception:  # noqa: BLE001
        return getattr(runtime, "last_playback", None) or {}


async def _output_devices(
    hass: HomeAssistant,
    runtime: Any,
    classification: AskDjIntent,
) -> list[dict[str, Any]]:
    if classification.action != "devices":
        status = getattr(runtime, "device_status", {}) or {}
        devices = status.get("available_outputs")
        return devices if isinstance(devices, list) else []
    try:
        result = await handle_spotify_command(hass, runtime, "devices")
        devices = result.get("devices") if isinstance(result, dict) else []
        return devices if isinstance(devices, list) else []
    except Exception:  # noqa: BLE001
        return []


def _informational_prompt(
    text: str,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    output_devices: list[dict[str, Any]],
) -> str:
    memory_text = prompt_context_text(memory_context)
    return (
        "Je bent DJConnect Ask DJ. Beantwoord informatieve muziekvragen zonder "
        "playback te wijzigen. Gebruik alleen meegegeven context en betrouwbare "
        "kennis die je al hebt; verzin geen trivia. Als bronnen beschikbaar zijn, "
        "houd rekening met Spotify metadata, DJ Memory, MusicBrainz, Wikidata, "
        "korte Wikipedia-samenvattingen, Last.fm, Discogs en TheAudioDB. "
        "Geef een kort natuurlijk antwoord voor een chat UI.\n\n"
        f"Vraag: {text}\n"
        f"Mood/energy: {payload.get('mood') or payload.get('energy') or 'onbekend'}\n"
        f"DJ stijl: {payload.get('dj_style') or 'standaard'}\n"
        f"Playback context: {_safe_inline_context(playback_context)}\n"
        f"Output devices: {_safe_inline_context(output_devices)}\n"
        f"DJ Memory: {memory_text or 'geen eerdere context'}"
    )


def _fallback_info_text(
    text: str,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
) -> str:
    normalized = _normalize(text)
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    last = memory.get("last_ask_dj") if isinstance(memory, dict) else {}
    if "waarom" in normalized and isinstance(last, dict) and last.get("response_text"):
        return str(last.get("response_text"))
    track = _track_label(playback_context)
    if "artiest" in normalized and track:
        return f"Ik kijk naar de huidige context rond {track}. Meer brondata is nog niet beschikbaar."
    return "Ik heb nu niet genoeg betrouwbare broninformatie om daar zeker antwoord op te geven."


def _images_from_context(
    hass: HomeAssistant,
    result: dict[str, Any],
    playback_context: dict[str, Any],
) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    provided = result.get("images")
    if isinstance(provided, list):
        for item in provided:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("thumbnail_url")
            if not url:
                continue
            proxy = register_image_proxy_url(hass, str(url))
            images.append(
                {
                    "url": proxy,
                    "thumbnail_url": proxy,
                    "title": str(item.get("title") or "Image"),
                    "subtitle": str(item.get("subtitle") or ""),
                    "kind": str(item.get("kind") or "image"),
                    "source": str(item.get("source") or "source"),
                }
            )
    for source in (result, playback_context):
        if not isinstance(source, dict):
            continue
        url = source.get("album_image_url") or source.get("media_image_url") or source.get("image_url") or source.get("thumbnail_url")
        if not url:
            track = source.get("track") if isinstance(source.get("track"), dict) else {}
            url = track.get("album_image_url") or track.get("image_url") or track.get("thumbnail_url")
        if url:
            proxy = register_image_proxy_url(hass, str(url))
            images.append(
                {
                    "url": proxy,
                    "thumbnail_url": proxy,
                    "title": source.get("track_name") or source.get("title") or source.get("name") or "Album art",
                    "subtitle": source.get("artist") or source.get("artist_name") or source.get("album_name") or "",
                    "kind": "album_art",
                    "source": "spotify",
                }
            )
            break
    return images


def _links_from_context(
    result: dict[str, Any],
    playback_context: dict[str, Any],
    classification: AskDjIntent,
) -> list[dict[str, Any]]:
    links = []
    uri = result.get("uri") or playback_context.get("uri") or playback_context.get("track_uri")
    if uri:
        links.append(
            {
                "url": str(uri),
                "title": "Spotify context",
                "subtitle": classification.intent,
                "kind": "source",
                "source": "source",
            }
        )
    return links


def register_image_proxy_url(hass: HomeAssistant, external_url: str) -> str:
    """Register an external image URL and return a Home Assistant proxy URL."""
    token = secrets.token_urlsafe(18)
    hass.data.setdefault(DOMAIN, {}).setdefault(IMAGE_PROXY_KEY, {})[token] = external_url
    return f"{API_IMAGE_PROXY_BASE}/{token}"


def image_proxy_target(hass: HomeAssistant, token: str) -> str | None:
    """Return registered image proxy target URL."""
    return (
        hass.data.get(DOMAIN, {})
        .get(IMAGE_PROXY_KEY, {})
        .get(str(token or "").strip())
    )


def _playback_volume(playback: Any, runtime: Any) -> int | None:
    if isinstance(playback, dict):
        for key in ("volume_percent", "volume", "device_volume"):
            if playback.get(key) is not None:
                try:
                    return int(playback[key])
                except (TypeError, ValueError):
                    pass
    status = getattr(runtime, "device_status", {}) or {}
    try:
        return int(status["volume"]) if status.get("volume") is not None else None
    except (TypeError, ValueError):
        return None


def _action_text(action: str) -> str:
    return {
        "pause": "Ik heb de muziek gepauzeerd.",
        "play": "Ik heb de muziek gestart.",
        "next": "Ik ga naar het volgende nummer.",
        "previous": "Ik ga naar het vorige nummer.",
    }.get(action, "Ik heb het aangepast.")


def _playback_failed_text(runtime: Any) -> str:
    language_getter = getattr(runtime, "device_language", None)
    language = str(language_getter() or "").lower() if callable(language_getter) else ""
    if language.startswith("en"):
        return "I understood your music request, but Spotify could not start it right now."
    return "Ik heb je muziekverzoek begrepen, maar Spotify kon het nu niet starten."


def _devices_text(devices: list[dict[str, Any]]) -> str:
    names = [str(device.get("name")) for device in devices if isinstance(device, dict) and device.get("name")]
    return "Beschikbare speakers: " + ", ".join(names) if names else "Ik zie nu geen Spotify speakers."


def _current_output_text(playback: dict[str, Any]) -> str:
    device = playback.get("device") if isinstance(playback.get("device"), dict) else {}
    name = device.get("name") or playback.get("device_name") or playback.get("output")
    return f"Muziek speelt nu op {name}." if name else "Ik kan nu niet zien waarop muziek speelt."


def _track_label(playback: dict[str, Any]) -> str:
    artist = playback.get("artist") or playback.get("artist_name")
    title = playback.get("track_name") or playback.get("title") or playback.get("name")
    return " - ".join(str(value) for value in (artist, title) if value)


def _safe_inline_context(value: Any) -> str:
    text = str(value)
    return text[:1200]


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _error_response(error: str, message: str, *, memory_key: str | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": error,
        "message": message,
        "text": message,
        "dj_text": message,
        "images": [],
        "links": [],
        "memory_key": memory_key,
    }
