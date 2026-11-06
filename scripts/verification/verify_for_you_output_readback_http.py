"""Paired HA For-you output readback, with only the external Spotify wire synthetic."""
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/verification')]
from verify_session_for_you_http import qualify as base_qualify  # noqa: E402


async def qualify(hass, manager, history, request, client):
    examples = []

    async def after(hass, manager, history, request, state):
        from custom_components.djconnect import spotify_backend
        wire = spotify_backend.async_get_clientsession(hass)
        original_request = wire.request
        cases = {}
        mode = ''

        def provider(method, url, **kwargs):
            response = original_request(method, url, **kwargs)
            path = urlsplit(url).path.removeprefix('/v1')
            transferred = any(e['kind'] == 'output' for e in state['effects'])
            if method == 'GET' and transferred:
                if path == '/me/player/devices':
                    response.value['devices'][0]['is_active'] = False
                elif path == '/me/player' and mode == 'unconfirmed':
                    response.value['device']['id'] = 'synthetic-other-output'
            return response

        async def choose(context, results, item, identifier, locale):
            return await request('POST', '/api/djconnect/v1/ask_dj/message', {
                'client_message_id': identifier, 'text': item['title'], 'language': locale,
                'audio_response': 'never', 'conversation_context': context,
                'choice_action': {'operation': 'select', 'result_set_id': results['result_set_id'],
                                  'action_id': item['action_id']}})

        with patch.object(wire, 'request', provider):
            for locale in ('en', 'nl'):
                for current_mode in ('confirmed', 'unconfirmed'):
                    mode = current_mode
                    old = manager.current_active('profile-a')
                    if old:
                        await manager.async_end(owner_profile_id='profile-a', session_id=old.session_id)
                    state.update(active=True, playing=False, track=None, effects=[], reads=[], tracks={})
                    started, status = await request('POST', '/api/djconnect/v1/session/start',
                                                    {'mood': 'chill', 'language': locale})
                    assert status == 201, started
                    offer = started['for_you']
                    state['active'] = False
                    # A paused old track is expected after an output-only transfer;
                    # it does not establish that the selected mix has started.
                    state['track'] = {'uri': 'spotify:track:' + 'Z' * 22,
                        'name': 'Synthetic previous paused track', 'artists': [{'name': 'Synthetic artist'}],
                        'duration_ms': 180000, 'album': {'name': 'Synthetic album', 'images': []}}
                    item = offer['result_set']['items'][0]
                    prefix = locale + '-' + mode
                    speakers, status = await choose(offer['conversation_context'], offer['result_set'],
                                                     item, prefix + '-genre', locale)
                    assert status == 200 and speakers['first_play']['state'] == 'output', speakers
                    assert not state['effects']
                    output = speakers['result_set']['items'][0]
                    context = offer['conversation_context']
                    result, status = await choose(context, speakers['result_set'], output,
                                                  prefix + '-output', locale)
                    if mode == 'confirmed':
                        assert status == 200 and result['action_outcome']['readback_confirmed'], result
                        assert state['effects'] == [{'kind': 'output', 'play': False},
                            {'kind': 'play', 'uris': item['uris'], 'output': 'synthetic-first-play-output'}]
                        repeated, duplicate_status = await choose(context, speakers['result_set'], output,
                                                                  prefix + '-output', locale)
                        assert duplicate_status == 200
                        assert repeated['assistant_message']['id'] == result['assistant_message']['id']
                        assert len(state['effects']) == 2
                        cases[locale + '_confirmed_original_output_beats_lagging_inventory_same_mix_once'] = 'PASS'
                        assert result['for_you']['state'] == 'confirmed'
                        cases[locale + '_old_paused_track_is_not_mix_confirmation'] = 'PASS'
                    else:
                        assert status == 409 and result.get('error') == 'first_play_output_changed', result
                        assert state['effects'] == [{'kind': 'output', 'play': False}]
                        repeated, duplicate_status = await choose(context, speakers['result_set'], output,
                                                                  prefix + '-output', locale)
                        assert duplicate_status == 409 and len(state['effects']) == 1
                        cases[locale + '_unconfirmed_output_no_mix_no_transfer_retry'] = 'PASS'
                    examples.append({'language': locale, 'case': mode, 'status': status, 'body': result,
                                     'synthetic_effects': list(state['effects'])})
        return cases

    result = await base_qualify(hass, manager, history, request, client, after=after)
    result.update(output_readback_examples=examples,
                  qualification='ACTUAL_ISOLATED_HA_FOR_YOU_OUTPUT_READBACK_SYNTHETIC_PROVIDER_ONLY',
                  harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return result


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
