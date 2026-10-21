"""Synthetic actual Store + SQLite recovery of one server-defined exchange."""
from copy import deepcopy
from pathlib import Path
import tempfile
import time
import unittest

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()
from tests.test_archived_session_erasure_safety import Store  # noqa: E402
from tests.test_history_deletion_journal import identifier  # noqa: E402
from custom_components.djconnect.ask_dj_history import AskDJHistoryManager, _request_hash  # noqa: E402
from custom_components.djconnect.content_deletion import ContentDeletionCoordinator  # noqa: E402
from custom_components.djconnect.persistence.content_deletion import ContentDeletionRepository, scope_digest  # noqa: E402
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository, ACTIVE  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402


class ContentDeletionCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'synthetic.sqlite3'
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.store = Store()
        self.history = AskDJHistoryManager(store=self.store)
        self.repo = HistoricalProjectionRepository(self.service)
        self.sessions = PersistentSessionRepository(self.service)
        await self.sessions.async_create('p', session_id='live')
        await self.sessions.async_transition('p', 'live', ACTIVE)
        self.saved = {}
        for name, refs in [('selected', []), ('dependent', ['selected']), ('independent', [])]:
            result = await self.history.async_append_exchange('profile:p',
                {'client_message_id':name,'text':'Synthetic question '+name},
                {'success':True,'text':'Synthetic answer '+name},
                session_turn={'turn_id':'turn-'+name,'context':{'session_id':'live'},
                              'dependency_request_hashes':[_request_hash('profile:p', x) for x in refs]})
            entries = [{'kind':'conversation_'+m['role'] if m['role']=='user' else 'conversation_dj',
                        'reference_id':name+'-'+m['role'],'body':{'message_id':m['id']}}
                       for m in result['messages']]
            result['entry_ids'] = await self.repo.async_append_entries('p','live',entries)
            self.saved[name] = result
        self.coordinator = ContentDeletionCoordinator(self.service, self.history)
        self.selector = {'kind':'message','session_id':'live','target_id':self.saved['selected']['user_message']['id']}
        self.op = identifier(int(time.time()*1000))
        self.digest = scope_digest({'confirmation_id':'synthetic-token'})

    async def asyncTearDown(self):
        await self.service.async_close()
        self.tmp.cleanup()

    async def preview(self, selector=None):
        return await self.coordinator.async_preview('p',selector or self.selector,authorize=lambda:True)

    async def execute(self, snapshot):
        return await self.coordinator.async_execute(owner='p',operation_id=self.op,binding='b'*64,
            digest=self.digest,snapshot=snapshot,authorize=lambda:True)

    async def test_one_exchange_durable_receipt_preserves_live_header_and_independent_rows(self):
        snapshot = await self.preview()
        self.assertEqual(snapshot['scope']['unit']['kind'],'exchange')
        self.assertEqual(len(snapshot['plan']['remove_message_ids']),2)
        self.assertEqual(len(snapshot['plan']['redact_message_ids']),2)
        result = await self.execute(snapshot)
        self.assertTrue(result['deleted'])
        self.assertEqual((await self.repo.async_session_record('live'))['lifecycle_status'],ACTIVE)
        for entry in self.saved['selected']['entry_ids']:
            self.assertIsNone(await self.repo.async_entry_record('p','live',entry))
        for entry in self.saved['independent']['entry_ids']:
            self.assertIsNotNone(await self.repo.async_entry_record('p','live',entry))
        messages = (await self.history.async_history('profile:p'))['messages']
        self.assertNotIn('selected',{m['client_message_id'] for m in messages})
        self.assertTrue(all(m.get('content_state')=='source_withdrawn' for m in messages if m['client_message_id']=='dependent'))
        self.assertEqual(await self.execute(None),result)

    async def test_changed_scope_refuses_before_any_store_effect(self):
        snapshot = await self.preview()
        before = deepcopy(self.store.data)
        await self.repo.async_append_entries('p','live',[{'kind':'playback_observed','reference_id':'new-observation','body':{'item_id':'new'}}])
        with self.assertRaisesRegex(ValueError,'content_delete_scope_conflict'):
            await self.execute(snapshot)
        self.assertEqual(self.store.data,before)
        self.assertEqual(await self.coordinator.journal.async_pending_content(),[])
        self.assertEqual(len((await self.history.async_history('profile:p'))['messages']),6)

    async def test_ack_loss_keeps_closed_and_new_process_recovery_uses_original_scope(self):
        snapshot = await self.preview()
        self.store.raise_after_save = True
        with self.assertRaises(OSError):
            await self.execute(snapshot)
        with self.assertRaises(RuntimeError):
            await self.history.async_history('profile:p')
        self.assertEqual(len(await self.coordinator.journal.async_pending_content()),1)
        await self.service.async_close()
        self.service = PersistenceService(self.path,SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.store.raise_after_save = False
        history = AskDJHistoryManager(store=self.store)
        recovered = ContentDeletionCoordinator(self.service,history)
        self.assertEqual(await recovered.async_recover(),1)
        self.assertEqual(await recovered.journal.async_pending_content(),[])
        self.assertNotIn('selected',{m['client_message_id'] for m in (await history.async_history('profile:p'))['messages']})
        self.assertTrue(await ContentDeletionRepository(self.service).async_request_deleted('p','selected'))

    async def test_pre_admission_request_is_fenced_without_touching_independent_history(self):
        selector = {'kind':'request','session_id':'','target_id':'not-yet-arrived'}
        snapshot = await self.preview(selector)
        before = deepcopy((await self.history.async_history('profile:p'))['messages'])
        receipt = await self.execute(snapshot)
        self.assertEqual(receipt['unit']['kind'],'attempt')
        self.assertEqual((await self.history.async_history('profile:p'))['messages'],before)
        self.assertTrue(await self.history.async_session_request_cleared('profile:p','not-yet-arrived'))

    async def test_cache_read_failure_after_intent_same_process_recovery_restores_both_fences(self):
        from unittest.mock import patch
        snapshot = await self.preview()
        with patch.object(self.coordinator.journal, 'async_refresh_fences', side_effect=OSError('synthetic lost cache acknowledgement')):
            with self.assertRaises(OSError):
                await self.execute(snapshot)
        self.assertEqual(len(await self.coordinator.journal.async_pending_content()), 1)
        self.assertEqual(await self.coordinator.async_recover(), 1)
        self.assertIn(_request_hash('profile:p', 'selected'), self.service.content_request_fences['p'])
        self.assertIn(('p', 'live', self.saved['selected']['entry_ids'][0]),
            self.service.content_source_fences['entries'])
        # SQL final fences outlive a future general Store clear/cache replacement.
        self.history._data['users']['profile:p']['cleared_request_hashes'] = []
        self.assertTrue(await self.coordinator.journal.async_request_deleted('p', 'selected'))
        self.assertEqual(await self.coordinator.journal.async_pending_content(), [])

    async def test_archived_transition_dependency_chain_survives_process_reload(self):
        import json
        await self.repo.async_append_entries('p', 'live', [
            {'kind': 'dj_moment', 'reference_id': mid,
             'body': {'moment_id': mid, 'text': 'Synthetic '+mid, 'dependency_moment_ids': deps}}
            for mid, deps in [('root', []), ('transition', ['root']),
                              ('transition-child', ['transition']), ('independent-moment', [])]])
        # New SQLite/Store owners: no live Moment engine or dialogue graph.
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.repo = HistoricalProjectionRepository(self.service)
        self.coordinator = ContentDeletionCoordinator(self.service, AskDJHistoryManager(store=self.store))
        snapshot = await self.preview({'kind': 'moment', 'session_id': 'live', 'target_id': 'root'})
        self.assertEqual({m for _, m in snapshot['scope']['moments']}, {'root', 'transition', 'transition-child'})
        await self.execute(snapshot)
        rows = await self.repo.async_entry_records('p', 'live')
        moments = {row['reference_id']: json.loads(row['body']) for row in rows if row['kind'] in {'dj_moment', 'dj_publication'}}
        self.assertNotIn('root', moments)
        self.assertEqual(moments['transition']['content_state'], 'unavailable')
        self.assertIsNone(moments['transition']['text'])
        self.assertEqual(moments['transition-child']['content_state'], 'unavailable')
        self.assertEqual(moments['independent-moment']['text'], 'Synthetic independent-moment')
        late = {'kind': 'dj_moment', 'reference_id': 'late-transition',
                'body': {'moment_id': 'late-transition', 'dependency_moment_ids': ['root']}}
        self.assertFalse(await self.repo.async_accept_moment('p', 'live', 'late-transition', late))
