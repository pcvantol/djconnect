"""Owner adapter, real Profile resolver and SQLite; HA/provider boundaries are fixtures."""

from datetime import UTC, datetime
import json
import threading
from unittest.mock import patch
from types import SimpleNamespace
import unittest

from tests import test_session_conversation_history as fixtures
from tests.test_profile_dj_settings_persistence import operation


class ProfileSettingsOwnerTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = fixtures.SessionConversationHistoryTest()
        await self.fixture.asyncSetUp()
        self.hass, self.runtime, _, self.identity, self.headers = await self.fixture.transport_fixture()
        from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
        from custom_components.djconnect import profile_settings
        self.settings = profile_settings
        self.hass.data['djconnect']['djconnect_profile_platform'].hass = self.hass
        self.fixture.manager._settings_repository = ProfileDJSettingsRepository(self.fixture.service)
        self.entry = SimpleNamespace(entry_id='owner-entry', data={**self.runtime.config,
            'device_token': self.runtime.device_token}, options={}, disabled_by=None,
            state=SimpleNamespace(value='loaded'))
        self.runtime.entry = self.entry
        self.hass.config_entries.async_get_entry = lambda entry_id: self.entry if entry_id == self.entry.entry_id else None
        self.now = int(datetime.now(UTC).timestamp()*1000)

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def read(self, **fields):
        return await self.settings.async_handle_settings(self.hass,
            {**self.identity, 'contract_version': 3, **fields}, headers=self.headers)

    async def choose(self, before, values, *, counter=1):
        session = before['snapshot']['session']
        expected = {key: session[key] for key in ('session_id', 'generation', 'revision')} if session else None
        return await self.settings.async_handle_settings(self.hass, {**self.identity, 'contract_version': 3,
            'binding': before['binding'], 'patch': values, 'operation_id': operation(self.now, counter),
            'expected_defaults_revision': before['snapshot']['defaults_revision'],
            'expected_session': expected}, headers=self.headers, write=True)

    async def test_owner_no_session_defaults_then_actual_runtime_inherits(self):
        before, status = await self.read()
        self.assertEqual(status, 200, before)
        self.assertIsNone(before['snapshot']['session'])
        accepted, status = await self.choose(before, {'persona': 'radio_dj', 'mood': 'energy', 'presence': 'music_only'})
        self.assertEqual(status, 200, accepted)
        self.assertIsNone(self.fixture.manager.current_active('profile-a'))
        active = await self.fixture.manager.async_start(owner_profile_id='profile-a')
        self.assertEqual((active.dj_persona.value, active.selected_mood, active.selected_presence),
                         ('radio_dj', 'energy', 'music_only'))
        after, status = await self.read()
        self.assertEqual(status, 200, after)
        self.assertEqual(after['snapshot']['session']['settings'], accepted['snapshot']['defaults'])

    async def test_invalid_profile_client_or_broad_ha_credentials_never_return_settings(self):
        for extra in ({'profile_id': 'other'}, {'client_type': 'windows'}, {'contract_version': 1}):
            body, status = await self.read(**extra)
            self.assertGreaterEqual(status, 400)
            self.assertNotIn('snapshot', body)
        headers, self.headers = self.headers, {'Authorization': 'Bearer broad-ha-token'}
        body, status = await self.read()
        self.assertEqual(status, 401, body)
        self.headers = headers
        self.entry.disabled_by = 'user'
        body, status = await self.read()
        self.assertEqual(status, 401, body)

    async def test_bound_profile_aba_rotates_binding_and_rejects_old_intent(self):
        before, status = await self.read()
        self.assertEqual(status, 200, before)
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        await storage.async_create_profile('Other', profile_id='profile-b', default_backend_id='later_manual')
        await storage.async_upsert_device(self.identity['device_id'], 'ios', linked_profile_id='profile-b')
        await storage.async_upsert_device(self.identity['device_id'], 'ios', linked_profile_id='profile-a')
        after, status = await self.read()
        self.assertEqual(status, 200, after)
        self.assertNotEqual(after['binding'], before['binding'])
        rejected, status = await self.choose(before, {'mood': 'party'})
        self.assertEqual((status, rejected['error']), (409, 'settings_binding_changed'))
        self.assertEqual(after['snapshot']['defaults_revision'], 0)

    async def test_active_partial_patch_commits_both_and_stale_defaults_conflicts(self):
        await self.fixture.manager.async_start(owner_profile_id='profile-a', selected_mood='chill')
        before, status = await self.read()
        self.assertEqual(status, 200, before)
        accepted, status = await self.choose(before, {'persona': 'club_dj', 'mood': 'party'})
        self.assertEqual(status, 200, accepted)
        stale, status = await self.choose(before, {'presence': 'music_only'}, counter=2)
        self.assertEqual((status, stale['error']), (409, 'settings_revision_conflict'))
        self.assertEqual(self.fixture.manager.current_active('profile-a').selected_mood, 'party')

    async def test_http_views_use_same_owner_and_preserve_no_store_and_receipt_readback(self):
        http = self.fixture.http
        request = SimpleNamespace(app={'hass': self.hass}, headers=self.headers,
                                  query={**self.identity, 'contract_version': '3'})
        response = await http.DJConnectProfileSettingsView(self.hass).get(request)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        before = json.loads(response.text)
        accepted, status = await self.choose(before, {'mood': 'energy'})
        self.assertEqual(status, 200, accepted)
        payload = {**self.identity, 'contract_version': 3, 'binding': before['binding'],
                   'operation_id': operation(self.now)}
        async def body():
            return payload
        request.json, request.query_string = body, ''
        readback = await http.DJConnectProfileSettingsOperationView(self.hass).post(request)
        self.assertEqual(readback.status, 200)
        self.assertEqual(json.loads(readback.text)['phase'], 'accepted')
        self.assertEqual(readback.headers['Cache-Control'], 'no-store')

    async def test_conflict_after_revocation_never_delivers_private_snapshot(self):
        before, _ = await self.read()
        await self.choose(before, {'mood': 'energy'})
        manager = self.fixture.manager
        original = manager.async_accept_dj_settings
        async def revoked_conflict(**kwargs):
            try:
                return await original(**kwargs)
            except self.settings.SettingsRevisionConflict:
                self.entry.disabled_by = 'user'
                raise
        with patch.object(manager, 'async_accept_dj_settings', revoked_conflict):
            rejected, status = await self.choose(before, {'persona': 'club_dj'}, counter=2)
        self.assertEqual(status, 401, rejected)
        self.assertNotIn('current', rejected)
        self.assertNotIn('snapshot', rejected)

    async def test_generic_provider_inventory_is_only_inspected_on_ha_loop(self):
        from custom_components.djconnect import speech_processor
        original = speech_processor.voice_options
        loop_thread = threading.get_ident()
        calls = []
        def loop_bound_provider(*args, **kwargs):
            self.assertEqual(threading.get_ident(), loop_thread)
            calls.append(True)
            return original(*args, **kwargs)
        with patch.object(speech_processor, 'voice_options', loop_bound_provider):
            before, status = await self.read()
            self.assertEqual(status, 200, before)
            accepted, status = await self.choose(before, {'voice': {'kind': 'provider_default'}})
        self.assertEqual(status, 200, accepted)
        self.assertGreaterEqual(len(calls), 3)

    async def test_read_refreshes_provider_availability_after_storage_wait(self):
        from custom_components.djconnect import speech_processor
        manager = self.fixture.manager
        original = manager.async_read_dj_settings
        withdrawn = False
        async def read_after_change(**kwargs):
            nonlocal withdrawn
            result = await original(**kwargs)
            withdrawn = True
            return result
        def options(*args):
            return {'state': 'unavailable' if withdrawn else 'available',
                    'revision': 'withdrawn' if withdrawn else 'before',
                    'reason': 'tts_provider_unavailable' if withdrawn else None,
                    'provider_voice': {'engine': 'tts.fixture'}, 'voices': [],
                    'gender_selection': {'values': []}}
        with patch.object(manager, 'async_read_dj_settings', read_after_change), \
                patch.object(speech_processor, 'voice_options', options):
            result, status = await self.read()
        self.assertEqual(status, 200, result)
        self.assertEqual(result['voice_revision'], 'withdrawn')
        self.assertEqual(result['voice_availability'],
                         {'available': False, 'reason': 'tts_provider_unavailable'})
        self.assertEqual(result['snapshot']['defaults_revision'], 0)
        self.assertEqual(result['snapshot']['defaults']['voice'], {'kind': 'provider_default'})

    async def test_active_profile_delete_and_import_cannot_split_runtime_identity(self):
        from custom_components.djconnect.domain.storage import ProfileStorageValidationError
        from custom_components.djconnect.profile_export import async_export_profile, async_import_profile
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        await storage.async_create_profile('Other', profile_id='profile-b', default_backend_id='later_manual')
        before, _ = await self.read()
        await self.choose(before, {'mood': 'party'})
        active = await self.fixture.manager.async_start(owner_profile_id='profile-a')
        exported = await async_export_profile(storage, 'profile-a')
        # Historical identity-only schema1 must also reject active replacement.
        exported = {key: value for key, value in exported.items()
                    if key not in {'profile_dj_defaults', 'settings_restore'}}
        exported['schema_version'] = 1
        with self.assertRaisesRegex(ProfileStorageValidationError, 'profile_has_active_session'):
            await storage.async_delete_profile('profile-a', reassign_to_profile_id='profile-b')
        with self.assertRaisesRegex(ProfileStorageValidationError, 'profile_has_active_session'):
            await async_import_profile(storage, exported, overwrite=True)
        self.assertIn('profile-a', storage.household.profiles)
        self.assertIs(self.fixture.manager.current_active('profile-a'), active)
        current, status = await self.read()
        self.assertEqual(status, 200, current)
        self.assertEqual(current['snapshot']['defaults']['mood'], 'party')

    async def test_deleted_or_crash_orphan_preferences_cannot_resurrect_on_id_reuse(self):
        from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        await storage.async_create_profile('Other', profile_id='profile-b', default_backend_id='later_manual')
        before, _ = await self.read()
        await self.choose(before, {'persona': 'club_dj', 'mood': 'party'})
        await storage.async_delete_profile('profile-a', reassign_to_profile_id='profile-b')
        repository = ProfileDJSettingsRepository(self.fixture.service)
        erased = await repository.async_read('profile-a', authorize=lambda: True)
        self.assertEqual(erased['defaults_revision'], 0)
        # Simulate a crash leftover after identity deletion but before erasure.
        await repository.async_accept_user_choice('profile-a', operation_id=operation(self.now, 7),
            binding='a'*64, patch={'mood':'energy'}, expected_defaults_revision=0,
            now_ms=self.now, authorize=lambda: True)
        await storage.async_create_profile('Recreated', profile_id='profile-a', default_backend_id='later_manual')
        fresh = await repository.async_read('profile-a', authorize=lambda: True)
        self.assertEqual(fresh['defaults_revision'], 0)
        self.assertEqual(fresh['defaults']['mood'], 'groove')
        absent = await repository.async_operation_result('profile-a', operation_id=operation(self.now,7),
            binding='a'*64, now_ms=self.now, authorize=lambda: True)
        self.assertEqual(absent['phase'], 'not_accepted')

    async def test_profile_id_collision_is_never_implicit_overwrite(self):
        from custom_components.djconnect.domain.storage import ProfileStorageValidationError
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        before, _ = await self.read()
        await self.choose(before, {'persona':'festival_dj'})
        with self.assertRaisesRegex(ProfileStorageValidationError, 'profile_id collision'):
            await storage.async_create_profile('Different', profile_id='profile-a', default_backend_id='later_manual')
        after, status = await self.read()
        self.assertEqual(status, 200, after)
        self.assertEqual(after['snapshot']['defaults']['persona'], 'festival_dj')

    async def test_parked_portability_retains_schema1_and_rejects_unpublished_schema2(self):
        from custom_components.djconnect.profile_export import (
            async_export_profile, async_export_household, async_import_profile, ProfileExportError)
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        before, _ = await self.read()
        accepted, _ = await self.choose(before, {'persona':'radio_dj', 'mood':'party'})
        exported = await async_export_profile(storage, 'profile-a')
        self.assertEqual(exported['schema_version'], 1)
        self.assertNotIn('profile_dj_defaults', exported)
        self.assertNotIn('operation_id', str(exported))
        self.assertNotIn('binding_generation', str(exported))
        self.assertNotIn('device_token', str(exported))
        state = storage.household
        with self.assertRaisesRegex(ProfileExportError, 'profile_settings_restore_required'):
            await async_import_profile(storage, {**exported, 'schema_version':2,
                'profile_dj_defaults':accepted['snapshot']['defaults']}, reassign_id=True)
        self.assertEqual(storage.household, state)
        household = await async_export_household(storage)
        self.assertEqual(household['schema_version'], 1)
        self.assertNotIn('profile_dj_defaults', household)
        after, status = await self.read()
        self.assertEqual(status, 200, after)
        self.assertEqual(after['snapshot']['defaults'], accepted['snapshot']['defaults'])
        private_export = await async_export_profile(storage, 'profile-a', include_personal_data=False)
        self.assertNotIn('profile_dj_defaults', private_export)

    async def test_identity_only_import_cannot_keep_unrelated_existing_defaults(self):
        from custom_components.djconnect.profile_export import async_export_profile, async_import_profile
        from custom_components.djconnect.domain.storage import ProfileStorageValidationError
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        historical = await async_export_profile(storage, 'profile-a')
        self.assertEqual(historical['schema_version'], 1)
        before, _ = await self.read()
        await self.choose(before, {'persona':'club_dj'})
        with self.assertRaisesRegex(ProfileStorageValidationError, 'profile_settings_restore_required'):
            await async_import_profile(storage, historical, overwrite=True)
        after, status = await self.read()
        self.assertEqual(status, 200, after)
        self.assertEqual(after['snapshot']['defaults']['persona'], 'club_dj')

    async def test_raised_ingress_revocation_during_conflict_is_closed_unauthorized(self):
        before, _ = await self.read()
        await self.choose(before, {'mood':'party'})
        revoked = False
        original = self.fixture.manager.async_accept_dj_settings
        async def late_conflict(**kwargs):
            nonlocal revoked
            try:
                return await original(**kwargs)
            except self.settings.SettingsRevisionConflict:
                revoked = True
                raise
        def ingress():
            if revoked:
                raise PermissionError('paired_lease_revoked')
        with patch.object(self.fixture.manager, 'async_accept_dj_settings', late_conflict):
            result, status = await self.settings.async_handle_settings(self.hass,
                {**self.identity, 'contract_version':3, 'binding':before['binding'],
                 'operation_id':operation(self.now,2), 'patch':{'persona':'club_dj'},
                 'expected_defaults_revision':0, 'expected_session':None},
                headers=self.headers, write=True, validate_ingress=ingress)
        self.assertEqual(status, 401, result)
        self.assertNotIn('current', result)

    async def test_unchanged_schema1_export_never_claims_canonical_defaults_backup(self):
        from custom_components.djconnect.profile_export import (
            async_export_profile, async_export_household)
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        before, _ = await self.read()
        await self.choose(before, {'mood':'party'})
        await self.fixture.service.async_close()
        for exporter in (lambda: async_export_profile(storage, 'profile-a'),
                         lambda: async_export_household(storage)):
            exported = await exporter()
            self.assertEqual(exported['schema_version'], 1)
            self.assertNotIn('profile_dj_defaults', exported)
        redacted = await async_export_profile(storage, 'profile-a', include_personal_data=False)
        self.assertFalse(redacted['privacy']['personal_data_included'])
        self.assertNotIn('profile_dj_defaults', redacted)
        await self.fixture.service.async_initialize()

    async def test_output_defaults_live_session_and_next_session_use_one_choice(self):
        before, _ = await self.read()
        chosen, status = await self.choose(before, {'announcement_output':'text_only'})
        self.assertEqual(status, 200, chosen)
        self.assertIsNone(self.fixture.manager.current_active('profile-a'))
        active = await self.fixture.manager.async_start(owner_profile_id='profile-a')
        self.assertEqual(active.selected_announcement_output, 'text_only')
        before_live, _ = await self.read()
        moments = tuple(active.broadcast.state.dj_moments)
        chosen, status = await self.choose(before_live, {'announcement_output':'client_device'}, counter=2)
        self.assertEqual(status, 200, chosen)
        self.assertEqual(chosen['snapshot']['session']['settings']['announcement_output'], 'client_device')
        self.assertEqual(chosen['snapshot']['defaults']['announcement_output'], 'client_device')
        self.assertEqual(tuple(active.broadcast.state.dj_moments), moments)
        for field in ('persona', 'voice', 'gender', 'mood', 'presence'):
            self.assertEqual(chosen['snapshot']['defaults'][field], before_live['snapshot']['defaults'][field])

    async def test_speaker_mode_requires_usable_ha_target_and_retains_unavailable_selection(self):
        before, _ = await self.read()
        rejected, status = await self.choose(before, {'announcement_output':'ha_speaker'})
        self.assertEqual((status, rejected['error']), (409, 'announcement_speaker_unavailable'))
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.private_target'
        state = SimpleNamespace(state='idle', attributes={'supported_features':512})
        self.hass.states = SimpleNamespace(get=lambda name: state if name=='media_player.private_target' else None)
        accepted, status = await self.choose(before, {'announcement_output':'ha_speaker'}, counter=2)
        self.assertEqual(status, 200, accepted)
        self.assertTrue(accepted['announcement_output']['speaker_available'])
        state.state = 'unavailable'
        retained, status = await self.read()
        self.assertEqual(status, 200, retained)
        self.assertEqual(retained['snapshot'], accepted['snapshot'])
        self.assertEqual(retained['announcement_output']['selected'], 'ha_speaker')
        self.assertFalse(retained['announcement_output']['speaker_available'])
        self.assertNotIn('media_player.private_target', json.dumps(retained))
        self.assertNotIn('speaker_entity_id', json.dumps(retained))

    async def test_ha_only_admin_values_are_denied_by_shared_settings_allowlist(self):
        before, _ = await self.read()
        for count, key in enumerate(('assist_pipeline_id', 'dj_announcement_speaker_entity_id',
                                     'firmware_channel', 'screen_brightness', 'wake_word_enabled'), 1):
            rejected, status = await self.choose(before, {key:'forbidden'}, counter=count)
            self.assertEqual(status, 400, rejected)
            self.assertNotIn('snapshot', rejected)
        after, _ = await self.read()
        self.assertEqual(after['snapshot'], before['snapshot'])
        self.assertEqual(after['writable_fields'],
                         sorted(['persona','voice','gender','mood','presence','announcement_output']))

    async def test_changed_speaker_after_staging_is_configuration_conflict_not_auth_failure(self):
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.private_target'
        state = SimpleNamespace(state='idle', attributes={'supported_features':512})
        self.hass.states = SimpleNamespace(get=lambda name: state)
        before, _ = await self.read()
        repo = self.fixture.manager._settings_repository
        run = repo._async_in_transaction
        async def change_before_commit(operation, **kwargs):
            final = kwargs['finalize_authorize']
            def changed():
                state.state = 'unavailable'
                return final()
            return await run(operation, **{**kwargs, 'finalize_authorize':changed})
        with patch.object(repo, '_async_in_transaction', new=change_before_commit):
            rejected, status = await self.choose(before, {'announcement_output':'both'})
        self.assertEqual((status, rejected['error']), (409, 'settings_configuration_changed'))
        self.assertEqual((await self.read())[0]['snapshot'], before['snapshot'])

    async def test_old_settings_contract_requires_explicit_upgrade_without_writing(self):
        rejected, status = await self.read(contract_version=2)
        self.assertEqual((status, rejected['error']), (426, 'settings_contract_upgrade_required'))
        self.assertEqual(rejected['settings_contract_version'], 3)
        self.assertFalse((await self.read())[0]['snapshot']['activated'])
