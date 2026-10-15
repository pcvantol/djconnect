"""One qualified configured HA processor; never fallback or inferred voice gender."""
from __future__ import annotations

import ipaddress
import io
import wave


class ProcessorUnavailable(ValueError):
    pass


def configured_processor(hass, conf, locale, preference):
    """Qualify actual HA entity/inventory before sending accepted text.

    Initially only installed Piper through the existing Wyoming HA entity on a
    literal local/private endpoint. Wyoming alone does not prove a local engine.
    No discovery, DNS, provider/model/config mutation, voice selection or fallback.
    HA Voice exposes ID/name, not gender; explicit gender is therefore unsupported.
    """
    try:
        from homeassistant.components import tts
        from homeassistant.components.wyoming.tts import WyomingTtsProvider
    except ImportError:
        raise ProcessorUnavailable("processor_not_qualified") from None
    from .tts import _tts_pipeline_candidates, _first_attr

    pipelines = _tts_pipeline_candidates(hass, conf)
    pipeline = pipelines[0] if pipelines else None
    engine_id = str(_first_attr(pipeline, "tts_engine", "tts_engine_id") or "")
    language = str(_first_attr(pipeline, "tts_language", "language") or "")
    voice_id = str(_first_attr(pipeline, "tts_voice", "voice") or "")
    try:
        entity = tts.get_engine_instance(hass, engine_id)
        service = entity.service if type(entity) is WyomingTtsProvider else None
        address = ipaddress.ip_address(service.host) if service else None
    except (KeyError, ValueError, AttributeError):
        raise ProcessorUnavailable("processor_not_qualified") from None
    info = getattr(getattr(entity, "coordinator", None), "data", None)
    programs = [p for p in info.tts if p.installed] if service and info else []
    if (not address or not (address.is_private or address.is_loopback) or address.is_unspecified
        or address.is_multicast or len(programs) != 1 or programs[0].name.lower() != "piper"):
        raise ProcessorUnavailable("processor_not_qualified")
    if language.split("-", 1)[0].split("_", 1)[0] != locale:
        raise ProcessorUnavailable("no_matching_locale")
    voices = entity.async_get_supported_voices(language) or []
    actual = next((v for v in voices if v.voice_id == voice_id), None)
    if not voice_id or actual is None:
        raise ProcessorUnavailable("no_matching_voice")
    if preference != "default":
        raise ProcessorUnavailable("voice_gender_unavailable")
    return entity, {"processor": "ha_configured", "engine": engine_id,
                    "provider": "wyoming_piper_local_network", "voice_id": actual.voice_id,
                    "voice_name": actual.name, "locale": language, "gender": None}


async def synthesize(entity, voice, text):
    """Call the exact already configured HA entity once, with the admitted text."""
    from .tts import _audio_type, TtsAudio

    mime, body = await entity.async_get_tts_audio(text, voice["locale"], {"voice": voice["voice_id"]})
    if not isinstance(body, bytes) or not 0 < len(body) <= 2 * 1024 * 1024:
        raise ProcessorUnavailable("unsupported_audio_extent")
    kind = _audio_type(mime, body)
    if kind != "wav" or not body.startswith(b"RIFF") or body[8:12] != b"WAVE":
        raise ProcessorUnavailable("unsupported_audio_type")
    try:
        with wave.open(io.BytesIO(body), "rb") as audio:
            if (audio.getcomptype() != "NONE" or not 1 <= audio.getnchannels() <= 2
                or not 1 <= audio.getsampwidth() <= 4 or not 8000 <= audio.getframerate() <= 192000
                or not 0 < audio.getnframes() <= 2 * 1024 * 1024):
                raise ProcessorUnavailable("unsupported_audio_type")
            if len(audio.readframes(audio.getnframes())) != audio.getnframes() * audio.getnchannels() * audio.getsampwidth():
                raise ProcessorUnavailable("unsupported_audio_type")
    except (EOFError, wave.Error):
        raise ProcessorUnavailable("unsupported_audio_type") from None
    return TtsAudio(body, "wav", "audio/wav")


def voice_options(hass, conf):
    """Read current provider support; no synthesis, lookup, inferred gender or writes."""
    from .tts import detect_tts_support
    status = detect_tts_support(hass, conf)
    locale = str(status.get("language") or "").replace("_", "-").split("-", 1)[0]
    options = {"schema_version": 1, "authority": "configured_ha_assist_pipeline_provider",
               "preference_scope": "device_local", "default_preference": "default",
               "default_available": False, "supported_preferences": ["default"],
               "gender_selection": {"available": False, "values": [],
                                    "reason": "provider_gender_metadata_unavailable"},
               "provider_voice": None, "cache_policy": "private,no-store"}
    try:
        _, voice = configured_processor(hass, conf, locale, "default")
    except ProcessorUnavailable as exc:
        options["state"] = "unavailable"
        options["reason"] = str(exc)
    else:
        options.update(state="available", reason=None, default_available=True, provider_voice=voice)
    # HA2026.10's supported Voice object exposes ID/name only. This qualified
    # adapter has no gender values to advertise, regardless of voice name/pitch.
    import hashlib
    import json
    options["revision"] = hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()[:24]
    return options
