from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_ASSIST_PIPELINE_ID,
    CONF_TTS_LANGUAGE,
    DEFAULT_TTS_LANGUAGE,
)

_LOGGER = logging.getLogger(__name__)
_ROOT_LOGGER = logging.getLogger("custom_components.djconnect")


async def process_text_with_assist(
    hass: HomeAssistant,
    user_text: str,
    conf: dict[str, Any],
    memory_context: str | None = None,
) -> dict[str, Any]:
    """Run text through HA Assist and return a DJConnect intent."""
    assist_context = _assist_context(hass, conf)
    response = await _conversation_process(
        hass,
        user_text,
        assist_context,
        memory_context=memory_context,
    )
    intent = _intent_from_assist_response(response, user_text)
    intent["assist"] = response
    return intent


async def correct_stt_text_with_assist(
    hass: HomeAssistant,
    user_text: str,
    conf: dict[str, Any],
) -> str:
    """Correct likely STT mistakes before DJConnect intent parsing."""
    original = str(user_text or "").strip()
    if not original:
        return original

    assist_context = _assist_context(hass, conf)
    language = assist_context.get("language") or DEFAULT_TTS_LANGUAGE
    prompt = _stt_correction_prompt(original, str(language))
    data = {"text": prompt, "language": language}
    if assist_context.get("pipeline_id"):
        data["pipeline_id"] = assist_context["pipeline_id"]
    if assist_context.get("agent_id"):
        data["agent_id"] = assist_context["agent_id"]

    try:
        _LOGGER.debug(
            "DJConnect Assist STT correction prompt language=%s agent_id=%s pipeline_id=%s",
            language,
            assist_context.get("agent_id"),
            assist_context.get("pipeline_id"),
        )
        result = await hass.services.async_call(
            "conversation",
            "process",
            data,
            blocking=True,
            return_response=True,
        )
        response = (result or {}).get("response") or {}
        corrected = _speech_from_response(response)
        block_reason = _stt_correction_block_reason(original, corrected)
        if block_reason is not None:
            _LOGGER.debug(
                "Ignoring unusable Assist STT correction (%s): %s",
                block_reason,
                corrected,
            )
            return original
        if corrected != original:
            _LOGGER.debug(
                "DJConnect STT correction applied original=%r corrected=%r",
                original,
                corrected,
            )
        return corrected
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect STT correction through Assist failed", exc_info=True)
        return original


def _assist_context(hass: HomeAssistant, conf: dict[str, Any]) -> dict[str, Any]:
    """Resolve the configured pipeline into conversation service arguments."""
    pipeline_id = (conf.get(CONF_ASSIST_PIPELINE_ID) or "").strip()
    context: dict[str, Any] = {
        "language": conf.get(CONF_TTS_LANGUAGE) or DEFAULT_TTS_LANGUAGE,
    }
    pipeline = (
        _get_assist_pipeline(hass, pipeline_id)
        if pipeline_id
        else _get_default_assist_pipeline(hass)
    )
    if pipeline is None:
        if pipeline_id:
            context["pipeline_id"] = pipeline_id
        return context

    conversation_engine = _first_attr(
        pipeline,
        "conversation_engine",
        "conversation_engine_id",
        "conversation_agent",
        "conversation_agent_id",
    )
    language = _first_attr(pipeline, "conversation_language", "language")
    if conversation_engine:
        context["agent_id"] = conversation_engine
    if language:
        context["language"] = language
    context["pipeline_id"] = pipeline_id or getattr(pipeline, "id", None)
    return context


def resolve_assist_language(hass: HomeAssistant, conf: dict[str, Any]) -> str:
    """Resolve language from Assist without consulting legacy TTS options."""
    pipeline_id = str(conf.get(CONF_ASSIST_PIPELINE_ID) or "").strip()
    pipeline = _get_assist_pipeline(hass, pipeline_id) if pipeline_id else None
    if pipeline is None:
        pipeline = _get_default_assist_pipeline(hass)
    if pipeline is not None:
        language = _first_attr(pipeline, "conversation_language", "language")
        if language:
            return normalize_supported_language(language)
    return normalize_supported_language(
        getattr(getattr(hass, "config", None), "language", "")
    )


