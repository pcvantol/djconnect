"""Ask DJ backend support."""
from __future__ import annotations

from dataclasses import dataclass
import logging
import random
import re
import secrets
from typing import Any
from urllib.parse import quote, urlsplit

from aiohttp import ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
from .mood import (
    enrich_payload_with_mood_zone,
    mood_context_text,
    mood_zone_for_value,
)
from .music_intent import parse_spoken_music_request
from .pipeline import _assist_context, _speech_from_response
from .processor import process_text_command
from .smart_home_context import smart_home_context, smart_home_context_text
from .spotify_backend import handle_spotify_command

_LOGGER = logging.getLogger(__name__)

IMAGE_PROXY_KEY = "image_proxy"
BANDSINTOWN_EVENTS_URL = "https://rest.bandsintown.com/artists/{artist}/events"
BANDSINTOWN_APP_ID = "djconnect"
TRACK_REFERENCE_WORDS = (
    "kraker",
    "monsterhit",
    "vette track",
    "dikke knaller",
    "knaller",
    "beuker",
)


@dataclass(frozen=True)
class AskDjIntent:
    """Classified Ask DJ intent."""

    category: str
    intent: str
    action: str | None = None
    value: Any | None = None
    play: bool = False


@dataclass(frozen=True)
class AskDjConversationTurn:
    """Conversation-aware classification for the latest Ask DJ message."""

    kind: str
    text: str
    response_text: str | None = None


async def async_handle_ask_dj(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Handle a text Ask DJ request and return the client response shape."""
    payload = enrich_payload_with_mood_zone(payload)
    text = str(payload.get("text") or payload.get("message") or "").strip()
    if not text:
        return _error_response("missing_text", "Ask DJ needs text to answer.")
    if payload.get("mood_zone"):
        _LOGGER.debug(
            "DJConnect Ask DJ mood context: mood=%s zone=%s",
            payload.get("mood"),
            payload.get("mood_zone"),
        )

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

    conversation_turn = classify_conversation_turn(text, memory_context)
    if conversation_turn.kind in {"conversational_followup", "clarification_needed"}:
        classification = AskDjIntent(
            "informational",
            conversation_turn.kind,
            "none",
        )
        result = _handle_conversational_followup(conversation_turn)
        response = _normalize_ask_dj_response(
            hass,
            runtime,
            result,
            classification,
            memory_key=memory_key,
            playback_context={},
        )
        if memory is not None:
            await memory.async_update_last_ask_dj(
                runtime,
                input_text=text,
                result={
                    "intent": response.get("intent") or {},
                    "dj_text": response.get("dj_text") or response.get("text"),
                    "playback": {},
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

    effective_text = conversation_turn.text
    classification = classify_ask_dj(effective_text)
    if (
        _is_voice_input(payload)
        and classification.category == "informational"
        and classification.intent == "ask_music_info"
        and _looks_like_bare_voice_music_request(effective_text)
    ):
        classification = AskDjIntent("hybrid", "play_music", "play_music", play=True)
    if classification.intent == "help":
        result = _help_response()
        response = _normalize_ask_dj_response(
            hass,
            runtime,
            result,
            classification,
            memory_key=memory_key,
            playback_context={},
        )
        response.pop("playback", None)
        return response
    playback_context = await _playback_context(hass, runtime)
    home_context = smart_home_context(hass, runtime)
    if home_context:
        memory_context["smart_home"] = home_context
    output_devices = await _output_devices(hass, runtime, classification)
    if classification.category == "hybrid" and _is_slang_track_reference(effective_text):
        track_label = _track_label(playback_context)
        if track_label:
            effective_text = f"speel {track_label}"
        else:
            classification = AskDjIntent("informational", "clarification_needed", "none")
            result = {
                "success": True,
                "text": "Welke track bedoel je?",
                "dj_text": "Welke track bedoel je?",
                "action": "none",
            }
            response = _normalize_ask_dj_response(
                hass,
                runtime,
                result,
                classification,
                memory_key=memory_key,
                playback_context=playback_context,
            )
            response.pop("playback", None)
            return response
    if (
        classification.category == "hybrid"
        and _is_deferred_playback_request(effective_text)
        and _playback_is_active(playback_context)
    ):
        result = await _deferred_playback_request_response(hass, runtime, effective_text)
        response = _normalize_ask_dj_response(
            hass,
            runtime,
            result,
            classification,
            memory_key=memory_key,
            playback_context=playback_context,
        )
        response.pop("playback", None)
        return response

    try:
        if classification.category == "action":
            result = await _handle_action(hass, runtime, effective_text, classification)
        elif classification.category == "hybrid":
            result = await _handle_hybrid(hass, runtime, effective_text, classification, payload)
        else:
            result = await _handle_informational(
                hass,
                runtime,
                effective_text,
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
            input_text=effective_text,
            result={
                "intent": response.get("intent") or {},
                "dj_text": response.get("dj_text") or response.get("text"),
                "playback": response.get("playback") or playback_context,
                "playback_actions": response.get("playback_actions") or [],
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


async def async_idle_suggestion(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Return one personalized Ask DJ system suggestion when playback is idle."""
    payload = enrich_payload_with_mood_zone(payload)
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
    if payload.get("mood_zone") is None:
        last_mood = _profile_mood(memory_context.get("memory") if isinstance(memory_context, dict) else {})
        if last_mood is not None:
            payload = enrich_payload_with_mood_zone({**payload, "mood": last_mood})
    playback_context = await _playback_context(hass, runtime)
    if _playback_is_active(playback_context):
        text = "Er speelt al muziek. Ik laat de suggestie even achterwege."
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "message": text,
            "message_kind": "system",
            "origin": "idle_suggestion",
            "intent": {"category": "informational", "intent": "idle_suggestion"},
            "action": "none",
            "memory_key": memory_key,
            "playback_actions": [],
        }
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
    selected_actions = actions[:1]
    if selected_actions:
        action = selected_actions[0]
        title = str(action.get("title") or "deze track").strip()
        subtitle = str(action.get("subtitle") or "").strip()
        item = f"{title} van {subtitle}" if subtitle else title
        text = (
            "Er speelt nu niets. Zin in iets nieuws? "
            f"Ik denk dat {item} goed past bij je recente luisterprofiel"
            f"{_mood_sentence_suffix(payload)}."
        )
    else:
        text = (
            "Er speelt nu niets. Ik heb nog te weinig luisterprofiel om direct "
            f"een goede Play Now suggestie te doen{_mood_sentence_suffix(payload)}."
        )
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "message": text,
        "message_kind": "system",
        "origin": "idle_suggestion",
        "intent": {"category": "informational", "intent": "idle_suggestion"},
        "action": "none",
        "memory_key": memory_key,
        "playback_actions": selected_actions,
        "sources": _profile_sources(memory_context, spotify_profile),
    }


def _playback_is_active(playback_context: dict[str, Any]) -> bool:
    if not isinstance(playback_context, dict):
        return False
    if playback_context.get("is_playing"):
        return True
    return bool(playback_context.get("has_playback") and playback_context.get("track_name"))


def _mood_sentence_suffix(payload: dict[str, Any]) -> str:
    zone = mood_zone_for_value(
        payload.get("mood") if payload.get("mood") is not None else payload.get("energy")
    )
    if zone is None:
        return ""
    return f" en je {zone.name}-vibe"


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


def classify_conversation_turn(
    text: str,
    memory_context: dict[str, Any],
) -> AskDjConversationTurn:
    """Classify short contextual chat turns before normal Ask DJ routing."""
    normalized = _normalize(text)
    if not normalized:
        return AskDjConversationTurn("informational_intent", text)
    if _is_retry_request(normalized):
        return _retry_previous_request_turn(memory_context)
    if _is_contextual_play_request(normalized):
        return _contextual_play_turn(memory_context)
    direct_track = _direct_track_answer_turn(text, memory_context)
    if direct_track is not None:
        return direct_track
    if _is_personal_recommendation_request(normalized):
        return AskDjConversationTurn("informational_intent", text)
    if _has_clear_playback_action(normalized):
        return AskDjConversationTurn(_conversation_kind_for_intent(text), text)
    if _is_conversational_acknowledgement(normalized):
        return AskDjConversationTurn(
            "conversational_followup",
            text,
            _conversational_response_text(normalized),
        )
    if _is_clarification_or_correction(normalized):
        merged = _merge_with_previous_user_request(text, memory_context)
        return AskDjConversationTurn("clarification_or_correction", merged)
    return AskDjConversationTurn(_conversation_kind_for_intent(text), text)


def _conversation_kind_for_intent(text: str) -> str:
    intent = classify_ask_dj(text)
    if intent.category == "hybrid":
        return "hybrid_intent"
    if intent.category == "action":
        return "playback_intent"
    return "informational_intent"


def _has_clear_playback_action(normalized: str) -> bool:
    return bool(
        re.search(
            r"\b(speel|draai|zet|pauzeer|volgende|vorige|next|skip|previous|harder|zachter|shuffle|repeat|herhaal)\b",
            normalized,
        )
        or "start muziek" in normalized
        or "speel verder" in normalized
    )


def _is_contextual_play_request(normalized: str) -> bool:
    return normalized in {
        "speel af",
        "speel maar",
        "speel maar af",
        "draai maar",
        "draai maar af",
        "zet maar op",
        "play it",
        "play that",
        "play this",
        "play",
    }


def _is_retry_request(normalized: str) -> bool:
    return normalized in {
        "probeer opnieuw",
        "probeer het opnieuw",
        "nog eens",
        "opnieuw",
        "retry",
        "try again",
        "try it again",
        "again",
    }


def _retry_previous_request_turn(memory_context: dict[str, Any]) -> AskDjConversationTurn:
    previous = _previous_retryable_user_request(memory_context)
    if not previous:
        return AskDjConversationTurn(
            "clarification_needed",
            "",
            "Welk verzoek wil je dat ik opnieuw probeer?",
        )
    return AskDjConversationTurn(_conversation_kind_for_intent(previous), previous)


def _previous_retryable_user_request(memory_context: dict[str, Any]) -> str:
    history = memory_context.get("server_history") if isinstance(memory_context, dict) else []
    if isinstance(history, list):
        for item in reversed(history):
            if not isinstance(item, dict) or item.get("role") != "user" or not item.get("text"):
                continue
            text = str(item.get("text") or "").strip()
            normalized = _normalize(text)
            if text and not _is_retry_request(normalized) and _has_clear_playback_action(normalized):
                return text
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    last = memory.get("last_ask_dj") if isinstance(memory, dict) else {}
    text = str(last.get("input") or "").strip() if isinstance(last, dict) else ""
    normalized = _normalize(text)
    if text and not _is_retry_request(normalized) and _has_clear_playback_action(normalized):
        return text
    return ""


def _contextual_play_turn(memory_context: dict[str, Any]) -> AskDjConversationTurn:
    track = _recent_user_track_like_text(memory_context)
    if not track:
        return AskDjConversationTurn(
            "clarification_needed",
            "",
            "Welk nummer wil je dat ik afspeel?",
        )
    artist = _artist_from_recent_assistant_text(memory_context) or _artist_from_server_history_context(memory_context)
    if not artist:
        return AskDjConversationTurn(
            "clarification_needed",
            "",
            "Welke artiest bedoel je?",
        )
    query = f"{track} {artist}".strip()
    return AskDjConversationTurn("hybrid_intent", f"speel {query}")


