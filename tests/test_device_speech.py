"""Actual discovery owner; explicit external provider metadata, zero processing."""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import importlib
import json
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

from tests import test_config_flow_helpers as config_fixtures
from tests import test_http_voice_helpers as http_fixtures


class DeviceSpeechTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_fixtures.ConfigFlowHelperTest.setUpClass()
        http_fixtures.VoiceHttpHelperTest.setUpClass()
        cls.owner = importlib.import_module('custom_components.djconnect.device_speech')
        cls.http = importlib.import_module('custom_components.djconnect.http')

    def setUp(self):
        self.stack = self.enterContext(ExitStack())
        self.identity = 'djconnect-ios-ABCDEF123456'
        self.config = {'assist_pipeline_id': 'chosen', 'device_id': self.identity,
                       'client_type': 'ios', 'device_token': 'private-device-token',
                       'spotify_refresh_token': 'private-spotify-token'}
        self.entry = NS(entry_id='entry', data=self.config, disabled_by=None, state=NS(value='loaded'))
        self.runtime = NS(config=self.config, entry=self.entry, device_token=self.config['device_token'],
            device_status={'device_id': self.identity, 'client_type': 'ios'})
        self.runtime.authorize_device_request = lambda headers, device_id, client_type=None: (
            headers.get('Authorization') == 'Bearer '+self.runtime.device_token
            and device_id == self.identity and client_type in (None, 'ios'))
        self.states = {}
        self.hass = NS(data={'djconnect': {'entry': self.runtime, 'runtime': self.runtime}},
            config=NS(language='en-US'), states=NS(get=self.states.get),
            config_entries=NS(async_get_entry=lambda eid: self.entry if eid == 'entry' else None))
        self.pipeline = NS(id='chosen', name='Private pipeline', language='en-US',
            conversation_engine='conversation.agent', stt_engine='stt.synthetic',
            stt_language='en-US', tts_engine='tts.synthetic', tts_language='en-US', tts_voice='voice-a')
        self.pipelines = {'chosen': self.pipeline}
        self.preferred = 'chosen'
        from homeassistant.components.assist_pipeline import pipeline as api
        from homeassistant.components import conversation
        def resolve(hass, selected=None):
            return self.pipelines[selected or self.preferred]
        self.stack.enter_context(patch.object(api, 'async_get_pipeline', side_effect=resolve))
        self.agent = NS(available=True, async_process=AsyncMock())
        self.stack.enter_context(patch.object(conversation, 'async_get_agent', return_value=self.agent))
        self.stt = NS(available=True, async_process_audio_stream=AsyncMock(),
            check_metadata=lambda m: m.language == 'en-US' and m.sample_rate == 16000)
        self.tts = NS(available=True, supported_languages=['en-US'], default_options={'voice':'voice-a'},
            async_get_tts_audio=AsyncMock(),
            async_get_supported_voices=lambda lang: [NS(voice_id='voice-a', name='Alex'),
                                                    NS(voice_id='voice-b', name='Taylor', gender='female')])
        stt = ModuleType('homeassistant.components.stt')
        stt.async_get_speech_to_text_engine = lambda hass, engine: self.stt if engine == 'stt.synthetic' else None
        stt.AudioFormats = NS(WAV='wav')
        stt.AudioCodecs = NS(PCM='pcm')
        stt.SpeechMetadata = lambda **kwargs: NS(**kwargs)
        tts = ModuleType('homeassistant.components.tts')
        tts.get_engine_instance = lambda hass, engine: self.tts if engine == 'tts.synthetic' else None
        self.stack.enter_context(patch.dict(sys.modules, {'homeassistant.components.stt': stt,
                                                         'homeassistant.components.tts': tts}))
        components = sys.modules['homeassistant.components']
        self.stack.enter_context(patch.object(components, 'stt', stt, create=True))
        self.stack.enter_context(patch.object(components, 'tts', tts, create=True))

    def project(self, **kwargs):
        return self.owner.snapshot(self.hass, self.runtime, **kwargs)

    def assert_no_processing(self):
        self.agent.async_process.assert_not_called()
        self.stt.async_process_audio_stream.assert_not_called()
        self.tts.async_get_tts_audio.assert_not_called()

    def test_all_four_audio_configurations_remain_independent_and_do_not_process(self):
        before = deepcopy(self.config)
        for stt, tts in ((None,None), ('stt.synthetic',None), (None,'tts.synthetic'), ('stt.synthetic','tts.synthetic')):
            with self.subTest(stt=stt,tts=tts):
                self.pipeline.stt_engine, self.pipeline.tts_engine = stt,tts
                result = self.project()
                self.assertEqual(result['assist']['conversation']['state'],'available')
                self.assertEqual(result['ha_stt']['state'],'available' if stt else 'unconfigured')
                self.assertEqual(result['ha_tts']['state'],'available' if tts else 'unconfigured')
                self.assertEqual(result['ha_speaker_target']['state'],'unconfigured')
                self.assertEqual(result['apple_local']['stt'],'client_owned')
                self.assertEqual(result['text_only'],{'available':True,'audio':False})
        self.assertEqual(self.config,before)
        self.assert_no_processing()

    def test_exact_selection_never_borrows_other_pipeline_and_default_changes_are_fresh(self):
        first = self.project()
        self.assertEqual(first['revision'],self.project()['revision'])
        self.config['assist_pipeline_id']='absent'
        missing=self.project()
        self.assertEqual(missing['ha_stt']['state'],'unknown')
        self.assertIsNone(missing['assist']['pipeline_id'])
        self.config['assist_pipeline_id']=''
        self.assertEqual(self.project()['assist']['pipeline_id'],'chosen')
        self.pipelines['other']=NS(**{**vars(self.pipeline),'id':'other','stt_engine':None})
        self.preferred='other'
        changed=self.project()
        self.assertEqual(changed['ha_stt']['state'],'unconfigured')
        self.assertNotEqual(first['revision'],changed['revision'])
        self.assert_no_processing()

    def test_stt_missing_unavailable_unsupported_and_unknown_are_not_ready(self):
        self.pipeline.stt_engine='stt.absent'
        self.assertEqual(self.project()['ha_stt']['state'],'unavailable')
        self.pipeline.stt_engine='stt.synthetic'
        self.stt.available=False
        self.assertEqual(self.project()['ha_stt']['state'],'unavailable')
        self.stt.available=True
        self.stt.check_metadata=lambda m:False
        self.assertEqual(self.project()['ha_stt']['state'],'unsupported')
        self.stt.check_metadata=None
        self.assertEqual(self.project()['ha_stt']['state'],'unknown')
        self.assert_no_processing()

    def test_tts_uses_qualified_locale_voice_and_only_explicit_gender(self):
        result=self.project()
        self.assertIsNone(result['ha_tts']['voices'][0]['gender'])
        self.assertEqual(result['ha_tts']['gender_selection']['values'],['female'])
        self.assertEqual(self.project(locale='nl-NL')['ha_tts']['state'],'unsupported')
        self.pipeline.tts_voice='missing'
        self.assertEqual(self.project()['ha_tts']['state'],'unsupported')
        self.pipeline.tts_voice='voice-a'
        self.tts.available=False
        self.assertEqual(self.project()['ha_tts']['state'],'unavailable')
        self.assert_no_processing()

    def test_all_five_locales_and_provider_gender_changes_are_recomputed(self):
        for language in ('en','nl','de','fr','es'):
            with self.subTest(language=language):
                self.pipeline.stt_language=self.pipeline.tts_language=language
                self.tts.supported_languages=[language]
                self.stt.check_metadata=lambda m:m.language == language
                result=self.project(locale=language)
                self.assertEqual(result['ha_stt']['state'],'available')
                self.assertEqual(result['ha_tts']['state'],'available')
        old=self.project(locale='es')
        self.tts.async_get_supported_voices=lambda lang:[NS(voice_id='voice-a',name='Alex')]
        changed=self.project(locale='es')
        self.assertEqual(changed['ha_tts']['gender_selection']['values'],[])
        self.assertNotEqual(old['revision'],changed['revision'])
        self.assert_no_processing()

    def test_conversation_validity_is_distinct_from_audio_configuration(self):
        self.agent.available=False
        result=self.project()
        self.assertEqual(result['assist']['conversation']['state'],'unavailable')
        self.assertEqual(result['ha_stt']['state'],'available')
        self.assertEqual(result['ha_tts']['state'],'available')
        self.assert_no_processing()

    def test_missing_metadata_and_discovery_errors_do_not_become_available(self):
        del self.stt.available
        self.assertEqual(self.project()['ha_stt']['state'],'unknown')
        def broken(metadata):
            raise ValueError('private provider exception')
        self.stt.check_metadata=broken
        result=self.project()
        self.assertEqual(result['ha_stt']['state'],'unknown')
        self.assertNotIn('private provider exception',json.dumps(result))
        self.assert_no_processing()

    def test_unexpected_provider_exception_cannot_export_private_reason_text(self):
        from custom_components.djconnect import speech_processor
        def broken(language):
            raise speech_processor.ProcessorUnavailable('private provider credentials or content')
        self.tts.async_get_supported_voices=broken
        result=self.project()
        self.assertEqual(result['ha_tts']['state'],'unknown')
        self.assertEqual(result['ha_tts']['reason'],'tts_discovery_failed')
        self.assertNotIn('private provider credentials or content',json.dumps(result))
        self.assert_no_processing()

    def test_speaker_target_is_independent_from_synthesis_and_never_claims_hearing(self):
        self.config['dj_announcement_speaker_entity_id']='media_player.room'
        self.states['media_player.room']=NS(state='idle',attributes={'supported_features':512})
        self.pipeline.tts_engine=None
        result=self.project()
        self.assertEqual(result['ha_speaker_target']['state'],'available')
        self.assertEqual(result['ha_tts']['state'],'unconfigured')
        self.assertEqual(result['ha_speaker_target']['audibility'],'not_tested')
        self.assertEqual(result['ha_speaker_target']['touch_reaction'],'not_qualified')
        self.assertIn('current_output_policy',result['ha_speaker_target']['requires'])
        self.assertEqual(result['text_only']['audio'],False)
        self.states['media_player.room'].state='unavailable'
        self.assertEqual(self.project()['ha_speaker_target']['state'],'unavailable')

    def test_private_health_is_owner_bound_expires_and_rejects_provider_replacement(self):
        from custom_components.djconnect import speech_feedback, speech_processor
        _,voice=speech_processor.configured_processor(self.hass,self.config,'en','default')
        speech_feedback.record(self.hass,self.runtime,'owner-a',voice,provider=self.tts,
                               reason='speech_preparation_failed')
        observed=self.project(owner='owner-a')['ha_tts']
        self.assertEqual(observed['state'],'available')
        self.assertEqual(observed['operational']['synthesis_state'],'failed')
        self.assertGreater(observed['operational']['retry_after_seconds'],0)
        now=speech_feedback.time.monotonic()
        with patch.object(speech_feedback.time,'monotonic',return_value=now+61):
            retry=self.project(owner='owner-a')['ha_tts']
            self.assertEqual(retry['state'],'available')
            self.assertEqual(retry['operational']['synthesis_state'],'failed')
            self.assertEqual(retry['operational']['retry_after_seconds'],0)
        self.assertEqual(self.project(owner='owner-b')['ha_tts']['operational']['synthesis_state'],'not_tested')
        self.assertEqual(self.project()['ha_tts']['operational']['synthesis_state'],'not_tested')
        original=self.tts
        self.tts=NS(**vars(original))
        self.assertEqual(self.project(owner='owner-a')['ha_tts']['operational']['synthesis_state'],'not_tested')
        self.tts=original
        with patch.object(speech_feedback.time,'monotonic',return_value=now+301):
            self.assertEqual(self.project(owner='owner-a')['ha_tts']['operational']['synthesis_state'],'not_tested')
        self.assert_no_processing()

    def test_publication_fence_rejects_revocation_entry_unload_and_wrong_device(self):
        def publish(authority,device=None):
            result={}
            self.owner.append_snapshot(result,self.hass,self.runtime,device_id=device or self.identity,
                client_type='ios',authority=authority)
            return result
        authority=self.owner.capture(self.hass,self.runtime,self.identity)
        self.assertIn('device_speech',publish(authority))
        self.assertNotIn('device_speech',publish(authority,'djconnect-ios-000000000000'))
        self.runtime.device_token='rotated'
        self.assertNotIn('device_speech',publish(authority))
        self.runtime.device_token=self.config['device_token']
        self.entry.state.value='unloaded'
        self.assertNotIn('device_speech',publish(authority))
        self.entry.state.value='loaded'
        self.runtime.authorize_device_request=lambda *args:False
        self.assertNotIn('device_speech',publish(authority))

    def test_snapshot_never_exports_secrets_full_config_or_inferred_apple_permissions(self):
        serialized=json.dumps(self.project())
        for forbidden in ('private-device-token','private-spotify-token','Private pipeline','spotify_refresh_token'):
            self.assertNotIn(forbidden,serialized)
        self.assertEqual(self.project()['apple_local'],
            {'stt':'client_owned','tts':'client_owned','permissions':'client_owned'})

    def test_status_collects_after_last_await_and_preserves_legacy_endpoint_booleans(self):
        async def run():
            started,release=asyncio.Event(),asyncio.Event()
            async def last_await(*args,**kwargs):
                started.set()
                await release.wait()
                return True
            request=NS(headers={'Authorization':'Bearer '+self.runtime.device_token})
            self.runtime.last_playback={}
            authority=self.owner.capture(self.hass,self.runtime,self.identity)
            with patch.object(self.http,'_status_backend_availability',last_await), \
                 patch.object(self.http,'_bootstrap_metadata',return_value={}), \
                 patch.object(self.http,'_push_status',new=AsyncMock(return_value={})), \
                 patch.object(self.http,'music_backend_metadata',return_value={}), \
                 patch.object(self.http,'async_ha_url_payload',new=AsyncMock(return_value={})), \
                 patch.object(self.http,'_debug_status_response'):
                task=asyncio.create_task(self.http._status_response(self.hass,self.runtime,request,
                    {'device_id':self.identity},'ios',None,{},speech_authority=authority))
                await asyncio.wait_for(started.wait(),2)
                self.pipeline.stt_engine=None
                release.set()
                result=await asyncio.wait_for(task,2)
                self.assertTrue(result['voice_supported'])
                self.assertTrue(result['ask_dj_audio_response_supported'])
                self.assertEqual(result['device_speech']['ha_stt']['state'],'unconfigured')
        asyncio.run(run())
        self.assert_no_processing()

    def test_status_revocation_during_first_await_cannot_publish_new_snapshot(self):
        async def run():
            started,release=asyncio.Event(),asyncio.Event()
            async def held_metadata(*args,**kwargs):
                started.set()
                await release.wait()
            runtime=self.runtime
            runtime.update=lambda **kwargs:None
            request=NS(app={'hass':self.hass},headers={'Authorization':'Bearer '+runtime.device_token},
                       json=AsyncMock(return_value={'device_id':self.identity,'client_type':'ios'}))
            with patch.object(self.http,'_update_memory_metadata',held_metadata), \
                 patch.object(self.http,'_persist_paired_device'), \
                 patch.object(self.http,'_status_backend_availability',new=AsyncMock(return_value=True)), \
                 patch.object(self.http,'_bootstrap_metadata',return_value={}), \
                 patch.object(self.http,'_push_status',new=AsyncMock(return_value={})), \
                 patch.object(self.http,'music_backend_metadata',return_value={}), \
                 patch.object(self.http,'async_ha_url_payload',new=AsyncMock(return_value={})), \
                 patch.object(self.http,'_debug_status_response'):
                task=asyncio.create_task(self.http.DJConnectStatusView(self.hass).post(request))
                await asyncio.wait_for(started.wait(),2)
                runtime.device_token='rotated-during-metadata'
                self.entry.data={**self.entry.data,'device_token':runtime.device_token}
                release.set()
                raw=await asyncio.wait_for(task,2)
                result=http_fixtures.VoiceHttpHelperTest.response_envelope(raw)
                self.assertNotIn('device_speech',result['payload'])
        asyncio.run(run())

    def test_profile_rebind_cannot_borrow_new_owner_health_during_request(self):
        from custom_components.djconnect.domain.storage import STORE_KEY
        profile=NS(profile_id='owner-a')
        device=NS(binding_generation='a'*32)
        storage=NS(_loaded=True,household=NS(devices={self.identity:device}),
            resolver=lambda:NS(resolve_bound_device=lambda device_id:profile))
        self.hass.data['djconnect'][STORE_KEY]=storage
        authority=self.owner.capture(self.hass,self.runtime,self.identity)
        profile=NS(profile_id='owner-b')
        device.binding_generation='b'*32
        result={}
        with patch.object(self.owner,'snapshot',side_effect=AssertionError('no_new_owner_probe')):
            self.owner.append_snapshot(result,self.hass,self.runtime,device_id=self.identity,
                client_type='ios',authority=authority)
        self.assertNotIn('device_speech',result)
