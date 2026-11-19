"""Actual paired HA status discovery; native metadata, zero speech processing."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time


async def run(hass, runtime, client, post, identity, output, headers, storage, base, processor, pair):
    from homeassistant.components import stt
    from homeassistant.components.assist_pipeline.pipeline import KEY_ASSIST_PIPELINE, async_get_pipeline
    from homeassistant.helpers.entity_component import EntityComponent
    from custom_components.djconnect import speech_feedback, speech_processor

    root = Path(__file__).resolve().parents[2]
    files = [*sorted((root/'custom_components/djconnect').rglob('*.py')), Path(__file__),
             Path(__file__).with_name('verify_hybrid_transport_http.py'),
             Path(__file__).with_name('verify_session_speech_http.py')]
    pins = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    process_calls = []

    class MetadataStt(stt.SpeechToTextEntity):
        _attr_name = 'Owned metadata qualification'
        _attr_unique_id = 'djc-owned-metadata-stt'

        @property
        def supported_languages(self):
            return ['en']

        @property
        def supported_formats(self):
            return [stt.AudioFormats.WAV]

        @property
        def supported_codecs(self):
            return [stt.AudioCodecs.PCM]

        @property
        def supported_bit_rates(self):
            return [stt.AudioBitRates(16)]

        @property
        def supported_sample_rates(self):
            return [stt.AudioSampleRates(16000)]

        @property
        def supported_channels(self):
            return [stt.AudioChannels(1)]

        async def async_process_audio_stream(self, metadata, stream):
            process_calls.append(True)
            raise AssertionError('Discovery must never process audio')

    component = EntityComponent(__import__('logging').getLogger(__name__), 'stt', hass)
    hass.data[stt.DATA_COMPONENT] = component
    entity = MetadataStt()
    entity.entity_id = 'stt.owned_metadata'
    await component.async_add_entities([entity])
    store = hass.data[KEY_ASSIST_PIPELINE].pipeline_store
    original = async_get_pipeline(hass)
    pipeline_id = original.id
    tts_id = original.tts_engine
    rows = [{'case':'ordinary_pair','snapshot':pair['device_speech']}]
    assert pair['device_speech']['schema_version'] == 1
    assert runtime.entry.data['device_token'] == runtime.device_token

    async def update(**changes):
        values = {**asdict(store.data[pipeline_id]), **changes}
        values.pop('id')
        await store.async_update_item(pipeline_id, values)

    async def read(case):
        body = await post('status', {**identity, 'locale':'en'})
        value = body['device_speech']
        assert body['voice_supported'] is True and body['ask_dj_audio_response_supported'] is True
        assert value['proof'] == 'current_configuration_not_remote_health_or_audio'
        assert value['text_only'] == {'available':True, 'audio':False}
        rows.append({'case':case, 'snapshot':value})
        return value

    for have_stt, have_tts in ((False,False),(True,False),(False,True),(True,True)):
        await update(stt_engine=entity.entity_id if have_stt else None,
            stt_language='en' if have_stt else None, tts_engine=tts_id if have_tts else None,
            tts_language='en' if have_tts else None, tts_voice='fixture-en' if have_tts else None)
        value = await read(f'configuration_stt_{have_stt}_tts_{have_tts}')
        assert value['assist']['conversation']['state'] == 'available', value
        assert value['ha_stt']['state'] == ('available' if have_stt else 'unconfigured'), value
        assert value['ha_tts']['state'] == ('available' if have_tts else 'unconfigured'), value

    unsupported = await post('status', {**identity, 'locale':'nl'})
    rows.append({'case':'locale_mismatch', 'snapshot':unsupported['device_speech']})
    assert unsupported['device_speech']['ha_stt']['state'] == 'unsupported'
    assert unsupported['device_speech']['ha_tts']['state'] == 'unsupported'

    other_data = {**asdict(original), 'name':'Owned alternate without speech',
                  'stt_engine':None, 'stt_language':None, 'tts_engine':None,
                  'tts_language':None, 'tts_voice':None}
    other_data.pop('id')
    other = await store.async_create_item(other_data)
    store.async_set_preferred_item(other.id)
    value = await read('preferred_changed')
    assert value['assist']['pipeline_id'] == other.id and value['ha_tts']['state'] == 'unconfigured'
    hass.config_entries.async_update_entry(runtime.entry,
        options={**runtime.entry.options,'assist_pipeline_id':pipeline_id})
    value = await read('explicit_ignores_other_preferred')
    assert value['assist']['pipeline_id'] == pipeline_id and value['ha_stt']['state'] == 'available'
    hass.config_entries.async_update_entry(runtime.entry,
        options={**runtime.entry.options,'assist_pipeline_id':'absent-selected'})
    value = await read('explicit_missing_no_borrow')
    assert value['ha_stt']['state'] == 'unknown' and value['ha_tts']['state'] == 'unknown'
    hass.config_entries.async_update_entry(runtime.entry,
        options={**runtime.entry.options,'assist_pipeline_id':pipeline_id})

    tts_entity, voice = speech_processor.configured_processor(hass,runtime.config,'en','default')
    speech_feedback.record(hass,runtime,'profile-a',voice,provider=tts_entity,reason='speech_preparation_failed')
    value = await read('same_owner_recent_failure')
    assert value['ha_tts']['state'] == 'available', value
    assert value['ha_tts']['operational']['synthesis_state'] == 'failed'
    # A controlled past deadline, not a claim of waiting five minutes.
    for item in hass.data['djconnect']['speech_provider_observations'].values():
        item['deadline'] = time.monotonic()-1
    value = await read('expired_observation')
    assert value['ha_tts']['operational']['synthesis_state'] == 'not_tested'

    await update(tts_engine=None,tts_voice=None,tts_language=None)
    hass.config_entries.async_update_entry(runtime.entry,
        options={**runtime.entry.options,'dj_announcement_speaker_entity_id':'media_player.owned_metadata'})
    hass.states.async_set('media_player.owned_metadata','idle',{'supported_features':512})
    value = await read('speaker_target_without_synthesis')
    assert value['ha_speaker_target']['state'] == 'available' and value['ha_tts']['state'] == 'unconfigured'
    assert value['ha_speaker_target']['audibility'] == 'not_tested'
    hass.states.async_set('media_player.owned_metadata','unavailable',{'supported_features':512})
    value = await read('speaker_target_withdrawal')
    assert value['ha_speaker_target']['state'] == 'unavailable'

    await component.async_remove_entity(entity.entity_id)
    value = await read('stt_entity_removed')
    assert value['ha_stt']['available'] is False
    async with client.post(base+'/api/djconnect/v1/status',json=identity,
            headers={'Authorization':'Bearer synthetic-wrong-token'}) as response:
        denied=await response.json()
        assert response.status == 401 and 'device_speech' not in denied
        rows.append({'case':'wrong_token', 'http_status':response.status})
    assert not processor[1] and not process_calls
    assert all(hashlib.sha256((root/p).read_bytes()).hexdigest() == digest for p,digest in pins.items())
    result = {'qualification':'ACTUAL_ISOLATED_HA_PAIRED_TLS_STATUS_METADATA',
        'pairing':'ordinary_device_token_minted_persisted', 'source_hashes':pins,
        'cases':rows, 'stt_process_calls':len(process_calls), 'tts_synthesis_calls':len(processor[1]),
        'model_calls':0, 'native':'NOT_RUN','installed':'NOT_RUN','audible':'NOT_RUN',
        'provider_boundary':'real native HA STT entity and Wyoming TTS metadata; external processing never invoked',
        'backend_boundary':'existing Spotify status provider fixture',
        'failure_boundary':'seeded owner-scoped observation; no failing synthesis executed',
        'expiry_boundary':'controlled past observation deadline; no elapsed-time or remote health claim'}
    (output/'device-speech-http.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'qualification':result['qualification'],'cases':len(rows),'speech_provider_calls':0}))