def _direct_track_answer_turn(
    text: str,
    memory_context: dict[str, Any],
) -> AskDjConversationTurn | None:
    normalized = _normalize(text)
    if not _looks_like_short_track_answer(normalized):
        return None
    if not _recent_assistant_asked_for_specific_music(memory_context):
        return None
    artist = _artist_from_recent_assistant_text(memory_context) or _artist_from_server_history_context(memory_context)
    query = f"{text.strip()} {artist}".strip()
    return AskDjConversationTurn("hybrid_intent", f"speel {query}")


def _looks_like_short_track_answer(normalized: str) -> bool:
    if not normalized or len(normalized.split()) > 8:
        return False
    if _is_conversational_acknowledgement(normalized):
        return False
    if _is_personal_recommendation_request(normalized) or _has_clear_playback_action(normalized):
        return False
    if classify_ask_dj(normalized).category != "informational":
        return False
    return True


def _recent_assistant_asked_for_specific_music(memory_context: dict[str, Any]) -> bool:
    history = memory_context.get("server_history") if isinstance(memory_context, dict) else []
    if not isinstance(history, list):
        return False
    needles = (
        "specifieke nummers",
        "specifiek nummer",
        "specifieke track",
        "specifieke artiest",
        "welke artiest",
        "welk nummer",
        "welke track",
        "track in gedachten",
        "artiest in gedachten",
    )
    for item in reversed(history[-6:]):
        if not isinstance(item, dict) or item.get("role") != "assistant":
            continue
        text = _normalize(str(item.get("text") or ""))
        if any(needle in text for needle in needles):
            return True
    return False


def _recent_user_track_like_text(memory_context: dict[str, Any]) -> str:
    history = memory_context.get("server_history") if isinstance(memory_context, dict) else []
    if isinstance(history, list):
        for item in reversed(history):
            if not isinstance(item, dict) or item.get("role") != "user":
                continue
            text = str(item.get("text") or "").strip()
            normalized = _normalize(text)
            if not text or _is_contextual_play_request(normalized):
                continue
            if classify_ask_dj(text).category == "informational" and len(normalized.split()) <= 8:
                return text
    previous = _previous_user_message(memory_context)
    if previous and not _is_contextual_play_request(_normalize(previous)):
        return previous
    return ""


def _artist_from_recent_assistant_text(memory_context: dict[str, Any]) -> str:
    history = memory_context.get("server_history") if isinstance(memory_context, dict) else []
    if not isinstance(history, list):
        return ""
    patterns = (
        r"\b(?:van|door|by)\s+([A-Z][\w'&.\-]*(?:\s+[A-Z&][\w'&.\-]*){0,5})",
        r"\b(?:in|over|rond)\s+([A-Z][\w'&\-]*(?:\s+[A-Z&][\w'&\-]*){0,5})",
        r"\blied\s+van\s+([^,.!]+)",
        r"\bsong\s+by\s+([^,.!]+)",
    )
    for item in reversed(history):
        if not isinstance(item, dict) or item.get("role") != "assistant":
            continue
        text = str(item.get("text") or "").strip()
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                artist = _clean_artist_name(match.group(1))
                if artist:
                    return artist
    return ""


def _is_conversational_acknowledgement(normalized: str) -> bool:
    if len(normalized.split()) > 5:
        return False
    exact = {
        "geeft niet",
        "dat geeft niet",
        "maakt niet uit",
        "laat maar",
        "ok",
        "okay",
        "oke",
        "dank je",
        "dankjewel",
        "bedankt",
        "thanks",
        "thank you",
        "probeer later nog eens",
        "nee hoeft niet",
        "nee",
        "hoeft niet",
        "prima",
        "top",
        "jammer",
        "helaas",
        "no worries",
        "never mind",
    }
    if normalized in exact:
        return True
    return normalized.startswith(("ok ", "oke ", "thanks ", "dank je "))


def _is_clarification_or_correction(normalized: str) -> bool:
    if _has_clear_playback_action(normalized):
        return False
    if normalized.startswith(("nee ", "niet ", "bedoel ", "ik bedoel ", "toch ")):
        return True
    if normalized.startswith(("alleen ", "van ", "tussen ", "uit ", "over ")):
        return True
    if any(phrase in normalized for phrase in ("ik bedoel", "bedoelde", "correctie")):
        return True
    if any(phrase in normalized for phrase in ("jaren 80", "jaren 90", "1980", "1990", "laatste album")):
        return len(normalized.split()) <= 8
    return False


def _merge_with_previous_user_request(
    text: str,
    memory_context: dict[str, Any],
) -> str:
    previous = _previous_user_message(memory_context)
    if not previous:
        return text
    correction = str(text or "").strip()
    normalized = _normalize(correction)
    if normalized.startswith(("nee ", "ik bedoel ", "bedoel ")):
        return f"{previous} Correctie: {correction}"
    return f"{previous} {correction}".strip()


def _previous_user_message(memory_context: dict[str, Any]) -> str:
    history = memory_context.get("server_history") if isinstance(memory_context, dict) else []
    if isinstance(history, list):
        for item in reversed(history):
            if isinstance(item, dict) and item.get("role") == "user" and item.get("text"):
                return str(item.get("text") or "").strip()
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    last = memory.get("last_ask_dj") if isinstance(memory, dict) else {}
    if isinstance(last, dict) and last.get("input"):
        return str(last.get("input") or "").strip()
    return ""


def _conversational_response_text(normalized: str) -> str:
    if "geeft niet" in normalized or "maakt niet uit" in normalized or "no worries" in normalized:
        return "Dank je, volgende keer beter ;)"
    if normalized in {"dank je", "dankjewel", "bedankt", "thanks", "thank you"} or normalized.startswith(("thanks ", "dank je ")):
        return "Graag gedaan."
    if "laat maar" in normalized or "never mind" in normalized:
        return "Helemaal goed, ik laat 'm liggen."
    if "jammer" in normalized or "helaas" in normalized:
        return "Ja, jammer. Ik probeer het de volgende keer beter te checken."
    if "hoeft niet" in normalized:
        return "Prima, dan laat ik het zo."
    if normalized == "nee":
        return "Helemaal goed, dan laat ik die vraag liggen."
    if normalized in {"ok", "okay", "oke", "prima", "top"} or normalized.startswith(("ok ", "oke ")):
        return "Helemaal goed."
    return "Helemaal goed."


def _handle_conversational_followup(turn: AskDjConversationTurn) -> dict[str, Any]:
    text = turn.response_text or "Helemaal goed."
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "message": text,
        "action": "none",
    }


def classify_ask_dj(text: str) -> AskDjIntent:
    """Classify Ask DJ text into informational, action or hybrid buckets."""
    normalized = _normalize(text)
    if _is_help_request(normalized):
        return AskDjIntent("informational", "help", "none")
    if _is_personal_music_profile_request(normalized):
        return AskDjIntent(
            "informational",
            "personal_music_profile_analysis",
            "profile_analysis",
        )
    if _is_morning_start_request(normalized):
        return AskDjIntent(
            "informational",
            "morning_music_suggestion",
            "none",
        )
    if _is_save_generated_playlist_request(normalized):
        return AskDjIntent("informational", "save_generated_playlist", "create_playlist")
    if _is_seed_mix_playlist_request(normalized):
        return AskDjIntent("informational", "build_playlist_from_seeds", "none")
    if _is_song_recommendation_request(normalized):
        return AskDjIntent("informational", "song_recommendations", "none")
    if _is_personal_recommendation_request(normalized):
        return AskDjIntent(
            "informational",
            "personal_music_recommendations",
            "none",
        )
    if _is_playlist_search_request(normalized):
        return AskDjIntent("informational", "spotify_playlist_search", "none")
    if _is_next_track_info_request(normalized):
        return AskDjIntent("informational", "next_track_info", "queue")
    if _is_concert_agenda_request(normalized):
        return AskDjIntent("informational", "artist_concerts", "concert_agenda")
    if any(phrase in normalized for phrase in ("waarom koos", "waarom heb je", "vertel iets", "wanneer speelt", "analyseer", "welke albums", "album art", "cover")):
        return AskDjIntent("informational", "ask_music_info")
    if any(term in normalized for term in ("vergelijkbaar", "vergelijkbare", "similar", "zelfde soort", "lijkt op", "nog meer leuk")):
        return AskDjIntent("informational", "ask_music_info")
    if any(phrase in normalized for phrase in ("aankondiging", "dj intro", "intro voor", "wat nu speelt")):
        return AskDjIntent("hybrid", "dj_announcement", "announce", play=False)
    if any(word in normalized for word in ("pauzeer", "stop muziek", "stop de muziek", "ik ga slapen", "ga slapen")):
        return AskDjIntent("action", "playback_control", "pause")
    if any(
        phrase in normalized
        for phrase in (
            "start muziek",
            "start de muziek",
            "speel verder",
            "hervat muziek",
            "hervat de muziek",
            "resume",
        )
    ):
        return AskDjIntent("action", "playback_control", "play")
    if "volgende" in normalized or normalized in {"next", "skip", "next song", "next track"}:
        return AskDjIntent("action", "playback_control", "next")
    if (
        "vorige" in normalized
        or "vorig nummer" in normalized
        or normalized in {"previous", "previous song", "previous track"}
    ):
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
    if _is_output_selection_request(normalized):
        return AskDjIntent("informational", "list_outputs", "devices")
    if "waarop" in normalized and "muziek" in normalized:
        return AskDjIntent("informational", "current_output", "status")
    if _is_deferred_playback_request(normalized):
        return AskDjIntent("hybrid", "play_music", "play_music", play=True)
    if re.search(r"\b(speel|draai|zet)\b", normalized):
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
            "images": [],
            "links": [],
            "sources": [],
        }
    if action in {"pause", "play", "next", "previous"}:
        result = await handle_spotify_command(hass, runtime, action)
        text_response = _action_text(action)
        return {
            "success": True,
            "text": text_response,
            "dj_text": text_response,
            "playback": result.get("playback") if isinstance(result, dict) else {},
            "images": [],
            "links": [],
            "sources": [],
            "playback_actions": _playback_control_actions(action),
        }
    if action == "set_shuffle":
        await handle_spotify_command(hass, runtime, "set_shuffle", classification.value)
        text_response = "Shuffle staat aan." if classification.value else "Shuffle staat uit."
        return {"success": True, "text": text_response, "dj_text": text_response}
    if action == "set_repeat":
        await handle_spotify_command(hass, runtime, "set_repeat", classification.value)
        text_response = "Repeat is uitgezet." if classification.value == "off" else "Repeat is aangezet."
        return {"success": True, "text": text_response, "dj_text": text_response}
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
        dj_text = _playback_failed_text(runtime, text)
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