def normalize_supported_language(value: Any) -> str:
    """Normalize a locale to one canonical supported language family."""
    language = str(value or "").strip().replace("_", "-")
    family = language.casefold().split("-", 1)[0]
    return family if family in {"en", "nl", "de", "fr", "es"} else "en"


def _get_assist_pipeline(hass: HomeAssistant, pipeline_id: str) -> Any | None:
    try:
        from homeassistant.components.assist_pipeline.pipeline import async_get_pipelines

        pipelines = async_get_pipelines(hass)
        available = _pipeline_list(pipelines)
        pipeline = _find_pipeline(pipelines, available, pipeline_id)
        if pipeline is not None:
            return pipeline
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not resolve Assist pipeline %s", pipeline_id, exc_info=True)
    return None


def _get_default_assist_pipeline(hass: HomeAssistant) -> Any | None:
    try:
        from homeassistant.components.assist_pipeline.pipeline import async_get_pipelines

        pipelines = async_get_pipelines(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not resolve default Assist pipeline", exc_info=True)
        return None

    available = _pipeline_list(pipelines)
    preferred_getter = getattr(pipelines, "async_get_preferred_pipeline", None)
    if callable(preferred_getter):
        try:
            preferred = preferred_getter()
            if preferred is not None:
                return preferred
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Preferred Assist pipeline lookup failed", exc_info=True)

    preferred = _first_attr(pipelines, "preferred_pipeline", "current_pipeline")
    if preferred is not None:
        return preferred

    for pipeline in available:
        if _first_attr(
            pipeline,
            "conversation_engine",
            "conversation_engine_id",
            "conversation_agent",
            "conversation_agent_id",
        ):
            return pipeline
    return available[0] if available else None


def _find_pipeline(
    pipelines: Any,
    available: list[Any],
    pipeline_id: str,
) -> Any | None:
    getter = getattr(pipelines, "async_get_pipeline", None)
    if callable(getter):
        try:
            pipeline = getter(pipeline_id)
            if pipeline is not None:
                return pipeline
        except Exception:  # noqa: BLE001
            return None
    for pipeline in available:
        if str(getattr(pipeline, "id", "") or "") == pipeline_id:
            return pipeline
    return None


def _pipeline_list(pipelines: Any) -> list[Any]:
    if isinstance(pipelines, dict):
        return list(pipelines.values())
    mapping = getattr(pipelines, "pipelines", None)
    if isinstance(mapping, dict):
        return list(mapping.values())
    if isinstance(mapping, list | tuple):
        return list(mapping)
    try:
        return list(pipelines)
    except TypeError:
        return []


def _first_attr(obj: Any, *names: str) -> Any | None:
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, ""):
            return value
    return None


async def _conversation_process(
    hass: HomeAssistant,
    user_text: str,
    assist_context: dict[str, Any],
    memory_context: str | None = None,
) -> dict[str, Any]:
    language = assist_context.get("language") or DEFAULT_TTS_LANGUAGE
    prompt = _djconnect_assist_prompt(user_text, str(language), memory_context)
    data = {
        "text": prompt,
        "language": language,
    }
    if assist_context.get("pipeline_id"):
        data["pipeline_id"] = assist_context["pipeline_id"]
    if assist_context.get("agent_id"):
        data["agent_id"] = assist_context["agent_id"]

    _LOGGER.debug(
        "DJConnect Assist command prompt language=%s agent_id=%s pipeline_id=%s",
        language,
        assist_context.get("agent_id"),
        assist_context.get("pipeline_id"),
    )
    result = await call_conversation_process_with_agent_retry(hass, data)
    if not isinstance(result, dict):
        raise RuntimeError("HA Assist did not return response data")
    result["pipeline_id"] = assist_context.get("pipeline_id")
    result["agent_id"] = assist_context.get("agent_id")
    return result


