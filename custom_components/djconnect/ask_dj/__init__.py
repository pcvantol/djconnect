"""Ask DJ backend support."""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import random
import re
import secrets
from typing import Any
from urllib.parse import quote, urlsplit

from aiohttp import ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..discovery_artwork import capture_refresh_guard

from ..ai_tools import async_call_ai_tool
from ..const import (
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_MUSIC_BACKEND,
    DEFAULT_TTS_LANGUAGE,
    DOMAIN,
    MUSIC_BACKEND_LATER_MANUAL,
)
from ..announcements import async_apply_announcement_output
from ..dj_response import async_create_dj_audio_url
from ..music_dna import prompt_context_text as prompt_context_text
from ..mood import (
    enrich_payload_with_mood_zone,
    mood_context_text as mood_context_text,
    mood_zone_for_value,
)
from ..music_intent import parse_spoken_music_request, music_command_subject, negated_music_command
from ..pipeline import _assist_context, _speech_from_response, call_conversation_process_with_agent_retry
from ..use_cases import (
    MusicBackendCapabilityError,
    build_playback_action,
    run_music_command,
    run_text_command,
)
from ..track_insight import (
    TrackInsightError,
    is_track_insight_request,
    track_insight_error_response,
)
from ..voice_profiles import voice_profile_for_mood_or_config, voice_profile_style_text_for_payload as voice_profile_style_text_for_payload
from .responses import image_proxy_target as image_proxy_target, register_image_proxy_url
from .read_copy import text as _read_text

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


async def async_send_dj_response_best_effort(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
) -> dict[str, Any]:
    """Create replayable Ask DJ audio without posting to a local ESP device."""
    return {"audio_url_value": await async_create_dj_audio_url(hass, runtime, text)}


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
    confirmed_entry: dict[str, Any] | None = None,
    saved_playback_result: dict[str, Any] | None = None,
    conversation_history_scope: str | None = None,
    ephemeral_conversation: bool = False,
    action_request: tuple[str, Any] | None = None,
) -> dict[str, Any]:
    """Handle a text Ask DJ request and return the client response shape."""
    payload = enrich_payload_with_mood_zone(payload)
    payload = _apply_mood_voice_profile(runtime, payload)
    text = str(payload.get("text") or payload.get("message") or "").strip()
    if not text:
        return _error_response("missing_text", "Ask DJ needs text to answer.")
    if saved_playback_result is not None:
        from ..session_conversation import historical_answer

        return historical_answer(payload, saved_playback_result)
    from .dialogue import current_turn, explicit_quote, model_source, is_refinement, DialogueError
    turn = current_turn.get()
    source = model_source(confirmed_entry)
    if turn is not None:
        await turn.guard()
        turn.source_context = source
    if action_request is None and negated_music_command(text) and not _blocked_music_preference_from_text(text):
        message=_read_text('no_play')
        return {'success':True,'text':message,'dj_text':message,'action':'none',
                'intent':{'category':'informational','intent':'ask_music_info'},
                'images':[],'links':[],'sources':[],'items':[],'playback_actions':[]}
    from .observations import current_artist_question, current_artist_read
    from .album_tracks import album_tracks_question, album_tracks_read
    if action_request is None and album_tracks_question(text):
        return await album_tracks_read(hass, runtime, text, confirmed_entry)
    from .observations import release_question, release_read
    if action_request is None and release_question(text):
        return await release_read(hass,runtime,confirmed_entry)
    if action_request is None and confirmed_entry is not None and current_artist_question(text):
        return await current_artist_read(hass, runtime, confirmed_entry)
    if action_request is not None:
        return await _execute_dialogue_command(hass, runtime, payload, action_request, user_id=user_id)
    if (turn is not None and turn.frame.pending and turn.frame.pending.get("type")=="mood_direction"
            and not turn.fast_control):
        from ..mood_music_steering import direction_response
        direction = await direction_response(hass,runtime,payload,text)
        if direction is not None:
            return direction
    if (turn is not None and turn.frame.pending and turn.frame.pending.get("type")=="playback_confirmation"
            and text.casefold().strip(" .!?") in {"yes", "ja", "oui", "sí", "si", "no", "nee", "nein", "non"}):
        response_value = "no" if text.casefold().strip(" .!?") in {"no", "nee", "nein", "non"} else "yes"
        return await _execute_dialogue_command(hass, runtime, payload,
                                             ("ask_dj_followup_response", {"response_value": response_value}), user_id=user_id)
    if confirmed_entry is not None and explicit_quote(text):
        attribution = confirmed_entry.get("source_attribution") or {}
        return {"success": True, "text": str(confirmed_entry.get("text") or ""),
                "dj_text": str(confirmed_entry.get("text") or ""),
                "sources": [attribution] if isinstance(attribution, dict) else attribution,
                "playback_actions": [], "intent": {"intent": "selected_contribution_quote"}}
    if turn is not None and not turn.resolving_output_request:
        if confirmed_entry is None:
            refined = await _dialogue_album_period_response(hass, payload, text)
            if refined is not None:
                return refined
            listed = await _dialogue_result_list_response(hass, payload, text)
            if listed is not None:
                return listed
        selected = await _dialogue_choice_response(hass, runtime, payload, text)
        if selected is not None:
            return selected
    if current_artist_question(text):
        return await current_artist_read(hass, runtime)
    if payload.get("mood_zone"):
        _LOGGER.debug(
            "DJConnect Ask DJ mood context: mood=%s zone=%s",
            payload.get("mood"),
            payload.get("mood_zone"),
        )

    identity_payload = _identity_payload(runtime, payload)
    memory = None if ephemeral_conversation else getattr(runtime, "memory", None)
    memory_context: dict[str, Any] = {}
    music_dna_key = str(payload.get("music_dna_key") or "").strip() or None
    if memory is not None:
        memory_context = await memory.async_context_for_runtime(
            runtime,
            identity_payload,
            user_id=user_id,
        )
        music_dna_key = memory_context.get("music_dna_key") or music_dna_key
    # The shared short window is operational, permission-qualified and independent of DNA.
    # Durable legacy/Session archive text is never an implicit model-history grant.
    if turn is not None:
        memory_context["server_history"] = turn.frame.local_turns if not turn.reset_topic else []
        memory_context["memory"] = {k: v for k, v in (memory_context.get("memory") or {}).items() if k not in {"last_ask_dj", "pending_followup"}}
        if turn.frame.result_set and not turn.reset_topic:
            memory_context["server_history"] = [*turn.frame.local_turns,
                {"role": "assistant", "playback_actions": turn.frame.result_set["items"], "items": turn.frame.result_set["items"]}]
    request_intent = classify_ask_dj(text)
    complex_music_search = (request_intent.intent == "song_recommendations"
                            and not _current_track_seed_mix_request(text)
                            and len(text.split()) > 8)
    if (is_refinement(text) or (turn is not None and complex_music_search)) and request_intent.category != "action":
        return await _informational_assist_response(hass, runtime, text, payload, memory_context, {}, [])
    if turn is not None and _is_retry_request(_normalize(text)) and turn.frame.retry:
        if turn.frame.retry.get("uncertain"):
            raise DialogueError("action_outcome_uncertain")
        text = turn.frame.retry["text"]
        from .dialogue import request_effect_grants
        turn.effect_grants = request_effect_grants(text, classify_ask_dj(text))
    conversation_turn = classify_conversation_turn(text, memory_context)
    if source or (_current_track_version_request(text) and not _has_clear_playback_action(_normalize(text))):
        conversation_turn = AskDjConversationTurn("request", text)
    response = await _async_conversation_turn_response(
        hass, runtime, payload, conversation_turn, memory, identity_payload,
        user_id, text, music_dna_key,
    )
    if response is not None:
        return response

    effective_text = _contextualize_play_request_from_recent_actions(
        conversation_turn.text,
        memory_context,
    )
    blocked_preference = _blocked_music_preference_from_text(effective_text)
    response = await _async_blocked_preference_response(
        hass, runtime, blocked_preference, memory, identity_payload,
        user_id, text, music_dna_key,
    )
    if response is not None:
        return response
    classification = classify_ask_dj(effective_text)
    response = _help_ask_dj_response(hass, runtime, payload, classification, music_dna_key)
    if response is not None:
        return response
    from .dialogue import references_topic
    current_reference = (references_topic(effective_text)
        or _is_current_artist_album_question(effective_text) or _is_current_artist_info_question(effective_text)
        or bool(_current_track_version_request(effective_text))
        or bool(_current_track_seed_mix_request(effective_text))
        or ("nog meer leuk" in _normalize(effective_text) and "artiest" in _normalize(effective_text))
        or bool(re.search(r"\b(?:nu|now|current|currently|huidige|gerade|aktuell|maintenant|ahora)\b", effective_text.casefold())))
    private_reads = {"previous_track_information", "session_forecast_information", "next_track_info", "list_outputs", "playback_control"}
    playback_context = (await _playback_context(hass, runtime)
        if classification.intent not in private_reads and (classification.intent != "ask_music_info" or classification.category in {"action", "hybrid"} or current_reference)
        else {})
    output_devices = await _output_devices(hass, runtime, classification)
    effective_text, classification, response = await _async_special_ask_dj_response(
        hass, runtime, effective_text, classification, playback_context, music_dna_key,
    )
    if response is not None:
        return response

    if _is_playback_mode_status_question(_normalize(effective_text)):
        classification = AskDjIntent("informational", "playback_mode_status", "status")

    try:
        if classification.category == "action":
            result = await _handle_action(
                hass,
                runtime,
                effective_text,
                classification,
                identity_payload,
                user_id=user_id,
            )
        elif classification.intent == "dj_announcement":
            result = _dj_announcement_response(playback_context)
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
        from ..session_conversation import SessionConversationError
        if isinstance(exc, (DialogueError, SessionConversationError)):
            raise
        _LOGGER.warning("DJConnect Ask DJ failed: %s", type(exc).__name__)
        return _error_response(
            "ask_dj_unavailable",
            "Ask DJ is nu niet bereikbaar.",
            music_dna_key=music_dna_key,
        )

    if turn is not None and turn.interpreted_context_research:
        # The admitted read plan supersedes an earlier keyword classification.
        # Do not attach a different current artist/album to the researched topic.
        classification = AskDjIntent("informational", "ask_music_info", "none")
        playback_context = {}
    response = _normalize_ask_dj_response(
        hass,
        runtime,
        result,
        classification,
        music_dna_key=music_dna_key,
        playback_context=playback_context,
    )

    return await _async_finalize_ask_dj_response(
        hass, runtime, response, classification, payload, memory, identity_payload,
        user_id, effective_text, playback_context,
    )


