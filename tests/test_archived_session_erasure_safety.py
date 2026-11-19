"""Synthetic Store/SQLite erasure preconditions, with no personal data deletion."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()

from custom_components.djconnect.ask_dj_history import AskDJHistoryManager  # noqa: E402
from custom_components.djconnect.ask_dj.dialogue import DialogueError, DialogueState, DialogueTurn  # noqa: E402
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository, ACTIVE, ENDED  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402


class Store:
    def __init__(self, data=None):
        self.data, self.saves = deepcopy(data), 0
        self.raise_after_save = False
        self.started = self.release = None

    async def async_load(self):
        return deepcopy(self.data)

    async def async_save(self, data):
        if self.started is not None:
            self.started.set()
            await self.release.wait()
        self.data = deepcopy(data)
        self.saves += 1
        if self.raise_after_save:
            raise OSError('synthetic acknowledgement loss')


class ArchivedStoreErasureSafetyTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = Store()
        self.history = AskDJHistoryManager(store=self.store)

    async def append(self, identifier, session='old', dependency=None, profile='p'):
        context = {'session_id': session}
        if dependency:
            context['selected_entry'] = {'session_id': dependency, 'entry_id': 'entry'}
        return await self.history.async_append_exchange(
            'profile:' + profile, {'client_message_id': identifier, 'text': 'Synthetic question'},
            {'success': True, 'text': 'Synthetic answer'},
            session_turn={'turn_id': identifier, 'context': context})

    async def test_exact_exchange_and_dependencies_removed_other_owner_live_and_dedup_survive(self):
        await self.append('old')
        await self.append('dependent', 'live', 'old')
        await self.append('live', 'live')
        await self.append('other-owner', 'old', profile='other')
        before = await self.history.async_scope_revision('profile:p')
        self.assertEqual(await self.history.async_forget_archived_sessions('p', frozenset({'old'})), 4)
        saved = await self.history.async_history('profile:p')
        self.assertEqual({m['client_message_id'] for m in saved['messages']}, {'live'})
        self.assertEqual(len((await self.history.async_history('profile:other'))['messages']), 2)
        self.assertEqual(saved['clear_revision'], 1)
        self.assertEqual(await self.history.async_scope_revision('profile:p'), before)
        self.assertTrue(await self.history.async_session_request_cleared('profile:p', 'old'))
        self.assertTrue(await self.history.async_session_request_cleared('profile:p', 'dependent'))
        writes = self.store.saves
        self.assertEqual(await self.history.async_forget_archived_sessions('p', frozenset({'old'})), 0)
        self.assertEqual(self.store.saves, writes)
        reloaded = AskDJHistoryManager(store=self.store)
        self.assertEqual(await reloaded.async_scope_revision('profile:p'), before)
        self.assertEqual(len((await reloaded.async_history('profile:p'))['messages']), 2)

    async def test_sql_message_ids_remove_legacy_turn_without_session_context(self):
        result = await self.history.async_append_exchange('profile:p',
            {'client_message_id': 'legacy', 'text': 'Synthetic legacy'},
            {'success': True, 'text': 'Synthetic legacy answer'}, session_turn={'turn_id': 'legacy'})
        await self.history.async_forget_archived_sessions('p', frozenset({'old'}),
            message_ids=frozenset({result['assistant_message']['id']}))
        self.assertEqual((await self.history.async_history('profile:p'))['messages'], [])

    async def test_targeted_then_normal_clear_and_restart_still_revoke_privacy(self):
        await self.append('old')
        await self.history.async_forget_archived_sessions('p', frozenset({'old'}))
        original = self.history.scope_revision('profile:p')
        await self.history.async_clear('profile:p')
        self.assertNotEqual(self.history.scope_revision('profile:p'), original)
        reloaded = AskDJHistoryManager(store=self.store)
        await reloaded.async_load()
        self.assertEqual(reloaded.scope_revision('profile:p'), self.history.scope_revision('profile:p'))
        self.assertEqual(reloaded.data['users']['profile:p']['targeted_clear_revision'], 1)

    async def test_full_clear_after_high_global_revision_changes_profile_privacy(self):
        for _ in range(5):
            await self.history.async_clear_all(include_profile_history=False)
        await self.append('old')
        await self.history.async_forget_archived_sessions('p', frozenset({'old'}))
        before = self.history.scope_revision('profile:p')
        await self.history.async_clear_all(include_profile_history=False)
        self.assertEqual(self.history.scope_revision('profile:p'), before)
        await self.history.async_clear_all()
        self.assertNotEqual(self.history.scope_revision('profile:p'), before)
        self.assertEqual(self.history.data['users']['profile:p']['targeted_clear_revision'], 1)

    async def test_new_append_receipt_compares_in_privacy_domain_after_targeted_clear(self):
        await self.append('old')
        await self.history.async_forget_archived_sessions('p', frozenset({'old'}))
        receipt = await self.append('new', 'live')
        self.assertEqual(receipt['clear_revision'], 1)
        self.assertEqual(self.history.scope_revision_for_receipt('profile:p', receipt),
                         self.history.scope_revision('profile:p'))

    async def test_legacy_counter_missing_defaults_zero_corrupt_counter_fails_closed(self):
        for value in (None, True, False, 0.0, 1.0, -1, 4, '1'):
            with self.subTest(value=value):
                state = {'clear_revision': 3, 'targeted_clear_revision': value, 'messages': []}
                manager = AskDJHistoryManager(store=Store({'users': {'profile:p': state}}))
                with self.assertRaisesRegex(ValueError, 'invalid_history_clear_revision'):
                    await manager.async_history('profile:p')
        manager = AskDJHistoryManager(store=Store({'users': {'profile:p': {'clear_revision': 3}}}))
        self.assertEqual(await manager.async_scope_revision('profile:p'), '0:3')

    async def test_unknown_store_save_blocks_stale_reads_and_writes_until_reload_recovery(self):
        await self.append('old')
        await self.append('live', 'live')
        self.store.raise_after_save = True
        with self.assertRaises(OSError):
            await self.history.async_forget_archived_sessions('p', frozenset({'old'}))
        with self.assertRaisesRegex(RuntimeError, 'history_delete_outcome_unknown'):
            await self.history.async_history('profile:p')
        with self.assertRaises(RuntimeError):
            await self.append('no-stale-overwrite', 'live')
        writes = self.store.saves
        self.store.raise_after_save = False
        self.assertEqual(await self.history.async_forget_archived_sessions('p', frozenset({'old'})), 0)
        self.assertEqual(self.store.saves, writes)
        messages = (await self.history.async_history('profile:p'))['messages']
        self.assertEqual({m['client_message_id'] for m in messages}, {'live'})

    async def test_repeated_cancel_waits_for_commit_before_releasing_write_lock(self):
        await self.append('old')
        self.store.started, self.store.release = asyncio.Event(), asyncio.Event()
        task = asyncio.create_task(self.history.async_forget_archived_sessions('p', frozenset({'old'})))
        await self.store.started.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        self.assertTrue(self.history._write_lock.locked())
        self.store.release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(self.history._write_lock.locked())
        self.assertEqual((await self.history.async_history('profile:p'))['messages'], [])

    async def test_waiting_append_rechecks_unknown_save_inside_lock(self):
        await self.append('old')
        self.store.started, self.store.release = asyncio.Event(), asyncio.Event()
        await self.history._write_lock.acquire()
        prune = asyncio.create_task(self.history.async_forget_archived_sessions('p', frozenset({'old'})))
        append = asyncio.create_task(self.append('must-not-write', 'live'))
        await asyncio.sleep(0)
        self.history._write_lock.release()
        await self.store.started.wait()
        self.store.raise_after_save = True
        self.store.release.set()
        results = await asyncio.gather(prune, append, return_exceptions=True)
        self.assertIsInstance(results[0], OSError)
        self.assertIsInstance(results[1], RuntimeError)
        self.assertNotIn('must-not-write', str(self.store.data))

    async def test_initial_load_cannot_overwrite_a_later_completed_erasure(self):
        await self.append('old')
        started, release = asyncio.Event(), asyncio.Event()
        original_load = self.store.async_load
        async def held_load():
            snapshot = await original_load()
            started.set()
            await release.wait()
            return snapshot
        self.store.async_load = held_load
        manager = AskDJHistoryManager(store=self.store)
        initial = asyncio.create_task(manager.async_history('profile:p'))
        await started.wait()
        prune = asyncio.create_task(manager.async_forget_archived_sessions('p', frozenset({'old'})))
        await asyncio.sleep(0)
        self.assertFalse(prune.done())
        release.set()
        await initial
        self.assertEqual(await prune, 2)
        self.assertEqual((await manager.async_history('profile:p'))['messages'], [])
        await manager.async_append_exchange('profile:p', {'client_message_id': 'live', 'text': 'Live'},
            {'success': True, 'text': 'Live answer'}, session_turn={'turn_id': 'live'})
        self.assertEqual({m['client_message_id'] for m in self.store.data['users']['profile:p']['messages']}, {'live'})

    async def test_pending_request_tombstone_is_durable_even_without_removed_messages(self):
        self.history.register_session_request('profile:p', 'pending-id')
        self.assertEqual(await self.history.async_forget_archived_sessions('p', frozenset({'old'})), 0)
        self.assertEqual(self.store.saves, 1)
        self.history.unregister_session_request('profile:p', 'pending-id')
        restored = AskDJHistoryManager(store=self.store)
        self.assertTrue(await restored.async_session_request_cleared('profile:p', 'pending-id'))
        with self.assertRaisesRegex(ValueError, 'conversation_history_changed'):
            await restored.async_append_exchange('profile:p',
                {'client_message_id': 'pending-id', 'text': 'Do not reexecute'},
                {'success': True, 'text': 'No'}, session_turn={'turn_id': 'pending'})
        self.assertEqual((await restored.async_history('profile:p'))['clear_revision'], 0)

    async def test_withdrawn_inflight_retry_cannot_reopen_after_original_worker_leaves(self):
        state = DialogueState()
        frame = state.frame('profile:p', 'thread', 'generation')
        original, admitted = state.reserve(frame, 'pending-id', 'digest', False)
        self.assertTrue(admitted)
        state.forget_archived_sessions('profile:p', frozenset({'old'}))
        frame.inflight.pop('pending-id')
        with self.assertRaisesRegex(DialogueError, 'choice_expired'):
            state.reserve(frame, 'pending-id', 'digest', False)
        with self.assertRaisesRegex(DialogueError, 'client_message_conflict'):
            state.reserve(frame, 'pending-id', 'changed', False)
        original.cancel()

    async def test_dedup_capacity_closes_frame_instead_of_evicting_proof(self):
        from custom_components.djconnect.ask_dj.dialogue import MAX_READ_RECEIPTS
        state = DialogueState()
        frame = state.frame('profile:p', 'thread', 'generation')
        original, _ = state.reserve(frame, 'fast-inflight', 'digest', True)
        frame.catalogue_replays = {str(i): ('digest', None, False, 0, 99999999.)
                                   for i in range(MAX_READ_RECEIPTS)}
        state.forget_archived_sessions('profile:p', frozenset({'old'}))
        frame.inflight.pop('fast-inflight')
        self.assertEqual(len(frame.catalogue_replays), MAX_READ_RECEIPTS)
        with self.assertRaisesRegex(DialogueError, 'conversation_capacity'):
            state.reserve(frame, 'fast-inflight', 'digest', True)
        original.cancel()

    async def test_pending_context_revoked_accepted_independent_speech_and_digests_preserved(self):
        state = DialogueState()
        frame = state.frame('profile:p', 'thread', 'generation')
        disposed = []
        for name, session, dependencies in [('old', 'old', []), ('dependent', 'live', [{'session_id': 'old'}]),
                                             ('live', 'live', [])]:
            frame.speech_references[name] = {'session_id': session, 'dependencies': dependencies,
                                             'dispose': lambda n=name: disposed.append(n)}
        frame.messages = [{'role': 'assistant', 'text': 'Erased private body'}]
        frame.local_turns = deepcopy(frame.messages)
        future = asyncio.get_running_loop().create_future()
        future.set_result({'text': 'Old private body'})
        frame.catalogue_replays['retry'] = ('digest', future, False, 10, 99999999.)
        async def validate():
            pass
        turn = DialogueTurn(frame, 'profile:p', 'thread', 'id', 'digest', frame.generation, validate, None)
        state.forget_archived_sessions('profile:p', frozenset({'old'}))
        self.assertEqual(disposed, ['old', 'dependent'])
        self.assertEqual(frame.generation, 'generation')
        self.assertEqual(frame.messages, [])
        self.assertEqual(frame.catalogue_replays['retry'], ('digest', None, False, 0, 99999999.))
        with self.assertRaisesRegex(DialogueError, 'conversation_context_changed'):
            await turn.guard()
        with self.assertRaisesRegex(DialogueError, 'choice_expired'):
            state.reserve(frame, 'retry', 'digest', False)
        with self.assertRaisesRegex(DialogueError, 'client_message_conflict'):
            state.reserve(frame, 'retry', 'different', False)
        state.complete(turn, {'success': True, '_dialogue_question': 'Stale question', 'text': 'Stale result'})
        self.assertEqual(frame.messages, [])


class ArchivedSQLiteErasureSafetyTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = PersistenceService(Path(self.tmp.name) / 'synthetic.sqlite3', SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.sessions = PersistentSessionRepository(self.service)
        self.history = HistoricalProjectionRepository(self.service)
        await self.sessions.async_create('p', session_id='old')
        await self.sessions.async_transition('p', 'old', ACTIVE)
        self.ended = await self.sessions.async_transition('p', 'old', ENDED)

    async def asyncTearDown(self):
        await self.service.async_close()
        self.tmp.cleanup()

    async def test_delayed_terminal_projection_cannot_resurrect_erased_header(self):
        await self.service.async_in_transaction(lambda tx: tx.execute(
            'DELETE FROM djconnect_persistent_sessions WHERE session_id=?', ('old',)))
        self.assertIsNone(await self.history.async_project_session(self.ended))
        self.assertIsNone(await self.history.async_get_session_for_originating_id('old'))

    async def test_terminal_projection_requires_matching_durable_owner_and_lifecycle(self):
        self.assertIsNone(await self.history.async_project_session(replace(self.ended, owner_profile_id='other')))
        self.assertIsNone(await self.history.async_project_session(replace(self.ended, lifecycle_status=ACTIVE)))
        self.assertIsNotNone(await self.history.async_project_session(self.ended))

    async def test_delayed_legacy_moment_cannot_resurrect_erased_or_foreign_header(self):
        async def project(owner='p'):
            return await self.history.async_project_moment(session_id='old', moment_id='m',
                owner_profile_id=owner, moment_type='track', rendered_text='Synthetic body',
                presentation_metadata='{}', ordering=0, created_at=self.ended.created_at)
        self.assertIsNone(await project('other'))
        await self.service.async_in_transaction(lambda tx: tx.execute(
            'DELETE FROM djconnect_persistent_sessions WHERE session_id=?', ('old',)))
        self.assertIsNone(await project())
        rows = await self.service.async_in_transaction(lambda tx: tx.fetchall(
            'SELECT historical_moment_id FROM djconnect_historical_moments'))
        self.assertEqual(rows, [])