async def call_conversation_process_with_agent_retry(hass, data, *, debug=None, model_guard=None):
    """Existing transport with bounded, rights-qualified Ask DJ execution context."""
    from .ask_dj.dialogue import current_turn, DialogueError, MAX_PROMPT_BYTES
    turn = current_turn.get()
    if turn is None and model_guard is None:
        return await _call_conversation_process_transport(hass, data, debug=debug)
    if turn is not None:
        await turn.guard()
    if model_guard is not None:
        model_guard()
    if len(str(data.get("text") or "").encode()) > MAX_PROMPT_BYTES:
        raise DialogueError("conversation_context_too_large", 413)
    if turn is not None and turn.agent_calls >= 2:
        raise DialogueError("conversation_call_budget", 503)
    if turn is not None:
        turn.prompt_bytes = max(turn.prompt_bytes, len(str(data.get("text") or "").encode()))
    # No instruction-only tool sandbox: enforce HA's advertised control boundary.
    from .ask_dj.dialogue import qualify_agent
    agent = qualify_agent(hass, data.get("agent_id"))
    if turn is not None:
        turn.agent_calls += 1
    import asyncio
    if not hasattr(hass, "bus"):
        result = await asyncio.wait_for(_call_conversation_process_transport(hass, data, debug=debug, allow_agent_fallback=False), 30)
    else:
        from homeassistant.helpers import chat_session
        with chat_session.async_get_chat_session(hass) as session:
            try:
                result = await asyncio.wait_for(_call_conversation_process_transport(
                    hass, {**data, "conversation_id": session.conversation_id}, debug=debug, allow_agent_fallback=False), 30)
            finally:
                session.async_cleanup()
    if qualify_agent(hass, data.get("agent_id")) is not agent:
        raise DialogueError("conversation_agent_changed")
    if turn is not None:
        await turn.guard()
    if model_guard is not None:
        model_guard()
    return result


async def _call_conversation_process_transport(
    hass: HomeAssistant,
    data: dict[str, Any],
    *,
    debug: dict[str, Any] | None = None,
    allow_agent_fallback: bool = True,
) -> dict[str, Any]:
    """Legacy non-model transport may retry; qualified dialogue never changes agents."""
    try:
        return await hass.services.async_call(
            "conversation",
            "process",
            data,
            blocking=True,
            return_response=True,
        )
    except Exception as exc:  # noqa: BLE001
        if not allow_agent_fallback or not data.get("agent_id") or not _looks_like_invalid_agent_id_error(exc):
            raise
        retry_data = dict(data)
        retry_data.pop("agent_id", None)
        if debug is not None:
            debug["agent_retry_without_agent_id"] = True
        _LOGGER.debug(
            "Retrying DJConnect conversation.process without invalid agent_id=%s",
            data.get("agent_id"),
        )
        return await hass.services.async_call(
            "conversation",
            "process",
            retry_data,
            blocking=True,
            return_response=True,
        )


def _djconnect_assist_prompt(
    user_text: str,
    language: str,
    memory_context: str | None = None,
) -> str:
    """Add DJConnect-specific DJ response guidance to the Assist text request."""
    memory_text = str(memory_context or "").strip()
    memory_block = (
        "\nAsk DJ context voor vervolgvragen:\n" + memory_text
        if memory_text and str(language or "").lower().startswith("nl")
        else "\nAsk DJ context for follow-up requests:\n" + memory_text
        if memory_text
        else ""
    )
    if str(language or "").lower().startswith("nl"):
        return (
            "Analyseer alleen deze DJConnect muziekopdracht. Bepaal de artiest, "
            "track, album of playlist voor Spotify. Geef waar mogelijk djconnect "
            "intentdata terug. Herken ook vervolgvragen zoals 'ik wil Zombie horen' "
            "en lijstvragen zoals 'wat heb je nog meer van Scala' of "
            "'wat voor grunge playlists heb je'. "
            "Gebruik geen apparaatbediening en interpreteer de instructietekst niet "
            "als apparaatnaam. "
            f"Opdracht: {user_text}{memory_block}"
        )
    return (
        "Analyze only this DJConnect music request. Determine the artist, track, "
        "album or playlist for Spotify. Return djconnect intent data when possible. "
        "Recognize follow-ups like 'I want to hear Zombie' and list requests like "
        "'what else do you have by Scala' or 'what kind of grunge playlists do you have'. Do not control "
        "Home Assistant devices and do not treat the instruction text as a device name. "
        f"Request: {user_text}{memory_block}"
    )


