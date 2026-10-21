"""Cross-store synthetic crash boundaries, unrelated data and replay authority."""
from copy import deepcopy
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from tests import test_history_deletion_journal as fixture_module
from tests.test_history_deletion_journal import identifier
from tests.test_archived_session_erasure_safety import Store
from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
from custom_components.djconnect.history_deletion import ArchiveDeletionCoordinator
from custom_components.djconnect.persistence.service import PersistenceService
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider
from custom_components.djconnect.persistence.history_deletion import HistoryDeletionRepository
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository


class CrossStoreDeletionTests(IsolatedAsyncioTestCase):
    asyncSetUp = fixture_module.HistoryDeletionJournalTests.asyncSetUp
    asyncTearDown = fixture_module.HistoryDeletionJournalTests.asyncTearDown
    raw_header_exists = fixture_module.HistoryDeletionJournalTests.raw_header_exists

    async def setup_store(self):
        self.store = Store()
        self.chat = AskDJHistoryManager(store=self.store)
        for key, session in [('erased', 'old'), ('independent', 'live'), ('foreign', 'foreign')]:
            await self.chat.async_append_exchange(
                'profile:other' if key == 'foreign' else 'profile:p',
                {'client_message_id': key, 'text': 'Synthetic ' + key},
                {'success': True, 'text': 'Synthetic answer ' + key},
                session_turn={'turn_id': key, 'context': {'session_id': session}})
        self.coordinator = ArchiveDeletionCoordinator(self.service, self.chat)
        self.args['authorize'] = lambda: True

    async def restart(self):
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.history = HistoricalProjectionRepository(self.service)
        self.journal = HistoryDeletionRepository(self.service)
        self.chat = AskDJHistoryManager(store=self.store)
        self.coordinator = ArchiveDeletionCoordinator(self.service, self.chat)

    async def test_both_stores_erased_before_receipt_other_owner_and_live_preserved(self):
        await self.setup_store()
        foreign = deepcopy((await self.chat.async_history('profile:other'))['messages'])
        receipt = await self.coordinator.async_delete(**self.args)
        self.assertTrue(receipt['deleted'])
        self.assertFalse(await self.raw_header_exists('old'))
        self.assertTrue(await self.raw_header_exists('kept'))
        self.assertTrue(await self.raw_header_exists('live'))
        self.assertTrue(await self.raw_header_exists('foreign'))
        self.assertNotIn('Synthetic answer erased', str(self.store.data))
        self.assertIn('Synthetic answer independent', str(self.store.data))
        self.assertEqual((await self.chat.async_history('profile:other'))['messages'], foreign)
        self.assertEqual(await self.coordinator.async_delete(**self.args), receipt)
        self.assertEqual(self.service.history_retention_writes, 0)

    async def test_lost_store_ack_survives_restart_and_recovery_beyond_transport_expiry(self):
        await self.setup_store()
        self.store.raise_after_save = True
        with self.assertRaises(OSError):
            await self.coordinator.async_delete(**self.args)
        self.assertTrue(await self.raw_header_exists('old'))
        self.assertIsNone(await self.history.async_session_record('old'))
        with self.assertRaisesRegex(RuntimeError, 'history_delete_outcome_unknown'):
            await self.chat.async_history('profile:p')
        self.store.raise_after_save = False
        await self.restart()
        self.assertEqual(await self.coordinator.async_recover(), 1)
        self.assertFalse(await self.raw_header_exists('old'))
        self.assertNotIn('Synthetic answer erased', str(await self.chat.async_history('profile:p')))
        self.assertEqual(await self.coordinator.async_recover(), 0)

    async def test_sql_failure_after_store_ack_never_returns_success_or_reopens_reads(self):
        await self.setup_store()
        with patch.object(self.coordinator.journal, 'async_complete', side_effect=OSError('synthetic SQL failure')):
            with self.assertRaises(OSError):
                await self.coordinator.async_delete(**self.args)
        self.assertNotIn('Synthetic answer erased', str(self.store.data))
        self.assertTrue(await self.raw_header_exists('old'))
        self.assertEqual((await self.journal.async_pending())[0]['state'], 'store_erased')
        with self.assertRaisesRegex(RuntimeError, 'history_delete_outcome_unknown'):
            await self.chat.async_history('profile:p')
        await self.coordinator.async_recover()
        self.assertFalse(await self.raw_header_exists('old'))
        self.assertIn('Synthetic answer independent', str(await self.chat.async_history('profile:p')))

    async def test_wrong_owner_never_revokes_media_or_mutates_store(self):
        await self.setup_store()
        before = deepcopy(self.store.data)
        invalidated = []
        self.coordinator._begin = invalidated.append
        with self.assertRaisesRegex(ValueError, 'history_unavailable'):
            await self.coordinator.async_delete(**{**self.args, 'targets': (('foreign', 0),)})
        self.assertEqual(self.store.data, before)
        self.assertEqual(invalidated, [])
        self.assertEqual(await self.journal.async_pending(), [])

    async def test_expired_admission_reopens_only_after_proving_no_intent(self):
        await self.setup_store()
        before = deepcopy(self.store.data)
        with self.assertRaisesRegex(ValueError, 'history_delete_operation_expired'):
            await self.coordinator.async_delete(**{**self.args, 'operation_id': identifier(self.now - 300_001)})
        self.assertEqual(self.store.data, before)
        self.assertIn('Synthetic answer erased', str(await self.chat.async_history('profile:p')))
        self.assertEqual(self.service.history_retention_writes, 0)

    async def test_completed_replay_requires_current_authority(self):
        await self.setup_store()
        await self.coordinator.async_delete(**self.args)
        with self.assertRaises(PermissionError):
            await self.coordinator.async_delete(**{**self.args, 'authorize': lambda: False})

    async def test_dependent_conversation_keeps_stable_unavailable_ids_and_unrelated_text(self):
        import json
        from custom_components.djconnect.historical_projection_query import HistoricalProjectionQueryService
        await self.setup_store()
        await self.chat.async_append_exchange('profile:p',
            {'client_message_id': 'dependent', 'text': 'Synthetic copied original question'},
            {'success': True, 'text': 'Synthetic copied old answer'},
            session_turn={'turn_id': 'dependent-turn', 'context': {'session_id': 'kept',
                'selected_entry': {'session_id': 'old', 'entry_id': 'source-entry'}}})
        messages = (await self.chat.async_history('profile:p'))['messages']
        dependent = [m for m in messages if m.get('client_message_id') == 'dependent']
        def admitted_fixture(tx):
            for number, message in enumerate(dependent, 1):
                tx.execute('INSERT INTO djconnect_session_entries '
                    '(entry_id,session_id,owner_profile_id,entry_order,kind,reference_id,body,occurred_at,retained_until) '
                    'VALUES (?,?,?,?,?,?,?,?,?)',
                    ('dependent-' + str(number), 'kept', 'p', number,
                     'conversation_user' if message['role'] == 'user' else 'conversation_dj', message['id'],
                     json.dumps({'history_scope': 'profile:p', 'message_id': message['id'], 'turn_id': 'dependent-turn'}),
                     '2026-10-21T07:00:00+00:00', '2027-01-01T07:00:00+00:00'))
        await self.service.async_in_transaction(admitted_fixture)
        before = await self.history.async_session_record('kept')
        await self.coordinator.async_delete(**self.args)
        rows = await self.history.async_entry_records('p', 'kept')
        self.assertEqual({r['entry_id'] for r in rows}, {'dependent-1', 'dependent-2'})
        query = HistoricalProjectionQueryService(self.history, self.chat)
        for row in rows:
            projected = await query._project_entry('p', row)
            self.assertEqual(projected['state'], 'source_withdrawn')
            self.assertEqual(projected['text'], '')
            self.assertNotIn('session_speech', projected)
        self.assertGreater((await self.history.async_session_record('kept'))['revision'], before['revision'])
        values = (await self.chat.async_history('profile:p'))['messages']
        self.assertNotIn('Synthetic copied', str(values))
        self.assertIn('Synthetic answer independent', str(values))
