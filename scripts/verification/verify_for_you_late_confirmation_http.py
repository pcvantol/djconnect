"""Actual paired HA late For-you readback using genuine original source samples."""
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from unittest.mock import patch

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/verification')]
from verify_session_for_you_http import qualify as base_qualify  # noqa: E402


async def qualify(hass, manager, history, request, client):
    examples = []

    async def after(hass, manager, history, request, state):
        from custom_components.djconnect import spotify_backend
        from custom_components.djconnect.playback_observation import playback_observation_manager
        from custom_components.djconnect import surface_status_samples as samples
        from custom_components.djconnect.surface_status_samples import capture_source, OriginalSample
        wire = spotify_backend.async_get_clientsession(hass)
        original_request = wire.request
        delayed = False
        original_seal = samples.seal
        actual_samples = []

        def observe_seal(*args, **kwargs):
            sample = original_seal(*args, **kwargs)
            if sample is not None:
                actual_samples.append(sample)
            return sample

        def provider(method, url, **kwargs):
            nonlocal delayed
            response = original_request(method, url, **kwargs)
            if method == 'GET' and urlsplit(url).path == '/v1/me/player' and delayed and state['effects']:
                delayed = False
                response.value['is_playing'] = False
            return response

        async def insight():
            return {}

        cases = {}
        with patch.object(wire, 'request', provider), patch.object(samples, 'seal', observe_seal):
            for locale in ('en', 'nl'):
                prior = manager.current_active('profile-a')
                if prior:
                    await manager.async_end(owner_profile_id='profile-a', session_id=prior.session_id)
                state.update(active=True, playing=False, track=None, effects=[], reads=[], tracks={})
                start, status = await request('POST', '/api/djconnect/v1/session/start',
                    {'mood': 'groove', 'language': locale})
                assert status == 201, start
                active = manager.current_active('profile-a')
                runtime = hass.data['djconnect']['owner-entry']
                observer = playback_observation_manager(hass)
                await observer.async_start_spotify(integration_runtime=runtime, session=active, insight_provider=insight)
                observed = observer._spotify_sessions.get('profile-a')
                assert observed is not None, ('ordinary fixture not observer-qualified', active.music_backend)
                source = capture_source(hass, observed)
                assert source is not None and source.current(), 'real source capture must qualify'
                offer = start['for_you']
                item = offer['result_set']['items'][0]
                delayed = True
                result, status = await request('POST', '/api/djconnect/v1/ask_dj/message', {
                    'client_message_id': 'late-original-'+locale, 'text': item['title'],
                    'language': locale, 'audio_response': 'never',
                    'conversation_context': offer['conversation_context'],
                    'choice_action': {'result_set_id': offer['result_set']['result_set_id'],
                        'action_id': item['action_id'], 'operation': 'select'}})
                assert status == 200 and result['success'], result
                assert result['first_play']['state'] == 'uncertain', result
                assert active.broadcast.first_play_state == 'attempted'
                assert len(state['effects']) == 1
                # The actual normal observer captures and seals the original
                # returned source/output; no fabricated source guard or DTO.
                await observer._async_poll_spotify(observed)
                assert active.broadcast.first_play_state == 'confirmed', 'late real sample did not close original mix'
                sample = actual_samples[-1]
                assert type(sample) is OriginalSample and sample.current() and sample.state == 'playing'
                assert sample.target_id == 'synthetic-first-play-output'
                current, status = await request('GET', '/api/djconnect/v1/session/active')
                assert status == 200 and current['for_you']['state'] == 'confirmed'
                assert not current['for_you']['visible'] and len(state['effects']) == 1
                await observer._async_poll_spotify(observed)
                assert len(state['effects']) == 1
                cases[locale+'_genuine_source_late_same_mix_same_output_once'] = 'PASS'
                examples.append({'language': locale, 'original_response': result,
                    'confirmed_projection': current['for_you'], 'synthetic_effects': list(state['effects']),
                    'actual_original_sample_type': type(sample).__name__})
                await observer.async_stop('profile-a', active.session_id)
        return cases

    result = await base_qualify(hass, manager, history, request, client, after=after, backend_id="spotify_direct")
    result.update(late_confirmation_examples=examples,
        qualification='ACTUAL_ISOLATED_HA_ORIGINAL_SOURCE_LATE_CONFIRMATION_SYNTHETIC_PROVIDER_ONLY',
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return result


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
