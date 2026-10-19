"""Real owner, Profile Store and SQLite migration; never map old tone to Persona."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from tests import test_profile_settings_owner as owner_tests


class LegacySettingsMigrationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        owner_tests.ProfileSettingsOwnerTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        owner_tests.ProfileSettingsOwnerTests.tearDownClass()

    async def asyncSetUp(self):
        self.owner = owner_tests.ProfileSettingsOwnerTests()
        await self.owner.asyncSetUp()
        self.hass = self.owner.hass
        self.hass.config_entries.async_entries = lambda domain: [self.owner.entry]
        self.storage = self.hass.data['djconnect']['djconnect_profile_platform']
        from tests.test_profile_storage import MemoryStore
        from custom_components.djconnect.domain.storage import household_to_storage
        self.storage._store = MemoryStore(household_to_storage(self.storage.household))
        from custom_components.djconnect.settings_migration import async_retire_activated
        from custom_components.djconnect.domain.profile.dj_settings import DJSettings
        self.retire = async_retire_activated
        self.values = DJSettings(persona='club_dj', mood='energy').as_dict()
        self.repo = self.owner.fixture.manager._settings_repository
        def update(entry, **kwargs):
            for key, value in kwargs.items():
                setattr(entry, key, value)
        self.hass.config_entries.async_update_entry = update

    async def asyncTearDown(self):
        await self.owner.asyncTearDown()

    async def legacy(self):
        from custom_components.djconnect.domain import ResponseStyle, VoiceStyle, MoodState
        profile = self.storage.household.profiles['profile-a']
        self.owner.entry.data.update(voice_profile='late_night', tts_voice='obsolete-voice',
                                     stt_engine='obsolete-stt', dj_response_prompt='old personal prompt')
        await self.storage.async_update_profile('profile-a', preferences=replace(profile.preferences,
            response_style=ResponseStyle.EXPRESSIVE, voice_style=VoiceStyle.ENERGY))
        household = self.storage.household
        profile = household.profiles['profile-a']
        await self.storage.async_save(replace(household, profiles={**household.profiles,
            'profile-a': replace(profile, mood=MoodState(value=90, zone='party'))}))

    async def test_legacy_review_requires_explicit_all_five_without_mapping(self):
        await self.legacy()
        before, status = await self.owner.read()
        self.assertEqual(status, 200, before)
        self.assertEqual(before['migration']['state'], 'choice_required')
        self.assertFalse(before['migration']['automatic_persona_mapping'])
        self.assertEqual(before['snapshot']['defaults']['persona'], 'home_dj')
        self.assertEqual(before['snapshot']['defaults']['mood'], 'groove')
        rejected, status = await self.owner.choose(before, {'mood':'chill'})
        self.assertEqual((status, rejected['error']), (409, 'settings_migration_choice_required'))
        unchanged, _ = await self.owner.read()
        self.assertEqual(unchanged['snapshot'], before['snapshot'])
        accepted, status = await self.owner.choose(before, self.values, counter=2)
        self.assertEqual(status, 200, accepted)
        self.assertEqual(accepted['snapshot']['defaults'], self.values)
        self.assertFalse(accepted['migration']['requires_review'])
        self.assertTrue(accepted['migration']['legacy_cleanup_pending'])

    async def test_conflicting_bound_device_tones_never_last_online_wins(self):
        await self.legacy()
        await self.storage.async_upsert_device('another-device', 'ios', linked_profile_id='profile-a')
        peer = SimpleNamespace(entry_id='peer-entry', data={'device_id':'another-device',
                               'voice_profile':'energy'}, options={})
        other = SimpleNamespace(entry_id='unbound-entry', data={'device_id':'unbound',
                                'voice_profile':'clean_host'}, options={})
        self.hass.config_entries.async_entries = lambda domain: [peer, self.owner.entry, other]
        before, status = await self.owner.read()
        self.assertEqual(status, 200, before)
        self.assertTrue(before['migration']['conflicting_entry_tones'])
        tones = [v['value'] for v in before['migration']['candidates'] if v['field']=='voice_profile']
        self.assertEqual(tones, ['energy', 'late_night'])
        self.assertNotIn('unbound-entry', str(before['migration']))
        self.assertEqual(before['snapshot']['defaults']['persona'], 'home_dj')

    async def test_cleanup_waits_for_acceptance_and_replay_binding_survives(self):
        await self.legacy()
        await self.retire(self.hass, self.storage, self.repo)
        self.assertIn('voice_profile', self.owner.entry.data)
        before, _ = await self.owner.read()
        accepted, status = await self.owner.choose(before, self.values)
        self.assertEqual(status, 200, accepted)
        await self.retire(self.hass, self.storage, self.repo)
        after, status = await self.owner.read()
        self.assertEqual(status, 200, after)
        self.assertEqual(after['binding'], before['binding'])
        self.assertFalse(after['migration']['legacy_cleanup_pending'])
        self.assertNotIn('voice_profile', self.owner.entry.data)
        self.assertNotIn('tts_voice', self.owner.entry.data)
        self.assertNotIn('stt_engine', self.owner.entry.data)
        self.assertNotIn('dj_response_prompt', self.owner.entry.data)
        from custom_components.djconnect.domain.storage import household_to_storage, household_from_storage
        stored = household_to_storage(self.storage.household)
        profile = next(p for p in stored['household']['profiles'] if p['profile_id']=='profile-a')
        self.assertNotIn('voice_style', profile['preferences'])
        self.assertNotIn('response_style', profile['preferences'])
        reloaded = household_to_storage(household_from_storage(stored))
        self.assertEqual(stored, reloaded)
        replay, status = await self.owner.choose(before, self.values)
        self.assertEqual(status, 200, replay)
        self.assertTrue(replay['replayed'])
        await self.retire(self.hass, self.storage, self.repo)
        self.assertEqual(after['snapshot'], (await self.owner.read())[0]['snapshot'])

    async def test_entry_cleanup_failure_remains_visible_and_retry_is_safe(self):
        await self.legacy()
        before, _ = await self.owner.read()
        await self.owner.choose(before, self.values)
        update = self.hass.config_entries.async_update_entry
        with patch.object(self.hass.config_entries, 'async_update_entry', side_effect=OSError('fixture storage failure')):
            with self.assertRaises(OSError):
                await self.retire(self.hass, self.storage, self.repo)
        after, status = await self.owner.read()
        self.assertEqual(status, 200, after)
        self.assertEqual(after['snapshot']['defaults'], self.values)
        self.assertTrue(after['migration']['legacy_cleanup_pending'])
        self.hass.config_entries.async_update_entry = update
        await self.retire(self.hass, self.storage, self.repo)
        self.assertFalse((await self.owner.read())[0]['migration']['legacy_cleanup_pending'])

    async def test_failed_profile_cleanup_never_undoes_an_accepted_choice(self):
        from unittest.mock import AsyncMock
        await self.legacy()
        before, _ = await self.owner.read()
        await self.owner.choose(before, self.values)
        with patch.object(self.storage._store, 'async_save', new=AsyncMock(side_effect=OSError('fixture save failure'))):
            with self.assertRaises(OSError):
                await self.retire(self.hass, self.storage, self.repo)
        retained, status = await self.owner.read()
        self.assertEqual(status, 200, retained)
        self.assertTrue(retained['migration']['legacy_cleanup_pending'])
        self.assertEqual(retained['snapshot']['defaults'], self.values)
        # An accepted Profile is not forced back through initial migration.
        next_value, status = await self.owner.choose(retained, {'mood':'party'}, counter=2)
        self.assertEqual(status, 200, next_value)
        await self.retire(self.hass, self.storage, self.repo)
        after, status = await self.owner.read()
        self.assertEqual(status, 200, after)
        self.assertEqual(after['snapshot']['defaults']['mood'], 'party')
        self.assertFalse(after['migration']['legacy_cleanup_pending'])

    async def test_import_cannot_use_a_foreign_retirement_marker_as_authority(self):
        from custom_components.djconnect.profile_export import async_export_profile, async_import_profile
        exported = await async_export_profile(self.storage, 'profile-a')
        exported['profile']['metadata']['dj_settings_version'] = 2
        exported['profile']['preferences'].update(voice_style='energy', response_style='expressive')
        imported = await async_import_profile(self.storage, exported, reassign_id=True)
        profile = self.storage.household.profiles[imported['profile_id']]
        self.assertEqual(profile.metadata.dj_settings_version, 1)
        from custom_components.djconnect.settings_migration import assessment
        state = assessment(self.hass, self.storage.household, profile, activated=False)
        self.assertTrue(state['requires_review'])
        self.assertFalse(state['automatic_persona_mapping'])

    async def test_waiting_partial_choice_rechecks_committed_profile_preferences(self):
        import asyncio
        from custom_components.djconnect.domain import ResponseStyle
        before, _ = await self.owner.read()
        entered, release = asyncio.Event(), asyncio.Event()
        save = self.storage._store.async_save

        async def held_save(value):
            entered.set()
            await release.wait()
            await save(value)

        profile = self.storage.household.profiles['profile-a']
        with patch.object(self.storage._store, 'async_save', new=held_save):
            changing = asyncio.create_task(self.storage.async_update_profile(
                'profile-a', preferences=replace(profile.preferences, response_style=ResponseStyle.EXPRESSIVE)))
            await asyncio.wait_for(entered.wait(), 2)
            choosing = asyncio.create_task(self.owner.choose(before, {'mood':'chill'}))
            await asyncio.sleep(0)
            self.assertFalse(choosing.done())
            release.set()
            await changing
            rejected, status = await choosing
        self.assertEqual((status, rejected['error']), (409, 'settings_migration_choice_required'))
        self.assertFalse((await self.owner.read())[0]['snapshot']['activated'])

    async def test_entry_change_after_sql_staging_rolls_back_partial_acceptance(self):
        import threading
        before, _ = await self.owner.read()
        run = self.repo._async_in_transaction
        loop_thread = threading.get_ident()

        async def mutate_before_admission(operation, **kwargs):
            final = kwargs['finalize_authorize']
            def changed_entry():
                self.assertEqual(threading.get_ident(), loop_thread)
                self.owner.entry.data['voice_profile'] = 'energy'
                return final()
            return await run(operation, **{**kwargs, 'finalize_authorize': changed_entry})

        with patch.object(self.repo, '_async_in_transaction', new=mutate_before_admission):
            rejected, status = await self.owner.choose(before, {'mood':'chill'})
        self.assertEqual((status, rejected['error']), (409, 'settings_migration_choice_required'))
        after, _ = await self.owner.read()
        self.assertEqual(before['snapshot'], after['snapshot'])
        # Same operation is genuinely unaccepted: an explicit five-field retry
        # succeeds rather than conflicting with a falsely persisted receipt.
        accepted, status = await self.owner.choose(before, self.values)
        self.assertEqual(status, 200, accepted)
        self.assertFalse(accepted['replayed'])

    async def test_accepted_partial_receipt_survives_later_legacy_evidence(self):
        before, _ = await self.owner.read()
        accepted, status = await self.owner.choose(before, {'mood':'chill'})
        self.assertEqual(status, 200, accepted)
        self.owner.entry.data['voice_profile'] = 'energy'
        replay, status = await self.owner.choose(before, {'mood':'chill'})
        self.assertEqual(status, 200, replay)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['snapshot'], accepted['snapshot'])

    async def test_new_factory_profile_omits_retired_keys_without_activating_settings(self):
        from custom_components.djconnect.domain.storage import household_to_storage
        from custom_components.djconnect.domain import VoiceStyle
        profile = await self.storage.async_create_profile('New factory', profile_id='new-factory')
        self.assertEqual(profile.metadata.dj_settings_version, 2)
        stored = household_to_storage(self.storage.household)
        factory = next(p for p in stored['household']['profiles'] if p['profile_id']=='new-factory')
        self.assertNotIn('voice_style', factory['preferences'])
        self.assertNotIn('response_style', factory['preferences'])
        snapshot = await self.repo.async_read('new-factory', authorize=lambda: True)
        self.assertFalse(snapshot['activated'])
        legacy = await self.storage.async_create_profile('Explicit legacy', profile_id='new-legacy',
                                                        voice_style=VoiceStyle.ENERGY)
        self.assertEqual(legacy.metadata.dj_settings_version, 1)

    async def test_historical_import_allows_absent_metadata_but_rejects_wrong_shape(self):
        from custom_components.djconnect.profile_export import async_export_profile, async_import_profile, ProfileExportError
        exported = await async_export_profile(self.storage, 'profile-a')
        exported['profile']['metadata'] = None
        imported = await async_import_profile(self.storage, exported, reassign_id=True)
        self.assertEqual(self.storage.household.profiles[imported['profile_id']].metadata.dj_settings_version, 1)
        exported['profile']['metadata'] = ['not', 'metadata']
        before = self.storage.household
        with self.assertRaisesRegex(ProfileExportError, 'invalid profile metadata'):
            await async_import_profile(self.storage, exported, reassign_id=True)
        self.assertEqual(self.storage.household, before)
