"""Persistent cross-device Ask DJ history."""
from __future__ import annotations

import asyncio
import hashlib
from collections import Counter
from copy import copy, deepcopy
from functools import wraps
from datetime import datetime, timedelta, timezone
import uuid
import re
from typing import Any

from .const import CONF_CLIENT_TYPE, CONF_DEVICE_ID, CONF_DEVICE_NAME

STORE_KEY = "djconnect_ask_dj_history"
STORE_VERSION = 1
MAX_MESSAGES_PER_USER = 1000
MAX_TEXT_LENGTH = 4000
MAX_ITEMS = 20
RETENTION_MESSAGE_COOLDOWN = timedelta(hours=1)
RETENTION_MESSAGE_TEXT = (
    "Ask DJ heeft de limiet van 1000 berichten bereikt. Oudste berichten worden verwijderd."
)


def _committed_mutation(method):
    """Expose mutations only after Store acknowledgement; serialize all writers."""

    @wraps(method)
    async def commit(self, *args, **kwargs):
        await self.async_load()
        async with self._write_lock:
            self._require_settled_erasure()
            staged = copy(self)
            staged._data = deepcopy(self._data)
            staged._committed_store_write = False
            task = asyncio.create_task(method(staged, *args, **kwargs))
            try:
                result = await asyncio.shield(task)
            except asyncio.CancelledError:
                # Resolve the in-flight save before allowing a subsequent writer.
                # Successful persisted data remains authoritative even if the caller left.
                try:
                    await _settle_store_writer(task)
                except Exception:
                    if staged._committed_store_write and self._store is not None:
                        await _settle_store_writer(asyncio.create_task(
                            self._store.async_save(_compact_store_data(self._data))))
                else:
                    self._data = staged._data
                raise
            except Exception:
                if staged._committed_store_write and self._store is not None:
                    await _settle_store_writer(asyncio.create_task(
                        self._store.async_save(_compact_store_data(self._data))))
                raise
            self._data = staged._data
            return result

    return commit


def validate_archive_erasure_plan(plan):
    """Only bounded opaque IDs/hashes may survive in cross-store recovery scope."""
    keys = {'remove_message_ids', 'redact_message_ids', 'dependent_session_ids', 'retry_hashes'}
    if not isinstance(plan, dict) or set(plan) != keys:
        raise ValueError('invalid_history_delete_request')
    for key, values in plan.items():
        if (type(values) is not list or len(values) > MAX_MESSAGES_PER_USER
                or any(not isinstance(v, str) or not 0 < len(v) <= 200 for v in values)
                or len(set(values)) != len(values)):
            raise ValueError('invalid_history_delete_request')
        if key == 'retry_hashes' and any(not re.fullmatch('[0-9a-f]{64}', v) for v in values):
            raise ValueError('invalid_history_delete_request')
    if set(plan['remove_message_ids']) & set(plan['redact_message_ids']):
        raise ValueError('invalid_history_delete_request')


def archive_erasure_plan(profile_id, messages, session_ids, *, message_ids=frozenset(),
                         entry_index=None, pending_client_ids=()):
    """Derive a bounded identifier-only cascade, without copying private bodies.

    Direct target exchanges disappear. Retained exchanges with a deleted source
    retain stable identities as unavailable. Propagate that unavailable basis
    through actual SQL entry references; cycles reach a bounded fixed point.
    """
    entry_index = entry_index or {}
    if (not isinstance(profile_id, str) or not profile_id
            or type(session_ids) is not frozenset or not session_ids
            or any(not isinstance(s, str) or not s for s in session_ids)
            or len(messages) > MAX_MESSAGES_PER_USER):
        raise ValueError('invalid_history_delete_request')
    exchanges = {}
    for message in messages:
        identifier = message.get('id')
        if not isinstance(identifier, str) or not identifier:
            raise ValueError('history_delete_outcome_unknown')
        exchange = message.get('exchange_id') or identifier
        exchanges.setdefault(exchange, []).append(message)
    removed = {
        exchange for exchange, values in exchanges.items()
        if any(m['id'] in message_ids
               or m.get('session_turn', {}).get('context', {}).get('session_id') in session_ids
               for m in values)
    }
    unavailable = set(removed)
    tainted_entries = set()
    for exchange in unavailable:
        for message in exchanges[exchange]:
            if message['id'] in entry_index:
                tainted_entries.add(tuple(entry_index[message['id']]))
    while True:
        discovered = {
            exchange for exchange, values in exchanges.items() if exchange not in unavailable
            and any(ref.get('session_id') in session_ids
                    or (ref.get('session_id'), ref.get('entry_id')) in tainted_entries
                    for m in values for ref in m.get('historical_entry_references', []))
        }
        if not discovered:
            break
        unavailable.update(discovered)
        for exchange in discovered:
            for message in exchanges[exchange]:
                if message['id'] in entry_index:
                    tainted_entries.add(tuple(entry_index[message['id']]))
    direct = [m for e in removed for m in exchanges[e]]
    dependent = [m for e in unavailable - removed for m in exchanges[e]]
    affected_sessions = {
        m.get('session_turn', {}).get('context', {}).get('session_id') for m in dependent
    } | {entry_index[m['id']][0] for m in dependent if m['id'] in entry_index}
    retry_hashes = {
        _request_hash('profile:' + profile_id, identifier)
        for identifier in (*pending_client_ids,
                           *(m.get('client_message_id') for m in direct + dependent))
        if isinstance(identifier, str) and identifier
    }
    result = {
        'remove_message_ids': sorted(m['id'] for m in direct),
        'redact_message_ids': sorted(m['id'] for m in dependent),
        'dependent_session_ids': sorted(s for s in affected_sessions if s and s not in session_ids),
        'retry_hashes': sorted(retry_hashes),
    }
    validate_archive_erasure_plan(result)
    return result


