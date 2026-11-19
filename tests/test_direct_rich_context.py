"""Actual Profile, paired SQLite ACK and Session; no display permission port."""
import asyncio
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.test_direct_rich_pair import Headers, Runtime
from tests.test_profile_storage import MemoryStore, ProfilePlatformStorage
from tests.test_session_runtime import _load_runtime_module
from custom_components.djconnect import direct_rich_context as rich
from custom_components.djconnect import profile_observation as observation
from custom_components.djconnect.direct_rich_wire import RichError
from custom_components.djconnect.domain import BackendProvider, ProfilePrivacyMode
from custom_components.djconnect.domain.music_account import MusicAccountKind
from custom_components.djconnect.persistence import PersistenceService, PersistentSessionRepository
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider
from custom_components.djconnect.surface_pair_journal import schedule_pair_registration
from custom_components.djconnect.surface_registration import PairingRetirement, retire_runtime


class Hass:
    pass


class DirectRichContextTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime_module, cls.previous_const = _load_runtime_module()
        if cls.previous_const is not None:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if cls.previous_const is None:
            sys.modules.pop('custom_components.djconnect.const', None)
        else:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const

    async def asyncSetUp(self):
        self.maintenance = patch('custom_components.djconnect.session_history_maintenance.schedule_history_maintenance')
        self.maintenance.start()
        self.temp = tempfile.TemporaryDirectory()
        self.service = PersistenceService(Path(self.temp.name) / 'context.sqlite', SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.hass = Hass()
        self.hass.data = {}
        self.hass.is_stopping = False
        self.hass.async_create_task = asyncio.create_task
        observation.bootstrap_from_integration_setup(self.hass)
        self.storage = ProfilePlatformStorage(self.hass, MemoryStore())
        observation.publish_manager(self.hass, self.hass.data['djconnect'], self.storage)
        await self.storage.async_create_profile('Synthetic owner', profile_id='synthetic-owner')
        await self.storage.async_upsert_music_backend('spotify_direct', BackendProvider.SPOTIFY_DIRECT,
            display_name='Synthetic backend')
        await self.storage.async_upsert_music_account('synthetic-account', 'spotify_direct',
            kind=MusicAccountKind.PERSONAL, display_name='Synthetic account',
            linked_profile_ids=frozenset({'synthetic-owner'}))
        profile = self.storage.household.profiles['synthetic-owner']
        await self.storage.async_update_profile('synthetic-owner', preferences=replace(profile.preferences,
            default_backend_id='spotify_direct', default_music_account_id='synthetic-account'))
        self.device = 'djconnect-ios-ABCDEF123456'
        await self.storage.async_upsert_device(self.device, 'ios', linked_profile_id='synthetic-owner')
        self.entry = SimpleNamespace(entry_id='synthetic-entry', disabled_by=None,
            state=SimpleNamespace(value='loaded'), options={}, data={
                'device_id': self.device, 'client_type': 'ios', 'device_token': 'SYNTHETIC-ONLY',
                'ha_install_id': 'synthetic-ha', 'music_backend': 'spotify_direct',
                'music_account_id': 'synthetic-account', 'spotify_refresh_token': 'SYNTHETIC-NOT-SENT'})
        self.runtime = Runtime()
        self.runtime.entry = self.entry
        self.runtime.device_token = self.entry.data['device_token']
        self.runtime.pairing_device_id = self.device
        self.runtime.surface_registration_retirement = PairingRetirement()
        self.runtime._receiver_end_generation = 0
        self.domain = self.hass.data['djconnect']
        self.domain.update({self.entry.entry_id: self.runtime, 'persistence_service': self.service})
        self.hass.config_entries = SimpleNamespace(async_entries=lambda _: [self.entry],
            async_get_entry=lambda key: self.entry if key == self.entry.entry_id else None)
        self.headers = Headers({'Authorization': 'Bearer SYNTHETIC-ONLY',
            'X-DJConnect-Device-ID': self.device, 'X-DJConnect-Client-Type': 'ios'})
        schedule_pair_registration(self.hass, self.runtime)
        registration = self.runtime.surface_pair_registration
        while registration.tasks:
            await asyncio.gather(*tuple(registration.tasks))
        self.manager = self.runtime_module.SessionRuntimeManager(PersistentSessionRepository(self.service))
        self.domain['session_runtime_manager'] = self.manager
        self.active = await self.manager.async_start(owner_profile_id='synthetic-owner',
            history_source_context={'backend_id': 'spotify_direct', 'music_account_id': 'synthetic-account',
                'provider_entry_id': self.entry.entry_id, 'provider_account_id': ''})

    async def asyncTearDown(self):
        for context in tuple(rich._contexts):
            if context.pair.hass is self.hass:
                context.retire()
        registration = self.runtime.surface_pair_registration
        while registration.tasks:
            await asyncio.gather(*tuple(registration.tasks), return_exceptions=True)
        await self.service.async_close()
        self.temp.cleanup()
        self.maintenance.stop()

    def capture(self):
        return rich.capture_context(self.hass, self.headers, device_id=self.device,
            client_type='ios', session_id=self.active.session_id)

    async def test_pure_capture_joins_real_pair_profile_source_and_active_SQL_session(self):
        with patch.object(self.storage, 'async_load', side_effect=AssertionError('No load')), \
                patch.object(self.manager, 'async_get_active', side_effect=AssertionError('No migration')), \
                patch.object(self.service, 'async_in_transaction', side_effect=AssertionError('No IO')):
            context = self.capture()
            attempt = context.attempt()
            self.assertTrue(attempt.current())
            self.assertEqual(context.owner, 'synthetic-owner')
            self.assertIs(context.broadcast, self.active.broadcast)
        self.assertFalse(any(hasattr(context, k) for k in ('credential', 'expires_ms', 'permission')))

    async def test_cosmetic_profile_commit_preserves_context_but_old_attempt_is_closed(self):
        context = self.capture()
        original = context.attempt()
        await self.storage.async_update_profile('synthetic-owner', display_name='Synthetic renamed')
        self.assertFalse(original.current())
        self.assertTrue(original.closed)
        self.assertIsNone(original.snapshot)
        self.assertTrue(context.attempt().current())
        self.assertFalse(context.retired)

    async def test_known_queued_profile_write_suspends_and_does_not_renew_or_retire_context(self):
        context = self.capture()
        await self.storage._write_lock.acquire()
        operation = asyncio.create_task(self.storage.async_save())
        await asyncio.sleep(0)
        with self.assertRaises(RichError) as caught:
            context.attempt()
        self.assertEqual(caught.exception.code, 'rich_frame_unavailable')
        self.assertFalse(context.retired)
        self.storage._write_lock.release()
        await operation
        self.assertTrue(context.attempt().current())

    async def test_privacy_staging_and_ABA_close_before_any_write_or_await(self):
        context = self.capture()
        attempt = context.attempt()
        original = self.storage.household
        profile = original.profiles['synthetic-owner']
        self.storage._household = replace(original, profiles={**original.profiles,
            profile.profile_id: replace(profile, privacy_mode=ProfilePrivacyMode.PRIVATE)})
        self.assertTrue(context.retired)
        self.assertTrue(attempt.closed)
        self.assertIsNone(attempt.snapshot)
        self.assertIsNone(attempt.active)
        self.storage._household = original
        self.assertFalse(attempt.current())
        with self.assertRaises(RichError):
            context.attempt()

    async def test_actual_end_fences_even_before_manager_lock_admission(self):
        context = self.capture()
        attempt = context.attempt()
        await self.manager._lock.acquire()
        operation = asyncio.create_task(self.manager.async_end(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id))
        await asyncio.sleep(0)
        self.assertTrue(context.retired)
        self.assertTrue(attempt.closed)
        self.manager._lock.release()
        await operation

    async def test_wrong_session_end_does_not_retire_another_original(self):
        context = self.capture()
        await self.manager.async_end(owner_profile_id='synthetic-owner', session_id='different-session')
        self.assertFalse(context.retired)
        self.assertTrue(context.attempt().current())

    async def test_actual_store_uncertainty_scrubs_held_attempts(self):
        context = self.capture()
        attempt = context.attempt()
        self.storage._store = MemoryStore()
        self.assertTrue(context.retired)
        self.assertTrue(attempt.closed)
        self.assertTrue(all(getattr(context, k) is None for k in context.__dataclass_fields__
            if k != 'retired'))

    async def test_runtime_retirement_fences_context_and_snapshot_before_background_SQL(self):
        context = self.capture()
        attempt = context.attempt()
        retire_runtime(self.runtime)
        self.assertTrue(context.retired)
        self.assertTrue(attempt.closed)
        self.assertIsNone(attempt.context)
        self.assertFalse(attempt.current())

    async def test_source_mismatch_cannot_be_adopted_and_read_does_not_repair_it(self):
        self.manager._history_source_contexts[self.active.session_id]['provider_account_id'] = 'different'
        before = dict(self.manager._history_source_contexts[self.active.session_id])
        with self.assertRaises(RichError):
            self.capture()
        self.assertEqual(self.manager._history_source_contexts[self.active.session_id], before)

    async def test_actual_mood_change_preserves_original_context_but_not_old_attempt(self):
        context = self.capture()
        attempt = context.attempt()
        await self.manager.async_update_mood(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, selected_mood='energy')
        self.assertFalse(attempt.current())
        current = context.attempt()
        self.assertTrue(current.current())
        self.assertEqual(current.active.selected_mood, 'energy')
        self.assertIs(current.active.broadcast, self.active.broadcast)
        self.assertFalse(context.retired)

    async def test_known_content_pending_suspends_attempt_without_restoring_old_snapshot(self):
        context = self.capture()
        attempt = context.attempt()
        self.active.broadcast.content_pending = True
        self.assertFalse(attempt.current())
        self.assertTrue(attempt.closed)
        self.assertFalse(context.retired)
        with self.assertRaises(RichError) as caught:
            context.attempt()
        self.assertEqual(caught.exception.code, 'rich_frame_unavailable')
        self.active.broadcast.content_pending = False
        self.assertFalse(attempt.current())
        self.assertTrue(context.attempt().current())

    async def test_same_content_genuine_backend_observation_closes_original_attempt_clock(self):
        fields = dict(owner_profile_id='synthetic-owner', session_id=self.active.session_id,
            state='playing', media_identity='spotify:track:' + 'A' * 22,
            title='Synthetic track', artist='Synthetic artist')
        await self.manager.async_update_playback_projection(**fields)
        context = self.capture()
        attempt = context.attempt()
        broadcast = self.active.broadcast
        serial = broadcast.passive_observation_serial
        original_state, sequence = broadcast.state, broadcast.delivery_sequence
        original_observation = broadcast.passive_observation
        changed = await self.manager.async_update_playback_projection(**fields)
        self.assertFalse(changed)
        self.assertIs(broadcast.state, original_state)
        self.assertEqual(broadcast.delivery_sequence, sequence)
        self.assertEqual(broadcast.passive_observation_serial, serial + 1)
        self.assertIsNot(broadcast.passive_observation, original_observation)
        self.assertFalse(attempt.current())
        self.assertTrue(attempt.closed)
        self.assertFalse(context.retired)
        self.assertTrue(context.attempt().current())
