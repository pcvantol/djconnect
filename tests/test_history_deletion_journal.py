"""Disposable SQLite deletion-intent recovery and receipt boundaries."""
from pathlib import Path
import tempfile
import unittest
from uuid import UUID

from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()

from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.sessions import (  # noqa: E402
    PersistentSessionRepository, ACTIVE, ENDED,
)
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.persistence.history_deletion import (  # noqa: E402
    HistoryDeletionRepository, HistoryDeletionError,
)


def identifier(ms, sequence=1):
    return str(UUID(int=(ms << 80) | (7 << 76) | (2 << 62) | sequence))


class HistoryDeletionJournalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'synthetic.sqlite3'
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.sessions = PersistentSessionRepository(self.service)
        self.history = HistoricalProjectionRepository(self.service)
        self.journal = HistoryDeletionRepository(self.service)
        self.now = 1_800_000_000_000
        self.models = {}
        for owner, name, terminal in [('p', 'old', True), ('p', 'kept', True),
                                      ('p', 'live', False), ('other', 'foreign', True)]:
            await self.sessions.async_create(owner, session_id=name)
            await self.sessions.async_transition(owner, name, ACTIVE)
            if terminal:
                self.models[name] = await self.sessions.async_transition(owner, name, ENDED)
        row = await self.history.async_session_record('old')
        self.args = dict(owner='p', operation_id=identifier(self.now), binding='b' * 64,
                         digest='d' * 64, targets=(('old', row['revision']),), now_ms=self.now)

    async def asyncTearDown(self):
        await self.service.async_close()
        self.tmp.cleanup()

    async def raw_header_exists(self, session_id):
        return await self.service.async_in_transaction(lambda tx: bool(tx.fetchone(
            'SELECT 1 FROM djconnect_persistent_sessions WHERE session_id=?', (session_id,))))

    async def test_pending_intent_survives_restart_and_transport_expiry(self):
        result = await self.journal.async_reserve(**self.args)
        self.assertEqual(result['state'], 'pending')
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        recovered = HistoryDeletionRepository(self.service)
        pending = await recovered.async_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['targets'], [['old', self.args['targets'][0][1]]])
        self.assertTrue(await recovered.async_is_fenced('p', 'old'))
        # A receipt deadline never abandons an unfinished erasure fence.
        with self.assertRaisesRegex(HistoryDeletionError, 'history_delete_operation_expired'):
            await recovered.async_reserve(**{**self.args, 'now_ms': self.now + 300_001})
        self.assertTrue(await recovered.async_is_fenced('p', 'old'))
        self.assertFalse(await recovered.async_is_fenced('other', 'old'))

    async def test_exact_duplicate_and_conflicting_operation(self):
        first = await self.journal.async_reserve(**self.args)
        self.assertEqual(await self.journal.async_reserve(**self.args), first)
        for delta in ({'binding': 'a' * 64}, {'digest': 'c' * 64}):
            with self.assertRaisesRegex(HistoryDeletionError, 'history_delete_operation_conflict'):
                await self.journal.async_reserve(**{**self.args, **delta})
        self.assertIsNone(await self.journal.async_receipt('other', self.args['operation_id'], 'b' * 64))

    async def test_all_targets_validated_before_any_fence(self):
        for target in ('foreign', 'missing', 'live'):
            with self.assertRaises(HistoryDeletionError):
                await self.journal.async_reserve(**{**self.args, 'targets': (*self.args['targets'], (target, 1))})
            self.assertEqual(await self.journal.async_pending(), [])
            self.assertFalse(await self.journal.async_is_fenced('p', 'old'))
        with self.assertRaisesRegex(HistoryDeletionError, 'history_revision_conflict'):
            await self.journal.async_reserve(**{**self.args, 'targets': (('old', 999),)})

    async def test_uncertain_store_stage_cannot_produce_a_success_receipt(self):
        await self.journal.async_reserve(**self.args)
        with self.assertRaisesRegex(HistoryDeletionError, 'history_delete_outcome_unknown'):
            await self.journal.async_complete('p', self.args['operation_id'], 'b' * 64, lambda tx: None)
        self.assertIsNone(await self.journal.async_receipt('p', self.args['operation_id'], 'b' * 64))
        self.assertTrue(await self.journal.async_is_fenced('p', 'old'))

    async def test_sql_effect_and_completion_receipt_commit_or_rollback_together(self):
        await self.journal.async_reserve(**self.args)
        await self.journal.async_store_erased('p', self.args['operation_id'], 'b' * 64)
        def fail(tx):
            tx.execute("DELETE FROM djconnect_persistent_sessions WHERE session_id='old'")
            raise OSError('synthetic transaction failure')
        with self.assertRaises(OSError):
            await self.journal.async_complete('p', self.args['operation_id'], 'b' * 64, fail)
        self.assertTrue(await self.raw_header_exists('old'))
        self.assertIsNone(await self.journal.async_receipt('p', self.args['operation_id'], 'b' * 64))
        def remove(tx):
            tx.execute("DELETE FROM djconnect_persistent_sessions WHERE session_id='old'")
        receipt = await self.journal.async_complete('p', self.args['operation_id'], 'b' * 64, remove)
        self.assertIsNone(await self.history.async_session_record('old'))
        self.assertTrue(receipt['deleted'])
        self.assertEqual(receipt['deleted_session_ids'], ['old'])
        self.assertIsNotNone(await self.history.async_session_record('kept'))
        self.assertIsNotNone(await self.history.async_session_record('live'))
        self.assertIsNotNone(await self.history.async_session_record('foreign'))
        self.assertFalse(await self.journal.async_is_fenced('p', 'old'))
        self.assertEqual(await self.journal.async_receipt('p', self.args['operation_id'], 'b' * 64), receipt)
        self.assertEqual(await self.journal.async_reserve(**self.args), {'state': 'completed', 'receipt': receipt})

    async def test_new_targets_cannot_overlap_an_unfinished_intent(self):
        await self.journal.async_reserve(**self.args)
        with self.assertRaisesRegex(HistoryDeletionError, 'history_delete_outcome_unknown'):
            await self.journal.async_reserve(**{**self.args, 'operation_id': identifier(self.now, 2)})

    async def test_journal_never_evicts_unfinished_intents_for_capacity(self):
        await self.journal.async_reserve(**self.args)
        kept = await self.history.async_session_record('kept')
        limited = HistoryDeletionRepository(self.service, max_records=1)
        with self.assertRaisesRegex(HistoryDeletionError, 'history_delete_capacity'):
            await limited.async_reserve(**{**self.args, 'operation_id': identifier(self.now, 2),
                                          'targets': (('kept', kept['revision']),)})
        self.assertTrue(await self.journal.async_is_fenced('p', 'old'))
        self.assertFalse(await self.journal.async_is_fenced('p', 'kept'))

    async def test_expiry_cannot_be_renewed_by_wall_clock_rollback_after_a_rejection(self):
        await self.journal.async_reserve(**self.args)
        for now in (self.now + 300_001, self.now):
            with self.assertRaisesRegex(HistoryDeletionError, 'history_delete_operation_expired'):
                await self.journal.async_reserve(**{**self.args, 'now_ms': now})
        self.assertTrue(await self.journal.async_is_fenced('p', 'old'))

    async def test_monotonic_elapsed_time_expires_before_any_wall_clock_expiry_observation(self):
        elapsed = [0.0]
        journal = HistoryDeletionRepository(self.service, monotonic=lambda: elapsed[0])
        await journal.async_reserve(**self.args)
        # No intervening request observes wall expiry. The wall clock is moved
        # back before the next duplicate, but real elapsed time still wins.
        elapsed[0] = 301.0
        with self.assertRaisesRegex(HistoryDeletionError, 'history_delete_operation_expired'):
            await journal.async_reserve(**{**self.args, 'now_ms': self.now + 1000})
        self.assertTrue(await journal.async_is_fenced('p', 'old'))

    async def test_commit_time_authority_loss_rolls_back_effect_receipt_and_fence_retirement(self):
        await self.journal.async_reserve(**self.args)
        await self.journal.async_store_erased('p', self.args['operation_id'], 'b' * 64)
        current = [True]
        def revoked_during_staging(tx):
            tx.execute("DELETE FROM djconnect_persistent_sessions WHERE session_id='old'")
            current[0] = False
        with self.assertRaises(PermissionError):
            await self.journal.async_complete(
                'p', self.args['operation_id'], 'b' * 64, revoked_during_staging,
                authorize=lambda: current[0], finalize_authorize=lambda: current[0])
        self.assertTrue(await self.raw_header_exists('old'))
        self.assertTrue(await self.journal.async_is_fenced('p', 'old'))
        self.assertIsNone(await self.journal.async_receipt('p', self.args['operation_id'], 'b' * 64))

    async def test_expired_completed_receipts_reclaimed_without_evicting_pending_recovery(self):
        limited = HistoryDeletionRepository(self.service, max_records=1)
        await limited.async_reserve(**self.args)
        await limited.async_store_erased('p', self.args['operation_id'], 'b' * 64)
        await limited.async_complete('p', self.args['operation_id'], 'b' * 64,
                                     lambda tx: tx.execute("DELETE FROM djconnect_persistent_sessions WHERE session_id='old'"))
        kept = await self.history.async_session_record('kept')
        later = self.now + 301_000
        await limited.async_reserve(**{**self.args, 'now_ms': later,
                                      'operation_id': identifier(later),
                                      'targets': (('kept', kept['revision']),)})
        self.assertEqual([r['targets'][0][0] for r in await limited.async_pending()], ['kept'])
        self.assertFalse(await limited.async_is_fenced('p', 'old'))
        self.assertTrue(await limited.async_is_fenced('p', 'kept'))

    async def test_noop_sql_eraser_cannot_retire_fence_or_claim_success(self):
        await self.journal.async_reserve(**self.args)
        await self.journal.async_store_erased('p', self.args['operation_id'], 'b' * 64)
        with self.assertRaisesRegex(HistoryDeletionError, 'history_delete_outcome_unknown'):
            await self.journal.async_complete('p', self.args['operation_id'], 'b' * 64, lambda tx: None)
        self.assertTrue(await self.raw_header_exists('old'))
        self.assertTrue(await self.journal.async_is_fenced('p', 'old'))
        self.assertIsNone(await self.journal.async_receipt('p', self.args['operation_id'], 'b' * 64))

    async def test_pending_fence_hides_current_and_legacy_readers_without_hiding_unrelated_session(self):
        session = self.models['old']
        await self.history.async_project_session(session)
        legacy = await self.history.async_get_session_for_originating_id('old')
        self.assertIsNotNone(legacy)
        await self.journal.async_reserve(**self.args)
        self.assertTrue(await self.raw_header_exists('old'))
        self.assertIsNone(await self.history.async_session_record('old'))
        self.assertIsNone(await self.history.async_get_session(legacy.historical_session_id))
        self.assertIsNone(await self.history.async_get_session_for_originating_id('old'))
        self.assertNotIn('old', {s['session_id'] for s in await self.history.async_session_records('p')})
        self.assertNotIn('old', {s.originating_session_id for s in await self.history.async_list_sessions_for_owner('p')})
        self.assertIsNotNone(await self.history.async_session_record('kept'))
        self.assertIsNone(await self.history.async_project_session(session))

    async def test_bounded_store_identity_join_uses_owner_message_index(self):
        from custom_components.djconnect.persistence.history_deletion import SCOPE_INDEX_SQL
        plan = await self.service.async_in_transaction(lambda tx: tx.fetchall(
            'EXPLAIN QUERY PLAN ' + SCOPE_INDEX_SQL, ('p', '["synthetic-message"]')))
        self.assertTrue(any('USING INDEX djconnect_session_entry_message' in row[3] for row in plan), plan)
