"""Actual paired authority, Runtime, Store and SQLite with synthetic provider data."""
import asyncio
from copy import deepcopy
from unittest.mock import patch
import unittest

from tests import test_history_deletion_api as archive_fixture
from tests.test_history_deletion_journal import identifier


class PairedContentDeleteTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        archive_fixture.PairedHistoryDeleteTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        archive_fixture.PairedHistoryDeleteTests.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = archive_fixture.PairedHistoryDeleteTests()
        await self.fixture.asyncSetUp()
        self.f = self.fixture.f
        self.hass = self.fixture.hass
        from custom_components.djconnect import content_deletion_api
        self.api = content_deletion_api
        messages = (await self.f.history.async_history('profile:profile-a'))['messages']
        self.message = next(m for m in messages if m['role'] == 'user')
        self.selector = {'kind': 'message', 'session_id': self.fixture.target.session_id,
                         'target_id': self.message['id']}
        self.identity = {**self.f.identity, 'contract_version': 1}
        self.operation = identifier(self.fixture.now, 17)

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def prepare(self, target=None):
        return await self.api.async_handle_content_delete(self.hass,
            {**self.identity, 'target': target or self.selector}, headers=self.f.headers, operation='prepare')

    async def delete(self, preview, **changes):
        return await self.api.async_handle_content_delete(self.hass,
            {**self.identity, 'confirmation_id': preview['confirmation_id'],
             'operation_id': self.operation, 'confirmed': True, **changes}, headers=self.f.headers)

    async def status(self, preview, **changes):
        return await self.api.async_handle_content_delete(self.hass,
            {**self.identity, 'confirmation_id': preview['confirmation_id'],
             'operation_id': self.operation, **changes}, headers=self.f.headers, operation='status')

    async def test_explicit_server_exchange_confirmation_either_bubble_and_original_receipt(self):
        preview, status = await self.prepare()
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview['unit']['kind'], 'exchange')
        self.assertEqual(len(preview['removed_message_ids']), 2)
        assistant = next(m for m in (await self.f.history.async_history('profile:profile-a'))['messages'] if m['role'] == 'assistant')
        other, status = await self.prepare({**self.selector, 'target_id': assistant['id']})
        self.assertEqual(status, 200, other)
        self.assertEqual(preview['unit'], other['unit'])
        self.assertEqual(preview['removed_message_ids'], other['removed_message_ids'])
        before, status = await self.status(preview)
        self.assertEqual((status, before['state'], before['definitive']), (200, 'unknown', False))
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['state'], 'completed')
        self.assertFalse(result['music_playback_undone'])
        self.assertEqual(await self.delete(preview), (result, 200))
        found, status = await self.status(preview)
        self.assertEqual((status, found['state']), (200, 'completed'))
        self.assertEqual(found['receipt']['removed_message_ids'], preview['removed_message_ids'])
        self.assertIsNotNone(await self.fixture.query._repository.async_session_record(self.fixture.target.session_id))

    async def test_no_confirmation_no_mutation_and_no_profile_hint(self):
        preview, _ = await self.prepare()
        for changes in ({'confirmed': False}, {'profile_id': 'profile-b'}, {'operation_id': 'bad'}):
            result, status = await self.delete(preview, **changes)
            self.assertEqual((status, result['error']), (400, 'invalid_content_delete_request'))
        self.assertTrue((await self.f.history.async_history('profile:profile-a'))['messages'])

    async def test_status_does_not_recover_pending_or_write_clock_or_store(self):
        preview, _ = await self.prepare()
        self.fixture.store.raise_after_save = True
        result, status = await self.delete(preview)
        self.assertEqual((status, result['error']), (503, 'content_delete_outcome_unknown'))
        from custom_components.djconnect.content_deletion import content_deletion_coordinator
        c = content_deletion_coordinator(self.hass)
        before = await c.persistence.async_in_transaction(lambda tx: tx.fetchall('SELECT * FROM djconnect_history_deletion_clock'))
        saved = deepcopy(self.fixture.store.data)
        self.fixture.store.raise_after_save = False
        result, status = await self.status(preview)
        self.assertEqual((status, result['state']), (200, 'pending'))
        self.assertEqual(saved, self.fixture.store.data)
        self.assertEqual(before, await c.persistence.async_in_transaction(lambda tx: tx.fetchall('SELECT * FROM djconnect_history_deletion_clock')))
        self.assertEqual(len(await c.journal.async_pending_content()), 1)
        self.hass.data['djconnect'].pop('content_confirmations', None)
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['state'], 'completed')

    async def test_changed_confirmation_body_cannot_resume_original_operation(self):
        preview, _ = await self.prepare()
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        wrong = {**preview, 'confirmation_id': 'x' * 43}
        result, status = await self.status(wrong)
        self.assertEqual((status, result['error']), (409, 'content_delete_operation_conflict'))
        result, status = await self.delete(wrong)
        self.assertEqual((status, result['error']), (409, 'content_delete_operation_conflict'))

    async def test_expiry_and_preview_restart_do_not_create_success(self):
        clock = [0.0]
        self.hass.data['djconnect']['content_confirmations'] = self.api.ContentConfirmations(monotonic=lambda: clock[0])
        preview, _ = await self.prepare()
        clock[0] = 301
        result, status = await self.delete(preview)
        self.assertEqual((status, result['error']), (409, 'content_delete_scope_conflict'))
        result, status = await self.status(preview, operation_id=identifier(self.fixture.now - 300_001, 15))
        self.assertEqual((status, result['state'], result['definitive']), (200, 'expired_unknown', False))
        self.hass.data['djconnect']['content_confirmations'] = self.api.ContentConfirmations()
        result, status = await self.delete(preview)
        self.assertEqual((status, result['error']), (404, 'content_unavailable'))

    async def test_original_uncertain_attempt_blocks_late_provider_and_replay(self):
        selector = {'kind': 'request', 'session_id': '', 'target_id': 'synthetic-not-arrived'}
        preview, status = await self.prepare(selector)
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview['removed_message_ids'], [])
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        result, status = await self.f.request('What is an ostinato?', identifier=selector['target_id'])
        self.assertNotEqual(status, 200, result)
        self.assertFalse(any(m.get('client_message_id') == selector['target_id'] for m in
            (await self.f.history.async_history('profile:profile-a'))['messages']))

    async def test_active_moment_withdraws_runtime_without_ending_or_replaying_music(self):
        active, moment, reference = await self.f.selected_credit()
        target = {'kind': 'moment', 'session_id': active.session_id, 'target_id': moment.moment_id}
        preview, status = await self.prepare(target)
        self.assertEqual(status, 200, preview)
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        active = self.f.fixture.manager.current_active('profile-a')
        self.assertEqual(active.session_id, target['session_id'])
        self.assertNotIn(moment.moment_id, {m.moment_id for m in active.broadcast.state.dj_moments})
        self.assertFalse(active.broadcast.content_pending)
        self.assertEqual(self.f.effects, [])
        self.assertFalse(active.allows_moment(moment))

    async def test_pending_provider_cannot_deliver_or_archive_after_original_attempt_cancel(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def pending(*args, **kwargs):
            entered.set()
            await release.wait()
            return {'speech': {'plain': {'speech': 'Synthetic delayed answer.'}}}
        original = 'synthetic-delayed-original'
        with patch.object(self.f.pipeline, '_call_conversation_process_transport', pending):
            task = asyncio.create_task(self.f.request('What is an ostinato?', identifier=original))
            try:
                await asyncio.wait_for(entered.wait(), 2)
                preview, status = await self.prepare({'kind': 'request', 'session_id': '', 'target_id': original})
                self.assertEqual(status, 200, preview)
                result, status = await self.delete(preview)
                self.assertEqual(status, 200, result)
                release.set()
                result, status = await asyncio.wait_for(task, 2)
                self.assertNotEqual(status, 200, result)
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        self.assertFalse(any(m.get('client_message_id') == original for m in
            (await self.f.history.async_history('profile:profile-a'))['messages']))
        self.assertEqual(self.f.effects, [])

    async def test_paused_planner_cannot_resurrect_deleted_flow_or_engine(self):
        active, moment, reference = await self.f.selected_credit()
        manager = self.f.fixture.manager
        current = manager.current_active('profile-a')
        clock = [current.presence_ledger.clock() + 100]
        manager._monotonic_source = lambda: clock[0]
        current.presence_ledger.clock = manager._monotonic_source
        current.planner.elapsed_time_source = manager._monotonic_source
        await manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=active.session_id,
            state='playing', media_identity='synthetic-next-media', title='Synthetic next',
            artist='Synthetic next performer', duration_ms=300000, position_ms=1000)
        entered, release = asyncio.Event(), asyncio.Event()
        async def paused(*args, **kwargs):
            entered.set()
            await release.wait()
            return None
        async def source():
            return {'track': {'title': 'Synthetic next', 'artist': 'Synthetic next performer'}}
        with patch.object(type(manager.current_active('profile-a').planning_coordinator), 'async_coordinate_track_started', paused):
            task = asyncio.create_task(manager.async_process_track_started(owner_profile_id='profile-a',
                session_id=active.session_id, media_identity='synthetic-next-media', insight_provider=source))
            try:
                await asyncio.wait_for(entered.wait(), 2)
                preview, status = await self.prepare({'kind': 'moment', 'session_id': active.session_id,
                    'target_id': moment.moment_id})
                self.assertEqual(status, 200, preview)
                result, status = await self.delete(preview)
                self.assertEqual(status, 200, result)
                release.set()
                self.assertIsNone(await asyncio.wait_for(task, 2))
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        current = manager.current_active('profile-a')
        self.assertNotIn(moment.moment_id, {m.moment_id for m in current.moment_engine.moments})
        self.assertNotIn(moment.moment_id, {i.moment_id for i in current.planner.output.session_flow.items})
        self.assertFalse(any(i.moment_id == moment.moment_id for c in current.planner.flow_change_journal for i in c.flow.items))
        self.assertNotIn(moment.moment_id, current.performance_memory.recent_moment_ids)

    async def test_foreign_owner_target_and_changed_sql_revision_refuse_before_erasure(self):
        foreign = await self.f.fixture.manager.async_start(owner_profile_id='profile-b', locale='en')
        result, status = await self.prepare({**self.selector, 'session_id': foreign.session_id})
        self.assertEqual((status, result['error']), (404, 'content_unavailable'))
        preview, _ = await self.prepare()
        await self.f.fixture.service.async_in_transaction(lambda tx: tx.execute(
            'UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?',
            (self.selector['session_id'],)))
        result, status = await self.delete(preview)
        self.assertEqual((status, result['error']), (409, 'content_delete_scope_conflict'))
        self.assertTrue((await self.f.history.async_history('profile:profile-a'))['messages'])

    async def test_standalone_descriptor_cannot_target_an_accepted_session_exchange(self):
        for target in ({**self.selector, 'session_id': ''},
                {'kind': 'request', 'session_id': '', 'target_id': self.message['client_message_id']}):
            result, status = await self.prepare(target)
            self.assertEqual((status, result['error']), (404, 'content_unavailable'))
        self.assertTrue((await self.f.history.async_history('profile:profile-a'))['messages'])

    async def test_live_history_opt_out_moment_still_deletes_without_creating_archive(self):
        active, moment, reference = await self.f.selected_credit()
        await self.f.fixture.service.async_in_transaction(lambda tx: tx.execute(
            'UPDATE djconnect_persistent_sessions SET history_enabled=0 WHERE session_id=?', (active.session_id,)))
        # Simulate the genuine opt-out shape: accepted live Moment, no retained SQL body.
        await self.f.fixture.service.async_in_transaction(lambda tx: tx.execute(
            'DELETE FROM djconnect_session_entries WHERE session_id=? AND reference_id=?',
            (active.session_id, moment.moment_id)))
        preview, status = await self.prepare({'kind': 'moment', 'session_id': active.session_id, 'target_id': moment.moment_id})
        self.assertEqual(status, 200, preview)
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        current = self.f.fixture.manager.current_active('profile-a')
        self.assertNotIn(moment.moment_id, {m.moment_id for m in current.broadcast.state.dj_moments})
        self.assertFalse(current.allows_moment(moment))

    async def test_archives_use_separate_exact_body_bound_read_only_status(self):
        from custom_components.djconnect.history_deletion_api import async_handle_history_delete_status
        query = {**self.identity, 'operation': 'single', 'operation_id': self.fixture.payload['operation_id'],
            'session_id': self.fixture.payload['session_id'], 'expected_revision': self.fixture.payload['expected_revision']}
        before, status = await async_handle_history_delete_status(self.hass, query, headers=self.f.headers)
        self.assertEqual((status, before['state']), (200, 'unknown'))
        self.fixture.store.raise_after_save = True
        result, status = await self.fixture.delete()
        self.assertEqual((status, result['error']), (503, 'history_delete_outcome_unknown'))
        from custom_components.djconnect.history_deletion import deletion_coordinator
        coordinator = deletion_coordinator(self.hass)
        clock = await coordinator.persistence.async_in_transaction(lambda tx: tx.fetchall('SELECT * FROM djconnect_history_deletion_clock'))
        pending, status = await async_handle_history_delete_status(self.hass, query, headers=self.f.headers)
        self.assertEqual((status, pending['state']), (200, 'pending'))
        self.assertEqual(clock, await coordinator.persistence.async_in_transaction(lambda tx: tx.fetchall('SELECT * FROM djconnect_history_deletion_clock')))
        self.assertEqual(len(await coordinator.journal.async_pending()), 1)
        self.fixture.store.raise_after_save = False
        result, status = await self.fixture.delete()
        self.assertEqual(status, 200, result)
        completed, status = await async_handle_history_delete_status(self.hass, query, headers=self.f.headers)
        self.assertEqual((status, completed['state']), (200, 'completed'))
        self.assertEqual(completed['receipt'], result)
        wrong, status = await async_handle_history_delete_status(self.hass,
            {**query, 'expected_revision': query['expected_revision']+'changed'}, headers=self.f.headers)
        self.assertEqual((status, wrong['error']), (409, 'history_delete_operation_conflict'))

    async def test_malformed_selector_types_are_rejected_without_server_error(self):
        for kind in ([], {}, 1, None):
            result, status = await self.prepare({**self.selector, 'kind': kind})
            self.assertEqual((status, result['error']), (400, 'invalid_content_delete_request'))

    async def test_final_live_reference_fence_rejects_deletion_during_last_source_await(self):
        from custom_components.djconnect.ask_dj import service
        active, moment, _ = await self.f.selected_credit()
        entered, release = asyncio.Event(), asyncio.Event()
        original = service._live_reference
        calls = 0
        async def delayed(*args, **kwargs):
            nonlocal calls
            result = await original(*args, **kwargs)
            calls += 1
            if calls == 2:
                entered.set()
                await release.wait()
            return result
        target = {'session_id': active.session_id, 'moment_id': moment.moment_id}
        with patch.object(service, '_live_reference', delayed):
            task = asyncio.create_task(self.f.request('Tell me more about that', identifier='synthetic-stale-moment',
                context={'session_id': active.session_id, 'selected_moment': target}))
            try:
                await asyncio.wait_for(entered.wait(), 2)
                preview, status = await self.prepare({'kind': 'moment', 'session_id': active.session_id, 'target_id': moment.moment_id})
                self.assertEqual(status, 200, preview)
                result, status = await self.delete(preview)
                self.assertEqual(status, 200, result)
                release.set()
                result, status = await asyncio.wait_for(task, 2)
                self.assertNotEqual(status, 200, result)
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        self.assertFalse(any(m.get('client_message_id') == 'synthetic-stale-moment' for m in
            (await self.f.history.async_history('profile:profile-a'))['messages']))

    def test_actual_wire_fixture_source_and_receipt_bindings(self):
        import hashlib
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root/'examples/client_contracts/session_conversation_history/content-deletion-v1-settings-migration-20261021.json').read_text())
        for relative, expected in fixture['source_pins'].items():
            self.assertEqual(hashlib.sha256((root/relative).read_bytes()).hexdigest(), expected, relative)
        self.assertEqual(hashlib.sha256((root/fixture['harness']).read_bytes()).hexdigest(), fixture['harness_sha256'])
        self.assertEqual((fixture['installed'], fixture['native'], fixture['model_provider_calls']), ('NOT_RUN', 'NOT_RUN', 0))
        examples = fixture['examples']
        self.assertEqual(examples['prepare_response']['unit'], examples['delete_response']['unit'])
        self.assertEqual(examples['prepare_response']['confirmation_id'], examples['delete_response']['confirmation_id'])
        self.assertEqual(examples['delete_request']['operation_id'], examples['delete_response']['operation_id'])
        expected = {'confirmation_id': examples['delete_request']['confirmation_id']}
        self.assertEqual(examples['delete_response']['request_digest'],
            hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        self.assertEqual(examples['completed_status_response']['receipt'], examples['delete_response'])
        self.assertEqual(examples['foreign_response']['error'], 'content_unavailable')
        self.assertEqual(examples['standalone_response']['unit']['session_id'], '')
        self.assertEqual(examples['pending_status_response']['state'], 'pending')
        self.assertEqual(examples['recovered_response']['state'], 'completed')

    async def test_accepted_artwork_url_closes_on_pending_cache_failure_before_withdrawal(self):
        import time
        from custom_components.djconnect import session_artwork as art
        from custom_components.djconnect.content_deletion import content_deletion_coordinator
        from custom_components.djconnect.image_proxy import ManagedSessionImages
        active, moment, _ = await self.f.selected_credit()
        context = type('SyntheticContext', (), {'profile_id': 'profile-a'})()
        target = {'moment_id': moment.moment_id}
        with patch.object(art, 'subject_for_fact', return_value='spotify:artist:'+'A'*22):
            resolved = await art.resolve_target(self.hass, self.f.runtime, context, active.session_id, target)
        self.assertIsNotNone(resolved)
        registry = ManagedSessionImages()
        self.hass.data['djconnect']['session_images'] = registry
        self.f.fixture.service.session_image_owner = registry
        key = art.target_key('profile-a', active.session_id, target, 1)
        registry.commit(key, {'asset_id': 'synthetic-accepted-asset', 'deadline': time.monotonic()+300,
            'body': b'synthetic disposable pixels', 'mime': 'image/png', 'authority': lambda: True,
            'allowed': resolved[2], 'delivery_scope': resolved[7], 'expected_source': resolved[1]})
        with patch.object(art, 'artist_authority', return_value=lambda: True):
            self.assertIsNotNone(await art.image(self.hass, context, active.session_id,
                'synthetic-accepted-asset', runtime=self.f.runtime))
            preview, status = await self.prepare({'kind': 'moment', 'session_id': active.session_id,
                'target_id': moment.moment_id})
            self.assertEqual(status, 200, preview)
            c = content_deletion_coordinator(self.hass)
            with patch.object(c.journal, 'async_refresh_fences', side_effect=OSError('synthetic cache read failure')):
                result, status = await self.delete(preview)
            self.assertEqual((status, result['error']), (503, 'content_delete_outcome_unknown'))
            current = self.f.fixture.manager.current_active('profile-a')
            self.assertNotIn(moment.moment_id, {a['moment_id'] for a in current.broadcast.native_delivery()['admissions']})
            safe = current.broadcast._safe_delivery_payload({'dj_moments': [moment.as_dict()]})
            self.assertEqual(safe['dj_moments'], [])
            self.assertIsNone(await art.image(self.hass, context, active.session_id,
                'synthetic-accepted-asset', runtime=self.f.runtime))
            self.assertEqual(await c.async_recover(), 1)
        self.assertFalse(self.f.fixture.manager.current_active('profile-a').broadcast.content_pending_moment_ids)

    async def test_explicit_session_end_during_pending_erasure_disposes_runtime_and_keeps_obligation(self):
        from custom_components.djconnect.content_deletion import content_deletion_coordinator
        active, moment, _ = await self.f.selected_credit()
        preview, status = await self.prepare({'kind': 'moment', 'session_id': active.session_id,
            'target_id': moment.moment_id})
        self.assertEqual(status, 200, preview)
        self.fixture.store.raise_after_save = True
        result, status = await self.delete(preview)
        self.assertEqual((status, result['error']), (503, 'content_delete_outcome_unknown'))
        ended = await self.f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=active.session_id)
        self.assertEqual(ended.runtime_state.value, 'ended')
        self.assertIsNone(self.f.fixture.manager.current_active('profile-a'))
        c = content_deletion_coordinator(self.hass)
        self.assertEqual(len(await c.journal.async_pending_content()), 1)
        self.fixture.store.raise_after_save = False
        self.assertEqual(await c.async_recover(), 1)
        self.assertEqual((await c.repository.async_session_record(active.session_id))['lifecycle_status'], 'ENDED')

    async def test_original_live_attempt_can_be_cancelled_with_history_storage_disabled(self):
        active = await self.f.fixture.manager.async_start(owner_profile_id='profile-a', locale='en', history_enabled=False)
        preview, status = await self.prepare({'kind': 'request', 'session_id': active.session_id,
            'target_id': 'synthetic-private-original-pending'})
        self.assertEqual(status, 200, preview)
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['unit']['kind'], 'attempt')
        self.assertIsNotNone(self.f.fixture.manager.current_active('profile-a'))
        self.assertEqual(result['removed_message_ids'], [])

    async def test_retained_moment_outside_live_window_and_missing_root_are_distinct(self):
        from dataclasses import replace
        active, moment, reference = await self.f.selected_credit()
        current = self.f.fixture.manager.current_active('profile-a')
        current.broadcast.state = replace(current.broadcast.state, dj_moments=())
        unknown, status = await self.prepare({'kind': 'moment', 'session_id': active.session_id,
            'target_id': 'moment-never-published'})
        self.assertEqual((status, unknown['error']), (404, 'content_unavailable'))
        preview, status = await self.prepare({'kind': 'entry', 'session_id': active.session_id,
            'target_id': reference['entry_id']})
        self.assertEqual(status, 200, preview)
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['unit']['target_id'], moment.moment_id)
        self.assertIsNotNone(self.f.fixture.manager.current_active('profile-a'))

    async def test_ordinary_transition_provenance_persisted_and_live_withdrawn(self):
        import json
        from dataclasses import replace
        from custom_components.djconnect import session_runtime as core
        from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
        _, root, _ = await self.f.selected_credit()
        active = self.f.fixture.manager.current_active('profile-a')
        source = replace(root, moment_type=core.DJMomentType.ARTIST)
        target = replace(root, moment_id='independent-target', moment_type=core.DJMomentType.RECOMMENDATION)
        active.moment_engine.moments = (*active.moment_engine.moments, target)
        decision = core.PlannerDecision(core.PlannerDecisionType.CREATE_TRANSITION, 'synthetic',
            core.KnowledgeIntent(core.KnowledgeIntentType.TRANSITION, 'Synthetic relation'),
            transition_moment_ids=(source.moment_id, target.moment_id), transition_placement='next')
        transition = active.moment_engine.create_transition(session_id=active.session_id, approval=decision,
            selected_mood='groove', persona=core.DJPersona.HOME_DJ, locale='en')
        self.assertEqual(transition.moment_type, core.DJMomentType.TRANSITION)
        self.assertIsNone(transition.genre_transition)
        # Advance the supported synthetic presence clock past the readable gap.
        active.presence_ledger.clock = lambda: active.presence_ledger.last_at + 91
        self.assertTrue(await self.f.fixture.manager._async_persist_moment(active, transition))
        repo = HistoricalProjectionRepository(self.f.fixture.service)
        row = next(r for r in await repo.async_entry_records('profile-a', active.session_id)
                   if r['reference_id'] == transition.moment_id)
        self.assertEqual(set(json.loads(row['body'])['dependency_moment_ids']), {root.moment_id, target.moment_id})
        active.broadcast.publish_moment(transition)
        preview, status = await self.prepare({'kind': 'moment', 'session_id': active.session_id, 'target_id': root.moment_id})
        self.assertEqual(status, 200, preview)
        self.assertIn(transition.moment_id, {m['moment_id'] for m in preview['affected_moments']})
        result, status = await self.delete(preview)
        self.assertEqual(status, 200, result)
        self.assertNotIn(transition.moment_id, {m.moment_id for m in active.broadcast.state.dj_moments})
        self.assertFalse(active.allows_moment(transition))
        self.assertIn(target.moment_id, {m.moment_id for m in active.moment_engine.moments})
