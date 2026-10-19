"""The exact configured HA TTS provider; no provider fallback or inferred gender."""
from __future__ import annotations

import ipaddress
import io
import wave
import hashlib
import json


class ProcessorUnavailable(ValueError):
    pass


def _local_processing(entity, language, voice_id):
    """Additional locality proof only for sources requiring local processing.

    This is not the provider compatibility gate. Unknown providers remain usable
    for independently cloud-qualified text, but are never assumed local.
    """
    try:
        from homeassistant.components.wyoming.tts import WyomingTtsProvider
    except ImportError:
        return None
    service = entity.service if type(entity) is WyomingTtsProvider else None
    try:
        address = ipaddress.ip_address(service.host) if service else None
    except (ValueError, AttributeError):
        return None
    info = getattr(getattr(entity, "coordinator", None), "data", None)
    programs = [p for p in info.tts if p.installed] if service and info else []
    if (not address or not (address.is_private or address.is_loopback) or address.is_unspecified
        or address.is_multicast or len(programs) != 1 or programs[0].name.lower() != "piper"):
        return None
    voice = next((v for v in programs[0].voices
                  if v.installed and v.name == voice_id and language in v.languages), None)
    if voice is None:
        return None
    return {"provider_version": programs[0].version, "voice_version": voice.version}


def _selected_pipeline(hass, conf):
    """Use HA's supported selector, including its real preferred/default rule."""
    try:
        from homeassistant.components.assist_pipeline.pipeline import async_get_pipeline
        return async_get_pipeline(hass, str(conf.get("assist_pipeline_id") or "").strip() or None)
    except Exception:
        raise ProcessorUnavailable("processor_not_qualified") from None


def preference_context():
    """Client-local Session preference; never shared pipeline/Profile settings."""
    return {"scope": "owner_session_device", "storage_owner": "client",
            "key_fields": ["ha_installation", "profile_id", "session_id", "device_id"],
            "runtime_mutable": True, "session_end": "discard"}


def voice_inventory(entity, language, *, configured_voice=None):
    """Only supported HA Voice metadata; bounded, no inferred gender."""
    from itertools import islice
    callback = getattr(entity, "async_get_supported_voices", None)
    voices = callback(language) if callable(callback) else []
    cloud_genders = _cloud_voice_genders(entity, language)
    result = []
    seen = set()
    for voice in islice(voices or [], 512):
        identifier = getattr(voice, "voice_id", None)
        name = getattr(voice, "name", None)
        if (not isinstance(identifier, str) or not 0 < len(identifier) <= 128
                or identifier != identifier.strip() or not identifier.isprintable()
                or identifier in seen or not isinstance(name, str) or not name.strip()
                or not name.isprintable()):
            continue
        seen.add(identifier)
        explicit = getattr(voice, "gender", None)
        explicit = getattr(explicit, "value", explicit)
        gender = explicit if explicit in ("female", "male") else None
        if cloud_genders is not None:
            # Only exact provider metadata; never derive gender from a name.
            mapped = cloud_genders.get(identifier)
            gender = mapped if gender is None or gender == mapped else None
        result.append({"voice_id": identifier, "name": name[:120], "gender": gender})
    # Some Cloud languages contain more than64 voices. Keep qualified gender
    # targets and the configured voice visible without making caller IDs a way
    # to bypass the advertised selection bound. Even iteration stays bounded.
    priority = {configured_voice, *(cloud_genders or {})}
    result.sort(key=lambda v: v["voice_id"] not in priority)
    return result[:64]


def _cloud_voice_genders(entity, language):
    """Installed Cloud metadata, intersected by the caller with live inventory.

    None means another provider or unavailable metadata. Do not copy catalogues
    or invoke the deprecated Cloud gender request option (which creates Repairs).
    """
    if type(entity).__module__ != "homeassistant.components.cloud.tts":
        return None
    try:
        from homeassistant.components.cloud.tts import CloudTTSEntity, CloudProvider
        from hass_nabucasa.voice import MAP_VOICE
    except ImportError:
        return None
    if type(entity) not in (CloudTTSEntity, CloudProvider) or not isinstance(MAP_VOICE, dict):
        return None
    result = {}
    for key, identifier in MAP_VOICE.items():
        if not isinstance(key, tuple) or len(key) != 2:
            continue
        locale, gender = key
        value = getattr(gender, "value", gender)
        if locale == language and value in ("female", "male") and isinstance(identifier, str):
            result[identifier] = value
    return result


def _gender_targets(inventory, configured_voice):
    """Stable, advertised targets; prefer the already configured matching voice."""
    targets = {}
    for gender in ("female", "male"):
        identifiers = sorted(v["voice_id"] for v in inventory if v["gender"] == gender)
        if identifiers:
            targets[gender] = configured_voice if configured_voice in identifiers else identifiers[0]
    return targets