def archive_scope_digest(plan):
    """Confirmation covers readable scope, not unrelated in-flight requests."""
    import json
    value = {k: v for k, v in plan.items() if k != 'retry_hashes'}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _unavailable_history_message(message):
    """Keep identity/order only; arbitrary quote, audio and context fields vanish."""
    value = {k: deepcopy(message[k]) for k in (
        'id', 'role', 'exchange_id', 'exchange_order', 'client_message_id', 'created_at',
    ) if k in message}
    turn = message.get('session_turn', {})
    value['session_turn'] = {
        **({'turn_id': turn['turn_id']} if turn.get('turn_id') else {}),
        'context': {'session_id': turn.get('context', {}).get('session_id', '')},
    }
    value.update(text='', content_state='source_withdrawn')
    return value


async def _settle_store_writer(task):
    """Repeated caller cancellation cannot release the serialized write boundary."""
    while True:
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.cancelled():
                raise


class AskDJHistoryManager:
    """Store user-scoped Ask DJ chat history for cross-device sync."""

    def __init__(self, hass: Any | None = None, store: Any | None = None) -> None:
        from .ask_dj.dialogue import DialogueState

        self.dialogue = DialogueState()
        self._write_lock = asyncio.Lock()
        self._pending_session_requests: dict[str, Counter] = {}
        self.hass = hass
        self._store = store if store is not None else self._create_store(hass)
        self._loaded = False
        self._erasure_uncertain = False
        self._deletion_barriers = set()
        self._data: dict[str, Any] = {"version": STORE_VERSION, "global_clear_revision": 0, "users": {}}

    def register_session_request(self, scope: str, client_id: str) -> None:
        self._pending_session_requests.setdefault(scope, Counter())[client_id] += 1

    def unregister_session_request(self, scope: str, client_id: str) -> None:
        pending = self._pending_session_requests.get(scope)
        if pending is not None:
            pending[client_id] -= 1
            if pending[client_id] <= 0:
                pending.pop(client_id, None)
            if not pending:
                self._pending_session_requests.pop(scope, None)

    async def async_session_request_cleared(self, scope: str, client_id: str) -> bool:
        await self.async_load()
        state = self._data.get("users", {}).get(scope, {})
        return _request_hash(scope, client_id) in state.get("cleared_request_hashes", [])

    @property
    def data(self) -> dict[str, Any]:
        """Return the in-memory history cache."""
        return self._data

    async def async_load(self) -> dict[str, Any]:
        """Load persistent Ask DJ history from Home Assistant Store."""
        self._require_settled_erasure()
        if self._loaded:
            return self._data
        # The first read can suspend in Store. It shares the commit boundary:
        # an older load must never overwrite a completed targeted erasure.
        async with self._write_lock:
            self._require_settled_erasure()
            if not self._loaded:
                loaded = await self._store.async_load() if self._store is not None else None
                self._data = _normalize_store_data(loaded)
                self._loaded = True
            return self._data

    def _require_settled_erasure(self) -> None:
        if self._erasure_uncertain or self._deletion_barriers:
            raise RuntimeError("history_delete_outcome_unknown")

    async def async_archive_scope_digest(self, profile_id, session_ids, *, entry_index):
        """Read committed scope without reentering a source-validator writer.

        Existing Store mutations may invoke history source validators while
        owning the write lock. Writers publish immutable staged copies only
        after acknowledgement; copying the committed pointer before a SQL await
        is a coherent read. Destructive prepare rechecks the digest UNDER the
        write boundary before it installs any intent.
        """
        await self.async_load()
        self._require_settled_erasure()
        messages = deepcopy(self._data.get('users', {}).get('profile:' + profile_id, {}).get('messages', []))
        index, message_ids = await entry_index(messages)
        self._require_settled_erasure()
        return archive_scope_digest(archive_erasure_plan(
            profile_id, messages, session_ids, entry_index=index, message_ids=message_ids))

    async def async_erase_archived_sessions(
        self, profile_id, session_ids, *, prepare_intent, entry_index,
        message_ids=frozenset(),
    ):
        """Existing Store owner commits an exact private plan after durable intent.

        prepare_intent runs inside this owner's write boundary. It must persist
        the minimal plan before returning it, or return its SAME durable plan on
        recovery. No SQL transaction is kept open across a Store await.
        """
        if self._store is None:
            raise RuntimeError('history_delete_outcome_unknown')
        async with self._write_lock:
            if self._erasure_uncertain or not self._loaded:
                data = _normalize_store_data(await self._store.async_load())
            else:
                data = deepcopy(self._data)
            scope = 'profile:' + profile_id
            state = data.get('users', {}).get(scope)
            messages = state.get('messages', []) if state else []
            if callable(entry_index):
                entry_index, message_ids = await entry_index(messages)
            plan = archive_erasure_plan(
                profile_id, messages, session_ids,
                message_ids=message_ids, entry_index=entry_index,
                pending_client_ids=self._pending_session_requests.get(scope, {}),
            )
            # Capacity never evicts a still useful original-request fence.
            if len(set(state.get('cleared_request_hashes', []) if state else [])
                   | set(plan['retry_hashes'])) > 1000:
                raise ValueError('history_delete_capacity')
            self._erasure_uncertain = True
            durable = await prepare_intent(deepcopy(plan))
            validate_archive_erasure_plan(durable)
            if state is None:
                state = {'history_revision': 0, 'clear_revision': 0,
                         'targeted_clear_revision': 0, 'messages': []}
                data.setdefault('users', {})[scope] = state
            removed = set(durable['remove_message_ids'])
            redacted = set(durable['redact_message_ids'])
            hashes = set(state.get('cleared_request_hashes', [])) | set(durable['retry_hashes'])
            if len(hashes) > 1000:
                raise ValueError('history_delete_capacity')
            messages = state.get('messages', [])
            changed = bool(removed.intersection(m['id'] for m in messages)
                           or any(m['id'] in redacted and m.get('content_state') != 'source_withdrawn'
                                  for m in messages))
            state['messages'] = [
                _unavailable_history_message(m) if m['id'] in redacted else m
                for m in messages if m['id'] not in removed
            ]
            state['cleared_request_hashes'] = sorted(hashes)
            if changed:
                state['history_revision'] += 1
                state['clear_revision'] += 1
                state['targeted_clear_revision'] = _targeted_clear_revision(state) + 1
                state['updated_at'] = _now()
            self.dialogue.forget_archived_sessions(scope, session_ids, entry_ids=frozenset(
                entry_index[m][1] for m in durable['redact_message_ids'] if m in entry_index))

            async def save():
                await self._store.async_save(_compact_store_data(data))
                self._data, self._loaded, self._erasure_uncertain = data, True, False
                return durable

            task = asyncio.create_task(save())
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                await _settle_store_writer(task)
                raise

    async def async_settle_rejected_deletion(self, barrier):
        """Only after the coordinator proves no durable intent was installed."""
        async with self._write_lock:
            loaded = await self._store.async_load() if self._store is not None else None
            self._data = _normalize_store_data(loaded)
            self._loaded, self._erasure_uncertain = True, False
            self._deletion_barriers.discard(barrier)

    async def async_forget_archived_sessions(
        self, profile_id: str, session_ids: frozenset[str], *, message_ids: frozenset[str] = frozenset()
    ) -> int:
        """Prune a committed SQL erasure from Store without resetting live speech.

        The erasure coordinator owns authorization and the durable SQL progress.
        Reapplying the same set is safe after a crash between Store and receipt.
        An uncertain save blocks history reads/writes until this owner reloads
        the actual Store and reapplies erasure; stale RAM can never overwrite it.
        """
        if (not isinstance(profile_id, str) or not profile_id
                or type(session_ids) is not frozenset or not session_ids
                or any(not isinstance(value, str) or not value for value in session_ids)):
            raise ValueError("invalid_history_delete_request")
        async with self._write_lock:
            if self._erasure_uncertain or not self._loaded:
                loaded = await self._store.async_load() if self._store is not None else None
                data = _normalize_store_data(loaded)
            else:
                data = deepcopy(self._data)
            scope = "profile:" + profile_id
            state = data.get("users", {}).get(scope)
            pending_ids = self._pending_session_requests.get(scope, {})
            if state is None and pending_ids:
                state = {"history_revision": 0, "clear_revision": 0,
                         "targeted_clear_revision": 0, "messages": []}
                data.setdefault("users", {})[scope] = state
            removed = 0
            changed = False
            if state is not None:
                _targeted_clear_revision(state)
                messages = state.get("messages", [])
                exchanges = {
                    message.get("exchange_id") or message.get("id")
                    for message in messages
                    if (message.get("id") in message_ids
                        or message.get("session_turn", {}).get("context", {}).get("session_id") in session_ids
                        or any(ref.get("session_id") in session_ids
                               for ref in message.get("historical_entry_references", [])))
                }
                discarded = [m for m in messages
                             if (m.get("exchange_id") or m.get("id")) in exchanges]
                removed = len(discarded)
                if removed:
                    state["messages"] = [m for m in messages
                                         if (m.get("exchange_id") or m.get("id")) not in exchanges]
                    hashes = list(state.get("cleared_request_hashes", []))
                    hashes.extend(_request_hash(scope, m["client_message_id"])
                                  for m in discarded if m.get("client_message_id"))
                    state["cleared_request_hashes"] = list(dict.fromkeys(hashes))[-1000:]
                    state["history_revision"] += 1
                    state["clear_revision"] += 1
                    state["targeted_clear_revision"] = _targeted_clear_revision(state) + 1
                    state["updated_at"] = _now()
                    changed = True
                hashes = list(state.get("cleared_request_hashes", []))
                pending_hashes = [_request_hash(scope, identifier) for identifier in pending_ids]
                updated_hashes = list(dict.fromkeys([*hashes, *pending_hashes]))[-1000:]
                if updated_hashes != hashes:
                    state["cleared_request_hashes"] = updated_hashes
                    changed = True
            # Invalidate pending read context even if no archived exchange had
            # text in Store. Preserve accepted independent speech and dedup.
            self.dialogue.forget_archived_sessions(scope, session_ids)
            self._erasure_uncertain = True

            async def save():
                if changed and self._store is not None:
                    await self._store.async_save(_compact_store_data(data))
                self._data = data
                self._loaded = True
                self._erasure_uncertain = False
                return removed

            task = asyncio.create_task(save())
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                # Cancellation never releases the lock over an unsettled save.
                await _settle_store_writer(task)
                raise

    async def async_save(self) -> None:
        """Persist compact Ask DJ history."""
        await self.async_load()
        if self._store is not None:
            await self._store.async_save(_compact_store_data(self._data))
            self._committed_store_write = True

    async def async_history(
        self,
        user_id: str | None,
        *,
        since_revision: int | None = None,
        limit: int = MAX_MESSAGES_PER_USER,
    ) -> dict[str, Any]:
        """Return bounded history for one HA user."""
        await self.async_load()
        user_key = _user_key(user_id)
        state = self._user_state(user_key)
        messages = sorted(
            list(state.get("messages") or []),
            key=lambda item: str(item.get("created_at") or ""),
        )
        if since_revision is not None and since_revision >= int(state.get("history_revision") or 0):
            messages = []
        else:
            messages = messages[-_limit(limit):]
        return {
            "success": True,
            "user_id": user_key,
            "history_revision": int(state.get("history_revision") or 0),
            "clear_revision": self._effective_clear_revision(state, user_key),
            **_history_limit_metadata(state),
            "messages": deepcopy(messages),
            "server_time": _now(),
        }

    @_committed_mutation
    async def async_clear(self, user_id: str | None, *, commit_guard=None) -> dict[str, Any]:
        """Clear history for one HA user and advance sync revisions."""
        await self.async_load()
        if commit_guard is not None:
            await commit_guard()
        user_key = _user_key(user_id)
        state = self._user_state(user_key)
        state["history_revision"] = int(state.get("history_revision") or 0) + 1
        state["clear_revision"] = int(state.get("clear_revision") or 0) + 1
        self._remember_cleared_session_requests(user_key, state)
        state["messages"] = []
        _clear_trim_metadata(state)
        state["updated_at"] = _now()
        await self.async_save()
        if commit_guard is not None:
            await commit_guard()
        self.dialogue.invalidate(user_key)
        return {
            "success": True,
            "cleared": True,
            "user_id": user_key,
            "history_revision": state["history_revision"],
            "clear_revision": self._effective_clear_revision(state, user_key),
            "ask_dj_clear_required": True,
            **_history_limit_metadata(state),
            "messages": [],
            "server_time": _now(),
        }

    def _remember_cleared_session_requests(self, user_key, state):
        """Keep bounded opaque retry tombstones; no cleared question text survives."""
        if not user_key.startswith("profile:"):
            return
        known = [m.get("client_message_id") for m in state.get("messages", [])]
        known.extend(self._pending_session_requests.get(user_key, {}))
        hashes = list(state.get("cleared_request_hashes", []))
        hashes.extend(
            _request_hash(user_key, identifier)
            for identifier in known if isinstance(identifier, str) and identifier
        )
        state["cleared_request_hashes"] = list(dict.fromkeys(hashes))[-1000:]

    @_committed_mutation
    async def async_clear_all(self, *, include_profile_history: bool = True) -> dict[str, Any]:
        """Clear history for all app clients and advance a global clear revision."""
        await self.async_load()
        global_clear_revision = int(self._data.get("global_clear_revision") or 0) + 1
        self._data["global_clear_revision"] = global_clear_revision
        if include_profile_history:
            self.dialogue.invalidate()
        users = self._data.setdefault("users", {})
        if not users:
            users[_user_key(None)] = {"history_revision": 0, "clear_revision": 0, "messages": []}
        max_history_revision = global_clear_revision
        for user_key in self._pending_session_requests:
            if include_profile_history and user_key.startswith("profile:"):
                self._user_state(user_key)
        for user_key, state in users.items():
            if user_key.startswith("profile:") and not include_profile_history:
                continue
            if not isinstance(state, dict):
                continue
            state["history_revision"] = int(state.get("history_revision") or 0) + 1
            state["clear_revision"] = max(
                int(state.get("clear_revision") or 0) + int(user_key.startswith("profile:")),
                global_clear_revision,
            )
            self._remember_cleared_session_requests(user_key, state)
            state["messages"] = []
            _clear_trim_metadata(state)
            state["updated_at"] = _now()
            max_history_revision = max(max_history_revision, int(state["history_revision"]))
        await self.async_save()
        return {
            "success": True,
            "cleared": True,
            "user_id": "all",
            "history_revision": max_history_revision,
            "clear_revision": global_clear_revision,
            "ask_dj_clear_required": True,
            "history_limit": MAX_MESSAGES_PER_USER,
            "history_trimmed_before": None,
            "history_trimmed_count": 0,
            "messages": [],
            "server_time": _now(),
        }

    @_committed_mutation
    async def async_append_exchange(
        self,
        user_id: str | None,
        request_payload: dict[str, Any],
        assistant_response: dict[str, Any],
        *,
        session_turn: dict[str, Any] | None = None,
        commit_guard=None,
    ) -> dict[str, Any]:
        """Append user and assistant messages, deduping client retries."""
        await self.async_load()
        user_key = _user_key(user_id)
        state = self._user_state(user_key)
        client_message_id = _clean_text(request_payload.get("client_message_id"))
        if session_turn is not None and _request_hash(user_key, client_message_id) in state.get(
            "cleared_request_hashes", []
        ):
            raise ValueError("conversation_history_changed")
        existing = self._find_exchange(state, client_message_id)
        if existing is not None:
            return {
                "success": True,
                "user_id": user_key,
                **existing,
                "history_revision": int(state.get("history_revision") or 0),
                "clear_revision": self._effective_clear_revision(state, user_key),
                **_history_limit_metadata(state),
                "server_time": _now(),
                "deduplicated": True,
            }

        user_message = _message_from_request(request_payload)
        stored_response = assistant_response
        if session_turn is not None:
            # Existing live response may carry transient media/actions; the archive does not.
            stored_response = {
                **assistant_response,
                "audio_url": None,
                "images": [],
                "playback_actions": [],
            }
        assistant_message = _message_from_response(request_payload, stored_response)
        exchange_id = _exchange_id(request_payload, user_message)
        if session_turn is not None:
            user_message["session_turn"] = deepcopy(session_turn)
            assistant_message["session_turn"] = deepcopy(session_turn)
            refs = list(assistant_response.get("historical_matches") or [])
            refs.extend(session_turn.get("dependency_entries", []))
            selected = session_turn.get("context", {}).get("selected_entry")
            if isinstance(selected, dict):
                refs.append(selected)
            implicit = session_turn.get("implicit_playback_entry")
            if isinstance(implicit, dict):
                refs.append(implicit)
            if isinstance(refs, list):
                user_message["historical_entry_references"] = assistant_message[
                    "historical_entry_references"
                ] = [
                    {"session_id": r["session_id"], "entry_id": r["entry_id"]}
                    for r in refs
                    if isinstance(r, dict) and r.get("session_id") and r.get("entry_id")
                ][:20]
        user_message["exchange_id"] = exchange_id
        user_message["exchange_order"] = 0
        assistant_message["exchange_id"] = exchange_id
        assistant_message["exchange_order"] = 1
        state.setdefault("messages", []).extend([user_message, assistant_message])
        state["history_revision"] = int(state.get("history_revision") or 0) + 1
        trimmed = _apply_history_limit(state)
        if trimmed:
            state["history_revision"] = int(state.get("history_revision") or 0) + 1
        state["updated_at"] = _now()
        if commit_guard is not None:
            await commit_guard()
        await self.async_save()
        if commit_guard is not None:
            await commit_guard()
        return {
            "success": True,
            "user_id": user_key,
            "user_message": deepcopy(user_message),
            "assistant_message": deepcopy(assistant_message),
            "messages": [deepcopy(user_message), deepcopy(assistant_message)],
            "history_revision": state["history_revision"],
            "clear_revision": self._effective_clear_revision(state, user_key),
            **_history_limit_metadata(state),
            "server_time": _now(),
        }

    @_committed_mutation
    async def async_discard_session_exchange(self, scope: str, client_id: str, turn_id: str) -> None:
        """Remove only this rejected exchange, preserving concurrent clears/writes."""
        await self.async_load()
        state = self._data.get("users", {}).get(_user_key(scope))
        if state is None:
            return
        messages = state.get("messages", [])
        safe = [
            message
            for message in messages
            if not (
                message.get("client_message_id") == client_id
                and message.get("session_turn", {}).get("turn_id") == turn_id
            )
        ]
        if len(safe) != len(messages):
            state["messages"] = safe
            state["history_revision"] = int(state.get("history_revision") or 0) + 1
            state["clear_revision"] = int(state.get("clear_revision") or 0) + 1
            await self.async_save()

    @_committed_mutation
    async def async_prune_session_history(
        self, valid_profiles: set[str], *, cutoff: str, dependency_validator=None
    ) -> int:
        """Prune only new Profile Session turns; legacy HA-user history stays intact."""
        await self.async_load()
        removed = 0
        for scope, state in self._data.get("users", {}).items():
            if not scope.startswith("profile:"):
                continue
            messages = state.get("messages", [])
            expired_exchanges = set()
            for message in messages:
                invalid = (
                    scope[8:] not in valid_profiles or str(message.get("created_at") or "") < cutoff
                )
                if not invalid and dependency_validator is not None:
                    for dependency in message.get("historical_entry_references", []):
                        if not await dependency_validator(scope[8:], dependency):
                            invalid = True
                            break
                if invalid:
                    expired_exchanges.add(message.get("exchange_id") or message.get("id"))
            safe = [
                message
                for message in messages
                if (message.get("exchange_id") or message.get("id")) not in expired_exchanges
            ]
            if len(safe) != len(messages):
                removed += len(messages) - len(safe)
                state["messages"] = safe
                state["history_revision"] = int(state.get("history_revision") or 0) + 1
                state["clear_revision"] = int(state.get("clear_revision") or 0) + 1
                state["updated_at"] = _now()
        if removed:
            await self.async_save()
        return removed

    async def async_saved_exchange(self, scope_key: str, client_message_id: str) -> dict[str, Any] | None:
        """Existing history authority read, scoped by a server-resolved Profile key."""
        await self.async_load()
        state=self._data.get("users",{}).get(_user_key(scope_key),{})
        result=self._find_exchange(state,client_message_id)
        return deepcopy(result) if result else None

    async def async_messages_by_id(self, scope_key: str, identifiers: set[str]) -> dict[str, dict]:
        await self.async_load()
        state=self._data.get("users",{}).get(_user_key(scope_key),{})
        return {str(m["id"]):deepcopy(m) for m in state.get("messages",[]) if str(m.get("id") or "") in identifiers}

    async def async_scope_revision(self, scope_key: str) -> str:
        await self.async_load()
        return self.scope_revision(scope_key)

    def scope_revision(self, scope_key: str) -> str:
        """Read the committed cache for a final fence without yielding authority."""
        user_key = _user_key(scope_key)
        state=self._data.get("users",{}).get(user_key,{})
        revision = self._effective_clear_revision(state, user_key)
        if user_key.startswith("profile:"):
            revision -= _targeted_clear_revision(state)
        return str(state.get("history_trimmed_count",0))+":"+str(revision)

    def scope_revision_for_receipt(self, scope_key: str, receipt: dict) -> str:
        """Compare an append receipt in the server privacy revision domain."""
        user_key = _user_key(scope_key)
        state = self._data.get("users", {}).get(user_key, {})
        revision = receipt.get("clear_revision", 0)
        if user_key.startswith("profile:"):
            revision -= _targeted_clear_revision(state)
        return str(receipt.get("history_trimmed_count", 0)) + ":" + str(revision)

    @_committed_mutation
    async def async_append_assistant_message(
        self,
        user_id: str | None,
        request_payload: dict[str, Any],
        assistant_response: dict[str, Any],
    ) -> dict[str, Any]:
        """Append an assistant-only message, for ambient server-side Ask DJ events."""
        await self.async_load()
        user_keys = self._target_user_keys(user_id)
        assistant_message = _message_from_response(request_payload, assistant_response)
        client_message_id = _clean_text(request_payload.get("client_message_id"))
        if client_message_id:
            existing = self._find_assistant_message(user_keys, client_message_id)
            if existing is not None:
                first_state = self._user_state(user_keys[0])
                return {
                    "success": True,
                    "user_id": user_keys[0],
                    "assistant_message": deepcopy(existing),
                    "history_revision": int(first_state.get("history_revision") or 0),
                    "clear_revision": self._effective_clear_revision(first_state, user_keys[0]),
                    **_history_limit_metadata(first_state),
                    "server_time": _now(),
                    "deduplicated": True,
                }
        for user_key in user_keys:
            state = self._user_state(user_key)
            state.setdefault("messages", []).append(deepcopy(assistant_message))
            state["history_revision"] = int(state.get("history_revision") or 0) + 1
            trimmed = _apply_history_limit(state)
            if trimmed:
                state["history_revision"] = int(state.get("history_revision") or 0) + 1
            state["updated_at"] = _now()
        await self.async_save()
        first_state = self._user_state(user_keys[0])
        return {
            "success": True,
            "user_id": user_keys[0],
            "assistant_message": deepcopy(assistant_message),
            "history_revision": int(first_state.get("history_revision") or 0),
            "clear_revision": self._effective_clear_revision(first_state, user_keys[0]),
            **_history_limit_metadata(first_state),
            "server_time": _now(),
        }

    async def async_has_client_message_id(
        self,
        user_id: str | None,
        client_message_id: str,
    ) -> bool:
        """Return whether a message id already exists for the target history."""
        await self.async_load()
        message_id = _clean_text(client_message_id)
        if not message_id:
            return False
        return self._find_assistant_message(self._target_user_keys(user_id), message_id) is not None

    @_committed_mutation
    async def async_reserve_dialogue_effect(self, scope: str, client_id: str, digest: str) -> None:
        """Opaque dispatch receipt survives failure/clear/reload; never persist content."""
        from .ask_dj.dialogue import DialogueError

        state = self._user_state(scope)
        receipts = state.setdefault("dialogue_effect_receipts", {})
        key = _request_hash(scope, client_id)
        if key in receipts:
            code = "action_outcome_uncertain" if receipts[key] == digest else "client_message_conflict"
            raise DialogueError(code)
        if len(receipts) >= 1000:
            raise DialogueError("action_receipt_capacity", 503)
        receipts[key] = digest
        await self.async_save()

    def recent_messages_for_prompt(
        self,
        user_id: str | None,
        *,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """Return recent messages already loaded in memory for prompt context."""
        user_key = _user_key(user_id)
        state = (self._data.get("users") or {}).get(user_key) or {}
        messages = sorted(
            [message for message in state.get("messages", []) if not message.get("session_turn")],
            key=lambda item: str(item.get("created_at") or ""),
        )
        return deepcopy(messages[-_limit(limit):])

    def _user_state(self, user_id: str) -> dict[str, Any]:
        users = self._data.setdefault("users", {})
        if user_id not in users or not isinstance(users[user_id], dict):
            users[user_id] = {
                "history_revision": 0,
                "clear_revision": 0,
                "targeted_clear_revision": 0,
                "messages": [],
                "history_trimmed_before": None,
                "history_trimmed_count": 0,
            }
        state = users[user_id]
        state.setdefault("history_revision", 0)
        state.setdefault("clear_revision", 0)
        state.setdefault("targeted_clear_revision", 0)
        state.setdefault("messages", [])
        state.setdefault("history_trimmed_before", None)
        state.setdefault("history_trimmed_count", 0)
        return state

    def _effective_clear_revision(self, state: dict[str, Any], scope_key: str = "") -> int:
        if scope_key.startswith("profile:"):
            return int(state.get("clear_revision") or 0)
        return max(
            int(state.get("clear_revision") or 0),
            int(self._data.get("global_clear_revision") or 0),
        )

    def _target_user_keys(self, user_id: str | None) -> list[str]:
        if _clean_text(user_id):
            return [_user_key(user_id)]
        users = self._data.get("users") or {}
        keys = [str(key) for key in users.keys() if _clean_text(key) and not str(key).startswith("profile:")]
        return keys or [_user_key(None)]

    def _find_exchange(
        self,
        state: dict[str, Any],
        client_message_id: str,
    ) -> dict[str, Any] | None:
        if not client_message_id:
            return None
        messages = list(state.get("messages") or [])
        for index, message in enumerate(messages):
            if (
                message.get("role") == "user"
                and message.get("client_message_id") == client_message_id
            ):
                assistant = None
                for candidate in messages[index + 1 :]:
                    if candidate.get("role") == "assistant":
                        assistant = candidate
                        break
                turn = message.get("session_turn")
                if turn and (not assistant or assistant.get("session_turn", {}).get("turn_id") != turn.get("turn_id") or assistant.get("exchange_id") != message.get("exchange_id")):
                    return None
                return {
                    "user_message": deepcopy(message),
                    "assistant_message": deepcopy(assistant or {}),
                    "messages": [deepcopy(message), deepcopy(assistant or {})],
                }
        return None

    def _find_assistant_message(
        self,
        user_keys: list[str],
        client_message_id: str,
    ) -> dict[str, Any] | None:
        if not client_message_id:
            return None
        for user_key in user_keys:
            state = self._user_state(user_key)
            for message in state.get("messages") or []:
                if (
                    isinstance(message, dict)
                    and message.get("role") == "assistant"
                    and message.get("client_message_id") == client_message_id
                ):
                    return deepcopy(message)
        return None

    def _create_store(self, hass: Any | None) -> Any | None:
        if hass is None:
            return None
        try:
            from homeassistant.helpers.storage import Store
        except Exception:  # noqa: BLE001
            return None
        return Store(hass, STORE_VERSION, STORE_KEY)


def _message_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    return _compact_message(
        {
            "id": _server_message_id(),
            "client_message_id": _clean_text(payload.get("client_message_id")),
            "role": "user",
            **({"message_kind":"system", "origin":"mood_change"} if payload.get("_setting_feedback") is True else {}),
            "text": _clean_text(payload.get("text") or payload.get("message")),
            "created_at": now,
            "client_id": _client_id(payload),
            "client_type": _clean_text(payload.get(CONF_CLIENT_TYPE)),
            "status": "delivered",
            "images": [],
            "links": [],
            "sources": [],
            "audio_url": None,
            "playback_actions": [],
        }
    )


def _message_from_response(
    request_payload: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, Any]:
    from .session_speech import accepted_processing_basis
    text = _clean_text(
        response.get("dj_text")
        or response.get("text")
        or response.get("message")
    )
    return _compact_message(
        {
            "id": _server_message_id(),
            "client_message_id": _clean_text(request_payload.get("client_message_id")),
            "role": "assistant",
            "message_kind": _message_kind(response),
            "origin": _clean_text(response.get("origin")),
            "text": text,
            "speech_processing_basis": accepted_processing_basis(response),
            "research_answer_qualification": ("supported_prefix_v1"
                if response.get("research_answer_qualification") == "supported_prefix_v1" else None),
            "historical_matches": _compact_items(response.get("historical_matches")),
            "navigation_actions": _compact_items(response.get("navigation_actions")),
            "created_at": _now(),
            "client_id": _client_id(request_payload),
            "client_type": _clean_text(request_payload.get(CONF_CLIENT_TYPE)),
            "status": "delivered" if response.get("success", True) else "error",
            "images": _compact_items(response.get("images")),
            "links": _compact_items(response.get("links")),
            "sources": _compact_items(response.get("sources")),
            "audio_url": _clean_text(response.get("audio_url")) or None,
            "playback_actions": _compact_items(response.get("playback_actions")),
            "intent": deepcopy(response.get("intent")) if response.get("intent") else None,
            "action": _clean_text(response.get("action")),
        }
    )


def _exchange_id(request_payload: dict[str, Any], user_message: dict[str, Any]) -> str:
    return (
        _clean_text(request_payload.get("client_message_id"))
        or _clean_text(user_message.get("id"))
        or _server_message_id()
    )


def _message_kind(response: dict[str, Any]) -> str:
    value = _clean_text(response.get("message_kind") or response.get("kind"))
    if value in {"system", "assistant", "error"}:
        return value
    intent = response.get("intent") if isinstance(response.get("intent"), dict) else {}
    if intent.get("intent") == "ambient_music_fact":
        return "system"
    return "assistant"


def _compact_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in message.items()
        if value not in ("", [], {}, None)
        or key in {"audio_url", "images", "links", "sources", "playback_actions"}
    }


