"""Production paired handler and Runtime/SQLite; synthetic device-auth, agent and Store boundaries."""
from datetime import UTC, datetime
from types import SimpleNamespace
import unittest

from tests import test_ask_dj_contextual_dialogue as dialogue
from tests.test_history_deletion_journal import identifier


class PairedHistoryDeleteTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        dialogue.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        dialogue.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = dialogue.SharedDialogueTest()
        await self.f.asyncSetUp()
        self.hass, self.runtime = self.f.hass, self.f.runtime
        self.entry = SimpleNamespace(entry_id='owner-entry', data={**self.runtime.config,
            'device_token': self.runtime.device_token}, options={}, disabled_by=None,
            state=SimpleNamespace(value='loaded'))
        self.runtime.entry = self.entry
        # The upstream fixture uses a constant-token device stand-in. Make that
        # explicit external boundary honor token rotation in this suite.
        self.runtime.authorize_device_request = lambda headers, device_id=None, client_type=None: (
            headers.get('Authorization') == 'Bearer ' + self.runtime.device_token
            and device_id == self.f.identity['device_id'] and client_type == self.f.identity['client_type'])
        self.hass.config_entries.async_get_entry = lambda eid: self.entry if eid == self.entry.entry_id else None
        from tests.test_archived_session_erasure_safety import Store
        self.store = Store()
        self.f.history._store = self.store
        self.now = int(datetime.now(UTC).timestamp() * 1000)
        from custom_components.djconnect import history_deletion_api
        self.api = history_deletion_api
        self.target = await self.f.fixture.manager.async_start(owner_profile_id='profile-a', selected_mood='chill', locale='en')
        answer, status = await self.f.request('What is an ostinato?', identifier='synthetic-erased',
                                            context={'session_id': self.target.session_id})
        self.assertEqual(status, 200, answer)
        await self.f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=self.target.session_id)
        from custom_components.djconnect.session_conversation import query_service
        self.query = query_service(self.hass, self.f.history)
        self.before = await self.query._session('profile-a', self.target.session_id)
        self.payload = {**self.f.identity, 'session_id': self.target.session_id,
                        'expected_revision': self.before['revision'], 'confirmed': True,
                        'operation_id': identifier(self.now), 'history_contract_version': 2}

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def delete(self, **changes):
        return await self.api.async_handle_history_delete(self.hass, {**self.payload, **changes}, headers=self.f.headers)

    async def test_exact_confirmed_owner_delete_and_receipt_replay(self):
        result, status = await self.delete()
        self.assertEqual(status, 200, result)
        self.assertEqual(result['deleted_session_id'], self.target.session_id)
        self.assertEqual(result['owner_profile_id'], 'profile-a')
        self.assertIsNone(await self.query._repository.async_session_record(self.target.session_id))
        self.assertNotIn('synthetic-erased', str((await self.f.history.async_history('profile:profile-a'))['messages']))
        self.assertEqual(await self.delete(), (result, status))
        conflict, status = await self.delete(expected_revision=self.before['revision'] + 'altered')
        self.assertEqual((status, conflict['error']), (409, 'history_delete_operation_conflict'))

    async def test_explicit_confirmation_and_opaque_detail_revision_required(self):
        for changes in ({'confirmed': False}, {'operation_id': 'not-a-uuid7'}):
            result, status = await self.delete(**changes)
            self.assertEqual((status, result['error']), (400, 'invalid_history_delete_request'))
        result, status = await self.delete(expected_revision=str(self.before['_sql_revision']))
        self.assertEqual((status, result['error']), (409, 'history_revision_conflict'))
        self.assertIsNotNone(await self.query._repository.async_session_record(self.target.session_id))

    async def test_unknown_target_and_active_runtime_never_erased(self):
        result, status = await self.delete(session_id='unknown-session')
        self.assertEqual((status, result['error']), (404, 'history_unavailable'))
        live = await self.f.fixture.manager.async_start(owner_profile_id='profile-a', selected_mood='chill', locale='en')
        result, status = await self.delete(session_id=live.session_id)
        self.assertEqual((status, result['error']), (409, 'session_not_archived'))
        self.assertEqual(self.f.fixture.manager.current_active('profile-a').session_id, live.session_id)

    async def test_delivery_and_replay_require_original_pairing(self):
        result, status = await self.delete()
        self.assertEqual(status, 200, result)
        self.runtime.device_token = 'synthetic-revoked-token'
        self.runtime.config['device_token'] = self.runtime.device_token
        self.entry.data['device_token'] = self.runtime.device_token
        result, status = await self.delete()
        self.assertIn(status, (401, 403), result)

    async def test_expired_admission_releases_real_media_callbacks_without_masking_error(self):
        result, status = await self.delete(operation_id=identifier(self.now - 300_001))
        self.assertEqual((status, result['error']), (409, 'history_delete_operation_conflict'))
        self.assertIsNotNone(await self.query._repository.async_session_record(self.target.session_id))
        self.assertEqual(self.query._repository.retention_fence[1], 0)
        self.assertTrue((await self.f.history.async_history('profile:profile-a'))['messages'])

    async def snapshot(self):
        result, status = await self.api.async_handle_history_delete(
            self.hass, self.f.identity, headers=self.f.headers, operation='snapshot')
        self.assertEqual(status, 200, result)
        return result

    async def delete_all(self, snapshot, *, sequence=10):
        return await self.api.async_handle_history_delete(self.hass,
            {**self.f.identity, 'confirmed': True, 'snapshot_id': snapshot['snapshot_id'],
             'operation_id': identifier(self.now, sequence)}, headers=self.f.headers, operation='all')

    async def test_bulk_captures_all_server_targets_and_preserves_new_completion(self):
        second = await self.f.fixture.manager.async_start(owner_profile_id='profile-a', selected_mood='chill', locale='en')
        await self.f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=second.session_id)
        snapshot = await self.snapshot()
        self.assertEqual(snapshot['target_count'], 2)
        newer = await self.f.fixture.manager.async_start(owner_profile_id='profile-a', selected_mood='chill', locale='en')
        await self.f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=newer.session_id)
        result, status = await self.delete_all(snapshot)
        self.assertEqual(status, 200, result)
        self.assertEqual(result['deleted_session_count'], 2)
        self.assertIsNone(await self.query._repository.async_session_record(self.target.session_id))
        self.assertIsNone(await self.query._repository.async_session_record(second.session_id))
        self.assertIsNotNone(await self.query._repository.async_session_record(newer.session_id))
        self.assertEqual(await self.delete_all(snapshot), (result, status))

    async def test_bulk_target_revision_conflict_erases_nothing(self):
        second = await self.f.fixture.manager.async_start(owner_profile_id='profile-a', selected_mood='chill', locale='en')
        await self.f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=second.session_id)
        snapshot = await self.snapshot()
        await self.f.fixture.service.async_in_transaction(lambda tx: tx.execute(
            'UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?',
            (second.session_id,)))
        result, status = await self.delete_all(snapshot)
        self.assertEqual((status, result['error']), (409, 'history_delete_snapshot_conflict'))
        self.assertIsNotNone(await self.query._repository.async_session_record(self.target.session_id))
        self.assertIsNotNone(await self.query._repository.async_session_record(second.session_id))
        self.assertTrue((await self.f.history.async_history('profile:profile-a'))['messages'])

    async def test_snapshot_restart_and_expiry_fail_closed_without_deletion(self):
        from custom_components.djconnect.history_deletion_snapshots import ArchiveDeletionSnapshots
        clock = [0.0]
        self.hass.data['djconnect']['history_deletion_snapshots'] = ArchiveDeletionSnapshots(monotonic=lambda: clock[0])
        snapshot = await self.snapshot()
        clock[0] = 301
        result, status = await self.delete_all(snapshot)
        self.assertEqual((status, result['error']), (409, 'history_delete_snapshot_conflict'))
        self.hass.data['djconnect']['history_deletion_snapshots'] = ArchiveDeletionSnapshots()
        result, status = await self.delete_all(snapshot)
        self.assertEqual((status, result['error']), (404, 'history_unavailable'))
        self.assertIsNotNone(await self.query._repository.async_session_record(self.target.session_id))

    async def test_same_pending_operation_resumes_after_lost_ack_without_process_restart(self):
        self.store.raise_after_save = True
        result, status = await self.delete()
        self.assertEqual((status, result['error']), (503, 'history_delete_outcome_unknown'))
        self.store.raise_after_save = False
        result, status = await self.delete()
        self.assertEqual(status, 200, result)
        self.assertEqual(self.query._repository.retention_fence[1], 0)
        self.assertIsNone(await self.query._repository.async_session_record(self.target.session_id))
        self.assertNotIn('synthetic-erased', str((await self.f.history.async_history('profile:profile-a'))['messages']))

    async def test_pending_erasure_has_same_typed_unavailable_outcome_on_shared_history_handler(self):
        self.store.raise_after_save = True
        result, status = await self.delete()
        self.assertEqual((status, result['error']), (503, 'history_delete_outcome_unknown'))
        result, status = await self.f.handlers.async_handle_ask_dj_history_payload(
            self.hass, self.f.identity, headers=self.f.headers)
        self.assertEqual((status, result['error']), (503, 'history_delete_outcome_unknown'))
        self.assertNotIn('messages', result)
        self.store.raise_after_save = False
        from custom_components.djconnect.history_deletion import deletion_coordinator
        await deletion_coordinator(self.hass).async_recover()

    def test_qualified_content_and_archive_capability_versions_are_explicit(self):
        from custom_components.djconnect.capability_contract import _platform_capabilities, _contract_versions
        capabilities, versions = _platform_capabilities(), _contract_versions()
        for key in ('session_history_delete', 'session_history_bulk_delete',
                    'session_content_delete', 'session_history_delete_status'):
            self.assertIs(capabilities[key], True)
            self.assertEqual(versions[key], 1)

    def test_actual_ha_wire_fixture_binds_current_source_without_claiming_installation(self):
        import hashlib
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        historical = root / 'examples/client_contracts/session_conversation_history/archive-deletion-v1-20261021.json'
        self.assertEqual(hashlib.sha256(historical.read_bytes()).hexdigest(),
                         '79fac1e077a157df0851797c84de2f1f61bc14be08f3048c703ba9acec9f2a67')
        fixture = json.loads((root / 'examples/client_contracts/session_conversation_history/archive-deletion-v1-current-track-insight-20261021.json').read_text())
        for path, expected in fixture['source_pins'].items():
            self.assertEqual(hashlib.sha256((root / path).read_bytes()).hexdigest(), expected, path)
        self.assertEqual(hashlib.sha256((root / fixture['harness']).read_bytes()).hexdigest(), fixture['harness_sha256'])
        self.assertEqual(fixture['model_provider_calls'], 0)
        self.assertEqual(fixture['installed'], 'NOT_RUN')
        examples = fixture['examples']
        self.assertEqual(examples['single_response']['operation_id'], examples['single_request']['operation_id'])
        self.assertEqual(examples['single_response']['deleted_session_id'], examples['single_request']['session_id'])
        self.assertEqual(examples['bulk_response']['deleted_session_count'], examples['snapshot_response']['target_count'])
        self.assertEqual(examples['bulk_response']['snapshot_id'], examples['bulk_request']['snapshot_id'])
        self.assertEqual(examples['pending_response']['error'], 'history_delete_outcome_unknown')