def configured_processor(hass, conf, locale, preference, *, selected_voice=None):
    """Resolve only the selected HA provider, language and voice, without I/O."""
    try:
        from homeassistant.components import tts
    except ImportError:
        raise ProcessorUnavailable("processor_not_qualified") from None
    from .tts import _first_attr

    pipeline = _selected_pipeline(hass, conf)
    selected_id = str(conf.get("assist_pipeline_id") or "").strip()
    pipeline_id = str(_first_attr(pipeline, "id") or "")
    if selected_id and selected_id != pipeline_id:
        # The legacy helper returns alternatives too. Session speech must not
        # silently use them when an explicitly selected pipeline is missing.
        raise ProcessorUnavailable("processor_not_qualified")
    engine_id = str(_first_attr(pipeline, "tts_engine", "tts_engine_id") or "")
    language = str(_first_attr(pipeline, "tts_language", "language") or "")
    voice_id = str(_first_attr(pipeline, "tts_voice", "voice") or "")
    configured_voice = voice_id
    explicit_voice = bool(voice_id)
    try:
        entity = tts.get_engine_instance(hass, engine_id) if engine_id else None
    except (KeyError, ValueError, AttributeError):
        raise ProcessorUnavailable("processor_not_qualified") from None
    if (entity is None or not callable(getattr(entity, "async_get_tts_audio", None))):
        raise ProcessorUnavailable("processor_not_qualified")
    if not getattr(entity, "available", True):
        raise ProcessorUnavailable("tts_provider_unavailable")
    if (language.replace("_", "-").split("-", 1)[0] != locale
            or language not in entity.supported_languages):
        raise ProcessorUnavailable("no_matching_locale")
    defaults = entity.default_options or {}
    if not voice_id:
        voice_id = str(defaults.get("voice") or "")
    voices = voice_inventory(entity, language, configured_voice=voice_id)
    if selected_voice is not None:
        if not any(v["voice_id"] == selected_voice for v in voices):
            raise ProcessorUnavailable("no_matching_voice")
        voice_id = selected_voice
    if preference != "default":
        targets = _gender_targets(voices, voice_id)
        if preference not in targets:
            raise ProcessorUnavailable("voice_gender_unavailable")
        if selected_voice is not None:
            if not any(v["voice_id"] == selected_voice and v["gender"] == preference for v in voices):
                raise ProcessorUnavailable("no_matching_voice")
        else:
            voice_id = targets[preference]
    actual = next((v for v in voices if v["voice_id"] == voice_id), None)
    if voice_id and actual is None and (explicit_voice or voices):
        raise ProcessorUnavailable("no_matching_voice")
    if voices and not voice_id:
        # An inventory is not permission to pick its first voice.
        raise ProcessorUnavailable("no_matching_voice")
    local = _local_processing(entity, language, voice_id)
    # Opaque equality evidence: never expose entry data, prompts or secrets.
    entry = getattr(entity, "entry", None)
    subentry = getattr(entity, "subentry", None)
    platform = getattr(entity, "platform", None)
    platform_entry = getattr(platform, "config_entry", None)
    revision = hashlib.sha256(json.dumps({
        "entry_modified": str(getattr(entry or platform_entry, "modified_at", "")),
        "subentry": getattr(subentry, "data", {}), "defaults": dict(defaults),
        "pipeline_voice": configured_voice,
        "voice_inventory": voices,
    }, sort_keys=True, default=str).encode()).hexdigest()[:24]
    return entity, {"processor": "ha_configured", "engine": engine_id,
                    "pipeline_id": pipeline_id,
                    "provider": str(getattr(platform, "platform_name", "") or engine_id.split(".")[0]),
                    "voice_id": voice_id or None,
                    "voice_name": actual["name"] if actual else None,
                    "voice_selection": "session_device_preference" if selected_voice is not None or preference != "default" else ("configured" if explicit_voice else "provider_default"),
                    "locale": language, "gender": actual["gender"] if actual else None,
                    "processing_scope": "qualified_local" if local else "configured_provider",
                    "configuration_revision": revision, **(local or {})}


MOOD_DELIVERY = {
    "chill": "Use a relaxed, gentle, unhurried delivery, soft emphasis and comfortable pauses. Stay warmly engaged, not sleepy or whispered.",
    "groove": "Use a warm, easy conversational rhythm, lightly buoyant phrasing and natural melodic emphasis.",
    "energy": "Use lively, confident delivery with crisp articulation, animated pitch contours and forward momentum. Do not shout.",
    "party": "Sound celebratory, playful and excited: animated pitch contours, bright emphatic accents and buoyant rhythmic phrasing. Keep clear natural speech; do not shout.",
}


