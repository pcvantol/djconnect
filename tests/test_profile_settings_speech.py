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
            {**self.f.identity, 'contract_version': 2}, headers=self.f.headers)
        self.assertEqual(status, 200, before)
        result, status = await self.settings.async_handle_settings(self.hass,
            {**self.f.identity, 'contract_version': 2, 'binding': before['binding'],
             'operation_id': operation(self.now, counter), 'expected_defaults_revision': before['snapshot']['defaults_revision'],
             'expected_session': None,
             'patch': {'voice': {'kind': 'provider_voice', 'provider_id': 'tts.fixture_cloud', 'voice_id': voice},
                       **(extra or {})}},
            headers=self.f.headers, write=True)
        self.assertEqual(status, 200, result)
        return result

    async def contribution(self):
        answer, status = await self.f.request('What is an ostinato?', identifier='shared-voice-source')
        self.assertEqual(status, 200, answer)
        return {**self.f.identity, 'contract_version': 2, 'processor': 'ha_configured',
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
            self.assertEqual(result['session_speech']['settings_contract_version'], 2)
            self.assertEqual(calls[-1][2]['voice'], 'cedar')
            self.assertEqual(pipeline.tts_voice, 'marin')
            self.assertEqual(entity.default_options['voice'], 'marin')
            old, status = await self.speech.async_handle_prepare(self.hass,
                {**payload, 'contract_version': 1, 'voice_preference': 'default'}, headers=self.f.headers)
            self.assertEqual((status, old['error']), (426, 'settings_contract_upgrade_required'))
            self.assertEqual(len(calls), 1)

    async def test_general_ask_dj_uses_confirmed_profile_style_not_legacy_numeric_init(self):
        stack, entity, pipeline, calls, _ = self.provider()
        with stack:
            await self.choose('cedar', extra={'persona': 'festival_dj', 'mood': 'party'})
            answer, status = await self.f.request('What is an ostinato?', identifier='shared-style',
                mood=0, dj_persona='club_dj', speech_contract_version=2, audio_response='always')
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