async def _async_conversation_turn_response(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    turn: AskDjConversationTurn,
    memory: Any,
    identity_payload: dict[str, Any],
    user_id: str | None,
    text: str,
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Return the response for a conversational turn, when applicable."""
    if turn.kind not in {"conversational_followup", "clarification_needed"}:
        return None
    classification = AskDjIntent("informational", turn.kind, "none")
    response = _normalize_ask_dj_response(
        hass, runtime, _handle_conversational_followup(turn), classification,
        music_dna_key=music_dna_key, playback_context={},
    )
    await _async_update_ask_dj_memory(
        memory, runtime, text, response, {}, identity_payload, user_id, include_items=True,
    )
    await _async_announce_ask_dj_response(hass, runtime, response, payload, classification)
    response.pop("playback", None)
    return response


async def _async_blocked_preference_response(
    hass: HomeAssistant,
    runtime: Any,
    blocked_preference: str | None,
    memory: Any,
    identity_payload: dict[str, Any],
    user_id: str | None,
    text: str,
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Record and answer an explicit music-preference exclusion."""
    if not blocked_preference:
        return None
    classification = AskDjIntent("informational", "blocked_music_preference", "none")
    result = await _record_blocked_music_preference_response(
        runtime, blocked_preference, identity_payload, user_id=user_id,
    )
    response = _normalize_ask_dj_response(
        hass, runtime, result, classification, music_dna_key=music_dna_key, playback_context={},
    )
    await _async_update_ask_dj_memory(
        memory, runtime, text, response, {}, identity_payload, user_id, include_items=True,
    )
    response.pop("playback", None)
    return response


def _help_ask_dj_response(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    classification: AskDjIntent,
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Return help before gathering playback state."""
    if classification.intent != "help":
        return None
    from .example_catalogue import help_context
    response = _normalize_ask_dj_response(
        hass, runtime, _help_response(_response_language(runtime, payload), help_context(hass, runtime)), classification,
        music_dna_key=music_dna_key, playback_context={},
    )
    response.pop("playback", None)
    return response


async def _async_special_ask_dj_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    classification: AskDjIntent,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> tuple[str, AskDjIntent, dict[str, Any] | None]:
    """Handle specialised requests before the general intent handlers."""
    response = await _async_music_lookup_response(
        hass, runtime, text, playback_context, music_dna_key,
    )
    if response is not None:
        return text, classification, response
    return await _async_playback_special_response(
        hass, runtime, text, classification, playback_context, music_dna_key,
    )


async def _async_music_lookup_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Resolve direct artist and track lookup requests."""
    request = _track_owner_question(text)
    if request:
        result = await _track_owner_response(hass, runtime, request)
        return _special_ask_dj_response(
            hass, runtime, result, AskDjIntent("informational", "track_artist_album_lookup", "none"),
            music_dna_key, playback_context,
        )
    request = _album_containing_track_request(text)
    if request:
        result = await _play_album_containing_track_response(hass, runtime, request)
        return _special_ask_dj_response(
            hass, runtime, result,
            AskDjIntent("hybrid", "play_album_containing_track", "play_music", play=True),
            music_dna_key, playback_context,
        )
    return await _async_artist_request_response(hass, runtime, text, playback_context, music_dna_key)


async def _async_artist_request_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Resolve artist-specific shortcut requests."""
    request = _artist_fun_queue_request(text)
    if request:
        result = await _artist_fun_queue_response(hass, runtime, request)
        intent = AskDjIntent("hybrid", "artist_fun_queue", "play_music", play=True)
    else:
        request = _artist_recommendation_request(text)
        if request:
            result = await _artist_seed_recommendations_response(hass, runtime, request)
            intent = AskDjIntent("informational", "artist_seed_recommendations", "none")
        else:
            return await _async_artist_item_response(
                hass, runtime, text, playback_context, music_dna_key,
            )
    return _special_ask_dj_response(hass, runtime, result, intent, music_dna_key, playback_context)


async def _async_artist_item_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Return the requested artist items or albums."""
    request = _play_something_from_artist_request(text)
    if request:
        result = await _artist_album_playlist_options_response(hass, runtime, request)
    else:
        request = _artist_item_list_request(text)
        if not request:
            return None
        result = await _artist_item_list_response(hass, runtime, request)
    return _special_ask_dj_response(
        hass, runtime, result, AskDjIntent("informational", "artist_item_list", "none"),
        music_dna_key, playback_context,
    )


async def _async_playback_special_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    classification: AskDjIntent,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> tuple[str, AskDjIntent, dict[str, Any] | None]:
    """Resolve playback shortcuts and return any rewritten request text."""
    response = await _async_current_track_response(
        hass, runtime, text, playback_context, music_dna_key,
    )
    if response is not None:
        return text, classification, response
    text, classification, response = _slang_track_reference_response(
        hass, runtime, text, classification, playback_context, music_dna_key,
    )
    if response is not None:
        return text, classification, response
    response = await _async_deferred_or_choice_response(
        hass, runtime, text, classification, playback_context, music_dna_key,
    )
    return text, classification, response


async def _async_current_track_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Handle shortcuts based on the current album or track."""
    if _is_current_album_play_request(text):
        result = await _play_current_album_response(hass, runtime, playback_context)
        intent = AskDjIntent("hybrid", "play_current_album", "play_music", play=True)
    else:
        request = _current_track_seed_mix_request(text)
        if request:
            result = await _current_track_seed_mix_response(hass, runtime, playback_context, request)
            intent = (AskDjIntent("hybrid", "current_track_seed_mix", "play_music", play=True)
                if request == "play" else AskDjIntent("informational", "current_track_seed_mix", "none"))
        else:
            return await _async_track_version_response(
                hass, runtime, text, playback_context, music_dna_key,
            )
    return _special_ask_dj_response(hass, runtime, result, intent, music_dna_key, playback_context)


async def _async_track_version_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Search alternate versions of a requested or current track."""
    request = _track_versions_search_request(text)
    if request:
        result = await _track_versions_search_response(hass, runtime, request)
        intent = AskDjIntent("informational", "track_versions_search", "none")
    else:
        request = _current_track_version_request(text)
        if not request:
            return None
        result = await _current_track_version_response(hass, runtime, playback_context, request)
        intent = AskDjIntent("informational", "current_track_versions", "none")
    return _special_ask_dj_response(hass, runtime, result, intent, music_dna_key, playback_context)


def _slang_track_reference_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    classification: AskDjIntent,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> tuple[str, AskDjIntent, dict[str, Any] | None]:
    """Expand a slang reference to the current track, or request clarification."""
    if classification.category != "hybrid" or not _is_slang_track_reference(text):
        return text, classification, None
    track_label = _track_label(playback_context)
    if track_label:
        return f"speel {track_label}", classification, None
    intent = AskDjIntent("informational", "clarification_needed", "none")
    result = {"success": True, "text": "Welke track bedoel je?", "dj_text": "Welke track bedoel je?", "action": "none"}
    return text, intent, _special_ask_dj_response(
        hass, runtime, result, intent, music_dna_key, playback_context,
    )


async def _async_deferred_or_choice_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    classification: AskDjIntent,
    playback_context: dict[str, Any],
    music_dna_key: str | None,
) -> dict[str, Any] | None:
    """Offer deferred playback or track choices before general playback."""
    if _should_defer_playback(text, classification, playback_context):
        result = await _deferred_playback_request_response(hass, runtime, text)
        return _special_ask_dj_response(
            hass, runtime, result, classification, music_dna_key, playback_context,
        )
    if classification.category != "hybrid" or classification.intent == "dj_announcement":
        return None
    query = _bare_track_title_play_query(text)
    if not query:
        return None
    result = await _track_title_choice_response(hass, runtime, query)
    if not result.get("playback_actions"):
        return None
    return _special_ask_dj_response(
        hass, runtime, result, AskDjIntent("informational", "track_title_choices", "none"),
        music_dna_key, playback_context,
    )


def _should_defer_playback(
    text: str,
    classification: AskDjIntent,
    playback_context: dict[str, Any],
) -> bool:
    """Return whether a hybrid request needs a choice before playback."""
    normalized_text = _normalize(text)
    return (
        classification.category == "hybrid"
        and _is_deferred_playback_request(text)
        and (
            not _execution_request(text)
            or _playback_is_active(playback_context)
            or _is_fuzzy_music_search_request(normalized_text)
            or _genre_options_request(text)
            or _is_something_from_artist_request(normalized_text)
        )
    )


def _special_ask_dj_response(
    hass: HomeAssistant,
    runtime: Any,
    result: dict[str, Any],
    classification: AskDjIntent,
    music_dna_key: str | None,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    """Normalize an early response and hide its internal playback context."""
    response = _normalize_ask_dj_response(
        hass, runtime, result, classification,
        music_dna_key=music_dna_key, playback_context=playback_context,
    )
    response.pop("playback", None)
    return response


async def _async_finalize_ask_dj_response(
    hass: HomeAssistant,
    runtime: Any,
    response: dict[str, Any],
    classification: AskDjIntent,
    payload: dict[str, Any],
    memory: Any,
    identity_payload: dict[str, Any],
    user_id: str | None,
    text: str,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    """Persist, announce and return a completed general Ask DJ response."""
    await _async_update_ask_dj_memory(
        memory, runtime, text, response, playback_context, identity_payload, user_id,
    )
    await _async_announce_ask_dj_response(hass, runtime, response, payload, classification)
    response.pop("playback", None)
    return response


async def _async_update_ask_dj_memory(
    memory: Any,
    runtime: Any,
    text: str,
    response: dict[str, Any],
    playback_context: dict[str, Any],
    identity_payload: dict[str, Any],
    user_id: str | None,
    *,
    include_items: bool = False,
) -> None:
    """Persist the normalized Ask DJ result when memory is available."""
    from .dialogue import current_turn
    if current_turn.get() is not None:
        return  # One operational dialogue owner, not a second last-Ask-DJ stack.
    if memory is None:
        return
    result = {
        "intent": response.get("intent") or {},
        "dj_text": response.get("dj_text") or response.get("text"),
        "playback": response.get("playback") or playback_context,
        "playback_actions": response.get("playback_actions") or [],
    }
    if include_items:
        result["items"] = []
    await memory.async_update_last_ask_dj(
        runtime, input_text=text, result=result, payload=identity_payload, user_id=user_id,
    )


async def _async_announce_ask_dj_response(
    hass: HomeAssistant,
    runtime: Any,
    response: dict[str, Any],
    payload: dict[str, Any],
    classification: AskDjIntent,
) -> None:
    """Common Profile dialogue presents accepted references after semantic commit."""
    from .dialogue import current_turn
    turn = current_turn.get()
    if turn is not None:
        # All common general/Session early and model replies converge in service.
        # Never synthesize or activate a speaker before the accepted turn exists.
        # Manual/autoplay preparation consumes that reference, not this request.
        response["audio_delivery"] = {"mode": "accepted_reference", "state": "deferred"}
        return
    await async_apply_announcement_output(
        hass, runtime, response, payload=payload,
        generate_audio=(
            bool(response.get("dj_text"))
            and _response_allows_audio(response)
            and _should_generate_audio_response(payload, classification)
        ),
        audio_url_factory=async_send_dj_response_best_effort,
    )


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
    music_dna_key = str(payload.get("music_dna_key") or "").strip() or None
    if memory is not None:
        memory_context = await memory.async_context_for_runtime(
            runtime,
            identity_payload,
            user_id=user_id,
        )
        music_dna_key = memory_context.get("music_dna_key") or music_dna_key
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
            "music_dna_key": music_dna_key,
            "playback_actions": [],
        }
    listening_profile = await _listening_profile_context(
        hass,
        runtime,
        payload,
        memory_context,
    )
    actions = _recommendation_playback_actions(
        hass,
        runtime,
        memory_context,
        playback_context,
        listening_profile,
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
        "music_dna_key": music_dna_key,
        "playback_actions": selected_actions,
        "sources": _profile_sources(memory_context, listening_profile),
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
    if classification.action in {
        "volume_delta",
        "set_shuffle",
        "set_repeat",
        "save_current_track",
        "set_current_track_favorite",
    } or classification.intent == "playback_mode_status":
        return False
    input_type = str(payload.get("input_type") or "").strip().lower()
    if input_type in {"voice", "ptt", "audio"}:
        return True
    if classification.intent in {"current_track_info", "current_track_reference"}:
        return True
    return classification.category in {"action", "hybrid"}


def _response_allows_audio(response: dict[str, Any]) -> bool:
    return str(response.get("error") or "").strip() != "playback_failed"


def _attach_audio_response(response: dict[str, Any], audio_url: str) -> None:
    """Attach replayable TTS audio to both response and assistant message."""
    response["audio_url"] = audio_url
    audio_type = _audio_type_from_url(audio_url)
    if audio_type:
        response["audio_type"] = audio_type
    assistant = response.get("assistant_message")
    if isinstance(assistant, dict):
        assistant["audio_url"] = audio_url
        if audio_type:
            assistant["audio_type"] = audio_type


def _audio_type_from_url(audio_url: str | None) -> str | None:
    if not audio_url:
        return None
    lowered = str(audio_url).lower().split("?", 1)[0]
    if lowered.endswith(".wav"):
        return "wav"
    if lowered.endswith(".mp3"):
        return "mp3"
    return None


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


def _is_current_playing_question(text: str) -> bool:
    normalized = _normalize(text).strip(" ?.!'")
    return normalized in {
        "wat speelt er",
        "wat speelt er nu",
        "wat speelt nu",
        "wat draait er",
        "wat draait er nu",
        "wat draai je",
        "hoe heet dit nummer",
        "welk liedje is dit",
        "welk nummer speelt er",
        "welk nummer speelt nu",
        "welk nummer speelt er nu",
        "welk nummer draait er nu",
        "welke track speelt er",
        "welke track speelt nu",
        "welke track hoor ik",
        "wat is die beuker",
        "what is playing",
        "what's playing",
        "whats playing",
        "what song is playing",
        "what track is playing",
        "current song",
        "current track",
        "what is playing now", "was läuft gerade", "qu’est-ce qui passe maintenant",
        "qu'est-ce qui passe maintenant", "¿qué está sonando ahora", "qué está sonando ahora",
    }


def _is_current_track_album_question(text: str) -> bool:
    normalized = _normalize(text)
    if "album" not in normalized:
        return False
    if any(
        phrase in normalized
        for phrase in (
            "op welk album",
            "welk album werd dit",
            "welk album is dit",
            "van welk album",
            "welk album staat dit",
            "on which album",
            "what album was this",
            "what album is this",
            "which album is this",
            "which album was this",
        )
    ):
        return True
    return bool(
        re.search(
            r"\b(?:dit|deze|this)\s+(?:nummer|track|song)\b.*\balbum\b",
            normalized,
        )
    )


def _is_current_album_play_request(text: str) -> bool:
    normalized = _normalize(text)
    return normalized in {
        "speel album",
        "speel het album",
        "speel dit album",
        "speel dat album",
        "draai album",
        "draai het album",
        "draai dit album",
        "zet album op",
        "zet het album op",
        "play album",
        "play the album",
        "play this album",
        "play that album",
    }


def _current_track_version_request(text: str) -> str:
    normalized = _normalize(text)
    if any(term in normalized for term in ("remix", "remixes", "geremixt", "remixed")):
        variant = "remix"
    elif any(term in normalized for term in ("akoestisch", "akoestische", "acoustic", "unplugged")):
        variant = "acoustic"
    elif any(term in normalized for term in ("live versie", "live version", "live uitvoering", "live opname")):
        variant = "live"
    else:
        return ""
    # A variant adjective is not a reference to current playback. Open searches
    # and refinements retain their own subject instead of borrowing the player.
    current = any(term in normalized for term in (
        "dit nummer", "deze track", "dit liedje", "huidige nummer", "daarvan",
        "this song", "this track", "current track", "of it", "of that",
    ))
    implicit_current = bool(re.fullmatch(
        r"(?:heb je|is er|do you have|find|show)\s+(?:een |a |the )?"
        r"(?:live|akoestische?|acoustic|unplugged|remixes?)(?:\s+(?:versie|version|opname|uitvoering))?[?.!]*",
        normalized,
    ))
    implicit_current = implicit_current or bool(re.fullmatch(
        r"(?:nee,?\s+)?ik bedoel\s+(?:de |een )?(?:live|akoestische?|acoustic|remix)\s+(?:versie|opname|uitvoering)[?.!]*",
        normalized,
    ))
    if not current and not implicit_current:
        return ""
    if any(
        term in normalized
        for term in (
            "heb je",
            "zoek",
            "vind",
            "speel",
            "draai",
            "zet",
            "is er",
            "do you have",
            "find",
            "play",
            "show",
            "ik bedoel",
        )
    ):
        return variant
    return ""


def _album_containing_track_request(text: str) -> dict[str, str]:
    value = str(text or "").strip()
    patterns = (
        r"^\s*(?:speel|start|zet|draai)\s+(?:het\s+)?album\s+(?:met|waar(?:op|in)\s+staat)\s+(?:het\s+)?(?:nummer|liedje|track)\s+(.+?)\s+van\s+(.+?)\s*(?:op|af|aan)?\s*$",
        r"^\s*(?:speel|start|zet|draai)\s+(?:de\s+)?plaat\s+(?:met|waar(?:op|in)\s+staat)\s+(?:het\s+)?(?:nummer|liedje|track)\s+(.+?)\s+van\s+(.+?)\s*(?:op|af|aan)?\s*$",
        r"^\s*(?:play|start|put\s+on)\s+(?:the\s+)?album\s+(?:with|containing|that\s+has)\s+(?:the\s+)?(?:song|track)\s+(.+?)\s+by\s+(.+?)\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        track = _clean_album_track_request_part(match.group(1))
        artist = _clean_album_track_request_part(match.group(2))
        if track and artist:
            return {"track": track, "artist": artist}
    return {}


def _track_owner_question(text: str) -> str:
    value = str(text or "").strip()
    patterns = (
        r"^\s*van\s+wie\s+is\s+(?:ook\s+al\s+weer\s+|ook\s+alweer\s+|eigenlijk\s+)?(?:het\s+)?(?:nummer|liedje|track|song)\s+(.+?)\s*\??\s*$",
        r"^\s*wie\s+(?:maakte|zong|speelde)\s+(?:ook\s+al\s+weer\s+|ook\s+alweer\s+)?(?:het\s+)?(?:nummer|liedje|track|song)\s+(.+?)\s*\??\s*$",
        r"^\s*who\s+(?:made|sang|plays|played)\s+(?:the\s+)?(?:song|track)\s+(.+?)\s*\??\s*$",
        r"^\s*who\s+is\s+(?:the\s+)?(?:song|track)\s+(.+?)\s+by\s*\??\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            return _clean_album_track_request_part(match.group(1))
    return ""


def _clean_album_track_request_part(value: Any) -> str:
    return re.sub(
        r"\s+(?:op|af|aan|please|graag|nu)\s*$",
        "",
        str(value or "").strip(" ?.!'\""),
        flags=re.IGNORECASE,
    ).strip()


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
    if _track_owner_question(text):
        return AskDjConversationTurn("informational_intent", text)
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


def _blocked_music_preference_from_text(text: str) -> dict[str, str]:
    value = str(text or "").strip()
    patterns = (
        r"^\s*ik\s+wil\s+(?:nooit\s+meer|niet\s+meer)\s+(.+?)\s+(?:horen|luisteren|afspelen|gespeeld\s+krijgen)\s*$",
        r"^\s*ik\s+wil\s+(?:nooit\s+meer|niet\s+meer)\s+(.+?)\s*$",
        r"^\s*(?:draai|speel|zet)\s+(?:nooit\s+meer|niet\s+meer)\s+(.+?)\s*$",
        r"^\s*(?:nooit\s+meer|niet\s+meer)\s+(.+?)\s+(?:horen|luisteren|afspelen)\s*$",
        r"^\s*i\s+(?:never|do\s+not|don't)\s+want\s+to\s+hear\s+(.+?)\s*$",
        r"^\s*(?:never|do\s+not|don't)\s+play\s+(.+?)\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        name = _clean_blocked_music_name(match.group(1))
        if name:
            return {"kind": "artist", "name": name, "reason": "user_never_wants_to_hear"}
    return {}


def _clean_blocked_music_name(value: Any) -> str:
    return re.sub(
        r"\s+(?:meer|again|anymore|please|graag|nu)\s*$",
        "",
        str(value or "").strip(" ?.!'\""),
        flags=re.IGNORECASE,
    ).strip()


async def _record_blocked_music_preference_response(
    runtime: Any,
    preference: dict[str, str],
    payload: dict[str, Any],
    *,
    user_id: str | None,
) -> dict[str, Any]:
    name = str(preference.get("name") or "").strip()
    memory = getattr(runtime, "memory", None)
    recorder = getattr(memory, "async_record_blocked_music_preference", None)
    if callable(recorder):
        await recorder(runtime, preference, payload, user_id=user_id)
    message = f"Ik zal er rekening mee houden vanaf nu: ik zet {name} niet meer voor je op."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "links": [],
        "items": [],
        "playback_actions": [],
        "confirmation_actions": [],
        "sources": [{"source": "djconnect_music_dna", "title": "Music DNA", "kind": "source"}],
        "intent": {"category": "informational", "intent": "blocked_music_preference"},
    }


def _contextualize_play_request_from_recent_actions(
    text: str,
    memory_context: dict[str, Any],
) -> str:
    normalized = _normalize(text)
    if not (
        _is_deferred_playback_request(normalized)
        or re.search(r"\b(speel|draai|zet)\b", normalized)
    ):
        return text
    parsed = parse_spoken_music_request(text)
    query = str(parsed.get("query") or "").strip()
    if not query:
        query = _play_request_title_candidate(text)
    if not query or len(_normalize(query).split()) > 8:
        return text
    action = _recent_playback_action_for_title(memory_context, query)
    if not action:
        return text
    title = str(action.get("title") or query).strip()
    artist = str(action.get("subtitle") or action.get("artist") or action.get("artist_name") or "").strip()
    if not title or not artist:
        return text
    return f"speel {title} {artist}"


def _play_request_title_candidate(text: str) -> str:
    value = str(text or "").strip()
    patterns = (
        r"^\s*ik\s+wil\s+(.+?)\s+(?:horen|luisteren|afspelen)\s*$",
        r"^\s*(?:speel|draai|zet)\s+(.+?)(?:\s+(?:op|af|aan|please|graag|nu))?\s*$",
        r"^\s*play\s+(.+?)\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            return _clean_album_track_request_part(match.group(1))
    return ""


def _recent_playback_action_for_title(
    memory_context: dict[str, Any],
    title: str,
) -> dict[str, Any]:
    wanted = _normalize(title)
    if not wanted:
        return {}
    for action in _recent_playback_actions(memory_context):
        if not isinstance(action, dict) or str(action.get("kind") or "") != "track":
            continue
        action_title = _normalize(str(action.get("title") or ""))
        if not action_title:
            continue
        if action_title == wanted or action_title in wanted or wanted in action_title:
            return action
    return {}


def _recent_playback_actions(memory_context: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    history = memory_context.get("server_history") if isinstance(memory_context, dict) else []
    if isinstance(history, list):
        for item in reversed(history[-8:]):
            if not isinstance(item, dict):
                continue
            item_actions = item.get("playback_actions")
            if isinstance(item_actions, list):
                actions.extend(action for action in item_actions if isinstance(action, dict))
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    last = memory.get("last_ask_dj") if isinstance(memory, dict) else {}
    item_actions = last.get("playback_actions") if isinstance(last, dict) else None
    if isinstance(item_actions, list):
        actions.extend(action for action in item_actions if isinstance(action, dict))
    return actions


def _simple_control_intent(normalized: str) -> AskDjIntent | None:
    value=normalized.strip(" .!?")
    controls={
        "pause":"pause","pauze":"pause","stop":"pause","pausa":"pause","pausar":"pause",
        "arrête la musique":"pause","pause die musik":"pause","mets la musique en pause":"pause",
        "next":"next","next track":"next","volgende":"next","nächstes lied":"next","suivant":"next","siguiente":"next",
        "previous":"previous","vorige":"previous","vorheriges lied":"previous","précédent":"previous","anterior":"previous",
    }
    if value in controls:
        return AskDjIntent("action","playback_control",controls[value])
    down={"turn volume down","turn the volume down","lower the volume","volume down","volume omlaag","zet zachter","zachter", "mach leiser", "lautstärke verringern", "baisse le volume", "baja el volumen"}
    up={"turn volume up","turn the volume up","raise the volume","volume up","volume omhoog","zet harder","harder", "mach lauter", "lautstärke erhöhen", "augmente le volume", "sube el volumen"}
    if value in down or value in up:
        return AskDjIntent("action","playback_control","volume_delta",-10 if value in down else 10)
    return None


def _has_clear_playback_action(normalized: str) -> bool:
    if _nonexecuting_speech_act(normalized):
        return False
    from ..music_intent import listening_request_target
    if listening_request_target(normalized):
        return True
    if _simple_control_intent(normalized) is not None:
        return True
    if _is_playback_mode_status_question(normalized):
        return False
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
    if _nonexecuting_speech_act(normalized):
        # A new question is not a track selection requested by older dialogue.
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
    nonexecuting = _nonexecuting_speech_act(normalized)
    from .observations import forecast_question, previous_question, current_artist_question
    from .observations import release_question
    from .album_tracks import album_tracks_question
    if album_tracks_question(normalized):
        return AskDjIntent("informational", "album_tracks_information")
    from .dialogue import affirmed_play_reference
    if affirmed_play_reference(normalized):
        return AskDjIntent("hybrid", "play_music", "play_music", play=True)
    if release_question(normalized):
        return AskDjIntent("informational", "current_release_information")
    if current_artist_question(normalized):
        return AskDjIntent("informational", "current_artist_information")
    if forecast_question(normalized) and not _execution_request(normalized):
        return AskDjIntent("informational", "session_forecast_information")
    if previous_question(normalized):
        return AskDjIntent("informational", "previous_track_information")
    if (seed_request := _current_track_seed_mix_request(normalized)) in {"queue", "play"}:
        if seed_request == "play" and _execution_request(normalized):
            return AskDjIntent("hybrid", "current_track_seed_mix", "play_music", play=True)
        return AskDjIntent("informational", "current_track_seed_mix", "none")
    if control := _simple_control_intent(normalized):
        return control
    favorite_target = _current_track_favorite_target(normalized)
    if favorite_target is not None and not nonexecuting:
        return AskDjIntent("action", "playback_control", "set_current_track_favorite", favorite_target)
    from ..music_intent import listening_request_target
    if not nonexecuting and listening_request_target(text):
        return AskDjIntent("hybrid", "play_music", "play_music", play=True)
    for predicate, intent in _ASK_DJ_INTENT_RULES:
        if predicate(normalized, text):
            resolved = intent(normalized) if callable(intent) else intent
            if (resolved.category in {"action", "hybrid"} and resolved.action != "announce"
                and (nonexecuting or not _execution_request(normalized))):
                if resolved.intent == "play_music" and _is_deferred_playback_request(normalized) and (
                    not nonexecuting or _is_fuzzy_music_search_request(normalized)
                ):
                    # Catalog choices are not an execution grant.
                    return AskDjIntent("hybrid", "play_music", "play_music", play=False)
                return AskDjIntent("informational", "ask_music_info")
            return resolved
    return AskDjIntent("informational", "ask_music_info")


def _nonexecuting_speech_act(text: str) -> bool:
    """Questions, quotations, negation and hypotheses are not execution grants.

    This lens qualifies existing intents; it does not answer music questions.
    Polite imperative requests (can you pause / kun je pauzeren) remain requests.
    """
    value = text.casefold().strip().lstrip("¿¡")
    if negated_music_command(text):
        return True
    if value.startswith(("\"", "'", "“", "‘")):
        return True
    if re.match(r"^(?:wat|welk\w*|wie|waar\w*|wanneer|hoe|what|which|who|why|when|where|how|was|welch\w*|wer|warum|wieso|wann|wo|wie|quoi|quel\w*|qui|pourquoi|quand|comment|qu[eé]|cu[aá]l\w*|qui[eé]n|por qu[eé]|cu[aá]ndo|d[oó]nde|c[oó]mo)\b", value):
        return True
    if re.match(r"^(?:if|suppose|imagine|als|stel|wenn|falls|si|disons|explain|leg uit|erkl[aä]r\w*|explique\w*|explica\w*|citeer|quote|zitier\w*|citer|cita)\b", value):
        return True
    if re.match(r"^(?:speel|draai|zet|play|put on|start(?:e)?|spiel(?:e)?|joue\w*|mets|reprodu\w*|pon)\b.+\s(?:niet|nooit|not|never|nicht|pas|no|nunca|jamais)\s*[.!?]*$", value):
        return True
    return bool(re.match(r"^(?:(?:please|alsjeblieft|bitte|s'il te plaît|por favor)\s+)?(?:do not|don't|never|niet|geen|no|ne\s+\w+\s+pas|nicht|kein\w*)\b", value)
                or re.search(r"\b(?:speel|draai|zet|play|put on|start(?:e)?|pause|skip|joue\w*|mets|pon|reprodu\w*|spiel\w*)\s+(?:(?:dit|dat|deze|die|het|this|that|it|das|le|la|el|af)\s+)*(?:niet|geen|not|never|nicht|keine?|pas)\b", value))


def _execution_request(text: str) -> bool:
    if _nonexecuting_speech_act(text):
        return False
    from .dialogue import affirmed_play_reference
    if affirmed_play_reference(text):
        return True
    from ..music_intent import listening_request_target
    if listening_request_target(text):
        return True
    value = text.casefold().strip(" .!?")
    value = re.sub(r"^(?:ok(?:ay)?|goed|alright|bon|vale|bien|gut),?\s+", "", value)
    if _simple_control_intent(value) is not None:
        return True
    value = re.sub(r"^(?:please|alsjeblieft|bitte|por favor|s'il te plaît)\s+", "", value)
    value = re.sub(r"^(?:can|could|would) you\s+|^(?:kun|wil|zou) je\s+|^(?:kannst|könntest) du\s+|^(?:peux|pourrais)-tu\s+|^(?:puedes|podrías)\s+", "", value)
    if _nonexecuting_speech_act(value):
        return False
    return bool(re.match(r"^(?:speel|draai|zet|start(?:e)?|hervat|pauzeer|stop|volgende|vorige|harder|zachter|shuffle|repeat|herhaal|skip|play|resume|pause|next|previous|put on|turn|set|save|sla|bewaar|verwijder|like|unlike|voeg|queue|enqueue|spiel\w*|mach|schalte|pausier\w*|joue\w*|mets|arrête|reprends|reprodu\w*|pon|pausa|sube|baja)\b", value)
                or value in {"ik ga slapen", "ga slapen", "i'm going to sleep", "i am going to sleep"})


_ASK_DJ_INTENT_RULES = (
    (lambda value, _: _is_help_request(value), AskDjIntent("informational", "help", "none")),
    (lambda value, _: _is_conversational_followup_request(value), AskDjIntent("informational", "conversational_followup", "none")),
    (lambda value, _: _is_current_playing_question(value), AskDjIntent("informational", "current_track_reference", "none")),
    (lambda value, _: _is_retry_request(value), AskDjIntent("informational", "retry_previous_request", "retry")),
    (lambda value, _: _is_recently_played_history_request(value), AskDjIntent("informational", "recently_played_history", "recently_played")),
    (lambda value, _: _is_personal_memory_request(value), AskDjIntent("informational", "personal_music_dna_summary", "music_dna_summary")),
    (lambda value, _: _is_music_discovery_summary_request(value), AskDjIntent("informational", "music_discovery_summary", "music_discovery_summary")),
    (lambda value, _: "luisterprofiel" in value or "listening profile" in value, AskDjIntent("informational", "personal_music_profile_analysis", "profile_analysis")),
    (lambda value, _: _is_personal_music_profile_request(value), AskDjIntent("informational", "personal_music_profile_analysis", "profile_analysis")),
    (lambda value, _: _is_personal_artist_recommendation_request(value), AskDjIntent("informational", "personal_artist_recommendations", "none")),
    (lambda value, _: _is_dj_announcement_request(value), AskDjIntent("hybrid", "dj_announcement", "announce", play=False)),
    (lambda value, _: is_track_insight_request(value) or _is_track_insight_analysis_request(value), AskDjIntent("informational", "track_insight", "track_insight")),
    (lambda value, _: _is_morning_start_request(value), AskDjIntent("informational", "morning_music_suggestion", "none")),
    (lambda value, _: _is_save_generated_playlist_request(value), AskDjIntent("informational", "save_generated_playlist", "create_playlist")),
    (lambda value, _: _is_seed_mix_playlist_request(value), AskDjIntent("informational", "build_playlist_from_seeds", "none")),
    (lambda value, _: _is_mood_mix_request(value), AskDjIntent("informational", "mood_mix", "none")),
    (lambda _, raw: _play_something_from_artist_request(raw), AskDjIntent("hybrid", "play_music", "play_music", play=True)),
    (lambda value, _: _artist_item_list_request(value), AskDjIntent("informational", "artist_item_list", "none")),
    (lambda value, _: value == "meer muziek van deze artiest" or _is_artist_more_tracks_question(value), AskDjIntent("informational", "artist_more_tracks", "none")),
    (lambda _, raw: _explicit_artist_from_more_tracks_question(raw), AskDjIntent("informational", "artist_more_tracks", "none")),
    (lambda value, _: _is_song_recommendation_request(value), AskDjIntent("informational", "song_recommendations", "none")),
    (lambda value, _: value in {"recommend a playlist", "welke afspeellijst past bij mijn bui"}, AskDjIntent("informational", "playlist_recommendation_offer", "none")),
    (lambda value, _: value in {"geef me aanbevelingen", "recommend music for me", "suggest something based on my taste"} or _is_personal_recommendation_request(value), AskDjIntent("informational", "personal_music_recommendations", "none")),
    (lambda value, _: _is_user_playlists_request(value), AskDjIntent("informational", "spotify_user_playlists", "none")),
    (lambda value, _: not _execution_request(value) and _vibe_playlist_query(value), AskDjIntent("informational", "spotify_vibe_playlists", "none")),
    (lambda value, _: not _execution_request(value) and _is_open_playlist_recommendation_request(value), AskDjIntent("informational", "playlist_recommendation_offer", "none")),
    (lambda value, _: not _execution_request(value) and _is_playlist_search_request(value), AskDjIntent("informational", "spotify_playlist_search", "none")),
    (lambda value, _: _is_next_track_info_request(value), AskDjIntent("informational", "next_track_info", "queue")),
    (lambda value, _: _is_concert_agenda_request(value), AskDjIntent("informational", "artist_concerts", "concert_agenda")),
    (lambda value, _: any(phrase in value for phrase in ("waarom koos", "waarom heb je", "vertel iets", "wanneer speelt", "analyseer", "welke albums", "album art", "cover")), AskDjIntent("informational", "ask_music_info")),
    (lambda value, _: any(phrase in value for phrase in ("vergelijkbare artiesten", "similar artists", "artiesten die hierop lijken", "artists like this", "klinkt er als")) or ("vergelijkbare muziek" in value and "artiest" in value), AskDjIntent("informational", "similar_artists", "none")),
    (lambda value, _: any(term in value for term in ("vergelijkbaar", "vergelijkbare", "similar", "zelfde soort", "lijkt op", "nog meer leuk")), AskDjIntent("informational", "ask_music_info")),
    (lambda value, _: any(word in value for word in ("pauzeer", "stop muziek", "stop de muziek", "ik ga slapen", "ga slapen", "pause music")), AskDjIntent("action", "playback_control", "pause")),
    (lambda value, _: any(phrase in value for phrase in ("start muziek", "start de muziek", "speel verder", "hervat muziek", "hervat de muziek", "resume", "play music")), AskDjIntent("action", "playback_control", "play")),
    (lambda value, _: value == "sla dit nummer op", AskDjIntent("action", "playback_control", "set_current_track_favorite", True)),
    (lambda value, _: "volgende" in value or value in {"next", "skip", "next song", "next track"}, AskDjIntent("action", "playback_control", "next")),
    (lambda value, _: "vorige" in value or "vorig nummer" in value or value in {"previous", "previous song", "previous track"}, AskDjIntent("action", "playback_control", "previous")),
    (lambda value, _: "harder" in value or "volume omhoog" in value, AskDjIntent("action", "playback_control", "volume_delta", 10)),
    (lambda value, _: "zachter" in value or "volume omlaag" in value, AskDjIntent("action", "playback_control", "volume_delta", -10)),
    (lambda value, _: _is_playback_mode_status_question(value), AskDjIntent("informational", "playback_mode_status", "status")),
    (lambda value, _: "shuffle" in value, lambda value: AskDjIntent("action", "playback_control", "set_shuffle", "uit" not in value)),
    (lambda value, _: "repeat" in value or "herhaal" in value, lambda value: AskDjIntent("action", "playback_control", "set_repeat", "off" if "uit" in value else "context")),
    (lambda value, _: _is_output_selection_request(value), AskDjIntent("informational", "list_outputs", "devices")),
    (lambda value, _: ("waarop" in value and "muziek" in value) or any(phrase in value for phrase in ("op welke speaker speelt de muziek", "welke speaker is actief", "waar speelt dit af", "what speaker is active")), AskDjIntent("informational", "current_output", "status")),
    (lambda value, _: _is_deferred_playback_request(value), AskDjIntent("hybrid", "play_music", "play_music", play=True)),
    (lambda value, _: bool(music_command_subject(value) or re.search(r"\b(speel|draai|zet|play|put on)\b", value)), AskDjIntent("hybrid", "play_music", "play_music", play=True)),
)


async def _handle_action(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    classification: AskDjIntent,
    payload: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    action = classification.action or ""
    if action == "volume_delta":
        return await _volume_delta_response(hass, runtime, classification)
    if action in {"pause", "play", "next", "previous"}:
        return await _playback_action_response(hass, runtime, text, action)
    if action == "set_shuffle":
        return await _toggle_playback_response(hass, runtime, "set_shuffle", classification.value)
    if action == "set_repeat":
        return await _toggle_playback_response(hass, runtime, "set_repeat", classification.value)
    if action in {"save_current_track", "set_current_track_favorite"}:
        return await _favorite_action_response(hass, runtime, action, classification.value, payload, user_id)
    raise ValueError(f"Unsupported Ask DJ action: {action}")


def _failed_backend_action(result: Any) -> dict[str, Any] | None:
    """Keep a failed backend command from becoming an Ask DJ success claim."""
    if not isinstance(result, dict) or result.get("success") is not False:
        return None
    message = str(result.get("message") or result.get("text") or "Playback is unavailable.")
    return {
        "success": False,
        "error": str(result.get("error") or "playback_unavailable"),
        "text": message,
        "dj_text": message,
        "images": [],
        "links": [],
        "sources": [],
        "playback_actions": [],
    }


async def _volume_delta_response(hass: HomeAssistant, runtime: Any, classification: AskDjIntent) -> dict[str, Any]:
    status = await run_music_command(hass, runtime, "status")
    if failure := _failed_backend_action(status):
        return failure
    playback = status.get("playback") if isinstance(status, dict) else {}
    current = _playback_volume(playback, runtime)
    if current is None:
        return {"success": False, "text": "Ik kan het huidige volume nu niet bepalen.", "error": "playback_unavailable"}
    target = max(0, min(60, current + int(classification.value or 0)))
    result = await run_music_command(hass, runtime, "set_volume", target)
    if failure := _failed_backend_action(result):
        return failure
    from .dialogue import current_turn
    turn=current_turn.get()
    language=turn.style.get("language","nl") if turn else "nl"
    text={"en":"Volume change requested.","nl":"Volumeaanpassing aangevraagd.",
          "de":"Lautstärkeänderung angefordert.","fr":"Modification du volume demandée.",
          "es":"Cambio de volumen solicitado."}[language]
    confirmed = result.get("playback") if isinstance(result.get("playback"), dict) else {}
    observed_volume = _playback_volume(confirmed, None) if confirmed else None
    return {"success": True, "text": text, "dj_text": text, "action_outcome": {"state": "dispatched", "readback_confirmed": observed_volume == target}, "playback": confirmed, "images": [], "links": [], "sources": [], "items": [], "audio_url": None, "playback_actions": _volume_control_actions(),
        **({"playback_projection_receipt": result["playback_projection_receipt"]} if "playback_projection_receipt" in result else {})}


async def _playback_action_response(hass: HomeAssistant, runtime: Any, text: str, action: str) -> dict[str, Any]:
    if action in {"next", "previous"}:
        return await _skip_playback_action_response(hass, runtime, text, action)
    result = await run_music_command(hass, runtime, action)
    if failure := _failed_backend_action(result):
        return failure
    text_response = _control_dispatch_text(action)
    return {"success": True, "text": text_response, "dj_text": text_response, "action_outcome": {"state": "dispatched", "readback_confirmed": False}, "playback": result.get("playback") if isinstance(result, dict) else {}, "images": [], "links": [], "sources": [], "playback_actions": _playback_control_actions(action),
        **({"playback_projection_receipt": result["playback_projection_receipt"]} if "playback_projection_receipt" in result else {})}


async def _skip_playback_action_response(hass: HomeAssistant, runtime: Any, text: str, action: str) -> dict[str, Any]:
    # The qualified control stays typed; never reparse it as a music search.
    result = await run_music_command(hass, runtime, action)
    if failure := _failed_backend_action(result):
        return failure
    text_response = _control_dispatch_text(action)
    playback = result.get("playback") if isinstance(result, dict) else {}
    title = _playback_text(playback or {}, "track_name", "title", "name")
    artist = _playback_text(playback or {}, "artist", "artist_name")
    if title:
        from .dialogue import current_turn
        turn = current_turn.get()
        language = turn.style.get("language", "nl") if turn else "nl"
        labels = {"en": ("Current playback", "by"), "nl": ("Actuele playback", "van"),
            "de": ("Aktuelle Wiedergabe", "von"), "fr": ("Lecture actuelle", "de"), "es": ("Reproducción actual", "de")}
        label, join = labels[language]
        text_response += f" {label}: {title}{f' {join} {artist}' if artist else ''}."
    # A control neither prefetches an unrelated queue nor replaces its choice set.
    return {"success": True, "text": text_response, "dj_text": text_response, "action_outcome": {"state": "dispatched", "readback_confirmed": False}, "playback": playback, "images": [], "links": [], "sources": [], "playback_actions": [], "items": [],
        **({"playback_projection_receipt": result["playback_projection_receipt"]} if "playback_projection_receipt" in result else {})}


def _control_dispatch_text(action):
    """A successful dispatch is distinct from observed playback."""
    from .dialogue import current_turn
    turn = current_turn.get()
    language = turn.style.get("language", "nl") if turn else "nl"
    captions = {
        "en": {"pause": "Pause requested.", "play": "Playback requested.", "next": "Next track requested.", "previous": "Previous track requested."},
        "nl": {"pause": "Pauzeren aangevraagd.", "play": "Afspelen aangevraagd.", "next": "Volgende nummer aangevraagd.", "previous": "Vorige nummer aangevraagd."},
        "de": {"pause": "Pause angefordert.", "play": "Wiedergabe angefordert.", "next": "Nächster Titel angefordert.", "previous": "Vorheriger Titel angefordert."},
        "fr": {"pause": "Pause demandée.", "play": "Lecture demandée.", "next": "Morceau suivant demandé.", "previous": "Morceau précédent demandé."},
        "es": {"pause": "Pausa solicitada.", "play": "Reproducción solicitada.", "next": "Siguiente canción solicitada.", "previous": "Canción anterior solicitada."},
    }
    return captions[language][action]


async def _toggle_playback_response(hass: HomeAssistant, runtime: Any, command: str, value: Any) -> dict[str, Any]:
    result = await run_music_command(hass, runtime, command, value)
    if failure := _failed_backend_action(result):
        return failure
    text = ("Shuffle staat aan." if value else "Shuffle staat uit.") if command == "set_shuffle" else ("Repeat is uitgezet." if value == "off" else "Repeat is aangezet.")
    return {"success": True, "text": text, "dj_text": text, "images": []}


async def _favorite_action_response(hass: HomeAssistant, runtime: Any, action: str, value: Any, payload: dict[str, Any] | None, user_id: str | None) -> dict[str, Any]:
    command = "set_current_track_favorite" if action == "set_current_track_favorite" else "save_current_track"
    result = await run_music_command(hass, runtime, command, value)
    if failure := _failed_backend_action(result):
        return failure
    playback = result.get("playback") if isinstance(result, dict) else {}
    favorite_status = _playback_favorite_status(playback) if isinstance(playback, dict) else None
    await _async_record_favorite_preference(runtime, playback, favorite_status, payload, user_id)
    title = _track_label(playback) if isinstance(playback, dict) else ""
    text = (f"Ik heb {title} uit je favorieten gehaald." if title else "Ik heb dit nummer uit je favorieten gehaald.") if favorite_status is False else (f"Ik heb {title} toegevoegd aan je favorieten." if title else "Ik heb dit nummer toegevoegd aan je favorieten.")
    return {"success": True, "text": text, "dj_text": text, "playback": {}, "images": [], "links": [], "sources": [], "items": [], "playback_actions": []}


async def _async_record_favorite_preference(runtime: Any, playback: Any, favorite_status: bool | None, payload: dict[str, Any] | None, user_id: str | None) -> None:
    if not isinstance(playback, dict):
        return
    method = "async_record_blocked_music_preference" if favorite_status is False else "async_record_current_track_favorite"
    recorder = getattr(getattr(runtime, "memory", None), method, None)
    if recorder is None:
        return
    try:
        value = _favorite_removed_preference(playback) if favorite_status is False else playback
        await recorder(runtime, value, payload, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect could not record favorite preference in Music DNA: %s", exc)


def _favorite_removed_preference(playback: dict[str, Any]) -> dict[str, str]:
    """Return a compact negative preference for a track removed from favorites."""
    title = _playback_text(playback, "track_name", "title", "name")
    artist = _playback_text(playback, "artist", "artist_name")
    uri = _playback_text(playback, "uri", "current_uri")
    name = " - ".join(value for value in (artist, title) if value) or title or uri
    return {
        "kind": "track",
        "name": name,
        "title": title or name,
        "artist": artist,
        "uri": uri,
        "reason": "removed_from_favorites",
    }


async def _handle_hybrid(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    classification: AskDjIntent,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not classification.play:
        return await _deferred_playback_request_response(hass, runtime, text)
    try:
        result = await run_text_command(
            hass,
            runtime,
            text,
            play=classification.play,
            correct_stt=_is_voice_input(payload or {}),
        )
        if result.get("playback_outcome"):
            from ..playback_request import response as playback_response
            return {**result, **await playback_response(hass,runtime,result["playback_outcome"])}
        canonical_text = _canonical_playback_confirmation(result)
        if canonical_text and _should_use_canonical_playback_confirmation(result, canonical_text):
            result = {**result, "text": canonical_text, "dj_text": canonical_text}
        return {"success": True, **result}
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("DJConnect Ask DJ playback request failed: %s", exc)
        if _looks_like_no_active_output_error(exc):
            speaker_response = await _playback_output_selection_response(
                hass,
                runtime,
                text,
                payload or {},
                classification,
                selection=getattr(exc, "playback_selection", None),
            )
            if speaker_response:
                return speaker_response
        dj_text = _playback_failed_text(runtime, text, payload)
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


async def _playback_output_selection_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    payload: dict[str, Any],
    classification: AskDjIntent,
    *, selection=None,
) -> dict[str, Any]:
    devices = await _available_output_devices(hass, runtime)
    actions = _output_device_play_request_actions(devices, text, payload, selection=selection)
    if not actions:
        return {}
    message = _read_text('speaker')
    await _store_pending_followup(
        runtime,
        payload,
        question=message,
        proposed_intent=classification.intent,
        proposed_action="select_output_for_playback",
        proposed_payload={"text": text, "playback_actions": actions},
    )
    return {
        "success": True,
        "error": "no_active_output",
        "message": message,
        "text": message,
        "dj_text": message,
        "action": "select_output",
        "intent": {
            "category": classification.category,
            "intent": classification.intent,
            "action": classification.action,
        },
        "images": [],
        "links": [],
        "sources": [{"source": "spotify_devices", "kind": "source", "title": "Spotify devices"}],
        "items": actions,
        "playback_actions": actions,
    }


async def _deferred_playback_request_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
) -> dict[str, Any]:
    parsed = parse_spoken_music_request(text)
    media_type = str(parsed.get("type") or "track").strip().lower() or "track"
    query = str(parsed.get("query") or text or "").strip()
    genre_query = _genre_options_request(text)
    if genre_query:
        return await _genre_media_options_response(hass, runtime, genre_query)
    if _is_fuzzy_music_search_request(_normalize(text)):
        return await _fuzzy_music_search_response(hass, runtime, query or text)
    try:
        result = await run_music_command(
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
    label = _public_play_now_label(action, fallback="je verzoek")
    message = (
        f"Ik heb {label} vooraan klaargezet. "
        "Wil je hem nu direct horen? Tik dan op Play Now."
    )
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": [action],
        "sources": [{"source": "spotify_search", "title": "Spotify search", "kind": "source"}],
    }


def _public_play_now_label(action: dict[str, Any], *, fallback: str) -> str:
    title = str(action.get("title") or "").strip()
    subtitle = str(action.get("subtitle") or "").strip()
    if _looks_like_spotify_uri(title):
        title = subtitle or ""
        subtitle = ""
    if _looks_like_spotify_uri(subtitle):
        subtitle = ""
    if not title:
        title = fallback
    return f"{title} van {subtitle}" if subtitle else title


def _canonical_playback_confirmation(result: dict[str, Any]) -> str:
    media = _resolved_media_from_result(result)
    if not media:
        return ""
    artist_playback = _track_playback_from_artist_request(result, media)
    if artist_playback:
        text = _artist_playback_confirmation(artist_playback)
        if text:
            return text
    derived = _track_from_search_query_and_playback_artist(result, media)
    if derived:
        text = _track_confirmation(derived)
        if text:
            return text
    return _media_playback_confirmation(media)


def _artist_playback_confirmation(playback: dict[str, Any]) -> str:
    """Build confirmation text for a resolved track from an artist request."""
    title = str(playback.get("track_name") or playback.get("title") or "").strip()
    artist = str(playback.get("artist") or playback.get("artist_name") or "").strip()
    album = str(playback.get("album_name") or playback.get("album") or "").strip()
    if title and artist and album:
        return f"Daar is {artist}, met {title}. Van {album}."
    return _track_confirmation({"title": title, "artist": artist})


def _track_confirmation(track: dict[str, Any]) -> str:
    """Build concise confirmation text for a title and artist."""
    title = str(track.get("title") or "").strip()
    artist = str(track.get("artist") or "").strip()
    return f"Daar is {title} van {artist}." if title and artist else ""


def _media_playback_confirmation(media: dict[str, Any]) -> str:
    """Build the fallback confirmation directly from resolved media."""
    media_type = str(media.get("type") or media.get("media_content_type") or "").strip().lower()
    title = str(media.get("track_name") or media.get("title") or media.get("name") or "").strip()
    artist = str(media.get("artist") or media.get("artist_name") or "").strip()
    if media_type == "artist":
        return f"Daar is {artist or title}." if artist or title else ""
    return _track_confirmation({"title": title, "artist": artist}) or (
        f"Daar is {title or artist}." if title or artist else ""
    )


def _should_use_canonical_playback_confirmation(
    result: dict[str, Any],
    canonical_text: str,
) -> bool:
    existing_text = str(result.get("dj_text") or result.get("text") or "").strip()
    if not existing_text:
        return True
    if _normalize(existing_text) == _normalize(canonical_text):
        return True
    identity = _playback_confirmation_identity(result)
    if identity.get("derived_from_query"):
        return True
    artist = str(identity.get("artist") or "").strip()
    title = str(identity.get("title") or "").strip()
    if artist and title:
        return not (_text_mentions(existing_text, artist) and _text_mentions(existing_text, title))
    if artist:
        return not _text_mentions(existing_text, artist)
    if title:
        return not _text_mentions(existing_text, title)
    return True


def _playback_confirmation_identity(result: dict[str, Any]) -> dict[str, str]:
    media = _resolved_media_from_result(result)
    if not media:
        return {}
    artist_playback = _track_playback_from_artist_request(result, media)
    if artist_playback:
        return {
            "title": str(artist_playback.get("track_name") or artist_playback.get("title") or "").strip(),
            "artist": str(artist_playback.get("artist") or artist_playback.get("artist_name") or "").strip(),
        }
    derived = _track_from_search_query_and_playback_artist(result, media)
    if derived:
        return {
            "title": str(derived.get("title") or "").strip(),
            "artist": str(derived.get("artist") or "").strip(),
            "derived_from_query": "1",
        }
    media_type = str(media.get("type") or media.get("media_content_type") or "").strip().lower()
    title = str(media.get("track_name") or media.get("title") or media.get("name") or "").strip()
    artist = str(media.get("artist") or media.get("artist_name") or "").strip()
    if media_type == "artist":
        return {"title": "", "artist": artist or title}
    return {"title": title, "artist": artist}


def _text_mentions(text: str, value: str) -> bool:
    normalized_text = _normalize(text)
    normalized_value = _normalize(value)
    return bool(normalized_text and normalized_value and normalized_value in normalized_text)


def _track_playback_from_artist_request(
    result: dict[str, Any],
    media: dict[str, Any],
) -> dict[str, Any]:
    requested_artist = _requested_artist_from_playback_result(result, media)
    if not requested_artist:
        return {}
    normalized_requested = _normalize(requested_artist)
    for source in _playback_media_sources(result):
        title = str(source.get("track_name") or source.get("title") or "").strip()
        artist = str(source.get("artist") or source.get("artist_name") or "").strip()
        if not title or not artist:
            continue
        if _normalize(artist) == normalized_requested:
            return source
    return {}


def _requested_artist_from_playback_result(
    result: dict[str, Any],
    media: dict[str, Any],
) -> str:
    media_type = str(media.get("type") or media.get("media_content_type") or "").strip().lower()
    candidates: list[Any] = []
    if media_type in {"artist", "track"}:
        candidates.extend((media.get("artist"), media.get("artist_name"), media.get("name"), media.get("title")))
    intent = result.get("intent") if isinstance(result.get("intent"), dict) else {}
    intent_type = str(intent.get("type") or "").strip().lower()
    if intent_type == "artist":
        candidates.extend((intent.get("artist"), intent.get("artist_name"), intent.get("name"), intent.get("query"), intent.get("spotify_search_query")))
    elif intent_type == "track":
        candidates.extend((intent.get("artist"), intent.get("artist_name")))
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return ""


def _track_from_search_query_and_playback_artist(
    result: dict[str, Any],
    media: dict[str, Any],
) -> dict[str, str]:
    query = _playback_search_query(result, media)
    if not query:
        return {}
    artist = _playback_artist_from_result(result, query)
    if not artist:
        return {}
    pattern = re.compile(rf"^(?P<title>.+?)\s+{re.escape(artist)}$", flags=re.IGNORECASE)
    match = pattern.match(query)
    if not match:
        return {}
    title = match.group("title").strip(" -–—,:;")
    if not title:
        return {}
    return {"title": _title_case_search_text(title), "artist": artist}


def _playback_search_query(result: dict[str, Any], media: dict[str, Any]) -> str:
    candidates: list[Any] = []
    intent = result.get("intent") if isinstance(result.get("intent"), dict) else {}
    candidates.extend(
        (
            intent.get("spotify_search_query"),
            intent.get("query"),
            media.get("spotify_search_query"),
            media.get("query"),
            media.get("artist") if str(media.get("type") or "").strip().lower() == "artist" else "",
            media.get("name") if str(media.get("type") or "").strip().lower() == "artist" else "",
        )
    )
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return ""


def _playback_artist_from_result(result: dict[str, Any], query: str) -> str:
    normalized_query = _normalize(query)
    for source in _playback_media_sources(result):
        artist = str(source.get("artist") or source.get("artist_name") or source.get("name") or "").strip()
        if not artist:
            continue
        normalized_artist = _normalize(artist)
        if normalized_artist and normalized_artist != normalized_query and normalized_query.endswith(normalized_artist):
            return artist
    return ""


def _playback_media_sources(result: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for key in ("playback", "resolved_media", "media", "track"):
        value = result.get(key)
        if isinstance(value, dict):
            sources.append(value)
            for nested_key in ("resolved_media", "media", "track", "device_response"):
                nested = value.get(nested_key)
                if isinstance(nested, dict):
                    sources.append(nested)
                    nested_playback = nested.get("playback")
                    if isinstance(nested_playback, dict):
                        sources.append(nested_playback)
    return sources


def _title_case_search_text(value: str) -> str:
    words = str(value or "").strip().split()
    return " ".join(word[:1].upper() + word[1:] for word in words)


def _resolved_media_from_result(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    for source in (
        result.get("resolved_media"),
        result.get("media"),
        result.get("track"),
        result.get("intent"),
    ):
        if isinstance(source, dict) and source:
            media = _media_from_result_source(source)
            if media:
                return media
    playback = result.get("playback")
    if isinstance(playback, dict):
        for source in (
            playback.get("resolved_media"),
            playback.get("media"),
            playback.get("track"),
            playback,
        ):
            if isinstance(source, dict) and source:
                media = _media_from_result_source(source)
                if media:
                    return media
    return {}


def _media_from_result_source(source: dict[str, Any]) -> dict[str, Any]:
    media_type = str(source.get("type") or source.get("media_content_type") or "").strip().lower()
    if media_type == "artist":
        artist = str(source.get("artist") or source.get("artist_name") or source.get("name") or source.get("title") or "").strip()
        return {"type": "artist", "artist": artist, "name": artist} if artist else {}
    if media_type == "album":
        album = str(source.get("album") or source.get("album_name") or source.get("name") or source.get("title") or "").strip()
        artist = str(source.get("artist") or source.get("artist_name") or "").strip()
        return {"type": "album", "title": album, "artist": artist} if album or artist else {}
    title = str(source.get("track_name") or source.get("title") or "").strip()
    artist = str(source.get("artist") or source.get("artist_name") or "").strip()
    if title or artist:
        media = dict(source)
        if media_type:
            media["type"] = media_type
        return media
    return {}


def _looks_like_spotify_uri(value: Any) -> bool:
    return str(value or "").strip().lower().startswith("spotify:")


async def _fuzzy_music_search_response(
    hass: HomeAssistant,
    runtime: Any,
    query: str,
) -> dict[str, Any]:
    """Return Spotify track, playlist and album candidates for broad music requests."""
    cleaned_query = _clean_fuzzy_music_query(query)
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for media_type in ("track", "playlist", "album"):
        try:
            result = await run_music_command(
                hass,
                runtime,
                "search_media",
                {"query": cleaned_query, "type": media_type},
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug(
                "DJConnect fuzzy Spotify %s search failed: %s",
                media_type,
                exc.__class__.__name__,
            )
            continue
        item = result.get("item") if isinstance(result, dict) else {}
        if not isinstance(item, dict) or not item.get("uri"):
            continue
        action = _play_now_action_from_spotify_item(hass, item)
        uri = str(action.get("uri") or "").strip()
        if not uri or uri in seen:
            continue
        seen.add(uri)
        actions.append(action)
    if not actions:
        message = "Ik kon geen passende tracks, playlists of albums vinden op Spotify."
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "images": [],
            "items": [],
            "playback_actions": [],
            "sources": [{"source": "spotify_search", "title": "Spotify search", "kind": "source"}],
        }
    kinds = _join_examples(
        [_spotify_kind_label(str(action.get("kind") or "")) for action in actions],
        limit=3,
    )
    message = (
        f"Ik vond {kinds} voor {cleaned_query} op Spotify. "
        "Kies wat je wilt horen met Play Now."
    )
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "items": actions,
        "playback_actions": actions,
        "sources": [{"source": "spotify_search", "title": "Spotify search", "kind": "source"}],
    }


async def _track_title_choice_response(
    hass: HomeAssistant,
    runtime: Any,
    query: str,
) -> dict[str, Any]:
    result = await _spotify_track_search(hass, runtime, query, limit=3)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    actions = _track_recommendation_actions(hass, tracks, limit=3, runtime=runtime)
    if not actions:
        return {
            "success": True,
            "text": "",
            "dj_text": "",
            "action": "none",
            "images": [],
            "items": [],
            "playback_actions": [],
            "sources": [{"source": "spotify_track_search", "title": "Spotify track search", "kind": "source"}],
        }
    lines = [
        f"{index}. {action.get('title') or 'Onbekend nummer'}"
        + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
        for index, action in enumerate(actions, start=1)
    ]
    message = (
        f"Welke artiest bedoel je met {query}?\n"
        + "\n".join(lines)
        + "\n\nTik op Play Now bij de versie die je wilt horen."
    )
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "items": actions,
        "playback_actions": actions,
        "sources": [{"source": "spotify_track_search", "title": "Spotify track search", "kind": "source"}],
    }


def _bare_track_title_play_query(text: str) -> str:
    normalized = _normalize(text)
    if not normalized:
        return ""
    if not (
        re.search(r"\b(?:nummer|liedje|track|song)\b", normalized)
        or normalized in {"speel zombie", "draai zombie", "zet zombie op", "play zombie"}
    ):
        return ""
    match = re.match(
        r"^\s*(?:speel|draai|zet)\s+(?:eens\s+|even\s+|graag\s+)?(.+?)\s*(?:op|af|aan)?\s*$",
        str(text or "").strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    query = re.sub(r"\s+", " ", match.group(1)).strip(" ?.!'\">")
    normalized_query = _normalize(query)
    if not query or len(normalized_query.split()) > 4:
        return ""
    if any(
        token in normalized_query
        for token in (
            "album",
            "artist",
            "artiest",
            "band",
            "playlist",
            "muziek",
            "music",
            "genre",
            "mood",
            "stemming",
        )
    ):
        return ""
    if re.search(r"\b(?:van|by|door|from|met|with)\b", normalized_query):
        return ""
    return query


def _clean_fuzzy_music_query(query: str) -> str:
    """Keep the user's broad music phrase useful for Spotify fuzzy search."""
    text = str(query or "").strip()
    match = re.search(
        r"\b(?:ik\s+wil|ik\s+wil\s+wel|ik\s+wil\s+graag|wil\s+ik|i\s+want|i\s+would\s+like)\b\s+(.+?)\s+\b(?:muziek|music)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"\b(?:wat\s+voor|welke|what\s+kind\s+of|which)\b\s+(.+?)\s+\b(?:muziek|music)\b(?:\s+(?:heb\s+je|have\s+you|do\s+you\s+have))?",
            text,
            flags=re.IGNORECASE,
        )
    cleaned = match.group(1) if match else text
    cleaned = re.sub(r"\b(?:muziek|music)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:heb\s+je|have\s+you|do\s+you\s+have)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ?.!'\">")
    return cleaned or text or "muziek"


def _spotify_kind_label(kind: str) -> str:
    return {
        "track": "tracks",
        "playlist": "playlists",
        "album": "albums",
        "artist": "artiesten",
    }.get(str(kind or "").strip().lower(), "resultaten")


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
    from .dialogue import current_turn
    turn = current_turn.get()
    if ask_intent.intent in {"ask_music_info", "artist_concerts"} and turn is not None and turn.source_context:
        return await _informational_assist_response(hass, runtime, text, payload, memory_context, {}, [])
    response = await _informational_intent_response(
        hass,
        runtime,
        text,
        payload,
        memory_context,
        playback_context,
        output_devices,
        ask_intent,
    )
    if response is not None:
        return response
    response = await _informational_catalog_response(
        hass,
        runtime,
        text,
        payload,
        memory_context,
        playback_context,
        ask_intent,
    )
    if response is not None:
        return response
    response = await _informational_profile_response(
        hass,
        runtime,
        text,
        payload,
        memory_context,
        playback_context,
        ask_intent,
    )
    if response is not None:
        return response
    return await _informational_assist_response(
        hass,
        runtime,
        text,
        payload,
        memory_context,
        playback_context,
        output_devices,
    )


async def _informational_intent_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    output_devices: list[dict[str, Any]],
    ask_intent: Any,
) -> dict[str, Any] | None:
    if ask_intent.intent == "help":
        from .example_catalogue import help_context
        return _help_response(_response_language(runtime, payload), help_context(hass, runtime))
    if ask_intent.intent == "session_forecast_information":
        from .observations import forecast_read
        return await forecast_read(hass, runtime)
    if ask_intent.intent == "previous_track_information":
        from .observations import previous_read
        return await previous_read(hass, runtime)
    if ask_intent.action == "devices":
        language = _response_language(runtime, payload)
        message = _devices_text(output_devices, language)
        actions = _output_device_actions(output_devices, language)
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "intent": {"category": "informational", "intent": "list_outputs"},
            "images": [],
            "links": [],
            "sources": [],
            "playback_actions": actions,
            "items": actions,
        }
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
    if ask_intent.intent == "recently_played_history":
        return await _recently_played_history_response(hass, runtime, text)
    if ask_intent.intent == "track_insight":
        return await _track_insight_response(hass, runtime, payload)
    if _is_current_track_album_question(text):
        return _current_track_album_response(hass, playback_context)
    if _is_current_playing_question(text):
        return await _current_track_reference_response(hass, runtime, payload, playback_context)
    if _is_slang_track_info_request(text):
        return await _current_track_reference_response(hass, runtime, payload, playback_context)
    if ask_intent.action == "status":
        return _playback_status_response(text, playback_context, runtime)
    if ask_intent.intent == "save_generated_playlist":
        return await _save_generated_playlist(hass, runtime, text, memory_context)
    if ask_intent.intent == "song_recommendations":
        return await _song_recommendations_response(hass, runtime, text)
    current_track_seed = _current_track_seed_mix_request(text)
    if current_track_seed:
        return await _current_track_seed_mix_response(hass, runtime, playback_context, current_track_seed)
    seed_mix = _seeds_from_mix_playlist_request(text) if ask_intent.intent == "build_playlist_from_seeds" else {}
    if seed_mix:
        result = await _spotify_seed_mix(hass, runtime, seed_mix)
        tracks = result.get("tracks") if isinstance(result, dict) else []
        track_actions = _track_recommendation_actions(hass, tracks, limit=10, runtime=runtime)
        mix_action = _seed_mix_playback_action(hass, seed_mix, tracks)
        actions = track_actions + ([mix_action] if mix_action else [])
        if actions:
            message = (
                "Ik heb een mix samengesteld op basis van "
                + _seed_mix_label(seed_mix)
                + ". Ik start nog niets; tik op Play Now bij een track of zet de hele mix in de wachtrij."
            )
        else:
            message = (
                f"Ik kon nu geen speelbare Spotify-mix samenstellen op basis van {_seed_mix_label(seed_mix)}."
            )
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "images": [],
            "items": actions,
            "playback_actions": actions,
            "sources": [
                {
                    "source": "spotify_recommendations",
                    "kind": "source",
                    "title": "Spotify recommendations",
                }
            ],
        }
    if ask_intent.intent == "mood_mix":
        return await _mood_mix_response(hass, runtime, payload, memory_context)
    if ask_intent.intent == "spotify_user_playlists":
        return await _spotify_user_playlists_response(hass, runtime)
    return None


async def _informational_catalog_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    ask_intent: Any,
) -> dict[str, Any] | None:
    item_list_request = _artist_item_list_request(text)
    if item_list_request:
        return await _artist_item_list_response(hass, runtime, item_list_request)
    more_media_artist = _artist_more_media_request(text, playback_context)
    if more_media_artist:
        return await _artist_more_media_response(hass, runtime, more_media_artist)
    vibe_playlist_query = _vibe_playlist_query(text)
    if vibe_playlist_query:
        return await _spotify_playlist_search_response(
            hass,
            runtime,
            vibe_playlist_query,
            limit=5,
            include_items=True,
            text_prefix="Ik vond vijf Spotify-playlists voor",
            include_idle_notice=False,
        )
    playlist_query = _playlist_query_from_question(text)
    if playlist_query:
        if _playlist_question_wants_track_choices(text):
            return await _playlist_track_choices_response(hass, runtime, playlist_query)
        return await _spotify_playlist_search_response(
            hass,
            runtime,
            playlist_query,
            limit=10,
            include_items=False,
            text_prefix="Zeker. Ik vond deze Spotify-playlists voor",
            include_idle_notice=True,
        )
    more_tracks_artist = _artist_from_more_tracks_question(
        text,
        memory_context,
        playback_context,
    )
    if more_tracks_artist:
        return await _artist_more_tracks_response(hass, runtime, more_tracks_artist)
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
            listening_profile = await _listening_profile_context(
                hass,
                runtime,
                payload,
                memory_context,
            )
            return _related_artists_response(related, memory_context, listening_profile)
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
    # Artist background belongs to the guarded semantic/public-research owner.
    # Catalog metadata alone is not a biography (or a locale-correct answer).
    return None


async def _informational_profile_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    ask_intent: Any,
) -> dict[str, Any] | None:
    if ask_intent.intent == "personal_music_profile_analysis":
        listening_profile = await _listening_profile_context(
            hass,
            runtime,
            payload,
            memory_context,
        )
        message = _personal_music_profile_text(
            text,
            memory_context,
            playback_context,
            listening_profile,
        )
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "profile_analysis",
            "sources": _profile_sources(memory_context, listening_profile),
        }
    if ask_intent.intent == "personal_music_dna_summary":
        message = _personal_music_dna_summary_text(memory_context)
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "music_dna_summary",
            "images": [],
            "links": [],
            "sources": [{"source": "djconnect_music_dna", "title": "Music DNA", "kind": "source"}],
            "playback_actions": [],
        }
    if ask_intent.intent == "music_discovery_summary":
        message = _music_discovery_summary_text(text, memory_context)
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "music_discovery_summary",
            "images": [],
            "links": [],
            "sources": [
                {"source": "djconnect_music_discovery", "title": "Music Discovery", "kind": "source"},
                {"source": "djconnect_music_dna", "title": "Music DNA", "kind": "source"},
            ],
            "playback_actions": [],
        }
    if ask_intent.intent == "personal_music_recommendations":
        tool_result = await async_call_ai_tool(
            hass,
            runtime,
            "djconnect_build_recommendations",
            {"music_dna_key": payload.get("music_dna_key")},
        )
        listening_profile = (
            (
                tool_result.get("listening_profile")
                or tool_result.get("profile")
                or tool_result.get("spotify_profile")
            )
            if isinstance(tool_result, dict)
            else {}
        )
        if not isinstance(listening_profile, dict):
            listening_profile = {}
        actions = _recommendation_playback_actions(
            hass,
            runtime,
            memory_context,
            playback_context,
            listening_profile,
            limit=5,
        )
        if actions:
            message = (
                "Verrassing. Ik heb vijf suggesties gekozen op basis van je Music DNA en luisterprofiel. "
                "Ik start nog niets; tik op Play Now als je er eentje wilt horen."
            )
        else:
            message = (
                "Ik heb nog te weinig concrete speelbare aanbevelingen om "
                "een Play Now lijst te maken."
            )
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "images": [],
            "playback_actions": actions,
            "confirmation_actions": _confirmation_actions() if actions else [],
            "sources": _profile_sources(memory_context, listening_profile),
        }
    if ask_intent.intent == "personal_artist_recommendations":
        listening_profile = await _listening_profile_context(
            hass,
            runtime,
            payload,
            memory_context,
        )
        actions = _personal_artist_recommendation_actions(hass, runtime, memory_context, listening_profile, limit=8)
        if actions:
            message = (
                "Deze artiesten passen goed bij je smaak op basis van je luisterprofiel en Music DNA. "
                "Ik start niets automatisch."
            )
        else:
            message = "Ik heb nog te weinig artiestinformatie om goede matches bij je smaak te tonen."
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "images": [],
            "items": actions,
            "playback_actions": actions,
            "sources": _profile_sources(memory_context, listening_profile),
        }
    if ask_intent.intent == "playlist_recommendation_offer":
        return await _playlist_recommendation_offer_response(runtime, payload)
    return None


