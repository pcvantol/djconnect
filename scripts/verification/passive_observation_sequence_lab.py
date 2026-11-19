"""Existing real paired/source-qualified HA fixture; no installed/native claim."""
import asyncio
import hashlib
import json
import os
from pathlib import Path


async def run(**kw):
    from custom_components.djconnect.playback_observation import playback_observation_manager
    from custom_components.djconnect.passive_session import BASE

    root = Path(os.environ['DJC_SOURCE_ROOT'])
    def pins():
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((root / 'custom_components/djconnect').rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    before_source = pins()
    assert len(before_source) == 315
    hass, manager, sid = kw['hass'], kw['manager'], kw['sid']
    client, identity, headers = kw['client'], kw['second_identity'], kw['second_headers']
    await playback_observation_manager(hass).async_stop('profile-a', sid)
    broadcast = manager.current_active('profile-a').broadcast
    original = broadcast.passive_observation[2]
    base = {**identity, 'contract_version': 1, 'projection_version': 3,
            'session_id': sid, 'surface': 'widget'}
    async def request(path, body):
        response = await client.post(BASE + path, json=body, headers=headers)
        result = await response.json()
        assert response.status == 200 and result['success'], (response.status, result)
        return result
    examples, cases = {}, {}
    for state in ('idle', 'paused'):
        values = {'owner_profile_id': 'profile-a', 'session_id': sid, 'state': state,
                  'media_identity': '' if state == 'idle' else 'spotify:track:' + kw['selected'][0] * 22,
                  'title': '' if state == 'idle' else original.title,
                  'artist': '' if state == 'idle' else original.artist,
                  'album': '' if state == 'idle' else original.album,
                  'target_name': '' if state == 'idle' else original.target_name,
                  'position_ms': None if state == 'idle' else original.position_ms,
                  'duration_ms': None if state == 'idle' else original.duration_ms}
        await manager.async_update_playback_projection(**values)
        authorized = await request('/authorize', {**base, 'enabled': True,
                                  'os_snapshot_cache': True, 'locked_display': False})
        read = {**base, 'grant_id': authorized['grant_id']}
        first = await request('/read', read)
        await asyncio.sleep(.01)
        assert not await manager.async_update_playback_projection(**values)
        second = await request('/read', read)
        a, b = first['passive_session'], second['passive_session']
        assert first['grant_id'] == second['grant_id'] == authorized['grant_id']
        assert all(a[k] == b[k] for k in ('binding_id', 'generation', 'session_id'))
        assert b['delivery_sequence'] > a['delivery_sequence']
        assert b['observed_at'] != a['observed_at'] and b['revision'] != a['revision']
        assert a['playback_state'] == b['playback_state'] == state
        clock = broadcast.passive_state_observed
        repeated = await request('/read', read)
        assert all(repeated['passive_session'][k] == b[k] for k in (
            'delivery_sequence', 'observed_at', 'expires_at', 'revision'))
        assert broadcast.passive_state_observed == clock
        await request('/authorize', {**base, 'enabled': False,
                      'os_snapshot_cache': True, 'locked_display': False})
        sequence = broadcast.delivery_sequence
        assert not await manager.async_update_playback_projection(**values)
        assert broadcast.delivery_sequence == sequence
        examples[state] = {'before': first, 'after': second, 'read_only_repeat': repeated}
        cases[state + '_new_source_frame_same_grant'] = 'PASS'
    cases.update(read_no_renewal='PASS', disabled_no_extra_event='PASS')
    assert pins() == before_source
    output = Path(kw['output'])
    receipt = {'source_unchanged': True, 'source_pins': before_source, 'cases': cases,
               'examples': examples, 'normal_pair_source_admission': True,
               'synthetic_provider_and_cdn': True, 'real_provider_calls': 0,
               'installed_mutations': 0, 'native_audible_apns_acceptance': 'NOT_RUN',
               'original_live_response_reconstructed': False}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'result': 'PASS', 'cases': cases}), flush=True)
