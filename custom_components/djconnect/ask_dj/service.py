"""The shared Ask DJ application boundary; Session is optional context."""
from __future__ import annotations

import asyncio
import hashlib
import json
from functools import wraps
from uuid import NAMESPACE_URL, uuid5

from ..session_conversation import SessionConversationError, history_question, query_service
from ..session_runtime import async_complete_conversation_commit, session_runtime_manager

def _pending_session_request(method):
    @wraps(method)
    async def pending(hass, runtime, payload, **kwargs):
        identifier = payload.get("client_message_id")
        if not isinstance(identifier, str) or not identifier or len(identifier) > 128:
            return await method(hass, runtime, payload, **kwargs)
        scope = "profile:" + kwargs["profile_id"]
        history = kwargs["history_manager"]
        history.register_session_request(scope, identifier)
        try:
            return await method(hass, runtime, payload, **kwargs)
        finally:
            history.unregister_session_request(scope, identifier)

    return pending


@_pending_session_request
async def async_exchange(
    hass,
    runtime,
    payload,
    *,
    profile_id,
    history_manager,
    delegate,
    validate_owner,
    persist_history=True,
):
    """One scoped invocation of existing Ask DJ, with retained-reference projection."""
    client_id = payload.get("client_message_id")
    if (
        not isinstance(client_id, str)
        or not client_id.strip()
        or len(client_id) > 128
        or client_id != client_id.strip()
    ):
        raise SessionConversationError("client_message_id_required", 400)
    context = payload.get("conversation_context") or {}
    if not isinstance(context, dict) or set(context) - {"session_id", "selected_entry"}:
        raise SessionConversationError("invalid_conversation_context", 400)
    session_id = context.get("session_id") or ""
    if not isinstance(session_id, str) or len(session_id) > 128:
        raise SessionConversationError("invalid_conversation_context", 400)
    history_scope = "profile:" + profile_id
    query = query_service(hass, history_manager)
    manager = session_runtime_manager(hass)
    locks = hass.data.setdefault("djconnect", {}).setdefault("session_conversation_locks", {})
    lock = locks.setdefault(profile_id, asyncio.Lock())
    text = str(payload.get("text") or payload.get("message") or "").strip()
    from . import classify_ask_dj

    request_intent = classify_ask_dj(text)
    explicit_playback_request = (
        request_intent.category in {"action", "hybrid"}
        and request_intent.action not in {None, "none", "announce"}
    ) or request_intent.action == "retry"
    track_changed_by_request = False
    if not text or len(text) > 4000:
        raise SessionConversationError("invalid_conversation_text", 400)
    digest = hashlib.sha256(
        json.dumps({"context": context, "text": text}, sort_keys=True).encode()
    ).hexdigest()
    async with lock:
        scope_revision = await history_manager.async_scope_revision(history_scope)
        if await history_manager.async_session_request_cleared(history_scope, client_id):
            raise SessionConversationError("conversation_history_changed")
        selected = None
        target = context.get("selected_entry")
        if target is not None:
            if not isinstance(target, dict) or set(target) != {"session_id", "entry_id"}:
                raise SessionConversationError("invalid_conversation_context", 400)
            if any(
                not isinstance(target[key], str)
                or not target[key]
                or len(target[key]) > 128
                or target[key] != target[key].strip()
                for key in ("session_id", "entry_id")
            ):
                raise SessionConversationError("invalid_conversation_context", 400)
            selected = await query.async_open_entry(
                profile_id, target["session_id"], target["entry_id"]
            )
        active = await manager.async_get_active(profile_id)
        if session_id and (active is None or active.session_id != session_id):
            raise SessionConversationError("session_context_changed")
        captured_playback = active.broadcast.state.playback.item_id if active else ""
        implicit_dependency = None
        if session_id:
            stored_session = await query._repository.async_session_record(session_id)
            if stored_session is None or not stored_session["history_enabled"]:
                persist_history = False
            if target is None and captured_playback and history_question(text) is None:
                anchor = await query._repository.async_current_playback_entry(
                    profile_id, session_id, captured_playback
                )
                if anchor:
                    try:
                        await query.async_open_entry(profile_id, session_id, anchor)
                    except PermissionError:
                        persist_history = False
                    else:
                        implicit_dependency = {"session_id": session_id, "entry_id": anchor}
                else:
                    persist_history = False
        if not persist_history:
            payload = {**payload, "private_session": True}
        saved = (
            await history_manager.async_saved_exchange(history_scope, client_id)
            if persist_history
            else None
        )
        if saved:
            await validate_owner()
            for dependency in saved["assistant_message"].get("historical_entry_references", []):
                await query.async_open_entry(
                    profile_id, dependency["session_id"], dependency["entry_id"]
                )
            turn = saved["user_message"].get("session_turn", {})
            track_changed_by_request = bool(turn.get("explicit_playback_request"))
            if turn.get("request_digest") != digest:
                raise SessionConversationError("client_message_conflict")
            if (
                session_id
                and target is None
                and not track_changed_by_request
                and turn.get("captured_playback_item_id") != captured_playback
            ):
                raise SessionConversationError("session_context_changed")
            result = {
                **saved["assistant_message"],
                "success": True,
                "dj_text": saved["assistant_message"]["text"],
                "deduplicated": True,
            }
        else:
            turn = {
                "turn_id": "turn-" + uuid5(NAMESPACE_URL, history_scope + ":" + client_id).hex,
                "request_digest": digest,
                "profile_id": profile_id,
                "context": context,
                "captured_playback_item_id": captured_playback,
                "input_type": "voice" if payload.get("input_type") == "voice" else "text",
                "explicit_playback_request": explicit_playback_request,
                "implicit_playback_entry": implicit_dependency,
            }
            artist = history_question(text)
            playback_result = (
                await query.async_find_playback(profile_id, artist=artist)
                if artist is not None
                else None
            )
            result = await delegate(
                payload, history_scope, selected["entry"] if selected else None, playback_result
            )
            if not result.get("success"):
                return result
            track_changed_by_request = explicit_playback_request
            await validate_owner()
            current = await manager.async_get_active(profile_id)
            if session_id and (
                current is None
                or current.session_id != session_id
                or (
                    target is None
                    and not track_changed_by_request
                    and current.broadcast.state.playback.item_id != captured_playback
                )
            ):
                raise SessionConversationError("session_context_changed")
            if target is not None:
                await query.async_open_entry(profile_id, target["session_id"], target["entry_id"])
            if not persist_history:
                return {
                    **result,
                    "history_persisted": False,
                    "conversation": {
                        "schema_version": 1,
                        "turn_id": turn["turn_id"],
                        "context": context,
                        "entry_ids": [],
                        "history_scope": "private_ephemeral",
                        "input_type": turn["input_type"],
                    },
                }

            async def commit_guard():
                await validate_owner()
                if await history_manager.async_scope_revision(history_scope) != scope_revision:
                    raise SessionConversationError("conversation_history_changed")
                if target is not None:
                    await query.async_open_entry(
                        profile_id, target["session_id"], target["entry_id"]
                    )
                if implicit_dependency is not None:
                    await query.async_open_entry(
                        profile_id,
                        implicit_dependency["session_id"],
                        implicit_dependency["entry_id"],
                    )
                for dependency in result.get("historical_matches", []):
                    await query.async_open_entry(
                        profile_id, dependency["session_id"], dependency["entry_id"]
                    )

        new_exchange = saved is None

        async def finish():
            nonlocal saved
            if saved is None:
                saved = await history_manager.async_append_exchange(
                    history_scope, payload, result, session_turn=turn, commit_guard=commit_guard
                )
            ids = []
            try:
                if session_id:
                    ids = await query._repository.async_append_entries(
                        profile_id,
                        session_id,
                        [
                            {
                                "kind": kind,
                                "reference_id": turn["turn_id"] + ":" + role,
                                "body": {
                                    "turn_id": turn["turn_id"],
                                    "message_id": saved[role]["id"],
                                    "history_scope": history_scope,
                                },
                                "occurred_at": saved[role]["created_at"],
                            }
                            for kind, role in [
                                ("conversation_user", "user_message"),
                                ("conversation_dj", "assistant_message"),
                            ]
                        ],
                    )
                await validate_owner()
                expected_revision = (
                    str(saved.get("history_trimmed_count", 0))
                    + ":"
                    + str(saved.get("clear_revision", 0))
                    if new_exchange
                    else scope_revision
                )
                if await history_manager.async_scope_revision(history_scope) != expected_revision:
                    raise SessionConversationError("conversation_history_changed")
                for dependency in saved["assistant_message"].get("historical_entry_references", []):
                    await query.async_open_entry(
                        profile_id, dependency["session_id"], dependency["entry_id"]
                    )
            except Exception:
                await query._repository.async_remove_entry_records(profile_id, ids)
                if new_exchange:
                    await history_manager.async_discard_session_exchange(
                        history_scope, client_id, turn["turn_id"]
                    )
                raise
            return ids

        if session_id:
            ids = await manager.async_accept_conversation(
                owner_profile_id=profile_id,
                session_id=session_id,
                playback_item_id=captured_playback,
                track_bound=target is None and not track_changed_by_request,
                commit=finish,
            )
        else:
            # Standalone turns have no Runtime to lock, but retain the same Store guard.
            ids = await async_complete_conversation_commit(finish)
        return {
            **result,
            **saved,
            "user_id": None,
            "owner_profile_id": profile_id,
            "conversation": {
                "schema_version": 1,
                "turn_id": turn["turn_id"],
                "context": context,
                "entry_ids": ids,
                "history_scope": "profile",
                "input_type": turn["input_type"],
            },
        }
