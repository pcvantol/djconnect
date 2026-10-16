"""Actual Runtime lock + existing SQLite acceptance, without transport mocks."""

import asyncio
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from tests.test_profile_dj_settings_persistence import operation
from tests.test_session_runtime import _load_runtime_module
from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository, SettingsCommitError
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository


class ProfileSettingsRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.r, self.previous_const = _load_runtime_module()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'runtime.sqlite'
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.repo = ProfileDJSettingsRepository(self.service)
        self.manager = self.r.SessionRuntimeManager(
            PersistentSessionRepository(self.service), HistoricalProjectionRepository(self.service),
            settings_repository=self.repo)
        self.active = await self.manager.async_start(owner_profile_id='owner', selected_mood='chill')
        self.now = int(datetime.now(UTC).timestamp()*1000)

    async def asyncTearDown(self):
        await self.service.async_close()
        self.temp.cleanup()
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if self.previous_const is None:
            sys.modules.pop('custom_components.djconnect.const', None)
        else:
            sys.modules['custom_components.djconnect.const'] = self.previous_const

    def expected(self, active=None):
        active = active or self.active
        return {'session_id': active.session_id, 'generation': active.settings_generation,
                'revision': active.settings_revision}

    async def choose(self, values, *, expected_defaults=0, expected_session='initial', counter=1,
                     authorize=lambda: True, validate_voice=lambda selected: None):
        return await self.manager.async_accept_dj_settings(
            owner_profile_id='owner', operation_id=operation(self.now, counter), binding='b'*64,
            patch=values, expected_defaults_revision=expected_defaults,
            expected_session=self.expected() if expected_session == 'initial' else expected_session,
            now_ms=self.now, authorize=authorize, validate_voice=validate_voice)

    async def test_all_five_acceptance_updates_runtime_and_summary_without_reset(self):
        self.active.presence_ledger.total_published = 3
        result = await self.choose({'mood': 'party', 'persona': 'club_dj', 'presence': 'music_only',
            'voice': {'kind': 'provider_voice', 'provider_id': 'tts.test', 'voice_id': 'v1'},
            'gender': 'female'})
        active = self.manager.current_active('owner')
        self.assertEqual(active.effective_dj_settings().as_dict(), result['snapshot']['session']['settings'])
        self.assertEqual(active.effective_dj_settings().as_dict(), result['snapshot']['defaults'])
        self.assertEqual(active.presence_ledger.total_published, 3)
        self.assertEqual((active.mood_revision, active.persona_revision, active.presence_revision), (1, 1, 1))
        self.assertEqual(active.broadcast.state.dj_moments, ())
        self.assertNotIn('selected_voice', active.broadcast.as_dict()['session'])
        row = await self.service.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT mood_current FROM djconnect_session_summaries WHERE session_id=?', (active.session_id,)))
        self.assertEqual(row, ('party',))

    async def test_sql_failure_keeps_runtime_and_defaults_old_then_retry_once(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("CREATE TRIGGER reject_choices BEFORE INSERT ON djconnect_profile_dj_settings BEGIN SELECT RAISE(ABORT,'injected failure'); END")
        with self.assertRaises(RuntimeError):
            await self.choose({'mood': 'energy', 'persona': 'radio_dj'})
        self.assertIs(self.manager.current_active('owner'), self.active)
        self.assertEqual((await self.repo.async_read('owner', authorize=lambda: True))['defaults_revision'], 0)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute('DROP TRIGGER reject_choices')
        self.assertFalse((await self.choose({'mood': 'energy', 'persona': 'radio_dj'}))['replayed'])
        self.assertTrue((await self.choose({'mood': 'energy', 'persona': 'radio_dj'}))['replayed'])
        self.assertEqual(self.manager.current_active('owner').settings_revision, 1)

    async def test_replay_never_rolls_newer_runtime_back(self):
        await self.choose({'persona': 'radio_dj'})
        current = self.manager.current_active('owner')
        await self.choose({'persona': 'club_dj'}, expected_defaults=1,
                          expected_session=self.expected(current), counter=2)
        replay = await self.choose({'persona': 'radio_dj'})
        self.assertTrue(replay['replayed'])
        self.assertEqual(self.manager.current_active('owner').dj_persona.value, 'club_dj')
        self.assertEqual(self.manager.current_active('owner').settings_revision, 2)

    async def test_broadcast_failure_is_durable_success_not_rejected_choice(self):
        with patch.object(self.active.broadcast, 'update_forecast', side_effect=RuntimeError('display failed')):
            result = await self.choose({'mood': 'energy'})
        self.assertTrue(result['accepted'])
        self.assertTrue(result['delivery_pending'])
        current = self.manager.current_active('owner')
        self.assertEqual(current.selected_mood, 'energy')
        self.assertEqual(current.broadcast.state.selected_mood, 'energy')
        self.assertEqual((await self.repo.async_read('owner', authorize=lambda: True))['defaults']['mood'], 'energy')

    async def test_no_session_write_starts_nothing_and_stale_active_fails(self):
        self.manager._active_by_profile.clear()
        with self.assertRaises(SettingsCommitError):
            await self.choose({'mood': 'party'})
        result = await self.choose({'mood': 'party'}, expected_session=None)
        self.assertIsNone(result['snapshot']['session'])
        self.assertIsNone(self.manager.current_active('owner'))

    async def test_authority_and_voice_failure_are_whole_patch_rejections(self):
        with self.assertRaises(PermissionError):
            await self.choose({'persona': 'club_dj'}, authorize=lambda: False)
        def reject(_selected):
            raise ValueError('selected_voice_unavailable')
        with self.assertRaises(ValueError):
            await self.choose({'persona': 'club_dj', 'gender': 'female'}, validate_voice=reject)
        self.assertIs(self.manager.current_active('owner'), self.active)
        self.assertEqual((await self.repo.async_read('owner', authorize=lambda: True))['defaults_revision'], 0)

    async def test_queued_change_cannot_outlive_original_session_generation(self):
        async with self.manager._lock:
            task = asyncio.create_task(self.choose({'mood': 'party'}))
            await asyncio.sleep(0)
            self.manager._active_by_profile['owner'] = self.r.DJSessionRuntime(
                **{**self.active.__dict__, 'settings_generation': 'replacement-generation'})
        with self.assertRaises(SettingsCommitError):
            await task
        self.assertEqual((await self.repo.async_read('owner', authorize=lambda: True))['defaults_revision'], 0)

    async def test_accepted_voice_replay_survives_inventory_withdrawal(self):
        values = {'voice': {'kind': 'provider_voice', 'provider_id': 'tts.test', 'voice_id': 'v1'}}
        await self.choose(values)
        def withdrawn(_selected):
            raise ValueError('selected_voice_unavailable')
        result = await self.choose(values, validate_voice=withdrawn)
        self.assertTrue(result['replayed'])
        self.assertEqual(self.manager.current_active('owner').selected_voice.voice_id, 'v1')

    async def test_defaults_and_effective_voice_are_independently_validated(self):
        values = {'voice': {'kind': 'provider_voice', 'provider_id': 'tts.test', 'voice_id': 'v1'}}
        await self.choose(values)
        before = self.manager.current_active('owner')
        # Simulate a differing live choice; both typed candidates must pass the
        # pure inventory policy before the shared patch may be accepted.
        from custom_components.djconnect.domain.profile.dj_settings import VoiceSelection
        active = self.r.DJSessionRuntime(**{**before.__dict__,
            'selected_voice': VoiceSelection('provider_voice', 'tts.test', 'v2')})
        self.manager._active_by_profile['owner'] = active
        seen = []
        def validate_both(selected):
            seen.append(selected.voice.voice_id)
            if selected.voice.voice_id == 'v1':
                raise ValueError('voice_gender_conflict')
        with self.assertRaises(ValueError):
            await self.choose({'gender': 'female'}, expected_defaults=1,
                              expected_session=self.expected(active), counter=2,
                              validate_voice=validate_both)
        self.assertEqual(seen, ['v1'])
        self.assertEqual((await self.repo.async_read('owner', authorize=lambda: True))['defaults_revision'], 1)
        self.assertIs(self.manager.current_active('owner'), active)

    async def test_automatic_mood_never_overwrites_explicit_default_or_breaks_next_patch(self):
        await self.choose({'mood': 'energy'})
        await self.manager.async_update_mood(owner_profile_id='owner', session_id=self.active.session_id,
                                             selected_mood='party')
        active = self.manager.current_active('owner')
        self.assertEqual(active.selected_mood, 'party')
        self.assertEqual(active.settings_revision, 2)
        stored = await self.repo.async_read('owner', session_id=active.session_id, authorize=lambda: True)
        self.assertEqual(stored['defaults']['mood'], 'energy')
        self.assertEqual(stored['session']['settings']['mood'], 'party')
        accepted = await self.choose({'persona': 'club_dj'}, expected_defaults=1,
                                    expected_session=self.expected(active), counter=2)
        self.assertEqual(accepted['snapshot']['defaults']['mood'], 'energy')
        self.assertEqual(accepted['snapshot']['session']['settings']['mood'], 'party')

    async def test_successor_inherits_all_five_without_initialization_write(self):
        values = {'mood': 'energy', 'persona': 'festival_dj', 'presence': 'music_only',
                  'voice': {'kind': 'provider_voice', 'provider_id': 'tts.test', 'voice_id': 'v1'},
                  'gender': 'female'}
        await self.choose(values)
        await self.manager.async_end(owner_profile_id='owner', session_id=self.active.session_id)
        new = await self.manager.async_start(owner_profile_id='owner', selected_mood='chill',
                                             dj_persona=self.r.DJPersona.HOME_DJ)
        self.assertEqual(new.effective_dj_settings().as_dict(), values)
        self.assertNotEqual(new.settings_generation, self.active.settings_generation)
        self.assertEqual(new.defaults_revision, 1)
        self.assertEqual(new.broadcast.state.selected_presence, 'music_only')
        self.assertEqual((await self.repo.async_read('owner', authorize=lambda: True))['defaults_revision'], 1)
        await self.manager.async_update_mood(owner_profile_id='owner', session_id=new.session_id,
                                             selected_mood='chill')
        self.assertEqual(self.manager.current_active('owner').settings_revision, 1)
        self.assertEqual((await self.repo.async_read('owner', authorize=lambda: True))['defaults']['mood'], 'energy')

    async def test_operation_readback_survives_end_and_distinguishes_expired_absence(self):
        async def receipt(counter=1, now=None):
            return await self.manager.async_dj_settings_operation_result(
                owner_profile_id='owner', operation_id=operation(self.now, counter),
                binding='b'*64, now_ms=now or self.now, authorize=lambda: True)
        self.assertEqual((await receipt())['phase'], 'not_accepted')
        accepted = await self.choose({'mood': 'energy'})
        await self.manager.async_end(owner_profile_id='owner', session_id=self.active.session_id)
        readback = await receipt()
        self.assertEqual(readback['phase'], 'accepted')
        self.assertEqual(readback['receipt'], accepted)
        self.assertIsNone(self.manager.current_active('owner'))
        self.assertEqual((await receipt(counter=2, now=self.now+300001))['phase'], 'unknown')

    async def test_locked_reads_are_coherent_and_do_not_write(self):
        before = await self.manager.async_read_dj_settings(owner_profile_id='owner', authorize=lambda: True)
        self.assertEqual(before['session']['settings']['mood'], 'chill')
        self.assertEqual(before['defaults']['mood'], 'groove')
        for _ in range(3):
            self.assertEqual(await self.manager.async_read_dj_settings(
                owner_profile_id='owner', authorize=lambda: True), before)
        count = await self.service.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT COUNT(*) FROM djconnect_profile_dj_settings'))
        self.assertEqual(count, (0,))
