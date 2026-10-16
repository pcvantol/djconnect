"""Connected ordinary-paired HA passive-purpose proof; external sources only fixture."""
import asyncio
import hashlib
import json
import time
from pathlib import Path


async def run(*, hass, runtime, client, headers, identity, manager, storage, sid,
              calls, output, source_hashes, second_identity, selected):
    from custom_components.djconnect.playback_observation import playback_observation_manager
    from custom_components.djconnect.passive_session import BASE

    # Freeze only the existing lab's polling workload at its normal stop boundary.
    # All accepted state, grants, storage, query and transport remain real.
    observation = playback_observation_manager(hass)
    await observation.async_stop('profile-a', sid)
    rows = []
    base = {**identity, 'contract_version': 1, 'session_id': sid, 'surface': 'widget'}

    async def request(path, payload, expected=200, auth=headers):
        response = await client.post(BASE + path, json=payload, headers=auth)
        body = await response.json()
        assert response.status in (expected if isinstance(expected, tuple) else (expected,)), (path, response.status, body)
        assert response.headers.get('Cache-Control') == 'no-store'
        return body

    consent = {**base, 'enabled': True, 'os_snapshot_cache': True, 'locked_display': False}
    await request('/authorize', {**consent, 'os_snapshot_cache': False}, 403)
    await request('/authorize', {**consent, 'surface': 'live_activity'}, 403)
    await request('/authorize', {**consent, 'surface': 'watch'}, 400)
    await request('/authorize', consent, 401, {})
    authorized = await request('/authorize', consent)
    grant = authorized['grant_id']
    read = {**base, 'grant_id': grant}
    first = await request('/read', read)
    frame = first['passive_session']
    assert frame['state'] == 'active' and frame['contribution'], frame
    assert frame['now_playing'] and frame['artwork'], frame
    current = manager._active_by_profile['profile-a']
    original = next(m for m in current.broadcast.state.dj_moments
                    if m.moment_id == frame['contribution']['moment_id'])
    assert original.content == frame['contribution']['text']
    assert dict(original.source_attribution) == frame['contribution']['source_attribution']
    assert frame['now_playing']['subject_uri'] == 'spotify:track:' + 'A'*22
    forbidden = ('device_token', 'profile_id', 'history', 'performance_memory', 'planner', 'horizon')
    assert all(name not in json.dumps(frame).lower() for name in forbidden)
    art = frame['artwork'][0]
    assert art['subject']['type'] in {'track', 'album'}
    image_query = {**identity, 'contract_version': '1', 'surface': 'widget', 'grant_id': grant}
    response = await client.get(art['image_path'], params=image_query, headers=headers)
    body = await response.read()
    assert response.status == 200 and response.headers['Cache-Control'] == 'no-store'
    assert body.startswith(b'\x89PNG')
    image_sha = hashlib.sha256(body).hexdigest()
    rows.append({'case': 'positive_actual_publication_metadata_cover', 'response': first,
                 'image_bytes_sha256': image_sha, 'image_http': 200})
    before = (len(calls), len(current.broadcast.state.dj_moments), current.presence_ledger.total_published,
              len(current.broadcast.replay_log), len(hass.data['djconnect']['session_images'].assets))
    repeated = [await request('/read', read) for _ in range(20)]
    after = (len(calls), len(current.broadcast.state.dj_moments), current.presence_ledger.total_published,
             len(current.broadcast.replay_log), len(hass.data['djconnect']['session_images'].assets))
    assert before == after, (before, after)
    assert all(x['passive_session']['revision'] == frame['revision'] for x in repeated)
    assert all(x['passive_session']['contribution']['published_at'] == original.created_at for x in repeated)
    rows.append({'case': 'twenty_pure_reads', 'before': before, 'after': after,
                 'same_revision_and_original_deadlines': True})
    await request('/read', {**read, 'grant_id': 'unknown'}, 403)
    await request('/read', {**read, 'surface': 'live_activity'}, 403)
    await request('/read', {**read, 'profile_id': 'forged'}, 400)
    # Another normally paired device may share owner Session, never this grant.
    hass.data['djconnect']['runtime'] = hass.data['djconnect']['second-owner']
    try:
        pair = await client.post('/api/djconnect/v1/pair', json={**second_identity, 'pair_code': '234567'})
    finally:
        hass.data['djconnect']['runtime'] = runtime
    second = await pair.json()
    assert pair.status == 200 and second['success'], (pair.status, second.get('error'))
    await request('/read', {**read, **second_identity}, 403,
        {'Authorization': 'Bearer '+second['device_token'], 'X-DJConnect-Device-ID': second_identity['device_id']})
    # Pairing a pre-bound second device need not mutate Profile bindings.
    # Its own token cannot use the first device's grant; the first remains valid.
    await request('/read', read)
    authorized = await request('/authorize', consent)
    read['grant_id'] = authorized['grant_id']
    old_generation = authorized['passive_session']['generation']
    await storage.async_upsert_device(identity['device_id'], 'ios', linked_profile_id='profile-other')
    await storage.async_upsert_device(identity['device_id'], 'ios', linked_profile_id='profile-a')
    await request('/read', read, 403)
    authorized = await request('/authorize', consent)
    assert authorized['passive_session']['generation'] != old_generation
    read['grant_id'] = authorized['grant_id']
    rows.append({'case': 'purpose_device_profile_ABA', 'denied_old_generation': True,
                 'new_generation_distinct': True})
    # Explicit existing media preparation is an owning lifecycle/action boundary,
    # separate from passive reads. New pixels do not republish the contribution.
    response = await client.get('/api/djconnect/v1/session/history/'+sid, params=identity, headers=headers)
    history = await response.json()
    playback_entry = next(e for e in history['entries'] if e['kind'] == 'playback_observed')
    prior_publications = len(current.broadcast.state.dj_moments)
    prepared = await client.post('/api/djconnect/v1/session/media/prepare', json={**identity,
        'contract_version': 1, 'session_id': sid, 'targets': [{'entry_id': playback_entry['entry_id']}]}, headers=headers)
    assert prepared.status == 200
    refreshed = await request('/read', read)
    assert refreshed['passive_session']['contribution'] == frame['contribution']
    assert len(current.broadcast.state.dj_moments) == prior_publications
    assert refreshed['passive_session']['artwork']
    assert refreshed['passive_session']['artwork'][0]['media_revision'] != art['media_revision']
    rows.append({'case': 'same_publication_new_media_revision', 'response': refreshed,
                 'semantic_publications_before': prior_publications,
                 'semantic_publications_after': len(current.broadcast.state.dj_moments)})
    # Confirmed setting goes through the actual private owner API.
    response = await client.post('/api/djconnect/v1/session/mood', json={**identity,
        'contract_version': 1, 'session_id': sid, 'selected_mood': 'energy',
        'expected_mood_revision': current.mood_revision}, headers=headers)
    mood = await response.json()
    assert response.status == 200, mood
    changed = await request('/read', read)
    assert changed['passive_session']['mood']['value'] == 'energy'
    assert changed['passive_session']['contribution'] == frame['contribution']
    rows.append({'case': 'mood_without_moment_rewrite', 'response': changed})
    # External provider fixture returns B; actual observation acceptance owns
    # the change. No ready passive payload or source identity is injected.
    from custom_components.djconnect.spotify_backend import SpotifyBackend
    selected[0] = 'D'
    observed_b = await SpotifyBackend(hass, runtime).async_observe_current_playback()
    await manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=sid,
        state='playing', media_identity=observed_b.media_identity, title=observed_b.title,
        artist=observed_b.artist, album=observed_b.album,
        album_uri=observed_b.catalog.get('album_uri', ''), duration_ms=observed_b.duration_ms,
        position_ms=observed_b.position_ms)
    different = await request('/read', read)
    assert different['passive_session']['contribution'] == frame['contribution']
    assert different['passive_session']['now_playing']['subject_uri'] == 'spotify:track:'+'D'*22
    assert different['passive_session']['artwork'] == []  # No A pixels relabelled as B.
    rows.append({'case': 'contribution_A_observed_B_independent', 'response': different})
    activity = await request('/authorize', {**consent, 'surface': 'live_activity', 'locked_display': True})
    assert activity['passive_session']['cache_policy']['locked_display'] is True
    rows.append({'case': 'explicit_locked_activity_consent', 'response': activity})
    # Music-only uses existing Core policy; no extra publication or catch-up.
    current = manager._active_by_profile['profile-a']
    response = await client.post('/api/djconnect/v1/session/presence', json={**identity,
        'contract_version': 1, 'session_id': sid, 'selected_presence': 'music_only',
        'expected_presence_revision': current.presence_revision}, headers=headers)
    assert response.status == 200, await response.text()
    quiet = await request('/read', read)
    assert quiet['passive_session']['contribution'] is None
    assert quiet['passive_session']['now_playing']
    rows.append({'case': 'music_only', 'response': quiet})
    # Real Runtime observation boundary; no synthetic session or ready projection.
    current = manager._active_by_profile['profile-a']
    p = current.broadcast.state.playback
    await manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=sid,
        state='paused', media_identity='spotify:track:'+'D'*22,
        title=p.title, artist=p.artist, album=p.album, duration_ms=p.duration_ms, position_ms=p.position_ms)
    paused = await request('/read', read)
    assert paused['passive_session']['state'] == 'active'
    assert paused['passive_session']['playback_state'] == 'paused'
    rows.append({'case': 'pause_not_end', 'response': paused})
    response = await client.get('/api/djconnect/v1/session/history/'+sid, params=identity, headers=headers)
    b_history = await response.json()
    b_entry = next(e for e in b_history['entries'] if e['kind'] == 'playback_observed'
                   and e['playback']['item_id'] == paused['passive_session']['now_playing']['item_id'])
    response = await client.post('/api/djconnect/v1/session/media/prepare', json={**identity,
        'contract_version': 1, 'session_id': sid, 'targets': [{'entry_id': b_entry['entry_id']}]}, headers=headers)
    assert response.status == 200
    before_withdrawal = await request('/read', read)
    b_art = before_withdrawal['passive_session']['artwork'][0]
    current_image_query = {**image_query, 'grant_id': read['grant_id']}
    b_pixels = await client.get(b_art['image_path'], params=current_image_query, headers=headers)
    assert b_pixels.status == 200
    await b_pixels.read()
    from custom_components.djconnect.domain.music_account import MusicAccountKind
    await storage.async_upsert_music_account('fixture-account', 'spotify_direct', kind=MusicAccountKind.PERSONAL,
        display_name='Fixture provider account', linked_profile_ids=frozenset(), provider_account_id='fixture-client')
    denied = await client.get(b_art['image_path'], params=current_image_query, headers=headers)
    assert denied.status in (401, 403, 404, 409)
    await request('/read', read, (401, 403, 404, 409))
    await storage.async_upsert_music_account('fixture-account', 'spotify_direct', kind=MusicAccountKind.PERSONAL,
        display_name='Fixture provider account', linked_profile_ids=frozenset({'profile-a'}), provider_account_id='fixture-client')
    await request('/read', read, 403)  # Restoration cannot revive an old generation.
    authorized = await request('/authorize', consent)
    read['grant_id'] = authorized['grant_id']
    rows.append({'case': 'source_withdrawal_and_restore_no_revival', 'old_image_http': denied.status,
                 'old_grant_http': 403})
    # Real wall/monotonic expiry, no patched Core clocks. Observe longer than the
    # 120-second original passive window; provider polling remains stopped.
    expiry_before = len(calls)
    until = current.broadcast.passive_observation[0] + 121
    await asyncio.sleep(max(0, until - time.monotonic()))
    expired = await request('/read', read)
    assert expired['passive_session']['contribution'] is None
    assert expired['passive_session']['now_playing'] is None
    assert expired['passive_session']['artwork'] == []
    assert len(calls) == expiry_before
    rows.append({'case': 'real_121_second_expiry', 'response': expired,
                 'provider_delta': len(calls)-expiry_before})
    async def race_read():
        response = await client.post(BASE+'/read', json=read, headers=headers)
        value = await response.json()
        assert response.status in (200, 403, 404)
        if response.status == 200:
            assert value['passive_session']['session_id'] == sid
        return response.status
    end_task = client.post('/api/djconnect/v1/session/end', json={**identity, 'session_id': sid}, headers=headers)
    raced = await asyncio.gather(*[race_read() for _ in range(20)], end_task)
    response = raced[-1]
    assert response.status == 200
    await request('/read', read, 404)
    rows.append({'case': 'twenty_reads_end_race_no_runtime_revival', 'read_http_after_end': 404,
                 'race_statuses': raced[:-1]})
    assert source_hashes == {str(p.relative_to(Path('/candidate'))): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path('/candidate/custom_components/djconnect').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (output/'passive-session.http.json').write_text(json.dumps({'contract_version': 1,
        'ordinary_pairing': True, 'core_authority_not_mocked': True, 'source_hashes': source_hashes,
        'rows': rows, 'external_fixture_calls': calls,
        'native_background_watch_installed_hardware': 'NOT_RUN'}, indent=2)+'\n')
    print(json.dumps({'passive_cases': len(rows), 'source_files': len(source_hashes),
                      'native_background_watch_hardware': 'OPEN'}), flush=True)
