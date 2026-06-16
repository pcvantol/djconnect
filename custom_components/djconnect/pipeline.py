from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_ASSIST_PIPELINE_ID,
    CONF_DJ_RESPONSE_PROMPT,
    CONF_TTS_LANGUAGE,
    DEFAULT_DJ_RESPONSE_PROMPT,
    DEFAULT_TTS_LANGUAGE,
)

_LOGGER = logging.getLogger(__name__)
_ROOT_LOGGER = logging.getLogger("custom_components.djconnect")


async def process_text_with_assist(
    hass: HomeAssistant,
    user_text: str,
    conf: dict[str, Any],
) -> dict[str, Any]:
    """Run text through HA Assist and return a DJConnect intent."""
    assist_context = _assist_context(hass, conf)
    response = await _conversation_process(hass, user_text, assist_context)
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
    if assist_context.get("agent_id"):
        data["agent_id"] = assist_context["agent_id"]

    try:
        _LOGGER.debug(
            "DJConnect Assist STT correction prompt language=%s agent_id=%s pipeline_id=%s prompt=%r",
            language,
            assist_context.get("agent_id"),
            assist_context.get("pipeline_id"),
            prompt,
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
            context["agent_id"] = pipeline_id
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
) -> dict[str, Any]:
    language = assist_context.get("language") or DEFAULT_TTS_LANGUAGE
    prompt = _djconnect_assist_prompt(user_text, str(language))
    data = {
        "text": prompt,
        "language": language,
    }
    if assist_context.get("agent_id"):
        data["agent_id"] = assist_context["agent_id"]

    _LOGGER.debug(
        "DJConnect Assist command prompt language=%s agent_id=%s pipeline_id=%s prompt=%r",
        language,
        assist_context.get("agent_id"),
        assist_context.get("pipeline_id"),
        prompt,
    )
    result = await hass.services.async_call(
        "conversation",
        "process",
        data,
        blocking=True,
        return_response=True,
    )
    if not isinstance(result, dict):
        raise RuntimeError("HA Assist did not return response data")
    result["pipeline_id"] = assist_context.get("pipeline_id")
    result["agent_id"] = assist_context.get("agent_id")
    return result


