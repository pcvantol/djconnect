"""Real paired HA routes and original publication clocks; no live provider/model."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from unittest.mock import patch


async def run(*, hass, client, manager, sid, calls, output, source_hashes,
              second_identity, second_headers, **unused):
    from custom_components.djconnect.passive_session import BASE, capability
    from custom_components.djconnect.playback_observation import playback_observation_manager
    await playback_observation_manager(hass).async_stop('profile-a', sid)
    active = manager.current_active('profile-a')
    b = active.broadcast
    observed = b.passive_observation
    headers, identity = second_headers, second_identity
    cases, examples = {}, []
    base = {**identity,'contract_version':1,'session_id':sid,'surface':'widget','projection_version':4}
    consent = {**base,'enabled':True,'os_snapshot_cache':True,'locked_display':False,'retained_latest':True}
    async def request(path, data, expected=200):
        response = await client.post(BASE+path,json=data,headers=headers)
        body = await response.json()
        assert response.status == expected, (path,response.status,body)
        assert response.headers['Cache-Control']=='no-store'
        return body
    await request('/authorize',{k:v for k,v in consent.items() if k!='retained_latest'},400)
    await request('/authorize',{**consent,'retained_latest':False},403)
    await request('/authorize',{**consent,'retained_latest':'true'},400)
    await request('/authorize',{**consent,'surface':'live_activity','locked_display':True},400)
    cases['explicit_own_widget4_retained_consent_not_activity_or_implicit_upgrade']='PASS'
    authorized = await request('/authorize',consent)
    read = {**base,'grant_id':authorized['grant_id']}
    first = authorized['passive_session']
    retained = first['latest_contribution']
    assert retained and retained['purpose']=='retained_latest'
    assert retained['text']==first['contribution']['text']
    boundary=b._moment_delivery_boundaries[retained['moment_id']]
    published_wall=datetime.fromisoformat(boundary.published_at).timestamp()
    assert datetime.fromisoformat(retained['retained_expires_at']).timestamp()<=published_wall+1800
    assert datetime.fromisoformat(retained['expires_at']).timestamp()<=datetime.fromisoformat(first['expires_at']).timestamp()
    cases['original_full_copy_publication_and_distinct_bounded_retained_lease']='PASS'
    examples.append({'case':'original_widget4','passive_session':first})
    old_consent={k:v for k,v in consent.items() if k!='retained_latest'}
    old_consent['projection_version']=3
    # Grants are entry+surface: authorize v3 once, prove it has no new field,
    # then obtain a new own v4 grant. Version mismatches cannot borrow it.
    old=await request('/authorize',old_consent)
    assert 'latest_contribution' not in old['passive_session']
    authorized=await request('/authorize',consent)
    read={**base,'grant_id':authorized['grant_id']}
    await request('/read',{**read,'projection_version':3},403)
    cases['v3_unchanged_and_exact_grant_version_fence']='PASS'
    live=await request('/authorize',{**old_consent,'surface':'live_activity','locked_display':True})
    live_read={**base,'projection_version':3,'surface':'live_activity','grant_id':live['grant_id']}
    now_cover=next(a for a in first['artwork'] if a['slot']=='now_playing')
    image=await client.get(now_cover['image_path'],params={**identity,'contract_version':'1',
        'surface':'widget','projection_version':'4','grant_id':authorized['grant_id']},headers=headers)
    pixels=await image.read()
    assert image.status==200 and pixels.startswith(b'\x89PNG')
    cases['current_cover_uses_only_own_version4_image_grant']='PASS'
    mono,wall=observed[:2]
    before=(len(calls),len(b.state.dj_moments),b.delivery_sequence,len(hass.data['djconnect']['session_images'].assets))
    with patch('time.monotonic',return_value=mono+40),patch('time.time',return_value=wall+40):
        later=(await request('/read',read))['passive_session']
        assert later['contribution'] is None and later['latest_contribution']
        assert later['latest_contribution']==retained
        assert later['now_playing']==first['now_playing']
        assert any(a['slot']=='now_playing' for a in later['artwork'])
        live_frame=(await request('/read',live_read))['passive_session']
        assert live_frame['contribution'] is None and live_frame['now_playing']
        assert 'latest_contribution' not in live_frame
        assert any(a['slot']=='now_playing' for a in live_frame['artwork'])
        for _ in range(10):
            again=(await request('/read',read))['passive_session']
            assert again['latest_contribution']==retained and again['revision']==later['revision']
    assert before==(len(calls),len(b.state.dj_moments),b.delivery_sequence,len(hass.data['djconnect']['session_images'].assets))
    assert b.passive_observation is observed
    cases['original_latest_survives_short_prominence_no_read_provider_or_publication_effect']='PASS'
    cases['activity_track_cover_mood_independent_of_short_dj_contribution']='PASS'
    examples.append({'case':'after_short_prominence','passive_session':later})
    with patch('time.monotonic',return_value=mono+121),patch('time.time',return_value=wall+121):
        stale=(await request('/read',read))['passive_session']
    assert stale['state']=='stale' and stale['latest_contribution'] is None and stale['now_playing'] is None
    cases['original_snapshot_expires_without_read_renewal']='PASS'
    # A genuine accepted observation refreshes its own snapshot, never publication.
    async def sample_at(delta):
        with patch('time.monotonic',return_value=mono+delta),patch('time.time',return_value=wall+delta):
            assert await manager.async_update_playback_projection(owner_profile_id='profile-a',session_id=sid,
                state='playing',media_identity=first['now_playing']['subject_uri'],
                title=observed[2].title,artist=observed[2].artist,album=observed[2].album,
                position_ms=1000+delta,duration_ms=observed[2].duration_ms)
            return (await request('/read',read))['passive_session']
    fresh=await sample_at(150)
    assert fresh['now_playing'] and fresh['latest_contribution']
    assert fresh['latest_contribution']['published_at']==retained['published_at']
    assert fresh['latest_contribution']['retained_expires_at']==retained['retained_expires_at']
    cases['genuine_new_observation_never_restarts_original_publication_lease']='PASS'
    examples.append({'case':'fresh_snapshot_same_original_publication','passive_session':fresh})
    expired=await sample_at(1801)
    assert expired['now_playing'] and expired['latest_contribution'] is None
    cases['retained_deadline_expires_independently_of_fresh_track_snapshot']='PASS'
    await request('/authorize',{**consent,'enabled':False})
    await request('/read',read,403)
    cases['own_grant_revocation_cannot_keep_retained_copy']='PASS'
    root=Path(__file__).resolve().parents[2]
    assert source_hashes=={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root/'custom_components/djconnect').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    result={'qualification':'ACTUAL_ISOLATED_HA_RETAINED_LATEST_SYNTHETIC_EXTERNAL_ONLY',
        'capability':capability(),'cases':cases,'examples':examples,'source_pins':source_hashes,
        'harness_pins':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in [
            'scripts/verification/verify_session_artwork_http.py',
            'scripts/verification/verify_passive_retained_http.py','scripts/verification/passive_retained_lab.py']},
        'source_unchanged':True,'real_provider_calls':0,'model_provider_calls':0,
        'native_installed_acceptance':'NOT_RUN'}
    (output/'passive-retained-qualification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('PASSIVE_RETAINED_PASS',len(cases),flush=True)