def _stt_correction_prompt(user_text: str, language: str) -> str:
    """Prompt HA Assist to normalize only STT text, not execute commands."""
    if str(language or "").lower().startswith("nl"):
        return (
            "Corrigeer alleen mogelijke spraak-naar-tekst fouten in deze DJConnect "
            "muziekopdracht. Dit is geen Home Assistant apparaatopdracht; bedien geen "
            "apparaten. Herken vooral Engelstalige artiesten, nummers, albums en "
            "playlists binnen een Nederlandse zin. Verander niets als je niet zeker "
            "bent. Antwoord alleen met de gecorrigeerde opdrachttekst, zonder uitleg, "
            f"zonder JSON en zonder URI.\nTranscript: {user_text}"
        )
    return (
        "Correct only likely speech-to-text mistakes in this DJConnect music request. "
        "This is not a Home Assistant device command; do not control devices. Focus on "
        "artist, track, album and playlist names. Leave the text unchanged when unsure. "
        "Return only the corrected request text, with no explanation, no JSON and no URI.\n"
        f"Transcript: {user_text}"
    )


async def generate_dj_response_with_assist(
    hass: HomeAssistant, *, media: dict[str, Any], fallback_text: str,
    conf: dict[str, Any], memory_context: str | None = None,
    debug: dict[str, Any] | None = None, narration=None, admission=None,
) -> str:
    """One qualified expression owner; unqualified commands keep their accepted answer.

    Media labels or compact memory alone are not a model-processing grant.
    Command responses do not create an independent proactive announcement.
    """
    if narration is None:
        if debug is not None:
            debug.update(fallback_used=True, block_reason="qualified_narration_required")
        return fallback_text
    return await _qualified_dj_response_with_assist(
        hass, narration=narration, admission=admission, fallback_text=fallback_text,
        conf=conf, debug=debug)


async def _qualified_dj_response_with_assist(hass, *, narration, admission, fallback_text, conf, debug):
    """Reuse the announcement transport with a minimal qualified fact grant.

    Two bounded calls: realization and separate semantic assessment. Neither
    output nor raw prompt enters legacy announcement diagnostics/history.
    """
    import asyncio
    from .narration_brief import NarrationBrief, NarratedText, candidate, assessed
    if debug is not None:
        debug.update(fallback_used=True, block_reason="narration_unavailable", model_attempts=0)
    if type(narration) is not NarrationBrief or not callable(admission):
        return fallback_text
    context = None

    def guard():
        admission()
        if not narration.current():
            raise PermissionError("narration_source_expired")
        if context is not None and _assist_context(hass, conf) != context:
            raise PermissionError("narration_pipeline_changed")

    try:
        guard()
        context = _assist_context(hass, conf)
        # A qualified request must never silently choose a different agent.
        if not context.get("agent_id"):
            return fallback_text
        async def ask(prompt):
            guard()
            if debug is not None:
                debug["model_attempts"] += 1
            result = await call_conversation_process_with_agent_retry(
                hass, {"text": prompt, "language": narration.locale,
                       "agent_id": context["agent_id"]}, model_guard=guard)
            guard()
            return _speech_from_response((result or {}).get("response") or {})

        async with asyncio.timeout(12):
            text = candidate(narration, await ask(narration.prompt()))
            if text is None or not assessed(await ask(narration.assessment_prompt(text))):
                return fallback_text
            guard()
            if debug is not None:
                debug.update(fallback_used=False, block_reason=None)
            return NarratedText(narration.render(text), text)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # Bounded local fallback, never raw provider text.
        if debug is not None:
            debug["block_reason"] = type(exc).__name__
        return fallback_text
















def _looks_like_invalid_agent_id_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "invalid agent id" in message or "invalid agent_id" in message