def _compact_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value[:MAX_ITEMS]:
        if isinstance(item, dict):
            clean = {
                str(key): _clean_value(entry)
                for key, entry in item.items()
                if _clean_value(entry) not in ("", [], {}, None)
            }
            if clean:
                items.append(clean)
    return items


def _targeted_clear_revision(state: dict[str, Any]) -> int:
    """Legacy absence is zero; corrupt privacy arithmetic must fail closed."""
    value = state.get("targeted_clear_revision", 0)
    clear = state.get("clear_revision", 0)
    if type(value) is not int or type(clear) is not int or not 0 <= value <= clear:
        raise ValueError("invalid_history_clear_revision")
    return value


def _compact_store_data(data: dict[str, Any]) -> dict[str, Any]:
    users: dict[str, Any] = {}
    for user_id, state in (data.get("users") or {}).items():
        if not isinstance(state, dict):
            continue
        messages = [
            _compact_message(message)
            for message in state.get("messages", [])[-MAX_MESSAGES_PER_USER:]
            if isinstance(message, dict)
        ]
        users[_user_key(user_id)] = {
            "history_revision": int(state.get("history_revision") or 0),
            "clear_revision": int(state.get("clear_revision") or 0),
            "targeted_clear_revision": _targeted_clear_revision(state),
            "messages": messages,
            "updated_at": _clean_text(state.get("updated_at")),
            "dialogue_effect_receipts": {k: v for k, v in list(state.get("dialogue_effect_receipts", {}).items())[:1000]
                                        if isinstance(k, str) and len(k) == 64 and isinstance(v, str) and len(v) == 64},
            "cleared_request_hashes": [
                value
                for value in state.get("cleared_request_hashes", [])[-1000:]
                if isinstance(value, str) and len(value) == 64
            ],
            "history_trimmed_before": _clean_text(state.get("history_trimmed_before")) or None,
            "history_trimmed_count": int(state.get("history_trimmed_count") or 0),
        }
    return {
        "version": STORE_VERSION,
        "global_clear_revision": int(data.get("global_clear_revision") or 0),
        "users": users,
    }