async def _informational_assist_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    output_devices: list[dict[str, Any]],
    *,
    research_subject: str | None = None,
    research_angle: str = "",
    contextual_research: bool = False,
) -> dict[str, Any]:
    if _looks_like_gibberish(text) or _looks_like_prompt_or_sandbox_attack(text):
        message = _unrecognized_request_text()
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "images": [],
        }

    from .dialogue import current_turn, requests_lookup
    from . import public_research
    turn = current_turn.get()
    fetched_sources = []
    research_state = {}
    semantic_scope = None
    from . import semantic_reads
    if turn and not requests_lookup(text):
        subject, qualified_music, ambiguous = ((research_subject, True, False) if research_subject
            else public_research.subject_for_question(text, turn))
        from .exploration import more_request
        if (not research_subject and more_request(text) and turn.selected_read_context is not None
                and turn.source_context.get("basis") == "cc0_normalized_fields_v1"):
            # An open exploration chooses an angle through the existing read
            # interpreter, even if just one typed name is available.
            subject, ambiguous = "", False
        named_subject = public_research.explicit_public_subject(text)
        implicit_subject = not named_subject or not public_research.safe_subject(named_subject)
        if implicit_subject and not research_subject and semantic_reads.admissible_question(text):
            semantic_scope = semantic_reads.capture_scope(hass, turn)
        if ambiguous:
            if semantic_scope is not None:
                semantic = await semantic_reads.read_response(hass, runtime, text, payload, scope=semantic_scope)
                if semantic is not None:
                    return semantic
            message = public_research.unavailable_answer(turn.style.get("language", "en"), ambiguous=True)
            return {"success": True, "text": message, "dj_text": message, "images": []}
        if not subject and turn.source_context.get("basis") != "runtime_authored_direction_v1":
            from .semantic_reads import read_response
            semantic = await read_response(hass, runtime, text, payload)
            if semantic is not None:
                return semantic
            # An unrecognized public question is not authority to answer from
            # unchecked recollection. Clarify in the same owner before any I/O.
            message = public_research.unavailable_answer(turn.style.get("language", "en"),
                ambiguous=bool(public_research.MUSIC.search(text)))
            return {"success": True, "text": message, "dj_text": message, "images": [],
                    "text_source": "core", "is_generated_text": False,
                    "knowledge_basis": "public_subject_required"}
        if subject:
            fetched_sources, research_state = await public_research.research(
                subject, text, turn.style.get("language", "en"), turn.guard,
                qualified_music=qualified_music,
                original_paragraphs=bool(research_subject or public_research.rich_introduction(text)),
                artist_introduction=bool(research_subject and not contextual_research),
                research_angle=research_angle,
                expected_roles=tuple(s.get("role") for s in turn.source_context.get("subjects", [])
                                     if s.get("name", "").casefold() == public_research.safe_subject(subject).casefold()))
            turn.public_research = public_research.research_projection(subject, fetched_sources, research_state, question=text)
            if research_subject:
                focus = public_research.documented_episode_focus(turn.public_research, angle=research_angle)
                if focus:
                    turn.public_research['editorial_focus'] = focus
            if not fetched_sources:
                if semantic_scope is not None:
                    semantic = await semantic_reads.read_response(hass, runtime, text, payload, scope=semantic_scope)
                    if semantic is not None:
                        return semantic
                message = public_research.unavailable_answer(turn.style.get("language", "en"))
                return {"success": True, "text": message, "dj_text": message, "images": [],
                        "text_source": "core", "is_generated_text": False,
                        "knowledge_basis": "public_research_unavailable",
                        "public_research_status": research_state}

    prompt = _informational_prompt(
        text,
        payload,
        memory_context,
        playback_context,
        output_devices,
        getattr(runtime, "config", {}) or {},
    )
    if semantic_scope is not None:
        prompt = semantic_reads.augment_answer_prompt(prompt, semantic_scope)
    try:
        assist_context = _assist_context(hass, getattr(runtime, "config", {}) or {})
        language = (turn.style['language'] if turn else
                    payload.get("language") or assist_context.get("language") or DEFAULT_TTS_LANGUAGE)
        data = {"text": prompt, "language": language}
        if assist_context.get("agent_id"):
            data["agent_id"] = assist_context["agent_id"]
        from .dialogue import current_turn, DialogueError
        turn = current_turn.get()
        if turn:
            await turn.guard()
        result = await _call_dialogue_agent(hass, data)
        if turn:
            await turn.guard()
        agent_response = (result or {}).get("response") or {}
        message = "" if agent_response.get("error") else _speech_from_response(agent_response)
    except Exception as exc:  # noqa: BLE001
        from .dialogue import DialogueError
        from ..session_conversation import SessionConversationError
        if isinstance(exc, (DialogueError, SessionConversationError)):
            raise
        _LOGGER.debug("DJConnect Ask DJ informational Assist answer failed: %s", type(exc).__name__)
        message = ""
    message = str(message or "").strip()
    if _looks_like_internal_prompt_leak(message):
        _LOGGER.debug("DJConnect Ask DJ informational answer ignored: internal prompt leak")
        message = ""
    if not message:
        message = _fallback_info_text(text, memory_context, playback_context)
        return {"success": True, "text": message, "dj_text": message, "images": []}
    if semantic_scope is not None:
        plan = semantic_reads.parse_plan(message)
        if plan is not None:
            semantic = await semantic_reads.execute_plan(hass, runtime, text, plan, semantic_scope)
            if semantic is not None:
                return semantic
            message = public_research.unavailable_answer(turn.style.get("language", "en"), ambiguous=True)
            return {"success": True, "text": message, "dj_text": message, "images": [],
                    "text_source": "core", "is_generated_text": False}
    from .dialogue import parse_model_reply, requests_lookup, answer_language_format_issue
    format_issue = None

    def parse_reply(reply):
        nonlocal format_issue
        answer, operation = parse_model_reply(reply)
        if fetched_sources and not operation:
            answer = public_research.without_duplicate_source_footer(answer, fetched_sources)
            if research_subject:
                from ..public_artist_narration import plain_work_titles
                answer = plain_work_titles(answer, turn.public_research)
        if turn and requests_lookup(text) and (
            operation.get("intent") not in {"lookup", "refine"} or not operation.get("query")
        ):
            raise DialogueError("conversation_model_response_invalid", 502)
        if turn and not requests_lookup(text) and operation:
            raise DialogueError("conversation_model_response_invalid", 502)
        if turn and not operation:
            from .dialogue import explicit_subject
            subjects = [s.get("name", "") for s in turn.frame.subjects + turn.source_context.get("subjects", [])]
            subjects.append(explicit_subject(text) or "")
            format_issue = answer_language_format_issue(answer, turn.style, subjects)
            if format_issue:
                raise DialogueError("conversation_model_response_invalid", 502)
        return answer, operation

    try:
        message, plan = parse_reply(message)
    except DialogueError as exc:
        if exc.code != "conversation_model_response_invalid" or not turn:
            raise
        if fetched_sources:
            # Research reserves call two for independent evidence review.
            # Invalid generation cannot buy a repair in its place or archive.
            raise
        # One read-only format retry through the same qualified agent/call budget.
        # Never send the invalid output back as context or repeat a provider effect.
        repair_instruction = (
            "Return only one valid JSON object with intent and query. No text or commentary.\n"
            if requests_lookup(text) else
            "Answer the user's factual question directly in natural prose. Do not return a search/choice/query object.\n"
        )
        if format_issue:
            repair_instruction += format_issue + " Do not change the subject or qualified source facts.\n"
        repaired = await _call_dialogue_agent(hass, {**data, "text": repair_instruction + prompt})
        response = (repaired or {}).get("response") or {}
        if response.get("error"):
            raise DialogueError("conversation_model_response_invalid", 502)
        message, plan = parse_reply(str(_speech_from_response(response) or ""))
    response = {"success": True, "text": message, "dj_text": message,
                "text_source": "generated", "is_generated_text": True,
                "model_processing_basis": "qualified_dialogue_v1",
                "knowledge_basis": "source_context_plus_general_knowledge" if turn and turn.source_context else "general_model_knowledge"}
    if turn and turn.source_context.get("attribution"):
        response["sources"] = [{**turn.source_context["attribution"], "kind": "source", "claim_scope": "qualified_credit_only"}]
    if fetched_sources and not plan:
        # Generation and grounding share the existing two-call turn budget. A
        # format repair cannot silently buy a third model call or publish an
        # unchecked answer. No excerpts are copied into history or transport.
        accepted = False
        answer_state = 'assessment_unavailable'
        if turn.agent_calls < (3 if turn.interpreted_artist_research or turn.interpreted_context_research else 2):
            grounding_context = {"public_music_research": turn.public_research,
                                 "qualified_context": turn.source_context}
            id_review = bool(turn.interpreted_artist_research
                and turn.public_research.get('schema_version') == 3)
            from ..public_artist_narration import complete_review_projection, resolve_review_quotes
            review_context = complete_review_projection(grounding_context) if id_review else grounding_context
            review_prompt = public_research.assessment_prompt(
                message, review_context, language, text, allow_prefix=not id_review, quote_by_id=id_review)
            if id_review:
                from ..narration_style import instructions as story_style
                review_prompt = review_prompt.replace('\nData:\n',
                    ' Also return language_ok and style_ok booleans. language_ok requires fluent '
                    'requested-language prose; style_ok requires a useful connected personal DJ '
                    'introduction in the requested Persona/Mood, not a metadata/biography list or '
                    'generic praise. No compulsory joke or fixed opening. '
                    + story_style(persona=turn.style['persona'], mood=turn.style['mood'], locale=language)
                    + '\nData:\n', 1)
            checked = await _call_dialogue_agent(hass, {**data, "text": review_prompt})
            await turn.guard()
            check_response = (checked or {}).get("response") or {}
            assessment = _speech_from_response(check_response)
            quality_ok = True
            if id_review:
                # Reuse the existing literal-ID wire decoder; factual coverage,
                # source identity, temporal and relationship checks are unchanged.
                from ..narration_brief import _object
                try:
                    review = _object(assessment)
                    quality_ok = review.pop('language_ok', None) is True
                    quality_ok = review.pop('style_ok', None) is True and quality_ok
                    if review.get('supported') is True:
                        review = resolve_review_quotes(review, grounding_context)
                    else:
                        review.pop('review_schema', None)  # Rejected text is never admitted.
                    assessment = json.dumps(review)
                except (ValueError, TypeError, KeyError):
                    assessment = '{}'
            accepted = (not check_response.get("error") and quality_ok
                and public_research.supported(assessment, message, grounding_context))
            if not check_response.get("error"):
                answer_state = ('full_answer_supported' if accepted
                                else 'narration_quality_unverified' if not quality_ok
                                else public_research.assessment_failure_reason(assessment))
            if not accepted and not check_response.get("error") and not id_review:
                prefix = public_research.qualified_prefix(assessment, message, grounding_context)
                if prefix is not None and answer_language_format_issue(prefix, turn.style) is None:
                    message = prefix
                    response.update(text=message, dj_text=message,
                                    research_answer_qualification='supported_prefix_v1')
                    accepted = True
                    answer_state = 'supported_prefix'
        if not accepted:
            message = public_research.unavailable_answer(turn.style.get("language", "en"), answer_unverified=True)
            response.update(text=message, dj_text=message, knowledge_basis="public_research_unqualified",
                            text_source="core", is_generated_text=False)
        else:
            response["knowledge_basis"] = "fetched_public_music_research_v1"
            actual_sources = [source.metadata() for source in fetched_sources]
            response["sources"] = response.get("sources", []) + actual_sources
            response["links"] = [{"kind": "source", "title": source.get("title", source.get("provider", "Source")),
                                  "url": source["url"], "source": source.get("provider", "Source")}
                                 for source in response["sources"] if source.get("url")]
        research_state = {**research_state, 'answer_state': answer_state}
    if research_state:
        response["public_research_status"] = research_state
    if plan:
        return await _realize_dialogue_plan(hass, runtime, payload, text, response, plan)
    return response


async def _spotify_user_playlists_response(
    hass: HomeAssistant,
    runtime: Any,
) -> dict[str, Any]:
    result = await _spotify_user_playlists(hass, runtime, limit=10)
    playlists = result.get("playlists") if isinstance(result, dict) else []
    actions = _playlist_search_playback_actions(hass, playlists, limit=10)
    message = _read_text('playlists' if actions else 'playlists_empty')
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": actions,
        "sources": [
            {
                "source": "spotify_user_playlists",
                "kind": "source",
                "title": "Spotify user playlists",
            }
        ],
    }


async def _spotify_playlist_search_response(
    hass: HomeAssistant,
    runtime: Any,
    query: str,
    *,
    limit: int,
    include_items: bool,
    text_prefix: str,
    include_idle_notice: bool,
) -> dict[str, Any]:
    result = await _spotify_playlist_search(hass, runtime, query, limit=limit)
    playlists = result.get("playlists") if isinstance(result, dict) else []
    actions = _playlist_search_playback_actions(hass, playlists, limit=limit)
    if actions:
        message = f"{text_prefix} {query}. "
        message += "Ik start nog niets; " if include_idle_notice else ""
        message += "Tik op Play Now bij de playlist die je wilt horen."
    else:
        message = f"Ik vond nu geen Spotify-playlists voor {query}."
    response = {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": actions,
        "sources": [
            {
                "source": "spotify_playlist_search",
                "title": "Spotify playlist search",
                "kind": "source",
            }
        ],
    }
    if include_items:
        response["items"] = actions
    return response


async def _playlist_recommendation_offer_response(
    runtime: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    message = (
        "Ik kan een paar persoonlijke playlist- of muzieksuggesties voor je maken "
        "op basis van je Music DNA en luisterprofiel. Wil je dat?"
    )
    confirmations = _confirmation_actions(yes_title="Ja graag", no_title="Nee dank je")
    await _store_pending_followup(
        runtime,
        payload,
        question=message,
        proposed_intent="personal_music_recommendations",
        proposed_action="ask_dj_personal_recommendations",
        proposed_payload={"text": "verras me met persoonlijke muzieksuggesties"},
    )
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "intent": {"category": "playback_confirmation", "intent": "playlist_recommendation_offer"},
        "images": [],
        "links": [],
        "sources": [],
        "playback_actions": confirmations,
        "confirmation_actions": confirmations,
    }


