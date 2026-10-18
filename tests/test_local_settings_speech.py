"""Owner-route native text grants preserve Settings/source fences without HA TTS."""
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_profile_settings_speech as shared


class LocalSettingsSpeechTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = shared.SharedSettingsSpeechTests.__dict__['setUpClass']
    tearDownClass = shared.SharedSettingsSpeechTests.__dict__['tearDownClass']
    asyncSetUp = shared.SharedSettingsSpeechTests.asyncSetUp
    asyncTearDown = shared.SharedSettingsSpeechTests.asyncTearDown
    choose = shared.SharedSettingsSpeechTests.choose
    contribution = shared.SharedSettingsSpeechTests.contribution
    provider = shared.SharedSettingsSpeechTests.provider

    async def prepare(self, payload):
        return await self.speech.async_handle_prepare(self.hass, payload, headers=self.f.headers)

    def local(self, payload, **extra):
        return {**payload, 'processor': 'local_on_device', **extra}

    def no_ha(self):
        return patch('custom_components.djconnect.speech_processor.voice_options',
                     side_effect=AssertionError('native preparation queried HA voice availability'))

    def record(self, name, rows):
        destination = os.environ.get('DJC_LOCAL_SPEECH_FIXTURES')
        if not destination:
            return
        p = Path(destination)
        body = json.loads(p.read_text()) if p.exists() else {
            'proof_boundary': 'Actual Core owner-route execution; synthetic owner/agent/source and OS renderer absent. No installed or audible proof.',
            'cases': {}}
        body['cases'][name] = rows
        p.write_text(json.dumps(body, indent=2, ensure_ascii=False)+'\n')

    async def test_local_grant_ignores_unavailable_ha_voice_preserves_exact_source_and_no_writes(self):
        stack, _, pipeline, calls, _ = self.provider()
        with stack:
            await self.choose('cedar', extra={'gender': 'default', 'mood': 'party'})
            pipeline.tts_engine = 'tts.unavailable'
            answer, status = await self.f.request('What is an ostinato?',
                identifier='native-after-settings', speech_contract_version=3, audio_response='always')
            self.assertEqual(status, 200, answer)
            self.assertEqual(answer['audio_delivery']['state'], 'deferred')
            original = answer['session_speech']
            payload = {**self.f.identity, 'contract_version': 3, 'processor': 'local_on_device',
                       'intent': 'manual', 'target': 'local', 'reference': original['reference']}
            before = await self.f.fixture.manager.async_read_dj_settings(owner_profile_id='profile-a', authorize=lambda: True)
            prompts_before = list(self.f.prompts)
            with self.no_ha():
                result, status = await self.prepare(payload)
            self.assertEqual(self.f.prompts, prompts_before)
            self.assertEqual(status, 200, result)
            d = result['session_speech']
            self.assertEqual((d['state'], d['audio_state'], d['processor']),
                             ('available', 'renderer_pending', 'local_on_device'))
            self.assertTrue(d['manual_allowed'])
            self.assertIsNone(d['effective_voice'])
            self.assertFalse(d['autoplay_eligible'])
            self.assertEqual(d['reference'], payload['reference'])
            self.assertEqual(d['settings_contract_version'], 3)
            self.assertTrue(d['text_revision'] and d['presentation_revision'])
            self.assertNotIn('voice_preference', d)
            self.assertNotIn('audio_reference', d)
            self.assertNotIn('audio_url', d)
            self.assertTrue(d['segments'])
            for key in ('segments', 'text_revision', 'presentation_revision', 'persona', 'persona_revision', 'mood', 'attribution', 'source_expires_at'):
                self.assertEqual(d.get(key), original.get(key), key)
            after = await self.f.fixture.manager.async_read_dj_settings(owner_profile_id='profile-a', authorize=lambda: True)
            self.assertEqual(after, before)
            self.assertEqual(calls, [])
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))
            self.record('unavailable_ha_voice', {'request': payload, 'response': result, 'status': status})

    async def test_output_intent_target_matrix_has_no_synthesis_or_speaker_effect(self):
        payload = self.local(await self.contribution())
        stack, _, _, calls, _ = self.provider()
        rows = []
        self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.fixture'
        with stack, patch('custom_components.djconnect.announcements.validate_announcement_speaker', return_value=None):
            for number, mode in enumerate(('client_device', 'both', 'ha_speaker', 'text_only'), 1):
                await self.choose('marin', counter=number, extra={'announcement_output': mode})
                for intent in ('manual', 'automatic'):
                    for target in ('local', 'ha_speaker', 'both'):
                        request = {**payload, 'intent': intent, 'target': target}
                        with self.no_ha():
                            result, status = await self.prepare(request)
                        self.assertEqual(status, 200, result)
                        d = result['session_speech']
                        admitted = target == 'local' and mode != 'text_only' and (intent == 'manual' or mode in ('client_device', 'both'))
                        self.assertEqual(d['manual_allowed'], admitted, (mode, intent, target, d))
                        if admitted:
                            self.assertEqual(d['audio_state'], 'renderer_pending')
                            self.assertFalse(d['autoplay_eligible'])
                        else:
                            self.assertEqual(d['segments'], [])
                            self.assertEqual(d['processors'], [])
                        rows.append({'output': mode, 'request': request, 'status': status, 'response': result})
            self.assertEqual(calls, [])
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))
        self.record('output_intent_target_matrix', rows)

    async def test_no_client_text_voice_gender_rate_pitch_or_unknown_processor_overrides(self):
        payload = self.local(await self.contribution())
        for extra in ({'voice_id': 'os-voice'}, {'voice_preference': 'female'}, {'gender': 'male'},
                      {'rate': 1.1}, {'pitch': 1.2}, {'text': 'caller text'}, {'processor': 'unknown'}):
            with self.subTest(extra=extra):
                result, status = await self.prepare({**payload, **extra})
                self.assertEqual((status, result['error']), (400, 'invalid_request'))

    async def test_prepare1_and2_cannot_bypass_activated_settings(self):
        payload = self.local(await self.contribution())
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.choose('marin')
            for version in (1, 2):
                request = {k: v for k, v in payload.items() if k not in ('intent', 'target')}
                request['contract_version'] = version
                if version == 1:
                    request['voice_preference'] = 'default'
                result, status = await self.prepare(request)
                self.assertEqual((status, result['error']), (426, 'settings_contract_upgrade_required'))

    async def test_live_and_retained_grants_keep_original_text_and_style_then_end_withdraws_live(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.choose('marin')
            session, moment, retained = await self.f.selected_credit()
            descriptor = self.speech.moment_projection(session.broadcast, moment)
            request = {**self.f.identity, 'contract_version': 3, 'processor': 'local_on_device',
                       'intent': 'manual', 'target': 'local',
                       'reference': {'session_id': session.session_id, 'moment_id': moment.moment_id}}
            with self.no_ha():
                live, status = await self.prepare(request)
            self.assertEqual(status, 200, live)
            for key in ('segments', 'text_revision', 'presentation_revision', 'persona', 'persona_revision', 'mood', 'attribution', 'source_expires_at'):
                self.assertEqual(live['session_speech'][key], descriptor[key], key)
            from custom_components.djconnect.transport_delivery import capture_delivery_admissions
            with capture_delivery_admissions() as checks:
                admitted, status = await self.prepare(request)
            self.assertEqual(status, 200, admitted)
            await self.f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=session.session_id)
            with self.assertRaises(PermissionError):
                checks[-1]()
            gone, status = await self.prepare(request)
            self.assertEqual(status, 404, gone)
            await self.f.fixture.service.async_close()
            await self.f.fixture.service.async_initialize()
            replay_request = {**request, 'reference': retained}
            with self.no_ha():
                replay, status = await self.prepare(replay_request)
            self.assertEqual(status, 200, replay)
            self.assertEqual(''.join(s['text'] for s in replay['session_speech']['segments']), moment.content)
            self.assertEqual(replay['session_speech']['persona_revision'], descriptor['persona_revision'])
            self.assertEqual(replay['session_speech']['mood'], descriptor['mood'])
            self.assertEqual(calls, [])
            self.record('live_and_retained', [
                {'request': request, 'response': live, 'status': 200},
                {'request': replay_request, 'response': replay, 'status': 200}])

    async def test_delayed_delivery_is_withdrawn_on_any_shared_setting_change(self):
        from custom_components.djconnect.transport_delivery import capture_delivery_admissions
        payload = self.local(await self.contribution())
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.choose('marin')
            for number, patch_value in enumerate(({'mood': 'party'}, {'persona': 'club_dj'},
                    {'presence': 'music_only'}, {'announcement_output': 'text_only'}), 2):
                with capture_delivery_admissions() as checks:
                    result, status = await self.prepare(payload)
                self.assertEqual(status, 200, result)
                self.assertTrue(result['session_speech']['manual_allowed'])
                await self.choose('marin', counter=number, extra=patch_value)
                with self.assertRaises(PermissionError):
                    checks[-1]()
            self.assertEqual(calls, [])

    async def test_local_source_expiry_and_withdrawal_invalidate_delayed_grant(self):
        from custom_components.djconnect.transport_delivery import capture_delivery_admissions
        payload = self.local(await self.contribution())
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.choose('marin')
            with capture_delivery_admissions() as checks:
                result, status = await self.prepare(payload)
            self.assertEqual(status, 200, result)
            expiry = datetime.fromisoformat(result['session_speech']['expires_at']).timestamp()
            with patch('time.time', return_value=expiry+1), self.assertRaises(PermissionError):
                checks[-1]()
            expired, status = await self.prepare(payload)
            # The deliberate second request can make a fresh bounded grant only
            # while the original turn still exists; its old grant stays expired.
            self.assertEqual(status, 200, expired)
            with capture_delivery_admissions() as current:
                result, status = await self.prepare(payload)
            await self.f.history.async_clear('profile:profile-a')
            with self.assertRaises(PermissionError):
                current[-1]()
            withdrawn, status = await self.prepare(payload)
            self.assertEqual(status, 404, withdrawn)
            self.record('withdrawn', {'request': payload, 'response': withdrawn, 'status': status})

    async def test_unknown_source_processing_basis_fails_closed_without_text(self):
        payload = self.local(await self.contribution())
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.choose('marin')
            original = self.speech.resolve_dialogue
            async def unknown(*args, **kwargs):
                descriptor, guard = await original(*args, **kwargs)
                guard.processor_basis = 'unknown'
                return descriptor, guard
            with patch.object(self.speech, 'resolve_dialogue', unknown), self.no_ha():
                result, status = await self.prepare(payload)
            self.assertEqual(status, 200, result)
            self.assertEqual(result['session_speech']['reason'], 'source_processor_not_qualified')
            self.assertEqual(result['session_speech']['segments'], [])
            self.record('unknown_source', {'request': payload, 'response': result, 'status': status})

    async def test_settings_change_while_resolving_source_never_delivers_old_grant(self):
        payload = self.local(await self.contribution())
        stack, _, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.speech.resolve_dialogue
        async def delayed(*args, **kwargs):
            result = await original(*args, **kwargs)
            entered.set()
            await release.wait()
            return result
        with stack:
            await self.choose('marin')
            with patch.object(self.speech, 'resolve_dialogue', delayed):
                pending = asyncio.create_task(self.prepare(payload))
                await asyncio.wait_for(entered.wait(), 2)
                await self.choose('marin', counter=2, extra={'announcement_output': 'text_only'})
                release.set()
                result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual(status, 404, result)
            self.assertNotIn('session_speech', result)
            self.assertEqual(calls, [])
            self.record('settings_changed_during_prepare', {'request': payload, 'response': result, 'status': status})

    async def test_expired_source_is_denied_and_native_processor_cannot_enter_speaker_operation(self):
        from types import SimpleNamespace
        from custom_components.djconnect import speaker_delivery
        payload = self.local(await self.contribution())
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.choose('marin')
            clock = self.f.history.dialogue.clock()
            with patch.object(self.f.history.dialogue, 'clock', return_value=clock+10000):
                result, status = await self.prepare(payload)
            self.assertEqual(status, 404, result)
            self.record('expired_source', {'request': payload, 'response': result, 'status': status})
            for target in ('both', 'ha_speaker'):
                request = {**payload, 'target': target,
                           'reference': {'session_id': 'synthetic-session', 'moment_id': 'synthetic-moment'}}
                # The actual operation rejects before reading a speaker/authority.
                result, status = await speaker_delivery.async_play(self.hass, SimpleNamespace(), request)
                self.assertEqual((status, result['error']), (400, 'invalid_request'))

    async def test_capability_explicitly_scopes_native_voice_and_preserves_ha_owner(self):
        d = self.speech.capability()
        for version in ('2', '3'):
            contract = d['prepare_contracts'][version]
            self.assertEqual(contract['processors'], ['local_on_device', 'ha_configured'])
            self.assertFalse(contract['caller_voice_override'])
            self.assertEqual(contract['local_on_device']['voice_settings_scope'], 'device_local')
            self.assertFalse(contract['local_on_device']['ha_voice_availability_required'])
        self.assertEqual(d['shared_profile_settings']['voice_processor'], 'ha_configured')
        self.record('capability', d)