def _normalize_store_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"version": STORE_VERSION, "global_clear_revision": 0, "users": {}}
    normalized = {
        "version": STORE_VERSION,
        "global_clear_revision": int(data.get("global_clear_revision") or 0),
        "users": {},
    }
    for user_id, state in (data.get("users") or {}).items():
        if not isinstance(state, dict):
            continue
        normalized["users"][_user_key(user_id)] = {
            "history_revision": int(state.get("history_revision") or 0),
            "clear_revision": int(state.get("clear_revision") or 0),
            "targeted_clear_revision": _targeted_clear_revision(state),
            "messages": [
                _compact_message(message)
                for message in state.get("messages", [])[-MAX_MESSAGES_PER_USER:]
                if isinstance(message, dict)
            ],
            "updated_at": _clean_text(state.get("updated_at")),
            "dialogue_effect_receipts": {k: v for k, v in list(state.get("dialogue_effect_receipts", {}).items())[:1000]
                                        if isinstance(k, str) and len(k) == 64 and isinstance(v, str) and len(v) == 64},
            "cleared_request_hashes": [
                value
                for value in state.get("cleared_request_hashes", [])[-1000:]
                if isinstance(value, str) and len(value) == 64
            ],
            "history_trimmed_before": _clean_text(state.get("history_trimmed_before")) or None,
            "history_trimmed_count": int(state.get("history_trimmed_count") or 0),
        }
    return normalized


