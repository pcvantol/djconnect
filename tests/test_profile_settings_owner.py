"""Owner adapter, real Profile resolver and SQLite; HA/provider boundaries are fixtures."""

from datetime import UTC, datetime
import json
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
            {**self.identity, 'contract_version': 2, **fields}, headers=self.headers)

    async def choose(self, before, values, *, counter=1):
        session = before['snapshot']['session']
        expected = {key: session[key] for key in ('session_id', 'generation', 'revision')} if session else None
        return await self.settings.async_handle_settings(self.hass, {**self.identity, 'contract_version': 2,
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
                                  query={**self.identity, 'contract_version': '2'})
        response = await http.DJConnectProfileSettingsView(self.hass).get(request)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        before = json.loads(response.text)
        accepted, status = await self.choose(before, {'mood': 'energy'})
        self.assertEqual(status, 200, accepted)
        payload = {**self.identity, 'contract_version': 2, 'binding': before['binding'],
                   'operation_id': operation(self.now)}
        async def body():
            return payload
        request.json, request.query_string = body, ''
        readback = await http.DJConnectProfileSettingsOperationView(self.hass).post(request)
        self.assertEqual(readback.status, 200)
        self.assertEqual(json.loads(readback.text)['phase'], 'accepted')
        self.assertEqual(readback.headers['Cache-Control'], 'no-store')
