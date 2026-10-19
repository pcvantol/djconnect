"""Selection-bound HA speech discovery; no inference, audio or provider I/O."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json

from .speech_processor import ProcessorUnavailable


def _route(state, reason=None, *, configured=None, **extra):
    return {"state": state, "configured": configured, "available": state == "available",
            "reason": reason, **extra}


def _family(value):
    if not isinstance(value, str) or len(value) > 32:
        return None
    family = value.replace("_", "-").casefold().split("-", 1)[0]
    return family if family in {"en", "nl", "de", "fr", "es"} else None


def _stt(hass, pipeline, locale, incarnations):
    engine = getattr(pipeline, "stt_engine", None)
    if not engine:
        return _route("unconfigured", "stt_not_configured", configured=False)
    try:
        from homeassistant.components import stt
        from .assist_stt import SttInfo, _speech_metadata

        getter = getattr(stt, "async_get_speech_to_text_engine", None)
        if not callable(getter):
            return _route("unsupported", "stt_interface_unsupported", configured=True)
        provider = getter(hass, engine)
        if provider is None:
            return _route("unavailable", "stt_provider_unavailable", configured=True)
        incarnations.append(id(provider))
        if getattr(provider, "available", None) is False:
            return _route("unavailable", "stt_provider_unavailable", configured=True)
        language = getattr(pipeline, "stt_language", None) or getattr(pipeline, "language", None)
        if not language or not locale:
            return _route("unknown", "stt_language_unknown", configured=True)
        if _family(language) != locale:
            return _route("unsupported", "stt_language_unsupported", configured=True)
        checker = getattr(provider, "check_metadata", None)
        processor = (getattr(provider, "internal_async_process_audio_stream", None)
                     or getattr(provider, "async_process_audio_stream", None))
        if not callable(processor):
            return _route("unsupported", "stt_interface_unsupported", configured=True)
        if not callable(checker):
            return _route("unknown", "stt_metadata_unknown", configured=True)
        metadata = _speech_metadata(stt, SttInfo("", getattr(pipeline, "id", None),
            None, engine, language, "wav", 16000, 1, 2, 0))
        if not checker(metadata):
            return _route("unsupported", "stt_audio_or_language_unsupported", configured=True)
        if getattr(provider, "available", None) is not True:
            return _route("unknown", "stt_provider_availability_unknown", configured=True)
        return _route("available", configured=True, locale=language,
                      audio={"format": "wav", "codec": "pcm", "sample_rate": 16000,
                             "sample_width": 2, "channels": 1},
                      operational_state="not_tested")
    except Exception:  # Metadata lookup never authorizes a fallback or a probe.
        return _route("unknown", "stt_discovery_failed", configured=True)


def _tts(hass, runtime, pipeline, locale, owner, incarnations):
    if not getattr(pipeline, "tts_engine", None):
        return _route("unconfigured", "tts_not_configured", configured=False)
    try:
        from .speech_processor import configured_processor, voice_options
        from .speech_feedback import status

        entity, voice = configured_processor(hass, runtime.config, locale or "", "default")
        incarnations.append(id(entity))
        if getattr(entity, "available", None) is not True:
            return _route("unknown", "tts_provider_availability_unknown", configured=True)
        options = voice_options(hass, runtime.config)
        # Health observations are private to the actual bound Profile, never a
        # payload hint, fallback Profile or another request's runtime hint.
        health = (status(hass, runtime, owner, options, locale) if owner else
                  {"synthesis_state": "not_tested", "reason": None,
                   "observed_at": None, "retry_after_seconds": 0})
        # A past failure is not a current configuration failure. Its bounded
        # retry delay stays operational advice, never a five-minute route lock.
        return _route("available", configured=True,
            locale=voice["locale"], voice={key: voice.get(key) for key in
                ("voice_id", "voice_name", "gender", "voice_selection")},
            voices=options["voices"], gender_selection=options["gender_selection"],
            configuration_revision=options["revision"],
            operational={key: health[key] for key in
                ("synthesis_state", "reason", "observed_at", "retry_after_seconds")})
    except ProcessorUnavailable as exc:
        reason = str(exc)
        if reason not in {"processor_not_qualified", "tts_provider_unavailable",
                          "no_matching_locale", "no_matching_voice", "voice_gender_unavailable"}:
            return _route("unknown", "tts_discovery_failed", configured=True)
        state = "unsupported" if reason in {
            "no_matching_locale", "no_matching_voice", "voice_gender_unavailable"} else "unavailable"
        return _route(state, reason, configured=True)
    except Exception:
        return _route("unknown", "tts_discovery_failed", configured=True)


def snapshot(hass, runtime, *, locale=None, owner=None):
    """Fresh synchronous metadata snapshot; availability is not operational PASS."""
    from .announcement_policy import output_policy
    from .announcements import configured_announcement_speaker

    family = _family(locale if locale is not None else getattr(getattr(hass, "config", None), "language", "en"))
    incarnations = []
    result = {"schema_version": 1, "authority": "configured_ha_selection",
        "locale": family, "cache_policy": "private,no-store",
        "refresh": "each_authorized_status_read", "push": False,
        "proof": "current_configuration_not_remote_health_or_audio",
        "speech_permission": "requires_current_settings3_and_source_admission",
        "text_only": {"available": True, "audio": False},
        "apple_local": {"stt": "client_owned", "tts": "client_owned", "permissions": "client_owned"}}
    requested = str(runtime.config.get("assist_pipeline_id") or "").strip()
    result["assist"] = {"selection": "explicit" if requested else "preferred",
                        "pipeline_id": None, "conversation": _route("unknown", "pipeline_unavailable")}
    try:
        from homeassistant.components.assist_pipeline.pipeline import async_get_pipeline
        from homeassistant.components.conversation import async_get_agent

        pipeline = async_get_pipeline(hass, requested or None)
        engine = getattr(pipeline, "conversation_engine", None)
        agent = async_get_agent(hass, engine) if engine else None
        incarnations.append(id(agent))
        valid = (agent is not None and getattr(agent, "available", True) is True
                 and callable(getattr(agent, "async_process", None)))
        result["assist"].update(pipeline_id=getattr(pipeline, "id", None),
            conversation=_route("available" if valid else "unavailable",
                                None if valid else "conversation_agent_unavailable", configured=bool(engine)))
        result["ha_stt"] = _stt(hass, pipeline, family, incarnations)
        result["ha_tts"] = _tts(hass, runtime, pipeline, family, owner, incarnations)
    except Exception:
        result["ha_stt"] = _route("unknown", "pipeline_unavailable")
        result["ha_tts"] = _route("unknown", "pipeline_unavailable")
    try:
        target = output_policy(hass, runtime)
        configured = bool(configured_announcement_speaker(runtime))
        reason = target.reason
        state = ("available" if target.speaker_available else "unconfigured" if not configured else
                 "unsupported" if reason in {"announcement_speaker_invalid", "announcement_speaker_no_play_media"}
                 else "unavailable")
        result["ha_speaker_target"] = _route(state, reason, configured=configured,
            requires=["ha_tts", "current_output_policy"], revision=target.revision,
            audibility="not_tested", touch_reaction="not_qualified")
    except Exception:
        result["ha_speaker_target"] = _route("unknown", "speaker_discovery_failed")
    # Provider incarnation is equality evidence only; never exported as an ID.
    result["revision"] = hashlib.sha256(json.dumps([result, incarnations], sort_keys=True).encode()).hexdigest()[:24]
    result["evaluated_at"] = datetime.now(UTC).isoformat()
    return result


def _binding(hass, device_id):
    from .domain.storage import STORE_KEY
    storage = hass.data.get("djconnect", {}).get(STORE_KEY)
    if storage is None or not getattr(storage, "_loaded", False):
        return None
    try:
        device = storage.household.devices.get(device_id)
        profile = storage.resolver().resolve_bound_device(device_id)
        return (id(storage), getattr(device, "binding_generation", None),
                profile.profile_id, id(profile))
    except Exception:
        return None


def capture(hass, runtime, device_id):
    """Private equality evidence captured immediately after authentication."""
    return (getattr(runtime, "device_token", None), getattr(runtime, "entry", None),
            _binding(hass, device_id))


def append_snapshot(response, hass, runtime, *, device_id, client_type,
                    authority, locale=None):
    """Publish only after the last transport await and current device binding."""
    if client_type not in {"ios", "macos", "watchos"}:
        return
    try:
        from .request_auth import resolve_runtime, runtime_matches_device, authorize_runtime_device_request
        expected_token, expected_entry, binding = authority
        def authorized():
            entry = getattr(runtime, "entry", None)
            headers = {"Authorization": "Bearer " + expected_token} if expected_token else {}
            return (bool(expected_token) and getattr(runtime, "device_token", None) == expected_token
                and entry is expected_entry and entry is not None
                and entry.disabled_by is None and getattr(entry.state, "value", entry.state) == "loaded"
                and hass.config_entries.async_get_entry(entry.entry_id) is entry
                and hass.data.get("djconnect", {}).get(entry.entry_id) is runtime
                and entry.data.get("device_token") == expected_token
                and resolve_runtime(hass, device_id, headers) is runtime
                and runtime_matches_device(runtime, device_id)
                and authorize_runtime_device_request(runtime, headers, device_id, client_type)
                and _binding(hass, device_id) == binding)
        if not authorized():
            return  # Absent v1 snapshot is unknown, never legacy-boolean ready.
        owner = binding[2] if binding else None
        projected = snapshot(hass, runtime, locale=locale, owner=owner)
        if authorized():
            response["device_speech"] = projected
    except Exception:
        return  # Discovery cannot fail an otherwise compatible legacy status.
