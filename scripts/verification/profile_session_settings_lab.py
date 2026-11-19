"""Owned real HA pairing/HTTP/Runtime/SQLite/Cloud-entity acceptance.

Only the external waveform and existing music provider boundaries are fixtures.
No installed HA mounts, credentials, client writer or audible acceptance.
"""

from dataclasses import asdict, replace
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace
from uuid import UUID


async def run(hass, runtime, client, post, identity, output, headers, manager, storage, *, peers=(), browser_serve=None):
    from homeassistant.components import tts
    from homeassistant.components.cloud.tts import CloudTTSEntity
    from homeassistant.components.assist_pipeline.pipeline import KEY_ASSIST_PIPELINE, async_get_pipeline
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    from custom_components.djconnect.playback_observation import playback_observation_manager
    root = Path(__file__).resolve().parents[2]
    source_files = [*sorted((root/'custom_components/djconnect').rglob('*.py')),
                    Path(__file__), Path(__file__).with_name('profile_session_settings_ws_lab.py'),
                    Path(__file__).with_name('manual_pi_pairing_lab.py'),
                    Path(__file__).with_name('verify_session_speech_http.py'),
                    Path(__file__).with_name('session_speech_browser_lab.py'),
                    Path(__file__).with_name('session_speech_browser.mjs')]
    source_hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}

    manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
    # Ordinary legacy HTTP entry without an explicit Mood must stay usable.
    # This precedes Cloud setup, so the existing real HA Wyoming entity owns
    # the qualified synthesis; only its external waveform service is a fixture.
    legacy_created = await post('/session/start', {**identity, 'locale': 'en'}, expected=201)
    legacy_sid = legacy_created['session']['session_id']
    legacy_session = manager.current_active('profile-a')
    assert legacy_session.selected_mood == '' and legacy_session.settings_contract_version == 1
    legacy_answer = await post('/ask_dj/message', {**identity, 'client_message_id': 'legacy-unknown-mood-probe',
        'text': 'help', 'audio_response': 'never', 'speech_contract_version': 1,
        'context': {'session_id': legacy_sid}})
    legacy_prepared = await post('/speech/prepare', {**identity, 'contract_version': 1,
        'processor': 'ha_configured', 'voice_preference': 'default',
        'reference': legacy_answer['session_speech']['reference']})
    assert legacy_prepared['success'] and legacy_prepared['session_speech'].get('reason') not in {
        'invalid_mood', 'settings_unavailable', 'settings_migration_choice_required'}, legacy_prepared
    response = await client.get('/api/djconnect/v1/profile/settings',
        params={**identity, 'contract_version': '3'}, headers=headers)
    legacy_read = await response.json()
    assert response.status == 200 and not legacy_read['snapshot']['activated']
    assert legacy_read['snapshot']['session']['settings'] is None
    assert legacy_read['snapshot']['session']['selection_required']
    assert legacy_read['migration']['requires_review']
    assert manager.current_active('profile-a').selected_mood == ''
    await playback_observation_manager(hass).async_stop('profile-a', legacy_sid)
    await post('/session/end', {**identity, 'session_id': legacy_sid})
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
    rows = [{'case': 'ordinary_legacy_HTTP_start_unknown_mood_askdj1_prepare1_settings_read',
             'response': legacy_read,
             'speech_state': legacy_prepared['session_speech'].get('audio_state', 'unavailable'),
             'speech_reason': legacy_prepared['session_speech'].get('reason'),
             'activation': False, 'invented_mood': False}]
    from manual_pi_pairing_lab import run as manual_pi_pairing_probe
    rows.append(await manual_pi_pairing_probe(hass, runtime, storage))

    async def read(auth=headers):
        response = await client.get('/api/djconnect/v1/profile/settings', params={
            **identity, 'contract_version': '3'}, headers=auth)
        body = await response.json()
        assert response.headers['Cache-Control'] == 'no-store'
        return body, response.status

    async def choose(before, patch, expected=200):
        nonlocal counter
        counter += 1
        now = int(time.time()*1000)
        operation = str(UUID(int=(now << 80) | (7 << 76) | (2 << 62) | counter))
        session = before['snapshot']['session']
        request = {**identity, 'contract_version': 3, 'binding': before['binding'],
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
    # Real Profile Store + ConfigEntry evidence, real owner HTTP admission and
    # SQLite rollback. This is not a mocked registration/query chain.
    from custom_components.djconnect.domain import ResponseStyle, VoiceStyle
    from custom_components.djconnect.settings_migration import async_retire_activated
    profile = storage.household.profiles['profile-a']
    await storage.async_update_profile('profile-a', preferences=replace(
        profile.preferences, response_style=ResponseStyle.EXPRESSIVE, voice_style=VoiceStyle.ENERGY))
    hass.config_entries.async_update_entry(runtime.entry,
        data={**runtime.entry.data, 'voice_profile': 'late_night'})
    first, status = await read()
    assert status == 200 and first['migration']['requires_review']
    rejected, _ = await choose(first, {'mood': 'chill'}, expected=409)
    assert rejected['error'] == 'settings_migration_choice_required'
    unchanged, status = await read()
    assert status == 200 and unchanged['snapshot'] == first['snapshot']
    await async_retire_activated(hass, storage, manager._settings_repository)
    assert runtime.entry.data['voice_profile'] == 'late_night'
    rows.append({'case': 'legacy_partial_activation_rejected_without_mapping',
                 'response': rejected, 'unchanged_snapshot': unchanged['snapshot']})
    chosen = {'persona': 'radio_dj', 'voice': {'kind': 'provider_voice',
        'provider_id': entity.entity_id, 'voice_id': 'JennyNeural'}, 'gender': 'female',
        'mood': 'energy', 'presence': 'balanced', 'announcement_output': 'client_device'}
    accepted, request = await choose(first, chosen)
    assert accepted['snapshot']['defaults'] == chosen
    assert manager.current_active('profile-a') is None
    rows.append({'case': 'paired_no_session_all_five', 'response': accepted})
    await async_retire_activated(hass, storage, manager._settings_repository)
    assert 'voice_profile' not in runtime.entry.data
    retired, status = await read()
    assert status == 200 and not retired['migration']['legacy_cleanup_pending']
    assert retired['binding'] == first['binding']
    assert retired['snapshot'] == accepted['snapshot']
    rows.append({'case': 'accepted_legacy_retirement_preserves_binding_and_defaults',
                 'response': retired})
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
    assert original_persona == chosen['persona']
    speech_request = {**identity, 'contract_version': 3, 'processor': 'ha_configured',
                      'intent': 'manual', 'target': 'local',
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
    text_only, _ = await choose(withdrawn, {'announcement_output': 'text_only'})
    blocked = (await post('/speech/prepare', speech_request))['session_speech']
    assert blocked['reason'] == 'announcement_text_only' and not blocked['manual_allowed']
    from custom_components.djconnect.dj_response import async_create_dj_audio_url
    assert await async_create_dj_audio_url(hass, runtime, 'Bounded legacy device reply') is None
    await post('/speech/audio', {**identity, 'contract_version': 1,
        'asset_id': second_speech['audio_reference']['asset_id']}, expected=404)
    owner_projection = manager.current_active('profile-a').broadcast.as_dict()
    assert owner_projection['session_speech']['moments']
    assert all(not entry['manual_allowed'] for entry in owner_projection['session_speech']['moments'])
    shared_projection = manager.current_active('profile-a').broadcast.as_dict(include_owner_only=False)
    assert 'session_speech' not in shared_projection
    assert 'announcement_output' not in json.dumps(shared_projection)
    assert len(calls) == 2
    restored_output, _ = await choose(text_only, {'announcement_output': 'client_device'})
    assert restored_output['snapshot']['defaults'] == changed['snapshot']['defaults']
    restored_output, speaker_evidence, speaker_sink = await speaker_probe(hass, runtime, client, identity, output, headers, manager, restored_output, choose, speech_request['reference'])
    rows.append(speaker_evidence)
    rows.append({'case': 'text_only_zero_synthesis_old_audio_denied_and_owner_controls_removed',
        'response': text_only, 'additional_synthesis_calls': 0, 'shared_settings_leak': False})
    await post('/session/end', {**identity, 'session_id': sid})
    before_successor_waveforms = len(calls)
    before_successor_speaker_fetches = len(speaker_sink[0])
    await post('/session/start', {**identity, 'locale': 'en'}, expected=201)
    successor = manager.current_active('profile-a')
    assert successor.session_id != sid
    assert successor.effective_dj_settings().as_dict() == changed['snapshot']['defaults']
    # The current opening contract permits one informative visual welcome at
    # Music-only. It must not become automatic speech or another contribution.
    from custom_components.djconnect.session_opening import opening_context
    from custom_components.djconnect.session_speech import moment_projection
    openings = successor.broadcast.state.dj_moments
    assert len(openings) == 1, 'music_only permits only the original informative opening'
    opening = openings[0]
    assert opening_context(opening) == successor.opening_context
    assert opening.session_id == successor.session_id and opening.visual_only
    assert not moment_projection(successor.broadcast, opening, autoplay=True)['autoplay_eligible']
    opening_identity = (opening.moment_id, opening.content, opening.generation_metadata)
    assert len(calls) == before_successor_waveforms
    assert len(speaker_sink[0]) == before_successor_speaker_fetches
    successor_state, status = await read()
    assert status == 200
    raised, _ = await choose(successor_state, {'presence': 'balanced'})
    successor = manager.current_active('profile-a')
    assert successor.selected_presence == 'balanced'
    assert len(successor.broadcast.state.dj_moments) == 1
    retained_opening = successor.broadcast.state.dj_moments[0]
    assert (retained_opening.moment_id, retained_opening.content,
            retained_opening.generation_metadata) == opening_identity
    await hass.async_block_till_done()
    assert len(calls) == before_successor_waveforms, 'raising Presence must not synthesize the old opening'
    assert len(speaker_sink[0]) == before_successor_speaker_fetches
    assert raised['snapshot']['defaults']['persona'] == 'club_dj'
    assert raised['snapshot']['defaults']['mood'] == 'party'
    rows.append({'case': 'published_opening_persona_then_inherited_off_and_no_catchup',
                 'original_published_persona': original_persona,
                 'successor_persona': successor.dj_persona.value,
                 'successor_mood': successor.selected_mood,
                 'music_only_informative_visual_openings': 1,
                 'music_only_automatic_speech': 0, 'raised_presence_catchup': 0,
                 'original_opening_identity_and_body_preserved': True})
    await playback_observation_manager(hass).async_stop('profile-a', successor.session_id)
    await post('/session/end', {**identity, 'session_id': successor.session_id})
    receipt = await post('/profile/settings/operation', {**identity, 'contract_version': 3,
        'binding': request['binding'], 'operation_id': changed_request['operation_id']})
    assert receipt['phase'] == 'accepted'
    assert receipt['receipt']['snapshot'] == changed['snapshot']
    rows.append({'case': 'successor_defaults_and_original_receipt_after_end', 'response': receipt})
    websocket = 'NOT_RUN'
    if (output/'server.pem').exists():
        from profile_session_settings_ws_lab import run as websocket_probe
        rows.append(await websocket_probe(hass, runtime, client, identity, output, peers))
        websocket = 'PASS_PAIRED_TLS_THREE_SURFACES_AND_PROFILE_ISOLATION'
    rows.append(await automatic_probe(hass, client, identity, manager, read, choose, post, speaker_sink, headers))
    if browser_serve is not None:
        import asyncio
        before_browser_calls = len(calls)
        created = await post('/session/start', {**identity, 'locale':'en'}, expected=201)
        browser_session = manager.current_active('profile-a')
        assert browser_session.session_id == created['session']['session_id']
        # The initial direction may precede the first playback observation and
        # is correctly ineligible once a current track exists. Wait for an
        # actual naturally budgeted, track-bound published contribution rather
        # than rewriting its identity, timestamp, placement or deadline.
        browser_moment = None
        for _ in range(650):
            browser_session = manager.current_active('profile-a')
            projection = browser_session.broadcast.as_dict(include_owner_only=False)
            candidates = [m for m in projection['dj_moments']
                          if m.get('playback_item_id') == projection['playback']['item_id']]
            if candidates:
                chosen_id = candidates[-1]['moment_id']
                browser_moment = next(m for m in browser_session.broadcast.state.dj_moments
                                      if m.moment_id == chosen_id)
                break
            await asyncio.sleep(.1)
        assert browser_moment is not None, 'No naturally qualified current-track Moment for browser proof'
        async def output_change(value):
            before, status = await read()
            assert status == 200
            accepted, _ = await choose(before, {'announcement_output':value})
            assert accepted['snapshot']['session']['settings']['announcement_output'] == value
            assert len(calls) == before_browser_calls
        async with browser_serve(client, identity, post, browser_session, browser_moment,
                                 output_change=output_change):
            assert len(calls) == before_browser_calls
        rows.append({'case':'actual_settings3_shared_renderer_both_builds_portrait_landscape',
                     'local_and_static':'PASS_BROWSER', 'mode_toggle_synthesis_calls':0,
                     'native':'NOT_RUN', 'hardware':'NOT_RUN', 'CAF':'MODELED_ONLY'})
    assert len(calls) == 4  # Two voice variants, explicit replay and one new automatic publication.
    assert source_hashes == {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}
    result = {'result': 'PASS_CORE_PAIRED_HTTP_RUNTIME_SQLITE', 'as_of': datetime.now(UTC).isoformat(),
        'cases': rows, 'waveform_calls': len(calls),
        'source_hashes_before_and_after': source_hashes,
        'boundaries': {'provider': 'installed_HA_Cloud_entity_external_waveform_fixture',
                       'real_speech': 'PASS_CORE_HA_SYNTHESIS_EXTERNAL_WAVEFORM_FIXTURE_NOT_AUDIBLE',
                       'websocket': websocket, 'native': 'OPEN', 'installed': 'NOT_RUN'}}
    (output/'profile-settings-http.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PROFILE_SETTINGS_PAIRED_HTTP_PASS', flush=True)


async def speaker_probe(hass, runtime, client, identity, output, headers, manager, current, choose, reference):
    """Actual HA media-player service + anonymous constrained media fetch.

    Only the external speaker sink is a fixture; no audible/hardware claim.
    """
    import asyncio
    import ssl
    from aiohttp import web
    from homeassistant.components import media_player
    from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState
    from custom_components.djconnect import hybrid_service
    from uuid import UUID

    received = []
    fetched = asyncio.Event()
    class OwnedSpeaker(MediaPlayerEntity):
        _attr_name = 'Own bounded test speaker'
        _attr_unique_id = 'djc-settings-owned-speaker'
        _attr_supported_features = MediaPlayerEntityFeature.PLAY_MEDIA
        _attr_state = MediaPlayerState.IDLE
        async def async_play_media(self, media_type, media_id, **kwargs):
            async with client.session.get(media_id) as response:
                data = await response.read()
                received.append({'status': response.status, 'bytes': len(data),
                    'checksum': hashlib.sha256(data).hexdigest(), 'url': media_id,
                    'cache': response.headers.get('Cache-Control')})
            fetched.set()
    speaker = OwnedSpeaker()
    speaker.entity_id = 'media_player.djc_settings_owned'
    await hass.data[media_player.DATA_COMPONENT].async_add_entities([speaker])
    hass.config_entries.async_update_entry(runtime.entry, data={**runtime.entry.data,
        'dj_announcement_speaker_entity_id':speaker.entity_id})
    original_internal = hass.config.internal_url
    hass.config.internal_url = str(client.server.make_url('')).rstrip('/')
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(output/'server.pem', output/'server-key.pem')
    site = web.TCPSite(client.server.runner, '127.0.0.1', 18238, ssl_context=tls)
    await site.start()
    try:
        chosen, _ = await choose(current, {'announcement_output':'ha_speaker'})
        journal = hybrid_service.operations(hass)
        created = int(time.time()*1000)
        operation_id = str(UUID(int=(created << 80) | (7 << 76) | (2 << 62) | 901))
        envelope = {'identity':identity, 'contract_version':1,
            'operation_id':operation_id, 'operation_epoch':journal.journal.epoch,
            'operation':'session/speech/play', 'payload': {'contract_version':3,
                'processor':'ha_configured', 'intent':'manual', 'target':'ha_speaker', 'reference':reference}}
        async def execute():
            response = await client.session.post('https://127.0.0.1:18238/api/djconnect/v1/transport/operation',
                json=envelope, headers=headers, ssl=False)
            body = await response.json()
            assert response.status == 200, (response.status, body)
            return body
        first = await execute()
        await asyncio.wait_for(fetched.wait(), 3)
        replay = await execute()
        assert first['delivery']['ha_speaker'] == 'queued'
        assert first['delivery']['audible'] == 'not_proven'
        assert replay['operation_receipt']['phase'] == 'confirmed'
        assert len(received) == 1 and received[0]['status'] == 200 and received[0]['bytes'] > 0, received
        assert received[0]['cache'] == 'no-store'
        assert 'audio_reference' not in first['session_speech']
        assert received[0]['url'] not in json.dumps(first)
        # Revocation takes effect on the actual bearer-free speaker fetch route.
        off, _ = await choose(chosen, {'announcement_output':'text_only'})
        async with client.session.get(received[0]['url']) as denied:
            assert denied.status == 404
        restored, _ = await choose(off, {'announcement_output':'client_device'})
        return restored, {'case':'actual_HA_media_player_service_private_media_fetch_and_operation_retry',
            'queued':True, 'actual_media_fetches':len(received), 'bytes':received[0]['bytes'],
            'checksum':received[0]['checksum'], 'text_only_old_grant_status':404,
            'native':'NOT_RUN', 'audible':'NOT_PROVEN', 'hardware':'NOT_RUN'}, (received, fetched)
    finally:
        hass.config.internal_url = original_internal
        await site.stop()


async def automatic_probe(hass, client, identity, manager, read, choose, post, sink, headers):
    """A genuine new HA Session opening drives one automatic speaker effect."""
    import asyncio
    received, fetched = sink
    count = len(received)
    fetched.clear()
    original_url = hass.config.internal_url
    hass.config.internal_url = str(client.server.make_url('')).rstrip('/')
    try:
        before, status = await read()
        assert status == 200 and before['snapshot']['session'] is None
        await choose(before, {'announcement_output':'ha_speaker', 'presence':'balanced'})
        response = await client.post('/api/djconnect/v1/session/start', json={**identity, 'locale':'en'},
                                     headers={name.lower():value for name,value in headers.items()})
        started = await response.json()
        assert response.status == 201, started
        session_id = started['session']['session_id']
        try:
            await asyncio.wait_for(fetched.wait(), 5)
        except TimeoutError:
            from custom_components.djconnect.hybrid_service import operations
            print({'automatic_probe': 'no_fetch', 'moment_count': len(manager.current_active('profile-a').broadcast.state.dj_moments),
                   'operation_outcomes': [(r['phase'],r.get('error')) for r in operations(hass).journal._state['records'].values()]}, flush=True)
            raise
        assert len(received) == count+1 and received[-1]['status'] == 200
        active = manager.current_active('profile-a')
        assert active.broadcast.state.dj_moments
        for _ in range(3):
            current, status = await read()
            assert status == 200
            response = await client.get('/api/djconnect/v1/session/active', params=identity,
                                        headers=headers)
            assert response.status == 200
            await response.read()
        local, _ = await choose(current, {'announcement_output':'client_device'})
        await choose(local, {'announcement_output':'ha_speaker'})
        await hass.async_block_till_done()
        assert len(received) == count+1  # No catch-up on reads or output switches.
        await post('/session/end', {**identity, 'session_id':session_id})
        async with client.session.get(received[-1]['url']) as denied:
            assert denied.status == 404
        closed, _ = await read()
        await choose(closed, {'announcement_output':'client_device'})
        return {'case':'actual_new_session_publication_automatic_speaker_no_read_or_toggle_catchup',
            'new_publications_delivered':1, 'read_or_toggle_deliveries':0,
            'session_end_media_status':404, 'audible':'NOT_PROVEN', 'hardware':'NOT_RUN'}
    finally:
        hass.config.internal_url = original_url