def _djconnect_assist_prompt(
    user_text: str,
    language: str,
) -> str:
    """Add DJConnect-specific DJ response guidance to the Assist text request."""
    if str(language or "").lower().startswith("nl"):
        return (
            "Analyseer alleen deze DJConnect muziekopdracht. Bepaal de artiest "
            "of playlist voor Spotify. Geef waar mogelijk djconnect intentdata terug. "
            "Gebruik geen apparaatbediening en interpreteer de instructietekst niet "
            "als apparaatnaam. "
            f"Opdracht: {user_text}"
        )
    return (
        "Analyze only this DJConnect music request. Determine the artist or playlist "
        "for Spotify. Return djconnect intent data when possible. Do not control "
        "Home Assistant devices and do not treat the instruction text as a device name. "
        f"Request: {user_text}"
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
    hass: HomeAssistant,
    *,
    media: dict[str, Any],
    fallback_text: str,
    conf: dict[str, Any],
    debug: dict[str, Any] | None = None,
) -> str:
    """Ask HA Assist for a short DJ response using resolved playback metadata."""
    prompt = str(conf.get(CONF_DJ_RESPONSE_PROMPT) or DEFAULT_DJ_RESPONSE_PROMPT).strip()
    assist_context = _assist_context(hass, conf)
    language = assist_context.get("language") or conf.get(CONF_TTS_LANGUAGE) or DEFAULT_TTS_LANGUAGE
    media_context = _dj_response_media_context(media)
    if debug is not None:
        debug.update(
            {
                "fallback_text": fallback_text,
                "media_context": dict(media_context),
                "fallback_used": False,
                "block_reason": None,
                "generated_text": None,
            }
        )
    if not media_context:
        if debug is not None:
            debug.update({"fallback_used": True, "block_reason": "empty media context"})
        return fallback_text
    media_lines = _dj_response_media_lines(media_context)
    text = (
        "Je schrijft alleen een korte gesproken DJ response voor het DJConnect device. "
        "Dit is geen Home Assistant apparaatopdracht. Bedien geen apparaten. "
        "Spreek Engelstalige artiesten, albums en nummers op z'n Engels uit, ook binnen "
        "een Nederlandse zin. "
        f"{prompt}\n\nMedia:\n{media_lines}\n\n"
        "Antwoord alleen met de tekst die uitgesproken moet worden. Geen JSON, geen uitleg, geen URI."
        if str(language).lower().startswith("nl")
        else "Write only a short spoken DJ response for the DJConnect device. "
        "This is not a Home Assistant device command. Do not control devices. "
        f"Style/content guidance:\n{prompt}\n\n"
        f"Media:\n{media_lines}\n\n"
        "Return only the text that should be spoken. No JSON, no explanation, no URI."
    )
    if debug is not None:
        debug["prompt"] = text
    try:
        _ROOT_LOGGER.debug(
            "DJConnect Assist DJ response prompt language=%s agent_id=%s pipeline_id=%s prompt=%r",
            language,
            assist_context.get("agent_id"),
            assist_context.get("pipeline_id"),
            text,
        )
        data = {"text": text, "language": language}
        if assist_context.get("agent_id"):
            data["agent_id"] = assist_context["agent_id"]
        result = await hass.services.async_call(
            "conversation",
            "process",
            data,
            blocking=True,
            return_response=True,
        )
        response = (result or {}).get("response") or {}
        generated = _speech_from_response(response)
        if debug is not None:
            debug["generated_text"] = generated
        blocked_reason = _dj_response_block_reason(generated)
        if blocked_reason is None:
            return generated
        if debug is not None:
            debug.update({"fallback_used": True, "block_reason": blocked_reason})
        _LOGGER.debug(
            "Ignoring unusable Assist DJ response (%s): %s",
            blocked_reason,
            generated,
        )
        return fallback_text
    except Exception as exc:  # noqa: BLE001
        if debug is not None:
            debug.update(
                {
                    "fallback_used": True,
                    "block_reason": type(exc).__name__,
                    "error": str(exc) or type(exc).__name__,
                }
            )
        _LOGGER.debug("DJConnect DJ response generation through Assist failed", exc_info=True)
        return fallback_text


def _dj_response_media_context(media: dict[str, Any]) -> dict[str, Any]:
    """Return safe user-facing media metadata for DJ response generation."""
    allowed_keys = (
        "type",
        "title",
        "track_name",
        "name",
        "artist",
        "artist_name",
        "album_name",
        "album",
        "playlist",
        "owner",
    )
    return {
        key: value
        for key in allowed_keys
        if (value := media.get(key)) not in (None, "", [], {})
    }


def _dj_response_media_lines(media_context: dict[str, Any]) -> str:
    labels = {
        "type": "type",
        "title": "titel",
        "track_name": "nummer",
        "name": "naam",
        "artist": "artiest",
        "artist_name": "artiest",
        "album_name": "album",
        "album": "album",
        "playlist": "playlist",
        "owner": "eigenaar",
    }
    lines = []
    seen = set()
    for key, value in media_context.items():
        label = labels.get(key, key)
        line = f"{label}: {value}"
        dedupe_key = (label, str(value).strip().lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        lines.append(line)
    return "\n".join(lines)


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
        if intent.get("dj_announcement"):
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


def _intent_debug_summary(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        key: intent.get(key)
        for key in ("type", "artist", "title", "playlist", "spotify_search_query")
        if intent.get(key) not in (None, "")
    }


def _assist_treated_prompt_as_ha_command(speech: str) -> bool:
    normalized = " ".join(str(speech or "").lower().split())
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
    ):
        return False
    if not (
        "niet vinden" in normalized
        or "can't find" in normalized
        or "cannot find" in normalized
        or "not find" in normalized
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
    )
    return any(fragment in normalized for fragment in prompt_or_media_fragments)
