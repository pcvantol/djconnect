"""Actual paired Mac passive v3; original observations/covers, no live provider."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import uuid
from unittest.mock import patch


async def run(*, hass, runtime, client, headers, identity, manager, storage, sid,
              calls, output, source_hashes, second_identity, selected, second_headers, watch_identity, watch_headers):
    from custom_components.djconnect.playback_observation import playback_observation_manager
    from custom_components.djconnect.passive_session import BASE, capability
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    await playback_observation_manager(hass).async_stop('profile-a', sid)
    manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
    # This Mac was paired through the ordinary route before source/cover capture.
    headers = second_headers
    assert type(headers) is dict and headers.get('Authorization', '').startswith('Bearer ')
    identity = second_identity
    active = manager.current_active('profile-a')
    b = active.broadcast
    original = b.passive_observation
    assert original and type(original[2].position_ms) is int and original[2].duration_ms > 0
    cases, examples = {}, []
    base = {**identity, 'contract_version': 1, 'session_id': sid, 'surface': 'widget', 'projection_version': 3}
    consent = {**base, 'enabled': True, 'os_snapshot_cache': True, 'locked_display': False}

    async def request(path, payload, expected=200, auth=None):
        response = await client.post(BASE+path, json=payload, headers=headers if auth is None else auth)
        body = await response.json()
        assert response.status == expected, (path, response.status, body)
        assert response.headers['Cache-Control'] == 'no-store'
        return body

    assert capability()['projection_versions'] == [1, 2, 3]
    assert capability()['default_projection_version'] == 1
    await request('/authorize', {**consent, 'os_snapshot_cache': False}, 403)
    await request('/authorize', consent, 401, {})
    authorized = await request('/authorize', consent)
    read = {**base, 'grant_id': authorized['grant_id']}
    frame = authorized['passive_session']
    assert frame['schema_version'] == 3 and frame['contribution'] and frame['now_playing'] and frame['artwork'], frame
    progress = frame['now_playing']['progress']
    assert progress['position_ms'] == original[2].position_ms and progress['duration_ms'] == original[2].duration_ms
    assert progress['playback_state'] == 'playing'
    assert b.passive_observation is original
    cases['ordinary_mac_pairing_explicit_v3_consent_original_progress_text_and_cover'] = 'PASS'
    examples.append({'case': 'original_mac_v3', 'passive_session': frame})
    live_consent = {**consent, 'surface':'live_activity'}
    await request('/authorize', live_consent, 403)
    live = await request('/authorize', {**live_consent, 'locked_display':True})
    live_read = {**base, 'surface':'live_activity', 'grant_id':live['grant_id']}
    live_frame = (await request('/read', live_read))['passive_session']
    assert live_frame['cache_policy']['locked_display'] is True
    assert live_frame['now_playing']['progress'] == progress
    assert capability()['background_delivery'] is False
    cases['live_activity_requires_locked_display_no_background_authority_added'] = 'PASS'
    examples.append({'case':'live_activity_v3', 'passive_session':live_frame})
    for version in (1, 2):
        await request('/read', {**read, 'projection_version': version}, 403)
    await request('/read', {k:v for k,v in read.items() if k!='projection_version'}, 403)
    cases['grant_version_cannot_silently_upgrade_or_downgrade'] = 'PASS'
    art = next(a for a in frame['artwork'] if a['slot'] == 'now_playing')
    image = await client.get(art['image_path'], params={**identity, 'contract_version':'1',
        'surface':'widget', 'projection_version':'3', 'grant_id':authorized['grant_id']}, headers=headers)
    pixels = await image.read()
    assert image.status == 200 and pixels.startswith(b'\x89PNG')
    cases['original_prepared_current_cover_bytes_no_foreground_url_borrowing'] = 'PASS'
    image_digest = hashlib.sha256(pixels).hexdigest()
    watch_base = {**watch_identity, 'contract_version':1, 'session_id':sid,
                  'surface':'watch_widget', 'projection_version':1}
    watch_consent = {**watch_base, 'enabled':True, 'os_snapshot_cache':True, 'locked_display':True}
    await request('/authorize', {**watch_consent, 'locked_display':False}, 403, watch_headers)
    await request('/authorize', {**watch_consent, 'os_snapshot_cache':False}, 403, watch_headers)
    for invalid in ({'projection_version':3}, {'client_type':'macos'}, {'surface':'widget'}):
        await request('/authorize', {**watch_consent, **invalid}, 400, watch_headers)
    watch = await request('/authorize', watch_consent, auth=watch_headers)
    watch_read = {**watch_base, 'grant_id':watch['grant_id']}
    watch_frame = watch['passive_session']
    assert watch_frame['scope'] == 'paired_watch_widget_v1'
    assert watch_frame['now_playing']['track'] == frame['now_playing']['track']
    assert set(watch_frame['now_playing']) == {'item_id','subject_uri','track','observed_at',
        'expires_at','source_url','attribution','usage_basis'}
    assert all(k not in watch_frame for k in ('contribution','persona','presence','navigation','playback_state'))
    assert len(watch_frame['artwork']) == 1
    watch_art = watch_frame['artwork'][0]
    assert watch_art['role'] == 'current_cover' and watch_art['rights']['paired_watch_cache'] is True
    assert watch_art['rights']['watch_replication'] is False
    cases['ordinary_watch_pairing_separate_minimal_scope_and_locked_consent'] = 'PASS'
    await request('/read', {**watch_read, 'grant_id':authorized['grant_id']}, 403, watch_headers)
    await request('/read', {**read, 'grant_id':watch['grant_id']}, 403)
    cases['watch_and_phone_grants_never_cross_scope'] = 'PASS'
    watch_image = await client.get(watch_art['image_path'], params={**watch_identity,
        'contract_version':'1', 'surface':'watch_widget', 'projection_version':'1',
        'grant_id':watch['grant_id']}, headers=watch_headers)
    assert watch_image.status == 200 and await watch_image.read() == pixels
    cases['own_watch_original_current_cover_bytes'] = 'PASS'
    examples.append({'case':'minimal_watch_widget', 'passive_session':watch_frame})
    before = (len(calls), len(b.state.dj_moments), active.presence_ledger.total_published,
              b.delivery_sequence, len(hass.data['djconnect']['session_images'].assets))
    for _ in range(20):
        again = (await request('/read', read))['passive_session']
        assert again['now_playing']['progress'] == progress
        assert again['contribution'] == frame['contribution']
        assert again['revision'] == frame['revision']
        watch_again = (await request('/read', watch_read, auth=watch_headers))['passive_session']
        assert watch_again['revision'] == watch_frame['revision']
    after = (len(calls), len(b.state.dj_moments), active.presence_ledger.total_published,
             b.delivery_sequence, len(hass.data['djconnect']['session_images'].assets))
    assert before == after and b.passive_observation is original
    cases['twenty_reads_no_model_provider_preparation_mutation_or_arrival_renewal'] = 'PASS'
    b.update_playback_progress(replace(b.state.playback, position_ms=original[2].position_ms+1000))
    ticked = (await request('/read', read))['passive_session']
    assert ticked['now_playing']['progress'] == progress and b.passive_observation is original
    cases['renderer_tick_never_replaces_original_observation_or_clock'] = 'PASS'
    # Exercise the same confirmed settings3 path as the actual clients.
    snapshot_response = await client.get('/api/djconnect/v1/profile/settings',
        params={**identity, 'contract_version':'3'}, headers=headers)
    snapshot = await snapshot_response.json()
    assert snapshot_response.status == 200, snapshot
    session = snapshot['snapshot']['session']
    mood_response = await client.patch('/api/djconnect/v1/profile/settings', headers=headers, json={
        **identity, 'contract_version':3, 'binding':snapshot['binding'], 'operation_id':str(uuid.uuid7()),
        'patch':{'mood':'energy'}, 'expected_defaults_revision':snapshot['snapshot']['defaults_revision'],
        'expected_session':{k:session[k] for k in ('session_id','generation','revision')}})
    mood = await mood_response.json()
    assert mood_response.status == 200, mood
    changed = (await request('/read', read))['passive_session']
    assert changed['mood']['value'] == 'energy' and b.passive_observation is original
    assert changed['now_playing']['item_id'] == frame['now_playing']['item_id']
    assert changed['now_playing']['progress'] == progress
    assert changed['contribution'] == frame['contribution']
    cases['confirmed_settings3_mood_preserves_subject_original_sample_and_contribution_lease'] = 'PASS'
    examples.append({'case':'confirmed_mood', 'passive_session':changed})
    watch_changed = (await request('/read', watch_read, auth=watch_headers))['passive_session']
    assert watch_changed['mood']['value'] == 'energy'
    assert watch_changed['now_playing'] == watch_frame['now_playing']
    assert watch_changed['artwork'] == watch_frame['artwork']
    cases['confirmed_mood_preserves_watch_original_sample_and_cover_deadline'] = 'PASS'
    examples.append({'case':'watch_confirmed_mood', 'passive_session':watch_changed})
    b.update_playback(replace(b.state.playback, state='paused'))
    paused_without_sample = (await request('/read', read))['passive_session']
    assert paused_without_sample['playback_state'] == 'paused'
    assert 'progress' not in paused_without_sample['now_playing']
    cases['pause_without_new_sample_stops_old_progress'] = 'PASS'
    for state, position in [('paused', 2000), ('playing', 1000)]:
        await manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=sid,
            state=state, media_identity='spotify:track:'+'A'*22, title=original[2].title,
            artist=original[2].artist, album=original[2].album,
            duration_ms=original[2].duration_ms, position_ms=position)
        current = (await request('/read', read))['passive_session']
        assert current['now_playing']['progress']['position_ms'] == position
        assert current['now_playing']['progress']['playback_state'] == state
        cases['new_accepted_'+state+'_sample_exact_not_extrapolated'] = 'PASS'
    await manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=sid,
        state='playing', media_identity='spotify:track:'+'D'*22, title='New exact recording',
        artist='Synthetic artist', album='Synthetic album', duration_ms=120000, position_ms=0)
    switched = (await request('/read', read))['passive_session']
    assert switched['now_playing']['subject_uri'] == 'spotify:track:'+'D'*22
    assert switched['now_playing']['progress']['position_ms'] == 0
    assert not any(a['slot']=='now_playing' for a in switched['artwork'])
    cases['track_switch_new_original_sample_never_relabels_old_cover'] = 'PASS'
    observed = b.passive_observation
    with patch('time.monotonic', return_value=observed[0]+121), patch('time.time', return_value=observed[1]+121):
        expired = (await request('/read', read))['passive_session']
    assert expired['state'] == 'stale' and expired['now_playing'] is None and expired['artwork'] == []
    assert b.passive_observation is observed
    cases['dual_clock_expiry_no_read_or_cache_renewal'] = 'PASS'
    await request('/authorize', {**watch_consent, 'enabled':False}, auth=watch_headers)
    await request('/read', watch_read, 403, watch_headers)
    await request('/authorize', {**live_consent, 'locked_display':True, 'enabled':False})
    await request('/authorize', {**consent, 'enabled':False})
    await request('/read', read, 403)
    cases['revoked_grant_cannot_keep_rich_content'] = 'PASS'
    root = Path(__file__).resolve().parents[2]
    assert source_hashes == {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root/'custom_components/djconnect').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    result = {'qualification':'ACTUAL_ISOLATED_HA_MAC_PASSIVE_V3_SYNTHETIC_PROVIDER_ONLY',
        'capability':capability(), 'cases':cases, 'examples':examples, 'cover_bytes_sha256':image_digest,
        'source_pins':source_hashes, 'harness_pins':{n:hashlib.sha256((root/n).read_bytes()).hexdigest()
            for n in ['scripts/verification/verify_session_artwork_http.py',
                      'scripts/verification/passive_progress_lab.py',
                      'scripts/verification/verify_passive_progress_http.py']},
        'source_unchanged':True, 'real_provider_calls':0, 'model_provider_calls':0,
        'native_widget_shared_cache_physical_acceptance':'NOT_RUN'}
    (output/'passive-progress-qualification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('PASSIVE_PROGRESS_V3_PASS',len(cases),flush=True)
