"""Owner-confirmed content units using the existing Store, Runtime and SQLite owners."""
from __future__ import annotations

from copy import deepcopy
from contextlib import asynccontextmanager
import json
from uuid import NAMESPACE_URL, uuid5

from .ask_dj_history import archive_erasure_plan, _request_hash
from .content_deletion_runtime import apply_runtime_content, finish_runtime_content, moment_closure, runtime_digest
from .history_deletion import ArchiveDeletionCoordinator
from .persistence.content_deletion import ContentDeletionRepository, MAX_UNITS, scope_digest, validate_scope
from .persistence.history import HistoricalProjectionRepository
from .persistence.history_deletion import HistoryDeletionError


def _message_session_id(message):
    """Standalone turns use JSON null; their explicit delete selector uses ''."""
    session = message.get('session_turn', {}).get('context', {}).get('session_id')
    return '' if session is None else session


@asynccontextmanager
async def runtime_lock(manager):
    if manager is None:
        yield
    else:
        async with manager._lock:
            yield


class ContentDeletionCoordinator(ArchiveDeletionCoordinator):
    """Manager → serialized Store → short SQL transaction; never reverse that order."""

    def __init__(self, persistence, history, *, manager=None):
        super().__init__(persistence, history)
        self.journal = ContentDeletionRepository(persistence)
        self.repository = HistoricalProjectionRepository(persistence)
        self.manager = manager
        self._content_media_tokens = {}

    async def _resolve(self, owner, selector, messages):
        kind, session, target = (selector[k] for k in ('kind', 'session_id', 'target_id'))
        unit_kind = kind
        selected_ids = set()
        moment_ids = set()
        original_ids = set()
        active = self.manager.current_active(owner) if self.manager is not None else None
        if kind == 'entry':
            row = await self.repository.async_entry_record(owner, session, target)
            if row is None:
                raise HistoryDeletionError('content_unavailable')
            if row['kind'] in {'dj_moment', 'dj_publication', 'dj_silence'}:
                unit_kind, target = 'moment', row['reference_id']
            elif row['kind'] in {'conversation_user', 'conversation_dj'}:
                unit_kind, target = 'message', json.loads(row['body']).get('message_id')
            else:
                raise HistoryDeletionError('content_unavailable')
        if unit_kind == 'moment':
            if not session:
                raise HistoryDeletionError('content_unavailable')
            moment_ids.add(target)
            if active is not None and active.session_id == session:
                moment_ids.update(moment_closure(active, {target}))
        elif unit_kind == 'message':
            selected = next((m for m in messages if m['id'] == target), None)
            if selected is None:
                raise HistoryDeletionError('content_unavailable')
            actual_session = _message_session_id(selected)
            if session != actual_session:
                raise HistoryDeletionError('content_unavailable')
            session = actual_session
            exchange = selected.get('exchange_id') or selected['id']
            selected_ids.update(m['id'] for m in messages if (m.get('exchange_id') or m['id']) == exchange)
            target, unit_kind = exchange, 'exchange'
        elif unit_kind == 'request':
            original_ids.add(target)
            selected_ids.update(m['id'] for m in messages if m.get('client_message_id') == target)
            if any(_message_session_id(m) != session
                   for m in messages if m['id'] in selected_ids):
                raise HistoryDeletionError('content_unavailable')
            unit_kind, target = 'attempt', _request_hash('profile:' + owner, target)
        else:
            raise HistoryDeletionError('invalid_content_delete_request')
        for m in messages:
            if m['id'] in selected_ids and m.get('client_message_id'):
                original_ids.add(m['client_message_id'])
        return {'kind': unit_kind, 'session_id': session, 'target_id': target}, selected_ids, moment_ids, original_ids

    async def _build(self, owner, selector, messages, index):
        """Pure bounded scope derivation under the existing Store writer boundary."""
        unit, selected_ids, moment_ids, original_ids = await self._resolve(owner, selector, messages)
        active = self.manager.current_active(owner) if self.manager is not None else None
        # Fixed SQL and bounded recursive ID provenance; never infer a relation
        # from titles, text or adjacency. RAM and durable edges can interleave.
        for _ in range(MAX_UNITS + 1):
            def read(tx):
                return tx.fetchall(
                    'WITH RECURSIVE affected(moment_id) AS ('
                    'SELECT value FROM json_each(?) UNION '
                    'SELECT e.reference_id FROM djconnect_session_entries AS e '
                    "JOIN json_each(e.body,'$.dependency_moment_ids') AS dependency "
                    'JOIN affected ON dependency.value=affected.moment_id '
                    "WHERE e.owner_profile_id=? AND e.session_id=? AND e.kind IN ('dj_moment','dj_publication','dj_silence') "
                    'LIMIT ?) SELECT session_id,entry_id,kind,reference_id FROM djconnect_session_entries '
                    "WHERE owner_profile_id=? AND session_id=? AND kind IN ('dj_moment','dj_publication','dj_silence') "
                    'AND reference_id IN (SELECT moment_id FROM affected) LIMIT ?',
                    (json.dumps(sorted(moment_ids)), owner, unit['session_id'], MAX_UNITS + 1,
                     owner, unit['session_id'], MAX_UNITS + 1))
            moment_rows = await self.persistence.async_in_transaction(read)
            added = moment_ids | {row[3] for row in moment_rows}
            if active is not None and active.session_id == unit['session_id']:
                added.update(moment_closure(active, added))
            if len(moment_rows) > MAX_UNITS or len(added) > MAX_UNITS:
                raise HistoryDeletionError('content_delete_capacity')
            if added == moment_ids:
                break
            moment_ids = added
        else:
            raise HistoryDeletionError('content_delete_capacity')
        moments = {(unit['session_id'], mid) for mid in moment_ids}
        if unit['kind'] == 'moment':
            active = self.manager.current_active(owner) if self.manager is not None else None
            live_root = (active is not None and active.session_id == unit['session_id']
                and any(m.moment_id == unit['target_id'] for m in active.broadcast.state.dj_moments))
            if not live_root and not any(row[3] == unit['target_id'] for row in moment_rows):
                raise HistoryDeletionError('content_unavailable')
        initial = frozenset((s, e) for s, e, _, _ in moment_rows)
        forced = set()
        for _ in range(MAX_UNITS + 1):
            plan = archive_erasure_plan(owner, messages, frozenset(), message_ids=frozenset(selected_ids),
                entry_index=index, pending_client_ids=tuple(original_ids), initial_entries=initial,
                individual=True, unavailable_client_ids=frozenset(forced), initial_moments=frozenset(moments))
            known = set(plan['retry_hashes'])
            known.update(_request_hash('profile:' + owner, client) for client in forced)
            added = self.history.dialogue.content_request_sources('profile:' + owner, known,
                entries=initial | frozenset(index[m] for m in plan['remove_message_ids'] + plan['redact_message_ids'] if m in index),
                moments=frozenset(moments))
            if added <= forced:
                break
            forced.update(added)
        else:
            raise HistoryDeletionError('content_delete_capacity')
        plan['retry_hashes'] = sorted(set(plan['retry_hashes']) | {
            _request_hash('profile:' + owner, client) for client in forced})
        direct = set(plan['remove_message_ids'])
        redacted = set(plan['redact_message_ids'])
        affected = direct | redacted
        entries = []
        for session, entry, kind, reference in moment_rows:
            mode = 'remove' if reference == unit['target_id'] else 'unavailable'
            entries.append([session, entry, kind, reference, mode])
        def read_entries(tx):
            return tx.fetchall(
                'SELECT session_id,entry_id,kind,reference_id,json_extract(body,\'$.message_id\') '
                'FROM djconnect_session_entries WHERE owner_profile_id=? '
                "AND kind IN ('conversation_user','conversation_dj') AND json_valid(body) "
                "AND json_extract(body,'$.message_id') IN (SELECT value FROM json_each(?)) LIMIT ?",
                (owner, json.dumps(sorted(affected)), MAX_UNITS + 1))
        for session, entry, kind, reference, message in await self.persistence.async_in_transaction(read_entries):
            entries.append([session, entry, kind, reference, 'remove' if message in direct else 'unavailable'])
        session_ids = {e[0] for e in entries} | {s for s, _ in moments}
        if unit['session_id']:
            session_ids.add(unit['session_id'])
        policy = await self.repository.async_retention_policy()
        sessions = []
        from .session_history_projection import session_retained
        for session in sorted(session_ids):
            row = await self.repository.async_session_record(session)
            if row is None or row['owner_profile_id'] != owner:
                raise HistoryDeletionError('content_unavailable')
            live = self.manager.current_active(owner) if self.manager is not None else None
            live_unit = unit['kind'] in {'moment', 'attempt'} and live is not None and live.session_id == session
            if not live_unit and not session_retained(row, retention_days=policy[0]):
                raise HistoryDeletionError('content_unavailable')
            sessions.append([session, row['revision']])
        clients = forced | original_ids | {m.get('client_message_id') for m in messages if m['id'] in affected and m.get('client_message_id')}
        turns = {m.get('session_turn', {}).get('turn_id') for m in messages if m['id'] in affected}
        turns.update('turn-' + uuid5(NAMESPACE_URL, 'profile:' + owner + ':' + client).hex for client in clients)
        scope = {'unit': unit, 'sessions': sessions, 'entries': sorted(entries),
                 'moments': sorted([list(pair) for pair in moments]),
                 'turn_ids': sorted(t for t in turns if t), 'request_hashes': plan['retry_hashes']}
        validate_scope(scope)
        if len(entries) + len(affected) + len(moments) > MAX_UNITS:
            raise HistoryDeletionError('content_delete_capacity')
        basis = {'retention': policy, 'runtime': runtime_digest(self.manager, owner, scope['moments'])}
        return scope, plan, basis

    async def async_preview(self, owner, selector, *, authorize):
        async with self._lock, runtime_lock(self.manager):
            await self.history.async_load()
            async with self.history._write_lock:
                self.history._require_settled_erasure()
                messages = deepcopy(self.history._data.get('users', {}).get('profile:' + owner, {}).get('messages', []))
                index, _ = await self.journal.async_scope_index(owner, messages, frozenset())
                scope, plan, basis = await self._build(owner, selector, messages, index)
                authorize()
                return {'scope': scope, 'plan': plan, 'basis': basis,
                        'selector': deepcopy(selector), 'digest': scope_digest([scope, plan, basis])}

    def _content_fence(self, intent):
        intent['targets'] = intent['scope']['sessions']
        key = self._fence(intent)
        active = self.manager.current_active(intent['owner']) if self.manager is not None else None
        if active is not None and any(s == active.session_id for s, _ in intent['scope']['sessions']):
            if not active.broadcast.content_pending:
                active.broadcast.content_epoch += 1
            active.broadcast.content_pending = True
            active.broadcast.content_pending_moment_ids.update(
                mid for sid, mid in intent['scope']['moments'] if sid == active.session_id)
        return key

    def _withdraw(self, intent):
        scope = intent['scope']
        owner = intent['owner']
        entries = frozenset((s, e) for s, e, _, _, _ in scope['entries'])
        moments = frozenset(tuple(p) for p in scope['moments'])
        self.history.dialogue.withdraw_content('profile:' + owner,
            request_hashes=frozenset(scope['request_hashes']), turn_ids=frozenset(scope['turn_ids']),
            entries=entries, moments=moments)
        from .dj_response import invalidate_private_speech_sources
        for session, moment in moments:
            invalidate_private_speech_sources(self.history.hass, session_id=session, moment_ids={moment}) if self.history.hass is not None else None
        if entries and self.history.hass is not None:
            invalidate_private_speech_sources(self.history.hass, entry_ids={e for _, e in entries})
        media = getattr(self.persistence, 'session_image_owner', None)
        if media is not None:
            media.withdraw_content(owner, entries=entries, moments=moments)
        apply_runtime_content(self.manager, owner, scope)

    def _content_release(self, intent):
        owned = (intent['owner'], intent['operation_id']) in self._barriers
        self._release(intent)
        if owned:
            finish_runtime_content(self.manager, intent['owner'], intent['scope'])

    async def _settle_content(self, intent, *, snapshot=None, authorize=None):
        owner = intent['owner']
        self._content_fence(intent)
        async def index(messages):
            result, _ = await self.journal.async_scope_index(owner, messages, frozenset())
            return result, frozenset()
        async def factory(messages, mapping):
            scope, plan, basis = await self._build(owner, snapshot['selector'], messages, mapping)
            if scope_digest([scope, plan, basis]) != snapshot['digest']:
                raise HistoryDeletionError('content_delete_scope_conflict')
            intent['scope'], intent['store_plan'] = scope, plan
            return plan
        async def prepare(plan):
            if snapshot is not None:
                await self.journal.async_reserve_content(owner=owner, operation_id=intent['operation_id'],
                    binding=intent['binding'], digest=intent['digest'], scope=intent['scope'],
                    store_plan=plan, authorize=authorize)
            else:
                await self.journal.async_refresh_fences()
            # Durable intent precedes any body, grant or Runtime mutation.
            self._withdraw(intent)
            return intent['store_plan']
        await self.history.async_erase_archived_sessions(owner, frozenset(), entry_index=index,
            prepare_intent=prepare, pending_client_ids=(), individual=True,
            plan_factory=factory if snapshot is not None else None,
            recovery_plan=intent['store_plan'] if snapshot is None else None,
            targeted_withdraw=lambda plan: self._withdraw(intent))
        self._withdraw(intent)  # Recover any incomplete same-process RAM handling.
        await self.journal.async_store_erased(owner, intent['operation_id'], intent['binding'])
        receipt = await self.journal.async_complete_content(intent, authorize=authorize)
        self._content_release(intent)
        return receipt

    async def async_execute(self, *, owner, operation_id, binding, digest, snapshot, authorize):
        async with self._lock, runtime_lock(self.manager):
            authorize()
            previous = await self.journal.async_content_operation(owner, operation_id, binding, digest=digest)
            authorize()
            if previous is not None:
                if previous['state'] == 'completed':
                    self._content_release(previous)
                    return previous['receipt']
                return await self._settle_content(previous, authorize=authorize)
            if snapshot is None:
                raise HistoryDeletionError('content_delete_scope_conflict')
            intent = {'owner': owner, 'operation_id': operation_id, 'binding': binding, 'digest': digest,
                      'scope': deepcopy(snapshot['scope']), 'store_plan': deepcopy(snapshot['plan'])}
            try:
                return await self._settle_content(intent, snapshot=snapshot, authorize=authorize)
            except BaseException:
                pending = await self.journal.async_pending_content()
                if not any(i['owner'] == owner and i['operation_id'] == operation_id for i in pending):
                    await self.history.async_settle_rejected_deletion((owner, operation_id))
                    self._content_release(intent)
                raise

    async def async_recover(self):
        async with self._lock, runtime_lock(self.manager):
            pending = await self.journal.async_pending_content()
            for intent in pending:
                self._content_fence(intent)
            for intent in pending:
                await self._settle_content(intent)
            return len(pending)


def content_deletion_coordinator(hass):
    from .history_deletion import deletion_coordinator
    from .session_runtime import session_runtime_manager
    archive = deletion_coordinator(hass)
    domain = hass.data.setdefault('djconnect', {})
    current = domain.get('content_deletion_coordinator')
    if current is None or current.persistence is not archive.persistence:
        current = ContentDeletionCoordinator(archive.persistence, archive.history, manager=session_runtime_manager(hass))
        domain['content_deletion_coordinator'] = current
    return current