def mood_prosody(entity, mood=None):
    """Qualify actual HA per-request instructions; speed is not expression."""
    available = False
    try:
        from homeassistant.components.openai_conversation.tts import OpenAITTSEntity
        available = (type(entity) is OpenAITTSEntity
                     and entity.subentry.data.get("chat_model") == "gpt-4o-mini-tts"
                     and isinstance(entity.subentry.data.get("prompt", ""), str)
                     and len(entity.subentry.data.get("prompt", "")) <= 4000)
    except (ImportError, AttributeError):
        pass
    return {"version": 1, "available": available,
            "moods": list(MOOD_DELIVERY) if available else [],
            "mood": mood if mood in MOOD_DELIVERY else None,
            "state": "applied" if available and mood in MOOD_DELIVERY else "unavailable",
            "reason": (None if available and mood in MOOD_DELIVERY else
                       "accepted_mood_unknown" if available else "provider_prosody_not_qualified")}


async def synthesize(entity, voice, text):
    """Call the exact already configured HA entity once, with the admitted text."""
    from .tts import _audio_type, TtsAudio

    options = dict(entity.default_options or {})
    expression = voice.get("mood_prosody") or {}
    qualified = mood_prosody(entity, expression.get("mood"))
    if qualified["state"] == "applied":
        original = entity.subentry.data.get("prompt", "")
        options["prompt"] = original + "\n\nDJConnect vocal delivery: " + MOOD_DELIVERY[qualified["mood"]] + (
            " Speak the supplied text verbatim in its original language. These instructions concern vocal intonation only."
            " Do not add or remove words, laughter, sound effects or facts. Preserve the selected voice."
        )
    if voice["voice_id"]:
        options["voice"] = voice["voice_id"]
        if _cloud_voice_genders(entity, voice["locale"]) is not None:
            options.pop("gender", None)
    mime, body = await entity.async_get_tts_audio(text, voice["locale"], options)
    if not isinstance(body, bytes) or not 0 < len(body) <= 2 * 1024 * 1024:
        raise ProcessorUnavailable("unsupported_audio_extent")
    kind = _audio_type(mime, body)
    if kind == "mp3" and _valid_mp3(body):
        return TtsAudio(body, "mp3", "audio/mpeg")
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


def _valid_mp3(body):
    """Require two complete contiguous Layer-III frames, not an ID3/MIME claim."""
    offset = 0
    if body.startswith(b"ID3"):
        if len(body) < 10 or any(b & 0x80 for b in body[6:10]):
            return False
        offset = 10 + sum(b << shift for b, shift in zip(body[6:10], (21, 14, 7, 0)))
        if body[5] & 0x10:
            offset += 10  # ID3v2.4 footer.
    for _ in range(2):
        if len(body) < offset + 4:
            return False
        a, b, c, _ = body[offset:offset+4]
        version, layer = (b >> 3) & 3, (b >> 1) & 3
        bitrate, rate = c >> 4, (c >> 2) & 3
        if (a != 0xFF or b & 0xE0 != 0xE0 or version == 1 or layer != 1
                or bitrate in (0, 15) or rate == 3):
            return False
        rates = (44100, 48000, 32000)
        sample_rate = rates[rate] // (1 if version == 3 else 2 if version == 2 else 4)
        bitrates = ((0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
                    if version == 3 else (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160))
        size = (144 if version == 3 else 72) * bitrates[bitrate] * 1000 // sample_rate + ((c >> 1) & 1)
        offset += size
        if offset > len(body):
            return False
    return True


def voice_options(hass, conf):
    """Read current provider support; no synthesis, lookup, inferred gender or writes."""
    from .tts import _first_attr
    options = {"schema_version": 1, "authority": "configured_ha_assist_pipeline_provider",
               "preference_scope": "device_local", "default_preference": "default",
               "default_available": False, "supported_preferences": ["default"],
               "gender_selection": {"available": False, "values": [],
                                    "reason": "provider_gender_metadata_unavailable"},
               "provider_voice": None, "cache_policy": "private,no-store",
               "preference_context": preference_context(), "voices": [],
               "voice_selection": {"available": False, "maximum_voices": 64}}
    try:
        pipeline = _selected_pipeline(hass, conf)
        locale = str(_first_attr(pipeline, "tts_language", "language") or "").replace("_", "-").split("-", 1)[0]
        entity, voice = configured_processor(hass, conf, locale, "default")
        inventory = voice_inventory(entity, voice["locale"], configured_voice=voice["voice_id"])
    except ProcessorUnavailable as exc:
        options["state"] = "unavailable"
        options["reason"] = str(exc)
    except Exception:
        options["state"] = "unavailable"
        options["reason"] = "processor_not_qualified"
    else:
        options.update(state="available", reason=None, default_available=True, provider_voice=voice,
                       voices=inventory, voice_selection={"available": bool(inventory), "maximum_voices": 64})
        options["mood_prosody"] = mood_prosody(entity)
        targets = _gender_targets(inventory, voice["voice_id"])
        if targets:
            options["gender_selection"] = {"available": True, "values": list(targets),
                "voice_ids": targets, "reason": None}
            options["supported_preferences"] += list(targets)
    import hashlib
    import json
    options["revision"] = hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()[:24]
    return options