async def _spotify_artist_albums(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    try:
        result = await run_music_command(
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
    listening_profile = await _listening_profile_context(
        hass,
        runtime,
        payload,
        memory_context,
    )
    actions = _recommendation_playback_actions(
        hass,
        runtime,
        memory_context,
        playback_context,
        listening_profile,
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
        "sources": _profile_sources(memory_context, listening_profile),
    }


async def _next_track_info_response(
    hass: HomeAssistant,
    runtime: Any,
) -> dict[str, Any]:
    from .observations import queue_read
    return await queue_read(hass, runtime)


def _queue_items_without_current(result: Any, runtime: Any) -> list[dict[str, Any]]:
    queue = result.get("queue") if isinstance(result, dict) else []
    # Provider queue already excludes now-playing. A repeated current URI is
    # still a legitimate upcoming occurrence, not a duplicate snapshot.
    return [item for item in (queue if isinstance(queue, list) else []) if isinstance(item, dict) and item]


def _spotify_queue_source() -> dict[str, str]:
    return {"source": "spotify_queue", "title": "Spotify queue", "kind": "source"}


def _empty_queue_response() -> dict[str, Any]:
    text = "Er staat nu geen volgend nummer in de Spotify wachtrij. Wil je wat anders horen? Laat het me weten. Zeg simpelweg 'verras me' en ik speel muziek op basis van jouw voorkeur."
    return {"success": True, "text": text, "dj_text": text, "action": "none", "images": [], "playback_actions": [], "sources": [_spotify_queue_source()]}


def _queue_response(hass: HomeAssistant, result: Any, queue: list[dict[str, Any]]) -> dict[str, Any]:
    return {"success": True, "text": "Hierna in de wachtrij:", "dj_text": "Hierna in de wachtrij:", "action": "none", "images": [], "playback_actions": [action for index, item in enumerate(queue, start=1) if (action := _queue_playback_action(hass, result, item, index))], "sources": [_spotify_queue_source()]}


def _queue_playback_action(hass: HomeAssistant, result: Any, item: dict[str, Any], index: int) -> dict[str, Any]:
    uri = str(item.get("uri") or "").strip()
    if not uri.startswith("spotify:track:"):
        return {}
    image_url = str(item.get("image_url") or item.get("album_image_url") or item.get("thumbnail_url") or "").strip()
    action = {"id": uri, "title": str(item.get("title") or item.get("track_name") or f"nummer {index}").strip(), "subtitle": str(item.get("subtitle") or item.get("artist") or "").strip(), "uri": uri, "kind": "track", "label": "Play Now", "button_label": "Play Now", "action_style": "play_now", "reason": "Track uit je Spotify wachtrij."}
    context_uri = str(item.get("context_uri") or item.get("contextUri") or "").strip()
    if context_uri:
        action.update({"context_uri": context_uri, "offset_uri": uri})
    if image_url:
        action["image_url"] = register_image_proxy_url(hass, image_url) if image_url.startswith(("http://", "https://")) else image_url
    return action


def _dedupe_queue_items(items: Any) -> list[dict[str, Any]]:
    """Return queue items once, preserving Spotify queue order."""
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        title = str(item.get("title") or item.get("track_name") or item.get("name") or "").strip().lower()
        artist = str(item.get("subtitle") or item.get("artist") or item.get("artist_name") or "").strip().lower()
        key = uri or f"{title}|{artist}"
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _playback_uri(playback: dict[str, Any]) -> str:
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


async def _recently_played_history_response(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
) -> dict[str, Any]:
    window = _recently_played_window(text)
    try:
        result = await async_call_ai_tool(
            hass,
            runtime,
            "djconnect_recently_played",
            {
                "item_type": _recently_played_history_type(text),
                "limit": 50,
            },
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect recent-played unavailable: %s", exc)
        if isinstance(exc, MusicBackendCapabilityError):
            message = (
                "De gekozen muziekbackend maakt recente luistergeschiedenis "
                "niet beschikbaar voor Ask DJ."
            )
        else:
            message = (
                "Ik kan je recente Spotify-afspeelgeschiedenis nu niet ophalen. "
                "Controleer of DJConnect Spotify opnieuw gemachtigd is met de scope user-read-recently-played."
            )
        return _recently_played_response(message)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    tracks = tracks if isinstance(tracks, list) else []
    filtered = _recently_played_tracks_in_window(tracks, window)
    history_type = _recently_played_history_type(text)
    label = _recently_played_window_label(window)
    if not filtered:
        return _recently_played_response(
            _read_text('recent_empty',kind=history_type,period=label),
            history_type=history_type,
        )
    items = _recently_played_history_items(hass, filtered, history_type)
    lines = [_read_text('recent',period=label)]
    for item in items[:10]:
        lines.append(f"- {_recent_history_item_line(item)}")
    if len(items) > 10:
        lines.append('- '+_read_text('recent_more',count=len(items)-10))
    return _recently_played_response(
        "\n".join(lines),
        history_type=history_type,
        items=items[:10],
    )


def _recent_history_item_line(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    subtitle = str(item.get("subtitle") or "").strip()
    if item.get("kind") == "track" and subtitle:
        return f"{subtitle} - {title}"
    return title + (f" - {subtitle}" if subtitle else "")


def _recently_played_response(
    message: str,
    *,
    history_type: str = "tracks",
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items = items if isinstance(items, list) else []
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "message": message,
        "action": "none",
        "intent": {
            "category": "informational",
            "intent": "recently_played_history",
            "action": "recently_played",
            "item_type": history_type,
        },
        "items": items,
        "images": _recently_played_images(items),
        "links": [],
        "sources": [
            {
                "source": "spotify_recently_played",
                "kind": "source",
                "title": "Spotify recently played",
            }
        ],
    }


def _recently_played_history_type(text: str) -> str:
    normalized = _normalize(text)
    if any(term in normalized for term in ("album", "albums")):
        return "albums"
    if any(term in normalized for term in ("playlist", "playlists", "afspeellijst", "afspeellijsten")):
        return "playlists"
    if any(term in normalized for term in ("artiest", "artiesten", "artist", "artists")):
        return "artists"
    return "tracks"


def _recently_played_history_items(
    hass: HomeAssistant,
    tracks: list[dict[str, Any]],
    history_type: str,
) -> list[dict[str, Any]]:
    if history_type == "albums":
        return _recent_album_items(hass, tracks)
    if history_type == "artists":
        return _recent_artist_items(hass, tracks)
    if history_type == "playlists":
        return _recent_playlist_items(hass, tracks)
    return [_recent_track_item(hass, track) for track in tracks if isinstance(track, dict)]


def _recent_track_item(hass: HomeAssistant, track: dict[str, Any]) -> dict[str, Any]:
    title = str(track.get("track_name") or track.get("title") or track.get("name") or "Onbekende track").strip()
    artist = str(track.get("artist") or track.get("artist_name") or "").strip()
    image_url = _proxy_recent_image(hass, _track_image_url(track))
    played_at = _parse_spotify_played_at(track.get("played_at"))
    return {
        key: value
        for key, value in {
            "title": title,
            "subtitle": artist,
            "kind": "track",
            "uri": str(track.get("uri") or "").strip(),
            "image_url": image_url,
            "thumbnail_url": image_url,
            "played_at": str(track.get("played_at") or "").strip(),
            "played_at_label": _played_at_time_label(played_at) if played_at else "",
        }.items()
        if value not in (None, "", [], {})
    }


def _recent_album_items(hass: HomeAssistant, tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _dedupe_recent_items(
        (
            {
                "title": str(track.get("album_name") or track.get("album") or "Onbekend album").strip(),
                "subtitle": str(track.get("artist") or track.get("artist_name") or "").strip(),
                "kind": "album",
                "uri": str(track.get("album_uri") or track.get("context_uri") or "").strip(),
                "image_url": _proxy_recent_image(hass, _track_image_url(track)),
                "thumbnail_url": _proxy_recent_image(hass, _track_image_url(track)),
                "played_at": str(track.get("played_at") or "").strip(),
            }
            for track in tracks
            if isinstance(track, dict) and (track.get("album_name") or track.get("album"))
        ),
        key_fields=("uri", "title", "subtitle"),
    )


def _recent_artist_items(hass: HomeAssistant, tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        artists = track.get("artists")
        names = artists if isinstance(artists, list) and artists else [track.get("artist") or track.get("artist_name")]
        for name in names:
            artist = str(name or "").strip()
            if artist:
                image_url = _proxy_recent_image(hass, _track_image_url(track))
                candidates.append(
                    {
                        "title": artist,
                        "subtitle": "Artiest",
                        "kind": "artist",
                        "image_url": image_url,
                        "thumbnail_url": image_url,
                        "played_at": str(track.get("played_at") or "").strip(),
                    }
                )
    return _dedupe_recent_items(candidates, key_fields=("title",))


def _recent_playlist_items(hass: HomeAssistant, tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        uri = str(track.get("context_uri") or "").strip()
        if not uri.startswith("spotify:playlist:"):
            continue
        image_url = _proxy_recent_image(hass, _track_image_url(track))
        candidates.append(
            {
                "title": str(track.get("context_name") or "Spotify playlist").strip(),
                "subtitle": str(track.get("track_name") or track.get("title") or "").strip(),
                "kind": "playlist",
                "uri": uri,
                "image_url": image_url,
                "thumbnail_url": image_url,
                "played_at": str(track.get("played_at") or "").strip(),
            }
        )
    return _dedupe_recent_items(candidates, key_fields=("uri", "title"))


def _dedupe_recent_items(
    items: Any,
    *,
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        key = tuple(str(item.get(field) or "").strip().lower() for field in key_fields)
        key = tuple(part for part in key if part)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append({k: v for k, v in item.items() if v not in (None, "", [], {})})
    return result


def _recently_played_images(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    images = []
    for item in items:
        url = str(item.get("image_url") or item.get("thumbnail_url") or "").strip()
        if not url:
            continue
        images.append(
            {
                "url": url,
                "thumbnail_url": url,
                "title": str(item.get("title") or "").strip(),
                "subtitle": str(item.get("subtitle") or "").strip(),
                "kind": str(item.get("kind") or "recent_item"),
                "source": "spotify_recently_played",
            }
        )
    return images


def _track_image_url(track: dict[str, Any]) -> str:
    return str(
        track.get("album_image_url")
        or track.get("image_url")
        or track.get("thumbnail_url")
        or ""
    ).strip()


def _proxy_recent_image(hass: HomeAssistant, url: str) -> str:
    return register_image_proxy_url(hass, url) if url.startswith(("http://", "https://")) else url


def _recently_played_window(text: str) -> timedelta:
    normalized = _normalize(text)
    if any(term in normalized for term in ("vandaag", "today")):
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return max(timedelta(minutes=1), now - start)
    if any(
        term in normalized
        for term in (
            "afgelopen week",
            "laatste week",
            "past week",
            "last week",
        )
    ):
        return timedelta(days=7)
    if any(
        term in normalized
        for term in (
            "afgelopen dag",
            "laatste dag",
            "past day",
            "last day",
            "yesterday",
            "gisteren",
        )
    ):
        return timedelta(days=1)
    if any(term in normalized for term in ("afgelopen paar uur", "last few hours", "past few hours")):
        return timedelta(hours=3)
    match = re.search(r"(?:afgelopen|laatste|last|past)\s+(\d+)\s*(?:uur|uren|hour|hours)", normalized)
    if match:
        return timedelta(hours=max(1, min(24, int(match.group(1)))))
    if any(term in normalized for term in ("afgelopen twee uur", "laatste twee uur", "last two hours", "past two hours")):
        return timedelta(hours=2)
    return timedelta(hours=1)


def _recently_played_window_label(window: timedelta) -> str:
    seconds = int(window.total_seconds())
    if seconds <= 90 * 60:
        return _read_text('hour')
    hours = max(1, round(seconds / 3600))
    if hours >= 20:
        return _read_text('today')
    return _read_text('hours',count=hours)


def _recently_played_tracks_in_window(
    tracks: list[Any],
    window: timedelta,
) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - window
    result: list[dict[str, Any]] = []
    for item in tracks:
        if not isinstance(item, dict):
            continue
        played_at = _parse_spotify_played_at(item.get("played_at"))
        if played_at is not None and played_at < cutoff:
            continue
        result.append(item)
    return result


def _parse_spotify_played_at(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _recently_played_track_line(track: dict[str, Any]) -> str:
    title = str(track.get("track_name") or track.get("title") or track.get("name") or "Onbekende track").strip()
    artist = str(track.get("artist") or track.get("artist_name") or "").strip()
    played_at = _parse_spotify_played_at(track.get("played_at"))
    prefix = f"{_played_at_time_label(played_at)} - " if played_at is not None else ""
    return prefix + (f"{artist} - {title}" if artist else title)


def _played_at_time_label(value: datetime) -> str:
    return value.astimezone().strftime("%H:%M")


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


async def _current_track_reference_response(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    title = _playback_text(playback_context, "track_name", "title", "name")
    artist = _playback_text(playback_context, "artist", "artist_name")
    album = _playback_text(playback_context, "album_name", "album")
    if not title and not artist:
        text = _read_text('current_none')
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "images": [],
            "playback_actions": [],
            "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
        }
    # Canonical Ask DJ owns generated dialogue. A low-level current-track
    # reference has no separate model announcer or proactive publication path.
    text, generated = "", False
    paused = playback_context.get('is_playing') is False or playback_context.get('state') == 'paused'
    playing = not paused and (playback_context.get('is_playing') is True or playback_context.get('state') == 'playing')
    if not playing:
        text=_read_text('current_context',title=title or artist,
            artist_part=' — '+artist if title and artist else '',
            album_part=' · '+album if album else '')
        if paused:
            text=_read_text('paused')+text
    if not text:
        if title and artist and album:
            text = _read_text('current_full',title=title,artist=artist,album=album)
        elif title and artist:
            text = _read_text('current_pair',title=title,artist=artist)
        else:
            text = _read_text('current_single',title=_track_label(playback_context) or title or artist)
        generated = False
    images = _images_from_context(hass, {}, playback_context)
    uri = str(playback_context.get("uri") or playback_context.get("track_uri") or "").strip()
    playback_actions: list[dict[str, Any]] = []
    if uri.startswith("spotify:track:"):
        action: dict[str, Any] = {
            "id": uri,
            "title": title,
            "subtitle": artist,
            "uri": uri,
            "kind": "track",
            "action_style": "play_now",
            "label": "Play Now",
            "button_label": "Play Now",
            "reason": _read_text('current_reason'),
        }
        if images:
            action["image_url"] = images[0]["url"]
        playback_actions.append(action)
    more_artist_action = _artist_more_media_action(artist)
    if more_artist_action:
        playback_actions.append(more_artist_action)
    favorite_action = _favorite_current_track_action(title, artist, playback_context)
    if favorite_action:
        playback_actions.append(favorite_action)
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "text_source": "generated" if generated else "fallback",
        "is_generated_text": generated,
        "action": "none",
        "images": images,
        "playback_actions": playback_actions,
        "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
    }




def _favorite_current_track_action(
    title: str,
    artist: str,
    playback_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not title and not artist:
        return {}
    favorite_status = _playback_favorite_status(playback_context or {})
    target_favorite = False if favorite_status is True else True
    label = "Haal uit favorieten" if favorite_status is True else "Zet in favorieten"
    prompt = (
        "Haal huidig nummer uit favorieten"
        if favorite_status is True
        else "Zet huidig nummer in favorieten"
    )
    state = "on" if favorite_status is True else "off" if favorite_status is False else "unknown"
    return {
        "id": "djconnect:control:current_track_favorite",
        "kind": "control",
        "action_style": "control",
        "command": "set_current_track_favorite",
        "value": target_favorite,
        "title": label,
        "label": label,
        "button_label": label,
        "prompt": prompt,
        "client_prompt": prompt,
        "toggle": True,
        "toggle_state": state,
        "favorite_status": favorite_status,
        "target_favorite_status": target_favorite,
        "reason": (
            "Haal de huidige Spotify-track uit Liked Songs/favorieten."
            if favorite_status is True
            else "Voeg de huidige Spotify-track toe aan Liked Songs/favorieten."
        ),
    }


def _playback_favorite_status(playback_context: Any) -> bool | None:
    if not isinstance(playback_context, dict):
        return None
    for container in (
        playback_context,
        playback_context.get("track") if isinstance(playback_context.get("track"), dict) else {},
        playback_context.get("item") if isinstance(playback_context.get("item"), dict) else {},
    ):
        if not isinstance(container, dict):
            continue
        for key in (
            "is_liked",
            "liked",
            "is_saved",
            "saved",
            "is_favorite",
            "favorite",
            "in_library",
            "is_in_library",
            "liked_song",
            "is_liked_song",
        ):
            value = container.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"true", "1", "yes", "ja", "on", "liked", "saved"}:
                    return True
                if normalized in {"false", "0", "no", "nee", "off", "unliked", "unsaved"}:
                    return False
    return None


def _current_track_album_response(
    hass: HomeAssistant,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    title = _playback_text(playback_context, "track_name", "title", "name")
    artist = _playback_text(playback_context, "artist", "artist_name")
    album = _playback_text(playback_context, "album_name", "album")
    year = _playback_release_year(playback_context)
    album_label = f"{album} (uit {year})" if album and year else album
    if not album:
        text = "Ik kan nu niet zien op welk album dit nummer staat."
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "images": [],
            "playback_actions": [],
        }
    if title and artist:
        text = f"{title} van {artist} werd uitgebracht op {album_label}."
    elif title:
        text = f"{title} werd uitgebracht op {album_label}."
    else:
        text = f"Dit nummer staat op {album_label}."
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": _images_from_context(hass, {}, playback_context),
        "playback_actions": [_current_album_playback_action(hass, playback_context)] if _current_album_uri(playback_context) else [],
        "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
    }


async def _play_current_album_response(
    hass: HomeAssistant,
    runtime: Any,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    album = _playback_text(playback_context, "album_name", "album")
    artist = _playback_text(playback_context, "artist", "artist_name")
    uri = _current_album_uri(playback_context)
    if not uri and album:
        uri = await _search_current_album_uri(hass, runtime, album, artist)
    if not album:
        text = "Ik weet nog niet welk album je bedoelt."
        return {"success": True, "text": text, "dj_text": text, "action": "none"}
    if not uri:
        text = f"Ik weet dat dit {album} is, maar ik kan de Spotify album-URI nu niet vinden."
        return {"success": True, "text": text, "dj_text": text, "action": "none"}
    result = await run_music_command(hass, runtime, "play", uri, play=True)
    text = f"{album} is in je wachtrij gezet."
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "play_music",
        "playback": result.get("playback") if isinstance(result, dict) else {},
        "playback_actions": [],
        "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
    }


async def _play_album_containing_track_response(
    hass: HomeAssistant,
    runtime: Any,
    request: dict[str, str],
) -> dict[str, Any]:
    track = str(request.get("track") or "").strip()
    artist = str(request.get("artist") or "").strip()
    if not track or not artist:
        text = "Welk nummer en welke artiest bedoel je?"
        return {"success": True, "text": text, "dj_text": text, "action": "none"}
    try:
        result = await run_music_command(
            hass,
            runtime,
            "search_media",
            {"query": f"{track} {artist}", "type": "track"},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect album-by-track search failed: %s", exc)
        text = f"Ik kan het album met {track} van {artist} nu niet vinden."
        return {"success": True, "text": text, "dj_text": text, "action": "none"}
    item = result.get("item") if isinstance(result, dict) else {}
    if not isinstance(item, dict):
        item = {}
    album = _playback_text(item, "album_name", "album")
    uri = _current_album_uri(item)
    if not uri:
        uri = str(item.get("album_uri") or "").strip()
    if not album:
        album = "dat album"
    if not uri.startswith("spotify:album:"):
        text = f"Ik vond {track} van {artist}, maar niet de Spotify album-URI."
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "sources": [{"source": "spotify_search", "title": "Spotify search", "kind": "source"}],
        }
    playback = await run_music_command(hass, runtime, "play", uri, play=True)
    text = f"{album} is in je wachtrij gezet."
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "play_music",
        "playback": playback.get("playback") if isinstance(playback, dict) else {},
        "sources": [{"source": "spotify_search", "title": "Spotify search", "kind": "source"}],
    }


def _track_versions_search_request(text: str) -> str:
    normalized = _normalize(text)
    if not normalized:
        return ""
    if not any(
        term in normalized
        for term in (
            "uitvoering",
            "uitvoeringen",
            "versie",
            "versies",
            "version",
            "versions",
            "cover",
            "covers",
            "remix",
            "remixes",
            "live",
            "akoestisch",
            "acoustic",
            "opname",
            "recording",
        )
    ):
        return ""
    if not re.search(r"\b(?:zoek|vind|geef|toon|laat\s+zien|doe\s+me|heb\s+je|find|show|give)\b", normalized):
        return ""
    value = str(text or "").strip()
    quoted = re.search(r"[\"'“”‘’](.+?)[\"'“”‘’]", value)
    if quoted:
        return _clean_track_versions_query(quoted.group(1))
    for pattern in (
        r"(?:van|voor|of)\s+(.+?)\s*$",
        r"(?:called|named|titled)\s+(.+?)\s*$",
    ):
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        query = _clean_track_versions_query(match.group(1))
        if query:
            return query
    return ""


def _clean_track_versions_query(value: str) -> str:
    cleaned = re.sub(
        r"\b(?:max(?:imaal)?|maximum|top)\s+\d+\s*(?:resultaten|results)?\b",
        " ",
        str(value or ""),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:door|by)\s+(?:verschillende|different|meerdere|multiple)\s+(?:artiesten|artists)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:mag|may|can)\s+(?:van|by)\s+(?:dezelfde|same|verschillende|different).*$",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:remix(?:es)?|live|akoestisch(?:e)?|acoustic|cover(?:s)?|uitvoering(?:en)?|versie(?:s)?|version(?:s)?)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ?.!'\"“”‘’")
    return cleaned if _track_versions_required_words(cleaned) else ""


async def _track_versions_search_response(
    hass: HomeAssistant,
    runtime: Any,
    query: str,
) -> dict[str, Any]:
    required_words = _track_versions_required_words(query)
    result = await _spotify_track_search(hass, runtime, query, limit=10)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    candidates = _track_versions_candidates(tracks, required_words)
    actions = _track_recommendation_actions(hass, candidates, limit=10, runtime=runtime)
    if actions:
        lines = [
            f"{index}. {action.get('title') or 'Onbekend nummer'}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(actions, start=1)
        ]
        text = (
            f"Ik vond deze uitvoeringen voor {query}. "
            "Ik start nog niets; tik op Play Now om er eentje te horen:\n"
            + "\n".join(lines)
        )
    else:
        text = f"Ik vond nu geen duidelijke uitvoeringen waarbij alle woorden uit {query} terugkomen."
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": [],
        "items": actions,
        "playback_actions": actions,
        "sources": [{"source": "spotify_track_search", "title": "Spotify track search", "kind": "source"}],
    }


def _track_versions_required_words(query: str) -> list[str]:
    normalized = re.sub(r"[^a-z0-9À-ÿ]+", " ", _normalize(query))
    words: list[str] = []
    for word in normalized.split():
        if len(word) < 2 or word in {"the", "de", "het", "een", "and", "en"}:
            continue
        if word not in words:
            words.append(word)
    return words


def _track_versions_candidates(tracks: Any, required_words: list[str]) -> list[dict[str, Any]]:
    if not isinstance(tracks, list) or not required_words:
        return []
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in tracks:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        if not uri.startswith("spotify:track:") or uri in seen:
            continue
        haystack = _normalize(
            " ".join(
                str(item.get(key) or "")
                for key in (
                    "track_name",
                    "title",
                    "name",
                    "album_name",
                    "album",
                    "artist",
                    "artist_name",
                    "subtitle",
                )
            )
        )
        haystack = re.sub(r"[^a-z0-9À-ÿ]+", " ", haystack)
        if all(re.search(rf"\b{re.escape(word)}\b", haystack) for word in required_words):
            seen.add(uri)
            selected.append(item)
        if len(selected) >= 10:
            break
    return selected


async def _current_track_version_response(
    hass: HomeAssistant,
    runtime: Any,
    playback_context: dict[str, Any],
    variant: str,
) -> dict[str, Any]:
    title = _playback_text(playback_context, "track_name", "title", "name")
    artist = _playback_text(playback_context, "artist", "artist_name")
    variant_label = _version_variant_label(variant)
    if not title:
        text = f"Ik weet nu niet van welk nummer je een {variant_label} zoekt."
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "images": [],
            "items": [],
            "playback_actions": [],
        }
    query = f"{title} {artist} {_version_variant_search_term(variant)}".strip()
    result = await _spotify_track_search(hass, runtime, query, limit=10)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    variant_tracks = _version_track_candidates(tracks, title, artist, variant)
    actions = _track_recommendation_actions(hass, variant_tracks, limit=5, runtime=runtime)
    label = f"{title} van {artist}" if artist else title
    if actions:
        lines = [
            f"{index}. {action.get('title') or variant_label.capitalize()}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(actions, start=1)
        ]
        text = (
            f"Ik vond deze {_version_variant_plural_label(variant)} voor {label}. "
            "Ik start nog niets; tik op Play Now om er eentje te horen:\n"
            + "\n".join(lines)
        )
    else:
        text = f"Ik vond nu geen duidelijke {variant_label} van {label} op Spotify."
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": [],
        "items": actions,
        "playback_actions": actions,
        "sources": [{"source": "spotify_track_search", "title": "Spotify track search", "kind": "source"}],
    }


def _version_track_candidates(tracks: Any, title: str, artist: str, variant: str) -> list[dict[str, Any]]:
    if not isinstance(tracks, list):
        return []
    normalized_title = _normalize(_strip_version_markers(title))
    normalized_artist = _normalize(artist)
    ranked: list[tuple[int, dict[str, Any]]] = []
    seen: set[str] = set()
    for item in tracks:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        if not uri.startswith("spotify:track:") or uri in seen:
            continue
        candidate_title = _playback_text(item, "track_name", "title", "name")
        candidate_artist = _playback_text(item, "artist", "artist_name")
        candidate_album = _playback_text(item, "album_name", "album")
        haystack = _normalize(f"{candidate_title} {candidate_album}")
        if not _contains_version_marker(haystack, variant):
            continue
        score = 10
        if normalized_title and normalized_title in _normalize(_strip_version_markers(candidate_title)):
            score += 10
        if normalized_artist and normalized_artist in _normalize(candidate_artist):
            score += 5
        title_haystack = _normalize(candidate_title)
        album_haystack = _normalize(candidate_album)
        if _contains_version_marker(title_haystack, variant):
            score += 3
        if _contains_version_marker(album_haystack, variant):
            score += 1
        seen.add(uri)
        ranked.append((score, item))
    ranked.sort(key=lambda entry: entry[0], reverse=True)
    return [item for _, item in ranked]


def _version_variant_label(variant: str) -> str:
    if variant == "acoustic":
        return "akoestische versie"
    if variant == "remix":
        return "remix"
    return "live-versie"


def _version_variant_plural_label(variant: str) -> str:
    if variant == "acoustic":
        return "akoestische versies"
    if variant == "remix":
        return "remixes"
    return "live-versies"


def _version_variant_search_term(variant: str) -> str:
    if variant == "acoustic":
        return "acoustic unplugged"
    if variant == "remix":
        return "remix"
    return "live"


def _contains_version_marker(value: str, variant: str) -> bool:
    normalized = _normalize(value)
    markers = {
        "live": (
            "live",
            "session",
            "sessions",
            "bbc",
            "mtv",
            "concert",
            "at ",
            "from ",
        ),
        "acoustic": (
            "acoustic",
            "akoestisch",
            "unplugged",
            "stripped",
            "session",
            "sessions",
        ),
        "remix": (
            "remix",
            "remixed",
            "mix",
            "edit",
            "club",
            "extended",
        ),
    }.get(variant, ())
    return any(marker in normalized for marker in markers)


def _strip_version_markers(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\s*[-–—]\s*(?:live|acoustic|akoestisch|unplugged|session|sessions|remix|remixed|mix|edit|extended|club|remaster(?:ed)?|radio edit|single version).*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\((?:live|acoustic|akoestisch|unplugged|session|sessions|remix|remixed|mix|edit|extended|club|remaster(?:ed)?|radio edit|single version)[^)]+\)", "", text, flags=re.IGNORECASE)
    return text.strip()


async def _track_owner_response(
    hass: HomeAssistant,
    runtime: Any,
    track_query: str,
) -> dict[str, Any]:
    query = str(track_query or "").strip()
    if not query:
        text = "Welk nummer bedoel je?"
        return {"success": True, "text": text, "dj_text": text, "action": "none"}
    try:
        result = await run_music_command(
            hass,
            runtime,
            "search_media",
            {"query": query, "type": "track"},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect track owner search failed: %s", exc)
        text = f"Ik kan nu niet betrouwbaar vinden van wie {query} is."
        return {"success": True, "text": text, "dj_text": text, "action": "none"}
    item = result.get("item") if isinstance(result, dict) else {}
    if not isinstance(item, dict) or not item:
        text = f"Ik vind nu geen betrouwbare Spotify-match voor {query}."
        return {"success": True, "text": text, "dj_text": text, "action": "none"}
    title = _playback_text(item, "track_name", "title", "name") or query
    artist = _playback_text(item, "artist", "artist_name")
    album = _playback_text(item, "album_name", "album")
    if artist and album:
        text = f"{title} is gemaakt door {artist}, uitgebracht op {album}."
    elif artist:
        text = f"{title} is gemaakt door {artist}."
    else:
        text = f"Ik vond {title}, maar Spotify gaf geen duidelijke artiest terug."
    actions = _track_and_album_actions_from_track_item(hass, item)
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "playback_actions": actions,
        "images": _images_from_context(hass, item, {}),
        "sources": [{"source": "spotify_search", "title": "Spotify search", "kind": "source"}],
    }


def _track_and_album_actions_from_track_item(
    hass: HomeAssistant,
    item: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    track_uri = str(item.get("uri") or item.get("track_uri") or "").strip()
    album_uri = _current_album_uri(item) or str(item.get("album_uri") or "").strip()
    image_url = _playback_text(
        item,
        "album_image_url",
        "image_url",
        "thumbnail_url",
        "media_image_url",
    )
    if image_url.startswith(("http://", "https://")):
        image_url = register_image_proxy_url(hass, image_url)
    title = _playback_text(item, "track_name", "title", "name")
    artist = _playback_text(item, "artist", "artist_name")
    album = _playback_text(item, "album_name", "album")
    if track_uri.startswith("spotify:track:"):
        action: dict[str, Any] = {
            "id": track_uri,
            "title": title or track_uri,
            "subtitle": artist,
            "uri": track_uri,
            "kind": "track",
            "label": "Play Now",
            "button_label": "Play Now",
            "action_style": "play_now",
            "image_url": image_url,
            "reason": "Gevonden track.",
        }
        if album_uri.startswith("spotify:album:"):
            action["context_uri"] = album_uri
            action["offset_uri"] = track_uri
        actions.append({key: value for key, value in action.items() if value not in ("", None)})
    if album_uri.startswith("spotify:album:"):
        actions.append(
            {
                key: value
                for key, value in {
                    "id": album_uri,
                    "title": album or album_uri,
                    "subtitle": artist,
                    "uri": album_uri,
                    "context_uri": album_uri,
                    "kind": "album",
                    "label": "Play Now",
                    "button_label": "Play Now",
                    "action_style": "play_now",
                    "image_url": image_url,
                    "reason": "Album waarop de gevonden track staat.",
                }.items()
                if value not in ("", None)
            }
        )
    return actions


async def _search_current_album_uri(
    hass: HomeAssistant,
    runtime: Any,
    album: str,
    artist: str,
) -> str:
    query = f"{album} {artist}".strip()
    if not query:
        return ""
    try:
        result = await run_music_command(
            hass,
            runtime,
            "search_media",
            {"query": query, "type": "album"},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect current album search failed: %s", exc)
        return ""
    item = result.get("item") if isinstance(result, dict) else {}
    uri = str(item.get("uri") or item.get("album_uri") or "").strip() if isinstance(item, dict) else ""
    return uri if uri.startswith("spotify:album:") else ""


def _current_album_playback_action(
    hass: HomeAssistant,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    uri = _current_album_uri(playback_context)
    album = _playback_text(playback_context, "album_name", "album") or uri
    artist = _playback_text(playback_context, "artist", "artist_name")
    year = _playback_release_year(playback_context)
    subtitle = f"{artist} · {year}" if artist and year else artist or year
    image_url = _playback_text(
        playback_context,
        "album_image_url",
        "image_url",
        "thumbnail_url",
        "media_image_url",
    )
    if image_url.startswith(("http://", "https://")):
        image_url = register_image_proxy_url(hass, image_url)
    return {
        key: value
        for key, value in {
            "id": uri,
            "title": album,
            "subtitle": subtitle,
            "uri": uri,
            "kind": "album",
            "label": "Play Now",
            "button_label": "Play Now",
            "action_style": "play_now",
            "image_url": image_url,
            "reason": "Album van de huidige track.",
        }.items()
        if value not in ("", None)
    }


def _playback_release_year(playback_context: dict[str, Any]) -> str:
    for key in (
        "album_release_date",
        "album_release_year",
        "release_date",
        "release_year",
        "released_at",
    ):
        year = _year_from_value(playback_context.get(key))
        if year:
            return year
    album = playback_context.get("album")
    if isinstance(album, dict):
        for key in ("release_date", "release_year", "released_at"):
            year = _year_from_value(album.get(key))
            if year:
                return year
    return ""


def _year_from_value(value: Any) -> str:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
    return match.group(1) if match else ""


def _current_album_uri(playback_context: dict[str, Any]) -> str:
    for key in ("album_uri", "albumUri", "context_uri", "contextUri", "queue_context"):
        value = str(playback_context.get(key) or "").strip()
        if value.startswith("spotify:album:"):
            return value
    album = playback_context.get("album")
    if isinstance(album, dict):
        for key in ("uri", "album_uri", "albumUri"):
            value = str(album.get(key) or "").strip()
            if value.startswith("spotify:album:"):
                return value
    return ""


def _playback_text(playback_context: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(playback_context.get(key) or "").strip()
        if value:
            return value
    return ""


async def _spotify_related_artists(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    try:
        result = await run_music_command(
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
        result = await run_music_command(
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


def _artist_albums_response(
    hass: HomeAssistant,
    discography: dict[str, Any],
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    albums = discography.get("albums") if isinstance(discography, dict) else []
    if not isinstance(albums, list) or not albums:
        return _empty_artist_albums_response(discography)
    artist = str(discography.get("artist") or albums[0].get("artist") or "deze artiest").strip()
    visible_limit = max(1, min(20, int(limit))) if limit is not None else 20
    visible_albums = albums[:visible_limit]
    album_labels = _artist_album_labels(visible_albums)
    text = _artist_albums_text(artist, album_labels, len(albums))
    images = _artist_album_images(visible_albums)
    playback_actions = _artist_album_playback_actions(hass, artist, visible_albums)
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": images,
        "items": playback_actions,
        "playback_actions": playback_actions,
        "sources": [{"source": "spotify_artist_albums", "title": "Spotify artist albums", "kind": "source"}],
    }


def _empty_artist_albums_response(discography: dict[str, Any]) -> dict[str, Any]:
    artist = str(discography.get("artist") or "deze artiest").strip()
    text = _read_text('albums_empty',artist=artist)
    return {"success": True, "text": text, "dj_text": text, "action": "none", "sources": [_spotify_artist_albums_source()]}


def _spotify_artist_albums_source() -> dict[str, str]:
    return {"source": "spotify_artist_albums", "title": "Spotify artist albums", "kind": "source"}


def _artist_album_labels(albums: list[Any]) -> list[str]:
    labels = []
    for album in albums:
        if not isinstance(album, dict):
            continue
        title = str(album.get("name") or album.get("title") or "").strip()
        year = str(album.get("release_date") or "").strip()[:4]
        if title:
            labels.append(f"- {title} ({year})" if year else f"- {title}")
    return labels


def _artist_albums_text(artist: str, labels: list[str], total: int) -> str:
    if not labels:
        return _read_text('album_titles_empty',artist=artist)
    extra_count = total - len(labels)
    suffix = "" if extra_count <= 0 else (
        '\n\n'+_read_text('albums_more',count=extra_count)
    )
    return (
        _read_text('albums',artist=artist)+'\n\n'
        f"{chr(10).join(labels)}{suffix}\n\n"+_read_text('album_play_hint')
    )


def _artist_album_images(albums: list[Any]) -> list[dict[str, str]]:
    return [{"url": str(album.get("image_url") or album.get("album_image_url") or ""), "title": str(album.get("name") or album.get("title") or "Album"), "subtitle": str(album.get("release_date") or ""), "kind": "album_art", "source": "spotify"} for album in albums if isinstance(album, dict) and (album.get("image_url") or album.get("album_image_url"))]


def _artist_album_playback_actions(
    hass: HomeAssistant, artist: str, albums: list[Any],
) -> list[dict[str, Any]]:
    actions = []
    for album in albums:
        action = _artist_album_playback_action(hass, artist, album)
        if action:
            actions.append(action)
    return actions


def _artist_album_playback_action(
    hass: HomeAssistant, artist: str, album: Any,
) -> dict[str, Any]:
    if not isinstance(album, dict):
        return {}
    uri = str(album.get("uri") or album.get("album_uri") or "").strip()
    if not uri.startswith("spotify:album:"):
        return {}
    release_date = str(album.get("release_date") or "").strip()
    image_url = str(album.get("image_url") or album.get("album_image_url") or "").strip()
    action = {"id": uri, "title": str(album.get("name") or album.get("title") or "Album").strip(), "subtitle": f"{artist} · {release_date[:4]}" if release_date[:4] else artist, "uri": uri, "context_uri": uri, "kind": "album", "label": "Play Now", "button_label": "Play Now", "action_style": "play_now", "reason": f"Album van {artist}."}
    action["release_date"] = release_date
    action["artist"] = artist
    if image_url:
        action["image_url"] = register_image_proxy_url(hass, image_url) if image_url.startswith(("http://", "https://")) else image_url
    return action


def _related_artists_response(
    related: dict[str, Any],
    memory_context: dict[str, Any] | None = None,
    listening_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artists = related.get("artists") if isinstance(related, dict) else []
    if not isinstance(artists, list) or not artists:
        return _empty_related_artists_response(related)
    source_artist = str(related.get("artist") or "deze artiest").strip()
    visible = artists[:12]
    labels = _related_artist_labels(visible)
    profile_hint = _profile_artist_hint(memory_context or {}, listening_profile or {})
    text = _related_artists_text(source_artist, labels, profile_hint)
    images = _related_artist_images(visible)
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "none",
        "images": images,
        "sources": [
            {"source": "spotify_related_artists", "title": "Spotify related artists", "kind": "source"},
            *(_profile_sources(memory_context or {}, listening_profile or {}) if profile_hint else []),
        ],
    }


def _spotify_related_artists_source() -> dict[str, str]:
    return {"source": "spotify_related_artists", "title": "Spotify related artists", "kind": "source"}


def _empty_related_artists_response(related: dict[str, Any]) -> dict[str, Any]:
    artist = str(related.get("artist") or "deze artiest").strip()
    text = f"Ik vind via Spotify geen vergelijkbare artiesten voor {artist}."
    return {"success": True, "text": text, "dj_text": text, "action": "none", "sources": [_spotify_related_artists_source()]}


def _related_artist_labels(artists: list[Any]) -> list[str]:
    return [str(item.get("name") or item.get("title") or "").strip() for item in artists if isinstance(item, dict) and str(item.get("name") or item.get("title") or "").strip()]


def _related_artists_text(source_artist: str, labels: list[str], profile_hint: str) -> str:
    if not labels:
        return f"Ik vind via Spotify geen bruikbare vergelijkbare artiesten voor {source_artist}."
    text = f"Volgens Spotify zitten deze artiesten in dezelfde muzikale buurt als {source_artist}: {', '.join(labels)}."
    return f"{profile_hint} {text}" if profile_hint else text


def _related_artist_images(artists: list[Any]) -> list[dict[str, str]]:
    return [{"url": str(item.get("image_url") or item.get("artist_image_url") or ""), "title": str(item.get("name") or item.get("title") or "Artiest"), "subtitle": ", ".join(str(genre) for genre in (item.get("genres") or [])[:3]), "kind": "artist_image", "source": "spotify"} for item in artists if isinstance(item, dict) and (item.get("image_url") or item.get("artist_image_url"))]


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
    if "album" not in normalized and not any(term in normalized for term in ("uitgebracht", "released", "release")):
        return ""
    patterns = (
        r"^\s*(?:geef|toon|laat\s+zien|show|give)\s+(?:me|mij)?\s*(?:de\s+)?albums\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*welke\s+albums\s+(?:heeft|hebben)\s+(.+?)\s+(?:allemaal\s+)?(?:uitgebracht|gemaakt|released)\s*\??\s*$",
        r"^\s*welke\s+albums\s+(?:heeft|hebben)\s+(.+?)\s*\??\s*$",
        r"^\s*wat\s+(?:heeft|hebben)\s+(.+?)\s+(?:allemaal\s+)?(?:uitgebracht|gereleased|released)\s*\??\s*$",
        r"^\s*welke\s+albums\s+bracht\s+(.+?)\s+uit\s*\??\s*$",
        r"^\s*welke\s+albums\s+zijn\s+er\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*albums\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*which\s+albums\s+(?:has|have)\s+(.+?)\s+released\s*\??\s*$",
        r"^\s*what\s+(?:has|have)\s+(.+?)\s+released\s*\??\s*$",
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
            "dit",
            "dit nummer",
            "deze track",
            "deze song",
            "deze muziek",
            "de huidige track",
            "het huidige nummer",
            "wat nu speelt",
            "nu speelt",
            "this",
            "this track",
            "this song",
            "this artist",
            "current artist",
            "current track",
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
        r"^\s*wat\s+voor\s+genre\s+is\s+(.+?)\s*\??\s*$",
        r"^\s*welk(?:e)?\s+genre\s+is\s+(.+?)\s*\??\s*$",
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
            if _normalize(artist) in {
                "dit",
                "dit nummer",
                "deze track",
                "deze song",
                "deze muziek",
                "deze artiest",
                "die artiest",
                "huidige artiest",
                "het huidige nummer",
                "de huidige track",
                "wat nu speelt",
                "this",
                "this track",
                "this song",
                "this artist",
                "current track",
                "current artist",
            }:
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
            "speelt metallica binnenkort",
            "wanneer komt",
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
    # A concert word inside a broad story is not a request for the current
    # performer's agenda. Only an explicit name/deictic query grants this fast
    # route; other phrasing belongs to the guarded semantic research owner.
    return ""


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


def _artist_from_more_tracks_question(
    text: str,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
) -> str:
    normalized = _normalize(text)
    if not _is_artist_more_tracks_question(normalized):
        return ""
    explicit = _explicit_artist_from_more_tracks_question(text)
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
            "current artist",
            "this artist",
            "that artist",
            "this band",
        )
    ):
        return _artist_from_playback_context(playback_context)
    return _artist_from_server_history_context(memory_context) or _artist_from_recent_context(memory_context) or _artist_from_playback_context(playback_context)


def _explicit_artist_from_more_tracks_question(text: str) -> str:
    patterns = (
        r"^\s*welke\s+(?:nummers|tracks|songs|muziek|music)\s+(?:heb\s+je|hebt\s+je|ken\s+je|have\s+you|do\s+you\s+have)\s+(?:van|by|from)\s+(.+?)\s*\??\s*$",
        r"^\s*wat\s+heb\s+je\s+(?:nog\s+)?meer\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*meer\s+(?:nummers|songs|tracks|muziek|music)\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*(?:(?:heb\s+je|geef)\s+)?(?:nog\s+)?meer\s+(?:nummers|songs|tracks|muziek|music)\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*(?:show\s+me\s+|give\s+me\s+)?more\s+(?:tracks|songs|music)\s+(?:by|from)\s+(.+?)\s*\??\s*$",
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
                "current artist",
                "this artist",
                "that artist",
                "this band",
            }:
                return ""
            return artist
    return ""


def _is_artist_more_tracks_question(normalized: str) -> bool:
    if any(
        phrase in normalized
        for phrase in (
            "wat heb je nog meer van",
            "wat heb je meer van",
            "nog meer van",
            "meer nummers van",
            "meer muziek van",
            "more tracks by",
            "more songs by",
            "more music by",
        )
    ):
        return True
    return bool(
        re.search(
            r"\bwelke\s+(?:nummers|tracks|songs|muziek)\s+(?:heb\s+je|hebt\s+je|ken\s+je)\b",
            normalized,
        )
        or re.search(r"\b(?:what|which)\s+(?:tracks|songs|music)\s+(?:do\s+you\s+have|have\s+you)\b", normalized)
    )


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
            or _artist_from_history_text(text)
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
                or _artist_from_history_text(text)
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
            or _artist_from_history_text(text)
        )
        if artist:
            return artist
    return ""


def _artist_from_history_text(text: str) -> str:
    value = str(text or "").strip()
    patterns = (
        r"^\s*(?:speel|draai|zet)\s+(.+?)\s*\??\s*$",
        r"^\s*(?:play|put\s+on)\s+(.+?)\s*\??\s*$",
        r"^\s*daar\s+is\s+(.+?)(?:\.|!|\s*$)",
        r"^\s*here\s+is\s+(.+?)(?:\.|!|\s*$)",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        artist = _clean_artist_name(match.group(1))
        if _normalize(artist) in {
            "iets",
            "wat",
            "muziek",
            "music",
            "something",
            "some",
            "een nummer",
            "a song",
        }:
            continue
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


def _is_current_artist_info_question(text: str) -> bool:
    normalized = _normalize(text)
    if not any(
        phrase in normalized
        for phrase in (
            "deze artiest",
            "die artiest",
            "huidige artiest",
            "deze band",
            "die band",
            "this artist",
            "that artist",
            "current artist",
            "this band",
            "that band",
        )
    ):
        return False
    if any(term in normalized for term in ("album", "playlist", "nummer", "track", "concert", "genre", "muziek maakt")):
        return False
    return any(
        phrase in normalized
        for phrase in (
            "vertel",
            "iets over",
            "meer over",
            "wie is",
            "wie zijn",
            "info",
            "informatie",
            "tell",
            "about",
            "who is",
            "who are",
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
    music_dna_key: str | None,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    text = str(result.get("dj_text") or result.get("text") or result.get("message") or "").strip() or "Home Assistant gaf geen antwoord."
    images = _normalized_response_images(hass, result, classification, playback_context)
    links = _links_from_context(result, playback_context, classification)
    sources = _sources_from_context(result, links)
    action = result.get("action") or classification.action
    confirmation_actions = result.get("confirmation_actions") or _confirmation_actions_from_playback_actions(result.get("playback_actions"))
    return _normalized_response_payload(result, classification, music_dna_key, playback_context, text, images, links, sources, action, confirmation_actions)


def _normalized_response_images(
    hass: HomeAssistant, result: dict[str, Any], classification: AskDjIntent, playback_context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Resolve explicit images or the permitted playback-context fallback."""
    context = playback_context if _should_use_playback_context_images(result, classification) and "images" not in result else {}
    return _images_from_context(hass, result, context)


def _normalized_response_payload(
    result: dict[str, Any], classification: AskDjIntent, music_dna_key: str | None,
    playback_context: dict[str, Any], text: str, images: list[dict[str, Any]],
    links: list[dict[str, Any]], sources: list[dict[str, Any]], action: Any,
    confirmation_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the stable normalized Ask DJ response contract."""
    result_intent = result.get("intent") if isinstance(result.get("intent"), dict) else {}
    generated_text = result.get("is_generated_text")
    text_source = str(result.get("text_source") or "").strip()
    text_generation_fields = {
        **({"text_source": text_source} if text_source else {}),
        **({"is_generated_text": bool(generated_text)} if generated_text is not None else {}),
    }
    response = {
        "success": bool(result.get("success", True)),
        "text": text,
        "dj_text": text,
        "message": text,
        **text_generation_fields,
        **{key: result[key] for key in ("model_processing_basis", "knowledge_basis", "public_research_status", "research_answer_qualification", "action_outcome", "analysis_basis",
            "queue_observation", "queue_append", "session_forecast", "previous_observation", "_private_current_context", "_catalogue_history_caption", "playback_projection_receipt", "playback_outcome") if key in result},
        "images": images,
        "links": links,
        "sources": sources,
        "playback_actions": result.get("playback_actions") or [],
        "confirmation_actions": confirmation_actions,
        "error": result.get("error"),
        "intent": {
            "category": result_intent.get("category") or classification.category,
            "intent": result_intent.get("intent") or classification.intent,
            **(
                {"action": result_intent.get("action") or action}
                if result_intent.get("action") or action
                else {}
            ),
            **(
                {"item_type": result_intent["item_type"]}
                if result_intent.get("item_type")
                else {}
            ),
        },
        **({"analysis": result.get("analysis")} if isinstance(result.get("analysis"), dict) else {}),
        **({"track_insight": result.get("track_insight")} if isinstance(result.get("track_insight"), dict) else {}),
        **({"type": result.get("type")} if result.get("type") else {}),
        **({"open_screen": result.get("open_screen")} if result.get("open_screen") else {}),
        "items": result.get("items") or [],
        "action": action,
        "music_dna_key": music_dna_key,
        "playback": result.get("playback") or playback_context,
        "assistant_message": {
            "role": "assistant",
            "message_kind": str(result.get("message_kind") or "assistant"),
            "origin": str(result.get("origin") or ""),
            "text": text,
            **text_generation_fields,
            **({"research_answer_qualification": result["research_answer_qualification"]}
               if result.get("research_answer_qualification") in {"supported_prefix_v1"} else {}),
            "images": images,
            "links": links,
            "sources": sources,
            "items": result.get("items") or [],
            **({"analysis": result.get("analysis")} if isinstance(result.get("analysis"), dict) else {}),
            **({"track_insight": result.get("track_insight")} if isinstance(result.get("track_insight"), dict) else {}),
            **({"open_screen": result.get("open_screen")} if result.get("open_screen") else {}),
            "playback_actions": result.get("playback_actions") or [],
            "confirmation_actions": confirmation_actions,
        },
    }
    return response


def _should_use_playback_context_images(result: dict[str, Any], classification: AskDjIntent) -> bool:
    if classification.intent in {
        "current_track_info",
        "current_track_album",
        "current_track_reference",
        "dj_announcement",
    }:
        return True
    if result.get("source") == "spotify_playback_context":
        return True
    sources = result.get("sources")
    if isinstance(sources, list) and any(
        isinstance(source, dict) and source.get("source") == "spotify_playback_context"
        for source in sources
    ):
        return True
    return any(isinstance(result.get(key), dict) for key in ("playback", "media", "resolved_media", "track"))


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
        "waar ik naar luister",
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


def _is_track_insight_analysis_request(normalized: str) -> bool:
    """Return true for analysis questions about the current track."""
    track_terms = (
        "dit nummer",
        "deze track",
        "deze plaat",
        "dit",
        "wat speelt",
        "nummer dat nu speelt",
        "track die nu speelt",
        "current track",
        "this track",
        "this song",
        "playing now",
        "now playing",
    )
    technical_terms = (
        "analyseer",
        "analyze",
        "technische analyse",
        "track analyse",
        "trackanalyse",
        "analyseer technisch",
        "analyseer de opbouw",
        "opbouw",
        "tempo",
        "maatsoort",
        "instrumenten",
        "instrumentatie",
        "melodische opbouw",
        "melodie",
        "intro",
        "couplet",
        "coupletten",
        "refrein",
        "bridge",
        "drop",
        "breakdown",
        "song structure",
        "technical analysis",
        "track analysis",
        "maakt dit nummer bijzonder",
        "makes this track special",
        "inzicht",
        "arrangement",
        "structure",
        "instruments",
        "melodic",
        "chorus",
        "verse",
    )
    return any(term in normalized for term in technical_terms) and (
        any(term in normalized for term in track_terms)
        or normalized.startswith(("analyseer", "analyze", "geef een analyse", "give me an analysis"))
    )


def _is_personal_memory_request(normalized: str) -> bool:
    """Return true for questions asking what DJConnect currently remembers."""
    normalized = str(normalized or "").strip(" ?.!'\"")
    return normalized in {
        "wat weet je nu over mij",
        "wat weet je over mij",
        "wat weet djconnect over mij",
        "wat staat er in mijn Music DNA",
        "wat staat er in Music DNA",
        "wat is mijn music dna",
        "wat zegt mijn music dna",
        "geef mijn music dna samenvatting",
        "wat herinner je je over mij",
        "what do you know about me",
        "what does djconnect know about me",
        "what is in my Music DNA",
        "what do you remember about me",
        "vertel wat je over mijn smaak weet",
        "wat heb ik laatst aan favorieten toegevoegd",
        "wat heb ik recent aan favorieten toegevoegd",
        "welke nummers heb ik laatst aan favorieten toegevoegd",
        "laatst aan favorieten toegevoegd",
        "what did i recently add to favorites",
        "what did i recently add to liked songs",
    } or (
        ("wat weet" in normalized or "what do you know" in normalized)
        and ("over mij" in normalized or "about me" in normalized)
    ) or (
        "music dna" in normalized
        and any(
            term in normalized
            for term in (
                "wat zegt",
                "what does",
                "wat staat",
                "what is in",
                "wat bewaart",
                "welke gegevens",
                "privacy",
                "data sources",
                "which data",
                "what data",
            )
        )
    )


def _is_music_discovery_summary_request(normalized: str) -> bool:
    """Return true for read-only questions about the Discover recommendation feed."""
    normalized = str(normalized or "").strip(" ?.!'\"")
    if (
        ("deze aanbeveling" in normalized or "this recommendation" in normalized)
        and ("smaak" in normalized or "taste" in normalized or "past" in normalized or "fit" in normalized)
    ):
        return True
    discovery_terms = (
        "discover",
        "ontdek",
        "music discovery",
    )
    if not any(term in normalized for term in discovery_terms):
        return False
    return any(
        phrase in normalized
        for phrase in (
            "hoe werkt",
            "how does",
            "wat is er nieuw",
            "wat is nieuw",
            "wat staat er",
            "waarom",
            "ververs",
            "refresh",
            "aanbevelingen",
            "recommendations",
            "feedback",
            "play now",
            "niet voor mij",
            "passen het beste",
            "fit me best",
            "past deze aanbeveling",
            "why does this recommendation",
            "recommendation fit",
        )
    )


def _music_discovery_summary_text(text: str, memory_context: dict[str, Any]) -> str:
    """Return a compact read-only explanation for Discover help-style requests."""
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    enabled = bool(memory.get("enabled")) if isinstance(memory, dict) else False
    normalized = _normalize(text)
    if "ververs" in normalized or "refresh" in normalized:
        return (
            "Discover wordt server-side vanuit Music DNA en Spotify-profielsignalen ververst. "
            "Open het Discover-scherm of gebruik de Discover refresh-knop om de nieuwste backend-feed op te halen; "
            "ik start hierbij geen muziek."
        )
    if (
        "waarom" in normalized
        or "why" in normalized
        or "past deze aanbeveling" in normalized
        or "feedback" in normalized
        or "play now" in normalized
        or "niet voor mij" in normalized
    ):
        return (
            "Discover legt aanbevelingen uit met compacte Music DNA-signalen zoals favoriete artiesten, genres, "
            "recente luistercontext, kwaliteitsscore en feedback. Een Play Now-keuze telt als positief signaal; "
            "Niet voor mij of Verberg artiest telt als negatief signaal voor toekomstige tips."
        )
    if enabled:
        return (
            "Discover gebruikt je ingeschakelde Music DNA om nieuwe aanbevelingen, rediscover-tips en artiestankers te maken. "
            "De feed toont backend-aanbevelingen met redenen en Play Now-knoppen; recent afgespeelde tracks worden alleen als context gebruikt."
        )
    return (
        "Discover werkt pas persoonlijk zodra Music DNA is ingeschakeld. Daarna gebruikt de backend compacte luistersignalen "
        "om aanbevelingen met redenen en Play Now-knoppen te maken."
    )


def _is_recently_played_history_request(normalized: str) -> bool:
    if (re.search(r"\b(?:welche|quels|quelles|qué|which)\b", normalized)
            and re.search(r"\b(?:songs?|tracks?|titres?|canciones|albums?|álbumes|playlists?)\b", normalized)
            and re.search(r"\b(?:did i play|habe ich|ai-je|escuché)\b", normalized)
            and re.search(r"\b(?:last|letzten|dernière|última)\b", normalized)):
        return True
    if any(
        phrase in normalized
        for phrase in (
            "wat speelde hiervoor",
            "wat speelde er hiervoor",
            "wat draaide hiervoor",
            "wat draaide er hiervoor",
            "wat draaide ik net",
            "wat hoorde ik hiervoor",
            "welke artiesten hoorde ik net",
            "welk nummer speelde hiervoor",
            "welke track speelde hiervoor",
            "what played before this",
            "what was before this",
            "what played previously",
            "what did i play last hour",
            "what have i listened to today",
        )
    ):
        return True
    history_terms = (
        "welke nummers",
        "welke tracks",
        "welke albums",
        "welke artiesten",
        "welke artists",
        "welke playlists",
        "welke afspeellijsten",
        "wat heb ik",
        "wat heb ik net",
        "wat luisterde ik",
        "wat heb ik geluisterd",
        "waar heb ik",
        "waar heb ik net",
        "waar heb ik naar geluisterd",
        "waar luisterde ik",
        "waar luister ik",
        "what songs",
        "what tracks",
        "what albums",
        "what artists",
        "what playlists",
        "what did i play",
        "what have i played",
        "what did i listen",
        "what have i listened",
        "where did i listen",
        "where have i listened",
    )
    playback_terms = (
        "afgespeeld",
        "gespeeld",
        "gedraaid",
        "geluisterd",
        "naar geluisterd",
        "luisterde",
        "luister",
        "played",
        "listened",
        "listening history",
    )
    period_terms = (
        "afgelopen uur",
        "laatste uur",
        "afgelopen 2 uur",
        "afgelopen twee uur",
        "afgelopen paar uur",
        "afgelopen dag",
        "laatste dag",
        "afgelopen week",
        "laatste week",
        "vandaag",
        "net",
        "zojuist",
        "eerder",
        "recent",
        "gisteren",
        "last hour",
        "past hour",
        "last 2 hours",
        "past 2 hours",
        "last day",
        "past day",
        "last week",
        "past week",
        "today",
        "recently",
        "earlier",
        "just now",
        "yesterday",
    )
    return (
        any(term in normalized for term in history_terms)
        and any(term in normalized for term in playback_terms)
        and (
            any(term in normalized for term in period_terms)
            or re.search(r"\b(?:om|rond|around|at)\s+\d{1,2}(?::\d{2})?\s*(?:uur|u|am|pm)?\b", normalized)
            is not None
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
        "speel maar wat",
        "speel maar wat af",
        "speel maar iets",
        "speel maar iets af",
        "draai maar wat",
        "draai maar wat af",
        "draai maar iets",
        "draai maar iets af",
        "zet maar wat op",
        "zet maar iets op",
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
        "muziektip",
        "muziektips",
        "aanbevelingen",
        "recommend",
        "recommendation",
        "suggest",
        "suggest something",
        "suggestion",
        "recommend music",
        "wat past bij mij",
        "welke muziek past bij mij",
        "op basis van mijn smaak",
        "based on my taste",
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


def _is_personal_artist_recommendation_request(normalized: str) -> bool:
    artist_terms = ("artiest", "artiesten", "artist", "artists", "bands")
    taste_terms = (
        "mijn smaak",
        "mijn muzieksmaak",
        "bij mijn smaak",
        "passen bij",
        "past bij",
        "voor mij",
        "leuk vinden",
        "music taste",
        "my taste",
        "fit my taste",
        "match my taste",
    )
    recommendation_terms = (
        "welke",
        "wat voor",
        "raad",
        "aanbevel",
        "suggest",
        "recommend",
        "passen",
        "match",
        "fit",
    )
    return (
        any(term in normalized for term in artist_terms)
        and any(term in normalized for term in taste_terms)
        and any(term in normalized for term in recommendation_terms)
    )


def _is_song_recommendation_request(normalized: str) -> bool:
    if not any(term in normalized for term in ("nummer", "nummers", "track", "tracks", "song", "songs")):
        return False
    return any(
        term in normalized
        for term in (
            "heb je",
            "geef",
            "raad",
            "toon",
            "laat zien",
            "aanbevel",
            "recommend",
            "suggest",
            "toffe",
            "leuke",
            "vette",
            "goede",
            "moet ik luisteren",
        )
    )


def _is_dj_announcement_request(normalized: str) -> bool:
    return any(
        phrase in normalized
        for phrase in (
            "aankondiging",
            "dj intro",
            "dj-intro",
            "intro voor",
            "intro van",
            "intro bij",
            "announce this",
            "announcement",
            "make a dj intro",
            "geef een intro",
            "maak een intro",
            "kondig dit nummer aan",
            "zeg iets over deze track als dj",
        )
    )


def _dj_announcement_response(playback_context: dict[str, Any]) -> dict[str, Any]:
    title = _playback_text(playback_context, "track_name", "title", "name")
    artist = _playback_text(playback_context, "artist", "artist_name")
    album = _playback_text(playback_context, "album_name", "album")
    if not title and not artist:
        text = "Ik kan nu geen DJ intro maken, omdat ik niet zie welk nummer er speelt."
        return {
            "success": True,
            "text": text,
            "dj_text": text,
            "action": "none",
            "images": [],
            "playback_actions": [],
        }
    subject = _track_label(playback_context) or title or artist
    album_part = f", van het album {album}" if album else ""
    if title and artist:
        text = f"Intro: dit is {title} van {artist}{album_part}. Even volume erbij, want deze verdient je aandacht."
    else:
        text = f"Intro: dit is {subject}{album_part}. Even volume erbij, want deze verdient je aandacht."
    return {
        "success": True,
        "text": text,
        "dj_text": text,
        "action": "announce",
        "source": "spotify_playback_context",
        "playback_actions": [],
        "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
    }


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


def _is_mood_mix_request(normalized: str) -> bool:
    if "mood" not in normalized and "stemming" not in normalized:
        return False
    return bool(
        re.search(r"\b(?:speel|draai|zet)\b.+\b(?:mood|stemming)\b", normalized)
        or re.search(r"\b(?:iets|muziek|mix)\b.+\b(?:bij|voor|op)\s+(?:mijn|me|my)\s+(?:mood|stemming)\b", normalized)
    )


def _is_deferred_playback_request(normalized: str) -> bool:
    return bool(
        _is_fuzzy_music_search_request(normalized)
        or re.search(
            r"\b(?:ik\s+wil|wil\s+ik|ik\s+wil\s+wel|ik\s+wil\s+graag)\b.+\bmuziek\b",
            normalized,
        )
        or re.search(
            r"\b(?:i\s+want|i\s+would\s+like)\b.+\bmusic\b",
            normalized,
        )
        or re.search(
            r"\b(?:ik\s+heb\s+zin\s+in|ik\s+heb\s+trek\s+in)\b.+\bmuziek\b",
            normalized,
        )
        or re.search(
            r"\b(?:i\s+feel\s+like)\b.+\bmusic\b",
            normalized,
        )
        or re.search(
            r"\b(?:speel|draai|zet)\b.+\bmuziek\b",
            normalized,
        )
        or re.search(
            r"\b(?:ik\s+wil|wil\s+ik|ik\s+wil\s+wel|ik\s+wil\s+graag)\b.+\b(?:horen|luisteren|opzetten|spelen)\b",
            normalized,
        )
        or re.search(
            r"\b(?:i\s+want|i\s+would\s+like)\b.+\b(?:hear|listen|play)\b",
            normalized,
        )
    )


def _is_playback_mode_status_question(normalized: str) -> bool:
    if not any(term in normalized for term in ("shuffle", "repeat", "herhaal")):
        return False
    if normalized in {"what is shuffle status", "is repeat on"}:
        return True
    return bool(
        "?" in normalized
        or re.search(r"\b(?:staat|is)\b.+\b(?:aan|uit|actief)\b", normalized)
        or re.search(r"\b(?:hoe\s+staat|wat\s+is)\b.+\b(?:shuffle|repeat|herhaal)\b", normalized)
    )


def _is_fuzzy_music_search_request(normalized: str) -> bool:
    """Return true for broad music requests that should show Spotify choices."""
    return bool(
        (
            re.search(r"\b(?:ik\s+wil|wil\s+ik|ik\s+wil\s+wel|ik\s+wil\s+graag)\b.+\bmuziek\b", normalized)
            or re.search(r"\b(?:i\s+want|i\s+would\s+like)\b.+\bmusic\b", normalized)
            or re.search(r"\b(?:ik\s+heb\s+zin\s+in|ik\s+heb\s+trek\s+in)\b.+\bmuziek\b", normalized)
            or re.search(r"\b(?:i\s+feel\s+like)\b.+\bmusic\b", normalized)
            or re.search(r"\b(?:speel|draai|zet)\b.+\bmuziek\b", normalized)
            or re.search(r"\b(?:wat\s+voor|welke)\b.+\bmuziek\b.+\bheb\s+je\b", normalized)
            or re.search(r"\b(?:what\s+kind\s+of|which)\b.+\bmusic\b.+\b(?:have\s+you|do\s+you\s+have)\b", normalized)
        )
        and not any(
            phrase in normalized
            for phrase in (
                "wat voor muziek maakt",
                "welke muziek maakt",
                "what kind of music does",
                "waarom",
                "analyseer",
                "profiel",
            )
        )
    )


def _is_morning_start_request(normalized: str) -> bool:
    return normalized in {
        "goedemorgen",
        "goedemorgen!",
        "hey goedemorgen",
        "goedemorgen dj",
        "goede morgen",
        "goeiemorgen",
        "morgen",
        "good morning",
        "morning",
    }


def _is_next_track_info_request(normalized: str) -> bool:
    if re.search(r"\b(?:what|was|qu['’]y|qué)\b", normalized) and re.search(
            r"\b(?:in the queue|in der warteschlange|dans la file d['’]attente|en la cola)\b", normalized):
        return True
    if any(
        phrase in normalized
        for phrase in (
            "wat speelt hierna",
            "wat komt hierna",
            "welk nummer speelt hierna",
            "welk nummer komt hierna",
            "welke track speelt hierna",
            "welke track komt hierna",
            "what plays after this",
            "what comes next",
            "what's next",
            "whats next",
            "next track in queue",
        )
    ):
        return True
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
        "wat zijn",
        "welk nummer wordt",
        "welk nummer is",
        "welke nummers zijn",
        "welke track wordt",
        "welke track is",
        "welke tracks zijn",
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
    if re.match(r"^(?:speel|start|zet|play|put on)\s+(?:mijn\s+|my\s+)?(?:playlist|afspeellijst)\s+(?!(?:voor|for|een|a)\b)\S", normalized):
        return False
    if (
        any(phrase in normalized for phrase in ("voor me", "voor mij", "for me"))
        and not re.search(r"\b(?:welke|wat\s+voor|zoek|vind|voor\s+(?:hardlopen|sport|koken|werken|slapen|feest|party|focus|rustig|grunge))\b", normalized)
    ):
        return False
    return any(
        phrase in normalized
        for phrase in (
            "heb je",
            "zoek",
            "vind",
            "toon",
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


def _is_user_playlists_request(normalized: str) -> bool:
    normalized = _normalize_playlist_typos(normalized)
    if "playlist" not in normalized and "afspeellijst" not in normalized:
        return False
    own_terms = (
        "heb ik",
        "mijn",
        "eigen",
        "my",
        "mine",
        "my playlists",
        "do i have",
        "habe ich", "ai-je", "tengo",
    )
    question_terms = (
        "welke",
        "wat voor",
        "toon",
        "laat",
        "laat zien",
        "geef",
        "show",
        "list",
        "what",
        "which",
        "welche", "quelles", "qué",
    )
    return any(term in normalized for term in own_terms) and (
        any(term in normalized for term in question_terms)
        or normalized in {"mijn playlists", "mijn afspeellijsten", "my playlists"}
    )


def _normalize_playlist_typos(normalized: str) -> str:
    text = str(normalized or "")
    replacements = (
        (r"\bplayl?ists?\b", "playlists"),
        (r"\bafspeel\s*lijst(?:en)?\b", "afspeellijsten"),
        (r"\bhebn\b", "hebben"),
        (r"\bhebbn\b", "hebben"),
        (r"\bhebn\s+ik\b", "heb ik"),
        (r"\bhebben\s+ik\b", "heb ik"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _playlist_question_wants_track_choices(text: str) -> bool:
    normalized = _normalize(text)
    if re.search(
        r"\b(?:wat\s+voor|welke|what\s+kind\s+of|which)\s+(?:spotify\s+)?(?:playlists?|afspeellijsten?)\b.+\b(?:van|voor|with|about|by|for)\b",
        normalized,
    ):
        return False
    return bool(
        ("playlist" in normalized or "afspeellijst" in normalized)
        and re.search(r"\b(?:wat\s+voor|welke|what\s+kind\s+of|which)\b", normalized)
    )


def _play_something_from_artist_request(text: str) -> str:
    value = str(text or "").strip()
    patterns = (
        r"^\s*(?:speel|draai|zet)\s+(?:maar\s+|eens\s+|even\s+|graag\s+)?(?:wat|iets|something|some)\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*(?:play|put\s+on)\s+(?:something|some)\s+(?:by|from)\s+(.+?)\s*\??\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            artist = _clean_artist_item_name(match.group(1))
            if artist:
                return artist
    return ""


def _is_something_from_artist_request(normalized: str) -> bool:
    return bool(
        re.search(
            r"\bik\s+wil\s+(?:wel\s+|graag\s+)?(?:iets|something)\s+van\s+.+\b(?:horen|luisteren|opzetten|spelen)\b",
            normalized,
        )
        or re.search(r"\bi\s+(?:want|would\s+like)\s+(?:something|some)\s+by\s+.+", normalized)
        or _play_something_from_artist_request(normalized)
    )


def _is_open_playlist_recommendation_request(normalized: str) -> bool:
    if "playlist" not in normalized and "afspeellijst" not in normalized:
        return False
    if any(
        phrase in normalized
        for phrase in (
            "welke playlist past",
            "welke afspeellijst past",
            "playlist tip",
            "playlisttip",
        )
    ):
        return True
    if _playlist_query_from_question(normalized):
        return False
    return any(
        phrase in normalized
        for phrase in (
            "geef",
            "toon",
            "laat zien",
            "raad",
            "suggest",
            "recommend",
            "tip",
        )
    ) or any(term in normalized for term in ("leuke", "goede", "toffe", "vette", "mooie"))


def _playlist_query_from_question(text: str) -> str:
    original = str(text or "").strip()
    normalized = _normalize(original)
    patterns = (
        r"(?:wat\s+voor|welke|what\s+kind\s+of|which)\s+(?:spotify\s+)?(?:playlists?|afspeellijsten?)(?:\s+(?:heb\s+je|hebt\s+je|do\s+you\s+have|have\s+you))?\s+(?:van|voor|with|about|by|for)\s+(.+)$",
        r"(?:wat\s+voor|welke|what\s+kind\s+of|which)\s+(.+?)\s+(?:playlists?|afspeellijsten?)(?:\s+(?:heb\s+je|hebt\s+je|do\s+you\s+have|have\s+you))?$",
        r"(?:doe\s+maar|maak|zet|start|speel)\s+(?:eens\s+|even\s+|graag\s+)?(?:een\s+|some\s+)?(?:spotify\s+)?(?:playlists?|afspeellijsten?)\s+(?:met|van|voor|with|about|by|for)\s+(.+)$",
        r"(?:heb je|zoek|vind|welke|do you have|find|search)\s+(?:een\s+|some\s+)?(?:spotify\s+)?(?:playlists?|afspeellijsten?)(?:\s+(?:van|voor|with|about|by|for))?\s+(.+)$",
        r"(?:playlists?|afspeellijsten?)\s+(?:van|voor|with|about|by|for)\s+(.+)$",
        r"(.+?)\s+(?:playlists?|afspeellijsten?)\s*$",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return _clean_playlist_query(match.group(1))
    return ""


def _vibe_playlist_query(text: str) -> str:
    normalized = _normalize(str(text or "").strip(" ?.!'\""))
    if not normalized:
        return ""
    energetic = _energetic_playlist_query(normalized)
    if energetic:
        return energetic
    match = re.match(
        r"^\s*(?:zoek|geef|heb\s+je|find|do\s+you\s+have)\s+(?:een\s+|a\s+)?(.+?)\s+(?:playlists?|afspeellijsten?)\s*$",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        query = _clean_playlist_query(match.group(1))
        if query in {"chill", "party", "ambient", "focus", "slapen", "werken"}:
            return query
    match = re.match(
        r"^\s*(?:heb\s+je|zoek|geef|find|do\s+you\s+have)\s+(?:een\s+|a\s+)?(?:playlists?|afspeellijsten?)\s+(?:voor|for)\s+(.+?)\s*$",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        query = _clean_playlist_query(match.group(1))
        if query in {"chill", "party", "ambient", "focus", "slapen", "werken"}:
            return query
    patterns = (
        r"^\s*(.+?)\s+(?:vibes?|mood|sfeer)\s*(?:graag|please|pls)?\s*$",
        r"^\s*(?:graag|please|pls)\s+(.+?)\s+(?:vibes?|mood|sfeer)\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        query = _clean_playlist_query(match.group(1))
        if not query:
            continue
        if query in {"vibe", "vibes", "mood", "sfeer"}:
            continue
        return f"{query} muziek" if query in {"summer", "zomer", "zomerse"} else query
    return ""


def _energetic_playlist_query(normalized: str) -> str:
    if re.search(
        r"\b(?:ik\s+wil|zin\s+in|doe\s+maar|graag)\b.*\b(?:knallen|beuken|rammen|losgaan)\b",
        normalized,
    ) or re.search(r"\b(?:knallen|beuken|rammen|losgaan)\s+(?:graag|please|pls)?\b", normalized):
        return "hardstyle gabber techno hardcore edm"
    return ""


def _clean_playlist_query(value: str) -> str:
    text = str(value or "").strip(" ?.!'\"")
    text = re.sub(r"^(?:van|voor|with|about|by|for)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:hebben|hebt|zijn|bestaan|please|pls)$", "", text, flags=re.IGNORECASE)
    text = text.strip()
    if _normalize(text) in {"me", "mij", "mezelf", "my", "myself"}:
        return ""
    return text


def _is_seed_mix_playlist_request(normalized: str) -> bool:
    if not any(term in normalized for term in ("playlist", "afspeellijst", "mix")):
        return False
    return any(
        phrase in normalized
        for phrase in (
            "stel",
            "samen",
            "maak",
            "bouw",
            "op basis van",
            "obv",
            "rond",
            "in genre",
            "in genres",
            "based on",
            "make",
            "create",
        )
    ) and bool(_seeds_from_mix_playlist_request(normalized))


def _current_track_seed_mix_request(text: str) -> str:
    normalized = _normalize(text)
    if any(
        phrase in normalized
        for phrase in (
            "ik wil vergelijkbare tracks",
            "ik wil vergelijkbare nummers",
            "zet vergelijkbare tracks",
            "zet vergelijkbare nummers",
            "speel vergelijkbare tracks",
            "speel vergelijkbare nummers",
            "queue similar tracks",
            "play similar tracks",
            "i want similar tracks",
            "i want similar songs",
        )
    ):
        if any(word in normalized for word in ("wachtrij", "queue", "enqueue")):
            return "queue"
        if _execution_request(normalized) and normalized.startswith(("speel", "draai", "play")):
            return "play"
        return "more"
    if any(
        phrase in normalized
        for phrase in (
            "hierop lijken",
            "hier op lijken",
            "die hierop lijken",
            "dat hierop lijkt",
            "vergelijkbaar met dit",
            "vergelijkbare nummers",
            "deze stijl",
            "die stijl",
            "zoals dit",
            "like this",
            "similar to this",
            "songs like this",
            "tracks like this",
        )
    ):
        return "more"
    if not any(term in normalized for term in ("huidig nummer", "huidige nummer", "dit nummer", "deze track", "deze muziek", "current track", "this track", "this song", "this music")):
        return ""
    if any(term in normalized for term in ("playlist", "afspeellijst")) and any(term in normalized for term in ("maak", "stel", "samen", "obv", "op basis van", "based on")):
        return "playlist"
    if any(phrase in normalized for phrase in ("meer van deze muziek", "meer zoals dit", "meer hiervan", "more like this", "more of this music")):
        return "more"
    return ""


def _is_save_generated_playlist_request(normalized: str) -> bool:
    return any(
        phrase in normalized
        for phrase in (
            "sla deze op",
            "sla dit op",
            "bewaar deze",
            "bewaar dit",
            "maak hier een playlist",
            "maak van deze selectie een playlist",
            "sla deze mix op",
            "save this",
            "save it",
            "make this a playlist",
            "create this playlist",
        )
    ) and any(term in normalized for term in ("playlist", "mix", "op", "save", "bewaar"))


def _is_save_current_track_request(normalized: str) -> bool:
    return _current_track_favorite_target(normalized) is True


def _current_track_favorite_target(normalized: str) -> bool | None:
    current_terms = (
        "huidig nummer",
        "huidige nummer",
        "dit nummer",
        "deze track",
        "dit liedje",
        "current track",
        "this track",
        "this song",
        "dit",
    )
    favorite_terms = (
        "favorieten",
        "favoriet",
        "liked songs",
        "likes",
        "like",
        "library",
        "bibliotheek",
    )
    save_terms = ("zet", "voeg", "toe", "bewaar", "save", "like")
    remove_terms = ("haal", "verwijder", "uit", "remove", "unlike", "unsave")
    if not any(term in normalized for term in current_terms):
        return None
    if not any(term in normalized for term in favorite_terms):
        return None
    if any(term in normalized for term in remove_terms):
        return False
    if any(term in normalized for term in save_terms):
        return True
    return None


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
    if seed_type == "artists":
        genre_values = _genre_seed_values_from_mix_source(source)
        if genre_values:
            return {"genres": genre_values}
    candidates = re.split(r"\s*(?:,|;|\+|/|\ben\b|\band\b)\s*", source)
    values: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        value = " ".join(candidate.strip(" ?.!'\"").split())
        if seed_type == "artists":
            value = _normalize_artist_seed_value(value)
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            values.append(value)
    return {seed_type: values} if values else {}


_ARTIST_SEED_ALIASES = {
    "bloodhound gang": "Bloodhound Gang",
    "bloodhoundgang": "Bloodhound Gang",
    "guns n roses": "Guns N' Roses",
    "guns roses": "Guns N' Roses",
    "gunsandroses": "Guns N' Roses",
    "gunsnroses": "Guns N' Roses",
    "london grammar": "London Grammar",
    "londongrammar": "London Grammar",
    "metalica": "Metallica",
    "metalicca": "Metallica",
    "metallica": "Metallica",
    "meticallica": "Metallica",
    "mettalica": "Metallica",
    "nirvana": "Nirvana",
    "pearl jam": "Pearl Jam",
    "pearljam": "Pearl Jam",
    "radiohead": "Radiohead",
}


def _normalize_artist_seed_value(value: str) -> str:
    cleaned = " ".join(str(value or "").strip().split())
    key = re.sub(r"[^a-z0-9]+", " ", cleaned.lower()).strip()
    compact_key = key.replace(" ", "")
    return _ARTIST_SEED_ALIASES.get(key) or _ARTIST_SEED_ALIASES.get(compact_key) or cleaned


def _genre_seed_values_from_mix_source(source: str) -> list[str]:
    normalized = _normalize(source)
    if not normalized:
        return []
    if any(term in normalized for term in ("90s", "90's", "nineties", "jaren 90")) and "dance" in normalized:
        return ["dance", "house", "pop", "electronic"]
    if "dance" in normalized:
        return ["dance", "house", "electronic"]
    known = []
    for genre in ("ambient", "techno", "house", "dance", "electronic", "edm", "trance", "hardcore", "disco", "funk", "jazz", "soul", "rock", "metal", "indie", "pop"):
        if re.search(rf"\b{re.escape(genre)}\b", normalized):
            known.append(genre)
    return known[:5]


def _artist_recommendation_request(text: str) -> str:
    patterns = (
        r"^\s*(?:speel|draai|zet)\s+(?:eens\s+|even\s+|graag\s+)?(?:iets|wat)\s+(?:anders|different|else)\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*(?:play|put\s+on)\s+(?:something|anything)\s+(?:else|different)\s+(?:by|from)\s+(.+?)\s*\??\s*$",
        r"^\s*(?:geef|toon|laat\s+zien|zoek|vind)\s+(?:me|mij)?\s*(?:aanbevelingen|suggesties|recommendations?)\s+(?:op\s+basis\s+van|obv|voor|van|by|from)\s+(.+?)\s*\??\s*$",
    )
    value = str(text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        artist = _normalize_artist_seed_value(_clean_artist_name(match.group(1)))
        if artist:
            return artist
    return ""


async def _artist_seed_recommendations_response(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    seeds = {"artists": [artist]}
    result = await _spotify_seed_mix(hass, runtime, seeds)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    actions = _track_recommendation_actions(hass, tracks, limit=10, runtime=runtime)
    mix_action = _seed_mix_playback_action(hass, seeds, tracks)
    if mix_action:
        actions.append(mix_action)
    if actions:
        lines = [
            f"{index}. {action.get('title') or 'Onbekend nummer'}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(actions, start=1)
            if action.get("kind") == "track"
        ]
        message = (
            f"Ik vond deze aanbevelingen op basis van {artist}.\n"
            + "\n".join(lines)
            + "\n\nIk start nog niets; tik op Play Now om er eentje te horen."
        )
    else:
        message = f"Ik vond nu geen speelbare aanbevelingen op basis van {artist}."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "items": actions,
        "playback_actions": actions,
        "sources": [{"source": "spotify_recommendations", "title": "Spotify recommendations", "kind": "source"}],
    }


async def _spotify_seed_mix(
    hass: HomeAssistant,
    runtime: Any,
    seeds: dict[str, list[str]],
) -> dict[str, Any]:
    try:
        result = await run_music_command(
            hass,
            runtime,
            "artist_recommendations",
            {**seeds, "limit": 25},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify artist recommendations unavailable: %s", exc)
        return {}
    return result if isinstance(result, dict) else {}


async def _current_track_seed_mix_response(
    hass: HomeAssistant,
    runtime: Any,
    playback_context: dict[str, Any],
    request_kind: str,
) -> dict[str, Any]:
    seeds = _current_track_seed_values(playback_context)
    title = _playback_text(playback_context, "track_name", "title", "name")
    artist = _playback_text(playback_context, "artist", "artist_name")
    label = f"{title} van {artist}" if title and artist else title or artist or "het huidige nummer"
    if not seeds:
        message = "Ik kan nu niet zien welk nummer als basis voor de mix moet dienen."
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "none",
            "images": [],
            "items": [],
            "playback_actions": [],
            "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
        }
    result = await _spotify_seed_mix_with_fallbacks(hass, runtime, playback_context, seeds)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    used_search_fallback = False
    if not tracks:
        tracks = await _current_track_search_fallback(hass, runtime, playback_context)
        used_search_fallback = bool(tracks)
    track_actions = _track_recommendation_actions(hass, tracks, limit=10, runtime=runtime)
    result_seeds = result.get("seeds") if isinstance(result.get("seeds"), dict) else seeds
    mix_action = {} if used_search_fallback else _seed_mix_playback_action(hass, result_seeds, tracks)
    if request_kind == "queue":
        from .dialogue import current_turn
        turn = current_turn.get()
        language = turn.style.get("language", "en") if turn else "en"
        message = {
            "en": "Appending these suggestions to the queue is not supported. Playback is unchanged; choose Play Now to start a result.",
            "nl": "Deze suggesties toevoegen aan de wachtrij wordt niet ondersteund. Playback blijft ongewijzigd; kies Afspelen om een resultaat te starten.",
            "de": "Diese Vorschläge können nicht zur Warteschlange hinzugefügt werden. Die Wiedergabe bleibt unverändert; wähle Abspielen, um ein Ergebnis zu starten.",
            "fr": "L’ajout de ces suggestions à la file n’est pas pris en charge. La lecture reste inchangée ; choisis Lire pour lancer un résultat.",
            "es": "No se admite añadir estas sugerencias a la cola. La reproducción no cambia; elige Reproducir para iniciar un resultado.",
        }[language]
        return {"success": True, "text": message, "dj_text": message, "action": "none",
            "queue_append": {"state": "unsupported"}, "images": [], "items": track_actions,
            "playback_actions": track_actions, "sources": [
                {"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"},
                {"source": "spotify_recommendations", "title": "Spotify recommendations", "kind": "source"}]}
    if request_kind == "play":
        uris = _track_uris_from_items(tracks, limit=50)
        playback_result = {}
        if uris:
            try:
                playback_result = await run_music_command(hass, runtime, "play_uris", uris, play=True)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("DJConnect current-track similar queue failed: %s", exc)
        if track_actions and playback_result:
            message = (
                f"Afspelen van vergelijkbare tracks op basis van {label} is aangevraagd. "
                "Dit zijn de eerste nummers; tik op Play Now om er eentje direct te starten."
            )
        elif track_actions:
            message = (
                f"Ik vond vergelijkbare tracks op basis van {label}, maar kon ze nu niet starten. "
                "Tik op Play Now om er eentje te starten."
            )
        else:
            message = f"Ik kon nu geen vergelijkbare Spotify-tracks vinden op basis van {label}."
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "play_music" if playback_result else "none",
            "images": [],
            "items": track_actions,
            "playback_actions": track_actions,
            "playback": playback_result.get("playback") if isinstance(playback_result, dict) else {},
            "sources": [
                {"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"},
                {"source": "spotify_recommendations", "title": "Spotify recommendations", "kind": "source"},
            ],
        }
    actions = track_actions + ([mix_action] if mix_action else [])
    if actions:
        intro = (
            f"Ik heb een mix samengesteld op basis van {label}. "
            if request_kind == "playlist"
            else f"Ik vond meer muziek in de sfeer van {label}. "
        )
        message = intro + "Ik start nog niets; tik op Play Now bij een track of zet de hele mix in de wachtrij."
    else:
        message = f"Ik kon nu geen speelbare Spotify-mix samenstellen op basis van {label}."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "items": actions,
        "playback_actions": actions,
        "sources": [
            {"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"},
            {"source": "spotify_recommendations", "title": "Spotify recommendations", "kind": "source"},
        ],
    }


def _current_track_seed_values(playback_context: dict[str, Any]) -> dict[str, list[str]]:
    uri = str(playback_context.get("uri") or playback_context.get("track_uri") or "").strip()
    if uri.startswith("spotify:track:"):
        return {"tracks": [uri]}
    label = _track_label(playback_context)
    return {"tracks": [label]} if label else {}


async def _current_track_search_fallback(
    hass: HomeAssistant,
    runtime: Any,
    playback_context: dict[str, Any],
) -> list[dict[str, Any]]:
    artist = _playback_text(playback_context, "artist", "artist_name")
    if not artist:
        return []
    result = await _spotify_track_search(hass, runtime, _normalize_artist_seed_value(artist), limit=25)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    matches = _tracks_matching_artist(tracks, artist)
    current_uri = str(playback_context.get("uri") or playback_context.get("track_uri") or "").strip()
    current_title = _normalize(_playback_text(playback_context, "track_name", "title", "name"))
    filtered: list[dict[str, Any]] = []
    for track in matches:
        uri = str(track.get("uri") or "").strip()
        title = _normalize(str(track.get("track_name") or track.get("title") or track.get("name") or ""))
        if uri and current_uri and uri == current_uri:
            continue
        if title and current_title and title == current_title:
            continue
        filtered.append(track)
    return filtered


async def _spotify_seed_mix_with_fallbacks(
    hass: HomeAssistant,
    runtime: Any,
    playback_context: dict[str, Any],
    primary_seeds: dict[str, list[str]],
) -> dict[str, Any]:
    for seeds in _current_track_seed_fallbacks(playback_context, primary_seeds):
        result = await _spotify_seed_mix(hass, runtime, seeds)
        tracks = result.get("tracks") if isinstance(result, dict) else []
        if isinstance(tracks, list) and tracks:
            return {**result, "seeds": seeds}
    return {}


def _current_track_seed_fallbacks(
    playback_context: dict[str, Any],
    primary_seeds: dict[str, list[str]],
) -> list[dict[str, list[str]]]:
    fallbacks: list[dict[str, list[str]]] = []
    seen: set[str] = set()

    def add(seeds: dict[str, list[str]]) -> None:
        clean = {
            key: [str(value).strip() for value in values if str(value).strip()]
            for key, values in seeds.items()
            if isinstance(values, list)
        }
        clean = {key: values for key, values in clean.items() if values}
        if not clean:
            return
        marker = repr(sorted(clean.items()))
        if marker in seen:
            return
        seen.add(marker)
        fallbacks.append(clean)

    add(primary_seeds)
    label = _track_label(playback_context)
    if label:
        add({"tracks": [label]})
    artist = _playback_text(playback_context, "artist", "artist_name")
    if artist:
        add({"artists": [_normalize_artist_seed_value(artist)]})
    return fallbacks


def _track_uris_from_items(tracks: Any, *, limit: int) -> list[str]:
    if not isinstance(tracks, list):
        return []
    uris: list[str] = []
    seen: set[str] = set()
    for track in tracks:
        if not isinstance(track, dict):
            continue
        uri = str(track.get("uri") or "").strip()
        if not uri.startswith("spotify:track:") or uri in seen:
            continue
        seen.add(uri)
        uris.append(uri)
        if len(uris) >= limit:
            break
    return uris


async def _mood_mix_response(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
) -> dict[str, Any]:
    mood_value = _payload_or_memory_mood(payload, memory_context)
    zone = mood_zone_for_value(mood_value) if mood_value is not None else None
    zone_name = zone.name if zone is not None else "groove"
    seeds = {"genres": _mood_mix_genres(zone_name)}
    result = await _spotify_seed_mix(hass, runtime, seeds)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    track_actions = _track_recommendation_actions(hass, tracks, limit=10, runtime=runtime)
    mix_action = _seed_mix_playback_action(hass, seeds, tracks)
    actions = track_actions + ([mix_action] if mix_action else [])
    mood_label = _mood_mix_label(mood_value, zone_name)
    if track_actions:
        lines = [
            f"{index}. {action.get('title') or 'Onbekend nummer'}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(track_actions, start=1)
        ]
        message = (
            f"Ik bouw een mix voor je huidige mood: {mood_label}. "
            f"Daarom kies ik richting {_join_examples(seeds['genres'], limit=4)}.\n"
            "Ik heb je wachtrij voorbereid met deze nummers:\n"
            + "\n".join(lines)
            + "\n\nTik op Play Now bij een track, of kies 'Zet allemaal in wachtrij & speel af' voor de hele mix."
        )
    else:
        message = (
            f"Ik wilde een mix maken voor je huidige mood: {mood_label}, "
            "maar ik vond nu geen speelbare Spotify-tracks."
        )
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": actions,
        "items": track_actions,
        "sources": [{"source": "spotify_recommendations", "title": "Spotify recommendations", "kind": "source"}],
    }


def _payload_or_memory_mood(payload: dict[str, Any], memory_context: dict[str, Any]) -> int | None:
    for value in (payload.get("mood"), payload.get("energy")):
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            continue
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    return _profile_mood(memory)


def _mood_mix_genres(zone_name: str) -> list[str]:
    return {
        "chill": ["ambient", "acoustic", "chill", "downtempo"],
        "groove": ["indie", "soul", "funk", "groove"],
        "energy": ["dance", "house", "pop", "electronic"],
        "party": ["party", "edm", "dance", "pop"],
    }.get(zone_name, ["indie", "soul", "funk", "groove"])


def _mood_mix_label(mood_value: int | None, zone_name: str) -> str:
    label = {
        "chill": "chill",
        "groove": "groove",
        "energy": "energy",
        "party": "party",
    }.get(zone_name, zone_name)
    if mood_value is None:
        return f"{label}-vibe"
    return f"{mood_value}/100 ({label})"


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
        result = await run_music_command(
            hass,
            runtime,
            "artist_recommendations",
            {**seeds, "limit": 10},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify song recommendations unavailable: %s", exc)
        result = {}
    tracks = result.get("tracks") if isinstance(result, dict) else []
    track_actions = _track_recommendation_actions(hass, tracks, limit=10, runtime=runtime)
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
    runtime: Any | None = None,
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
        action = _play_now_action_from_spotify_item(hass, {**item, "type": "track"}, runtime=runtime)
        if not action:
            continue
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
    labels = {
        "artists": ("artiest ", "artiesten "),
        "tracks": ("track ", "tracks "),
        "genres": ("genre ", "genres "),
    }
    for key, (singular, plural) in labels.items():
        values = seeds.get(key)
        if isinstance(values, list) and values:
            prefix = singular if len(values) == 1 else plural
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
        result = await run_music_command(
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
    *,
    limit: int = 10,
) -> dict[str, Any]:
    try:
        result = await async_call_ai_tool(
            hass,
            runtime,
            "djconnect_search_music",
            {"query": query, "media_type": "playlist", "limit": limit},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify playlist search unavailable: %s", exc)
        return {}
    if not isinstance(result, dict):
        return {}
    backend_result = result.get("result")
    return backend_result if isinstance(backend_result, dict) else result


async def _spotify_track_search(
    hass: HomeAssistant,
    runtime: Any,
    query: str,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    try:
        result = await run_music_command(
            hass,
            runtime,
            "search_tracks",
            {"query": query, "limit": limit},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify track search unavailable: %s", exc)
        return {}
    return result if isinstance(result, dict) else {}


async def _spotify_album_search(
    hass: HomeAssistant,
    runtime: Any,
    query: str,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    try:
        result = await run_music_command(
            hass,
            runtime,
            "search_albums",
            {"query": query, "limit": limit},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify album search unavailable: %s", exc)
        return {}
    return result if isinstance(result, dict) else {}


def _genre_options_request(text: str) -> str:
    value = str(text or "").strip()
    patterns = (
        r"^\s*ik\s+wil\s+(?:graag\s+|wel\s+)?(?:genre\s+)?(.+?)\s+(?:horen|spelen|luisteren|draaien)\s*\??\s*$",
        r"^\s*(?:speel|draai|zet)\s+(?:eens\s+|even\s+|graag\s+)?(?:genre\s+)?(.+?)\s*(?:muziek)?\s*(?:op|af|aan)?\s*$",
        r"^\s*i\s+(?:want|would\s+like)\s+(?:to\s+hear|to\s+play|to\s+listen\s+to)?\s*(?:genre\s+)?(.+?)\s*\??\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        query = _clean_genre_options_query(match.group(1))
        if query and _looks_like_genre_query(value, query):
            return query
    return ""


def _clean_genre_options_query(value: Any) -> str:
    query = str(value or "").strip()
    query = re.sub(r"\b(?:muziek|music|genre)\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+", " ", query).strip(" ?.!'\">")
    return query


def _looks_like_genre_query(original: str, query: str) -> bool:
    normalized_original = _normalize(original)
    normalized_query = _normalize(query)
    if "genre" in normalized_original:
        return True
    known_genres = {
        "ambient",
        "blues",
        "classical",
        "country",
        "dance",
        "disco",
        "drum and bass",
        "dnb",
        "edm",
        "folk",
        "funk",
        "grunge",
        "hardcore",
        "hip hop",
        "hiphop",
        "house",
        "indie",
        "jazz",
        "metal",
        "pop",
        "punk",
        "r&b",
        "rap",
        "reggae",
        "rock",
        "soul",
        "techno",
        "trance",
    }
    return normalized_query in known_genres


async def _genre_media_options_response(
    hass: HomeAssistant,
    runtime: Any,
    genre: str,
) -> dict[str, Any]:
    album_result = await _spotify_album_search(hass, runtime, genre, limit=10)
    playlist_result = await _spotify_playlist_search(hass, runtime, genre, limit=10)
    albums = album_result.get("albums") if isinstance(album_result, dict) else []
    playlists = playlist_result.get("playlists") if isinstance(playlist_result, dict) else []
    album_actions = _album_search_playback_actions(hass, albums, limit=10)
    playlist_actions = _playlist_search_playback_actions(hass, playlists, limit=10)
    actions = _interleave_playback_actions(album_actions, playlist_actions, limit=10)
    return _media_options_response(runtime, genre, actions)


def _media_options_response(
    runtime: Any, query: str, actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """One playable collection; its title/art/type belong to the action cards.

    Do not also emit a text list and informational items for those same cards.
    The accepted intro is the exact replay text; no caller text or new model
    invocation is needed to present already qualified catalogue choices.
    """
    from .dialogue import current_turn
    turn = current_turn.get()
    language = turn.style["language"] if turn is not None else _response_language(runtime)
    introductions = {
        "en": "I've found albums and playlists for {query}. Choose where we start.",
        "nl": "Ik heb albums en playlists voor {query} gevonden. Kies waar we mee beginnen.",
        "de": "Ich habe Alben und Playlists für {query} gefunden. Such aus, womit wir beginnen.",
        "fr": "J'ai trouvé des albums et playlists pour {query}. Choisis par où on commence.",
        "es": "He encontrado álbumes y listas para {query}. Elige por dónde empezamos.",
    }
    empty = {
        "en": "I couldn't find playable albums or playlists for {query} just now.",
        "nl": "Ik vond nu geen speelbare albums of playlists voor {query}.",
        "de": "Ich habe gerade keine abspielbaren Alben oder Playlists für {query} gefunden.",
        "fr": "Je n'ai pas trouvé d'albums ou de playlists à écouter pour {query} pour le moment.",
        "es": "Ahora no he encontrado álbumes ni listas que pueda reproducir para {query}.",
    }
    message = (introductions if actions else empty)[language].format(query=query)
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": actions,
        "items": [],
        "sources": [
            {"source": "spotify_album_search", "title": "Spotify album search", "kind": "source"},
            {"source": "spotify_playlist_search", "title": "Spotify playlist search", "kind": "source"},
        ],
    }


async def _artist_album_playlist_options_response(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    album_result = await _spotify_album_search(hass, runtime, artist, limit=10)
    playlist_result = await _spotify_playlist_search(hass, runtime, artist, limit=10)
    albums = album_result.get("albums") if isinstance(album_result, dict) else []
    playlists = playlist_result.get("playlists") if isinstance(playlist_result, dict) else []
    album_actions = _album_search_playback_actions(hass, albums, limit=10)
    playlist_actions = _playlist_search_playback_actions(hass, playlists, limit=10)
    actions = _interleave_playback_actions(album_actions, playlist_actions, limit=10)
    return _media_options_response(runtime, artist, actions)


def _interleave_playback_actions(
    first: list[dict[str, Any]],
    second: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    max_len = max(len(first), len(second))
    for index in range(max_len):
        for source in (first, second):
            if index >= len(source):
                continue
            action = source[index]
            uri = str(action.get("uri") or action.get("context_uri") or "").strip()
            if not uri or uri in seen:
                continue
            seen.add(uri)
            actions.append(action)
            if len(actions) >= limit:
                return actions
    return actions


def _artist_item_list_request(text: str) -> dict[str, Any]:
    from .album_choices import other_album_request
    if request := other_album_request(text):
        return request
    album_choice_patterns = (
        r"^\s*(?:speel|draai|zet)\s+(?:eens\s+|even\s+|graag\s+)?(?:een\s+)?album\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*(?:speel|draai|zet)\s+(?:eens\s+|even\s+|graag\s+)?(?:een\s+)?(?:ander|andere)\s+album\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*(?:play|put\s+on)\s+(?:an?\s+)?album\s+(?:by|from)\s+(.+?)\s*\??\s*$",
        r"^\s*(?:play|put\s+on)\s+(?:another|a\s+different)\s+album\s+(?:by|from)\s+(.+?)\s*\??\s*$",
    )
    value = str(text or "").strip()
    for pattern in album_choice_patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            artist = _clean_artist_item_name(match.group(1))
            if artist:
                return {"item_type": "album", "artist": artist, "count": None}
    patterns = (
        r"^\s*(?:zeig(?:e)?|gib|montre|donne|muestra|muéstrame|dame)(?:-moi|\s+mir)?\s+(?:(?:les|los|las|die)\s+)?(?:(\d+)\s+)?(alben|álbumes?|albums?|songs?|titres?|canciones|tracks?|playlists?)\s+(?:von|de)\s+(.+?)\s*\??\s*$",
        r"^\s*(?:geef|toon|laat\s+zien|laat|zoek|vind)\s+(?:me|mij)?\s*(?:(\d+|een|twee|drie|vier|vijf|zes|zeven|acht|negen|tien)\s+)?(albums?|tracks?|nummers?|songs?|playlists?|afspeellijsten?)\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*welke\s+(albums?)\s+(?:bracht|brachten|heeft|hebben)\s+(.+?)\s+(?:uit|uitgebracht|gereleased|released)\s*\??\s*$",
        r"^\s*welke\s+(muziek|tracks?|nummers?|songs?)\s+(?:heeft|hebben)\s+(.+?)\s+(?:gemaakt|uitgebracht|gereleased|released)\s*\??\s*$",
        r"^\s*what\s+(music|tracks?|songs?)\s+(?:has|have|did)\s+(.+?)\s+(?:made|released)\s*\??\s*$",
        r"^\s*(?:give|show|find)\s+(?:me\s+)?(?:(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+)?(albums?|tracks?|songs?|playlists?)\s+(?:by|from)\s+(.+?)\s*\??\s*$",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        if len(match.groups()) == 2:
            count = 5
            item_type = _artist_item_type(match.group(1))
            artist = _clean_artist_item_name(match.group(2))
        else:
            count = _bounded_item_count(match.group(1), default=5)
            item_type = _artist_item_type(match.group(2))
            artist = _clean_artist_item_name(match.group(3))
        if _normalize(artist) in {
            "deze artiest",
            "die artiest",
            "huidige artiest",
            "deze band",
            "die band",
            "current artist",
            "this artist",
            "that artist",
            "this band",
        }:
            return {}
        if re.search(r"\bwelke\s+albums?\s+(?:bracht|brachten)\b", _normalize(value)):
            artist = _normalize(artist)
        if item_type and artist:
            return {"item_type": item_type, "artist": artist, "count": count}
    return {}


def _artist_fun_queue_request(text: str) -> str:
    patterns = (
        r"^\s*(?:speel|draai|zet)\s+(?:eens\s+|even\s+|graag\s+)?(?:wat|iets)\s+(?:leuks|lekkers|moois|fijns)\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*(?:play|put\s+on)\s+(?:something|some)\s+(?:nice|fun|good)\s+(?:by|from)\s+(.+?)\s*\??\s*$",
    )
    value = str(text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            return _clean_artist_item_name(match.group(1))
    return ""


async def _artist_fun_queue_response(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    result = await _spotify_track_search(hass, runtime, artist, limit=25)
    tracks = _tracks_matching_artist(result.get("tracks") if isinstance(result, dict) else [], artist)
    random.shuffle(tracks)
    selected = tracks[:5]
    actions = _track_recommendation_actions(hass, selected, limit=5, runtime=runtime)
    uris = _track_uris_from_items(selected, limit=5)
    playback_result: dict[str, Any] = {}
    if uris:
        try:
            playback_result = await run_music_command(hass, runtime, "play_uris", uris, play=True)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect artist fun queue failed: %s", exc)
    if actions and playback_result:
        lines = [
            f"{index}. {action.get('title') or 'Onbekend nummer'}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(actions, start=1)
        ]
        message = (
            f"Ik heb vijf nummers van {artist} in je wachtrij gezet:\n"
            + "\n".join(lines)
            + "\n\nTik op Play Now om er eentje direct te starten."
        )
    elif actions:
        message = (
            f"Ik vond vijf nummers van {artist}, maar kon de wachtrij nu niet vullen. "
            "Tik op Play Now om er eentje direct te starten."
        )
    else:
        message = f"Ik vond nu geen speelbare Spotify-nummers van {artist}."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "play_music" if playback_result else "none",
        "images": [],
        "items": actions,
        "playback_actions": actions,
        "playback": playback_result.get("playback") if isinstance(playback_result, dict) else {},
        "sources": [{"source": "spotify_track_search", "title": "Spotify track search", "kind": "source"}],
    }


def _clean_artist_item_name(value: Any) -> str:
    artist = _clean_artist_name(str(value or ""))
    artist = re.sub(r"^\s*(?:artiest|artist|band)\s+", "", artist, flags=re.IGNORECASE).strip()
    return _normalize_artist_seed_value(artist)


def _artist_more_media_request(text: str, playback_context: dict[str, Any]) -> str:
    patterns = (
        r"^\s*meer\s+van\s+(.+?)\s*\??\s*$",
        r"^\s*more\s+(?:by|from)\s+(.+?)\s*\??\s*$",
    )
    value = str(text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if not match:
            continue
        artist = _clean_artist_name(match.group(1))
        if _normalize(artist) in {
            "deze artiest",
            "die artiest",
            "huidige artiest",
            "deze band",
            "die band",
            "current artist",
            "this artist",
            "that artist",
            "this band",
        }:
            return _artist_from_playback_context(playback_context)
        return artist
    return ""


def _bounded_item_count(value: Any, *, default: int) -> int:
    words = {
        "een": 1,
        "one": 1,
        "twee": 2,
        "two": 2,
        "drie": 3,
        "three": 3,
        "vier": 4,
        "four": 4,
        "vijf": 5,
        "five": 5,
        "zes": 6,
        "six": 6,
        "zeven": 7,
        "seven": 7,
        "acht": 8,
        "eight": 8,
        "negen": 9,
        "nine": 9,
        "tien": 10,
        "ten": 10,
    }
    raw = str(value or "").strip().lower()
    if not raw:
        return default
    try:
        count = int(raw)
    except ValueError:
        count = words.get(raw, default)
    return max(1, min(10, count))


def _artist_item_type(value: Any) -> str:
    normalized = _normalize(str(value or ""))
    if normalized.startswith(("album", "álbum")) or normalized == 'alben':
        return "album"
    if normalized in {"muziek", "music", "track", "tracks", "nummer", "nummers", "song", "songs", "titre", "titres", "canción", "canciones"}:
        return "track"
    if normalized in {"playlist", "playlists", "afspeellijst", "afspeellijsten"}:
        return "playlist"
    return ""


async def _artist_item_list_response(
    hass: HomeAssistant,
    runtime: Any,
    request: dict[str, Any],
) -> dict[str, Any]:
    artist = str(request.get("artist") or "").strip()
    item_type = str(request.get("item_type") or "").strip()
    count_value = request.get("count")
    count = None if count_value is None and item_type == "album" else _bounded_item_count(count_value, default=5)
    if item_type == "album":
        if request.get("exclude_current"):
            from .album_choices import other_album_response
            return await other_album_response(hass, runtime, artist)
        discography = await _spotify_artist_albums(hass, runtime, artist)
        if discography:
            return _artist_albums_response(hass, discography, limit=count)
        return _empty_artist_item_list_response(artist, "albums", "spotify_artist_albums")
    if item_type == "track":
        result = await _spotify_track_search(hass, runtime, artist, limit=count)
        tracks = result.get("tracks") if isinstance(result, dict) else []
        tracks = _tracks_matching_artist(tracks, artist)
        actions = _track_recommendation_actions(hass, tracks, limit=count, runtime=runtime)
        return _artist_clickable_rows_response(
            artist,
            "nummers",
            actions,
            "spotify_track_search",
            _read_text('tracks',artist=artist),
        )
    if item_type == "playlist":
        result = await _spotify_playlist_search(hass, runtime, artist, limit=count)
        playlists = result.get("playlists") if isinstance(result, dict) else []
        actions = _playlist_search_playback_actions(hass, playlists, limit=count)
        return _artist_clickable_rows_response(
            artist,
            "playlists",
            actions,
            "spotify_playlist_search",
            _read_text('artist_playlists',artist=artist),
        )
    return _empty_artist_item_list_response(artist, "resultaten", "spotify_search")


def _tracks_matching_artist(tracks: Any, artist: str) -> list[dict[str, Any]]:
    if not isinstance(tracks, list):
        return []
    wanted = _normalize(artist)
    wanted_key = _artist_match_key(artist)
    matches: list[dict[str, Any]] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        artist_values = [
            str(track.get("artist") or ""),
            str(track.get("artist_name") or ""),
            str(track.get("artists") or ""),
        ]
        if any(
            (wanted and wanted in _normalize(value))
            or (wanted_key and wanted_key in _artist_match_key(value))
            for value in artist_values
        ):
            matches.append(track)
    return matches


def _artist_match_key(value: Any) -> str:
    normalized = _normalize(str(value or ""))
    normalized = re.sub(r"\b(?:and|en)\b", " ", normalized)
    normalized = normalized.replace("&", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def _artist_clickable_rows_response(
    artist: str,
    label: str,
    actions: list[dict[str, Any]],
    source: str,
    intro: str,
) -> dict[str, Any]:
    if actions:
        lines = [
            f"{index}. {action.get('title') or 'Onbekend'}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(actions, start=1)
        ]
        message = (
            f"{intro}\n"
            + "\n".join(lines)
            + '\n\n'+_read_text('play_hint')
        )
    else:
        message = _read_text('empty',label=label,artist=artist)
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": actions,
        "items": actions,
        "sources": [{"source": source, "title": source.replace("_", " "), "kind": "source"}],
    }


async def _artist_more_media_response(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    album_result = await _spotify_album_search(hass, runtime, artist, limit=10)
    playlist_result = await _spotify_playlist_search(hass, runtime, artist, limit=10)
    track_result = await _spotify_track_search(hass, runtime, artist, limit=10)
    albums = album_result.get("albums") if isinstance(album_result, dict) else []
    playlists = playlist_result.get("playlists") if isinstance(playlist_result, dict) else []
    tracks = track_result.get("tracks") if isinstance(track_result, dict) else []
    actions = _ordered_playback_actions(
        [
            *_album_search_playback_actions(hass, albums, limit=10),
            *_playlist_search_playback_actions(hass, playlists, limit=10),
            *_track_recommendation_actions(hass, tracks, limit=10, runtime=runtime),
        ],
        limit=10,
    )
    if actions:
        lines = [
            f"{index}. {action.get('title') or 'Spotify resultaat'}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(actions, start=1)
        ]
        message = (
            f"Ik vond meer van {artist}: eerst albums, daarna playlists en tracks.\n"
            + "\n".join(lines)
            + "\n\nTik op Play Now om er eentje direct te starten."
        )
    else:
        message = f"Ik vond nu geen speelbare albums, playlists of tracks voor {artist}."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": actions,
        "items": actions,
        "sources": [
            {"source": "spotify_album_search", "title": "Spotify album search", "kind": "source"},
            {"source": "spotify_playlist_search", "title": "Spotify playlist search", "kind": "source"},
            {"source": "spotify_track_search", "title": "Spotify track search", "kind": "source"},
        ],
    }


def _ordered_playback_actions(
    candidates: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for action in candidates:
        uri = str(action.get("uri") or action.get("context_uri") or "").strip()
        if not uri or uri in seen:
            continue
        seen.add(uri)
        actions.append(action)
        if len(actions) >= limit:
            break
    return actions


def _empty_artist_item_list_response(artist: str, label: str, source: str) -> dict[str, Any]:
    message = _read_text('empty',label=label,artist=artist)
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": [],
        "items": [],
        "sources": [{"source": source, "title": source.replace("_", " "), "kind": "source"}],
    }


async def _playlist_track_choices_response(
    hass: HomeAssistant,
    runtime: Any,
    query: str,
) -> dict[str, Any]:
    result = await _spotify_track_search(hass, runtime, query, limit=10)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    actions = _track_recommendation_actions(hass, tracks, limit=10, runtime=runtime)
    if actions:
        lines = [
            f"{index}. {action.get('title') or 'Onbekend nummer'}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(actions, start=1)
        ]
        message = (
            "Ik heb je wachtrij gevuld met de volgende nummers:\n"
            + "\n".join(lines)
        )
    else:
        message = f"Ik vond nu geen speelbare Spotify-nummers voor {query}."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": actions,
        "items": actions,
        "sources": [{"source": "spotify_track_search", "title": "Spotify track search", "kind": "source"}],
    }


async def _artist_more_tracks_response(
    hass: HomeAssistant,
    runtime: Any,
    artist: str,
) -> dict[str, Any]:
    result = await _spotify_track_search(hass, runtime, artist, limit=10)
    tracks = result.get("tracks") if isinstance(result, dict) else []
    actions = _track_recommendation_actions(hass, tracks, limit=10, runtime=runtime)
    if actions:
        lines = [
            f"{index}. {action.get('title') or 'Onbekend nummer'}"
            + (f" - {action.get('subtitle')}" if action.get("subtitle") else "")
            for index, action in enumerate(actions, start=1)
        ]
        message = (
            f"Ik vond nog meer nummers van {artist}. Tik op Play Now om er eentje te starten:\n"
            + "\n".join(lines)
        )
    else:
        message = f"Ik vond nu geen speelbare Spotify-nummers van {artist}."
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "images": [],
        "playback_actions": actions,
        "items": actions,
        "sources": [{"source": "spotify_track_search", "title": "Spotify track search", "kind": "source"}],
    }


async def _spotify_user_playlists(
    hass: HomeAssistant,
    runtime: Any,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    try:
        result = await run_music_command(
            hass,
            runtime,
            "playlists",
            {"limit": limit},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify user playlists unavailable: %s", exc)
        return {}
    return result if isinstance(result, dict) else {}


def _playlist_search_playback_actions(
    hass: HomeAssistant,
    playlists: Any,
    *,
    limit: int = 10,
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
        action = build_playback_action(
            _first_runtime(hass),
            {
                **playlist,
                "uri": uri,
                "context_uri": uri,
                "title": title,
                "subtitle": subtitle,
                "image_url": proxy_image,
                "thumbnail_url": proxy_image,
            },
            "playlist",
            "Spotify playlist-resultaat op basis van je Ask DJ vraag.",
        )
        if not action:
            continue
        actions.append(action)
        if len(actions) >= limit:
            break
    return actions


def _album_search_playback_actions(
    hass: HomeAssistant,
    albums: Any,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if not isinstance(albums, list):
        return []
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for album in albums:
        if not isinstance(album, dict):
            continue
        uri = str(album.get("uri") or album.get("album_uri") or "").strip()
        if not uri.startswith("spotify:album:") or uri in seen:
            continue
        seen.add(uri)
        image_url = str(
            album.get("image_url")
            or album.get("album_image_url")
            or album.get("entity_picture")
            or album.get("thumbnail_url")
            or ""
        ).strip()
        proxy_image = (
            register_image_proxy_url(hass, image_url)
            if image_url.startswith(("http://", "https://"))
            else image_url
        )
        title = str(album.get("title") or album.get("name") or uri).strip()
        subtitle = str(album.get("subtitle") or album.get("artist") or album.get("artist_name") or "").strip()
        action = build_playback_action(
            _first_runtime(hass),
            {
                **album,
                "uri": uri,
                "context_uri": uri,
                "title": title,
                "subtitle": subtitle,
                "image_url": proxy_image,
                "thumbnail_url": proxy_image,
            },
            "album",
            "Spotify album-resultaat op basis van je Ask DJ vraag.",
        )
        if not action:
            continue
        actions.append(action)
        if len(actions) >= limit:
            break
    return actions


def _personal_music_profile_text(
    text: str,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    listening_profile: dict[str, Any] | None = None,
) -> str:
    period = _profile_period_label(text)
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    session = memory_context.get("session") if isinstance(memory_context, dict) else []
    listening_profile = listening_profile if isinstance(listening_profile, dict) else {}
    tracks = _profile_tracks(memory, playback_context, listening_profile)
    artists = _profile_artists(memory, tracks, listening_profile)
    albums = _top_values(tracks, ("album", "album_name"))
    genres = _profile_genres(memory, listening_profile)
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
        profile_hint = " Je backend gaf ook nog geen bruikbare recente of top-items terug." if listening_profile else ""
        return (
            f"Ik heb nog te weinig luistergeschiedenis om je muzieksmaak over {period} eerlijk te analyseren."
            f"{detail}{profile_hint} Zodra er meer recente luisterprofiel-snapshots of Music DNA data staat, kan ik daar een veel scherper profiel van maken."
        )

    profile_source = (
        "je Music DNA en recente luistergeschiedenis"
        if listening_profile
        else "je Music DNA en beschikbare luistercontext"
    )
    lines = [f"Voor {period} zie ik dit profiel op basis van {profile_source}."]
    if listening_profile:
        lines.extend(["", "Bronnen:", "- Luisterprofiel recent/top-data", "- Music DNA"])
    lines.append("")
    if genres:
        lines.append("- Harde observatie: je genres neigen naar " + _join_examples(genres, limit=4) + ".")
    elif artists:
        lines.append(
            "- Harde observatie: ik zie vooral terugkerende artiesten zoals "
            + _join_examples(artists, limit=4)
            + "."
        )
    if albums:
        lines.append("- Albums/contexts die eruit springen: " + _join_examples(albums, limit=3) + ".")
    lines.append("")
    vibe = _profile_vibe(genres, energy, mood)
    lines.append(
        "- Interpretatie: je profiel lijkt "
        + vibe
        + "; dat is een voorzichtige duiding, geen harde diagnose."
    )
    if mood is not None:
        zone = mood_zone_for_value(mood)
        if zone is not None:
            lines.append(
                f"- Laatste mood/energy in Music DNA: {mood}/100 "
                f"({zone.name}: {zone.prompt_hint})."
            )
        else:
            lines.append(f"- Laatste mood/energy in Music DNA: {mood}/100.")
    if examples:
        lines.extend(["", "Concrete voorbeelden:", *[f"- {item}" for item in examples[:6]]])
    if listening_profile and _profile_limited(listening_profile):
        lines.append("")
        lines.append("Let op: DJConnect bewaart geen onbeperkte ruwe luistergeschiedenis, dus dit blijft een profielschets op basis van recente en top-item snapshots.")
    if isinstance(last_ask, dict) and last_ask.get("input"):
        lines.append("")
        lines.append(f"Recente Ask DJ context: je vroeg eerder '{last_ask['input']}'.")
    return "\n".join(line for line in lines if line is not None).strip()


async def _track_insight_response(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Return Track Insight through the shared backend service."""
    from ..track_insight import is_track_insight_navigation_request
    navigation = is_track_insight_navigation_request(str(payload.get("text") or payload.get("message") or ""))
    try:
        insight = await async_call_ai_tool(
            hass,
            runtime,
            "djconnect_track_insight",
            payload,
        )
    except TrackInsightError as exc:
        error = track_insight_error_response(exc)
        message = str(error.get("message") or "Track Insight is nu niet beschikbaar.")
        return {
            "success": False,
            "text": message,
            "dj_text": message,
            "message": message,
            "error": error.get("error"),
            "action": "none",
            "intent": {"category": "informational", "intent": "track_insight", "action": "none"},
            "images": [],
            "links": [],
            "sources": [],
            "items": [],
            "playback_actions": [],
        }
    title = str((insight.get("track") or {}).get("title") or "dit nummer").strip()
    artist = str((insight.get("track") or {}).get("artist") or "").strip()
    introductions = {"en": "Here is the Track Insight for", "nl": "Dit is de Track Insight voor",
        "de": "Hier ist der Track Insight für", "fr": "Voici le Track Insight pour", "es": "Este es el Track Insight de"}
    language = str(insight.get("language") or payload.get("language") or "en").split("-", 1)[0]
    speak = f"{introductions.get(language,introductions['en'])} {title}{f' · {artist}' if artist else ''}." if navigation else ""
    music_dna = insight.get("music_dna") if isinstance(insight.get("music_dna"), dict) else {}
    music_dna_summary = str(music_dna.get("summary") or "").strip()
    if music_dna_summary:
        speak = f"{speak} {music_dna_summary}"
    analysis = insight.get("analysis") or {}
    summary = str(analysis.get("summary") or "").strip()
    if summary:
        speak = f"{speak} {summary}".strip()
    attribution = analysis.get("source_attribution") or {}
    basis = analysis.get("basis")
    if not navigation and basis == "qualified_credit_and_interpretation_v1":
        labels = {"en": "Interpretation; audio was not measured", "nl": "Interpretatie; de audio is niet gemeten",
            "de": "Interpretation; das Audio wurde nicht gemessen", "fr": "Interprétation ; l’audio n’a pas été mesuré",
            "es": "Interpretación; no se ha medido el audio"}
        speak = f"{labels.get(language,labels['en'])}: {speak}"
    return {
        "success": True,
        "type": "track_insight" if navigation else "message",
        "text": speak,
        "dj_text": speak,
        "message": speak,
        "action": "track_insight" if navigation else "none",
        **({"open_screen": "track_insight", "track_insight": insight, "analysis": insight.get("analysis")} if navigation else {}),
        "items": [],
        "images": [],
        "links": [],
        "sources": [{"source": "track_insight", "title": "DJConnect Track Insight", "kind": "source", "claim_scope": "interpretation_not_measured_audio"}]
                   + ([{**attribution, "kind": "source", "claim_scope": "verified_credit_only"}] if attribution else []),
        "analysis_basis": {"basis": basis, "measured_audio": analysis.get("measured_audio"),
            "verified_context": str(analysis.get("verified_context") or "")[:2000],
            "interpretation": basis == "qualified_credit_and_interpretation_v1"},
        "playback_actions": [],
        "intent": {"category": "informational", "intent": "track_insight", "action": "track_insight" if navigation else "none"},
    }


def _personal_music_dna_summary_text(memory_context: dict[str, Any]) -> str:
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    session = memory_context.get("session") if isinstance(memory_context, dict) else []
    if not isinstance(memory, dict):
        memory = {}
    detail_lines = [
        *_music_dna_mood_lines(memory),
        *_music_dna_preference_lines(memory),
        *_music_dna_playtime_lines(memory),
        *_music_dna_recent_lines(memory),
        *_music_dna_session_lines(memory, session),
    ]
    lines = ["Dit laat je Music DNA nu zien:", *detail_lines]
    if not detail_lines:
        lines.append("- Nog weinig concreets. Zodra je meer vraagt of afspeelt, bouw ik dit compact op.")

    lines.append("")
    lines.append("Ik gebruik hiervoor alleen je Music DNA, niet je live playbackstatus of extra backend-profieldata.")
    lines.append("Privacy: Music DNA bewaart geen raw audio, OAuth tokens of volledige prompts.")
    return "\n".join(lines).strip()


def _music_dna_mood_lines(memory: dict[str, Any]) -> list[str]:
    mood = _profile_mood(memory)
    if mood is None:
        return []
    zone = mood_zone_for_value(mood)
    return [f"- Mood/energy: {mood}/100 ({zone.name}: {zone.prompt_hint})." if zone else f"- Mood/energy: {mood}/100."]


def _music_dna_preference_lines(memory: dict[str, Any]) -> list[str]:
    genres = _memory_text_values(memory.get("favorite_genres"), keys=("name", "genre"))
    artists = _memory_text_values(memory.get("favorite_artists"), keys=("name", "artist", "artist_name"))
    return [*(["- Favorite genres: " + _join_examples(genres, limit=5) + "."] if genres else []), *(["- Artiesten die terugkomen: " + _join_examples(artists, limit=5) + "."] if artists else [])]


def _music_dna_playtime_lines(memory: dict[str, Any]) -> list[str]:
    playtime = memory.get("playtime") if isinstance(memory.get("playtime"), dict) else {}
    if not playtime and (memory.get("total_play_seconds") is not None or isinstance(memory.get("artist_play_seconds"), dict)):
        playtime = _music_dna_playtime_from_memory(memory)
    if not isinstance(playtime, dict) or int(playtime.get("total_seconds") or 0) <= 0:
        return []
    artists = [f"{artist.get('name')} ({artist.get('formatted')})" for artist in playtime.get("top_artists") or [] if isinstance(artist, dict) and artist.get("name") and artist.get("formatted")]
    return [f"- Totale luistertijd: {playtime.get('formatted_total') or str(playtime.get('total_hours')) + ' uur'}.", *(["- Top artiesten op luistertijd: " + _join_examples(artists, limit=3) + "."] if artists else [])]


def _music_dna_recent_lines(memory: dict[str, Any]) -> list[str]:
    examples = _profile_examples(_profile_tracks(memory, {}, {}))
    favorites = _profile_examples([item for item in memory.get("recent_favorite_tracks") or [] if isinstance(item, dict)])
    last_ask = memory.get("last_ask_dj")
    learned = f"- Recent learned from Ask DJ: {last_ask['input']}." if isinstance(last_ask, dict) and last_ask.get("input") else ""
    return [*(["- Recente voorbeelden: " + _join_examples(examples, limit=5) + "."] if examples else []), *(["- Laatst aan favorieten toegevoegd: " + _join_examples(favorites, limit=5) + "."] if favorites else []), *([learned] if learned else [])]


def _music_dna_session_lines(memory: dict[str, Any], session: Any) -> list[str]:
    return [f"- In deze sessie zie ik {len(session)} recente Ask DJ berichten."] if session else []


def _memory_text_values(values: Any, *, keys: tuple[str, ...]) -> list[str]:
    if not isinstance(values, list):
        return []
    counts: dict[str, int] = {}
    for item in values:
        if isinstance(item, dict):
            text = ""
            for key in keys:
                text = str(item.get(key) or "").strip()
                if text:
                    break
        else:
            text = str(item or "").strip()
        if text:
            counts[text] = counts.get(text, 0) + 1
    return [
        value
        for value, _count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )
    ]


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
    guard = await capture_refresh_guard(runtime, payload)
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
        return stored if guard is None or guard.valid() else {}
    try:
        if guard is not None and not guard.valid():
            return {}
        result = await run_music_command(hass, runtime, "listening_profile")
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect listening profile unavailable: %s", exc)
        return stored if isinstance(stored, dict) and (guard is None or guard.valid()) else {}
    if guard is not None and not guard.valid():
        return {}
    profile = result.get("profile") if isinstance(result, dict) else {}
    if isinstance(profile, dict) and profile:
        profile["last_profile_refresh"] = profile.get("last_profile_refresh") or _now_iso()
        if memory is not None:
            try:
                await memory.async_update_listening_profile(runtime, profile, payload, **({"refresh_guard": guard} if guard is not None else {}))
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("DJConnect listening profile memory update failed: %s", exc)
        return profile if guard is None or guard.valid() else {}
    return stored if isinstance(stored, dict) else {}


def _profile_tracks(
    memory: Any,
    playback_context: dict[str, Any],
    listening_profile: dict[str, Any] | None = None,
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
    if isinstance(listening_profile, dict):
        recent = listening_profile.get("recent_tracks")
        if isinstance(recent, list):
            tracks.extend(item for item in recent if isinstance(item, dict))
        top_tracks = listening_profile.get("top_tracks_by_range")
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
    listening_profile: dict[str, Any],
) -> list[str]:
    artists = _top_values(tracks, ("artist", "artist_name"))
    for source in (listening_profile, memory.get("listening_profile") if isinstance(memory, dict) else {}):
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
    listening_profile: dict[str, Any],
) -> str:
    """Return a short user-facing hint that Music DNA/listening profile was used."""
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    if not isinstance(memory, dict):
        memory = {}
    artists = _profile_artists({}, [], listening_profile)
    tracks = memory.get("recent_tracks") if isinstance(memory.get("recent_tracks"), list) else []
    artists.extend(_profile_artists(memory, tracks, {}))
    artists = _unique_ordered(artists)
    artists = [artist for artist in artists if artist][:3]
    if not artists:
        return ""
    return f"Ik zie in je Music DNA en luisterprofiel dat je ook regelmatig naar {_join_human(artists)} luistert."


def _join_human(items: list[str]) -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} en {values[1]}"
    return f"{', '.join(values[:-1])} en {values[-1]}"


def _profile_genres(memory: Any, listening_profile: dict[str, Any]) -> list[str]:
    if not isinstance(memory, dict):
        memory = {}
    genres = memory.get("favorite_genres") or memory.get("genres")
    result = [str(item) for item in genres if item] if isinstance(genres, list) else []
    for source in (listening_profile, memory.get("listening_profile")):
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


def _music_dna_playtime_from_memory(memory: dict[str, Any]) -> dict[str, Any]:
    total_seconds = max(0, int(memory.get("total_play_seconds") or 0))
    artist_seconds = memory.get("artist_play_seconds")
    top_artists: list[dict[str, Any]] = []
    if isinstance(artist_seconds, dict):
        for artist, seconds in sorted(
            artist_seconds.items(),
            key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
        )[:3]:
            value = max(0, int(seconds or 0))
            name = str(artist or "").strip()
            if name and value > 0:
                top_artists.append(
                    {
                        "name": name,
                        "seconds": value,
                        "hours": round(value / 3600, 2),
                        "formatted": _format_playtime_duration(value),
                    }
                )
    return {
        "total_seconds": total_seconds,
        "total_hours": round(total_seconds / 3600, 2),
        "formatted_total": _format_playtime_duration(total_seconds),
        "top_artists": top_artists,
    }


def _format_playtime_duration(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}u {minutes}m"
    if hours:
        return f"{hours}u"
    if minutes:
        return f"{minutes}m"
    return "0m"


def _join_examples(values: list[str], *, limit: int) -> str:
    selected = [str(value) for value in values if value][:limit]
    if len(selected) <= 1:
        return selected[0] if selected else ""
    return ", ".join(selected[:-1]) + " en " + selected[-1]


def _profile_sources(
    memory_context: dict[str, Any],
    listening_profile: dict[str, Any],
) -> list[dict[str, str]]:
    sources = [{"source": "djconnect_music_dna", "kind": "source", "title": "Music DNA"}]
    profile_sources = listening_profile.get("sources") if isinstance(listening_profile, dict) else []
    for source in profile_sources or []:
        text = str(source or "").strip()
        if text:
            sources.append({"source": text, "kind": "source", "title": text.replace("_", " ")})
    if isinstance(memory_context, dict) and memory_context.get("session"):
        sources.append({"source": "ask_dj_session", "kind": "source", "title": "Ask DJ session"})
    return sources


def _recommendation_playback_actions(
    hass: HomeAssistant,
    runtime: Any,
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    listening_profile: dict[str, Any],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    candidates = _recommendation_candidates(memory_context, playback_context, listening_profile)
    random.shuffle(candidates)

    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    reason = _recommendation_reason(memory_context)
    for item in candidates:
        item_id = _playable_item_id(item)
        kind = _playable_item_kind(item, item_id)
        if kind not in {"track", "album", "artist", "playlist", "music"} or not item_id or item_id in seen:
            continue
        seen.add(item_id)
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
        title = str(item.get("track_name") or item.get("title") or item.get("name") or item_id).strip()
        subtitle = str(item.get("artist") or item.get("artist_name") or item.get("album_name") or "").strip()
        action = build_playback_action(
            runtime,
            {
                **item,
                "item_id": item_id,
                "title": title,
                "subtitle": subtitle,
                "image_url": proxy_image,
            },
            kind,
            reason,
        )
        if not action:
            continue
        if kind == "track":
            context_uri = str(item.get("context_uri") or "").strip()
            if context_uri:
                action["context_uri"] = context_uri
                action["offset_uri"] = item_id
        actions.append({key: value for key, value in action.items() if value not in ("", None)})
        if len(actions) >= limit:
            break
    return actions


def _recommendation_candidates(
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    listening_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """Collect playable recommendation candidates from existing contexts."""
    candidates: list[dict[str, Any]] = []
    if isinstance(listening_profile, dict):
        candidates.extend(_listening_profile_candidates(listening_profile))
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    if isinstance(memory, dict):
        candidates.extend(_memory_recommendation_candidates(memory))
    if playback_context:
        candidates.append(playback_context)
    return candidates


def _listening_profile_candidates(listening_profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract typed recommendation candidates from listening-profile data."""
    candidates: list[dict[str, Any]] = []
    for key in ("top_tracks_by_range", "top_artists_by_range"):
        ranges = listening_profile.get(key)
        if not isinstance(ranges, dict):
            continue
        for range_name in ("short_term", "medium_term", "long_term"):
            items = ranges.get(range_name)
            if isinstance(items, list):
                candidates.extend(item for item in items if isinstance(item, dict))
    recent = listening_profile.get("recent_tracks")
    if isinstance(recent, list):
        candidates.extend(item for item in recent if isinstance(item, dict))
    return candidates


def _memory_recommendation_candidates(memory: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract typed recommendation candidates from persisted Music DNA."""
    candidates: list[dict[str, Any]] = []
    recent = memory.get("recent_tracks")
    if isinstance(recent, list):
        candidates.extend(item for item in recent if isinstance(item, dict))
    for key in ("favorite_artists", "favorite_genres", "favorite_playlists"):
        values = memory.get(key)
        if isinstance(values, list):
            candidates.extend(
                item if isinstance(item, dict) else {"name": str(item), "source": key}
                for item in values
                if item
            )
    return candidates


def _personal_artist_recommendation_actions(
    hass: HomeAssistant,
    runtime: Any,
    memory_context: dict[str, Any],
    listening_profile: dict[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    candidates = _personal_artist_candidates(memory_context, listening_profile)
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        action = _personal_artist_recommendation_action(hass, runtime, item, seen)
        if not action:
            continue
        actions.append(action)
        if len(actions) >= limit:
            break
    return actions


def _personal_artist_candidates(
    memory_context: dict[str, Any], listening_profile: dict[str, Any]
) -> list[dict[str, Any]]:
    """Collect artist candidates from listening data and Music DNA."""
    candidates: list[dict[str, Any]] = []
    top_artists = listening_profile.get("top_artists_by_range") if isinstance(listening_profile, dict) else {}
    if isinstance(top_artists, dict):
        for range_name in ("short_term", "medium_term", "long_term"):
            items = top_artists.get(range_name)
            if isinstance(items, list):
                candidates.extend(item for item in items if isinstance(item, dict))
    memory = memory_context.get("memory") if isinstance(memory_context, dict) else {}
    if isinstance(memory, dict):
        values = memory.get("favorite_artists")
        if isinstance(values, list):
            candidates.extend(
                item if isinstance(item, dict) else {"name": str(item), "source": "favorite_artists"}
                for item in values
                if item
            )
    return candidates


def _personal_artist_recommendation_action(
    hass: HomeAssistant, runtime: Any, item: dict[str, Any], seen: set[str]
) -> dict[str, Any] | None:
    """Build a deduplicated artist recommendation action."""
    name = str(item.get("name") or item.get("artist") or item.get("artist_name") or "").strip()
    if not name:
        return None
    key = _normalize(name)
    if key in seen:
        return None
    seen.add(key)
    item_id = _playable_item_id(item)
    image_url = str(
        item.get("image_url") or item.get("artist_image_url") or item.get("thumbnail_url")
        or item.get("entity_picture") or ""
    ).strip()
    proxy_image = register_image_proxy_url(hass, image_url) if image_url.startswith(("http://", "https://")) else image_url
    genres = item.get("genres")
    subtitle = ", ".join(str(genre) for genre in genres[:2]) if isinstance(genres, list) else ""
    action = build_playback_action(
        runtime,
        {**item, "item_id": item_id or f"djconnect:artist:{key}", "title": name, "subtitle": subtitle, "image_url": proxy_image},
        "artist", "Past bij je luisterprofiel en Music DNA.",
    )
    if not action:
        return None
    if not item_id:
        action.update(label="", button_label="", action_style="info")
    return {field: value for field, value in action.items() if value not in ("", None, [])}


def _play_now_action_from_spotify_item(
    hass: HomeAssistant,
    item: dict[str, Any],
    *,
    runtime: Any | None = None,
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
    title = str(item.get("track_name") or item.get("title") or item.get("name") or uri).strip()
    subtitle = str(
        item.get("artist")
        or item.get("artist_name")
        or item.get("album_name")
        or item.get("subtitle")
        or item.get("owner")
        or ""
    ).strip()
    if _looks_like_spotify_uri(title):
        title = subtitle or "Spotify resultaat"
        subtitle = ""
    if _looks_like_spotify_uri(subtitle):
        subtitle = ""
    action = build_playback_action(
        runtime or _first_runtime(hass),
        {
            **item,
            "uri": uri,
            "title": title,
            "subtitle": subtitle,
            "image_url": proxy_image,
            "thumbnail_url": proxy_image,
        },
        kind,
        "Voor je klaargezet terwijl het huidige nummer doorspeelt.",
    )
    if not action:
        return {}
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
    sources: list[dict[str, Any]] = []
    provided = result.get("sources")
    for item in (provided[:12] if isinstance(provided, list) else []):
        if isinstance(item, dict):
            provider = str(item.get("provider") or item.get("source") or item.get("title") or "source")[:128]
            source = {"source": provider, "title": str(item.get("title") or provider)[:256], "kind": "source"}
            for key in ("provider", "license", "claim_scope", "language", "fetched_at", "expires_at", "content_hash", "wikidata_id"):
                if isinstance(item.get(key), str):
                    source[key] = item[key][:128]
            revision_url = item.get("revision_url")
            if item.get("claim_scope") == "fetched_public_music_reference":
                from .public_research import public_url
                if isinstance(revision_url, str) and public_url(revision_url):
                    source["revision_url"] = revision_url
            url = item.get("url")
            if isinstance(url, str) and len(url) <= 2048:
                try:
                    parsed = urlsplit(url)
                    safe = parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
                except ValueError:
                    safe = False
                if safe:
                    source["url"] = url
                    if not any(link.get("url") == url for link in links):
                        links.append({"url": url, "title": source["title"], "kind": "source", "source": provider,
                                      **{key: source[key] for key in ("license", "claim_scope") if key in source}})
            sources.append(source)
        elif isinstance(item, str) and item:
            sources.append({"source": item[:128], "title": item[:256], "kind": "source"})
    for link in links[:12]:
        if isinstance(link, dict) and (link.get("kind") == "source" or link.get("source") == "source"):
            if any(source.get("url") == link.get("url") for source in sources if source.get("url")):
                continue
            sources.append({"source": str(link.get("source") or link.get("title") or "source")[:128],
                            "title": str(link.get("title") or link.get("source") or "Source")[:256], "kind": "source"})
    return sources


def _profile_limited(listening_profile: dict[str, Any]) -> bool:
    recent = listening_profile.get("recent_tracks")
    top_tracks = listening_profile.get("top_tracks_by_range")
    top_artists = listening_profile.get("top_artists_by_range")
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
    payload = _apply_mood_voice_profile(runtime, payload)
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    status = getattr(runtime, "device_status", {}) or {}
    return {
        CONF_DEVICE_ID: payload.get(CONF_DEVICE_ID) or identity.get(CONF_DEVICE_ID) or status.get(CONF_DEVICE_ID),
        CONF_CLIENT_TYPE: payload.get(CONF_CLIENT_TYPE) or identity.get(CONF_CLIENT_TYPE) or status.get(CONF_CLIENT_TYPE),
        CONF_DEVICE_NAME: payload.get(CONF_DEVICE_NAME) or identity.get(CONF_DEVICE_NAME) or status.get(CONF_DEVICE_NAME),
        "music_dna_key": payload.get("music_dna_key") or identity.get("music_dna_key"),
        "mood": payload.get("mood") if payload.get("mood") is not None else payload.get("energy"),
        "mood_zone": payload.get("mood_zone"),
        "mood_zone_prompt": payload.get("mood_zone_prompt"),
        "dj_style": payload.get("dj_style"),
        "preferred_device_id": payload.get("preferred_device_id"),
    }


def _apply_mood_voice_profile(runtime: Any, payload: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(payload)
    profile = voice_profile_for_mood_or_config(getattr(runtime, "config", {}) or {}, resolved)
    resolved["voice_profile"] = profile
    resolved.setdefault("dj_style", profile)
    return resolved


async def _playback_context(hass: HomeAssistant, runtime: Any) -> dict[str, Any]:
    try:
        result = await async_call_ai_tool(hass, runtime, "djconnect_now_playing")
        playback = result.get("playback") if isinstance(result, dict) else {}
        if isinstance(playback, dict):
            updater = getattr(runtime, "update", None)
            if callable(updater):
                updater(last_playback=playback)
            else:
                setattr(runtime, "last_playback", playback)
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
        result = await async_call_ai_tool(hass, runtime, "djconnect_list_outputs")
        from .dialogue import DialogueError
        if not isinstance(result, dict) or result.get("success") is False or not isinstance(result.get("outputs"), list):
            raise DialogueError("output_read_unavailable", 503)
        return [d for d in result["outputs"] if isinstance(d, dict)
                and isinstance(d.get("id"), str) and 0 < len(d["id"].strip()) <= 128
                and not d.get("cached") and not d.get("is_restricted")]
    except Exception as exc:  # noqa: BLE001
        from .dialogue import DialogueError
        if isinstance(exc, DialogueError):
            raise
        raise DialogueError("output_read_unavailable", 503) from exc


def _informational_prompt(
    text: str,
    payload: dict[str, Any],
    memory_context: dict[str, Any],
    playback_context: dict[str, Any],
    output_devices: list[dict[str, Any]],
    conf: dict[str, Any] | None = None,
) -> str:
    from .dialogue import model_prompt
    return model_prompt(text, payload)


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


def _looks_like_internal_prompt_leak(text: str) -> bool:
    """Return whether Assist echoed DJConnect's hidden prompt instead of answering."""
    normalized = _normalize(text)
    if not normalized:
        return False
    leak_markers = (
        "je bent djconnect ask dj",
        "you are djconnect ask dj",
        "beantwoord informatieve muziekvragen",
        "answer informational music questions",
        "zonder playback te wijzigen",
        "without changing playback",
        "gebruik alleen meegegeven context",
        "use only provided context",
        "betrouwbare kennis die je al hebt",
        "reliable knowledge you already have",
        "verzin geen trivia",
        "do not invent trivia",
        "als bronnen beschikbaar zijn",
        "when sources are available",
        "musicbrainz wikidata",
        "last fm discogs",
        "theaudiodb",
        "gebruik de recente ask dj gespreksgeschiedenis",
        "use the recent ask dj conversation history",
        "geef een kort natuurlijk antwoord",
        "give a short natural answer",
        "voor een chat ui",
        "for a chat ui",
        "voice profile",
        "klink als",
        "sound like",
        "mood energy",
        "mood:",
        "vraag:",
        "question:",
    )
    matches = sum(1 for marker in leak_markers if marker in normalized)
    if matches >= 2:
        return True
    device_error = (
        "geen apparaat vinden" in normalized
        or "kan geen apparaat" in normalized
        or "can't find" in normalized
        or "cannot find" in normalized
        or "no device" in normalized
    )
    return device_error and matches >= 1


def _images_from_context(
    hass: HomeAssistant,
    result: dict[str, Any],
    playback_context: dict[str, Any],
) -> list[dict[str, Any]]:
    images = _provided_images(hass, result.get("images"))
    album_art = _context_album_art_image(
        hass, (result, *_nested_image_sources(result), playback_context),
    )
    return [*images, *([album_art] if album_art else [])]


def _provided_images(hass: HomeAssistant, provided: Any) -> list[dict[str, Any]]:
    if not isinstance(provided, list):
        return []
    images = []
    for item in provided:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("thumbnail_url")
        if not url:
            continue
        proxy = register_image_proxy_url(hass, str(url))
        images.append({"url": proxy, "thumbnail_url": proxy, "title": str(item.get("title") or "Image"), "subtitle": str(item.get("subtitle") or ""), "kind": str(item.get("kind") or "image"), "source": str(item.get("source") or "source")})
    return images


def _nested_image_sources(result: dict[str, Any]) -> list[dict[str, Any]]:
    sources = []
    for key in ("playback", "media", "resolved_media", "track"):
        nested = result.get(key)
        if not isinstance(nested, dict):
            continue
        sources.append(nested)
        for nested_key in ("resolved_media", "media", "track", "device_response"):
            child = nested.get(nested_key)
            if isinstance(child, dict):
                sources.append(child)
                if isinstance(child.get("playback"), dict):
                    sources.append(child["playback"])
    return sources


def _context_album_art_image(
    hass: HomeAssistant, sources: tuple[Any, ...],
) -> dict[str, Any] | None:
    for source in sources:
        image = _album_art_image_for_source(hass, source)
        if image:
            return image
    return None


def _album_art_image_for_source(hass: HomeAssistant, source: Any) -> dict[str, Any] | None:
    if not isinstance(source, dict):
        return None
    url = source.get("album_image_url") or source.get("media_image_url") or source.get("image_url") or source.get("thumbnail_url")
    if not url and isinstance(source.get("track"), dict):
        track = source["track"]
        url = track.get("album_image_url") or track.get("image_url") or track.get("thumbnail_url")
    if not url:
        return None
    proxy = register_image_proxy_url(hass, str(url))
    return {"url": proxy, "thumbnail_url": proxy, "title": source.get("track_name") or source.get("title") or source.get("name") or "Album art", "subtitle": source.get("artist") or source.get("artist_name") or source.get("album_name") or "", "kind": "album_art", "source": "spotify"}


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
    uri = result.get("uri")
    if "links" not in result and _should_use_playback_context_images(result, classification):
        uri = uri or playback_context.get("uri") or playback_context.get("track_uri")
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


def _playable_item_id(item: dict[str, Any]) -> str:
    for key in (
        "uri",
        "current_uri",
        "context_uri",
        "playlist_uri",
        "album_uri",
        "artist_uri",
        "item_id",
        "media_content_id",
        "id",
    ):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def _playable_item_kind(item: dict[str, Any], item_id: str) -> str:
    spotify_kind = _spotify_uri_kind(item_id)
    if spotify_kind:
        return spotify_kind
    kind = str(
        item.get("media_type")
        or item.get("type")
        or item.get("kind")
        or "music"
    ).strip().lower()
    return kind if kind in {"track", "album", "artist", "playlist"} else "music"


def _first_runtime(hass: HomeAssistant) -> Any | None:
    domain_data = getattr(hass, "data", {}).get(DOMAIN, {})
    if not isinstance(domain_data, dict):
        return None
    for key, value in domain_data.items():
        if key == IMAGE_PROXY_KEY or not hasattr(value, "config"):
            continue
        return value
    return None


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
            "title": "Muziek hervatten",
            "label": "Muziek hervatten",
            "button_label": "Muziek hervatten",
            "prompt": "Start muziek",
            "reason": "De muziek is gepauzeerd.",
        }
    ]


def _volume_control_actions() -> list[dict[str, Any]]:
    return [
        {
            "id": "djconnect:control:volume:-10",
            "kind": "control",
            "action_style": "control",
            "command": "volume_delta",
            "value": -10,
            "title": "Zachter",
            "label": "Zachter",
            "button_label": "Zachter",
            "prompt": "Zachter",
            "reason": "Volume zachter zetten vanuit Ask DJ.",
        },
        {
            "id": "djconnect:control:volume:+10",
            "kind": "control",
            "action_style": "control",
            "command": "volume_delta",
            "value": 10,
            "title": "Harder",
            "label": "Harder",
            "button_label": "Harder",
            "prompt": "Harder",
            "reason": "Volume harder zetten vanuit Ask DJ.",
        },
    ]


def _artist_more_media_action(artist: str) -> dict[str, Any]:
    artist = str(artist or "").strip()
    if not artist:
        return {}
    prompt = f"Meer van {artist}"
    title = "Meer van deze artiest"
    return {
        "id": f"djconnect:artist_more:{_normalize(artist).replace(' ', '-')}",
        "kind": "control",
        "action_style": "control",
        "command": "ask_dj_message",
        "value": {"text": prompt, "prompt": prompt},
        "text": prompt,
        "title": title,
        "label": title,
        "button_label": title,
        "prompt": prompt,
        "client_prompt": prompt,
        "reason": "Vraag Ask DJ om meer albums, playlists en tracks van deze artiest.",
    }


def _confirmation_actions(
    *,
    yes_title: str = "Ja",
    no_title: str = "Nee",
) -> list[dict[str, Any]]:
    return [
        {
            "id": "ask_dj_followup_yes",
            "title": yes_title,
            "label": yes_title,
            "button_label": yes_title,
            "kind": "confirmation",
            "action_style": "confirmation",
            "response_value": "yes",
            "command": "ask_dj_followup_response",
        },
        {
            "id": "ask_dj_followup_no",
            "title": no_title,
            "label": no_title,
            "button_label": no_title,
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
    from .dialogue import current_turn, CHOICE_SECONDS, MAX_PENDING_BYTES, encoded_size, DialogueError
    turn = current_turn.get()
    if turn is None:
        return
    await turn.guard()
    pending = {"type":"playback_confirmation","question":question,
        "proposed_intent":proposed_intent,"proposed_action":proposed_action,
        "proposed_payload":proposed_payload,"deadline":turn.history.dialogue.clock()+CHOICE_SECONDS,
        "session_id":turn.session_id}
    if encoded_size(pending) > MAX_PENDING_BYTES:
        raise DialogueError("conversation_context_too_large",413)
    turn.pending = pending


async def _available_output_devices(hass: HomeAssistant, runtime: Any) -> list[dict[str, Any]]:
    try:
        result = await run_music_command(hass, runtime, "devices")
        devices = result.get("devices") if isinstance(result, dict) else []
        if isinstance(devices, list) and devices:
            return [device for device in devices if isinstance(device, dict)]
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Spotify output lookup unavailable: %s", exc)
    status = getattr(runtime, "device_status", {}) or {}
    devices = status.get("available_outputs")
    return [device for device in devices if isinstance(device, dict)] if isinstance(devices, list) else []


def _looks_like_no_active_output_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    return any(
        term in message
        for term in (
            "no active device",
            "no active spotify device",
            "spotify device unavailable",
            "no active output",
            "geen actieve",
            "geen spotify apparaat",
            "geen speaker",
        )
    )


def _output_device_play_request_actions(
    devices: list[dict[str, Any]],
    text: str,
    payload: dict[str, Any],
    *,
    selection: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    request_payload = {
        key: value
        for key, value in {
            "text": text,
            "client_type": payload.get("client_type"),
            "client_id": payload.get("client_id"),
            "device_id": payload.get("device_id"),
            "device_name": payload.get("device_name"),
            "music_dna_key": payload.get("music_dna_key"),
            "mood": payload.get("mood"),
            "mood_zone": payload.get("mood_zone"),
            "audio_response": payload.get("audio_response"),
        }.items()
        if value not in ("", None)
    }
    # Only a producer resolution may supply this state. Caller payloads are
    # never media authority, even when incorporated into a server-owned offer.
    if isinstance(selection, dict):
        request_payload["_frozen_playback_selection"] = deepcopy(selection)
    for device in devices:
        if not isinstance(device, dict):
            continue
        device_id = str(device.get("id") or "").strip()
        name = str(device.get("name") or "").strip()
        if not device_id or not name or device_id in seen:
            continue
        seen.add(device_id)
        device_type = str(device.get("type") or "Spotify Connect").strip()
        actions.append(
            {
                key: value
                for key, value in {
                    "id": f"play_request_on_output:{device_id}",
                    "title": name,
                    "subtitle": device_type,
                    "label": "Speel hier",
                    "button_label": "Speel hier",
                    "kind": "output",
                    "command": "ask_dj_play_request_on_output",
                    "value": {
                        "output_id": device_id,
                        "device_id": device_id,
                        "device_name": name,
                        "request": request_payload,
                    },
                    "device_id": device_id,
                    "device_name": name,
                    "reason": "Kies deze Spotify Connect speaker en start daarna het Ask DJ playbackverzoek.",
                }.items()
                if value not in ("", None)
            }
        )
        if len(actions) >= 8:
            break
    return actions


def _playback_failed_text(runtime: Any, text: str = "", payload: dict[str, Any] | None = None) -> str:
    """The confirmed conversation/request language also owns failure replies."""
    from .dialogue import current_turn
    turn = current_turn.get()
    payload = payload if isinstance(payload, dict) else {}
    has_locale = any(str(payload.get(key) or "").lower().replace("_", "-").split("-", 1)[0]
                     in {"en", "nl", "de", "fr", "es"}
                     for key in ("language", "locale", "device_language"))
    if turn is not None:
        language = turn.style["language"]
    elif has_locale:
        language = _response_language(runtime, payload)
    elif _looks_dutch(_normalize(text)):
        language = "nl"
    else:
        language = _response_language(runtime)
    return {
        "en": "I understood your music request, but Spotify could not start it right now.",
        "nl": "Ik heb je muziekverzoek begrepen, maar Spotify kon het nu niet starten.",
        "de": "Ich habe deinen Musikwunsch verstanden, aber Spotify konnte ihn gerade nicht starten.",
        "fr": "J’ai compris ta demande musicale, mais Spotify n’a pas pu lancer la lecture pour le moment.",
        "es": "He entendido tu petición musical, pero Spotify no ha podido iniciar la reproducción ahora.",
    }[language]


def _is_help_request(normalized: str) -> bool:
    normalized = str(normalized or "").strip(" ?.!'\"")
    if normalized in {
        "help",
        "hulp",
        "help me even",
        "help ask dj",
        "show help",
        "wat kan je",
        "wat kun je",
        "wat kan je allemaal",
        "wat kan ik vragen",
        "wat kun je doen",
        "toon hulp",
        "laat hulp zien",
        "welke commando's",
        "welke commandos",
        "welke commando's kan ik gebruiken",
        "welke commandos kan ik gebruiken",
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
            "geef me voorbeelden",
            "wat kan djconnect",
            "wat kan ask dj",
        )
    )


def _is_conversational_followup_request(normalized: str) -> bool:
    return str(normalized or "").strip(" ?.!'\"") in {
        "ok",
        "oke",
        "prima",
        "top",
        "dank je",
        "thanks",
        "laat maar",
        "nee laat maar",
        "geeft niet",
        "maakt niet uit",
        "helemaal goed",
        "oké dank je",
        "oke dank je",
        "never mind",
        "no worries",
    }


def _response_language(runtime: Any = None, payload: dict[str, Any] | None = None) -> str:
    """Return one of the supported user-facing response languages."""
    payload = payload if isinstance(payload, dict) else {}
    for candidate in (
        payload.get("language"),
        payload.get("locale"),
        payload.get("device_language"),
        getattr(runtime, "device_language", None)() if callable(getattr(runtime, "device_language", None)) else None,
    ):
        language = str(candidate or "").strip().lower().replace("_", "-")
        if language.startswith(("nl", "de", "fr", "es")):
            return language[:2]
        if language.startswith("en"):
            return "en"
    return "nl"


def _help_sections(language: str = "nl", context=None) -> list[tuple[str, list[str]]]:
    from .example_catalogue import help_sections
    return help_sections(language, context)


def _help_response(language: str = "nl", context=None) -> dict[str, Any]:
    from .example_catalogue import help_text
    message = help_text(language, context)
    return {
        "success": True, "text": message, "dj_text": message, "action": "none",
        "intent": {"category": "informational", "intent": "help"},
        "images": [], "links": [], "sources": [], "playback_actions": [],
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


def _devices_text(devices: list[dict[str, Any]], language: str = "nl") -> str:
    names = [str(device.get("name")) for device in devices if isinstance(device, dict) and device.get("name")]
    labels = {
        "en": ("No speakers are currently available.", "Currently available speakers:"),
        "nl": ("Er zijn nu geen speakers beschikbaar.", "Momenteel beschikbare speakers:"),
        "de": ("Derzeit sind keine Lautsprecher verfügbar.", "Derzeit verfügbare Lautsprecher:"),
        "fr": ("Aucune enceinte n’est disponible actuellement.", "Enceintes actuellement disponibles :"),
        "es": ("No hay altavoces disponibles ahora.", "Altavoces disponibles ahora:"),
    }
    empty, title = labels.get(language, labels["en"])
    if not names:
        return empty
    return title + "\n\n" + "\n".join(f"- {name}" for name in names)


def _is_output_selection_request(normalized: str) -> bool:
    if (
        "welke speakers" in normalized
        or "welke apparaten" in normalized
        or "welke outputs" in normalized
        or "laat speakers zien" in normalized
        or "toon beschikbare speakers" in normalized
        or "toon outputs" in normalized
        or any(term in normalized for term in ("which speakers", "available speakers", "show outputs", "welche speaker", "welche lautsprecher", "verfügbare lautsprecher", "quelles enceintes", "enceintes disponibles", "qué altavoces", "altavoces disponibles"))
    ):
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


def _output_device_actions(devices: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    labels = {"en": ("Active", "Activate", "Active output"), "nl": ("Actief", "Activeer", "Actieve uitvoer"),
              "de": ("Aktiv", "Aktivieren", "Aktive Ausgabe"), "fr": ("Active", "Activer", "Sortie active"),
              "es": ("Activo", "Activar", "Salida activa")}
    active_label, activate_label, active_subtitle = labels.get(language, labels["en"])
    for device in devices:
        if not isinstance(device, dict):
            continue
        device_id = str(device.get("id") or "").strip()
        name = str(device.get("name") or "").strip()
        if not device_id or not name or device_id in seen or device.get("is_restricted") or device.get("cached"):
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
                    "subtitle": active_subtitle if is_active else device_type,
                    "label": active_label if is_active else activate_label,
                    "kind": "output",
                    "command": "set_output",
                    "value": device_id,
                    "device_id": device_id,
                    "device_name": name,
                    "active": is_active,
                    "backend": device.get("backend") or device.get("provider") or "spotify_direct",
                    "provider": device.get("provider") or device.get("source") or "spotify",
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


def _playback_status_response(
    text: str, playback: dict[str, Any], runtime: Any
) -> dict[str, Any]:
    normalized = _normalize(text)
    selected_backend = (
        getattr(runtime, "profile_context_backend_id", "")
        or getattr(runtime, "config", {}).get(CONF_MUSIC_BACKEND)
    )
    manual_backend = selected_backend == MUSIC_BACKEND_LATER_MANUAL
    if "shuffle" in normalized:
        enabled = _playback_shuffle_enabled(playback)
        message = (
            "Shuffle staat aan."
            if enabled is True
            else "Shuffle staat uit."
            if enabled is False
            else "Ik kan nu niet zien of shuffle aan staat."
        )
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "images": [],
            "links": [],
            "sources": [],
            "items": [],
            "audio_url": None,
            "playback_actions": [] if manual_backend else [_shuffle_toggle_action(enabled)],
        }
    if "repeat" in normalized or "herhaal" in normalized:
        repeat_state = _playback_repeat_state(playback)
        message = _repeat_status_text(repeat_state)
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "images": [],
            "links": [],
            "sources": [],
            "items": [],
            "audio_url": None,
            "playback_actions": [] if manual_backend else _repeat_option_actions(repeat_state),
        }
    message = _current_output_text(playback)
    return {"success": True, "text": message, "dj_text": message}


def _playback_shuffle_enabled(playback: dict[str, Any]) -> bool | None:
    for key in ("shuffle", "shuffle_state", "shuffleState", "shuffle_enabled", "shuffleEnabled"):
        if key not in playback:
            continue
        value = playback.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "on", "aan", "1", "yes"}:
                return True
            if normalized in {"false", "off", "uit", "0", "no"}:
                return False
    return None


def _playback_repeat_state(playback: dict[str, Any]) -> str:
    for key in ("repeat", "repeat_state", "repeatState", "repeat_mode", "repeatMode"):
        value = str(playback.get(key) or "").strip().lower()
        if value in {"off", "track", "context"}:
            return value
        if value in {"uit", "none", "false", "0"}:
            return "off"
        if value in {"nummer", "song", "one"}:
            return "track"
        if value in {"alles", "all", "aan", "on", "true"}:
            return "context"
    return "unknown"


def _repeat_status_text(state: str) -> str:
    return {
        "off": "Repeat staat uit.",
        "track": "Repeat staat op dit nummer.",
        "context": "Repeat staat aan voor de huidige context.",
    }.get(state, "Ik kan nu niet zien hoe repeat staat.")


def _shuffle_toggle_action(enabled: bool | None) -> dict[str, Any]:
    next_value = False if enabled is True else True
    title = "Shuffle uitzetten" if enabled is True else "Shuffle aanzetten"
    return {
        "id": f"djconnect:control:set_shuffle:{str(next_value).lower()}",
        "kind": "control",
        "action_style": "control",
        "command": "set_shuffle",
        "value": next_value,
        "title": title,
        "label": title,
        "button_label": title,
        "prompt": title,
        "reason": "Shuffle wijzigen vanuit Ask DJ.",
    }


def _repeat_option_actions(current: str) -> list[dict[str, Any]]:
    options = (
        ("off", "Repeat uitzetten"),
        ("track", "Repeat nummer"),
        ("context", "Repeat alles"),
    )
    actions = []
    for value, title in options:
        active = value == current
        label = "Actief" if active else title
        actions.append(
            {
                "id": f"djconnect:control:set_repeat:{value}",
                "kind": "control",
                "action_style": "control",
                "command": "set_repeat",
                "value": value,
                "title": title,
                "label": label,
                "button_label": label,
                "prompt": title,
                "active": active,
                "disabled": active,
                "reason": "Repeat wijzigen vanuit Ask DJ.",
            }
        )
    return actions


def _track_label(playback: dict[str, Any]) -> str:
    artist = playback.get("artist") or playback.get("artist_name")
    title = playback.get("track_name") or playback.get("title") or playback.get("name")
    return " - ".join(str(value) for value in (artist, title) if value)


def _safe_inline_context(value: Any) -> str:
    text = str(value)
    return text[:1200]


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _error_response(error: str, message: str, *, music_dna_key: str | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": error,
        "message": message,
        "text": message,
        "dj_text": message,
        "images": [],
        "links": [],
        "music_dna_key": music_dna_key,
    }


async def _call_dialogue_agent(hass, data):
    """One existing HA transport owns budgets, source fences and fresh agent cleanup."""
    return await call_conversation_process_with_agent_retry(hass, data)


async def _realize_dialogue_plan(hass, runtime, payload, text, response, plan):
    """Only existing qualified catalog tools produce cards; model text grants no URI/effect."""
    from .dialogue import current_turn, requests_lookup, DialogueError
    turn = current_turn.get()
    if turn is None:
        return response
    if plan.get("intent") == "choose":
        from .dialogue import choice_index
        if choice_index(text) is not None and choice_index(text) == plan.get("index"):
            return await _dialogue_choice_response(hass, runtime, payload, text, index=plan["index"]) or response
        return response
    # A refinement is read-only; open requests never execute a model proposal.
    if plan.get("intent") not in {"lookup", "refine"} or not plan.get("query"):
        return response
    if not requests_lookup(text):
        return response
    await turn.guard()
    if turn.lookup_calls >= 2:
        raise DialogueError("conversation_lookup_budget", 503)
    turn.lookup_calls += 1
    found = await _spotify_track_search(hass, runtime, plan["query"], limit=8)
    await turn.guard()
    if not isinstance(found, dict) or found.get("success") is False or not isinstance(found.get("tracks"), list):
        raise DialogueError("conversation_lookup_unavailable", 503)
    actions = _track_recommendation_actions(hass, found.get("tracks") or [], limit=8, runtime=runtime)
    # The semantic query is model-assisted; only actual catalog rows authorize
    # the result caption. Generated track suggestions cannot masquerade as rows.
    language = turn.style.get("language", "en")
    captions = {"en": "Found {count} {unit} for {query}.", "nl": "{count} {unit} gevonden voor {query}.",
        "de": "{count} {unit} für {query} gefunden.", "fr": "Recherche : {query} · {count} {unit}.",
        "es": "Búsqueda: {query} · {count} {unit}."}
    units = {"en": ("track", "tracks"), "nl": ("nummer", "nummers"), "de": ("Titel", "Titel"),
        "fr": ("morceau", "morceaux"), "es": ("canción", "canciones")}
    count = len(actions)
    caption = captions[language].format(count=count, unit=units[language][count != 1], query=plan["query"])
    from .dialogue import catalogue_result_text
    message = catalogue_result_text(actions, language, caption=caption) if actions else caption
    response.pop("model_processing_basis", None)
    return {**response, "text": message, "dj_text": message, "text_source": "qualified_catalog_result",
            "_catalogue_history_caption": caption,
            "knowledge_basis": "qualified_provider_result_fields", "query_basis": "model_assisted_user_request",
            "is_generated_text": False, "items": actions, "playback_actions": actions,
            "sources": [{"source": "spotify_track_search", "title": "Spotify", "kind": "source"}]}


async def _dialogue_album_period_response(hass, payload, text):
    """Refine a live bounded album offer using structured catalog dates only."""
    from .dialogue import current_turn, catalogue_result_text, DialogueError
    turn = current_turn.get()
    match = re.fullmatch(r"(?:alleen tussen|only between|nur zwischen|seulement entre|solo entre)\s+(\d{4})\s+(?:en|and|und|et|y)\s+(\d{4})[.!?]*", text.strip(), re.I)
    if turn is None or not match or turn.source_context or turn.reset_topic:
        return None
    shown = turn.frame.result_set
    if shown is None:
        # Neither old captions nor a cleared/expired offer qualify the subject.
        language = turn.style.get('language','en')
        labels = {
            'en':'Please request an album list first; the earlier selection is no longer available.',
            'nl':'Vraag eerst een albumlijst op; de eerdere selectie is niet meer beschikbaar.',
            'de':'Frage zuerst nach einer Albumliste; die frühere Auswahl ist nicht mehr verfügbar.',
            'fr':'Demande d’abord une liste d’albums ; la sélection précédente n’est plus disponible.',
            'es':'Pide primero una lista de álbumes; la selección anterior ya no está disponible.',
        }
        return {'success':True,'text':labels[language],'dj_text':labels[language],'action':'none','items':[],'playback_actions':[],
                'knowledge_basis':'public_subject_required','is_generated_text':False,
                'intent':{'category':'informational','intent':'ask_music_info'}}
    if turn.history.dialogue.clock() >= shown['deadline']:
        raise DialogueError('choice_expired')
    expected = (payload.get('conversation_context') or {}).get('result_set_id')
    if expected and expected != shown['result_set_id']:
        raise DialogueError('choice_changed')
    start, end = map(int,match.groups())
    if start > end or not shown['items'] or any(a.get('kind')!='album' for a in shown['items']):
        return None
    await turn.guard()
    missing = sum(not re.match(r'^\d{4}(?:-|$)',str(a.get('release_date') or '')) for a in shown['items'])
    selected = [deepcopy(a) for a in shown['items'] if re.match(r'^\d{4}(?:-|$)',str(a.get('release_date') or ''))
                and start <= int(a['release_date'][:4]) <= end]
    original_items = deepcopy(shown['items'])
    def validate_offer_evidence():
        if turn.history.dialogue.clock() >= shown['deadline']:
            raise DialogueError('choice_expired')
        if shown['generation'] != turn.generation:
            raise DialogueError('choice_changed')
        if shown.get('session_id'):
            from ..session_runtime import session_runtime_manager
            active = session_runtime_manager(hass).current_active(turn.scope.removeprefix('profile:'))
            if active is None or active.session_id != shown['session_id']:
                raise DialogueError('choice_expired')
    def validate_offer():
        validate_offer_evidence()
        if turn.frame.result_set is not shown or shown['items'] != original_items:
            raise DialogueError('choice_changed')
    validate_offer_evidence.speech_deadline = shown['deadline']
    turn.delivery_validators.append(validate_offer_evidence)
    turn.effect_validators.append(validate_offer)
    turn.replacement_result_deadline = shown['deadline']
    turn.clear_result_set = not selected
    language = turn.style.get('language','en')
    labels = {
        'en':'Of the shown catalog editions, these are dated {start}–{end}. Missing dates: {missing}.',
        'nl':'Van de getoonde catalogusuitgaven vallen deze in {start}–{end}. Ontbrekende datums: {missing}.',
        'de':'Von den angezeigten Katalogausgaben stammen diese aus {start}–{end}. Fehlende Daten: {missing}.',
        'fr':'Parmi les éditions affichées, celles-ci datent de {start}–{end}. Dates manquantes : {missing}.',
        'es':'De las ediciones mostradas, estas datan de {start}–{end}. Fechas ausentes: {missing}.',
    }
    caption=labels[language].format(start=start,end=end,missing=missing)
    message = catalogue_result_text(selected,language,caption=caption)
    return {'success':True,'text':message,'dj_text':message,
            'action':'none','items':selected,'playback_actions':selected,'images':[],
            'text_source':'qualified_catalog_result','is_generated_text':False,'_private_current_context':True,
            'filtering_coverage':{'basis':'shown_catalog_editions','input_items':len(shown['items']),
                                  'missing_date':missing,'matched':len(selected)},
            'intent':{'category':'informational','intent':'shown_result_list'}}


async def _dialogue_result_list_response(hass, payload, text):
    """Re-present frozen local results without extending or selecting the offer."""
    from .dialogue import current_turn, result_list_requested, catalogue_result_text, DialogueError
    turn = current_turn.get()
    if turn is None or turn.reset_topic or turn.source_context or not result_list_requested(text):
        return None
    shown = turn.frame.result_set
    language = turn.style.get("language", "en")
    if shown is None:
        labels = {
            "en": "The earlier result list is no longer available. Ask for results again.",
            "nl": "De eerdere keuzelijst is niet meer beschikbaar. Vraag de resultaten opnieuw op.",
            "de": "Die frühere Ergebnisliste ist nicht mehr verfügbar. Frage erneut nach den Ergebnissen.",
            "fr": "La liste précédente n’est plus disponible. Demande à nouveau les résultats.",
            "es": "La lista anterior ya no está disponible. Vuelve a pedir los resultados.",
        }
        message = labels[language]
        return {"success": True, "text": message, "dj_text": message, "action": "none",
                "items": [], "playback_actions": [], "is_generated_text": False,
                "text_source": "qualified_catalog_result", "_private_current_context": True,
                "intent": {"category": "informational", "intent": "result_list_unavailable"}}
    expected = (payload.get("conversation_context") or {}).get("result_set_id")
    if expected and expected != shown["result_set_id"]:
        raise DialogueError("choice_changed")
    items = deepcopy(shown["items"])

    def validate_offer():
        if turn.history.dialogue.clock() >= shown["deadline"]:
            raise DialogueError("choice_expired")
        if (turn.frame.result_set is not shown or shown["generation"] != turn.generation
                or shown["items"] != items):
            raise DialogueError("choice_changed")
        if shown.get("session_id"):
            from ..session_runtime import session_runtime_manager
            active = session_runtime_manager(hass).current_active(turn.scope.removeprefix("profile:"))
            if active is None or active.session_id != shown["session_id"]:
                raise DialogueError("choice_expired")

    validate_offer.speech_deadline = shown["deadline"]
    turn.delivery_validators.append(validate_offer)
    await turn.guard()
    validate_offer()
    presentation = deepcopy(shown.get('presentation'))
    message = (presentation['caption'] if presentation and presentation.get('kind') == 'album_tracks'
               else catalogue_result_text(items, language))
    # No playback_actions: complete() must retain the exact set, original IDs,
    # chosen item and deadline, rather than minting a fresh600s offer.
    return {"success": True, "text": message, "dj_text": message, "action": "none",
            "items": items, "playback_actions": [], "is_generated_text": False,
            "text_source": "qualified_catalog_result", "_private_current_context": True,
            "result_set": {"schema_version": 1, "result_set_id": shown["result_set_id"],
                           "expires_in": max(0, shown["deadline"] - turn.history.dialogue.clock()),
                           "items": deepcopy(items),
                           **({'presentation': presentation} if presentation else {})},
            "intent": {"category": "informational", "intent": "shown_result_list"}}


async def _dialogue_choice_response(hass, runtime, payload, text, *, index=None):
    from .dialogue import current_turn, choice_index, explicit_play, explicit_activate, play_selected, references_topic, DialogueError, valid_uri
    turn = current_turn.get()
    if turn is None:
        return None
    value = payload.get("choice_action")
    chosen = choice_index(text) if index is None else index
    if chosen is None and value is None and turn.frame.result_set:
        from .dialogue import offered_media_index
        chosen = offered_media_index(text, turn.frame.result_set["items"])
    version_match = re.fullmatch(r"(?:(?:de|die|the|la|le|el|speel|play|joue|spiel|pon)\s+)*(live|acoustic|akoestische|akustische|acoustique|acústica)(?:\s*(?:versie|version|versión|one))?", text.casefold().strip(" .!?"))
    play_reference = play_selected(text) and not (
        _is_current_album_play_request(text) and turn.frame.result_set is None)
    activate_reference = explicit_activate(text) and (references_topic(text) or text.casefold().strip(" .!?") in {"activate", "activeer", "aktiviere", "active", "activa"})
    if chosen is None and value is None and version_match is None and not play_reference and not activate_reference:
        shown = turn.frame.result_set
        if (shown and turn.frame.chosen_action_id and not turn.reset_topic and not turn.source_context
            and references_topic(text)):
            if turn.history.dialogue.clock() >= shown["deadline"]:
                raise DialogueError("choice_expired")
            action = next((a for a in shown["items"] if a["action_id"] == turn.frame.chosen_action_id), None)
            if action is None:
                raise DialogueError("choice_changed")
            labels = {
                "en": "Which artist or aspect of the selected result do you mean? Please name it so I can explain it.",
                "nl": "Welke artiest of welk aspect van het gekozen resultaat bedoel je? Noem het, dan kan ik het toelichten.",
                "de": "Welchen Künstler oder welchen Aspekt des ausgewählten Ergebnisses meinst du? Nenne ihn, damit ich ihn erklären kann.",
                "fr": "Quel artiste ou quel aspect du résultat sélectionné veux-tu approfondir ? Nomme-le pour que je puisse l’expliquer.",
                "es": "¿Qué artista o aspecto del resultado seleccionado quieres conocer? Nómbralo para que pueda explicarlo.",
            }
            artist = action.get("artist") or action.get("artist_name")
            if action.get("kind") == "track" and not artist:
                artist = action.get("subtitle")
            if action.get("kind") == "artist":
                artist = action.get("title") or action.get("name") or artist
            # Display rights do not grant model processing or external lookups.
            # Multiple credited names remain genuinely ambiguous; never choose one.
            single_artist = isinstance(artist, str) and 0 < len(artist) <= 256 and not re.search(r"[,;/&]|\b(?:feat\.?|featuring|with|and|en|und|et|y)\b", artist, re.I)
            if single_artist:
                labels = {
                    "en": "The selected result credits {artist}. I can identify that catalog credit here; I do not yet have independently qualified context for a further explanation.",
                    "nl": "Het gekozen resultaat vermeldt {artist} als artiest. Ik kan die catalogusvermelding hier identificeren; voor verdere uitleg ontbreekt nog onafhankelijk gekwalificeerde context.",
                    "de": "Das ausgewählte Ergebnis nennt {artist} als Künstler. Diese Katalogangabe kann ich hier zuordnen; für eine weitere Erklärung fehlt noch unabhängig qualifizierter Kontext.",
                    "fr": "Le résultat sélectionné indique {artist} comme artiste. Je peux identifier cette mention du catalogue ; il manque encore un contexte qualifié indépendant pour l’expliquer davantage.",
                    "es": "El resultado seleccionado acredita a {artist} como artista. Puedo identificar esa mención del catálogo; aún falta contexto cualificado independiente para ampliarla.",
                }
            reply = labels[turn.style.get("language", "en")].format(artist=artist)
            return {"success": True, "text": reply, "dj_text": reply, "items": [action],
                "text_source": "qualified_catalog_result", "is_generated_text": False,
                "_private_current_context": True,
                "playback_actions": [], "intent": {"intent": "selected_result_identification" if single_artist else "selected_result_clarification"}}
        return None
    shown = turn.frame.result_set
    if shown is not None and isinstance(shown.get("music_steering"), dict):
        from ..mood_music_steering import validate_offer
        await validate_offer(hass, runtime, shown["music_steering"], turn)
    if shown is None and activate_reference:
        raise DialogueError("choice_expired")
    if shown is None and play_reference and value is None:
        labels = {"en":"Which shown result should I play? Please search or choose a result first.",
                  "nl":"Welk getoond resultaat wil je afspelen? Zoek of kies eerst een resultaat.",
                  "de":"Welches angezeigte Ergebnis soll ich abspielen? Suche oder wähle zuerst ein Ergebnis.",
                  "fr":"Quel résultat affiché veux-tu écouter ? Recherche ou sélectionne d’abord un résultat.",
                  "es":"¿Qué resultado mostrado quieres reproducir? Busca o elige un resultado primero."}
        reply = labels[turn.style.get("language", "en")]
        return {"success":True,"text":reply,"dj_text":reply,"action":"none",
                "intent":{"category":"informational", "intent":"clarification_needed"},"playback_actions":[]}
    if shown is None or turn.history.dialogue.clock() >= shown["deadline"]:
        raise DialogueError("choice_expired")
    context = payload.get("conversation_context") or {}
    expected = context.get("result_set_id") or (value.get("result_set_id") if isinstance(value, dict) else None)
    if expected and expected != shown["result_set_id"]:
        raise DialogueError("choice_changed")
    if value is not None:
        if not isinstance(value, dict) or set(value) != {"result_set_id", "action_id", "operation"} or value.get("operation") not in {"select", "play", "activate"}:
            raise DialogueError("invalid_choice_action", 400)
        chosen = next((i for i, a in enumerate(shown["items"]) if a["action_id"] == value.get("action_id")), None)
    if (play_reference or activate_reference) and chosen is None and value is None:
        chosen = next((i for i, a in enumerate(shown["items"]) if a["action_id"] == turn.frame.chosen_action_id), None)
        if chosen is None:
            if len(shown["items"]) != 1:
                raise DialogueError("choice_ambiguous")
            chosen = 0
    if version_match and chosen is None:
        tag = "live" if version_match[1] == "live" else "acoustic"
        candidates = [i for i, a in enumerate(shown["items"]) if tag in str(a.get("title") or "").casefold()]
        if len(candidates) != 1:
            raise DialogueError("choice_ambiguous")
        chosen = candidates[0]
    if chosen is None or not 0 <= chosen < len(shown["items"]):
        raise DialogueError("choice_unavailable")
    action = shown["items"][chosen]
    output = action.get("kind") == "output" and bool(action.get("device_id"))
    if shown["generation"] != turn.generation or (not output and not valid_uri(action.get("uri") or action.get("context_uri"))):
        raise DialogueError("choice_changed")
    # Bind authorization to the exact offered set through adapter token/receipt awaits.
    action_identity = dict(action)
    def validate_choice_evidence():
        if turn.history.dialogue.clock() >= shown["deadline"]:
            raise DialogueError("choice_expired")
        if shown.get("session_id"):
            from ..session_runtime import session_runtime_manager
            active = session_runtime_manager(hass).current_active(turn.scope.removeprefix("profile:"))
            if active is None or active.session_id != shown["session_id"]:
                raise DialogueError("choice_expired")
    def validate_choice():
        validate_choice_evidence()
        if (turn.frame.result_set is not shown or shown["generation"] != turn.generation
            or chosen >= len(shown["items"]) or shown["items"][chosen] != action_identity):
            raise DialogueError("choice_changed")
    turn.effect_validators.append(validate_choice)
    validate_choice_evidence.speech_deadline = shown["deadline"]
    turn.delivery_validators.append(validate_choice_evidence)
    await turn.guard()
    activate = explicit_activate(text) or (isinstance(value, dict) and value["operation"] == "activate")
    play = explicit_play(text) or (isinstance(value, dict) and value["operation"] == "play")
    no_play = re.search(r"\b(?:without (?:starting |resuming )?(?:playback|playing)|zonder (?:afspelen|te spelen|muziek te starten)|ohne (?:wiedergabe|abzuspielen)|sans (?:lancer|reprendre|jouer)|sin (?:reproducir|iniciar))\b", text.casefold())
    if play and (_nonexecuting_speech_act(text) or no_play):
        raise DialogueError("playback_effect_not_authorized", 403)
    if output and (activate or play):
        return await _activate_dialogue_output(hass, runtime, payload, action, turn, play=play)
    if activate and not output:
        raise DialogueError("invalid_choice_action", 400)
    if play:
        from .dialogue import EffectGrant, effect_media
        turn.effect_grants = (EffectGrant(frozenset({"play"}), "validated_result_play", media=effect_media(action)),)
        from ..http import _handle_ask_dj_play_recommendation
        result = await _handle_ask_dj_play_recommendation(hass, runtime, action, payload)
        await turn.guard()
        if result.get("action") == "select_output":
            # A new output offer needs its own frozen identity, not the old
            # media selection marker that would suppress result-set admission.
            return result
        return {**result, "selected_action_id": action["action_id"]}
    labels = {"en": "Selected; playback is unchanged.", "nl": "Geselecteerd; afspelen is niet gewijzigd.",
              "de": "Ausgewählt; die Wiedergabe bleibt unverändert.", "fr": "Sélectionné ; la lecture reste inchangée.",
              "es": "Seleccionado; la reproducción sigue igual."}
    language = turn.style.get("language", "en")
    return {"success": True, "text": labels[language], "dj_text": labels[language],
            "selected_action_id": action["action_id"], "playback_actions": [action], "items": [action]}


async def _activate_dialogue_output(hass, runtime, payload, action, turn, *, play=False):
    from .dialogue import EffectGrant, effect_media, DialogueError
    # Revalidate the exact ID using the same existing backend inventory.
    inventory = await run_music_command(hass, runtime, "devices")
    devices = inventory.get("devices", []) if isinstance(inventory, dict) else []
    if not any(d.get("id") == action["device_id"] and not d.get("is_restricted") and not d.get("cached") for d in devices if isinstance(d, dict)):
        raise DialogueError("choice_unavailable")
    await turn.guard()
    output_grant = EffectGrant(frozenset({"output"}), "validated_output_activation", output_id=action["device_id"])
    compound = action.get("command")
    if play and compound == "ask_dj_play_recommendation_on_output":
        recommendation = (action.get("value") or {}).get("recommendation")
        if not isinstance(recommendation, dict) or not effect_media(recommendation):
            raise DialogueError("invalid_choice_action", 400)
        turn.play_output_id = action["device_id"]
        turn.effect_grants = (output_grant, EffectGrant(frozenset({"play"}), "validated_output_result_play", media=effect_media(recommendation), output_id=action["device_id"]))
        from ..http import _handle_ask_dj_play_recommendation_on_output
        result = await _handle_ask_dj_play_recommendation_on_output(hass, runtime, action["value"], payload)
        await turn.guard()
        return {**result, "selected_action_id": action["action_id"]}
    if play and compound == "ask_dj_play_request_on_output":
        shown = turn.frame.result_set
        if shown.get("play_request_attempted"):
            raise DialogueError("choice_expired")
        original = (action.get("value") or {}).get("request") or {}
        original_text = str(original.get("text") or "")
        from .dialogue import request_effect_grants
        grants = request_effect_grants(original_text, classify_ask_dj(original_text))
        if not grants or any(g.families != frozenset({"play"}) for g in grants):
            raise DialogueError("invalid_choice_action", 400)
        turn.play_output_id = action["device_id"]
        frozen = original.get("_frozen_playback_selection")
        exact_media = tuple(frozen.get("uris") or ([frozen['context_uri']] if frozen.get('context_uri') else [])) if isinstance(frozen,dict) else ()
        turn.effect_grants = (output_grant, *(EffectGrant(g.families, g.origin, exact_media or g.media, action["device_id"]) for g in grants))
        from ..http import _handle_ask_dj_play_request_on_output
        # Single-use output continuation. A new client message ID must not
        # repeat a prior dispatch (including an uncertain provider outcome).
        shown["play_request_attempted"] = True
        turn.resolving_output_request = True
        try:
            result = await _handle_ask_dj_play_request_on_output(hass, runtime, action["value"], payload)
        finally:
            turn.resolving_output_request = False
        await turn.guard()
        return {**result, "selected_action_id": action["action_id"]}
    turn.effect_grants = (output_grant,)
    result = await run_music_command(hass, runtime, "set_output", action["device_id"], play=False)
    if failure := _failed_backend_action(result):
        return failure
    language = turn.style.get("language", "en")
    text = {"en": "Output transfer requested; playback state is preserved.", "nl": "Uitvoerwissel aangevraagd; de afspeeltoestand blijft behouden.",
            "de": "Ausgabewechsel angefordert; der Wiedergabestatus bleibt erhalten.", "fr": "Changement de sortie demandé ; l’état de lecture est conservé.",
            "es": "Cambio de salida solicitado; se conserva el estado de reproducción."}[language]
    playback = result.get("playback") or {}
    confirmed = ((playback.get("device") or {}).get("id") or playback.get("device_id")) == action["device_id"]
    return {"success": True, "text": text, "dj_text": text, "selected_action_id": action["action_id"], "playback": playback,
            "action_outcome": {"state": "dispatched", "readback_confirmed": confirmed}, "playback_actions": [], "items": [],
            **({"playback_projection_receipt": result["playback_projection_receipt"]} if "playback_projection_receipt" in result else {})}


async def _execute_dialogue_command(hass, runtime, payload, action_request, *, user_id=None):
    """Normalized taps/confirmations use the same existing effect processors as text/STT."""
    from .dialogue import current_turn, DialogueError
    from ..http import (_handle_ask_dj_play_recommendation, _handle_ask_dj_play_recommendation_on_output,
                        _handle_ask_dj_play_request_on_output, _handle_ask_dj_followup_response)
    turn = current_turn.get()
    if turn is None:
        raise DialogueError("conversation_authority_required", 403)
    command, value = action_request
    handler = {"ask_dj_play_recommendation": _handle_ask_dj_play_recommendation,
               "ask_dj_play_recommendation_on_output": _handle_ask_dj_play_recommendation_on_output,
               "ask_dj_play_request_on_output": _handle_ask_dj_play_request_on_output,
               "ask_dj_followup_response": _handle_ask_dj_followup_response}.get(command)
    if handler is None:
        raise DialogueError("unsupported_dialogue_action", 400)
    if command in {"ask_dj_play_recommendation_on_output", "ask_dj_play_request_on_output"}:
        if not isinstance(value, dict):
            raise DialogueError("invalid_choice_action", 400)
        from .dialogue import effect_media
        shown = turn.frame.result_set
        output_id = value.get("output_id") or value.get("device_id")
        def matches_output(action):
            if action.get("command") != command or action.get("device_id") != output_id:
                return False
            frozen = action.get("value") or {}
            if command == "ask_dj_play_recommendation_on_output":
                media = effect_media(frozen.get("recommendation"))
                return bool(media) and media == effect_media(value.get("recommendation"))
            return frozen.get("request") == value.get("request")
        matches = [a for a in (shown or {}).get("items", []) if matches_output(a)]
        if len(matches) != 1:
            raise DialogueError("choice_expired")
        return await _dialogue_choice_response(hass, runtime, {**payload, "choice_action": {
            "result_set_id": shown["result_set_id"], "action_id": matches[0]["action_id"], "operation": "play"}}, str(payload.get("text") or "play"))
    if command == "ask_dj_play_recommendation" and isinstance(value, dict) and value.get("action_id"):
        return await _dialogue_choice_response(hass, runtime,
            {**payload, "choice_action": {"result_set_id": value.get("result_set_id"),
             "action_id": value["action_id"], "operation": "play"}}, "play")
    if command == "ask_dj_play_recommendation" and isinstance(value, dict):
        from .dialogue import effect_media, valid_uri
        from ..http import (_stale_backend_action_error, _normalize_recommendation_value,
                           _validated_spotify_recommendation, music_backend_metadata)
        normalized = _normalize_recommendation_value(value)
        if stale := _stale_backend_action_error(runtime, normalized):
            return {**stale, **music_backend_metadata(hass, runtime), "_response_status": 400}
        checked = _validated_spotify_recommendation(normalized)
        if isinstance(checked, dict):
            return {**checked, "_response_status": 400}
        if any(not valid_uri(uri) for uri in effect_media(normalized)):
            raise DialogueError("invalid_recommendation_uri", 400)
        shown = turn.frame.result_set
        matches = [a for a in (shown or {}).get("items", []) if effect_media(a) and effect_media(a) == effect_media(value)]
        if not matches:
            raise DialogueError("choice_expired")
        return await _dialogue_choice_response(hass, runtime, {**payload, "choice_action": {
            "result_set_id": shown["result_set_id"], "action_id": matches[0]["action_id"], "operation": "play"}}, "play")
    await turn.guard()
    result = await handler(hass, runtime, value, payload, user_id=user_id)
    await turn.guard()
    if result.get("success") is False and result.get("error") in {
        "missing_recommendation", "missing_recommendation_uri", "unsupported_recommendation_kind", "invalid_recommendation", "invalid_recommendation_uri", "stale_backend_action", "unsupported_backend_action",
        "missing_followup_response", "invalid_followup_response", "missing_output", "invalid_output",
    }:
        result["_response_status"] = 400
    return result
