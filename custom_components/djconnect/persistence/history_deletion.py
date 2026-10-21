"""Durable private deletion intents; transport expiry never abandons recovery.

This repository does not authorize a user request, erase HA Store, register an
endpoint or advertise a capability. The application coordinator must establish
owner/device authority and public revision admission, fence reads/writers, then
settle Store and SQL through their existing owners before acknowledging success.
"""
from __future__ import annotations

import json
import re
import time

from .service import PersistenceRepository
from ..transport_operations import FUTURE_SKEW_MS, LIFETIME_MS, OperationError, operation_created_ms

MAX_RECORDS = 1024
MAX_TARGETS = 10_000
_HASH = re.compile(r"[0-9a-f]{64}\Z")


SCOPE_INDEX_SQL = (
    "SELECT json_extract(body,'$.message_id'),session_id,entry_id "
    "FROM djconnect_session_entries WHERE owner_profile_id=? "
    "AND kind IN ('conversation_user','conversation_dj') AND json_valid(body) "
    "AND json_extract(body,'$.message_id') IN (SELECT value FROM json_each(?))"
)


class HistoryDeletionError(ValueError):
    """Content-free private coordinator failure."""


def _identifier(value):
    return isinstance(value, str) and 0 < len(value) <= 200


class HistoryDeletionRepository(PersistenceRepository):
    """One persistence transaction owner, bounded receipts, durable pending fences."""

    def __init__(self, persistence, *, max_records=MAX_RECORDS, monotonic=None):
        super().__init__(persistence)
        if type(max_records) is not int or not 1 <= max_records <= MAX_RECORDS:
            raise ValueError('invalid_history_delete_capacity')
        self._max_records = max_records
        self._monotonic = monotonic or time.monotonic
        self._anchor_wall = None
        self._anchor_mono = self._monotonic()

    def _now(self, tx, now_ms=None):
        now = int(time.time() * 1000) if now_ms is None else now_ms
        if type(now) is not int or now < 0:
            raise HistoryDeletionError('invalid_history_delete_request')
        stored = tx.fetchone('SELECT high_water_ms FROM djconnect_history_deletion_clock WHERE singleton=1')
        observed = max(now, stored[0])
        monotonic = self._monotonic()
        advanced = (int(self._anchor_wall + max(0, monotonic - self._anchor_mono) * 1000)
                    if self._anchor_wall is not None else observed)
        if self._anchor_wall is None or observed > advanced:
            self._anchor_wall, self._anchor_mono = observed, monotonic
        now = max(observed, advanced)
        tx.execute('UPDATE djconnect_history_deletion_clock SET high_water_ms=? WHERE singleton=1', (now,))
        return now

    @staticmethod
    def _row(tx, owner, operation_id, binding):
        if not _identifier(owner) or not _identifier(operation_id) or not isinstance(binding, str) or not _HASH.fullmatch(binding):
            raise HistoryDeletionError('invalid_history_delete_request')
        row = tx.fetchone(
            'SELECT binding,digest,targets,state,created_ms,expires_ms,receipt,store_plan '
            'FROM djconnect_history_deletions WHERE owner_profile_id=? AND operation_id=?',
            (owner, operation_id),
        )
        if row and row[0] != binding:
            raise HistoryDeletionError('history_delete_operation_conflict')
        return row

    async def async_reserve(self, *, owner, operation_id, binding, digest, targets, now_ms=None,
                            store_plan=None, authorize=None, finalize_authorize=None):
        """Atomically validate the complete captured SQL set and install its intent."""
        if (not _identifier(owner) or not isinstance(binding, str) or not _HASH.fullmatch(binding)
                or not isinstance(digest, str) or not _HASH.fullmatch(digest)
                or type(targets) is not tuple or not 1 <= len(targets) <= MAX_TARGETS
                or any(type(t) is not tuple or len(t) != 2 or not _identifier(t[0])
                       or type(t[1]) is not int or t[1] < 0 for t in targets)
                or len({t[0] for t in targets}) != len(targets)):
            raise HistoryDeletionError('invalid_history_delete_request')
        try:
            created_ms = operation_created_ms(operation_id)
        except OperationError:
            raise HistoryDeletionError('invalid_history_delete_request') from None
        encoded = json.dumps(sorted(targets), separators=(',', ':'))
        if store_plan is not None:
            from ..ask_dj_history import validate_archive_erasure_plan
            validate_archive_erasure_plan(store_plan)
        encoded_store = json.dumps(store_plan or {}, sort_keys=True, separators=(',', ':'))

        def reserve(tx):
            now = self._now(tx, now_ms)
            if created_ms > now + FUTURE_SKEW_MS or now > created_ms + LIFETIME_MS:
                raise HistoryDeletionError('history_delete_operation_expired')
            row = self._row(tx, owner, operation_id, binding)
            if row:
                if row[1] != digest or row[2] != encoded:
                    raise HistoryDeletionError('history_delete_operation_conflict')
                return ({'state': 'completed', 'receipt': json.loads(row[6])}
                        if row[3] == 'completed' else {'state': row[3]})
            # Expired completed receipts may leave the transport journal; an
            # unfinished intent/fence is NEVER evicted, regardless of age.
            tx.execute("DELETE FROM djconnect_history_deletions WHERE state='completed' AND expires_ms<?", (now,))
            count = tx.fetchone('SELECT COUNT(*) FROM djconnect_history_deletions')[0]
            if count >= self._max_records:
                raise HistoryDeletionError('history_delete_capacity')
            for session_id, revision in sorted(targets):
                session = tx.fetchone(
                    'SELECT owner_profile_id,lifecycle_status,history_revision '
                    'FROM djconnect_persistent_sessions WHERE session_id=?', (session_id,),
                )
                if not session or session[0] != owner:
                    raise HistoryDeletionError('history_unavailable')
                if session[1] not in {'ENDED', 'INTERRUPTED'}:
                    raise HistoryDeletionError('session_not_archived')
                if session[2] != revision:
                    raise HistoryDeletionError('history_revision_conflict')
                if tx.fetchone(
                    'SELECT 1 FROM djconnect_history_deletion_targets '
                    'WHERE owner_profile_id=? AND session_id=?', (owner, session_id),
                ):
                    raise HistoryDeletionError('history_delete_outcome_unknown')
            tx.execute(
                'INSERT INTO djconnect_history_deletions '
                '(owner_profile_id,operation_id,binding,digest,targets,state,created_ms,expires_ms,store_plan) '
                "VALUES (?,?,?,?,?,'pending',?,?,?)",
                (owner, operation_id, binding, digest, encoded, created_ms, created_ms + LIFETIME_MS, encoded_store),
            )
            for session_id, _ in targets:
                tx.execute('INSERT INTO djconnect_history_deletion_targets VALUES (?,?,?)',
                           (owner, session_id, operation_id))
            return {'state': 'pending'}

        def commit_clock_on_rejection(tx):
            # Typed admission failures happen before intent/fence insertion.
            # Preserve observed time even for a rejected expired operation;
            # otherwise a later wall-clock rollback could renew its lifetime.
            try:
                return reserve(tx)
            except HistoryDeletionError as error:
                return error

        result = await self._async_in_transaction(commit_clock_on_rejection, authorize=authorize,
                                                  finalize_authorize=finalize_authorize)
        if isinstance(result, HistoryDeletionError):
            raise result
        return result

    async def async_pending(self):
        """Return only opaque recovery identifiers, never stored conversation bodies."""
        def read(tx):
            rows = tx.fetchall(
                "SELECT owner_profile_id,operation_id,binding,targets,state,store_plan FROM "
                "djconnect_history_deletions WHERE state!='completed' ORDER BY created_ms LIMIT ?",
                (MAX_RECORDS,),
            )
            return [{'owner': r[0], 'operation_id': r[1], 'binding': r[2],
                     'targets': json.loads(r[3]), 'state': r[4], 'store_plan': json.loads(r[5])} for r in rows]
        return await self._async_in_transaction(read)

    async def async_lookup(self, owner, operation_id, binding, digest, *, now_ms=None):
        """Read exact private resume scope without renewing its transport lifetime."""
        def read(tx):
            row = self._row(tx, owner, operation_id, binding)
            if not row:
                return None
            now = self._now(tx, now_ms)
            if now > row[5]:
                return HistoryDeletionError('history_delete_operation_expired')
            if row[1] != digest:
                return HistoryDeletionError('history_delete_operation_conflict')
            return {'state': row[3], 'targets': json.loads(row[2]),
                    'store_plan': json.loads(row[7]),
                    'receipt': json.loads(row[6]) if row[6] else None}
        result = await self._async_in_transaction(read)
        if isinstance(result, HistoryDeletionError):
            raise result
        return result

    async def async_terminal_records(self, owner):
        """One complete bounded server capture, independent of pages or filters."""
        def read(tx):
            rows = tx.fetchall(
                "SELECT session_id,owner_profile_id,lifecycle_status,created_at,started_at,"
                "ended_at,interrupted_at,history_revision,history_enabled "
                "FROM djconnect_persistent_sessions WHERE owner_profile_id=? "
                "AND lifecycle_status IN ('ENDED','INTERRUPTED') "
                "ORDER BY session_id LIMIT ?", (owner, MAX_TARGETS + 1))
            if len(rows) > MAX_TARGETS:
                raise HistoryDeletionError('history_delete_capacity')
            keys = ('session_id', 'owner_profile_id', 'lifecycle_status', 'created_at',
                    'started_at', 'ended_at', 'interrupted_at', 'revision', 'history_enabled')
            return [dict(zip(keys, row)) for row in rows]
        return await self._async_in_transaction(read)

    async def async_validate_targets(self, owner, targets, *, authorize):
        """Read-only admission before any process-local media invalidation."""
        def read(tx):
            for session_id, revision in targets:
                row = tx.fetchone('SELECT owner_profile_id,lifecycle_status,history_revision '
                                  'FROM djconnect_persistent_sessions WHERE session_id=?', (session_id,))
                if not row or row[0] != owner:
                    raise HistoryDeletionError('history_unavailable')
                if row[1] not in {'ENDED', 'INTERRUPTED'}:
                    raise HistoryDeletionError('session_not_archived')
                if row[2] != revision:
                    raise HistoryDeletionError('history_revision_conflict')
        await self._async_in_transaction(read, authorize=authorize, finalize_authorize=authorize)

    async def async_scope_index(self, owner, messages, session_ids):
        """Resolve only the bounded current Store identities through the SQL owner."""
        ids = [m['id'] for m in messages]
        def read(tx):
            rows = tx.fetchall(SCOPE_INDEX_SQL, (owner, json.dumps(ids)))
            index = {}
            for message_id, session_id, entry_id in rows:
                if message_id in index:
                    raise HistoryDeletionError('history_delete_outcome_unknown')
                index[message_id] = (session_id, entry_id)
            return index, frozenset(m for m, (s, _) in index.items() if s in session_ids)
        return await self._async_in_transaction(read)

    @staticmethod
    def erase_sql(tx, owner, session_ids, store_plan):
        """Existing transaction owner erases captured bodies and advances survivors."""
        for session_id in session_ids:
            for table, column in (
                ('djconnect_historical_moments', 'originating_session_id'),
                ('djconnect_historical_sessions', 'originating_session_id'),
                ('djconnect_session_entries', 'session_id'),
                ('djconnect_session_acceptances', 'session_id'),
                ('djconnect_session_summaries', 'session_id'),
                ('djconnect_session_dj_settings', 'session_id'),
                ('djconnect_persistent_sessions', 'session_id'),
            ):
                tx.execute(f'DELETE FROM {table} WHERE {column}=? AND EXISTS ('
                           'SELECT 1 FROM djconnect_persistent_sessions AS owned '
                           'WHERE owned.session_id=? AND owned.owner_profile_id=?)',
                           (session_id, session_id, owner))
        for session_id in store_plan['dependent_session_ids']:
            tx.execute('UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 '
                       'WHERE owner_profile_id=? AND session_id=?', (owner, session_id))

    async def async_is_fenced(self, owner, session_id):
        return await self._async_in_transaction(lambda tx: bool(tx.fetchone(
            'SELECT 1 FROM djconnect_history_deletion_targets WHERE owner_profile_id=? AND session_id=?',
            (owner, session_id),
        )))

    async def async_store_erased(self, owner, operation_id, binding):
        """Coordinator calls only after acknowledged existing Store-owner erasure."""
        def mark(tx):
            row = self._row(tx, owner, operation_id, binding)
            if not row:
                raise HistoryDeletionError('history_unavailable')
            if row[3] == 'pending':
                tx.execute("UPDATE djconnect_history_deletions SET state='store_erased' "
                           'WHERE owner_profile_id=? AND operation_id=?', (owner, operation_id))
        await self._async_in_transaction(mark)

    async def async_complete(self, owner, operation_id, binding, erase_sql, *,
                             authorize=None, finalize_authorize=None):
        """SQL effect, target-fence retirement and completion receipt are ONE commit."""
        def complete(tx):
            row = self._row(tx, owner, operation_id, binding)
            if not row:
                raise HistoryDeletionError('history_unavailable')
            if row[3] == 'completed':
                return json.loads(row[6])
            if row[3] != 'store_erased':
                raise HistoryDeletionError('history_delete_outcome_unknown')
            erase_sql(tx)
            # A callback returning normally is not proof of erasure. Refuse a
            # successful receipt while any captured SQL content/header remains.
            for session_id, _ in json.loads(row[2]):
                for table, column in (
                    ('djconnect_persistent_sessions', 'session_id'),
                    ('djconnect_session_entries', 'session_id'),
                    ('djconnect_session_summaries', 'session_id'),
                    ('djconnect_session_acceptances', 'session_id'),
                    ('djconnect_session_dj_settings', 'session_id'),
                    ('djconnect_historical_sessions', 'originating_session_id'),
                    ('djconnect_historical_moments', 'originating_session_id'),
                ):
                    if tx.fetchone(f'SELECT 1 FROM {table} WHERE {column}=? LIMIT 1', (session_id,)):
                        raise HistoryDeletionError('history_delete_outcome_unknown')
            receipt = {'success': True, 'schema_version': 1, 'operation_id': operation_id,
                       'owner_profile_id': owner, 'deleted': True,
                       'deleted_session_ids': [t[0] for t in json.loads(row[2])]}
            tx.execute("UPDATE djconnect_history_deletions SET state='completed',receipt=? "
                       'WHERE owner_profile_id=? AND operation_id=?',
                       (json.dumps(receipt, separators=(',', ':')), owner, operation_id))
            tx.execute('DELETE FROM djconnect_history_deletion_targets WHERE owner_profile_id=? AND operation_id=?',
                       (owner, operation_id))
            return receipt
        return await self._async_in_transaction(complete, authorize=authorize,
                                                finalize_authorize=finalize_authorize)

    async def async_receipt(self, owner, operation_id, binding, *, now_ms=None):
        """Caller must freshly authorize owner/device before returning any receipt."""
        def read(tx):
            row = self._row(tx, owner, operation_id, binding)
            if not row or row[3] != 'completed' or self._now(tx, now_ms) > row[5]:
                return None
            return json.loads(row[6])
        return await self._async_in_transaction(read)