def _client_id(payload: dict[str, Any]) -> str:
    return _clean_text(
        payload.get("client_id")
        or payload.get(CONF_DEVICE_ID)
        or payload.get(CONF_DEVICE_NAME)
    )


def _clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_clean_value(item) for item in value[:MAX_ITEMS]]
    if isinstance(value, dict):
        return {
            str(key): _clean_value(item)
            for key, item in value.items()
            if _clean_value(item) not in ("", [], {}, None)
        }
    return _clean_text(value)


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) > MAX_TEXT_LENGTH:
        return text[:MAX_TEXT_LENGTH]
    return text


def _limit(value: int) -> int:
    try:
        return max(1, min(MAX_MESSAGES_PER_USER, int(value)))
    except (TypeError, ValueError):
        return MAX_MESSAGES_PER_USER


def _history_limit_metadata(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "history_limit": MAX_MESSAGES_PER_USER,
        "history_trimmed_before": _clean_text(state.get("history_trimmed_before")) or None,
        "history_trimmed_count": int(state.get("history_trimmed_count") or 0),
    }


def _clear_trim_metadata(state: dict[str, Any]) -> None:
    state["history_trimmed_before"] = None
    state["history_trimmed_count"] = 0


def _apply_history_limit(state: dict[str, Any]) -> bool:
    messages = [message for message in state.get("messages", []) if isinstance(message, dict)]
    if len(messages) <= MAX_MESSAGES_PER_USER:
        state["messages"] = messages
        state.setdefault("history_trimmed_before", None)
        state.setdefault("history_trimmed_count", 0)
        return False

    add_notice = _should_add_retention_message(messages)
    remove_count = len(messages) - MAX_MESSAGES_PER_USER + (1 if add_notice else 0)
    removed = messages[:remove_count]
    kept = messages[remove_count:]
    cutoff = _trim_cutoff_timestamp(kept, removed)
    if add_notice:
        kept.append(_retention_system_message())
    else:
        _move_retention_message_to_end(kept)
    state["messages"] = kept[-MAX_MESSAGES_PER_USER:]
    state["history_trimmed_before"] = cutoff
    previous_count = int(state.get("history_trimmed_count") or 0)
    state["history_trimmed_count"] = previous_count + len(removed)
    return True


