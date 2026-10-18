"""Configured preview uses real paired/Settings/operation/byte owners; TTS is a fixture."""
import asyncio
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from tests import test_profile_settings_speech as shared
from tests.test_transport_operation_journal import Store, identifier


class VoicePreviewTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = shared.SharedSettingsSpeechTests.__dict__['setUpClass']
    tearDownClass = shared.SharedSettingsSpeechTests.__dict__['tearDownClass']
    choose = shared.SharedSettingsSpeechTests.choose
    provider = shared.SharedSettingsSpeechTests.provider

    async def asyncSetUp(self):
        await shared.SharedSettingsSpeechTests.asyncSetUp(self)
        from custom_components.djconnect import hybrid_service
        self.hybrid = hybrid_service
        self.store = Store()
        self.operations = hybrid_service.HybridOperations(self.hass, self.store)
        self.counter = 0
        self.sent = []
        async def deliver(*args, **kwargs):
            self.sent.append(args[2])
        self.hass.services = SimpleNamespace(async_call=deliver)

    async def asyncTearDown(self):
        await self.operations.close()
        await shared.SharedSettingsSpeechTests.asyncTearDown(self)

    def request(self, language='en', **overrides):
        self.counter += 1
        return {'contract_version': 1, 'operation_id': identifier(self.now, 100+self.counter),
                'operation_epoch': self.operations.journal.epoch, 'operation': 'speech/preview',
                'payload': {'contract_version': 1, 'language': language, **overrides}}

    async def execute(self, request=None, *, transport='http'):
        authority = await self.hybrid.PairedAuthority.resolve(self.hass, self.f.identity, self.f.headers)
        request = request or self.request()
        result, status = await self.operations.execute(authority, request, transport=transport)
        if destination := os.environ.get('DJC_VOICE_PREVIEW_FIXTURES'):
            path = Path(destination)
            document = json.loads(path.read_text()) if path.exists() else {
                'proof_boundary': 'Actual paired Core operation/Settings/private-byte owners; external TTS and HA speaker I/O fixtures. No installed, paid-provider, native or audible proof.',
                'cases': {}}
            key = self._testMethodName + '/' + str(self.counter)
            document['cases'][key] = {'request': request, 'response': result, 'status': status}
            path.write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
        return result, status

    def speaker(self):
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.owned_speaker'
        self.hass.states = SimpleNamespace(get=lambda entity: SimpleNamespace(
            state='idle', attributes={'supported_features': 512})
            if entity == 'media_player.owned_speaker' else None)

    async def test_preview_without_session_is_literal_five_language_and_has_no_domain_writes(self):
        from custom_components.djconnect.voice_preview import TEXT
        stack, entity, pipeline, calls, _ = self.provider()
        entity.supported_languages = ['en-US', 'nl-NL', 'de-DE', 'fr-FR', 'es-ES']
        with stack:
            await self.choose('cedar', extra={'mood': 'party'})
            before = await self.f.fixture.manager.async_read_dj_settings(
                owner_profile_id='profile-a', authorize=lambda: True)
            history = await self.f.history.async_history('profile:profile-a')
            for language, text in TEXT.items():
                pipeline.tts_language = {'en': 'en-US', 'nl': 'nl-NL', 'de': 'de-DE',
                                         'fr': 'fr-FR', 'es': 'es-ES'}[language]
                original = deepcopy(pipeline.__dict__)
                result, status = await self.execute(self.request(language))
                self.assertEqual(status, 200, result)
                value = result['voice_preview']
                self.assertEqual((value['text'], value['locale']), (text, language))
                self.assertEqual(value['effective_voice']['voice_id'], 'cedar')
                self.assertEqual(calls[-1][0], text)
                self.assertEqual(calls[-1][2]['voice'], 'cedar')
                self.assertNotIn('session_speech', result)
                self.assertNotIn('mood', value)
                self.assertEqual(pipeline.__dict__, original)
                self.assertLessEqual(datetime.fromisoformat(value['expires_at']).timestamp(),
                                     datetime.now().timestamp()+120)
            after = await self.f.fixture.manager.async_read_dj_settings(
                owner_profile_id='profile-a', authorize=lambda: True)
            now_history = await self.f.history.async_history('profile:profile-a')
            for value in (history, now_history):
                value.pop('server_time', None)
            self.assertEqual(history, now_history)
            self.assertEqual(before, after)
            self.assertIsNone(self.f.fixture.manager.current_active('profile-a'))
            self.assertEqual((self.f.prompts, self.f.effects, self.sent), ([], [], []))
            self.assertNotIn(TEXT['nl'], json.dumps(self.store.data))

    async def test_text_only_and_unconfirmed_settings_have_zero_provider_or_speaker_effects(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            unknown, status = await self.execute()
            self.assertEqual(status, 409, unknown)
            self.assertEqual(unknown['error'], 'settings_migration_choice_required')
            self.assertEqual((await unknown.admitted_body())['error'], 'settings_migration_choice_required')
            await self.choose('marin', extra={'announcement_output': 'text_only'})
            denied, status = await self.execute()
            self.assertEqual((status, denied['error']), (409, 'announcement_text_only'))
            self.assertNotIn('voice_preview', denied)
            self.assertEqual((calls, self.sent, self.f.prompts), ([], [], []))
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))

    async def test_closed_preview_payload_rejects_text_voice_target_locale_and_reference_overrides(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.choose('marin')
            for values in ({'text': 'caller text'}, {'voice_id': 'cedar'}, {'target': 'both'},
                           {'reference': {'turn_id': 'previous'}}, {'language': 'it'},
                           {'contract_version': True}):
                result, status = await self.execute(self.request(**values))
                self.assertEqual((status, result['error']), (400, 'invalid_request'), result)
            self.assertEqual((calls, self.sent), ([], []))

    async def test_duplicate_and_socket_cancel_never_resynthesize_or_dispatch_speaker_twice(self):
        from custom_components.djconnect import speaker_delivery
        stack, entity, _, calls, _ = self.provider()
        self.speaker()
        entered, release = asyncio.Event(), asyncio.Event()
        original = entity.async_get_tts_audio
        async def held(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        entity.async_get_tts_audio = held
        with stack, patch.object(speaker_delivery, '_async_ha_base_url',
                                  new=AsyncMock(return_value='https://ha-owned.invalid')):
            await self.choose('marin', extra={'announcement_output': 'both'})
            request = self.request()
            pending = asyncio.create_task(self.execute(request, transport='websocket'))
            await asyncio.wait_for(entered.wait(), 2)
            repeated, status = await self.execute(request)
            self.assertEqual(status, 202, repeated)
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            release.set()
            await asyncio.gather(*tuple(self.operations.tasks.values()))
            again, status = await self.execute(request)
            self.assertEqual((status, again['operation_receipt']['phase']), (200, 'confirmed'))
            self.assertFalse(again['result_available'])
            self.assertEqual((len(calls), len(self.sent)), (1, 1))

    async def test_settings_change_during_synthesis_never_returns_or_sends_old_audio(self):
        stack, entity, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        original = entity.async_get_tts_audio
        async def held(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        entity.async_get_tts_audio = held
        with stack:
            await self.choose('marin')
            pending = asyncio.create_task(self.execute())
            await asyncio.wait_for(entered.wait(), 2)
            await self.choose('cedar', counter=2)
            release.set()
            result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual((status, result['error']), (409, 'voice_preview_withdrawn'), result)
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))
            self.assertEqual((len(calls), self.sent), (1, []))

    async def test_all_outputs_share_one_audio_owner_and_keep_separate_delivery_outcomes(self):
        from custom_components.djconnect import speaker_delivery
        stack, _, _, calls, _ = self.provider()
        self.speaker()
        with stack, patch.object(speaker_delivery, '_async_ha_base_url',
                                  new=AsyncMock(return_value='https://ha-owned.invalid')):
            for counter, output in enumerate(('client_device', 'ha_speaker', 'both'), 1):
                await self.choose('cedar', counter=counter, extra={'announcement_output': output})
                result, status = await self.execute()
                self.assertEqual(status, 200, result)
                self.assertEqual(result['delivery']['local'], 'not_requested' if output == 'ha_speaker' else 'ready')
                self.assertEqual(result['delivery']['ha_speaker'], 'not_requested' if output == 'client_device' else 'queued')
                self.assertEqual(result['delivery']['audible'], 'not_proven')
                self.assertEqual('audio_reference' in result['voice_preview'], output != 'ha_speaker')
            self.assertEqual((len(calls), len(self.sent)), (3, 2))

    async def test_both_partial_failure_keeps_client_audio_and_unknown_dispatch_is_not_repeated(self):
        from custom_components.djconnect import speaker_delivery
        stack, _, _, calls, _ = self.provider()
        self.speaker()
        with stack:
            await self.choose('cedar', extra={'announcement_output': 'both'})
            self.hass.states.get = lambda _: None
            partial, status = await self.execute()
            self.assertEqual(status, 200, partial)
            self.assertEqual(partial['delivery']['ha_speaker'], 'unavailable')
            self.assertEqual(partial['delivery']['local'], 'ready')
            self.assertIn('audio_reference', partial['voice_preview'])
            self.assertEqual(self.sent, [])
            self.speaker()
            async def uncertain(*args, **kwargs):
                self.sent.append(args[2])
                raise OSError('private service detail')
            self.hass.services.async_call = uncertain
            request = self.request()
            with patch.object(speaker_delivery, '_async_ha_base_url',
                              new=AsyncMock(return_value='https://ha-owned.invalid')):
                failed, status = await self.execute(request)
                self.assertEqual((status, failed['error']), (503, 'speaker_delivery_unknown'))
                self.assertEqual(failed['delivery']['local'], 'ready')
                self.assertIn('audio_reference', failed['voice_preview'])
                repeated, status = await self.execute(request)
                self.assertEqual((status, repeated['operation_receipt']['phase']), (503, 'unknown'))
                self.assertNotIn('private service detail', json.dumps(failed))
                self.assertEqual(len(self.sent), 1)
            self.assertEqual(len(calls), 2)

    async def test_new_press_reuses_original_sample_deadline_and_provider_failure_backoff(self):
        stack, entity, _, calls, _ = self.provider()
        with stack:
            await self.choose('marin')
            first, status = await self.execute()
            second, status = await self.execute()
            for field in ('expires_at', 'audio_reference'):
                self.assertEqual(first['voice_preview'][field], second['voice_preview'][field])
            self.assertNotEqual(first['voice_preview']['preview_id'], second['voice_preview']['preview_id'])
            self.assertEqual(len(calls), 1)
            await self.choose('cedar', counter=2)
            failures = []
            async def fail(*args):
                failures.append(True)
                raise RuntimeError('PRIVATE_PROVIDER_KEY_PROMPT_URL')
            entity.async_get_tts_audio = fail
            result, status = await self.execute()
            self.assertEqual((status, result['error']), (409, 'speech_preparation_failed'))
            self.assertEqual(result['notification']['code'], 'tts_preparation_failed')
            self.assertEqual((await result.admitted_body())['notification']['code'], 'tts_preparation_failed')
            self.assertNotIn('PRIVATE_PROVIDER', json.dumps(result))
            backed_off, status = await self.execute()
            self.assertEqual((status, backed_off['error']), (409, 'speech_retry_backoff'))
            self.assertEqual(failures, [True])

    async def test_old_bytes_denied_after_provider_change_and_text_only(self):
        stack, entity, _, calls, _ = self.provider()
        with stack:
            await self.choose('marin')
            result, status = await self.execute()
            asset = result['voice_preview']['audio_reference']['asset_id']
            read = {**self.f.identity, 'contract_version': 1, 'asset_id': asset}
            item, status = await self.speech.async_handle_audio(self.hass, read, headers=self.f.headers)
            self.assertEqual(status, 200)
            self.assertIsNotNone(item)
            entity.subentry.data['tts_speed'] = 1.1
            changed, status = await self.speech.async_handle_audio(self.hass, read, headers=self.f.headers)
            self.assertEqual(status, 409, changed)
            fresh, status = await self.execute()
            read['asset_id'] = fresh['voice_preview']['audio_reference']['asset_id']
            await self.choose('marin', counter=2, extra={'announcement_output': 'text_only'})
            denied, status = await self.speech.async_handle_audio(self.hass, read, headers=self.f.headers)
            self.assertEqual((status, denied), (404, None))
            self.assertEqual(len(calls), 2)

    async def test_original_monotonic_expiry_survives_clock_rollback(self):
        from custom_components.djconnect import voice_preview
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.choose('marin')
            mono = voice_preview.time.monotonic()
            wall = voice_preview.time.time()
            result, status = await self.execute()
            read = {**self.f.identity, 'contract_version': 1,
                    'asset_id': result['voice_preview']['audio_reference']['asset_id']}
            with patch.object(voice_preview.time, 'time', return_value=wall-3600), \
                    patch.object(voice_preview.time, 'monotonic', return_value=mono+121):
                value, status = await self.speech.async_handle_audio(self.hass, read, headers=self.f.headers)
            self.assertEqual((status, value), (404, None))
            self.assertEqual(len(calls), 1)

    async def test_active_session_identity_and_history_are_preserved_then_end_revokes_preview(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.choose('cedar')
            session, _, _ = await self.f.selected_credit()
            await self.choose('cedar', counter=2)
            manager = self.f.fixture.manager
            current = manager.current_active('profile-a')
            before = current.as_dict()
            result, status = await self.execute()
            self.assertEqual(status, 200, result)
            self.assertIs(manager.current_active('profile-a'), current)
            self.assertEqual(current.as_dict(), before)
            read = {**self.f.identity, 'contract_version': 1,
                    'asset_id': result['voice_preview']['audio_reference']['asset_id']}
            await manager.async_end(owner_profile_id='profile-a', session_id=session.session_id)
            denied, status = await self.speech.async_handle_audio(self.hass, read, headers=self.f.headers)
            self.assertEqual((status, denied), (404, None))
            self.assertEqual(len(calls), 1)

    async def test_target_change_while_resolving_media_url_has_zero_speaker_dispatch(self):
        from custom_components.djconnect import speaker_delivery
        stack, _, _, calls, _ = self.provider()
        self.speaker()
        entered, release = asyncio.Event(), asyncio.Event()
        async def url(*args):
            entered.set()
            await release.wait()
            return 'https://ha-owned.invalid'
        with stack, patch.object(speaker_delivery, '_async_ha_base_url', new=url):
            await self.choose('marin', extra={'announcement_output': 'ha_speaker'})
            pending = asyncio.create_task(self.execute())
            await asyncio.wait_for(entered.wait(), 2)
            self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.replacement'
            release.set()
            result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual((status, result['error']), (409, 'voice_preview_withdrawn'), result)
            self.assertEqual((len(calls), self.sent), (1, []))

    async def test_provider_and_gender_selection_are_qualified_without_locale_fallback(self):
        stack, entity, pipeline, calls, _ = self.provider()
        entity.async_get_supported_voices = lambda locale: [
            SimpleNamespace(voice_id='marin', name='Marin', gender='male'),
            SimpleNamespace(voice_id='cedar', name='Cedar', gender='female')]
        with stack:
            await self.choose('cedar', extra={'gender': 'female'})
            result, status = await self.execute()
            self.assertEqual(status, 200, result)
            self.assertEqual(result['voice_preview']['effective_voice']['gender'], 'female')
            self.assertEqual(calls[-1][2]['voice'], 'cedar')
            wrong_locale, status = await self.execute(self.request('fr'))
            self.assertEqual((status, wrong_locale['error']), (409, 'no_matching_locale'))
            self.assertEqual(pipeline.tts_language, 'en-US')
            entity.available = False
            unavailable, status = await self.execute()
            self.assertEqual(status, 409, unavailable)
            self.assertEqual(unavailable['notification']['code'], 'tts_provider_unavailable')
            self.assertEqual(len(calls), 1)

    async def test_queued_result_revalidates_provider_before_semantic_delivery(self):
        stack, entity, _, _, _ = self.provider()
        with stack:
            await self.choose('marin')
            result, status = await self.execute()
            self.assertEqual(status, 200, result)
            self.assertIn('voice_preview', await result.admitted_body())
            entity.subentry.data['tts_speed'] = 1.1
            withdrawn = await result.admitted_body()
            self.assertFalse(withdrawn['result_available'])
            self.assertNotIn('voice_preview', withdrawn)
            self.assertEqual(withdrawn['operation_receipt']['phase'], 'confirmed')

    def test_capability_exposes_only_existing_owner_operation_and_fixed_languages(self):
        from custom_components.djconnect import voice_preview
        capability = self.speech.capability()['voice_preview']
        self.assertEqual(capability, voice_preview.capability())
        self.assertEqual(capability['operation'], 'speech/preview')
        self.assertEqual(set(capability['language_families']), {'en', 'nl', 'de', 'fr', 'es'})
        self.assertFalse(capability['caller_text_or_voice_override'])
        self.assertFalse(capability['history_publication'])
        self.assertFalse(capability['session_required'])
        self.assertIn(capability['operation'], self.hybrid.ACTION_OPERATIONS)
        self.assertIn(capability['operation'], self.hybrid.HTTP_OPERATIONS)

    async def test_pairing_revocation_during_synthesis_discards_bytes_and_preserves_single_intent(self):
        stack, entity, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        original = entity.async_get_tts_audio
        async def held(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        entity.async_get_tts_audio = held
        with stack:
            await self.choose('marin')
            pending = asyncio.create_task(self.execute())
            await asyncio.wait_for(entered.wait(), 2)
            self.runtime.device_token = 'synthetic-revoked-pairing'
            release.set()
            with self.assertRaises(self.hybrid.OperationError):
                await asyncio.wait_for(pending, 2)
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))
            self.assertEqual((len(calls), self.sent), (1, []))
            self.assertEqual(len(self.store.data['records']), 1)

    async def test_new_session_during_synthesis_rejects_original_no_session_sample(self):
        stack, entity, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        original = entity.async_get_tts_audio
        async def held(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        entity.async_get_tts_audio = held
        with stack:
            await self.choose('marin')
            pending = asyncio.create_task(self.execute())
            await asyncio.wait_for(entered.wait(), 2)
            session, _, _ = await self.f.selected_credit()
            release.set()
            result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual((status, result['error']), (409, 'voice_preview_withdrawn'), result)
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))
            self.assertEqual(self.f.fixture.manager.current_active('profile-a').session_id, session.session_id)
            self.assertEqual((len(calls), self.sent), (1, []))
