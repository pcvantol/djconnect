"""One Ask DJ application service. Session references enrich, never select a pipeline."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
import time
from uuid import NAMESPACE_URL, uuid5

from .dialogue import (
    DialogueError, DialogueTurn, current_turn, model_source, references_topic,
    style_projection, explicit_quote,
    request_effect_grants,
    source_scope,
)
from ..session_conversation import (
    SessionConversationError, history_question, query_service, async_history_grant_revision,
    history_grant_revision,
)
from ..session_runtime import async_complete_conversation_commit, session_runtime_manager


def _identifier(value) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 128 and value == value.strip()


def _context(payload):
    context = payload.get("conversation_context") or {}
    if (not isinstance(context, dict) or set(context) - {
        "session_id", "selected_entry", "selected_moment", "thread_id", "result_set_id"
    } or (context.get("selected_entry") and context.get("selected_moment"))):
        raise SessionConversationError("invalid_conversation_context", 400)
    for key in ("session_id", "thread_id", "result_set_id"):
        if context.get(key) is not None and context.get(key) != "" and not _identifier(context[key]):
            raise SessionConversationError("invalid_conversation_context", 400)
    for key, identifier in (("selected_entry", "entry_id"), ("selected_moment", "moment_id")):
        target = context.get(key)
        if target is not None and (not isinstance(target, dict) or set(target) != {"session_id", identifier}
                                   or not all(_identifier(target[k]) for k in ("session_id", identifier))):
            raise SessionConversationError("invalid_conversation_context", 400)
    return context


async def _live_reference(manager, profile, target):
    active = await manager.async_get_active(profile)
    if active is None or active.session_id != target["session_id"]:
        raise SessionConversationError("session_context_changed")
    # Only semantically published Moments in the immutable engine, never a proposal.
    moment = next((m for m in active.broadcast.state.dj_moments if m.moment_id == target["moment_id"]), None)
    if moment is None or moment.moment_type.value == "silence":
        raise SessionConversationError("moment_context_unavailable", 404)
    source = moment.source_fact
    metadata = dict(moment.generation_metadata)
    from ..public_artist_narration import ResearchMomentAcceptance, admitted, BASIS, sources_for
    if type(moment.narration_acceptance) is ResearchMomentAcceptance:
        if not admitted(moment):
            raise SessionConversationError("moment_context_unqualified", 403)
        return {"text":moment.content,"moment_type":moment.moment_type.value,"archive_basis":BASIS,
            "source_attribution":dict(moment.source_attribution),"sources":sources_for(moment),
            **moment.narration_acceptance.accepted.qualified_fact()}
    if (source is None and not moment.source_attribution and moment.source_references == ("session_direction",)
        and moment.moment_type.value == "session" and metadata.get("context_source") == "session_direction"
        and metadata.get("validated") == "true"):
        return {"text": moment.content, "archive_basis": "runtime_authored_direction_v1", "source_attribution": {}}
    from ..session_facts import QualifiedSessionFact
    if (not isinstance(source, QualifiedSessionFact) or not source.eligible(source.media_identity, time.monotonic())
        or source.provider not in {"MusicBrainz", "Wikidata"} or source.license != "CC0-1.0"
        or dict(moment.source_attribution) != {"provider": source.provider, "url": source.source_url, "license": source.license}):
        raise SessionConversationError("moment_context_unqualified", 403)
    from .dialogue import normalized_subjects
    return {"text": moment.content, "moment_type": moment.moment_type.value, "archive_basis": "cc0_normalized_fields_v1",
            "source_attribution": dict(moment.source_attribution),
            "qualified_fact_text": source.copy_for(active.locale)[1],
            "dialogue_subjects": normalized_subjects(source)}


async def async_exchange(hass, runtime, payload, *, profile_id, history_manager, delegate,
                         validate_owner, persist_history=True, profile=None, validate_immediate=None):
    """Reserve a bounded turn, execute without broad locks, commit through existing owners."""
    client_id = payload.get("client_message_id")
    if not _identifier(client_id):
        raise SessionConversationError("client_message_id_required", 400)
    speech_version = payload.get("speech_contract_version")
    if speech_version is not None and (type(speech_version) is not int or speech_version not in (1, 2, 3)):
        raise SessionConversationError("unsupported_speech_contract", 400)
    context = _context(payload)
    text = str(payload.get("text") or payload.get("message") or "").strip()
    if not text or len(text) > 4000:
        raise SessionConversationError("invalid_conversation_text", 400)
    from . import classify_ask_dj
    intent = classify_ask_dj(text)
    fast = intent.category == "action"
    explicit_action = intent.category in {"action", "hybrid"} and intent.action not in {None, "none", "announce"}
    digest = hashlib.sha256(json.dumps({"context": context, "text": text,
        "choice_action": payload.get("choice_action"), "command_action": payload.get("_command_action"),
        "track_insight_target":payload.get("track_insight_target"),
        "options":{k:payload.get(k) for k in ("language","locale","mood","dj_persona","audio_response","privacy_mode","speech_contract_version")}}, sort_keys=True).encode()).hexdigest()
    scope, thread = "profile:" + profile_id, context.get("thread_id") or "default"
    history_manager.register_session_request(scope, client_id)
    token = None
    turn = None
    future = None
    reserved = False
    try:
        await history_manager.async_load()
        await validate_owner()
        from ..persona_reactions import withdraw_for_interaction
        withdraw_for_interaction(hass, profile_id)
        scope_revision = await history_manager.async_scope_revision(scope)
        if await history_manager.async_session_request_cleared(scope, client_id):
            raise SessionConversationError("conversation_history_changed")
        grant = await async_history_grant_revision(hass, profile_id)
        manager = session_runtime_manager(hass)
        def query():
            return query_service(hass, history_manager)
        active = await manager.async_get_active(profile_id)
        shared_settings = None
        settings_token = None
        if manager._settings_repository is not None:
            from ..domain.profile.dj_settings import DJSettings
            def settings_read_authority():
                if validate_immediate is not None:
                    validate_immediate()
                return True
            snapshot = await manager.async_read_dj_settings(owner_profile_id=profile_id,
                authorize=settings_read_authority)
            active = manager.current_active(profile_id)
            if snapshot['activated'] or (active is not None and active.settings_contract_version >= 2):
                shared_settings = DJSettings.from_dict(snapshot['defaults'])
                settings_token = manager.dj_settings_fence_token(profile_id)
        # Style is captured once, including general-screen turns enriched by an
        # active Session. Never relabel or accept old prose after a live CAS.
        style_session = active.session_id if active else ""
        style_revision = active.persona_revision if active else None
        def validate_persona():
            if settings_token is not None and manager.dj_settings_fence_token(profile_id) != settings_token:
                raise SessionConversationError('conversation_context_changed')
            if style_session:
                current = manager.current_active(profile_id)
                if (current is None or current.session_id != style_session
                    or current.persona_revision != style_revision):
                    raise SessionConversationError("conversation_context_changed")

        session_id = context.get("session_id") or ""
        if session_id and (active is None or active.session_id != session_id):
            raise SessionConversationError("session_context_changed")
        if session_id:
            stored = await query()._repository.async_session_record(session_id)
            if stored is None or not stored["history_enabled"]:
                persist_history = False
        target, live = context.get("selected_entry"), context.get("selected_moment")
        # Explicit subjects come from the current question. A stale chip cannot block them.
        from .public_research import explicit_public_subject, safe_subject
        new_subject = explicit_public_subject(text)
        from .dialogue import requests_lookup, is_refinement
        independent_search = requests_lookup(text) and not is_refinement(text) and not references_topic(text)
        selected_preview = None
        references_selected_subject = False
        if new_subject and (target or live):
            try:
                selected_preview = ((await query().async_open_source_entry(profile_id, target["session_id"], target["entry_id"]))["entry"]
                    if target else await _live_reference(manager, profile_id, live))
            except (PermissionError, SessionConversationError):
                # An independent explicit topic must not be held hostage by an expired chip.
                selected_preview = None
            from .public_research import resolve_partial_name
            _, references_selected_subject, ambiguous_selected_subject = resolve_partial_name(
                new_subject, model_source(selected_preview).get("subjects", []))
            references_selected_subject = references_selected_subject or ambiguous_selected_subject
        if (new_subject and not safe_subject(new_subject) and not references_selected_subject
                and selected_preview is not None):
            # A broad question grammar can capture a clause instead of a name.
            # It is not an independent public topic or authority to drop a chip.
            new_subject = None
        detached = bool((target or live) and not references_selected_subject
                        and (new_subject or (not references_topic(text) and intent.intent != "ask_music_info"))
                        and not explicit_quote(text))
        reset_topic = (detached or bool(new_subject and not references_selected_subject) or independent_search
                       or payload.get("_setting_feedback") is True)
        if detached:
            target = live = None
            context = {k: v for k, v in context.items() if k not in {"selected_entry", "selected_moment"}}
        if context.get("selected_moment"):
            persist_history = False
        # Body archiveability is per turn. A live reference and its next question
        # share the same operational rights epoch, even without another chip.
        frame = history_manager.dialogue.frame(scope, thread,
            scope_revision + ":" + grant + ":" + hashlib.sha256(json.dumps(source_scope(profile)).encode()).hexdigest()
            + ":" + str(payload.get("privacy_mode") or "default"))
        future, reserved = history_manager.dialogue.reserve(frame, client_id, digest, fast)
        if not reserved:
            accepted, admission = await asyncio.shield(future)
            result = deepcopy(accepted)
            if "session_speech" in result:
                result["session_speech"]["autoplay_eligible"] = False
            # The original caller's fence does not authorize another joined
            # transport whose pairing/entry may have been withdrawn meanwhile.
            await admission(owner=validate_owner, immediate=validate_immediate)
            from ..transport_delivery import register_delivery_admission
            register_delivery_admission(lambda: admission(owner=validate_owner, immediate=validate_immediate))
            return result
        if intent.intent in {"current_artist_information", "current_release_information", "album_tracks_information"}:
            # Even a subsequently rejected read is not consent to retry older music.
            frame.retry = None
        selected = selected_preview if references_selected_subject else None
        if selected is None:
            selected = (await query().async_open_source_entry(profile_id, target["session_id"], target["entry_id"]))["entry"] if target else None
            if live:
                selected = await _live_reference(manager, profile_id, live)
        dependencies = [target] if target else []
        # A previous subject is used only while its source and Session are still valid.
        for dependency in ([] if reset_topic else frame.dependencies):
            try:
                if "moment_id" in dependency:
                    await _live_reference(manager, profile_id, dependency)
                else:
                    await query().async_open_source_entry(profile_id, dependency["session_id"], dependency["entry_id"])
            except (PermissionError, SessionConversationError):
                frame.reset("expired-context:" + client_id)
                break
        if not reset_topic:
            dependencies.extend(d for d in deepcopy(frame.dependencies) if d not in dependencies)
        if live:
            dependencies.append(live)
        captured = active.broadcast.state.playback.item_id if active else ""
        # Only genuinely current-playback questions bind to a playback item.
        track_bound = not target and not live and (intent.intent in {"current_track_reference", "current_artist_information", "current_release_information", "album_tracks_information", "track_insight", "dj_announcement"}
            or (references_topic(text) and not frame.messages and not frame.subjects and not frame.result_set))
        playback_fence_session = session_id or (
            active.session_id if active and track_bound and intent.intent in {"current_artist_information", "current_release_information", "album_tracks_information"} else ""
        )
        implicit = None
        if session_id:
            if track_bound and captured:
                anchor = await query()._repository.async_current_playback_entry(profile_id, session_id, captured)
                if anchor:
                    try:
                        await query().async_open_source_entry(profile_id, session_id, anchor)
                    except PermissionError:
                        persist_history = False
                    else:
                        implicit = {"session_id": session_id, "entry_id": anchor}
                        dependencies.append(implicit)
                else:
                    persist_history = False
        if live or any("moment_id" in d for d in dependencies):
            # A live-only grant does not authorize copying its body into a durable archive.
            persist_history = False
        # RAM-only material cannot gain archival rights by changing endpoint.
        # An explicit independent topic can open a new archiveable subject.
        if not reset_topic and not frame.archiveable:
            persist_history = False
        payload = {**payload, "private_session": not persist_history}
        generation = frame.generation

        async def guard(*, check_runtime=True, owner=validate_owner, immediate=validate_immediate):
            await owner()
            if await history_manager.async_scope_revision(scope) != scope_revision:
                raise SessionConversationError("conversation_history_changed")
            if await async_history_grant_revision(hass, profile_id) != grant:
                frame.reset("rights_changed")
                raise SessionConversationError("conversation_context_changed")
            if check_runtime:
                current = await manager.async_get_active(profile_id)
                if playback_fence_session and (current is None or current.session_id != playback_fence_session
                    or (track_bound and not explicit_action and current.broadcast.state.playback.item_id != captured)):
                    raise SessionConversationError("session_context_changed")
            for dependency in dependencies:
                if "moment_id" in dependency:
                    await _live_reference(manager, profile_id, dependency)
                else:
                    await query().async_open_source_entry(profile_id, dependency["session_id"], dependency["entry_id"])
            # Nothing may yield after this final committed-state/paired-owner fence.
            if history_manager.scope_revision(scope) != scope_revision:
                raise SessionConversationError("conversation_history_changed")
            if history_grant_revision(hass, profile_id) != grant:
                raise SessionConversationError("conversation_context_changed")
            if playback_fence_session:
                current = manager.current_active(profile_id)
                if current is None or current.session_id != playback_fence_session or (
                    track_bound and not explicit_action and current.broadcast.state.playback.item_id != captured):
                    raise SessionConversationError("session_context_changed")
            validate_persona()
            if frame.generation != generation:
                raise SessionConversationError("conversation_context_changed")
            if immediate is not None:
                immediate()

        turn = DialogueTurn(frame, scope, thread, client_id, digest, generation, guard, history_manager,
                            style=style_projection(payload, active, profile, settings=shared_settings), session_id=session_id,
                            captured_playback_item_id=captured if track_bound and intent.intent in {"current_artist_information", "current_release_information", "album_tracks_information"} else "",
                            source_context=model_source(selected), selected_read_context=selected,
                            dependencies=dependencies, fast_control=fast, reset_topic=reset_topic,
                            archiveable=persist_history)
        accepted_offer = None
        async def joined_admission(*, owner, immediate):
            await guard(owner=owner, immediate=immediate)
            # Local read/effect adapters can add narrower Session, item or
            # output fences even without an explicit conversation_context.
            for validate in turn.delivery_validators:
                validate()
            if accepted_offer is not None:
                if history_manager.dialogue.clock() >= accepted_offer["deadline"]:
                    raise DialogueError("choice_expired")
                if frame.result_set is not accepted_offer:
                    raise DialogueError("choice_changed")

        from ..transport_delivery import register_delivery_admission
        register_delivery_admission(lambda: joined_admission(owner=validate_owner, immediate=validate_immediate))

        turn.effect_grants = request_effect_grants(text, intent)
        token = current_turn.set(turn)
        saved = await history_manager.async_saved_exchange(scope, client_id) if persist_history else None
        if saved:
            if not await query().async_conversation_source_visible(profile_id,saved["assistant_message"]):
                raise SessionConversationError("conversation_source_withdrawn",409)
            old = saved["user_message"].get("session_turn", {})
            if old.get("request_digest") != digest:
                raise SessionConversationError("client_message_conflict")
            for dep in saved["assistant_message"].get("historical_entry_references", []):
                await query().async_open_source_entry(profile_id, dep["session_id"], dep["entry_id"])
            result = {**saved["assistant_message"], "success": True,
                      "dj_text": saved["assistant_message"]["text"], "deduplicated": True}
        else:
            artist = history_question(text)
            playback = await query().async_find_playback(profile_id, artist=artist) if artist else None
            result = await delegate(payload, scope, selected, playback)
            await turn.guard()
            if turn.explicit_research_subject:
                context = {k:v for k,v in context.items() if k not in {"selected_entry","selected_moment"}}
            if result.pop("_private_current_context", False):
                # Live mutable intent and unqualified catalog retention are not
                # promoted into the permanent conversation/Session archive.
                persist_history = False
                turn.archiveable = False
                # Display-only selected catalog credits keep the existing bounded
                # choice/deadline for a later explicit action, without model or
                # archival rights. Current playback/Forecast still reset topic.
                turn.reset_topic = turn.reset_topic or result.get("text_source") != "qualified_catalog_result"
            if not result.get("success"):
                frame.retry = {"text": text, "uncertain": turn.effect_started}
                future.set_result((deepcopy(result), joined_admission))
                return result
        turn_record = {"turn_id": "turn-" + uuid5(NAMESPACE_URL, scope + ":" + client_id).hex,
                       "request_digest": digest, "profile_id": profile_id, "context": context,
                       "effective_style": {**turn.style, "persona_revision": style_revision},
                       "captured_playback_item_id": captured if track_bound else "",
                       "input_type": "setting_feedback" if payload.get("_setting_feedback") is True else "voice" if payload.get("input_type") == "voice" else "text",
                       "explicit_playback_request": explicit_action,
                       "implicit_playback_entry": implicit,
                       "dependency_entries": [d for d in dependencies if "entry_id" in d]}
        if turn.provider_display_source is not None:
            turn_record["provider_display_source"] = deepcopy(turn.provider_display_source)
        ids = []
        if persist_history:
            new = saved is None
            async def persistence_guard():
                # SessionRuntimeManager owns its short lock here; never reacquire it.
                await guard(check_runtime=not (bool(style_session) or settings_token is not None))

            async def finish():
                nonlocal saved
                if saved is None:
                    archival_result = result
                    catalogue_caption = result.get("_catalogue_history_caption")
                    if (result.get("text_source") == "qualified_catalog_result"
                            and isinstance(catalogue_caption, str)):
                        # Keep the existing count/query archive. Actual catalog
                        # labels remain current-response display data only.
                        archival_result = {**result, "text": catalogue_caption, "dj_text": catalogue_caption}
                    saved = await history_manager.async_append_exchange(scope, payload, archival_result,
                        session_turn=turn_record, commit_guard=persistence_guard)
                entries = []
                try:
                    if session_id:
                        entries = await query()._repository.async_append_entries(profile_id, session_id, [
                            {"kind": kind, "reference_id": turn_record["turn_id"] + ":" + role,
                             "body": {"turn_id": turn_record["turn_id"], "message_id": saved[role]["id"], "history_scope": scope},
                             "occurred_at": saved[role]["created_at"]}
                            for kind, role in (("conversation_user", "user_message"), ("conversation_dj", "assistant_message"))])
                    await validate_owner()
                    expected = str(saved.get("history_trimmed_count", 0))+":"+str(saved.get("clear_revision", 0)) if new else scope_revision
                    if await history_manager.async_scope_revision(scope) != expected:
                        raise SessionConversationError("conversation_history_changed")
                    for dependency in saved["assistant_message"].get("historical_entry_references", []):
                        await query().async_open_source_entry(profile_id, dependency["session_id"], dependency["entry_id"])
                    # All authority/storage/source awaits precede this synchronous acceptance fence.
                    if history_manager.scope_revision(scope) != expected or history_grant_revision(hass, profile_id) != grant:
                        raise SessionConversationError("conversation_context_changed")
                    if session_id:
                        current = manager.current_active(profile_id)
                        if current is None or current.session_id != session_id or (
                            track_bound and not explicit_action and current.broadcast.state.playback.item_id != captured):
                            raise SessionConversationError("session_context_changed")
                    validate_persona()
                    if validate_immediate is not None:
                        validate_immediate()
                except Exception:
                    if entries:
                        await query()._repository.async_remove_entry_records(profile_id, entries)
                    if new:
                        await history_manager.async_discard_session_exchange(scope, client_id, turn_record["turn_id"])
                    raise
                return entries
            if style_session or settings_token is not None:
                ids = await manager.async_accept_conversation(owner_profile_id=profile_id, session_id=style_session,
                    playback_item_id=captured, track_bound=track_bound and not explicit_action,
                    persona_revision=style_revision, settings_token=settings_token, commit=finish)
            else:
                ids = await async_complete_conversation_commit(finish)
        if not saved or not result.get("deduplicated"):
            result["_dialogue_question"] = text
            history_manager.dialogue.complete(turn, result)
            if result.get("result_set", {}).get("result_set_id"):
                accepted_offer = frame.result_set
            if explicit_action and (not result.get("success") or result.get("error")):
                # Chat delivery can succeed while the requested playback failed.
                # Only a proven pre-dispatch failure is safe for an explicit retry.
                frame.retry = {"text":text,"uncertain":turn.effect_started}
            result.pop("_dialogue_question", None)
            result.pop("_consume_pending", None)
        catalogue_caption = result.pop("_catalogue_history_caption", None)
        if saved and not result.get("deduplicated"):
            # Preserve the existing live bubble contract without turning transient
            # artwork/audio/actions into an archival retention grant.
            live_values={**(result.get("assistant_message") or {}),**result}
            live_message = {**saved["assistant_message"], **{key:deepcopy(live_values[key]) for key in (
                "images", "links", "sources", "audio_url", "playback_actions", "confirmation_actions", "items",
                "track_insight", "open_screen", "navigation_actions", "origin", "text_source", "is_generated_text",
                "type", "action_outcome") if key in live_values}}
            if catalogue_caption is not None and result.get("text_source") == "qualified_catalog_result":
                live_message["text"] = result["text"]
            saved = {**saved, "assistant_message":live_message,
                     "messages":[saved["user_message"],live_message], "media_delivery_basis":"current_response_only"}
        response = {**result, **(saved or {"history_persisted": False}), "user_id": None,
            "owner_profile_id": profile_id, "client_message_id": client_id,
            "conversation": {"schema_version": 1, "turn_id": turn_record["turn_id"], "thread_id": thread,
                "context": context, "entry_ids": ids, "history_scope": "profile" if persist_history else "private_ephemeral",
                "input_type": turn_record["input_type"],
                "style": (saved["assistant_message"].get("session_turn", {}).get("effective_style")
                          if saved and result.get("deduplicated") else turn_record["effective_style"]),
                "style_basis": "accepted_turn" if not result.get("deduplicated") or (saved and saved["assistant_message"].get("session_turn", {}).get("effective_style")) else "legacy_unknown",
                "model_source_basis": turn.source_context.get("basis"),
                "metrics": {"agent_calls": turn.agent_calls, "lookup_calls": turn.lookup_calls, "prompt_bytes": turn.prompt_bytes}}}
        from ..session_speech import remember
        from . import _should_generate_audio_response
        requested_audio = _should_generate_audio_response(payload, intent)
        # Old AVPlayer clients only understand a headerless GET audio_url.
        # An accepted private reference cannot be downgraded to that grant.
        # Negotiate the new adapter explicitly; text/semantic acceptance stays
        # the same and upgrade is never an invitation to resend the question.
        required_speech_version = 3 if shared_settings is not None else 1
        speech_negotiated = speech_version in (1, 2, 3) and speech_version >= required_speech_version
        speech_output = (active.selected_announcement_output if active is not None
                         else shared_settings.announcement_output if shared_settings is not None else 'client_device')
        response["audio_delivery"] = ({"mode": "accepted_reference", "state": "deferred"}
            if speech_negotiated else {"mode": "accepted_reference",
                "state": "unavailable" if requested_audio else "not_requested",
                "reason": "client_protocol_upgrade_required" if requested_audio else None,
                "required_speech_contract_version": required_speech_version})
        response["session_speech"] = remember(history_manager.dialogue, turn, result,
            turn_id=turn_record["turn_id"], session_id=style_session,
            persona_revision=style_revision, scope_revision=history_manager.scope_revision(scope),
            grant_revision=grant, profile_source=source_scope(profile),
            playback_item_id=captured if track_bound and not explicit_action else "",
            deduplicated=bool(result.get("deduplicated")),
            autoplay_eligible=speech_negotiated and requested_audio,
            announcement_output=speech_output)
        if speech_output == 'text_only':
            response['audio_delivery'] = {'mode': 'accepted_reference', 'state': 'not_applicable',
                                          'reason': 'announcement_text_only'}
        if isinstance(response.get("assistant_message"), dict):
            live_assistant = {**response["assistant_message"], "session_speech": response["session_speech"],
                              "audio_delivery": response["audio_delivery"]}
            response["assistant_message"] = live_assistant
            if isinstance(response.get("messages"), list):
                response["messages"] = [live_assistant if message.get("id") == live_assistant.get("id") else message
                                        for message in response["messages"]]
        # RAM-only admission travels with this bounded in-flight future. Each
        # waiter rechecks the original evidence with its own caller authority.
        future.set_result((deepcopy(response), joined_admission))
        history_manager.dialogue.remember_catalogue_read(turn, response, future)
        return response
    except (SessionConversationError, DialogueError) as exc:
        if turn is not None and turn.effect_started and frame.generation == turn.generation:
            frame.retry = {"text":text,"uncertain":True}
        if reserved and future and not future.done():
            future.set_exception(exc)
            future.exception()  # observed by the owner too, without unhandled-future noise
        raise SessionConversationError(exc.code, exc.status) from exc
    except BaseException as exc:
        if turn is not None and turn.effect_started and frame.generation == turn.generation:
            frame.retry = {"text": text, "uncertain": True}
        if reserved and future and not future.done():
            future.set_exception(exc)
            future.exception()
        raise
    finally:
        if token is not None:
            current_turn.reset(token)
        if reserved:
            frame.inflight.pop(client_id, None)
        history_manager.unregister_session_request(scope, client_id)
