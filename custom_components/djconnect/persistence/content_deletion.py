"""Identifier-only individual erasure through the existing SQLite intent owner."""
from __future__ import annotations

import hashlib
import json
import re

from .history_deletion import HistoryDeletionError, HistoryDeletionRepository, MAX_RECORDS
from ..transport_operations import FUTURE_SKEW_MS, LIFETIME_MS, operation_created_ms

MAX_UNITS = 1000
MAX_TOMBSTONES = 10_000
_ID = re.compile(r'[A-Za-z0-9_.:\-]{1,200}\Z')
_HASH = re.compile(r'[a-f0-9]{64}\Z')


def scope_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def request_deleted_now(hass, owner, client_id):
    """Synchronous final fence populated by bootstrap and durable reservation."""
    from ..ask_dj_history import _request_hash
    domain = getattr(hass, 'data', {}).get('djconnect', {})
    service = domain.get('persistence_service')
    return _request_hash('profile:' + owner, client_id) in getattr(service, 'content_request_fences', {}).get(owner, set())


def validate_scope(scope):
    if (not isinstance(scope, dict) or set(scope) != {
            'unit', 'sessions', 'entries', 'moments', 'turn_ids', 'request_hashes'}):
        raise HistoryDeletionError('invalid_content_delete_request')
    unit = scope['unit']
    if (not isinstance(unit, dict) or set(unit) != {'kind', 'session_id', 'target_id'}
            or unit['kind'] not in {'moment', 'exchange', 'attempt'}
            or not isinstance(unit['session_id'], str)
            or (unit['session_id'] and not _ID.fullmatch(unit['session_id']))
            or not isinstance(unit['target_id'], str) or not _ID.fullmatch(unit['target_id'])):
        raise HistoryDeletionError('invalid_content_delete_request')
    shapes = {'sessions': 2, 'entries': 5, 'moments': 2}
    for key, size in shapes.items():
        rows = scope[key]
        if type(rows) is not list or len(rows) > MAX_UNITS or len({json.dumps(r) for r in rows}) != len(rows):
            raise HistoryDeletionError('content_delete_capacity')
        for row in rows:
            if type(row) is not list or len(row) != size:
                raise HistoryDeletionError('invalid_content_delete_request')
            strings = row[:-1] if key == 'sessions' else row
            if any(not isinstance(v, str) or not _ID.fullmatch(v) for v in strings):
                raise HistoryDeletionError('invalid_content_delete_request')
            if key == 'sessions' and (type(row[1]) is not int or row[1] < 0):
                raise HistoryDeletionError('invalid_content_delete_request')
            if key == 'entries' and (row[4] not in {'remove', 'unavailable'} or row[2] not in {'dj_moment', 'dj_publication', 'dj_silence', 'conversation_user', 'conversation_dj'}):
                raise HistoryDeletionError('invalid_content_delete_request')
    for key in ('turn_ids', 'request_hashes'):
        values = scope[key]
        if (type(values) is not list or len(values) > MAX_UNITS or len(set(values)) != len(values)
                or any(not isinstance(v, str) or not (_HASH if key == 'request_hashes' else _ID).fullmatch(v) for v in values)):
            raise HistoryDeletionError('invalid_content_delete_request')
    sessions = {s for s, _ in scope['sessions']}
    if len(sessions) != len(scope['sessions']):
        raise HistoryDeletionError('invalid_content_delete_request')
    if (any(r[0] not in sessions for r in scope['entries'])
            or any(s not in sessions for s, _ in scope['moments'])):
        raise HistoryDeletionError('invalid_content_delete_request')