def _normalize_media_match_text(value: str) -> str:
    normalized = str(value or "").lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _intent_from_assist_response(response: dict[str, Any], user_text: str) -> dict[str, Any]:
    conversation_response = response.get("response") or {}
    response_type = conversation_response.get("response_type")
    if response_type == "error":
        speech = _speech_from_response(conversation_response)
        if _assist_treated_prompt_as_ha_command(speech):
            return _fallback_search_intent(user_text)
        raise RuntimeError(speech or "HA Assist could not process the command")

    data = _djconnect_data(conversation_response)
    has_djconnect_data = _has_djconnect_data(conversation_response)
    local_intent = _local_music_intent(user_text)

    intent = {
        "intent": data.get("intent") or "play_music",
        "type": data.get("type") or data.get("media_type") or "search",
        "artist": data.get("artist"),
        "title": data.get("title"),
        "playlist": data.get("playlist"),
        "query": data.get("query") or user_text,
        "spotify_search_query": data.get("spotify_search_query") or data.get("query") or user_text,
        "dj_announcement": data.get("dj_announcement")
        or (_speech_from_response(conversation_response) if has_djconnect_data else ""),
    }
    if not intent["dj_announcement"]:
        intent["dj_announcement"] = "Daar gaan we. Ik zet hem voor je klaar."
    if _should_prefer_local_intent(intent, local_intent, has_djconnect_data):
        _LOGGER.debug(
            "DJConnect local intent parser overrode Assist intent user_text=%r assist=%s local=%s",
            user_text,
            _intent_debug_summary(intent),
            _intent_debug_summary(local_intent),
        )
        local_intent["assist_intent"] = intent
        if _announcement_matches_local_intent(intent.get("dj_announcement"), local_intent):
            local_intent["dj_announcement"] = intent["dj_announcement"]
        return local_intent
    return intent


def _fallback_search_intent(user_text: str) -> dict[str, Any]:
    local_intent = _local_music_intent(user_text)
    if local_intent.get("spotify_search_query"):
        return local_intent
    return {
        "intent": "play_music",
        "type": "search",
        "artist": None,
        "title": None,
        "playlist": None,
        "query": user_text,
        "spotify_search_query": user_text,
        "dj_announcement": "Daar gaan we. Ik zet hem voor je klaar.",
    }


def _local_music_intent(user_text: str) -> dict[str, Any]:
    from .music_intent import parse_spoken_music_request

    parsed = parse_spoken_music_request(user_text)
    media_type = str(parsed.get("type") or "artist").strip() or "artist"
    query = str(parsed.get("query") or user_text or "").strip()
    return {
        "intent": "play_music",
        "type": media_type,
        "artist": parsed.get("artist"),
        "title": parsed.get("title"),
        "playlist": parsed.get("playlist"),
        "query": query,
        "spotify_search_query": query,
        "dj_announcement": "Daar gaan we. Ik zet hem voor je klaar.",
    }


def _should_prefer_local_intent(
    assist_intent: dict[str, Any],
    local_intent: dict[str, Any],
    has_djconnect_data: bool,
) -> bool:
    """Prefer deterministic parsing when Assist returns stale or unrelated media."""
    local_query = str(local_intent.get("spotify_search_query") or "").strip()
    if not local_query:
        return False
    if not has_djconnect_data:
        return True
    local_type = str(local_intent.get("type") or "").strip().lower()
    assist_type = str(assist_intent.get("type") or "").strip().lower()
    if local_type and assist_type in {"", "search", "music"} and local_type != assist_type:
        return True
    if local_type and assist_type not in {"", "search", "music"} and local_type != assist_type:
        return True
    for key in ("artist", "title", "playlist"):
        local_value = _normalized_intent_value(local_intent.get(key))
        assist_value = _normalized_intent_value(assist_intent.get(key))
        if local_value and assist_value and local_value != assist_value:
            return True
    if any(assist_intent.get(key) for key in ("artist", "title", "playlist")):
        return False
    assist_query = _normalized_intent_value(assist_intent.get("spotify_search_query"))
    local_query_normalized = _normalized_intent_value(local_query)
    return bool(assist_query and local_query_normalized and local_query_normalized not in assist_query)