async def _deferred_playback_request_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
) -> dict[str, Any]:
    parsed = parse_spoken_music_request(text)
    media_type = str(parsed.get("type") or "track").strip().lower() or "track"
    query = str(parsed.get("query") or text or "").strip()
    try:
        result = await handle_spotify_command(
            hass,
            runtime,
            "search_media",
            {"query": query, "type": media_type},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect deferred playback search failed: %s", exc)
        message = "Ik kon je verzoek nu niet concreet vinden op Spotify."
        return {"success": True, "text": message, "dj_text": message, "action": "none"}
    item = result.get("item") if isinstance(result, dict) else {}
    if not isinstance(item, dict) or not item.get("uri"):
        message = "Ik kon je verzoek nu niet concreet vinden op Spotify."
        return {"success": True, "text": message, "dj_text": message, "action": "none"}
    action = _play_now_action_from_spotify_item(hass, item)
    title = str(action.get("title") or "je verzoek").strip()
    subtitle = str(action.get("subtitle") or "").strip()
    label = f"{title} van {subtitle}" if subtitle else title
    message = (
        f"Ik heb {label} vooraan klaargezet. "
        "Wil je hem nu direct horen? Tik dan op Play Now."
    )
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "playback_actions": [action],
        "sources": [{"source": "spotify_search", "title": "Spotify search", "kind": "source"}],
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
    ask_intent = classify_ask_dj(text)
    if ask_intent.intent == "help":
        return _help_response()
    if ask_intent.action == "devices":
        message = _devices_text(output_devices)
        actions = _output_device_actions(output_devices)
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "intent": {"category": "informational", "intent": "list_outputs"},
            "images": [],
            "links": [],
            "sources": [],
            "playback_actions": actions,
        }
    if ask_intent.action == "status":
        message = _current_output_text(playback_context)
        return {"success": True, "text": message, "dj_text": message}
    if ask_intent.intent == "morning_music_suggestion":
        return await _morning_music_suggestion_response(
            hass,
            runtime,
            payload,
            memory_context,
            playback_context,
        )
    if ask_intent.intent == "next_track_info":
        return await _next_track_info_response(hass, runtime)
    if _is_slang_track_info_request(text):
        return _current_track_reference_response(hass, playback_context)
    if ask_intent.intent == "save_generated_playlist":
        return await _save_generated_playlist(hass, runtime, text, memory_context)
    if ask_intent.intent == "song_recommendations":
        return await _song_recommendations_response(hass, runtime, text)
    seed_mix = _seeds_from_mix_playlist_request(text) if ask_intent.intent == "build_playlist_from_seeds" else {}
    if seed_mix:
        result = await _spotify_seed_mix(hass, runtime, seed_mix)
        tracks = result.get("tracks") if isinstance(result, dict) else []
        action = _seed_mix_playback_action(hass, seed_mix, tracks)
        if action:
            message = (
                "Ik heb een mix samengesteld op basis van "
                + _seed_mix_label(seed_mix)
                + ". Ik start nog niets; tik op Play Now om de mix te horen."
            )
        else:
            message = (
                "Ik kon nu geen speelbare Spotify-mix samenstellen met deze artiesten."
            )
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "playback_actions": [action] if action else [],
            "sources": [
                {
                    "source": "spotify_recommendations",
                    "kind": "source",
                    "title": "Spotify recommendations",
                }
            ],
        }
    playlist_query = _playlist_query_from_question(text)
    if playlist_query:
        result = await _spotify_playlist_search(hass, runtime, playlist_query)
        playlists = result.get("playlists") if isinstance(result, dict) else []
        actions = _playlist_search_playback_actions(hass, playlists)
        if actions:
            message = (
                f"Zeker. Ik vond deze Spotify-playlists voor {playlist_query}. "
                "Ik start nog niets; tik op Play Now bij de playlist die je wilt horen."
            )
        else:
            message = f"Ik vond nu geen Spotify-playlists voor {playlist_query}."
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "playback_actions": actions,
            "sources": [
                {
                    "source": "spotify_playlist_search",
                    "kind": "source",
                    "title": "Spotify playlist search",
                }
            ],
        }
    album_artist = _artist_from_album_question(text)
    if not album_artist and _is_current_artist_album_question(text):
        album_artist = _artist_from_playback_context(playback_context)
    if album_artist:
        discography = await _spotify_artist_albums(hass, runtime, album_artist)
        if discography:
            return _artist_albums_response(hass, discography)
    similar_artist = _artist_from_similar_artists_question(
        text,
        memory_context,
        playback_context,
    )
    if similar_artist:
        related = await _spotify_related_artists(hass, runtime, similar_artist)
        if related and related.get("artists"):
            spotify_profile = await _listening_profile_context(
                hass,
                runtime,
                payload,
                memory_context,
            )
            return _related_artists_response(related, memory_context, spotify_profile)
    concert_artist = _artist_from_concert_question(
        text,
        memory_context,
        playback_context,
    )
    if concert_artist:
        events = await _fetch_artist_concert_events(hass, concert_artist)
        return _artist_concerts_response(concert_artist, events)
    genre_artist = _artist_from_genre_question(
        text,
        memory_context,
        playback_context,
    )
    if genre_artist:
        profile = await _spotify_artist_profile(hass, runtime, genre_artist)
        if profile:
            return _artist_genre_response(profile)
    if ask_intent.intent == "personal_music_profile_analysis":
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
    if ask_intent.intent == "personal_music_recommendations":
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
            limit=5,
        )
        if actions:
            message = (
                "Verrassing. Ik heb vijf suggesties gekozen op basis van je DJ Memory en Spotify-profiel. "
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
            "confirmation_actions": _confirmation_actions() if actions else [],
            "sources": _profile_sources(memory_context, spotify_profile),
        }

    if _looks_like_gibberish(text) or _looks_like_prompt_or_sandbox_attack(text):
        message = _unrecognized_request_text()
        return {"success": True, "text": message, "dj_text": message, "action": "none"}

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


async def _spotify_artist_albums(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    try:
        result = await handle_spotify_command(
            hass,
            runtime,
            "artist_albums",
            {"artist": artist},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify artist albums unavailable: %s", exc)
        return {}
    return result if isinstance(result, dict) else {}


async def _morning_music_suggestion_response(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    if _playback_is_active(playback_context):
        text = "Goedemorgen! Er speelt al muziek, dus ik laat alles lekker doorlopen."
        return {"success": True, "text": text, "dj_text": text, "action": "none"}
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
        limit=1,
    )
    selected = actions[:1]
    if selected:
        action = selected[0]
        title = str(action.get("title") or "je ochtendmuziek").strip()
        subtitle = str(action.get("subtitle") or "").strip()
        item = f"{title} van {subtitle}" if subtitle else title
        text = f"Goedemorgen! Zal ik {item} voor je aanzetten?"
        await _store_pending_followup(
            runtime,
            payload,
            question=text,
            proposed_intent="morning_music_suggestion",
            proposed_action="ask_dj_play_recommendation",
            proposed_payload=action,
        )
    else:
        text = "Goedemorgen! Zal ik iets rustigs opzetten om de dag te starten?"
    confirmations = _confirmation_actions()
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "intent": {"category": "playback_confirmation", "intent": "morning_music_suggestion"},
        "playback_actions": [*selected, *confirmations],
        "confirmation_actions": confirmations,
        "sources": _profile_sources(memory_context, spotify_profile),
    }


async def _next_track_info_response(
    hass: HomeAssistant,
    runtime: Any,
) -> dict[str, Any]:
    try:
        result = await handle_spotify_command(hass, runtime, "queue")
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify queue unavailable for Ask DJ: %s", exc)
        result = {}
    queue = result.get("queue") if isinstance(result, dict) else []
    current_uri = _current_playback_uri(runtime)
    queue_items = [
        item
        for item in (queue if isinstance(queue, list) else [])
        if isinstance(item, dict)
        and item
        and not (current_uri and str(item.get("uri") or "").strip() == current_uri)
    ]
    next_track = queue_items[0] if queue_items else {}
    current_uri = _current_playback_uri(runtime)
    next_uri = str(next_track.get("uri") or "").strip() if isinstance(next_track, dict) else ""
    if not isinstance(next_track, dict) or not next_track or (current_uri and next_uri == current_uri):
        text = (
            "Er staat nu geen volgend nummer in de Spotify wachtrij. "
            "Wil je wat anders horen? Laat het me weten. Zeg simpelweg 'verras me' "
            "en ik speel muziek op basis van jouw voorkeur."
        )
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "images": [],
            "playback_actions": [],
            "sources": [{"source": "spotify_queue", "title": "Spotify queue", "kind": "source"}],
        }
    first_five = queue_items[:5]
    lines = ["Dit zijn de eerste nummers in je Spotify wachtrij:"]
    images = []
    playback_actions = []
    for index, item in enumerate(first_five, start=1):
        title = str(item.get("title") or item.get("track_name") or f"nummer {index}").strip()
        artist = str(item.get("subtitle") or item.get("artist") or "").strip()
        uri = str(item.get("uri") or "").strip()
        label = f"{title} - {artist}" if artist else title
        lines.append(f"{index}. {label}")
        image_url = str(item.get("image_url") or item.get("album_image_url") or item.get("thumbnail_url") or "").strip()
        proxy = register_image_proxy_url(hass, image_url) if image_url.startswith(("http://", "https://")) else image_url
        if proxy:
            images.append(
                {
                    "url": proxy,
                    "thumbnail_url": proxy,
                    "title": title,
                    "subtitle": artist,
                    "kind": "album_art",
                    "source": "spotify",
                }
            )
        if uri.startswith("spotify:track:"):
            action: dict[str, Any] = {
                "id": uri,
                "title": title,
                "subtitle": artist,
                "uri": uri,
                "kind": "track",
                "reason": "Track uit je Spotify wachtrij.",
            }
            context_uri = str(item.get("context_uri") or item.get("contextUri") or result.get("context_uri") or "").strip()
            if context_uri:
                action["context_uri"] = context_uri
                action["offset_uri"] = uri
            if proxy:
                action["image_url"] = proxy
            playback_actions.append(action)
    lines.append("Tik op Play Now om een nummer uit de wachtrij nu naar voren te halen.")
    text = "\n".join(lines)
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": images,
        "playback_actions": playback_actions,
        "sources": [{"source": "spotify_queue", "title": "Spotify queue", "kind": "source"}],
    }


def _current_playback_uri(runtime: Any) -> str:
    playback = getattr(runtime, "last_playback", None)
    if not isinstance(playback, dict):
        status = getattr(runtime, "device_status", {}) or {}
        playback = status.get("playback") if isinstance(status, dict) else {}
    if not isinstance(playback, dict):
        return ""
    for key in ("uri", "track_uri", "trackUri"):
        value = str(playback.get(key) or "").strip()
        if value:
            return value
    track = playback.get("track")
    if isinstance(track, dict):
        for key in ("uri", "track_uri", "trackUri"):
            value = str(track.get(key) or "").strip()
            if value:
                return value
    return ""


def _current_track_reference_response(
    hass: HomeAssistant,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    track = _track_label(playback_context)
    if not track:
        text = "Ik weet niet welke track je bedoelt."
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "images": [],
            "playback_actions": [],
        }
    text = f"Die track is {track}."
    images = _images_from_context(hass, {}, playback_context)
    uri = str(playback_context.get("uri") or playback_context.get("track_uri") or "").strip()
    playback_actions: list[dict[str, Any]] = []
    if uri.startswith("spotify:track:"):
        title = str(
            playback_context.get("track_name")
            or playback_context.get("title")
            or playback_context.get("name")
            or track
        ).strip()
        artist = str(playback_context.get("artist") or playback_context.get("artist_name") or "").strip()
        action: dict[str, Any] = {
            "id": uri,
            "title": title,
            "subtitle": artist,
            "uri": uri,
            "kind": "track",
            "reason": "Huidige track waar je informeel naar verwijst.",
        }
        if images:
            action["image_url"] = images[0]["url"]
        playback_actions.append(action)
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": images,
        "playback_actions": playback_actions,
        "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
    }


