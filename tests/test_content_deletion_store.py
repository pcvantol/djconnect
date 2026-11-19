"""Selected exchange/attempt withdrawal preserves unrelated Store and dialogue owners."""
from copy import deepcopy
import unittest

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()
from tests.test_archived_session_erasure_safety import Store  # noqa: E402
from custom_components.djconnect.ask_dj_history import AskDJHistoryManager, _request_hash  # noqa: E402


class ContentDeletionStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = Store()
        self.history = AskDJHistoryManager(store=self.store)
        self.saved = {}
        for key, sources in [('selected', []), ('dependent', ['selected']), ('independent', [])]:
            self.saved[key] = await self.history.async_append_exchange(
                'profile:p', {'client_message_id': key, 'text': 'Synthetic question '+key},
                {'success': True, 'text': 'Synthetic answer '+key},
                session_turn={'turn_id': 'turn-'+key, 'context': {},
                              'dependency_request_hashes': [_request_hash('profile:p', x) for x in sources]})

    async def erase(self, role='assistant_message', recovery_plan=None):
        selected = self.saved['selected'][role]['id']
        async def prepare(plan):
            self.plan = deepcopy(plan)
            return plan
        def withdraw(plan):
            self.history.dialogue.withdraw_content('profile:p', request_hashes=set(plan['retry_hashes']),
                turn_ids={'turn-selected', 'turn-dependent'})
        return await self.history.async_erase_archived_sessions(
            'p', frozenset(), message_ids=frozenset({selected}), pending_client_ids=('selected',),
            entry_index={}, prepare_intent=prepare, individual=True,
            targeted_withdraw=withdraw, recovery_plan=recovery_plan)

    async def test_either_role_removes_exact_complete_standalone_exchange(self):
        for role in ('assistant_message', 'user_message'):
            # Restore an independent disposable owner for each role selection.
            if role == 'user_message':
                await self.asyncSetUp()
            before = await self.history.async_scope_revision('profile:p')
            await self.erase(role)
            messages = (await self.history.async_history('profile:p'))['messages']
            self.assertNotIn('selected', {m['client_message_id'] for m in messages})
            independent = [m for m in messages if m['client_message_id']=='independent']
            self.assertEqual(len(independent), 2)
            self.assertTrue(all('Synthetic' in m['text'] for m in independent))
            dependent = [m for m in messages if m['client_message_id']=='dependent']
            self.assertEqual([m['id'] for m in dependent], [m['id'] for m in self.saved['dependent']['messages']])
            self.assertTrue(all(m['content_state']=='source_withdrawn' and m['text']=='' for m in dependent))
            self.assertEqual(await self.history.async_scope_revision('profile:p'), before)

    async def test_unrelated_pending_request_not_fenced_and_effect_receipt_preserved(self):
        self.history.register_session_request('profile:p', 'unrelated-inflight')
        await self.history.async_reserve_dialogue_effect('profile:p', 'selected', 'd'*64)
        effect = deepcopy(self.history.data['users']['profile:p']['dialogue_effect_receipts'])
        await self.erase()
        self.assertFalse(await self.history.async_session_request_cleared('profile:p', 'unrelated-inflight'))
        self.assertEqual(self.history.data['users']['profile:p']['dialogue_effect_receipts'], effect)
        with self.assertRaisesRegex(ValueError, 'conversation_history_changed'):
            await self.history.async_append_exchange('profile:p', {'client_message_id': 'selected', 'text': 'Late retry'},
                {'success': True, 'text': 'Must never resurrect'}, session_turn=None)

    async def test_unknown_store_ack_recovers_original_plan_not_new_scope(self):
        self.store.raise_after_save = True
        with self.assertRaises(OSError):
            await self.erase()
        captured = deepcopy(self.plan)
        with self.assertRaises(RuntimeError):
            await self.history.async_history('profile:p')
        self.store.raise_after_save = False
        await self.erase(recovery_plan=captured)
        self.assertNotIn('selected', {m['client_message_id'] for m in (await self.history.async_history('profile:p'))['messages']})

    async def test_pre_admission_attempt_creates_original_request_fence_without_erasing_other_turns(self):
        before = deepcopy((await self.history.async_history('profile:p'))['messages'])
        async def prepare(plan):
            self.assertEqual(plan['remove_message_ids'], [])
            return plan
        await self.history.async_erase_archived_sessions('p', frozenset(), entry_index={},
            pending_client_ids=('not-yet-arrived',), prepare_intent=prepare, individual=True,
            targeted_withdraw=lambda plan: None)
        self.assertEqual((await self.history.async_history('profile:p'))['messages'], before)
        self.assertTrue(await self.history.async_session_request_cleared('profile:p', 'not-yet-arrived'))

    async def test_targeted_dialogue_window_and_replay_withdrawal_preserves_other_thread(self):
        state = self.history.dialogue
        target = state.frame('profile:p', 'target', 'g')
        safe = state.frame('profile:p', 'safe', 'g')
        target.messages = [{'role':'assistant','text':'Synthetic selected','_client_id':'selected'},
                           {'role':'assistant','text':'Independent same-window','_client_id':'independent'}]
        target.local_turns = deepcopy(target.messages)
        safe.messages = [{'role':'assistant','text':'Other thread','_client_id':'other-thread'}]
        target.current_client_id = 'selected'
        target.subjects = [{'name':'Synthetic selected subject'}]
        target.catalogue_replays['selected'] = ('d', object(), False, 10, 2000)
        target.catalogue_replays['independent'] = ('i', object(), False, 12, 2000)
        original = target.catalogue_replays['independent']
        target.read_context_revision = 7
        await self.erase()
        self.assertEqual([m['text'] for m in target.messages], ['Independent same-window'])
        self.assertEqual(target.read_context_revision, 7)
        self.assertIsNone(target.catalogue_replays['selected'][1])
        self.assertEqual(target.catalogue_replays['independent'], original)
        self.assertEqual(safe.messages[0]['text'], 'Other thread')

    async def test_durable_selected_moment_lineage_survives_empty_dialogue_and_store_reload(self):
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager, archive_erasure_plan
        first = await self.history.async_append_exchange('profile:p',
            {'client_message_id': 'moment-reader', 'text': 'Synthetic explicit Moment question'},
            {'success': True, 'text': 'Synthetic selected Moment answer'},
            session_turn={'turn_id': 'moment-reader-turn', 'context': {'session_id': 'live',
                'selected_moment': {'session_id': 'live', 'moment_id': 'moment-selected'}}})
        second = await self.history.async_append_exchange('profile:p',
            {'client_message_id': 'moment-followup', 'text': 'Synthetic followup'},
            {'success': True, 'text': 'Synthetic derived answer'},
            session_turn={'turn_id': 'moment-followup-turn', 'context': {},
                'dependency_request_hashes': [_request_hash('profile:p', 'moment-reader')]})
        reloaded = AskDJHistoryManager(store=self.store)
        rows = (await reloaded.async_history('profile:p'))['messages']
        self.assertEqual(reloaded.dialogue.owners, {})
        plan = archive_erasure_plan('p', rows, frozenset(), individual=True,
            initial_moments=frozenset({('live', 'moment-selected')}))
        self.assertEqual(set(plan['redact_message_ids']), {m['id'] for m in first['messages'] + second['messages']})
        async def intent(proposed):
            return plan
        await reloaded.async_erase_archived_sessions('p', frozenset(), entry_index={},
            prepare_intent=intent, individual=True, targeted_withdraw=lambda _: None,
            recovery_plan=plan)
        after = (await reloaded.async_history('profile:p'))['messages']
        self.assertTrue(all(m['text'] == '' for m in after if m['id'] in plan['redact_message_ids']))
        self.assertTrue(all('Synthetic' in m['text'] for m in after if m['id'] not in plan['redact_message_ids']))
