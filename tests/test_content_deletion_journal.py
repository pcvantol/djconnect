"""Actual disposable SQL: single contribution erasure is never whole-Session erasure."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()
from tests.test_history_deletion_journal import identifier  # noqa: E402
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository, ACTIVE  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.persistence.history_deletion import HistoryDeletionRepository, HistoryDeletionError  # noqa: E402
from custom_components.djconnect.persistence.content_deletion import ContentDeletionRepository  # noqa: E402
from custom_components.djconnect.ask_dj_history import _request_hash  # noqa: E402


class ContentDeletionJournalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'synthetic.sqlite3'
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.sessions = PersistentSessionRepository(self.service)
        self.history = HistoricalProjectionRepository(self.service)
        self.journal = ContentDeletionRepository(self.service)
        await self.sessions.async_create('p', session_id='live')
        await self.sessions.async_transition('p', 'live', ACTIVE)
        self.entry = (await self.history.async_append_entries('p', 'live', [
            {'kind': 'dj_moment', 'reference_id': 'moment-one', 'body': {'text': 'Synthetic selected contribution'}},
        ]))[0]
        self.kept = (await self.history.async_append_entries('p', 'live', [
            {'kind': 'playback_observed', 'reference_id': 'observation', 'body': {'item_id': 'independent-playback'}},
        ]))[0]
        revision = (await self.history.async_session_record('live'))['revision']
        self.scope = {'unit': {'kind': 'moment', 'session_id': 'live', 'target_id': 'moment-one'},
                      'sessions': [['live', revision]],
                      'entries': [['live', self.entry, 'dj_moment', 'moment-one', 'remove']],
                      'moments': [['live', 'moment-one']], 'turn_ids': [],
                      'request_hashes': [_request_hash('profile:p', 'original-request')]}
        self.now = 1_800_000_000_000
        self.args = dict(owner='p', operation_id=identifier(self.now), binding='b'*64,
                         digest='d'*64, scope=self.scope, now_ms=self.now, authorize=lambda: True,
                         store_plan={'remove_message_ids': [], 'redact_message_ids': [],
                                     'dependent_session_ids': [], 'retry_hashes': self.scope['request_hashes']})

    async def asyncTearDown(self):
        await self.service.async_close()
        self.tmp.cleanup()

    async def count(self, table):
        statements = {'fences': 'SELECT count(*) FROM djconnect_content_tombstones',
                      'intents': 'SELECT count(*) FROM djconnect_history_deletions'}
        return await self.service.async_in_transaction(lambda tx: tx.fetchone(statements[table])[0])

    async def complete(self):
        await self.journal.async_reserve_content(**self.args)
        intent = (await self.journal.async_pending_content())[0]
        await self.journal.async_store_erased('p', self.args['operation_id'], 'b'*64)
        return await self.journal.async_complete_content(intent)

    async def test_selected_live_entry_removed_header_playback_and_order_preserved(self):
        result = await self.complete()
        self.assertTrue(result['deleted'])
        self.assertFalse(result['music_playback_undone'])
        self.assertIsNone(await self.history.async_entry_record('p', 'live', self.entry))
        kept = await self.history.async_entry_record('p', 'live', self.kept)
        self.assertEqual(kept['order'], 2)
        self.assertEqual((await self.history.async_session_record('live'))['lifecycle_status'], ACTIVE)
        self.assertFalse(await self.journal.async_is_fenced('p', 'live'))
        self.assertTrue(await self.journal.async_request_deleted('p', 'original-request'))
        self.assertFalse(await self.journal.async_request_deleted('other', 'original-request'))

    async def test_late_projection_cannot_resurrect_after_completed_receipt(self):
        await self.complete()
        with self.assertRaisesRegex(PermissionError, 'content_deleted'):
            await self.history.async_append_entries('p', 'live', [
                {'kind': 'dj_moment', 'reference_id': 'moment-one', 'body': {'text': 'Late synthetic copy'}}])
        self.assertFalse(await self.history.async_accept_moment('p', 'live', 'moment-one'))
        self.assertIsNone(await self.history.async_project_moment(
            session_id='live', moment_id='moment-one', owner_profile_id='p', moment_type='track',
            rendered_text='Late synthetic legacy copy', presentation_metadata='{}', ordering=1, created_at='2026-10-21T00:00:00Z'))

    async def test_no_receipt_before_store_ack_and_pending_modes_do_not_cross(self):
        await self.journal.async_reserve_content(**self.args)
        intent = (await self.journal.async_pending_content())[0]
        self.assertEqual(await HistoryDeletionRepository(self.service).async_pending(), [])
        with self.assertRaisesRegex(HistoryDeletionError, 'content_delete_outcome_unknown'):
            await self.journal.async_complete_content(intent)
        self.assertTrue(await self.journal.async_is_fenced('p', 'live'))

    async def test_restart_and_expiry_retain_recovery_and_original_request_fence(self):
        await self.journal.async_reserve_content(**self.args)
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        recovered = ContentDeletionRepository(self.service)
        self.assertEqual(len(await recovered.async_pending_content()), 1)
        with self.assertRaisesRegex(HistoryDeletionError, 'content_delete_operation_expired'):
            await recovered.async_content_operation('p', self.args['operation_id'], 'b'*64, now_ms=self.now+300_001)
        self.assertTrue(await recovered.async_is_fenced('p', 'live'))
        self.assertTrue(await recovered.async_request_deleted('p', 'original-request'))

    async def test_all_revision_and_owner_checks_precede_any_tombstone(self):
        for owner, revision in [('other', self.scope['sessions'][0][1]), ('p', 999)]:
            scope = deepcopy(self.scope)
            scope['sessions'][0][1] = revision
            with self.assertRaises(HistoryDeletionError):
                await self.journal.async_reserve_content(**{**self.args, 'owner': owner, 'scope': scope})
            self.assertEqual(await self.count('fences'), 0)
            self.assertEqual(await self.count('intents'), 0)

    async def test_sql_failure_rolls_back_erasure_and_receipt_together(self):
        await self.journal.async_reserve_content(**self.args)
        intent = (await self.journal.async_pending_content())[0]
        await self.journal.async_store_erased('p', self.args['operation_id'], 'b'*64)
        await self.service.async_in_transaction(lambda tx: tx.execute(
            "CREATE TRIGGER synthetic_delete_failure BEFORE DELETE ON djconnect_session_entries BEGIN SELECT RAISE(ABORT,'synthetic failure'); END"))
        with self.assertRaises(Exception):
            await self.journal.async_complete_content(intent)
        operation = await self.journal.async_content_operation('p', self.args['operation_id'], 'b'*64, now_ms=self.now)
        self.assertEqual(operation['state'], 'store_erased')
        self.assertIsNone(operation['receipt'])
        self.assertTrue(await self.journal.async_is_fenced('p', 'live'))

    async def test_playback_record_is_never_an_individual_erase_unit(self):
        scope = deepcopy(self.scope)
        scope['entries'] = [['live', self.kept, 'playback_observed', 'observation', 'remove']]
        with self.assertRaisesRegex(HistoryDeletionError, 'invalid_content_delete_request'):
            await self.journal.async_reserve_content(**{**self.args, 'scope': scope})
        self.assertEqual(await self.count('fences'), 0)
