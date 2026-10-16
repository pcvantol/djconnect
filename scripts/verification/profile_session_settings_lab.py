"""Owned real HA pairing/HTTP/Runtime/SQLite/Cloud-entity acceptance.

Only the external waveform and existing music provider boundaries are fixtures.
No installed HA mounts, credentials, client writer or audible acceptance.
"""

from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace
from uuid import UUID


async def run(hass, runtime, client, post, identity, output, headers, manager, storage, *, peers=()):
    from homeassistant.components import tts
    from homeassistant.components.cloud.tts import CloudTTSEntity
    from homeassistant.components.assist_pipeline.pipeline import KEY_ASSIST_PIPELINE, async_get_pipeline
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    from custom_components.djconnect.playback_observation import playback_observation_manager
    root = Path(__file__).resolve().parents[2]
    source_files = [*sorted((root/'custom_components/djconnect').rglob('*.py')),
                    Path(__file__), Path(__file__).with_name('profile_session_settings_ws_lab.py'),
                    Path(__file__).with_name('verify_session_speech_http.py')]
    source_hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}

    manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
    calls = []
    async def waveform(**kwargs):
        assert len(calls) < 12
        assert kwargs['gender'] is None
        calls.append({'voice': kwargs['voice'], 'language': kwargs['language'],
                      'text_sha256': hashlib.sha256(kwargs['text'].encode()).hexdigest()})
        return (b'\xff\xfb\x90\x00' + bytes(413))*2
    prefs = SimpleNamespace(tts_default_voice=('en-US', 'JennyNeural'),
                            async_listen_updates=lambda callback: lambda: None)
    entity = CloudTTSEntity(SimpleNamespace(client=SimpleNamespace(prefs=prefs),
                                          voice=SimpleNamespace(process_tts=waveform)))
    entity.entity_id = 'tts.owned_settings_cloud_fixture'
    await hass.data[tts.DATA_COMPONENT].async_add_entities([entity])
    store = hass.data[KEY_ASSIST_PIPELINE].pipeline_store
    previous = async_get_pipeline(hass)
    pipeline = await store.async_create_item({
        'name': 'Owned shared settings qualification', 'language': 'en',
        'conversation_engine': previous.conversation_engine, 'conversation_language': '*',
        'stt_engine': None, 'stt_language': None, 'tts_engine': entity.entity_id,
        'tts_language': 'en-US', 'tts_voice': 'JennyNeural', 'wake_word_entity': None, 'wake_word_id': None})
    hass.config_entries.async_update_entry(runtime.entry,
        data={**runtime.entry.data, 'assist_pipeline_id': pipeline.id})
    for entry_id in peers:
        peer = hass.config_entries.async_get_entry(entry_id)
        hass.config_entries.async_update_entry(peer, data={**peer.data, 'assist_pipeline_id': pipeline.id})
    counter = 0
    rows = []

    async def read(auth=headers):
        response = await client.get('/api/djconnect/v1/profile/settings', params={
            **identity, 'contract_version': '2'}, headers=auth)
        body = await response.json()
        assert response.headers['Cache-Control'] == 'no-store'
        return body, response.status

    async def choose(before, patch, expected=200):
        nonlocal counter
        counter += 1
        now = int(time.time()*1000)
        operation = str(UUID(int=(now << 80) | (7 << 76) | (2 << 62) | counter))
        session = before['snapshot']['session']
        request = {**identity, 'contract_version': 2, 'binding': before['binding'],
            'operation_id': operation, 'patch': patch,
            'expected_defaults_revision': before['snapshot']['defaults_revision'],
            'expected_session': {k: session[k] for k in ('session_id', 'generation', 'revision')} if session else None}
        response = await client.patch('/api/djconnect/v1/profile/settings', json=request, headers=headers)
        body = await response.json()
        assert response.status == expected, (response.status, body)
        assert response.headers['Cache-Control'] == 'no-store'
        return body, request

    first, status = await read()
    assert status == 200, first
    assert first['snapshot']['defaults_revision'] == 0 and first['snapshot']['session'] is None
    denied, status = await read({})
    assert status == 401 and 'snapshot' not in denied
    chosen = {'persona': 'radio_dj', 'voice': {'kind': 'provider_voice',
        'provider_id': entity.entity_id, 'voice_id': 'JennyNeural'}, 'gender': 'female',
        'mood': 'energy', 'presence': 'balanced'}
    accepted, request = await choose(first, chosen)
    assert accepted['snapshot']['defaults'] == chosen
    assert manager.current_active('profile-a') is None
    rows.append({'case': 'paired_no_session_all_five', 'response': accepted})
    started = await post('/session/start', {**identity, 'mood': 'chill', 'locale': 'en'}, expected=201)
    sid = started['session']['session_id']
    active = manager.current_active('profile-a')
    assert active.effective_dj_settings().as_dict() == chosen
    await playback_observation_manager(hass).async_stop('profile-a', sid)
    current, status = await read()
    assert status == 200 and current['snapshot']['session']['session_id'] == sid
    published = tuple(active.broadcast.state.dj_moments)
    assert published, 'Expected the real qualified opening contribution'
    moment = published[0]
    original_content = moment.content
    original_persona = moment.presentation_intent.dj_persona.value
    speech_request = {**identity, 'contract_version': 2, 'processor': 'ha_configured',
                      'reference': {'session_id': sid, 'moment_id': moment.moment_id}}
    first_speech = (await post('/speech/prepare', speech_request))['session_speech']
    assert first_speech['audio_state'] == 'ready', first_speech
    assert first_speech['effective_voice']['voice_id'] == 'JennyNeural'
    old_audio = {**identity, 'contract_version': 1,
                 'asset_id': first_speech['audio_reference']['asset_id']}
    audio_response = await client.post('/api/djconnect/v1/speech/audio', json=old_audio, headers=headers)
    first_audio = await audio_response.read()
    assert audio_response.status == 200 and first_audio
    changed, changed_request = await choose(current, {'persona': 'club_dj', 'mood': 'party', 'presence': 'music_only',
        'voice': {'kind': 'provider_voice', 'provider_id': entity.entity_id, 'voice_id': 'GuyNeural'}, 'gender': 'male'})
    active = manager.current_active('profile-a')
    assert active.effective_dj_settings().as_dict() == changed['snapshot']['session']['settings']
    assert active.effective_dj_settings().as_dict() == changed['snapshot']['defaults']
    assert tuple(active.broadcast.state.dj_moments) == published
    await post('/speech/audio', old_audio, expected=404)
    second_speech = (await post('/speech/prepare', speech_request))['session_speech']
    assert second_speech['audio_state'] == 'ready', second_speech
    assert second_speech['effective_voice']['voice_id'] == 'GuyNeural'
    assert second_speech['source_expires_at'] == first_speech['source_expires_at']
    assert moment.content == original_content and moment.presentation_intent.dj_persona.value == original_persona
    assert calls == [
        {'voice': voice, 'language': 'en-US', 'text_sha256': hashlib.sha256(original_content.encode()).hexdigest()}
        for voice in ('JennyNeural', 'GuyNeural')]
    assert async_get_pipeline(hass, pipeline.id).tts_voice == 'JennyNeural'
    rows.append({'case': 'actual_ha_tts_shared_voice_gender_source_expiry_and_old_audio_fence',
                 'calls': list(calls), 'audio_bytes_sha256': hashlib.sha256(first_audio).hexdigest(),
                 'original_persona': original_persona, 'old_text_unchanged': True,
                 'audible_native_acceptance': 'NOT_RUN'})
    response = await client.patch('/api/djconnect/v1/profile/settings', json=changed_request, headers=headers)
    replay = await response.json()
    assert response.status == 200 and replay['replayed']
    assert manager.current_active('profile-a').settings_revision == 1
    rows.append({'case': 'active_atomic_all_five_and_replay', 'response': changed})
    conflict, _ = await choose(current, {'mood': 'chill'}, expected=409)
    assert conflict['error'] == 'settings_revision_conflict'
    at = manager.dj_settings_fence_token('profile-a')
    for _ in range(3):
        same, status = await read()
        assert status == 200 and same['snapshot'] == replay['snapshot']
    assert manager.dj_settings_fence_token('profile-a') == at
    await manager.async_update_mood(owner_profile_id='profile-a', session_id=sid, selected_mood='groove')
    evolved, status = await read()
    assert evolved['snapshot']['session']['settings']['mood'] == 'groove'
    assert evolved['snapshot']['defaults']['mood'] == 'party'
    before_bad = evolved['snapshot']
    bad, _ = await choose(evolved, {'gender': 'female'}, expected=409)
    assert bad['error'] == 'voice_gender_conflict'
    after_bad, _ = await read()
    assert after_bad['snapshot'] == before_bad
    update = asdict(pipeline)
    update.pop('id')
    await store.async_update_item(pipeline.id, {**update, 'tts_engine': 'tts.missing'})
    withdrawn, status = await read()
    assert status == 200 and not withdrawn['voice_availability']['available']
    assert withdrawn['snapshot']['defaults']['voice']['voice_id'] == 'GuyNeural'
    rows.append({'case': 'automatic_mood_default_preserved_and_provider_withdrawal', 'response': withdrawn})
    await store.async_update_item(pipeline.id, update)
    await post('/session/end', {**identity, 'session_id': sid})
    await post('/session/start', {**identity, 'locale': 'en'}, expected=201)
    successor = manager.current_active('profile-a')
    assert successor.session_id != sid
    assert successor.effective_dj_settings().as_dict() == changed['snapshot']['defaults']
    await playback_observation_manager(hass).async_stop('profile-a', successor.session_id)
    await post('/session/end', {**identity, 'session_id': successor.session_id})
    receipt = await post('/profile/settings/operation', {**identity, 'contract_version': 2,
        'binding': request['binding'], 'operation_id': changed_request['operation_id']})
    assert receipt['phase'] == 'accepted'
    assert receipt['receipt']['snapshot'] == changed['snapshot']
    rows.append({'case': 'successor_defaults_and_original_receipt_after_end', 'response': receipt})
    websocket = 'NOT_RUN'
    if (output/'server.pem').exists():
        from profile_session_settings_ws_lab import run as websocket_probe
        rows.append(await websocket_probe(hass, runtime, client, identity, output, peers))
        websocket = 'PASS_PAIRED_TLS_THREE_SURFACES_AND_PROFILE_ISOLATION'
    assert len(calls) == 2
    assert source_hashes == {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}
    result = {'result': 'PASS_CORE_PAIRED_HTTP_RUNTIME_SQLITE', 'as_of': datetime.now(UTC).isoformat(),
        'cases': rows, 'waveform_calls': len(calls),
        'source_hashes_before_and_after': source_hashes,
        'boundaries': {'provider': 'installed_HA_Cloud_entity_external_waveform_fixture',
                       'real_speech': 'PASS_CORE_HA_SYNTHESIS_EXTERNAL_WAVEFORM_FIXTURE_NOT_AUDIBLE',
                       'websocket': websocket, 'native': 'OPEN', 'installed': 'NOT_RUN'}}
    (output/'profile-settings-http.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PROFILE_SETTINGS_PAIRED_HTTP_PASS', flush=True)
