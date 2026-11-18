"""Synthetic Store erasure plans preserve unrelated turns and stable unavailable IDs."""
from copy import deepcopy
import unittest

from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()

from custom_components.djconnect.ask_dj_history import (  # noqa: E402
    AskDJHistoryManager, archive_erasure_plan,
)
from tests.test_archived_session_erasure_safety import Store  # noqa: E402


class ArchiveErasurePlanTests(unittest.TestCase):
    def test_transitive_context_becomes_unavailable_without_deleting_other_exchange_ids(self):
        messages = [
            {'id': 'q1', 'exchange_id': 'e1', 'role': 'user', 'text': 'Synthetic old',
             'client_message_id': 'old-request', 'session_turn': {'context': {'session_id': 'old'}}},
            {'id': 'a1', 'exchange_id': 'e1', 'role': 'assistant', 'text': 'Synthetic private old',
             'client_message_id': 'old-request', 'session_turn': {'context': {'session_id': 'old'}}},
            {'id': 'q2', 'exchange_id': 'e2', 'role': 'user', 'text': 'Quote Synthetic private old',
             'client_message_id': 'dependent', 'session_turn': {'context': {'session_id': 'kept'}},
             'historical_entry_references': [{'session_id': 'old', 'entry_id': 'entry-a1'}]},
            {'id': 'a2', 'exchange_id': 'e2', 'role': 'assistant', 'text': 'Dependent quote',
             'client_message_id': 'dependent', 'session_turn': {'context': {'session_id': 'kept'}}},
            {'id': 'q3', 'exchange_id': 'e3', 'role': 'user', 'text': 'Further quoted text',
             'client_message_id': 'further', 'session_turn': {'context': {'session_id': 'other-kept'}},
             'historical_entry_references': [{'session_id': 'kept', 'entry_id': 'entry-a2'}]},
            {'id': 'a3', 'exchange_id': 'e3', 'role': 'assistant', 'text': 'Further answer',
             'client_message_id': 'further', 'session_turn': {'context': {'session_id': 'other-kept'}}},
            {'id': 'safe', 'exchange_id': 'safe-e', 'role': 'assistant', 'text': 'Independent',
             'session_turn': {'context': {'session_id': 'live'}}},
        ]
        before = deepcopy(messages)
        plan = archive_erasure_plan('p', messages, frozenset({'old'}), entry_index={
            'a1': ('old', 'entry-a1'), 'a2': ('kept', 'entry-a2'),
            'a3': ('other-kept', 'entry-a3')})
        self.assertEqual(plan['remove_message_ids'], ['a1', 'q1'])
        self.assertEqual(plan['redact_message_ids'], ['a2', 'a3', 'q2', 'q3'])
        self.assertEqual(plan['dependent_session_ids'], ['kept', 'other-kept'])
        self.assertNotIn('Synthetic private old', str(plan))
        self.assertEqual(messages, before)


class ArchiveStorePlanTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = Store()
        self.history = AskDJHistoryManager(store=self.store)
        for identifier, session, dependency in [('old', 'old', ''), ('dependent', 'kept', 'old'),
                                                 ('safe', 'live', '')]:
            await self.history.async_append_exchange(
                'profile:p', {'client_message_id': identifier, 'text': 'Synthetic ' + identifier},
                {'success': True, 'text': 'Synthetic answer ' + identifier},
                session_turn={'turn_id': identifier, 'context': {'session_id': session,
                    **({'selected_entry': {'session_id': dependency, 'entry_id': 'old-entry'}} if dependency else {})}})

    async def test_intent_precedes_store_write_and_unavailable_exchange_survives_reload(self):
        captured = []
        async def prepare(plan):
            self.assertIn('Synthetic answer old', str(self.store.data))
            captured.append(deepcopy(plan))
            return plan
        result = await self.history.async_erase_archived_sessions(
            'p', frozenset({'old'}), prepare_intent=prepare,
            entry_index={})
        self.assertEqual(len(captured), 1)
        self.assertEqual(result, captured[0])
        restored = AskDJHistoryManager(store=self.store)
        values = (await restored.async_history('profile:p'))['messages']
        self.assertEqual({m['client_message_id'] for m in values}, {'dependent', 'safe'})
        dependent = [m for m in values if m.get('client_message_id') == 'dependent']
        self.assertEqual(len(dependent), 2)
        self.assertTrue(all(m['content_state'] == 'source_withdrawn' for m in dependent))
        self.assertTrue(all(not m.get('text') and not m.get('historical_entry_references') for m in dependent))
        self.assertIn('Synthetic answer safe', str(values))
        self.assertNotIn('Synthetic answer dependent', str(self.store.data))
        self.assertTrue(await restored.async_session_request_cleared('profile:p', 'dependent'))

    async def test_failed_intent_never_erases_store(self):
        before = deepcopy(self.store.data)
        async def fail(plan):
            raise OSError('synthetic SQL admission failure')
        with self.assertRaises(OSError):
            await self.history.async_erase_archived_sessions('p', frozenset({'old'}),
                                                            prepare_intent=fail, entry_index={})
        self.assertEqual(self.store.data, before)

    async def test_lost_store_ack_keeps_reads_closed_until_same_intent_reapplied(self):
        recorded = []
        async def prepare(plan):
            if not recorded:
                recorded.append(deepcopy(plan))
            return recorded[0]
        self.store.raise_after_save = True
        with self.assertRaises(OSError):
            await self.history.async_erase_archived_sessions('p', frozenset({'old'}),
                                                            prepare_intent=prepare, entry_index={})
        with self.assertRaisesRegex(RuntimeError, 'history_delete_outcome_unknown'):
            await self.history.async_history('profile:p')
        self.store.raise_after_save = False
        await self.history.async_erase_archived_sessions('p', frozenset({'old'}),
                                                        prepare_intent=prepare, entry_index={})
        self.assertNotIn('Synthetic answer old', str(await self.history.async_history('profile:p')))

    async def test_confirmation_read_inside_existing_store_validation_never_reenters_writer_lock(self):
        import asyncio
        async def index(messages):
            return {}, frozenset()
        # Existing serialized Store mutations call source validators, which read
        # query revisions. Those readers must use an immutable committed snapshot.
        async with self.history._write_lock:
            digest = await asyncio.wait_for(self.history.async_archive_scope_digest(
                'p', frozenset({'old'}), entry_index=index), 0.1)
        self.assertEqual(len(digest), 64)