async def _spotify_related_artists(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    try:
        result = await handle_spotify_command(
            hass,
            runtime,
            "related_artists",
            {"artist": artist},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify related artists unavailable: %s", exc)
        return {}
    return result if isinstance(result, dict) else {}


async def _spotify_artist_profile(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    try:
        result = await handle_spotify_command(
            hass,
            runtime,
            "artist_profile",
            {"artist": artist},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify artist profile unavailable: %s", exc)
        return {}
    artist_profile = result.get("artist") if isinstance(result, dict) else {}
    return artist_profile if isinstance(artist_profile, dict) else {}


def _artist_albums_response(hass: HomeAssistant, discography: dict[str, Any]) -> dict[str, Any]:
    albums = discography.get("albums") if isinstance(discography, dict) else []
    if not isinstance(albums, list) or not albums:
        artist = str(discography.get("artist") or "deze artiest").strip()
        text = f"Ik vind via Spotify geen albumlijst voor {artist}."
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "sources": [{"source": "spotify_artist_albums", "title": "Spotify artist albums", "kind": "source"}],
        }
    artist = str(discography.get("artist") or albums[0].get("artist") or "deze artiest").strip()
    album_labels = []
    visible_albums = albums[:20]
    for album in visible_albums:
        if not isinstance(album, dict):
            continue
        title = str(album.get("name") or album.get("title") or "").strip()
        year = str(album.get("release_date") or "").strip()[:4]
        if title:
            album_labels.append(f"- {title} ({year})" if year else f"- {title}")
    if not album_labels:
        text = f"Ik vind via Spotify geen bruikbare albumtitels voor {artist}."
    else:
        extra_count = len(albums) - len(album_labels)
        suffix = (
            ""
            if extra_count <= 0
            else f"\n\nSpotify toont daarnaast nog {extra_count} albumvermelding(en), vaak deluxe/live/remaster varianten."
        )
        text = (
            f"Volgens Spotify heeft {artist} onder andere deze albums uitgebracht:\n\n"
            f"{chr(10).join(album_labels)}"
            f"{suffix}\n\n"
            "Tik op Play Now om een album direct te starten."
        )
    images = [
        {
            "url": str(album.get("image_url") or album.get("album_image_url") or ""),
            "title": str(album.get("name") or album.get("title") or "Album"),
            "subtitle": str(album.get("release_date") or ""),
            "kind": "album_art",
            "source": "spotify",
        }
        for album in visible_albums
        if isinstance(album, dict) and (album.get("image_url") or album.get("album_image_url"))
    ]
    playback_actions: list[dict[str, Any]] = []
    for album in visible_albums:
        if not isinstance(album, dict):
            continue
        uri = str(album.get("uri") or album.get("album_uri") or "").strip()
        if not uri.startswith("spotify:album:"):
            continue
        title = str(album.get("name") or album.get("title") or "Album").strip()
        release_date = str(album.get("release_date") or "").strip()
        image_url = str(album.get("image_url") or album.get("album_image_url") or "").strip()
        action: dict[str, Any] = {
            "id": uri,
            "title": title,
            "subtitle": f"{artist} · {release_date[:4]}" if release_date[:4] else artist,
            "uri": uri,
            "context_uri": uri,
            "kind": "album",
            "reason": f"Album van {artist}.",
        }
        if image_url:
            action["image_url"] = (
                register_image_proxy_url(hass, image_url)
                if image_url.startswith(("http://", "https://"))
                else image_url
            )
        playback_actions.append(action)
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": images,
        "playback_actions": playback_actions,
        "sources": [{"source": "spotify_artist_albums", "title": "Spotify artist albums", "kind": "source"}],
    }


def _related_artists_response(
    related: dict[str, Any],
    memory_context: dict[str, Any] | None = None,
    spotify_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artists = related.get("artists") if isinstance(related, dict) else []
    if not isinstance(artists, list) or not artists:
        artist = str(related.get("artist") or "deze artiest").strip()
        text = f"Ik vind via Spotify geen vergelijkbare artiesten voor {artist}."
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "sources": [{"source": "spotify_related_artists", "title": "Spotify related artists", "kind": "source"}],
        }
    source_artist = str(related.get("artist") or "deze artiest").strip()
    visible = artists[:12]
    labels = [str(item.get("name") or item.get("title") or "").strip() for item in visible if isinstance(item, dict)]
    labels = [label for label in labels if label]
    profile_hint = _profile_artist_hint(memory_context or {}, spotify_profile or {})
    text = (
        f"Volgens Spotify zitten deze artiesten in dezelfde muzikale buurt als {source_artist}: "
        + ", ".join(labels)
        + "."
        if labels
        else f"Ik vind via Spotify geen bruikbare vergelijkbare artiesten voor {source_artist}."
    )
    if labels and profile_hint:
        text = f"{profile_hint} {text}"
    images = [
        {
            "url": str(item.get("image_url") or item.get("artist_image_url") or ""),
            "title": str(item.get("name") or item.get("title") or "Artiest"),
            "subtitle": ", ".join(str(genre) for genre in (item.get("genres") or [])[:3]),
            "kind": "artist_image",
            "source": "spotify",
        }
        for item in visible
        if isinstance(item, dict) and (item.get("image_url") or item.get("artist_image_url"))
    ]
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": images,
        "sources": [
            {"source": "spotify_related_artists", "title": "Spotify related artists", "kind": "source"},
            *(_profile_sources(memory_context or {}, spotify_profile or {}) if profile_hint else []),
        ],
    }


def _artist_genre_response(profile: dict[str, Any]) -> dict[str, Any]:
    artist = str(profile.get("name") or profile.get("artist") or "deze artiest").strip()
    genres = [str(genre).strip() for genre in (profile.get("genres") or []) if str(genre).strip()]
    if not genres:
        text = f"Spotify geeft voor {artist} geen duidelijke genre-tags terug. Ik kan het daardoor niet betrouwbaar inkleuren."
    else:
        text = f"{artist} maakt vooral {_genre_phrase(genres)}."
    image_url = str(profile.get("image_url") or profile.get("artist_image_url") or "").strip()
    images = [
        {
            "url": image_url,
            "title": artist,
            "subtitle": ", ".join(genres[:3]),
            "kind": "artist_image",
            "source": "spotify",
        }
    ] if image_url else []
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": images,
        "sources": [{"source": "spotify_artist_profile", "title": "Spotify artist profile", "kind": "source"}],
    }


def _genre_phrase(genres: list[str]) -> str:
    clean = [genre.replace("-", " ").strip() for genre in genres if genre.strip()]
    if not clean:
        return "muziek die lastig in een genre te vangen is"
    primary = clean[0]
    if len(clean) == 1:
        return primary
    if len(clean) == 2:
        return f"een mix van {primary} met een vleugje {clean[1]}"
    return f"een mix van {primary}, {clean[1]} en een vleugje {clean[2]}"