class ContentDeletionRepository(HistoryDeletionRepository):
    """Share intent capacity, original clock and pending Session fences with archives."""

    @staticmethod
    def _content_row(tx, owner, operation_id, binding):
        row = HistoryDeletionRepository._row(tx, owner, operation_id, binding)
        if row:
            kind = tx.fetchone('SELECT operation_kind,content_scope FROM djconnect_history_deletions '
                               'WHERE owner_profile_id=? AND operation_id=?', (owner, operation_id))
            if kind[0] != 'content':
                raise HistoryDeletionError('content_delete_operation_conflict')
            return row, json.loads(kind[1])
        return None

    async def async_reserve_content(self, *, owner, operation_id, binding, digest, scope,
                                    store_plan, authorize, now_ms=None):
        validate_scope(scope)
        from ..ask_dj_history import validate_archive_erasure_plan
        validate_archive_erasure_plan(store_plan)
        if set(scope['request_hashes']) != set(store_plan['retry_hashes']):
            raise HistoryDeletionError('invalid_content_delete_request')
        if not isinstance(digest, str) or not _HASH.fullmatch(digest):
            raise HistoryDeletionError('invalid_content_delete_request')
        created = operation_created_ms(operation_id)
        encoded = json.dumps(scope, sort_keys=True, separators=(',', ':'))
        tombstones = {(s, k, ref, eid) for s, eid, k, ref, _ in scope['entries']}
        tombstones.update((s, 'moment', ref, '') for s, ref in scope['moments'])

        def admit(tx):
            now = self._now(tx, now_ms)
            # All typed rejections precede intent/fence/tombstone insertion.
            def validate():
                if created > now + FUTURE_SKEW_MS or now > created + LIFETIME_MS:
                    raise HistoryDeletionError('content_delete_operation_expired')
                old = self._content_row(tx, owner, operation_id, binding)
                if old:
                    if old[0][1] != digest:
                        raise HistoryDeletionError('content_delete_operation_conflict')
                    return old
                count = tx.fetchone("SELECT count(*) FROM djconnect_history_deletions WHERE state!='completed' OR expires_ms>=?", (now,))[0]
                if count >= self._max_records:
                    raise HistoryDeletionError('content_delete_capacity')
                if (tx.fetchone('SELECT count(*) FROM djconnect_content_tombstones')[0] + len(tombstones) > MAX_TOMBSTONES
                        or tx.fetchone('SELECT count(*) FROM djconnect_content_request_fences WHERE owner_profile_id=?', (owner,))[0]
                        + len(scope['request_hashes']) > MAX_UNITS
                        or tx.fetchone('SELECT count(*) FROM djconnect_content_request_fences')[0] + len(scope['request_hashes']) > MAX_TOMBSTONES):
                    raise HistoryDeletionError('content_delete_capacity')
                for session, revision in scope['sessions']:
                    row = tx.fetchone('SELECT owner_profile_id,history_revision FROM djconnect_persistent_sessions WHERE session_id=?', (session,))
                    if not row or row[0] != owner:
                        raise HistoryDeletionError('content_unavailable')
                    if row[1] != revision:
                        raise HistoryDeletionError('content_delete_scope_conflict')
                    if tx.fetchone('SELECT 1 FROM djconnect_history_deletion_targets WHERE owner_profile_id=? AND session_id=?', (owner, session)):
                        raise HistoryDeletionError('content_delete_outcome_unknown')
                for session, entry, kind, reference, _ in scope['entries']:
                    row = tx.fetchone('SELECT kind,reference_id FROM djconnect_session_entries WHERE owner_profile_id=? AND session_id=? AND entry_id=?', (owner, session, entry))
                    if row != (kind, reference):
                        raise HistoryDeletionError('content_delete_scope_conflict')
                return None
            try:
                old = validate()
            except HistoryDeletionError as error:
                return error  # Persist high-water time even on expired admission.
            if old:
                return {'state': old[0][3]}
            tx.execute("DELETE FROM djconnect_history_deletions WHERE state='completed' AND expires_ms<?", (now,))
            tx.execute(
                'INSERT INTO djconnect_history_deletions '
                '(owner_profile_id,operation_id,binding,digest,targets,state,created_ms,expires_ms,store_plan,operation_kind,content_scope) '
                "VALUES (?,?,?,?,?,'pending',?,?,?,'content',?)",
                (owner, operation_id, binding, digest, json.dumps(scope['sessions']), created, created + LIFETIME_MS,
                 json.dumps(store_plan, sort_keys=True), encoded))
            for session, _ in scope['sessions']:
                tx.execute('INSERT INTO djconnect_history_deletion_targets VALUES (?,?,?)', (owner, session, operation_id))
            for session, kind, reference, entry in sorted(tombstones):
                tx.execute('INSERT OR IGNORE INTO djconnect_content_tombstones VALUES (?,?,?,?,?,?)',
                           (owner, session, kind, reference, entry, now))
            for request_hash in scope['request_hashes']:
                tx.execute('INSERT OR IGNORE INTO djconnect_content_request_fences VALUES (?,?,?)', (owner, request_hash, now))
            return {'state': 'pending'}
        result = await self._async_in_transaction(admit, authorize=authorize, finalize_authorize=authorize)
        if isinstance(result, HistoryDeletionError):
            raise result
        await self.async_refresh_fences()
        return result

    async def async_refresh_fences(self):
        """Publish both bounded durable caches together before reopening a pending owner."""
        requests = await self.async_request_fences()
        sources = await self.async_source_fences()
        self._persistence.content_request_fences = requests
        self._persistence.content_source_fences = sources

    async def async_source_fences(self):
        def read(tx):
            rows = tx.fetchall('SELECT owner_profile_id,session_id,kind,reference_id,entry_id '
                               'FROM djconnect_content_tombstones LIMIT ?', (MAX_TOMBSTONES + 1,))
            if len(rows) > MAX_TOMBSTONES:
                raise HistoryDeletionError('content_delete_capacity')
            return {'entries': {(o, s, e) for o, s, _, _, e in rows if e},
                    'moments': {(o, s, ref) for o, s, kind, ref, _ in rows if kind == 'moment'}}
        return await self._async_in_transaction(read)

    async def async_request_fences(self):
        def read(tx):
            rows = tx.fetchall('SELECT owner_profile_id,request_hash FROM djconnect_content_request_fences LIMIT ?', (MAX_TOMBSTONES + 1,))
            if len(rows) > MAX_TOMBSTONES:
                raise HistoryDeletionError('content_delete_capacity')
            result = {}
            for owner, key in rows:
                result.setdefault(owner, set()).add(key)
            return result
        return await self._async_in_transaction(read)

    async def async_content_operation(self, owner, operation_id, binding, *, digest=None, now_ms=None):
        def read(tx):
            record = self._content_row(tx, owner, operation_id, binding)
            if record is None:
                return None
            row, scope = record
            now = self._now(tx, now_ms)
            if now > row[5]:
                return HistoryDeletionError('content_delete_operation_expired')
            if digest is not None and digest != row[1]:
                return HistoryDeletionError('content_delete_operation_conflict')
            return {'owner': owner, 'operation_id': operation_id, 'binding': binding,
                    'scope': scope, 'state': row[3], 'store_plan': json.loads(row[7]),
                    'receipt': json.loads(row[6]) if row[6] else None}
        result = await self._async_in_transaction(read)
        if isinstance(result, HistoryDeletionError):
            raise result
        return result

    async def async_content_status(self, owner, operation_id, binding, digest):
        """Read only: no recovery, erasure, expiry extension or clock-table update."""
        import time
        created = operation_created_ms(operation_id)
        def read(tx):
            stored = tx.fetchone('SELECT high_water_ms FROM djconnect_history_deletion_clock WHERE singleton=1')[0]
            advanced = (int(self._anchor_wall + max(0, self._monotonic() - self._anchor_mono) * 1000)
                        if self._anchor_wall is not None else 0)
            observed = max(int(time.time() * 1000), stored)
            if self._anchor_wall is None or observed > advanced:
                self._anchor_wall, self._anchor_mono = observed, self._monotonic()
            now = max(observed, advanced)
            record = self._content_row(tx, owner, operation_id, binding)
            if created > now + FUTURE_SKEW_MS:
                raise HistoryDeletionError('invalid_content_delete_request')
            if now > created + LIFETIME_MS:
                return {'state': 'expired_unknown', 'definitive': False}
            if record is None:
                return {'state': 'unknown', 'definitive': False}
            row, scope = record
            if row[1] != digest:
                raise HistoryDeletionError('content_delete_operation_conflict')
            if row[3] == 'completed':
                return {'state': 'completed', 'definitive': True, 'receipt': json.loads(row[6])}
            return {'state': 'pending', 'definitive': False, 'unit': scope['unit']}
        return await self._async_in_transaction(read)

    async def async_pending_content(self):
        def read(tx):
            rows = tx.fetchall("SELECT owner_profile_id,operation_id,binding,content_scope,state,store_plan FROM djconnect_history_deletions WHERE state!='completed' AND operation_kind='content' ORDER BY created_ms LIMIT ?", (MAX_RECORDS,))
            return [{'owner': o, 'operation_id': i, 'binding': b, 'scope': json.loads(s),
                     'state': state, 'store_plan': json.loads(plan)} for o, i, b, s, state, plan in rows]
        return await self._async_in_transaction(read)

    async def async_request_deleted(self, owner, client_id):
        from ..ask_dj_history import _request_hash
        key = _request_hash('profile:' + owner, client_id)
        return await self._async_in_transaction(lambda tx: bool(tx.fetchone(
            'SELECT 1 FROM djconnect_content_request_fences WHERE owner_profile_id=? AND request_hash=?', (owner, key))))

    async def async_complete_content(self, intent, *, authorize=None):
        owner, operation, binding = (intent[k] for k in ('owner', 'operation_id', 'binding'))
        def complete(tx):
            current = self._content_row(tx, owner, operation, binding)
            if current is None:
                raise HistoryDeletionError('content_unavailable')
            row, scope = current
            if row[3] == 'completed':
                return json.loads(row[6])
            if row[3] != 'store_erased':
                raise HistoryDeletionError('content_delete_outcome_unknown')
            for session, entry, kind, reference, mode in scope['entries']:
                if mode == 'remove':
                    tx.execute('DELETE FROM djconnect_session_entries WHERE owner_profile_id=? AND session_id=? AND entry_id=?', (owner, session, entry))
                    if tx.fetchone('SELECT 1 FROM djconnect_session_entries WHERE owner_profile_id=? AND session_id=? AND entry_id=?', (owner, session, entry)):
                        raise HistoryDeletionError('content_delete_outcome_unknown')
                elif kind not in {'conversation_user', 'conversation_dj'}:
                    tx.execute("UPDATE djconnect_session_entries SET kind='dj_publication',body=? WHERE owner_profile_id=? AND session_id=? AND entry_id=?",
                               (json.dumps({'moment_id': reference, 'content_state': 'unavailable', 'unavailable_reason': 'owner_deleted_dependency', 'text': None, 'speech_available': False}), owner, session, entry))
                if mode == 'remove':
                    tx.execute('DELETE FROM djconnect_session_acceptances WHERE session_id=? AND entry_id=?', (session, entry))
            for session, moment in scope['moments']:
                tx.execute('DELETE FROM djconnect_historical_moments WHERE owner_profile_id=? AND originating_session_id=? AND originating_moment_id=?', (owner, session, moment))
            for session, _ in scope['sessions']:
                tx.execute('DELETE FROM djconnect_session_summaries WHERE session_id=?', (session,))
                tx.execute('UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE owner_profile_id=? AND session_id=?', (owner, session))
            receipt = {'success': True, 'schema_version': 1, 'operation_id': operation,
                       'owner_profile_id': owner, 'state': 'completed', 'deleted': True,
                       'request_digest': row[1],
                       'unit': scope['unit'], 'affected_entries': [{'session_id': s, 'entry_id': e, 'disposition': mode} for s, e, _, _, mode in scope['entries']],
                       'removed_message_ids': intent['store_plan']['remove_message_ids'],
                       'unavailable_message_ids': intent['store_plan']['redact_message_ids'],
                       'music_playback_undone': False}
            tx.execute("UPDATE djconnect_history_deletions SET state='completed',receipt=? WHERE owner_profile_id=? AND operation_id=?", (json.dumps(receipt, sort_keys=True), owner, operation))
            tx.execute('DELETE FROM djconnect_history_deletion_targets WHERE owner_profile_id=? AND operation_id=?', (owner, operation))
            return receipt
        return await self._async_in_transaction(complete, authorize=authorize, finalize_authorize=authorize)