def _should_add_retention_message(messages: list[dict[str, Any]]) -> bool:
    latest = None
    for message in reversed(messages):
        if (
            message.get("role") == "assistant"
            and message.get("message_kind") == "system"
            and message.get("origin") == "history_retention"
        ):
            latest = _parse_time(message.get("created_at"))
            break
    if latest is None:
        return True
    return datetime.now(timezone.utc) - latest >= RETENTION_MESSAGE_COOLDOWN


def _retention_system_message() -> dict[str, Any]:
    return _compact_message(
        {
            "id": _server_message_id(),
            "role": "assistant",
            "message_kind": "system",
            "origin": "history_retention",
            "text": RETENTION_MESSAGE_TEXT,
            "created_at": _now(),
            "status": "delivered",
            "images": [],
            "links": [],
            "sources": [],
            "audio_url": None,
            "playback_actions": [],
            "intent": {
                "category": "system",
                "intent": "history_limit_reached",
            },
            "action": "none",
        }
    )


def _move_retention_message_to_end(messages: list[dict[str, Any]]) -> None:
    """Keep the single existing retention notice visible after a later trim."""
    for index, message in enumerate(messages):
        if (
            message.get("role") == "assistant"
            and message.get("message_kind") == "system"
            and message.get("origin") == "history_retention"
        ):
            messages.append(messages.pop(index))
            return


def _trim_cutoff_timestamp(kept: list[dict[str, Any]], removed: list[dict[str, Any]]) -> str:
    for message in kept:
        timestamp = _clean_text(message.get("created_at"))
        if timestamp:
            return timestamp
    for message in reversed(removed):
        timestamp = _clean_text(message.get("created_at"))
        if timestamp:
            return timestamp
    return _now()


def _parse_time(value: Any) -> datetime | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _server_message_id() -> str:
    return f"server-{uuid.uuid4()}"


def _user_key(user_id: Any) -> str:
    cleaned = _clean_text(user_id)
    return cleaned or "anonymous"


def _request_hash(scope: str, client_id: str) -> str:
    return hashlib.sha256((scope + "\0" + client_id).encode()).hexdigest()