def _artist_from_album_question(text: str) -> str:
    normalized = _normalize(text)
    if "album" not in normalized:
        return ""
    patterns = (
        r"^\s*(?:geef|toon|laat\s+zien|show|give)\s+(?:me|mij)?\s*(?:de\s+)?albums\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*welke\s+albums\s+(?:heeft|hebben)\s+(.+?)\s+(?:allemaal\s+)?(?:uitgebracht|gemaakt|released)\s*\??\s*$",
        r"^\s*welke\s+albums\s+bracht\s+(.+?)\s+uit\s*\??\s*$",
        r"^\s*welke\s+albums\s+zijn\s+er\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*albums\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*which\s+albums\s+(?:has|have)\s+(.+?)\s+released\s*\??\s*$",
        r"^\s*what\s+albums\s+did\s+(.+?)\s+release\s*\??\s*$",
        r"^\s*albums\s+by\s+(.+?)\s*\??\s*$",
    )
    value = str(text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            artist = _clean_artist_name(match.group(1))
            if _normalize(artist) in {"deze artiest", "de artiest", "this artist", "the artist"}:
                return ""
            return artist
    return ""


def _artist_from_genre_question(
    text: str,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
) -> str:
    normalized = _normalize(text)
    if not any(term in normalized for term in ("wat voor muziek", "welk genre", "welke genre", "genre", "soort muziek", "what kind of music", "what genre")):
        return ""
    explicit = _explicit_artist_from_genre_question(text)
    if explicit:
        return explicit
    if any(
        phrase in normalized
        for phrase in (
            "deze artiest",
            "die artiest",
            "huidige artiest",
            "deze band",
            "wat nu speelt",
            "nu speelt",
            "this artist",
            "current artist",
            "this band",
        )
    ):
        return _artist_from_playback_context(playback_context)
    if "conversatie" in normalized or "gesprek" in normalized or "conversation" in normalized:
        return _artist_from_server_history_context(memory_context) or _artist_from_recent_context(memory_context) or _artist_from_playback_context(playback_context)
    return _artist_from_recent_context(memory_context) or _artist_from_playback_context(playback_context)


def _explicit_artist_from_genre_question(text: str) -> str:
    patterns = (
        r"^\s*wat\s+voor\s+muziek\s+maakt\s+(.+?)\s*\??\s*$",
        r"^\s*welk(?:e)?\s+genre\s+maakt\s+(.+?)\s*\??\s*$",
        r"^\s*in\s+welk(?:e)?\s+genre\s+valt\s+(.+?)\s*\??\s*$",
        r"^\s*wat\s+is\s+het\s+genre\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*what\s+kind\s+of\s+music\s+does\s+(.+?)\s+make\s*\??\s*$",
        r"^\s*what\s+genre\s+is\s+(.+?)\s*\??\s*$",
    )
    value = str(text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            artist = _clean_artist_name(match.group(1))
            if _normalize(artist) in {"deze artiest", "die artiest", "huidige artiest", "wat nu speelt"}:
                return ""
            return artist
    return ""


def _is_concert_agenda_request(normalized: str) -> bool:
    if not normalized:
        return False
    return any(
        term in normalized
        for term in (
            "concert",
            "concerten",
            "tour",
            "tourdata",
            "tour dates",
            "optreden",
            "optredens",
            "speelt in nederland",
            "wanneer speelt",
            "wanneer treedt",
            "when is",
            "when does",
            "live dates",
        )
    )


def _artist_from_concert_question(
    text: str,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
) -> str:
    normalized = _normalize(text)
    if not _is_concert_agenda_request(normalized):
        return ""
    explicit = _explicit_artist_from_concert_question(text)
    if explicit:
        return explicit
    if any(
        phrase in normalized
        for phrase in (
            "deze artiest",
            "die artiest",
            "huidige artiest",
            "deze band",
            "die band",
            "wat nu speelt",
            "nu speelt",
            "this artist",
            "current artist",
            "this band",
        )
    ):
        return _artist_from_playback_context(playback_context)
    return _artist_from_server_history_context(memory_context) or _artist_from_recent_context(memory_context) or _artist_from_playback_context(playback_context)


def _explicit_artist_from_concert_question(text: str) -> str:
    patterns = (
        r"^\s*heeft\s+(deze\s+artiest|die\s+artiest|huidige\s+artiest|deze\s+band|die\s+band)\s+(?:binnenkort\s+)?(?:concerten|tourdata|optredens)\s*\??\s*$",
        r"^\s*wanneer\s+speelt\s+(.+?)(?:\s+in\s+.+?)?\s*\??\s*$",
        r"^\s*wanneer\s+treedt\s+(.+?)(?:\s+op|\s+in\s+.+?)?\s*\??\s*$",
        r"^\s*waar\s+speelt\s+(.+?)(?:\s+binnenkort|\s+live)?\s*\??\s*$",
        r"^\s*(?:concerten|concertagenda|tourdata|tour)\s+(?:van|voor)\s+(.+?)\s*\??\s*$",
        r"^\s*heeft\s+(.+?)\s+(?:binnenkort\s+)?(?:concerten|tourdata|optredens)\s*\??\s*$",
        r"^\s*when\s+(?:does|is)\s+(.+?)\s+(?:play|playing|touring)(?:\s+.+?)?\s*\??\s*$",
        r"^\s*(?:concerts|tour dates|live dates)\s+(?:for|by)\s+(.+?)\s*\??\s*$",
    )
    value = str(text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            artist = _clean_artist_name(match.group(1))
            if _normalize(artist) in {
                "deze artiest",
                "die artiest",
                "huidige artiest",
                "deze band",
                "die band",
                "wat nu speelt",
            }:
                return ""
            return artist
    return ""


async def _fetch_artist_concert_events(
    hass: HomeAssistant,
    artist: str,
) -> list[dict[str, Any]]:
    """Fetch upcoming artist concerts from a public web agenda source."""
    clean_artist = _clean_artist_name(artist)
    if not clean_artist:
        return []
    session = async_get_clientsession(hass)
    url = BANDSINTOWN_EVENTS_URL.format(artist=quote(clean_artist, safe=""))
    params = {
        "app_id": BANDSINTOWN_APP_ID,
        "date": "upcoming",
    }
    try:
        async with session.get(
            url,
            params=params,
            timeout=ClientTimeout(total=8),
        ) as response:
            if getattr(response, "status", 0) != 200:
                _LOGGER.debug(
                    "DJConnect concert agenda lookup failed status=%s artist=%s",
                    getattr(response, "status", None),
                    clean_artist,
                )
                return []
            data = await response.json(content_type=None)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect concert agenda lookup unavailable: %s", exc)
        return []
    if not isinstance(data, list):
        return []
    events = [_normalize_concert_event(item) for item in data[:12] if isinstance(item, dict)]
    return [event for event in events if event.get("date") or event.get("location")]


def _normalize_concert_event(item: dict[str, Any]) -> dict[str, Any]:
    venue = item.get("venue") if isinstance(item.get("venue"), dict) else {}
    city = str(venue.get("city") or "").strip()
    region = str(venue.get("region") or "").strip()
    country = str(venue.get("country") or "").strip()
    name = str(venue.get("name") or item.get("venue_name") or "").strip()
    location_parts = [part for part in (name, city, region, country) if part]
    return {
        "date": _format_concert_date(str(item.get("datetime") or item.get("date") or "").strip()),
        "location": ", ".join(location_parts),
        "url": str(item.get("url") or item.get("facebook_rsvp_url") or "").strip(),
        "title": str(item.get("title") or "").strip(),
        "source": "bandsintown",
    }


def _format_concert_date(value: str) -> str:
    if not value:
        return ""
    date_part = value.split("T", 1)[0]
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date_part)
    if not match:
        return date_part or value
    year, month, day = match.groups()
    months = {
        "01": "jan",
        "02": "feb",
        "03": "mrt",
        "04": "apr",
        "05": "mei",
        "06": "jun",
        "07": "jul",
        "08": "aug",
        "09": "sep",
        "10": "okt",
        "11": "nov",
        "12": "dec",
    }
    return f"{int(day)} {months.get(month, month)} {year}"


def _artist_concerts_response(
    artist: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    clean_artist = _clean_artist_name(artist) or "deze artiest"
    visible = [event for event in events if isinstance(event, dict)][:8]
    if not visible:
        text = (
            f"Ik vind nu geen actuele concertagenda voor {clean_artist}. "
            "Check voor de zekerheid de officiele artist site of ticketkanalen."
        )
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "sources": [{"source": "bandsintown", "title": "Bandsintown", "kind": "source"}],
        }
    lines = [f"Ik vond deze aankomende concerten voor {clean_artist}:"]
    links: list[dict[str, Any]] = []
    for index, event in enumerate(visible, start=1):
        date = str(event.get("date") or "datum onbekend").strip()
        location = str(event.get("location") or "locatie onbekend").strip()
        url = str(event.get("url") or "").strip()
        line = f"{index}. {date} - {location}"
        if url:
            line = f"{line} - {url}"
            links.append(
                {
                    "url": url,
                    "title": f"{date} - {location}",
                    "subtitle": clean_artist,
                    "kind": "source",
                    "source": "bandsintown",
                }
            )
        lines.append(line)
    text = "\n".join(lines)
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "links": links,
        "sources": [{"source": "bandsintown", "title": "Bandsintown", "kind": "source"}],
    }


def _artist_from_similar_artists_question(
    text: str,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
) -> str:
    normalized = _normalize(text)
    if not any(term in normalized for term in ("vergelijkbaar", "vergelijkbare", "similar", "zelfde soort", "lijkt op", "zoals", "nog meer leuk")):
        return ""
    if not any(term in normalized for term in ("artiest", "artiesten", "artist", "artists", "muziek", "music")):
        return ""
    explicit = _explicit_artist_from_similar_question(text)
    if explicit:
        return explicit
    if any(
        phrase in normalized
        for phrase in (
            "wat nu speelt",
            "nu speelt",
            "deze artiest",
            "die artiest",
            "huidige artiest",
            "deze band",
            "die band",
            "current artist",
            "this artist",
            "that artist",
            "this band",
        )
    ):
        return _artist_from_playback_context(playback_context)
    if "conversatie" in normalized or "gesprek" in normalized or "conversation" in normalized:
        return _artist_from_server_history_context(memory_context) or _artist_from_recent_context(memory_context) or _artist_from_playback_context(playback_context)
    return _artist_from_recent_context(memory_context) or _artist_from_playback_context(playback_context)


def _explicit_artist_from_similar_question(text: str) -> str:
    patterns = (
        r"^\s*welke\s+artiesten\s+maken\s+vergelijkbare\s+muziek\s+(?:als|zoals)\s+(.+?)\s*\??\s*$",
        r"^\s*welke\s+artiesten\s+lijken\s+op\s+(.+?)\s*\??\s*$",
        r"^\s*vergelijkbare\s+artiesten\s+(?:als|zoals)\s+(.+?)\s*\??\s*$",
        r"^\s*similar\s+artists\s+(?:to|like)\s+(.+?)\s*\??\s*$",
        r"^\s*which\s+artists\s+make\s+similar\s+music\s+(?:to|as)\s+(.+?)\s*\??\s*$",
    )
    value = str(text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            artist = _clean_artist_name(match.group(1))
            if _normalize(artist) in {
                "wat nu speelt",
                "deze artiest",
                "die artiest",
                "huidige artiest",
                "de artiest waar het in de conversatie over gaat",
            }:
                return ""
            return artist
    return ""


def _artist_from_recent_context(memory_context: dict[str, Any]) -> str:
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    last = memory.get("last_ask_dj") if isinstance(memory, dict) else {}
    if isinstance(last, dict):
        track = last.get("track") if isinstance(last.get("track"), dict) else {}
        for key in ("artist", "artist_name"):
            value = str(track.get(key) or "").strip()
            if value:
                return value
        text = str(last.get("input") or "").strip()
        artist = (
            _artist_from_album_question(text)
            or _explicit_artist_from_similar_question(text)
            or _explicit_artist_from_concert_question(text)
            or _explicit_artist_from_genre_question(text)
        )
        if artist:
            return artist
    history = memory_context.get("server_history") if isinstance(memory_context, dict) else []
    if isinstance(history, list):
        for item in reversed(history):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            artist = (
                _artist_from_album_question(text)
                or _explicit_artist_from_similar_question(text)
                or _explicit_artist_from_concert_question(text)
                or _explicit_artist_from_genre_question(text)
            )
            if artist:
                return artist
    return ""


def _artist_from_server_history_context(memory_context: dict[str, Any]) -> str:
    history = memory_context.get("server_history") if isinstance(memory_context, dict) else []
    if not isinstance(history, list):
        return ""
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        artist = (
            _artist_from_album_question(text)
            or _explicit_artist_from_similar_question(text)
            or _explicit_artist_from_concert_question(text)
            or _explicit_artist_from_genre_question(text)
        )
        if artist:
            return artist
    return ""


def _is_current_artist_album_question(text: str) -> bool:
    normalized = _normalize(text)
    if "album" not in normalized:
        return False
    return any(
        phrase in normalized
        for phrase in (
            "deze artiest",
            "die artiest",
            "huidige artiest",
            "deze band",
            "die band",
            "current artist",
            "this artist",
            "that artist",
            "this band",
        )
    )


def _artist_from_playback_context(playback_context: dict[str, Any]) -> str:
    for key in ("artist", "artist_name"):
        value = str(playback_context.get(key) or "").strip()
        if value:
            return value
    track = playback_context.get("track")
    if isinstance(track, dict):
        for key in ("artist", "artist_name"):
            value = str(track.get(key) or "").strip()
            if value:
                return value
    return ""


def _clean_artist_name(value: str) -> str:
    return re.sub(
        r"\s+(?:allemaal|uitgebracht|gemaakt|released)\s*$",
        "",
        str(value or "").strip(" ?.!'\""),
        flags=re.IGNORECASE,
    ).strip()


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
    images = (
        _images_from_context(hass, result, playback_context)
        if "images" not in result
        else _images_from_context(hass, result, {})
    )
    links = _links_from_context(result, playback_context, classification)
    sources = _sources_from_context(result, links)
    action = result.get("action") or classification.action
    confirmation_actions = result.get("confirmation_actions") or _confirmation_actions_from_playback_actions(result.get("playback_actions"))
    result_intent = result.get("intent") if isinstance(result.get("intent"), dict) else {}
    return {
        "success": bool(result.get("success", True)),
        "text": text,
        "dj_text": text,
        "message": text,
        "images": images,
        "links": links,
        "sources": sources,
        "playback_actions": result.get("playback_actions") or [],
        "confirmation_actions": confirmation_actions,
        "error": result.get("error"),
        "intent": {
            "category": result_intent.get("category") or classification.category,
            "intent": result_intent.get("intent") or classification.intent,
        },
        "action": action,
        "memory_key": memory_key,
        "playback": result.get("playback") or playback_context,
        "assistant_message": {
            "role": "assistant",
            "message_kind": str(result.get("message_kind") or "assistant"),
            "origin": str(result.get("origin") or ""),
            "text": text,
            "images": images,
            "links": links,
            "sources": sources,
            "playback_actions": result.get("playback_actions") or [],
            "confirmation_actions": confirmation_actions,
        },
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
    if normalized in {
        "verras me",
        "verras mij",
        "doe maar wat",
        "nee doe maar wat",
        "nee verras me",
        "nee verras mij",
        "surprise me",
        "speel wat anders",
        "speel iets anders",
        "draai wat anders",
        "draai iets anders",
        "play something else",
        "play something different",
    }:
        return True
    if any(
        phrase in normalized
        for phrase in (
            "verras me",
            "verras mij",
            "doe maar wat",
            "surprise me",
            "speel wat anders",
            "speel iets anders",
            "draai wat anders",
            "draai iets anders",
            "play something else",
            "play something different",
        )
    ):
        return True
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


def _is_song_recommendation_request(normalized: str) -> bool:
    if not any(term in normalized for term in ("nummer", "nummers", "track", "tracks", "song", "songs")):
        return False
    return any(
        term in normalized
        for term in (
            "heb je",
            "geef",
            "toon",
            "laat zien",
            "aanbevel",
            "recommend",
            "suggest",
            "toffe",
            "leuke",
            "vette",
            "goede",
        )
    )


def _song_recommendation_seeds(text: str) -> dict[str, list[str]]:
    normalized = _normalize(text)
    cleaned = re.sub(
        r"\b(?:heb|hebt|je|jij|een|paar|wat|toffe|leuke|vette|goede|mooie|nummers|nummer|tracks|track|songs|song|aanbevelingen|recommendations|suggestions|voor|me|mij)\b",
        " ",
        normalized,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.strip(" ?.!'\"")
    if cleaned:
        return {"genres": [cleaned]}
    return {}


def _is_deferred_playback_request(normalized: str) -> bool:
    return bool(
        re.search(
            r"\b(?:ik\s+wil|wil\s+ik|ik\s+wil\s+wel|ik\s+wil\s+graag)\b.+\b(?:horen|luisteren|opzetten|spelen)\b",
            normalized,
        )
        or re.search(
            r"\b(?:i\s+want|i\s+would\s+like)\b.+\b(?:hear|listen|play)\b",
            normalized,
        )
    )


def _is_morning_start_request(normalized: str) -> bool:
    return normalized in {
        "goedemorgen",
        "goedemorgen!",
        "goede morgen",
        "good morning",
        "morning",
    }


def _is_next_track_info_request(normalized: str) -> bool:
    if any(
        phrase in normalized
        for phrase in (
            "in de wachtrij",
            "in mijn wachtrij",
            "in spotify wachtrij",
            "in de queue",
            "in mijn queue",
            "in queue",
        )
    ) and any(term in normalized for term in ("welke", "wat", "nummers", "tracks", "songs")):
        return True
    if "volgende" not in normalized and "next" not in normalized:
        return False
    question_prefixes = (
        "wat wordt",
        "wat is",
        "welk nummer wordt",
        "welk nummer is",
        "welke track wordt",
        "welke track is",
        "what is",
        "what will",
        "which song",
        "which track",
    )
    if normalized.startswith(question_prefixes):
        return True
    return normalized.endswith("?") and any(
        phrase in normalized
        for phrase in (
            "volgende nummer",
            "volgende track",
            "next song",
            "next track",
        )
    )


def _is_slang_track_reference(text: str) -> bool:
    normalized = _normalize(text)
    return any(word in normalized for word in TRACK_REFERENCE_WORDS)


def _is_slang_track_info_request(text: str) -> bool:
    normalized = _normalize(text)
    if not _is_slang_track_reference(normalized):
        return False
    return normalized.startswith(("wat is", "welke", "welk", "wie is", "vertel", "waarom", "hoe heet"))


def _is_playlist_search_request(normalized: str) -> bool:
    if "playlist" not in normalized and "afspeellijst" not in normalized:
        return False
    return any(
        phrase in normalized
        for phrase in (
            "heb je",
            "zoek",
            "vind",
            "welke",
            "suggest",
            "recommend",
            "do you have",
            "find",
            "search",
            "doe maar",
            "maak",
            "start",
            "speel",
            "zet",
        )
    )


def _playlist_query_from_question(text: str) -> str:
    original = str(text or "").strip()
    normalized = _normalize(original)
    patterns = (
        r"(?:doe\s+maar|maak|zet|start|speel)\s+(?:eens\s+|even\s+|graag\s+)?(?:een\s+|some\s+)?(?:spotify\s+)?(?:playlist|afspeellijst)\s+(?:met|van|voor|with|about|by|for)\s+(.+)$",
        r"(?:heb je|zoek|vind|welke|do you have|find|search)\s+(?:een\s+|some\s+)?(?:spotify\s+)?(?:playlist|afspeellijst)(?:\s+(?:van|voor|with|about|by|for))?\s+(.+)$",
        r"(?:playlist|afspeellijst)\s+(?:van|voor|with|about|by|for)\s+(.+)$",
        r"(.+?)\s+(?:playlist|afspeellijst)s?\s*$",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return _clean_playlist_query(match.group(1))
    return ""


def _clean_playlist_query(value: str) -> str:
    text = str(value or "").strip(" ?.!'\"")
    text = re.sub(r"^(?:van|voor|with|about|by|for)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:hebben|hebt|zijn|bestaan|please|pls)$", "", text, flags=re.IGNORECASE)
    return text.strip()


def _is_seed_mix_playlist_request(normalized: str) -> bool:
    if not any(term in normalized for term in ("playlist", "afspeellijst", "mix")):
        return False
    return any(
        phrase in normalized
        for phrase in (
            "stel",
            "samen",
            "maak",
            "op basis van",
            "obv",
            "in genre",
            "in genres",
            "based on",
            "make",
            "create",
        )
    ) and bool(_seeds_from_mix_playlist_request(normalized))


def _is_save_generated_playlist_request(normalized: str) -> bool:
    return any(
        phrase in normalized
        for phrase in (
            "sla deze op",
            "sla dit op",
            "bewaar deze",
            "bewaar dit",
            "maak hier een playlist",
            "save this",
            "save it",
            "make this a playlist",
            "create this playlist",
        )
    ) and any(term in normalized for term in ("playlist", "mix", "op", "save", "bewaar"))


def _seeds_from_mix_playlist_request(text: str) -> dict[str, list[str]]:
    cleaned = str(text or "").strip(" ?.!'\"")
    seed_type = "artists"
    if re.search(r"\b(?:track|tracks|nummer|nummers|song|songs)\b", cleaned, flags=re.IGNORECASE):
        seed_type = "tracks"
    elif re.search(r"\b(?:genre|genres)\b", cleaned, flags=re.IGNORECASE):
        seed_type = "genres"
    patterns = (
        r"(?:op basis van|obv|based on)\s+(.+)$",
        r"(?:in genre|in genres|genre|genres)\s+(.+)$",
        r"(?:met|van|voor|with|from)\s+(.+)$",
    )
    source = cleaned
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            source = match.group(1)
            break
    source = re.sub(
        r"^(?:artiesten|artists|tracks|nummers|songs|genres|genre)\s+",
        "",
        source,
        flags=re.IGNORECASE,
    )
    source = re.sub(
        r"\b(?:ik|wil|een|playlist|afspeellijst|mix|samenstellen|samen|maken|maak|stel|create|make|based|basis|obv|in)\b",
        "",
        source,
        flags=re.IGNORECASE,
    )
    candidates = re.split(r"\s*(?:,|;|\+|/|\ben\b|\band\b)\s*", source)
    values: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        value = " ".join(candidate.strip(" ?.!'\"").split())
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            values.append(value)
    return {seed_type: values} if values else {}


async def _spotify_seed_mix(
    hass: HomeAssistant,
    runtime: Any,
    seeds: dict[str, list[str]],
) -> dict[str, Any]:
    try:
        result = await handle_spotify_command(
            hass,
            runtime,
            "artist_recommendations",
            {**seeds, "limit": 25},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify artist recommendations unavailable: %s", exc)
        return {}
    return result if isinstance(result, dict) else {}


async def _song_recommendations_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
) -> dict[str, Any]:
    seeds = _song_recommendation_seeds(text)
    if not seeds:
        message = "Welke stijl of sfeer zoek je voor die nummers?"
        return {"success": True, "text": message, "dj_text": message, "action": "none"}
    try:
        result = await handle_spotify_command(
            hass,
            runtime,
            "artist_recommendations",
            {**seeds, "limit": 10},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify song recommendations unavailable: %s", exc)
        result = {}
    tracks = result.get("tracks") if isinstance(result, dict) else []
    track_actions = _track_recommendation_actions(hass, tracks, limit=10)
    mix_action = _seed_mix_playback_action(hass, seeds, tracks)
    actions = track_actions + ([mix_action] if mix_action else [])
    if track_actions:
        message = (
            f"Zeker. Ik vond deze {len(track_actions)} tracks voor {_seed_mix_label(seeds)}. "
            "Tik op Play Now bij een track, of kies 'Zet allemaal in wachtrij & speel af' om de huidige wachtrij te vervangen."
        )
    else:
        message = "Ik kon nu geen speelbare Spotify-nummers vinden voor die stijl."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "playback_actions": actions,
        "sources": [{"source": "spotify_recommendations", "title": "Spotify recommendations", "kind": "source"}],
    }


def _track_recommendation_actions(
    hass: HomeAssistant,
    tracks: Any,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if not isinstance(tracks, list):
        return []
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in tracks:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        if not uri.startswith("spotify:track:") or uri in seen:
            continue
        seen.add(uri)
        action = _play_now_action_from_spotify_item(hass, {**item, "type": "track"})
        action["label"] = "Play Now"
        action["reason"] = "Aanbevolen op basis van je Ask DJ vraag."
        actions.append(action)
        if len(actions) >= limit:
            break
    return actions


def _seed_mix_playback_action(
    hass: HomeAssistant,
    seeds: dict[str, list[str]],
    tracks: Any,
) -> dict[str, Any]:
    if not isinstance(tracks, list):
        return {}
    track_items = [track for track in tracks if isinstance(track, dict) and track.get("uri")]
    uris = [
        str(track.get("uri") or "").strip()
        for track in track_items
        if str(track.get("uri") or "").startswith("spotify:track:")
    ][:50]
    if not uris:
        return {}
    image_url = str(
        track_items[0].get("album_image_url")
        or track_items[0].get("image_url")
        or track_items[0].get("thumbnail_url")
        or ""
    ).strip()
    proxy_image = (
        register_image_proxy_url(hass, image_url)
        if image_url.startswith(("http://", "https://"))
        else image_url
    )
    label = _seed_mix_label(seeds)
    title = "DJConnect mix: " + label
    return {
        key: value
        for key, value in {
            "id": "djconnect:mix:" + secrets.token_urlsafe(8),
            "title": title,
            "subtitle": f"{len(uris)} Spotify tracks",
            "uri": uris[0],
            "uris": uris,
            "kind": "track_mix",
            "label": "Zet allemaal in wachtrij & speel af",
            "image_url": proxy_image,
            "reason": "Samengesteld op basis van de artiesten in je Ask DJ vraag.",
        }.items()
        if value not in ("", None, [])
    }


def _seed_mix_label(seeds: dict[str, list[str]]) -> str:
    for key, prefix in (
        ("artists", "artiesten "),
        ("tracks", "tracks "),
        ("genres", "genres "),
    ):
        values = seeds.get(key)
        if isinstance(values, list) and values:
            return prefix + _join_examples(values, limit=5)
    return "je Ask DJ vraag"


async def _save_generated_playlist(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    memory_context: dict[str, Any],
) -> dict[str, Any]:
    recommendation = _last_mix_recommendation(memory_context)
    uris = recommendation.get("uris") if isinstance(recommendation, dict) else []
    if not isinstance(uris, list) or not uris:
        message = "Ik heb nog geen samengestelde mix om als Spotify playlist op te slaan."
        return {"success": True, "text": message, "dj_text": message, "action": "none"}
    name = _playlist_name_from_save_request(text) or str(recommendation.get("title") or "DJConnect mix")
    try:
        result = await handle_spotify_command(
            hass,
            runtime,
            "create_playlist",
            {
                "name": name,
                "description": "Samengesteld door DJConnect Ask DJ.",
                "uris": uris,
            },
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify playlist save unavailable: %s", exc)
        message = (
            "Ik kon de Spotify playlist nu niet opslaan. Controleer of DJConnect opnieuw "
            "Spotify toestemming heeft voor playlist-aanpassingen."
        )
        return {
            "success": False,
            "text": message,
            "dj_text": message,
            "error": "spotify_playlist_save_failed",
            "action": "create_playlist",
        }
    playlist = result.get("playlist") if isinstance(result, dict) else {}
    title = str(playlist.get("title") or playlist.get("name") or name).strip()
    message = f"Opgeslagen als Spotify playlist: {title}."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "create_playlist",
        "links": _playlist_links(playlist),
    }


def _last_mix_recommendation(memory_context: dict[str, Any]) -> dict[str, Any]:
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    if not isinstance(memory, dict):
        return {}
    for key in ("last_played_recommendation",):
        item = memory.get(key)
        if isinstance(item, dict) and item.get("kind") == "track_mix" and item.get("uris"):
            return item
    last = memory.get("last_ask_dj")
    actions = last.get("playback_actions") if isinstance(last, dict) else []
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, dict) and action.get("kind") == "track_mix" and action.get("uris"):
                return action
    return {}


def _playlist_name_from_save_request(text: str) -> str:
    match = re.search(r"(?:als|as)\s+(.+)$", str(text or "").strip(), flags=re.IGNORECASE)
    return match.group(1).strip(" ?.!'\"")[:100] if match else ""


def _playlist_links(playlist: Any) -> list[dict[str, str]]:
    if not isinstance(playlist, dict):
        return []
    url = ""
    external = playlist.get("external_urls")
    if isinstance(external, dict):
        url = str(external.get("spotify") or "").strip()
    title = str(playlist.get("title") or playlist.get("name") or "Spotify playlist").strip()
    if not url:
        return []
    return [{"url": url, "title": title, "kind": "link", "source": "spotify"}]


async def _spotify_playlist_search(
    hass: HomeAssistant,
    runtime: Any,
    query: str,
) -> dict[str, Any]:
    try:
        result = await handle_spotify_command(
            hass,
            runtime,
            "search_playlists",
            {"query": query, "limit": 5},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify playlist search unavailable: %s", exc)
        return {}
    return result if isinstance(result, dict) else {}


def _playlist_search_playback_actions(
    hass: HomeAssistant,
    playlists: Any,
) -> list[dict[str, Any]]:
    if not isinstance(playlists, list):
        return []
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for playlist in playlists:
        if not isinstance(playlist, dict):
            continue
        uri = str(playlist.get("uri") or playlist.get("playlist_uri") or "").strip()
        if not uri.startswith("spotify:playlist:") or uri in seen:
            continue
        seen.add(uri)
        image_url = str(
            playlist.get("image_url")
            or playlist.get("album_image_url")
            or playlist.get("entity_picture")
            or playlist.get("thumbnail_url")
            or ""
        ).strip()
        proxy_image = (
            register_image_proxy_url(hass, image_url)
            if image_url.startswith(("http://", "https://"))
            else image_url
        )
        title = str(playlist.get("title") or playlist.get("name") or uri).strip()
        subtitle = str(playlist.get("subtitle") or playlist.get("owner") or "Spotify playlist").strip()
        actions.append(
            {
                key: value
                for key, value in {
                    "id": uri,
                    "title": title,
                    "subtitle": subtitle,
                    "uri": uri,
                    "context_uri": uri,
                    "kind": "playlist",
                    "image_url": proxy_image,
                    "reason": "Spotify playlist-resultaat op basis van je Ask DJ vraag.",
                }.items()
                if value not in ("", None)
            }
        )
        if len(actions) >= 5:
            break
    return actions


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
    lines.append("")
    if genres:
        lines.append("Harde observatie: je genres neigen naar " + _join_examples(genres, limit=4) + ".")
    elif artists:
        lines.append("Harde observatie: ik zie vooral terugkerende artiesten zoals " + _join_examples(artists, limit=4) + ".")
    if albums:
        lines.append("Albums/contexts die eruit springen: " + _join_examples(albums, limit=3) + ".")
    lines.append("")
    vibe = _profile_vibe(genres, energy, mood)
    lines.append(
        "Interpretatie: je profiel lijkt "
        + vibe
        + "; dat is een voorzichtige duiding, geen harde diagnose."
    )
    if mood is not None:
        zone = mood_zone_for_value(mood)
        if zone is not None:
            lines.append(
                f"Je laatste mood/energy waarde in DJ Memory is {mood}/100 "
                f"({zone.name}: {zone.prompt_hint})."
            )
        else:
            lines.append(f"Je laatste mood/energy waarde in DJ Memory is {mood}/100.")
    if examples:
        lines.extend(["", "Concrete voorbeelden:", *[f"- {item}" for item in examples[:6]]])
    if spotify_profile and _profile_limited(spotify_profile):
        lines.append("")
        lines.append("Let op: Spotify geeft geen onbeperkte ruwe luistergeschiedenis, dus dit blijft een profielschets op basis van recente en top-item snapshots.")
    if isinstance(last_ask, dict) and last_ask.get("input"):
        lines.append("")
        lines.append(f"Recente Ask DJ context: je vroeg eerder '{last_ask['input']}'.")
    return "\n".join(line for line in lines if line is not None).strip()


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


def _profile_artist_hint(
    memory_context: dict[str, Any],
    spotify_profile: dict[str, Any],
) -> str:
    """Return a short user-facing hint that DJ Memory/listening profile was used."""
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    if not isinstance(memory, dict):
        memory = {}
    artists = _profile_artists({}, [], spotify_profile)
    tracks = memory.get("recent_tracks") if isinstance(memory.get("recent_tracks"), list) else []
    artists.extend(_profile_artists(memory, tracks, {}))
    artists = _unique_ordered(artists)
    artists = [artist for artist in artists if artist][:3]
    if not artists:
        return ""
    return f"Ik zie in je DJ Memory en Spotify-profiel dat je ook regelmatig naar {_join_human(artists)} luistert."


def _join_human(items: list[str]) -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} en {values[1]}"
    return f"{', '.join(values[:-1])} en {values[-1]}"


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
        zone = mood_zone_for_value(mood)
        if zone is not None and zone.name == "chill":
            return "chill"
        if zone is not None and zone.name in {"energy", "party"}:
            return "energiek"
    text = " ".join(str(track).lower() for track in tracks)
    if any(word in text for word in ("ambient", "acoustic", "chill", "sleep", "rustig")):
        return "chill"
    if any(word in text for word in ("dance", "party", "workout", "hard", "rock")):
        return "intens"
    return "mellow"


def _profile_vibe(genres: list[str], energy: str, mood: int | None) -> str:
    genre_text = " ".join(genres).lower()
    if mood is not None:
        zone = mood_zone_for_value(mood)
        if zone is not None and zone.name == "chill":
            return "rustig, warm en naar ontspanning gericht"
        if zone is not None and zone.name == "groove":
            return "vloeiend, ritmisch en sociaal gericht"
        if zone is not None and zone.name == "energy":
            return "uptempo en naar beweging of momentum gericht"
        if zone is not None and zone.name == "party":
            return "feestelijk, herkenbaar en op maximale energie gericht"
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
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    top_tracks = spotify_profile.get("top_tracks_by_range") if isinstance(spotify_profile, dict) else {}
    if isinstance(top_tracks, dict):
        for range_name in ("short_term", "medium_term", "long_term"):
            items = top_tracks.get(range_name)
            if isinstance(items, list):
                candidates.extend(item for item in items if isinstance(item, dict))
    top_artists = spotify_profile.get("top_artists_by_range") if isinstance(spotify_profile, dict) else {}
    if isinstance(top_artists, dict):
        for range_name in ("short_term", "medium_term", "long_term"):
            items = top_artists.get(range_name)
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
        for key in ("favorite_artists", "favorite_genres", "favorite_playlists"):
            values = memory.get(key)
            if isinstance(values, list):
                candidates.extend(
                    item if isinstance(item, dict) else {"name": str(item), "source": key}
                    for item in values
                    if item
                )
    if playback_context:
        candidates.append(playback_context)
    random.shuffle(candidates)

    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    reason = _recommendation_reason(memory_context)
    for item in candidates:
        uri = str(
            item.get("uri")
            or item.get("current_uri")
            or item.get("context_uri")
            or item.get("playlist_uri")
            or item.get("album_uri")
            or item.get("artist_uri")
            or ""
        ).strip()
        kind = _spotify_uri_kind(uri)
        if kind not in {"track", "album", "artist", "playlist"} or uri in seen:
            continue
        seen.add(uri)
        image_url = str(
            item.get("album_image_url")
            or item.get("image_url")
            or item.get("artist_image_url")
            or item.get("album_art_url")
            or item.get("media_image_url")
            or item.get("entity_picture")
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
            "reason": reason,
        }
        if kind == "track":
            context_uri = str(item.get("context_uri") or "").strip()
            if context_uri:
                action["context_uri"] = context_uri
                action["offset_uri"] = uri
        actions.append({key: value for key, value in action.items() if value not in ("", None)})
        if len(actions) >= limit:
            break
    return actions


def _play_now_action_from_spotify_item(
    hass: HomeAssistant,
    item: dict[str, Any],
) -> dict[str, Any]:
    uri = str(item.get("uri") or "").strip()
    kind = _spotify_uri_kind(uri) or str(item.get("type") or "track").strip().lower()
    image_url = str(
        item.get("album_image_url")
        or item.get("image_url")
        or item.get("thumbnail_url")
        or item.get("media_image_url")
        or ""
    ).strip()
    proxy_image = register_image_proxy_url(hass, image_url) if image_url.startswith(("http://", "https://")) else image_url
    action = {
        "id": uri,
        "title": str(item.get("track_name") or item.get("title") or item.get("name") or uri).strip(),
        "subtitle": str(item.get("artist") or item.get("artist_name") or item.get("album_name") or "").strip(),
        "uri": uri,
        "kind": kind,
        "image_url": proxy_image,
        "reason": "Voor je klaargezet terwijl het huidige nummer doorspeelt.",
    }
    context_uri = str(item.get("context_uri") or "").strip()
    if kind == "track" and context_uri:
        action["context_uri"] = context_uri
        action["offset_uri"] = uri
    return {key: value for key, value in action.items() if value not in ("", None)}


def _recommendation_reason(memory_context: dict[str, Any]) -> str:
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    time_context = memory.get("listening_time_context") if isinstance(memory, dict) else {}
    if isinstance(time_context, dict) and time_context:
        daypart = str(time_context.get("daypart") or "").strip()
        weekend = "weekend" if time_context.get("is_weekend") else "weekdag"
        if daypart:
            return f"Past bij je recente luisterprofiel en je gebruikelijke {daypart} op een {weekend}."
    return "Past bij je recente luisterprofiel."


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
    payload = enrich_payload_with_mood_zone(payload)
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    status = getattr(runtime, "device_status", {}) or {}
    return {
        CONF_DEVICE_ID: payload.get(CONF_DEVICE_ID) or identity.get(CONF_DEVICE_ID) or status.get(CONF_DEVICE_ID),
        CONF_CLIENT_TYPE: payload.get(CONF_CLIENT_TYPE) or identity.get(CONF_CLIENT_TYPE) or status.get(CONF_CLIENT_TYPE),
        CONF_DEVICE_NAME: payload.get(CONF_DEVICE_NAME) or identity.get(CONF_DEVICE_NAME) or status.get(CONF_DEVICE_NAME),
        "memory_key": payload.get("memory_key") or identity.get("memory_key"),
        "mood": payload.get("mood") if payload.get("mood") is not None else payload.get("energy"),
        "mood_zone": payload.get("mood_zone"),
        "mood_zone_prompt": payload.get("mood_zone_prompt"),
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
    smart_home_text = smart_home_context_text(
        memory_context.get("smart_home")
        if isinstance(memory_context.get("smart_home"), list)
        else []
    )
    return (
        "Je bent DJConnect Ask DJ. Beantwoord informatieve muziekvragen zonder "
        "playback te wijzigen. Gebruik alleen meegegeven context en betrouwbare "
        "kennis die je al hebt; verzin geen trivia. Als bronnen beschikbaar zijn, "
        "houd rekening met Spotify metadata, DJ Memory, MusicBrainz, Wikidata, "
        "korte Wikipedia-samenvattingen, Last.fm, Discogs en TheAudioDB. "
        "Gebruik de recente Ask DJ gesprekshistorie. Als het laatste bericht een "
        "korte bevestiging, afwijzing, bedankje, excuus, emotionele reactie of "
        "conversationele follow-up is, reageer natuurlijk op die context. Herhaal "
        "dan niet de vorige lookup of vorige foutmelding en voer geen playbackactie "
        "uit tenzij de gebruiker duidelijk om een nieuwe actie vraagt. Als het "
        "laatste bericht de vorige vraag corrigeert of vernauwt, combineer het met "
        "die vorige vraag voordat je antwoordt. "
        "Geef een kort natuurlijk antwoord voor een chat UI.\n\n"
        f"Vraag: {text}\n"
        f"Mood/energy: {mood_context_text(payload)}\n"
        f"DJ stijl: {payload.get('dj_style') or 'standaard'}\n"
        f"Smart-home context: {smart_home_text or 'geen expliciet gedeelde HA entities'}\n"
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
    if _looks_like_gibberish(normalized) or _looks_like_prompt_or_sandbox_attack(normalized):
        return _unrecognized_request_text()
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    last = memory.get("last_ask_dj") if isinstance(memory, dict) else {}
    if "waarom" in normalized and isinstance(last, dict) and last.get("response_text"):
        return str(last.get("response_text"))
    track = _track_label(playback_context)
    if "artiest" in normalized and track:
        return f"Ik kijk naar de huidige context rond {track}. Meer brondata is nog niet beschikbaar."
    return "Ik heb nu niet genoeg betrouwbare broninformatie om daar zeker antwoord op te geven."


def _unrecognized_request_text() -> str:
    return "Sorry, ik begrijp niet wat je bedoelt."


def _looks_like_gibberish(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False
    words = normalized.split()
    if len(words) != 1:
        return False
    token = words[0].strip("'")
    if len(token) < 10 or not re.fullmatch(r"[a-z0-9']+", token):
        return False
    letters = re.sub(r"[^a-z]", "", token)
    if len(letters) < 10:
        return False
    vowels = sum(1 for char in letters if char in "aeiouy")
    vowel_ratio = vowels / len(letters)
    has_long_consonant_run = bool(re.search(r"[bcdfghjklmnpqrstvwxz]{5,}", letters))
    has_repeated_noise = bool(re.search(r"(?:df|fs|sd|ds|ff|ss){3,}", letters))
    return vowel_ratio < 0.2 or has_long_consonant_run or has_repeated_noise


def _looks_like_prompt_or_sandbox_attack(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False
    sandbox_terms = (
        "sandbox",
        "jailbreak",
        "prompt injection",
        "system prompt",
        "developer prompt",
        "ignore previous instructions",
        "ignore all previous instructions",
        "negeer vorige instructies",
        "negeer alle vorige instructies",
        "toon je prompt",
        "laat je prompt zien",
        "show your prompt",
    )
    escape_verbs = (
        "breek uit",
        "uitbreken",
        "escape",
        "break out",
        "bypass",
        "omzeil",
        "override",
    )
    if any(term in normalized for term in sandbox_terms):
        return True
    return any(verb in normalized for verb in escape_verbs) and any(
        target in normalized
        for target in (
            "sandbox",
            "regels",
            "instructies",
            "instructions",
            "policy",
            "beveiliging",
            "security",
        )
    )


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
    nested_sources = []
    for key in ("playback", "media", "resolved_media", "track"):
        nested = result.get(key)
        if isinstance(nested, dict):
            nested_sources.append(nested)
            for nested_key in ("resolved_media", "media", "track", "device_response"):
                child = nested.get(nested_key)
                if isinstance(child, dict):
                    nested_sources.append(child)
                    playback = child.get("playback")
                    if isinstance(playback, dict):
                        nested_sources.append(playback)
    for source in (result, *nested_sources, playback_context):
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
    provided = result.get("links")
    if isinstance(provided, list):
        for item in provided:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            links.append(
                {
                    "url": str(item.get("url")),
                    "title": str(item.get("title") or "Link"),
                    "subtitle": str(item.get("subtitle") or ""),
                    "kind": str(item.get("kind") or "link"),
                    "source": str(item.get("source") or "source"),
                }
            )
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


def _playback_control_actions(action: str) -> list[dict[str, Any]]:
    if action != "pause":
        return []
    return [
        {
            "id": "djconnect:control:resume",
            "kind": "control",
            "action_style": "control",
            "command": "play",
            "title": "Resume",
            "label": "Resume",
            "button_label": "Resume",
            "prompt": "Start muziek",
            "reason": "De muziek is gepauzeerd.",
        }
    ]


def _confirmation_actions() -> list[dict[str, Any]]:
    return [
        {
            "id": "ask_dj_followup_yes",
            "title": "Ja",
            "kind": "confirmation",
            "action_style": "confirmation",
            "response_value": "yes",
            "command": "ask_dj_followup_response",
        },
        {
            "id": "ask_dj_followup_no",
            "title": "Nee",
            "kind": "confirmation",
            "action_style": "confirmation",
            "response_value": "no",
            "command": "ask_dj_followup_response",
        },
    ]


def _confirmation_actions_from_playback_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    return [
        action
        for action in actions
        if isinstance(action, dict)
        and action.get("kind") == "confirmation"
        and action.get("action_style") == "confirmation"
    ]


async def _store_pending_followup(
    runtime: Any,
    payload: dict[str, Any],
    *,
    question: str,
    proposed_intent: str,
    proposed_action: str,
    proposed_payload: dict[str, Any],
) -> None:
    memory = getattr(runtime, "memory", None)
    storer = getattr(memory, "async_store_pending_followup", None)
    if not callable(storer):
        return
    try:
        await storer(
            runtime,
            {
                "type": "playback_confirmation",
                "question": question,
                "proposed_intent": proposed_intent,
                "proposed_action": proposed_action,
                "proposed_payload": proposed_payload,
            },
            payload,
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect pending Ask DJ follow-up store failed: %s", exc)


def _playback_failed_text(runtime: Any, text: str = "") -> str:
    normalized = _normalize(text)
    if _looks_dutch(normalized):
        return "Ik heb je muziekverzoek begrepen, maar Spotify kon het nu niet starten."
    language_getter = getattr(runtime, "device_language", None)
    language = str(language_getter() or "").lower() if callable(language_getter) else ""
    if language.startswith("en"):
        return "I understood your music request, but Spotify could not start it right now."
    return "Ik heb je muziekverzoek begrepen, maar Spotify kon het nu niet starten."


def _is_help_request(normalized: str) -> bool:
    if normalized in {
        "help",
        "hulp",
        "wat kan je",
        "wat kun je",
        "wat kan ik vragen",
        "wat kun je doen",
        "welke commando's",
        "welke commandos",
        "welke opdrachten",
        "toon commando's",
        "toon commandos",
        "lijst commando's",
        "lijst commandos",
        "commands",
        "show commands",
        "what can you do",
    }:
        return True
    return any(
        phrase in normalized
        for phrase in (
            "welke prompts",
            "prompt opties",
            "promptopties",
            "commando opties",
            "voorbeelden van vragen",
            "voorbeelden wat ik kan vragen",
            "wat kan djconnect",
            "wat kan ask dj",
        )
    )


def _help_text() -> str:
    return "\n".join(
        [
            "Dit kun je aan Ask DJ vragen:",
            "",
            "Muziek starten",
            "- Speel Nirvana",
            "- Speel Metallica, One",
            "- Draai Nothing Else Matters",
            "- Zet een rustige playlist op",
            "- Speel iets voor tijdens het koken",
            "",
            "Play Now keuzes",
            "- Geef me albums van Radiohead",
            "- Welke albums bracht Nirvana uit?",
            "- Geef vergelijkbare artiesten als The xx",
            "- Welke playlists zijn er voor hardlopen?",
            "- Maak een mix op basis van Radiohead, Massive Attack en Bon Iver",
            "",
            "Speakers en playback",
            "- Welke speakers zijn er?",
            "- Wissel van speaker",
            "- Waarop speelt de muziek?",
            "- Pauzeer",
            "- Speel verder",
            "- Volgende nummer",
            "- Vorige nummer",
            "- Harder",
            "- Zachter",
            "- Shuffle aan",
            "- Repeat uit",
            "",
            "DJ uitleg en context",
            "- Wat speelt er nu?",
            "- Waarom koos je dit nummer?",
            "- Vertel iets over deze artiest",
            "- Welk nummer komt hierna?",
            "- Geef een DJ intro voor dit nummer",
            "- Wat voor genre is dit?",
            "",
            "Persoonlijke muzieksmaak",
            "- Analyseer mijn luisterprofiel",
            "- Wat luisterde ik de afgelopen maand?",
            "- Geef persoonlijke muziekaanbevelingen",
            "- Welke artiesten passen bij mijn smaak?",
            "",
            "Follow-ups",
            "- Probeer opnieuw",
            "- Speel af",
            "- Nee, ik bedoel de live versie",
            "- Alleen uit de jaren 90",
            "- Maak hier een playlist van",
            "",
            "Goed om te weten",
            "- Ask DJ start muziek alleen direct bij duidelijke speelopdrachten.",
            "- Bij lijsten, albums, aanbevelingen en speakers krijg je knoppen zoals Play Now of Activeer.",
        ]
    )


def _help_response() -> dict[str, Any]:
    message = _help_text()
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "intent": {"category": "informational", "intent": "help"},
        "images": [],
        "links": [],
        "sources": [],
        "playback_actions": [],
    }


def _looks_dutch(normalized: str) -> bool:
    return any(
        token in normalized
        for token in (
            "speel",
            "draai",
            "zet",
            "maar",
            "muziek",
            "nummer",
            "artiest",
            "playlist",
            "afspeellijst",
            "harder",
            "zachter",
            "volgende",
            "vorige",
        )
    )


def _devices_text(devices: list[dict[str, Any]]) -> str:
    names = [str(device.get("name")) for device in devices if isinstance(device, dict) and device.get("name")]
    if not names:
        return "Ik zie nu geen Spotify speakers."
    return "Dit zijn de momenteel beschikbare speakers:\n\n" + "\n".join(f"- {name}" for name in names)


def _is_output_selection_request(normalized: str) -> bool:
    if "welke speakers" in normalized or "welke apparaten" in normalized:
        return True
    has_output = any(
        term in normalized
        for term in (
            "speaker",
            "speakers",
            "output",
            "uitvoer",
            "geluidsuitvoer",
            "apparaat",
            "spotify connect",
        )
    )
    if not has_output:
        return False
    return any(
        term in normalized
        for term in (
            "wissel",
            "wisselen",
            "verander",
            "veranderen",
            "wijzig",
            "wijzigen",
            "switch",
            "change",
            "zet over",
            "verplaats",
        )
    )


def _output_device_actions(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for device in devices:
        if not isinstance(device, dict):
            continue
        device_id = str(device.get("id") or "").strip()
        name = str(device.get("name") or "").strip()
        if not device_id or not name or device_id in seen:
            continue
        seen.add(device_id)
        device_type = str(device.get("type") or "Spotify Connect").strip()
        is_active = bool(device.get("active") or device.get("is_active"))
        actions.append(
            {
                key: value
                for key, value in {
                    "id": f"set_output:{device_id}",
                    "title": name,
                    "subtitle": "Actieve uitvoer" if is_active else device_type,
                    "label": "Actief" if is_active else "Activeer",
                    "kind": "output",
                    "command": "set_output",
                    "value": device_id,
                    "device_id": device_id,
                    "device_name": name,
                    "active": is_active,
                    "reason": "Spotify Connect uitvoer wijzigen vanuit Ask DJ.",
                }.items()
                if value not in ("", None)
            }
        )
        if len(actions) >= 8:
            break
    return actions


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
