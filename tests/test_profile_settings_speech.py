"""One accepted speech path; only external agent/provider boundaries are fixtures."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
import unittest

from tests import test_ask_dj_contextual_dialogue as dialogue
from tests.test_profile_dj_settings_persistence import operation


class SharedSettingsSpeechTests(unittest.IsolatedAsyncioTestCase):
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
        from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
        from custom_components.djconnect import profile_settings, session_speech
        self.settings, self.speech = profile_settings, session_speech
        self.f.fixture.manager._settings_repository = ProfileDJSettingsRepository(self.f.fixture.service)
        self.entry = SimpleNamespace(entry_id='owner-entry', data={**self.runtime.config,
            'device_token': self.runtime.device_token}, options={}, disabled_by=None,
            state=SimpleNamespace(value='loaded'))
        self.runtime.entry = self.entry
        self.hass.config_entries.async_get_entry = lambda eid: self.entry if eid == self.entry.entry_id else None
        self.now = int(datetime.now(UTC).timestamp()*1000)

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def choose(self, voice, *, counter=1, extra=None):
        before, status = await self.settings.async_handle_settings(self.hass,
            {**self.f.identity, 'contract_version': 3}, headers=self.f.headers)
        self.assertEqual(status, 200, before)
        session = before['snapshot']['session']
        result, status = await self.settings.async_handle_settings(self.hass,
            {**self.f.identity, 'contract_version': 3, 'binding': before['binding'],
             'operation_id': operation(self.now, counter), 'expected_defaults_revision': before['snapshot']['defaults_revision'],
             'expected_session': {key:session[key] for key in ('session_id','generation','revision')} if session else None,
             'patch': {'voice': {'kind': 'provider_voice', 'provider_id': 'tts.fixture_cloud', 'voice_id': voice},
                       **(extra or {})}},
            headers=self.f.headers, write=True)
        self.assertEqual(status, 200, result)
        return result

    async def contribution(self):
        answer, status = await self.f.request('What is an ostinato?', identifier='shared-voice-source')
        self.assertEqual(status, 200, answer)
        return {**self.f.identity, 'contract_version': 3, 'processor': 'ha_configured',
                'intent': 'manual', 'target': 'local',
                'reference': answer['session_speech']['reference']}

    def provider(self):
        stack, entity, pipeline, calls, processor = self.f.generic_tts()
        entity.async_get_supported_voices = lambda locale: [
            SimpleNamespace(voice_id='marin', name='Marin'), SimpleNamespace(voice_id='cedar', name='Cedar')]
        return stack, entity, pipeline, calls, processor

    async def test_shared_voice_prepares_exact_provider_and_legacy_cannot_override(self):
        payload = await self.contribution()
        stack, entity, pipeline, calls, _ = self.provider()
        with stack:
            await self.choose('cedar')
            result, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, result)
            self.assertEqual(result['session_speech']['effective_voice']['voice_id'], 'cedar')
            self.assertEqual(result['session_speech']['settings_contract_version'], 3)
            self.assertEqual(calls[-1][2]['voice'], 'cedar')
            self.assertEqual(pipeline.tts_voice, 'marin')
            self.assertEqual(entity.default_options['voice'], 'marin')
            old, status = await self.speech.async_handle_prepare(self.hass,
                {**{k:v for k,v in payload.items() if k not in ('intent','target')},
                 'contract_version': 1, 'voice_preference': 'default'}, headers=self.f.headers)
            self.assertEqual((status, old['error']), (426, 'settings_contract_upgrade_required'))
            self.assertEqual(len(calls), 1)

    async def test_general_ask_dj_uses_confirmed_profile_style_not_legacy_numeric_init(self):
        stack, entity, pipeline, calls, _ = self.provider()
        with stack:
            await self.choose('cedar', extra={'persona': 'festival_dj', 'mood': 'party'})
            answer, status = await self.f.request('What is an ostinato?', identifier='shared-style',
                mood=0, dj_persona='club_dj', speech_contract_version=3, audio_response='always')
            self.assertEqual(status, 200, answer)
            style = answer['conversation']['style']
            self.assertEqual((style['persona'], style['mood'], style['mood_basis']),
                             ('festival_dj', 'party', 'confirmed_profile_defaults'))
            self.assertNotIn('response_style', style)
            self.assertEqual(answer['audio_delivery']['state'], 'deferred')
            self.assertIsNone(self.f.fixture.manager.current_active('profile-a'))
            self.assertEqual(len(self.f.prompts), 1)
            self.assertEqual(calls, [])
            self.assertEqual(len(self.f.prompts), 1)

    async def test_voice_change_during_synthesis_discards_old_audio_without_repeating_turn(self):
        payload = await self.contribution()
        stack, entity, pipeline, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        original = entity.async_get_tts_audio
        async def delayed(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        entity.async_get_tts_audio = delayed
        with stack:
            await self.choose('marin')
            task = asyncio.create_task(self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers))
            await asyncio.wait_for(entered.wait(), 2)
            await self.choose('cedar', counter=2)
            release.set()
            denied, status = await asyncio.wait_for(task, 2)
            self.assertEqual(status, 404, denied)
            current, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, current)
            self.assertEqual(current['session_speech']['effective_voice']['voice_id'], 'cedar')
            self.assertEqual(len(self.f.prompts), 1)
            self.assertEqual([call[2]['voice'] for call in calls], ['marin', 'cedar'])

    async def test_voice_change_rejects_old_cached_audio_and_withdrawal_preserves_choice(self):
        payload = await self.contribution()
        stack, entity, pipeline, calls, _ = self.provider()
        with stack:
            await self.choose('marin')
            first, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, first)
            asset = first['session_speech']['audio_reference']['asset_id']
            await self.choose('cedar', counter=2)
            old, status = await self.speech.async_handle_audio(self.hass,
                {**self.f.identity, 'contract_version': 1, 'asset_id': asset}, headers=self.f.headers)
            self.assertEqual(status, 404, old)
            pipeline.tts_engine = 'tts.other_provider'
            missing, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, missing)
            self.assertFalse(missing['session_speech']['manual_allowed'])
            snapshot = await self.f.fixture.manager.async_read_dj_settings(
                owner_profile_id='profile-a', authorize=lambda: True)
            self.assertEqual(snapshot['defaults']['voice']['voice_id'], 'cedar')
            self.assertEqual(snapshot['defaults_revision'], 2)
            self.assertEqual(len(calls), 1)

    async def test_text_only_preserves_voice_but_prevents_synthesis_and_replay_assets(self):
        payload = await self.contribution()
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.choose('marin')
            first, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, first)
            asset = first['session_speech']['audio_reference']['asset_id']
            chosen = await self.choose('marin', counter=2, extra={'announcement_output':'text_only'})
            self.assertEqual(chosen['snapshot']['defaults']['voice']['voice_id'], 'marin')
            self.assertEqual(chosen['announcement_output']['voice_applicability'], 'not_applicable_text_only')
            denied, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, denied)
            self.assertEqual(denied['session_speech']['reason'], 'announcement_text_only')
            self.assertFalse(denied['session_speech']['manual_allowed'])
            item, status = await self.speech.async_handle_audio(self.hass,
                {**self.f.identity, 'contract_version':1, 'asset_id':asset}, headers=self.f.headers)
            self.assertEqual(status, 404)
            self.assertIsNone(item)
            self.assertEqual(len(calls), 1)
            answer, status = await self.f.request('What is a major chord?', identifier='text-only-source',
                speech_contract_version=3, audio_response='always')
            self.assertEqual(status, 200, answer)
            self.assertFalse(answer['session_speech']['manual_allowed'])
            self.assertEqual(answer['session_speech']['reason'], 'announcement_text_only')
            self.assertEqual(answer['audio_delivery']['state'], 'not_applicable')
            self.assertEqual(len(calls), 1)

    async def test_output_change_during_synthesis_discards_pending_audio(self):
        payload = await self.contribution()
        stack, entity, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        synthesize = entity.async_get_tts_audio
        async def held(*args):
            entered.set()
            await release.wait()
            return await synthesize(*args)
        entity.async_get_tts_audio = held
        with stack:
            await self.choose('marin')
            pending = asyncio.create_task(self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers))
            await asyncio.wait_for(entered.wait(), 2)
            await self.choose('marin', counter=2, extra={'announcement_output':'text_only'})
            release.set()
            result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual(status, 404, result)
            self.assertNotIn('audio_reference', result)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(self.f.prompts), 1)

    async def test_speaker_only_manual_local_is_allowed_but_never_silent_target_fallback(self):
        payload = await self.contribution()
        stack, _, _, calls, _ = self.provider()
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.owned_speaker'
        self.hass.states = SimpleNamespace(get=lambda entity_id: SimpleNamespace(
            state='idle', attributes={'supported_features':512}) if entity_id=='media_player.owned_speaker' else None)
        with stack:
            await self.choose('marin', extra={'announcement_output':'ha_speaker'})
            local, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, local)
            self.assertEqual(local['session_speech']['audio_state'], 'ready')
            auto, status = await self.speech.async_handle_prepare(self.hass,
                {**payload, 'intent':'automatic'}, headers=self.f.headers)
            self.assertEqual(status, 200, auto)
            self.assertEqual(auto['session_speech']['reason'], 'automatic_target_not_allowed')
            speaker, status = await self.speech.async_handle_prepare(self.hass,
                {**payload, 'target':'ha_speaker'}, headers=self.f.headers)
            self.assertEqual(status, 200, speaker)
            self.assertEqual(speaker['session_speech']['reason'], 'use_speech_play_operation')
            self.assertEqual(len(calls), 1)

    async def test_legacy_generation_gate_cannot_bypass_text_only(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import dj_response, speech_processor
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.choose('marin', extra={'announcement_output':'text_only'})
            with patch.object(dj_response, 'create_tts_audio', new=AsyncMock()) as legacy, \
                    patch.object(speech_processor, 'synthesize', new=AsyncMock()) as shared:
                result = await dj_response.async_create_dj_audio_url(self.hass, self.runtime, 'An old device reply')
            self.assertIsNone(result)
            legacy.assert_not_awaited()
            shared.assert_not_awaited()

    async def test_old_disabled_flag_needs_explicit_review_then_cannot_override_shared_output(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import dj_response
        from custom_components.djconnect.domain.profile.dj_settings import DJSettings
        payload = await self.contribution()
        self.runtime.config['dj_response_enabled'] = False
        self.entry.data['dj_response_enabled'] = False
        self.hass.config_entries.async_entries = lambda domain:[self.entry]
        stack, _, _, calls, _ = self.provider()
        with stack:
            pending, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual((status, pending['session_speech']['reason']), (200, 'settings_migration_choice_required'))
            with patch.object(dj_response, '_async_ha_base_url', new=AsyncMock(return_value='https://ha-owned.invalid')):
                self.assertIsNone(await dj_response.async_create_dj_audio_url(self.hass, self.runtime, 'Old disabled route'))
                self.assertEqual(calls, [])
                await self.choose('cedar', extra=DJSettings().as_dict())
                url = await dj_response.async_create_dj_audio_url(self.hass, self.runtime, 'Explicitly enabled canonical output')
                self.assertIsNotNone(url)
                self.assertEqual(len(calls), 1)
                self.assertEqual(self.runtime.config['dj_response_enabled'], False)  # No silent old-setting rewrite.

    def legacy_disabled_evidence(self):
        self.runtime.config['dj_response_enabled'] = False
        self.entry.data['dj_response_enabled'] = False
        self.hass.config_entries.async_entries = lambda domain: [self.entry]

    async def test_prepare_one_cannot_bypass_pending_legacy_output_review(self):
        payload = await self.contribution()
        payload = {**{key: value for key, value in payload.items() if key not in ('intent', 'target')},
                   'contract_version': 1, 'voice_preference': 'default'}
        self.legacy_disabled_evidence()
        stack, _, _, calls, _ = self.provider()
        with stack:
            result, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
        self.assertEqual((status, result['session_speech']['reason']),
                         (200, 'settings_migration_choice_required'))
        self.assertEqual(calls, [])

    async def test_factory_reads_and_old_prepare_do_not_activate_new_contract(self):
        payload = await self.contribution()
        old = {**{key: value for key, value in payload.items() if key not in ('intent', 'target')},
               'contract_version': 1, 'voice_preference': 'default'}
        stack, _, _, calls, _ = self.provider()
        with stack:
            for _ in range(2):
                result, status = await self.settings.async_handle_settings(self.hass,
                    {**self.f.identity, 'contract_version': 3}, headers=self.f.headers)
                self.assertEqual(status, 200, result)
                self.assertFalse(result['snapshot']['activated'])
                self.assertEqual(result['snapshot']['defaults_revision'], 0)
            prepared, status = await self.speech.async_handle_prepare(self.hass, old, headers=self.f.headers)
            self.assertEqual(status, 200, prepared)
            self.assertEqual(prepared['session_speech']['audio_state'], 'ready')
            await self.choose('cedar')
            denied, status = await self.speech.async_handle_prepare(self.hass, old, headers=self.f.headers)
            self.assertEqual((status, denied['error']), (426, 'settings_contract_upgrade_required'))
            self.assertEqual(len(calls), 1)

    async def test_legacy_output_review_revokes_inflight_and_existing_private_audio(self):
        payload = await self.contribution()
        stack, entity, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        synthesize = entity.async_get_tts_audio
        async def held(*args):
            entered.set()
            await release.wait()
            return await synthesize(*args)
        with stack:
            first, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, first)
            asset = first['session_speech']['audio_reference']['asset_id']
            # A different authorized contribution ensures this is a real
            # synthesis race, rather than a cache hit for the first asset.
            answer, status = await self.f.request('What is a major chord?', identifier='legacy-race-source')
            self.assertEqual(status, 200, answer)
            entity.async_get_tts_audio = held
            pending = asyncio.create_task(self.speech.async_handle_prepare(self.hass,
                {**payload, 'reference': answer['session_speech']['reference']}, headers=self.f.headers))
            await asyncio.wait_for(entered.wait(), 2)
            self.legacy_disabled_evidence()
            release.set()
            result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual(status, 404, result)
            item, status = await self.speech.async_handle_audio(self.hass,
                {**self.f.identity, 'contract_version': 1, 'asset_id': asset}, headers=self.f.headers)
            self.assertEqual(status, 404)
            self.assertIsNone(item)
            self.assertEqual(len(calls), 2)

    async def test_legacy_url_admission_rechecks_new_output_evidence(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import dj_response
        stack, entity, _, _, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        synthesize = entity.async_get_tts_audio
        async def held(*args):
            entered.set()
            await release.wait()
            return await synthesize(*args)
        entity.async_get_tts_audio = held
        with stack, patch.object(dj_response, '_async_ha_base_url',
                                 new=AsyncMock(return_value='https://ha-owned.invalid')):
            pending = asyncio.create_task(dj_response.async_create_dj_audio_url(
                self.hass, self.runtime, 'A bounded legacy reply'))
            await asyncio.wait_for(entered.wait(), 2)
            self.legacy_disabled_evidence()
            release.set()
            self.assertIsNone(await asyncio.wait_for(pending, 2))

    async def test_profile_tone_change_revokes_inflight_and_existing_private_audio(self):
        from dataclasses import replace
        from custom_components.djconnect.domain import ResponseStyle
        from custom_components.djconnect.profile_context import profile_storage
        payload = await self.contribution()
        stack, entity, _, _, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        synthesize = entity.async_get_tts_audio
        async def held(*args):
            entered.set()
            await release.wait()
            return await synthesize(*args)
        with stack:
            first, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, first)
            asset = first['session_speech']['audio_reference']['asset_id']
            answer, status = await self.f.request('What is a major chord?', identifier='profile-tone-race-source')
            self.assertEqual(status, 200, answer)
            entity.async_get_tts_audio = held
            pending = asyncio.create_task(self.speech.async_handle_prepare(self.hass,
                {**payload, 'reference': answer['session_speech']['reference']}, headers=self.f.headers))
            await asyncio.wait_for(entered.wait(), 2)
            storage = profile_storage(self.hass)
            profile = storage.household.profiles['profile-a']
            await storage.async_update_profile('profile-a', preferences=replace(
                profile.preferences, response_style=ResponseStyle.EXPRESSIVE))
            release.set()
            result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual(status, 404, result)
            item, status = await self.speech.async_handle_audio(self.hass,
                {**self.f.identity, 'contract_version': 1, 'asset_id': asset}, headers=self.f.headers)
            self.assertEqual(status, 404)
            self.assertIsNone(item)

    async def test_legacy_device_url_uses_exact_shared_voice_and_later_revokes(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import dj_response
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.choose('cedar')
            with patch.object(dj_response, '_async_ha_base_url', new=AsyncMock(return_value='https://ha-owned.invalid')):
                url = await dj_response.async_create_dj_audio_url(self.hass, self.runtime, 'A bounded device reply')
            self.assertIsNotNone(url)
            self.assertEqual(calls[-1][2]['voice'], 'cedar')
            token = url.rsplit('/', 1)[-1].split('.')[0]
            self.assertEqual(dj_response.get_tts_audio(self.hass, token)[0], 200)
            await self.choose('cedar', counter=2, extra={'announcement_output':'text_only'})
            self.assertEqual(dj_response.get_tts_audio(self.hass, token), (404, None))
            self.assertEqual(len(calls), 1)

    async def test_roaming_output_overrides_legacy_payload_and_removes_stale_response_audio(self):
        from unittest.mock import AsyncMock
        from custom_components.djconnect.announcements import async_apply_announcement_output
        stack, _, _, _, _ = self.provider()
        retained = {'role':'assistant', 'text':'Unchanged accepted text', 'audio_url':'https://old.invalid/audio.mp3'}
        with stack:
            await self.choose('marin', extra={'announcement_output':'text_only'})
            response = {'text':'Unchanged accepted text', 'audio_url':'https://old.invalid/audio.mp3',
                        'assistant_message':retained, 'messages':[retained]}
            factory = AsyncMock(return_value='https://must-not-be-used.invalid/audio.mp3')
            result = await async_apply_announcement_output(self.hass, self.runtime, response,
                payload={'dj_announcement_output':'both'}, generate_audio=True, audio_url_factory=factory)
            factory.assert_not_awaited()
            self.assertEqual(result['announcement']['output'], 'text_only')
            self.assertNotIn('audio_url', result)
            self.assertNotIn('audio_url', result['assistant_message'])
            self.assertNotIn('audio_url', result['messages'][0])
            self.assertEqual(result['messages'][0]['text'], retained['text'])
            self.assertIn('audio_url', retained)  # A read projection never rewrites history.

    async def test_unscoped_pre_upgrade_asset_cannot_bypass_connected_profile_policy(self):
        from custom_components.djconnect import dj_response
        token = dj_response.store_tts_audio(self.hass, b'legacy-fixture', content_type='audio/mpeg', extension='mp3')
        self.assertEqual(dj_response.get_tts_audio(self.hass, token), (404, None))

    async def test_legacy_audio_withdraws_on_loaded_entry_token_and_generation_changes(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import dj_response
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.choose('cedar')
            for change in ('unload', 'remove', 'token', 'generation'):
                with self.subTest(change=change):
                    with patch.object(dj_response, '_async_ha_base_url', new=AsyncMock(return_value='https://ha-owned.invalid')):
                        url = await dj_response.async_create_dj_audio_url(self.hass, self.runtime, 'An accepted device reply')
                    token = url.rsplit('/', 1)[-1].split('.')[0]
                    self.assertEqual(dj_response.get_tts_audio(self.hass, token)[0], 200)
                    old_data = dict(self.entry.data)
                    if change == 'unload':
                        self.entry.state = 'not_loaded'
                    elif change == 'remove':
                        self.hass.data['djconnect'].pop(self.entry.entry_id)
                    elif change == 'token':
                        self.entry.data['device_token'] = 'synthetic-rotated'
                        self.runtime.device_token = 'synthetic-rotated'
                    else:
                        self.runtime._receiver_end_generation = 1
                    self.assertEqual(dj_response.get_tts_audio(self.hass, token), (404, None))
                    self.entry.state = 'loaded'
                    self.hass.data['djconnect'][self.entry.entry_id] = self.runtime
                    self.entry.data = old_data
                    self.runtime.device_token = old_data['device_token']
                    self.runtime._receiver_end_generation = 0

    async def test_pending_legacy_synthesis_drops_bytes_after_entry_unload(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import dj_response
        stack, entity, _, calls, _ = self.provider()
        original = entity.async_get_tts_audio
        async def unloaded(*args):
            result = await original(*args)
            self.entry.state = 'not_loaded'
            return result
        entity.async_get_tts_audio = unloaded
        with stack:
            await self.choose('cedar')
            with patch.object(dj_response, '_async_ha_base_url', new=AsyncMock(return_value='https://ha-owned.invalid')):
                self.assertIsNone(await dj_response.async_create_dj_audio_url(self.hass, self.runtime, 'Bounded reply'))
            self.assertEqual(len(calls), 1)
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))

    async def test_target_change_during_generation_never_dispatches_old_or_new_speaker(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import announcements
        stack, _, _, _, _ = self.provider()
        with stack, patch.object(announcements, 'validate_announcement_speaker', return_value=None):
            self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.original'
            await self.choose('cedar', extra={'announcement_output':'both'})
            async def changing(*args):
                self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.replacement'
                return 'https://ha-owned.invalid/audio.mp3'
            dispatch = AsyncMock()
            self.hass.services = SimpleNamespace(async_call=dispatch)
            result = await announcements.async_apply_announcement_output(self.hass, self.runtime,
                {'text':'Bounded announcement'}, payload={}, generate_audio=True, audio_url_factory=changing)
            dispatch.assert_not_awaited()
            self.assertNotIn('audio_url', result)
            self.assertIn('announcement_settings_changed', result['announcement']['warnings'])

    async def test_speaker_replay_uses_existing_operation_owner_and_revocable_bounded_media_grant(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import dj_response, hybrid_service, speaker_delivery
        from tests.test_transport_operation_journal import Store, identifier
        stack, _, _, calls, _ = self.provider()
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.owned_speaker'
        self.hass.states = SimpleNamespace(get=lambda _: SimpleNamespace(state='idle', attributes={'supported_features':512}))
        with stack:
            await self.choose('marin', extra={'announcement_output':'ha_speaker'})
            session, moment, _ = await self.f.selected_credit()
            authority = await hybrid_service.PairedAuthority.resolve(self.hass, self.f.identity, self.f.headers)
            store = Store()
            operations = hybrid_service.HybridOperations(self.hass, store)
            request = {'contract_version':1, 'operation_id':identifier(self.now),
                'operation_epoch':operations.journal.epoch, 'operation':'session/speech/play',
                'payload': {'contract_version':3, 'processor':'ha_configured', 'intent':'manual',
                            'target':'ha_speaker', 'reference': {'session_id':session.session_id, 'moment_id':moment.moment_id}}}
            sent = []
            async def deliver(*args, **kwargs):
                sent.append(args[2]['media_content_id'])
            self.hass.services = SimpleNamespace(async_call=deliver)
            try:
                with patch.object(speaker_delivery, '_async_ha_base_url', new=AsyncMock(return_value='https://ha-owned.invalid')):
                    first, status = await operations.execute(authority, request, transport='http')
                    repeated, repeated_status = await operations.execute(authority, request, transport='websocket')
                self.assertEqual((status, repeated_status), (200, 200), first)
                self.assertEqual(first['delivery']['ha_speaker'], 'queued')
                self.assertNotIn('audio_reference', first['session_speech'])
                self.assertEqual(repeated['operation_receipt']['phase'], 'confirmed')
                self.assertEqual((len(sent), len(calls)), (1, 1))
                asset, grant = sent[0].rsplit('/', 2)[-2:]
                self.assertEqual(dj_response.get_tts_audio(self.hass, asset), (404, None))
                self.assertIsNone(dj_response.get_speaker_media(self.hass, asset, 'wrong'))
                for _ in range(4):
                    self.assertIsNotNone(dj_response.get_speaker_media(self.hass, asset, grant))
                self.assertIsNone(dj_response.get_speaker_media(self.hass, asset, grant))
                self.assertNotIn(grant, str(store.data))
                item = dj_response.get_private_tts_audio(self.hass, asset, 'profile-a')
                fresh = dj_response.grant_speaker_media(self.hass, asset, 'profile-a', item.admission)
                await self.f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=session.session_id)
                self.assertIsNone(dj_response.get_speaker_media(self.hass, asset, fresh))
            finally:
                await operations.close()

    async def test_speaker_media_deadline_survives_wall_clock_rollback(self):
        from unittest.mock import patch
        import time
        from custom_components.djconnect import dj_response
        payload = await self.contribution()
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.choose('marin')
            prepared, status = await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)
            self.assertEqual(status, 200, prepared)
            asset = prepared['session_speech']['audio_reference']['asset_id']
            item = dj_response.get_private_tts_audio(self.hass, asset, 'profile-a')
            grant = dj_response.grant_speaker_media(self.hass, asset, 'profile-a', item.admission)
            deadline = item.speaker_grants[grant]['deadline']
            wall = time.time()
            with patch.object(dj_response.time, 'time', return_value=wall-60), \
                    patch.object(dj_response.time, 'monotonic', return_value=deadline+1):
                self.assertIs(dj_response.get_private_tts_audio(self.hass, asset, 'profile-a'), item)
                self.assertIsNone(dj_response.get_speaker_media(self.hass, asset, grant))

    async def test_automatic_speaker_only_new_publication_no_client_replay_or_catchup(self):
        from dataclasses import replace
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import hybrid_service, speaker_delivery
        from tests.test_transport_operation_journal import Store
        stack, _, _, calls, _ = self.provider()
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.owned_speaker'
        self.hass.states = SimpleNamespace(get=lambda _: SimpleNamespace(state='idle', attributes={'supported_features':512}))
        tasks = []
        release = asyncio.Event()
        release.set()
        def schedule(coroutine, name):
            async def held():
                await release.wait()
                return await coroutine
            task = asyncio.create_task(held())
            tasks.append(task)
            return task
        self.hass.async_create_task = schedule
        journal = hybrid_service.HybridOperations(self.hass, Store())
        self.hass.data['djconnect']['hybrid_operation_manager'] = journal
        dispatch = AsyncMock()
        self.hass.services = SimpleNamespace(async_call=dispatch)
        try:
            with stack, patch.object(speaker_delivery, '_async_ha_base_url', new=AsyncMock(return_value='https://ha-owned.invalid')):
                await self.choose('marin', extra={'announcement_output':'ha_speaker'})
                session, original, _ = await self.f.selected_credit()
                class WireHeaders(dict):
                    # The real HA acceptance sends lowercase wire headers.
                    # Lightweight units do not install aiohttp/multidict.
                    def get(self, name, default=None):
                        return super().get(name.lower(), default)
                speaker_delivery.connect_automatic(self.hass, self.runtime, session,
                    {**self.f.identity, 'locale':'en', 'mood':'groove'},
                    WireHeaders({'authorization':self.f.headers['Authorization']}))
                session.broadcast.publish_moment(original)
                self.assertEqual(tasks, [])  # Attaching and old duplicate publications never catch up.
                # Callback unit seam: clone a previously qualified immutable
                # contribution; the actual HA test proves the full opening chain.
                next_moment = replace(original, moment_id=original.moment_id+'-new')
                session.broadcast.publish_moment(next_moment)
                session.broadcast.publish_moment(next_moment)
                await asyncio.gather(*tasks)
                self.assertEqual((len(tasks), dispatch.await_count, len(calls)), (1, 1, 1))
                authority = await hybrid_service.PairedAuthority.resolve(self.hass, self.f.identity, self.f.headers)
                denied, status = await speaker_delivery.async_play(self.hass, authority,
                    {**self.f.identity, 'contract_version':3, 'processor':'ha_configured', 'intent':'automatic',
                     'target':'ha_speaker', 'reference': {'session_id':session.session_id, 'moment_id':next_moment.moment_id}})
                self.assertEqual((status, denied['error']), (409, 'automatic_speech_requires_publication'))
                pending = replace(original, moment_id=original.moment_id+'-pending')
                release.clear()
                session.broadcast.publish_moment(pending)
                # Change before the scheduled job is admitted; no old audio.
                await self.choose('marin', counter=2, extra={'announcement_output':'text_only'})
                release.set()
                await asyncio.gather(*tasks)
                self.assertEqual(dispatch.await_count, 1)
                await self.choose('marin', counter=3, extra={'announcement_output':'ha_speaker'})
                self.assertEqual(len(tasks), 2)
        finally:
            await journal.close()

    async def test_both_target_keeps_local_ready_when_speaker_becomes_unavailable(self):
        from unittest.mock import AsyncMock
        from custom_components.djconnect import hybrid_service, speaker_delivery
        stack, _, _, calls, _ = self.provider()
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.owned_speaker'
        self.hass.states = SimpleNamespace(get=lambda _: SimpleNamespace(state='idle', attributes={'supported_features':512}))
        with stack:
            await self.choose('marin', extra={'announcement_output':'both'})
            session, moment, _ = await self.f.selected_credit()
            self.hass.states.get = lambda _: None
            dispatch = AsyncMock()
            self.hass.services = SimpleNamespace(async_call=dispatch)
            authority = await hybrid_service.PairedAuthority.resolve(self.hass, self.f.identity, self.f.headers)
            result, status = await speaker_delivery.async_play(self.hass, authority,
                {**self.f.identity, 'contract_version':3, 'processor':'ha_configured', 'intent':'manual',
                 'target':'both', 'reference': {'session_id':session.session_id, 'moment_id':moment.moment_id}})
            self.assertEqual(status, 200, result)
            self.assertEqual(result['delivery'], {'ha_speaker':'unavailable',
                'speaker_reason':'announcement_speaker_not_found', 'local':'ready', 'audible':'not_proven'})
            self.assertIn('audio_reference', result['session_speech'])
            self.assertEqual(len(calls), 1)
            dispatch.assert_not_awaited()

    async def test_uncertain_both_target_dispatch_preserves_local_result_and_never_retries_effect(self):
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect import hybrid_service, speaker_delivery
        from tests.test_transport_operation_journal import Store, identifier
        stack, _, _, calls, _ = self.provider()
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.owned_speaker'
        self.hass.states = SimpleNamespace(get=lambda _: SimpleNamespace(state='idle', attributes={'supported_features':512}))
        journal = hybrid_service.HybridOperations(self.hass, Store())
        dispatch = AsyncMock(side_effect=TimeoutError('External sink acceptance unknown'))
        self.hass.services = SimpleNamespace(async_call=dispatch)
        try:
            with stack, patch.object(speaker_delivery, '_async_ha_base_url', new=AsyncMock(return_value='https://ha-owned.invalid')):
                await self.choose('marin', extra={'announcement_output':'both'})
                session, moment, _ = await self.f.selected_credit()
                authority = await hybrid_service.PairedAuthority.resolve(self.hass, self.f.identity, self.f.headers)
                request = {'contract_version':1, 'operation_id':identifier(self.now),
                    'operation_epoch':journal.journal.epoch, 'operation':'session/speech/play',
                    'payload': {'contract_version':3, 'processor':'ha_configured', 'intent':'manual',
                        'target':'both', 'reference': {'session_id':session.session_id, 'moment_id':moment.moment_id}}}
                first, status = await journal.execute(authority, request, transport='http')
                again, repeated_status = await journal.execute(authority, request, transport='websocket')
                self.assertEqual((status, repeated_status), (503, 503), first)
                self.assertEqual(first['delivery'], {'ha_speaker':'unknown', 'local':'ready', 'audible':'not_proven'})
                self.assertIn('audio_reference', first['session_speech'])
                self.assertEqual(again['operation_receipt']['phase'], 'unknown')
                self.assertEqual((dispatch.await_count, len(calls)), (1, 1))
        finally:
            await journal.close()
