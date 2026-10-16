"""Private accepted-reference speech presentation in existing contribution owners.

Text is never supplied by a caller. The dialogue window owns ephemeral replies;
this module neither archives a body nor repeats semantic Ask DJ execution.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import time

PATH = "/api/djconnect/v1/speech/prepare"
TTL = 300
MAX_TEXT = 4000
MAX_SEGMENT = 1200
MAX_SEGMENTS = 8
MAX_REFERENCES = 8


def accepted_processing_basis(result):
    """Server-established processing provenance, never inferred from history text."""
    basis = result.get("speech_processing_basis") or result.get("model_processing_basis")
    return basis if basis in {"qualified_dialogue_v1", "cc0_normalized_fields_v1",
        "runtime_authored_direction_v1", "spotify_owner_local_read_v1"} else "accepted_local_reply"


def capability():
    return {"available": True, "version": 1, "path": PATH, "method": "POST",
            "authentication": "paired_device_bearer", "owner_only": True,
            "supported_reference_kinds": ["turn_id", "moment_id", "entry_id"],
            "source_kinds": ["accepted_ask_dj", "published_dj_moment", "retained_dj_contribution"],
            "processors": ["local_on_device", "ha_configured"],
            "processor_qualification_required": True,
            "provider_feedback": {"version": 1, "voice_options_path": "/api/djconnect/v1/speech/voice-options",
                                  "audio_configuration_error_status": 409,
                                  "languages": ["en", "nl", "de", "fr", "es"]},
            "voice_preference_context": {"scope": "owner_session_device", "storage_owner": "client",
                                         "runtime_mutable": True, "session_end": "discard"},
            "session_voice_selection": {"optional_voice_id": True, "authority": "configured_ha_assist_pipeline_provider"},
            "gender_preference": {"optional": True, "authority": "configured_ha_assist_pipeline_provider",
                                  "options_path": "/api/djconnect/v1/speech/voice-options"}, "voice_selection": "renderer_owned_or_exact_configured",
            "autoplay_scope": "per_device_new_publication_only", "manual_after_never": True,
            "ask_dj_request_version_field": "speech_contract_version",
            "voice_request_version_header": "X-DJConnect-Speech-Contract-Version",
            "legacy_private_audio_disposition": "client_protocol_upgrade_required",
            "history_mints_reference": False, "maximum_seconds": TTL,
            "maximum_text_characters": MAX_TEXT, "maximum_segments": MAX_SEGMENTS,
            "cache_policy": "private,no-store"}


def unavailable(reference, reason):
    return {"schema_version": 1, "reference": reference, "state": "unavailable",
            "reason": reason, "manual_allowed": False, "autoplay_eligible": False,
            "segments": [], "processors": [], "cache_policy": "private,no-store"}


def exact_segments(text):
    """Keep every accepted character; split only at natural whitespace boundaries."""
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        return None
    from .presentation_composer import SpeechSegment, SpeakerRole
    remaining, result = text, []
    while remaining and len(result) < MAX_SEGMENTS:
        end = min(MAX_SEGMENT, len(remaining))
        if len(remaining) > end:
            end = max(remaining.rfind("\n", 0, end) + 1,
                      remaining.rfind(" ", 0, end) + 1)
            if end <= 0:
                return None
        result.append(SpeechSegment(len(result) + 1, SpeakerRole.DJ, remaining[:end]).as_dict())
        remaining = remaining[end:]
    return result if not remaining else None


def projection(record, *, autoplay=False):
    return {"schema_version": 1, "reference": {"turn_id": record["turn_id"]},
            "source_kind": "accepted_ask_dj", "source_id": record["turn_id"],
            "session_id": record["session_id"] or None,
            "text_revision": record["text_revision"],
            "presentation_revision": record["text_revision"],
            "persona": record["persona"], "persona_revision": record["persona_revision"],
            "locale": record["locale"], "segments": exact_segments(record["text"]),
            "state": "available", "reason": None, "manual_allowed": True,
            "autoplay_eligible": autoplay, "processors": ["local_on_device", "ha_configured"],
            "processor_qualification_required": True,
            "expires_at": record["expires_at"], "cache_policy": "private,no-store",
            "attribution": deepcopy(record["attribution"])}


def remember(state, turn, result, *, turn_id, session_id, persona_revision,
             scope_revision, grant_revision, profile_source, playback_item_id="", deduplicated=False, autoplay_eligible=False):
    """Attach an immutable reference only after the common semantic commit.

    Exactly eight bounded replies per already bounded frame, original five-minute
    deadlines. Deleting a frame deletes its references. A saved/deduplicated turn
    never opens a new grant or renews the first one.
    """
    frame = turn.frame
    now = state.clock()
    for key, item in list(frame.speech_references.items()):
        if now >= item["deadline"]:
            old = frame.speech_references.pop(key)
            old["dispose"]()
    if turn_id in frame.speech_references:
        return projection(frame.speech_references[turn_id])
    reference = {"turn_id": turn_id}
    text = result.get("text") or result.get("dj_text")
    if deduplicated:
        return unavailable(reference, "original_reference_not_retained")
    if exact_segments(text) is None:
        return unavailable(reference, "unsupported_text_extent")
    if len(frame.speech_references) >= MAX_REFERENCES:
        old = frame.speech_references.pop(next(iter(frame.speech_references)))
        old["dispose"]()
    revision = hashlib.sha256(text.encode()).hexdigest()[:24]
    admissions = tuple(turn.delivery_validators)
    deadline = min([now + TTL, *(getattr(validate, "speech_deadline", now + TTL) for validate in admissions)])
    if turn.speech_deadline is not None:
        deadline = min(deadline, turn.speech_deadline)
    if frame.result_set:
        deadline = min(deadline, frame.result_set["deadline"])
    for name in ("queue_observation", "session_forecast"):
        stamp = (result.get(name) or {}).get("valid_until")
        if stamp:
            try:
                expiry = datetime.fromisoformat(stamp)
                if expiry.tzinfo is None:
                    return unavailable(reference, "original_source_expired")
                deadline = min(deadline, now + expiry.timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                return unavailable(reference, "original_source_expired")
    try:
        for validate in admissions:
            validate()
    except Exception:
        return unavailable(reference, "original_source_withdrawn")
    attribution = result.get("sources") or []
    if not isinstance(attribution, list) or len(attribution) > 8 or len(json.dumps(attribution)) > 4096:
        return unavailable(reference, "unsupported_attribution_extent")
    if deadline <= now:
        return unavailable(reference, "original_source_expired")
    record = {"turn_id": turn_id, "text": text, "text_revision": revision,
              "persona": turn.style["persona"], "persona_revision": persona_revision,
              "locale": turn.style["language"], "session_id": session_id,
              "playback_item_id": playback_item_id, "generation": frame.generation,
              "scope_revision": scope_revision, "grant_revision": grant_revision,
              "profile_source": deepcopy(profile_source), "dependencies": deepcopy(turn.dependencies),
              "deadline": deadline, "admissions": admissions,
              "expires_at": datetime.fromtimestamp(time.time() + deadline - now, UTC).isoformat(),
              "attribution": deepcopy(attribution),
              "processor_basis": accepted_processing_basis(result)}
    record["disposals"] = []
    def expire():
        if frame.speech_references.get(turn_id) is record:
            frame.speech_references.pop(turn_id, None)
        handle = record.pop("expiry_handle", None)
        if handle is not None:
            handle.cancel()
        record["withdrawn"] = True
        record.pop("text", None)
        record["admissions"] = ()
        for dispose in record.pop("disposals", []):
            dispose()
    record["dispose"] = expire
    record["expiry_handle"] = asyncio.get_running_loop().call_later(deadline - now, expire)
    frame.speech_references[turn_id] = record
    return projection(record, autoplay=autoplay_eligible)


async def resolve_dialogue(hass, history, profile_id, reference, *, profile_source):
    """Read an accepted RAM reference without touching idle or source deadlines."""
    from .ask_dj.service import _live_reference
    from .session_conversation import async_history_grant_revision, history_grant_revision, query_service
    from .session_runtime import session_runtime_manager

    threads = history.dialogue.owners.get("profile:" + profile_id, {})
    found = next(((f, f.speech_references[reference["turn_id"]]) for f in threads.values()
                  if reference["turn_id"] in f.speech_references), None)
    if found is None:
        raise PermissionError("speech_reference_unavailable")
    frame, record = found
    manager = session_runtime_manager(hass)
    scope = "profile:" + profile_id
    # Read durable invalidation epochs before checking the synchronous final fence.
    await history.async_scope_revision(scope)
    await async_history_grant_revision(hass, profile_id)

    def guard():
        if (record.get("withdrawn") or record["generation"] != frame.generation
            or not any(current is frame for current in history.dialogue.owners.get(scope, {}).values())
            or frame.speech_references.get(record["turn_id"]) is not record
            or history.dialogue.clock() >= record["deadline"]
            or record["scope_revision"] != history.scope_revision(scope)
            or record["grant_revision"] != history_grant_revision(hass, profile_id)
            or record["profile_source"] != profile_source):
            raise PermissionError("speech_reference_withdrawn")
        for validate in record["admissions"]:
            validate()
        if record["session_id"]:
            active = manager.current_active(profile_id)
            if (active is None or active.session_id != record["session_id"]
                or (record["playback_item_id"] and active.broadcast.state.playback.item_id != record["playback_item_id"])):
                raise PermissionError("speech_reference_withdrawn")
    guard()
    for dependency in record["dependencies"]:
        if "moment_id" in dependency:
            await _live_reference(manager, profile_id, dependency)
        else:
            await query_service(hass, history).async_open_entry(profile_id, dependency["session_id"], dependency["entry_id"])
        guard()
    def on_withdraw(callback):
        if record.get("withdrawn"):
            callback()
            return lambda: None
        record["disposals"].append(callback)
        def remove():
            callbacks = record.get("disposals", [])
            if callback in callbacks:
                callbacks.remove(callback)
        return remove
    guard.on_withdraw = on_withdraw
    guard.processor_basis = record["processor_basis"]
    if record["session_id"]:
        from .dj_response import PrivateSpeechSource, invalidate_private_speech_sources, collect_private_speech_sources
        source = PrivateSpeechSource(hass, guard,
            expires_at=datetime.fromisoformat(record["expires_at"]).timestamp(), session_id=record["session_id"])
        original_watch = source.on_withdraw
        def watch(callback):
            remove = original_watch(callback)
            try:
                remove_record = guard.on_withdraw(source.withdraw)
            except BaseException:
                remove()
                raise
            def unsubscribe():
                remove()
                remove_record()
            return unsubscribe
        source.on_withdraw = watch
        source.processor_basis = guard.processor_basis
        active = manager.current_active(profile_id)
        active.broadcast.speech_cleanup = lambda: invalidate_private_speech_sources(hass, session_id=record["session_id"])
        active.broadcast.speech_refresh = lambda: collect_private_speech_sources(hass, session_id=record["session_id"])
        return projection(record), source
    return projection(record), guard


def _contribution_descriptor(reference, *, text, locale, persona, persona_revision,
                             expires_at, source_kind, attribution, autoplay=False):
    if not isinstance(locale, str) or locale not in {"en", "nl", "de", "fr", "es"}:
        return unavailable(reference, "original_locale_unknown")
    try:
        if not isinstance(attribution, list) or len(attribution) > 8 or len(json.dumps(attribution, allow_nan=False)) > 4096:
            return unavailable(reference, "unsupported_attribution_extent")
    except (TypeError, ValueError):
        return unavailable(reference, "unsupported_attribution_extent")
    if persona not in ("home_dj", "radio_dj", "club_dj", "festival_dj"):
        persona = None
    if type(persona_revision) is not int or persona_revision < 0:
        persona_revision = None
    segments = exact_segments(text)
    if segments is None:
        return unavailable(reference, "unsupported_text_extent")
    revision = hashlib.sha256(text.encode()).hexdigest()[:24]
    presentation = hashlib.sha256(json.dumps([reference, revision, locale, persona,
        persona_revision, attribution], sort_keys=True).encode()).hexdigest()[:24]
    return {"schema_version": 1, "reference": reference, "source_kind": source_kind,
            "source_id": reference.get("moment_id") or reference.get("entry_id"),
            "session_id": reference["session_id"], "text_revision": revision,
            "presentation_revision": presentation, "persona": persona,
            "persona_revision": persona_revision, "locale": locale, "segments": segments,
            "style_basis": "accepted_contribution" if persona is not None else "legacy_unknown",
            "state": "available", "reason": None, "manual_allowed": True,
            "autoplay_eligible": autoplay, "processors": ["local_on_device", "ha_configured"],
            "processor_qualification_required": True,
            "expires_at": expires_at, "source_expires_at": expires_at,
            "attribution": attribution, "cache_policy": "private,no-store"}


def moment_projection(broadcast, moment, *, autoplay=False, admission=None):
    """Pure owner speech admission over already published immutable content."""
    reference = {"session_id": broadcast.state.session_id, "moment_id": moment.moment_id}
    if admission is None:
        admission = next((a for a in broadcast.native_delivery()["admissions"]
                          if a["moment_id"] == moment.moment_id), None)
    boundary = broadcast._moment_delivery_boundaries.get(moment.moment_id)
    if (boundary is None or not admission or admission["qualification"] != "qualified"
            or not (admission["current_display_allowed"] or admission["active_flow_display_allowed"])):
        return unavailable(reference, "original_source_unavailable")
    # No read renews the source window. Current-only catalog retains its display
    # deadline; CC0 Flow uses the source deadline, authored direction1800s.
    expiry = (admission["source_expires_at"] or boundary.utc_at(boundary.published_monotonic + 1800)
              if admission["active_flow_display_allowed"] else admission["display_expires_at"])
    if not expiry or datetime.fromisoformat(expiry).timestamp() <= time.time():
        return unavailable(reference, "original_source_expired")
    return _contribution_descriptor(reference, text=moment.content, locale=broadcast.state.locale,
        persona=moment.presentation_intent.dj_persona.value, persona_revision=boundary.persona_revision,
        expires_at=expiry, source_kind="published_dj_moment",
        attribution=[dict(moment.source_attribution)] if moment.source_attribution else [], autoplay=autoplay)


async def resolve_moment(hass, profile_id, reference):
    from .session_runtime import session_runtime_manager
    from .dj_response import PrivateSpeechSource, invalidate_private_speech_sources, collect_private_speech_sources
    manager = session_runtime_manager(hass)
    active = manager.current_active(profile_id)
    if active is None or active.session_id != reference["session_id"]:
        raise PermissionError("speech_reference_unavailable")
    broadcast = active.broadcast
    moment = next((m for m in broadcast.state.dj_moments if m.moment_id == reference["moment_id"]), None)
    if moment is None:
        raise PermissionError("speech_reference_unavailable")
    descriptor = moment_projection(broadcast, moment)
    if not descriptor["manual_allowed"]:
        raise PermissionError("speech_reference_unavailable")
    descriptor["expires_at"] = datetime.fromtimestamp(min(time.time()+TTL,
        datetime.fromisoformat(descriptor["source_expires_at"]).timestamp()), UTC).isoformat()
    def validate():
        current = manager.current_active(profile_id)
        if (current is None or current.broadcast is not broadcast
                or not moment_projection(broadcast, moment)["manual_allowed"]):
            raise PermissionError("speech_reference_withdrawn")
    guard = PrivateSpeechSource(hass, validate,
        expires_at=datetime.fromisoformat(descriptor["expires_at"]).timestamp(), session_id=active.session_id)
    source = moment.source_fact
    guard.processor_basis = ("spotify_owner_local_read_v1" if (source is not None and source.provider == "Spotify") or moment.observed_playback is not None or moment.genre_transition is not None
        else "cc0_normalized_fields_v1" if source is not None else "runtime_authored_direction_v1")
    broadcast.speech_cleanup = lambda: invalidate_private_speech_sources(hass, session_id=active.session_id)
    broadcast.speech_refresh = lambda: collect_private_speech_sources(hass, session_id=active.session_id)
    guard()
    return descriptor, guard


def retained_projection(entry):
    """Pure owner-entry speech state; no resources or new read-time deadline."""
    reference = {"session_id": entry["session_id"], "entry_id": entry["entry_id"]}
    if entry["kind"] == "dj_moment" and entry.get("archive_basis") in {
            "cc0_normalized_fields_v1", "runtime_authored_direction_v1"}:
        style = {"language": entry.get("locale"), "persona": entry.get("persona"),
                 "persona_revision": entry.get("persona_revision")}
        attribution = [entry["source_attribution"]] if entry.get("source_attribution") else []
    elif entry["kind"] == "conversation_dj" and entry.get("role") == "assistant":
        style = entry.get("effective_style") or {}
        if not isinstance(style, dict):
            style = {}
        attribution = entry.get("sources") or []
    else:
        return unavailable(reference, "original_source_unqualified")
    return _contribution_descriptor(reference, text=entry.get("text"), locale=style.get("language"),
        persona=style.get("persona"), persona_revision=style.get("persona_revision"),
        expires_at=entry["retained_until"], source_kind="retained_dj_contribution", attribution=attribution)


async def resolve_retained(hass, history, profile_id, reference):
    from .session_conversation import (query_service, async_history_grant_revision, history_grant_revision)
    from .persistence import persistence_service
    from .dj_response import PrivateSpeechSource, invalidate_private_speech_sources
    domain = hass.data.setdefault("djconnect", {})
    epoch = domain.setdefault("tts_audio_authority_revision", 0)
    service = persistence_service(hass)
    service.session_speech_invalidator = lambda: invalidate_private_speech_sources(hass)
    grant = await async_history_grant_revision(hass, profile_id)
    revision = await history.async_scope_revision("profile:" + profile_id)
    opened = await query_service(hass, history).async_open_entry(profile_id, reference["session_id"], reference["entry_id"])
    entry = opened["entry"]
    if entry["kind"] not in {"dj_moment", "conversation_dj"}:
        raise PermissionError("speech_reference_unqualified")
    descriptor = retained_projection(entry)
    basis = (entry.get("archive_basis") if entry["kind"] == "dj_moment"
             else entry.get("speech_processing_basis") or "retained_owner_local_read_v1")
    expires = min(time.time() + TTL, datetime.fromisoformat(entry["retained_until"]).timestamp())
    if descriptor["manual_allowed"]:
        descriptor["expires_at"] = datetime.fromtimestamp(expires, UTC).isoformat()
    def validate():
        if (history_grant_revision(hass, profile_id) != grant
                or history.scope_revision("profile:" + profile_id) != revision):
            raise PermissionError("speech_reference_withdrawn")
    guard = PrivateSpeechSource(hass, validate, expires_at=expires)
    guard.epoch = epoch  # Also fence a destructive transaction during entry reads.
    guard.processor_basis = basis
    guard()
    return descriptor, guard


async def async_handle_prepare(hass, data, *, headers=None):
    from .api_handlers import _session_profile_context, _conversation_profile_fence
    from .ask_dj.dialogue import source_scope
    from .http import _history_manager
    from .profile_privacy import resolve_profile_privacy_policy
    from .session_conversation import SessionConversationError
    from .ask_dj.dialogue import DialogueError
    from .transport_delivery import register_delivery_admission
    from .session_history_projection import HistoryQueryError

    fields = {"contract_version", "device_id", "client_type", "reference", "processor", "voice_preference"}
    if (not isinstance(data, dict) or not fields <= set(data) or set(data) - fields - {"voice_id"}
        or ("voice_id" in data and (data.get("processor") != "ha_configured"
            or not isinstance(data["voice_id"], str) or not 0 < len(data["voice_id"]) <= 128
            or data["voice_id"] != data["voice_id"].strip() or not data["voice_id"].isprintable()))
        or type(data["contract_version"]) is not int or data["contract_version"] != 1
        or data["processor"] not in ("local_on_device", "ha_configured")
        or data["voice_preference"] not in ("default", "male", "female")
        or not isinstance(data["reference"], dict)
        or set(data["reference"]) not in ({"turn_id"}, {"session_id", "moment_id"}, {"session_id", "entry_id"})
        or not all(isinstance(value, str) and 0 < len(value) <= 128 and value == value.strip()
                   for value in data["reference"].values())):
        return {"success": False, "error": "invalid_request"}, 400
    headers = headers or {}
    if not str(headers.get("Authorization", "")).startswith("Bearer ") or data["client_type"] == "windows":
        return {"success": False, "error": "unauthorized"}, 401
    identity = {key: data[key] for key in ("device_id", "client_type")}
    runtime, context, error, status = await _session_profile_context(
        hass, identity, headers=headers, user_id=None, source="session_speech_prepare")
    if error is not None:
        return error, status
    try:
        if not context.privacy_policy.allow_personal_read or not resolve_profile_privacy_policy(context.profile, {}).allow_personal_read:
            raise PermissionError("speech_not_allowed")
        history = _history_manager(hass, runtime)
        reference = data["reference"]
        if "moment_id" in reference:
            descriptor, source_guard = await resolve_moment(hass, context.profile_id, reference)
        elif "entry_id" in reference:
            descriptor, source_guard = await resolve_retained(hass, history, context.profile_id, reference)
        else:
            descriptor, source_guard = await resolve_dialogue(hass, history,
                context.profile_id, reference, profile_source=source_scope(context.profile))
        def guard():
            _conversation_profile_fence(hass, runtime, identity, headers, context)
            source_guard()
        guard.on_withdraw = source_guard.on_withdraw
        guard.processor_basis = source_guard.processor_basis
        guard()
        register_delivery_admission(guard)
        if not descriptor["manual_allowed"]:
            return {"success": True, "session_speech": descriptor}, 200
        if data["processor"] == "ha_configured":
            descriptor = await prepare_ha(hass, runtime, context.profile_id, data,
                                          descriptor, guard)
            guard()
        else:
            from .speech_processor import voice_options
            allowed = voice_options(hass, runtime.config)["gender_selection"]["values"]
            if data["voice_preference"] != "default" and data["voice_preference"] not in allowed:
                descriptor = unavailable(data["reference"], "voice_gender_unavailable")
            else:
                descriptor.update(audio_state="renderer_pending", effective_voice=None,
                                  voice_preference=data["voice_preference"], autoplay_eligible=False)
        guard()
        return {"success": True, "session_speech": descriptor}, 200
    except SessionConversationError as exc:
        return {"success": False, "error": exc.code}, exc.status
    except DialogueError:
        return {"success": False, "error": "speech_reference_unavailable"}, 404
    except HistoryQueryError:
        return {"success": False, "error": "speech_context_changed"}, 409
    except PermissionError as exc:
        status = 403 if str(exc) == "speech_not_allowed" else 404
        return {"success": False, "error": "speech_reference_unavailable"}, status


async def prepare_ha(hass, runtime, owner, data, descriptor, admission):
    from .dj_response import prepare_private_tts_audio, get_private_tts_audio
    from .speech_processor import configured_processor, synthesize, ProcessorUnavailable
    from .speech_feedback import SpeechProviderChanged, notification, record

    def failed(reason):
        result = unavailable(data["reference"], reason)
        notice = notification(reason, descriptor["locale"], retry_after=60 if reason in {
            "speech_retry_backoff", "speech_preparation_failed", "speech_preparation_timeout",
            "unsupported_audio_type", "unsupported_audio_extent"} else 0)
        if notice:
            result["notification"] = notice
        return result

    # CC0/direction support is admitted by its original owner below, not inferred
    # from a provider label. Private/catalog display is no cloud-processing grant.
    if admission.processor_basis not in {"qualified_dialogue_v1", "cc0_normalized_fields_v1", "runtime_authored_direction_v1", "spotify_owner_local_read_v1", "retained_owner_local_read_v1"}:
        return unavailable(data["reference"], "source_processor_not_qualified")
    def resolve_processor():
        if "voice_id" in data:
            return configured_processor(hass, runtime.config, descriptor["locale"],
                                        data["voice_preference"], selected_voice=data["voice_id"])
        return configured_processor(hass, runtime.config, descriptor["locale"], data["voice_preference"])

    entity = voice = None
    try:
        entity, voice = resolve_processor()
        if (admission.processor_basis in {"spotify_owner_local_read_v1", "retained_owner_local_read_v1"}
                and voice.get("processing_scope") != "qualified_local"):
            return unavailable(data["reference"], "source_processor_not_qualified")
        key = (owner, descriptor["source_id"], descriptor["text_revision"],
               descriptor["presentation_revision"], voice["engine"], voice["voice_id"], voice["locale"], id(entity),
               voice.get("provider_version"), voice.get("voice_version"),
               voice.get("configuration_revision"))
        def qualified_admission():
            admission()
            try:
                current_entity, current_voice = resolve_processor()
            except ProcessorUnavailable as exc:
                raise SpeechProviderChanged(str(exc), descriptor["locale"]) from None
            if current_entity is not entity or current_voice != voice:
                raise SpeechProviderChanged("speech_configuration_changed", descriptor["locale"])
        qualified_admission.on_withdraw = admission.on_withdraw
        qualified_admission.on_synthesized = lambda: record(hass, runtime, owner, voice, provider=entity)
        token = await prepare_private_tts_audio(hass, owner_profile_id=owner, cache_key=key,
            expires_at=datetime.fromisoformat(descriptor["expires_at"]).timestamp(), admission=qualified_admission,
            synthesize=lambda: synthesize(entity, voice, "".join(segment["text"] for segment in descriptor["segments"])))
        asset = get_private_tts_audio(hass, token, owner)
        return {**descriptor, "expires_at": datetime.fromtimestamp(asset.expires_at, UTC).isoformat(),
                "audio_state": "ready", "effective_voice": voice, "autoplay_eligible": False,
                "audio_reference": {"asset_id": token, "path": "/api/djconnect/v1/speech/audio", "method": "POST"}}
    except PermissionError:
        # Source/owner withdrawal stays opaque. A still-authorized contribution
        # can explain a provider change, even if a joined job masked its reason.
        admission()
        if entity is not None:
            try:
                qualified_admission()
            except SpeechProviderChanged as exc:
                return failed(str(exc))
        raise
    except Exception as exc:
        codes = {"processor_not_qualified", "tts_provider_unavailable", "no_matching_locale", "no_matching_voice", "voice_gender_unavailable",
                 "unsupported_audio_extent", "unsupported_audio_type", "speech_retry_backoff", "speech_capacity"}
        reason = str(exc) if isinstance(exc, (ProcessorUnavailable, ValueError)) and str(exc) in codes else (
            "speech_preparation_timeout" if isinstance(exc, TimeoutError) else "speech_preparation_failed")
        admission()
        if voice is not None and reason in {"speech_preparation_failed", "speech_preparation_timeout", "unsupported_audio_type", "unsupported_audio_extent"}:
            record(hass, runtime, owner, voice, provider=entity, reason=reason)
        return failed(reason)


async def async_handle_audio(hass, data, *, headers=None):
    """No bearer-free speech audio URL. Exact source admission on every byte read."""
    from .api_handlers import _session_profile_context, _conversation_profile_fence
    from .dj_response import get_private_tts_audio
    from .session_conversation import SessionConversationError
    from .speech_feedback import SpeechProviderChanged, notification
    fields = {"contract_version", "device_id", "client_type", "asset_id"}
    if (not isinstance(data, dict) or set(data) != fields
        or type(data["contract_version"]) is not int or data["contract_version"] != 1
        or not isinstance(data["asset_id"], str) or not 0 < len(data["asset_id"]) <= 64):
        return None, 400
    headers = headers or {}
    if not str(headers.get("Authorization", "")).startswith("Bearer ") or data["client_type"] == "windows":
        return None, 401
    identity = {key: data[key] for key in ("device_id", "client_type")}
    runtime, context, error, status = await _session_profile_context(
        hass, identity, headers=headers, user_id=None, source="session_speech_audio")
    if error is not None:
        return None, status
    try:
        _conversation_profile_fence(hass, runtime, identity, headers, context)
        item = get_private_tts_audio(hass, data["asset_id"], context.profile_id)
        return item, 200
    except SessionConversationError as exc:
        return None, exc.status
    except SpeechProviderChanged as exc:
        return {"success": False, "error": "speech_configuration_changed",
                "notification": notification(str(exc), exc.locale)}, 409
    except PermissionError:
        return None, 404


async def async_handle_voice_options(hass, data, *, headers=None):
    """Private owner readback for the optional provider-supported client setting."""
    from .api_handlers import _session_profile_context, _conversation_profile_fence
    from .speech_processor import voice_options
    from .session_conversation import SessionConversationError
    from .speech_feedback import status as provider_status
    fields = {"contract_version", "device_id", "client_type"}
    if (not isinstance(data, dict) or set(data) != fields
        or type(data["contract_version"]) is not int or data["contract_version"] != 1):
        return {"success": False, "error": "invalid_request"}, 400
    headers = headers or {}
    if not str(headers.get("Authorization", "")).startswith("Bearer ") or data["client_type"] == "windows":
        return {"success": False, "error": "unauthorized"}, 401
    identity = {key: data[key] for key in ("device_id", "client_type")}
    runtime, context, error, status = await _session_profile_context(
        hass, identity, headers=headers, user_id=None, source="session_speech_voice_options")
    if error is not None:
        return error, status
    try:
        result = voice_options(hass, runtime.config)
        result["provider_status"] = provider_status(hass, runtime, context.profile_id, result,
            getattr(hass.config, "language", "en"))
        result["notification"] = result["provider_status"]["notification"]
        result["revision"] = hashlib.sha256(json.dumps(
            {key: value for key, value in result.items() if key != "revision"}, sort_keys=True).encode()).hexdigest()[:24]
        _conversation_profile_fence(hass, runtime, identity, headers, context)
        return {"success": True, "speech_voice_options": result}, 200
    except SessionConversationError as exc:
        return {"success": False, "error": exc.code}, exc.status