def _normalized_intent_value(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _announcement_matches_local_intent(announcement: Any, local_intent: dict[str, Any]) -> bool:
    text = _normalize_media_match_text(str(announcement or ""))
    if not text:
        return False
    for key in ("artist", "title", "playlist"):
        value = _normalize_media_match_text(str(local_intent.get(key) or ""))
        if value and value not in text:
            return False
    return any(local_intent.get(key) for key in ("artist", "title", "playlist"))


def _intent_debug_summary(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        key: intent.get(key)
        for key in ("type", "artist", "title", "playlist", "spotify_search_query")
        if intent.get(key) not in (None, "")
    }


def _assist_treated_prompt_as_ha_command(speech: str) -> bool:
    normalized = " ".join(str(speech or "").lower().split())
    if _looks_like_device_lookup_error(normalized):
        return True
    return (
        "djconnect muziekopdracht" in normalized
        or "djconnect music request" in normalized
        or "opdracht " in normalized
        or "request " in normalized
    ) and (
        "geen apparaat vinden" in normalized
        or "niet vinden" in normalized
        or "can't find" in normalized
        or "cannot find" in normalized
        or "no device" in normalized
    )


def _has_djconnect_data(conversation_response: dict[str, Any]) -> bool:
    data = conversation_response.get("data") or {}
    return isinstance(data.get("djconnect"), dict)


def _djconnect_data(conversation_response: dict[str, Any]) -> dict[str, Any]:
    """Extract the structured intent payload returned by Assist, when available."""
    data = conversation_response.get("data") or {}
    if isinstance(data.get("djconnect"), dict):
        return data["djconnect"]
    return data


def _speech_from_response(conversation_response: dict[str, Any]) -> str:
    speech = conversation_response.get("speech") or {}
    plain = speech.get("plain") or {}
    ssml = speech.get("ssml") or {}
    return (plain.get("speech") or ssml.get("speech") or "").strip()


def _stt_correction_block_reason(original: str, corrected: str) -> str | None:
    """Return why an Assist STT correction should be ignored."""
    text = str(corrected or "").strip()
    if not text:
        return "empty"
    normalized = " ".join(text.lower().split())
    if _looks_like_device_lookup_error(normalized):
        return "device lookup error"
    if len(text) > max(180, len(original) * 3):
        return "too long"
    blocked_fragments = (
        "corrigeer alleen",
        "speech-to-text",
        "spraak-naar-tekst",
        "transcript:",
        "antwoord alleen",
        "return only",
        "geen json",
        "no json",
        "geen uri",
        "no uri",
        "djconnect muziekopdracht",
        "djconnect music request",
        "home assistant apparaatopdracht",
        "home assistant device command",
        "spotify:artist:",
        "spotify:track:",
        "spotify:album:",
        "spotify:playlist:",
        "{",
        "}",
    )
    for fragment in blocked_fragments:
        if fragment in normalized:
            return fragment
    return None


def _is_usable_dj_response(value: str) -> bool:
    """Return whether Assist produced displayable DJ response text."""
    return _dj_response_block_reason(value) is None


def _dj_response_block_reason(value: str) -> str | None:
    """Return why generated DJ response text should not be displayed."""
    text = str(value or "").strip()
    if not text:
        return "empty"
    normalized = " ".join(text.lower().split())
    if _looks_like_device_lookup_error(normalized):
        return "device lookup error"
    blocked_fragments = (
        "geen apparaat vinden",
        "kan geen apparaat",
        "can't find",
        "cannot find",
        "no device",
        "home assistant devices",
        "djconnect muziekopdracht",
        "djconnect music request",
        "spotify:artist:",
        "spotify:track:",
        "spotify:album:",
        "spotify:playlist:",
        "{'type'",
        '"type"',
        "'uri'",
        '"uri"',
    )
    for fragment in blocked_fragments:
        if fragment in normalized:
            return fragment
    return None


def _looks_like_device_lookup_error(normalized: str) -> bool:
    if not (
        normalized.startswith("sorry, ik kan ")
        or normalized.startswith("sorry ik kan ")
        or normalized.startswith("sorry, i can't ")
        or normalized.startswith("sorry i can't ")
        or normalized.startswith("sorry, i am not aware of ")
        or normalized.startswith("sorry i am not aware of ")
    ):
        return False
    if not (
        "niet vinden" in normalized
        or "can't find" in normalized
        or "cannot find" in normalized
        or "not find" in normalized
        or "not aware of any area called" in normalized
        or "not aware of any device called" in normalized
    ):
        return False
    prompt_or_media_fragments = (
        "noem de artiest",
        "geef een leuk",
        "klink warm",
        "media type",
        "type artist",
        "artiest ",
        "artist ",
        "antwoord alleen",
        "geen json",
        "geen uitleg",
        "geen uri",
        "dj response",
        "djconnect muziekopdracht",
        "djconnect music request",
        "je bent djconnect ask dj",
        "you are djconnect ask dj",
        "beantwoord informatieve muziekvragen",
        "answer informational music questions",
        "gebruik alleen meegegeven context",
        "use only provided context",
        "voice profile",
        "voor een chat ui",
        "for a chat ui",
    )
    return any(fragment in normalized for fragment in prompt_or_media_fragments)
