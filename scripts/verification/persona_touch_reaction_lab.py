"""Real paired HA TLS/HTTP/Store/SQLite chain; external waveform is a fixture."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time


async def run(hass, runtime, client, post, identity, output, headers, manager, storage, base, processor):
    from scripts.verification.verify_hybrid_transport_http import new_id
    from custom_components.djconnect.hybrid_service import operations
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    from custom_components.djconnect.playback_observation import playback_observation_manager

    root = Path(__file__).resolve().parents[2]
    source = [*sorted((root/'custom_components/djconnect').rglob('*.py')),
              Path(__file__), Path(__file__).with_name('verify_hybrid_transport_http.py'),
              Path(__file__).with_name('verify_session_speech_http.py')]
    pins = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
    manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
    _, syntheses = processor
    rows = []
    sid = None
    try:
        async with client.get(base+'/api/djconnect/v1/profile/settings', params={**identity, 'contract_version': '3'}, headers=headers) as response:
            before = await response.json()
            assert response.status == 200, before
        selected = {'persona': 'festival_dj', 'mood': 'party', 'presence': 'music_only',
                    'voice': {'kind': 'provider_default'}, 'gender': 'default',
                    'announcement_output': 'client_device'}
        async with client.patch(base+'/api/djconnect/v1/profile/settings', headers=headers, json={
                **identity, 'contract_version': 3, 'binding': before['binding'],
                'operation_id': new_id(), 'expected_defaults_revision': before['snapshot']['defaults_revision'],
                'expected_session': None, 'patch': selected}) as response:
            accepted = await response.json()
            assert response.status == 200, accepted
        assert accepted['snapshot']['defaults'] == selected
        started = await post('session/start', {**identity, 'locale': 'en'}, 201)
        sid = started['session']['session_id']
        await playback_observation_manager(hass).async_stop('profile-a', sid)
        async with client.get(base+'/api/djconnect/v1/profile/settings', params={**identity, 'contract_version': '3'}, headers=headers) as response:
            snapshot = (await response.json())['snapshot']
            assert response.status == 200
        context = {k: snapshot['session'][k] for k in ('session_id', 'generation', 'revision')}
        async def operation(name, payload, expected=200, original=None):
            request = original or {'identity': identity, 'contract_version': 1,
                'operation_id': new_id(), 'operation_epoch': operations(hass).journal.epoch,
                'operation': name, 'payload': payload}
            body = await post('transport/operation', request, expected)
            rows.append({'request': request, 'status': expected, 'body': body})
            return body, request
        def reaction(processor):
            return {'contract_version': 1, 'session': context, 'kind': 'playful',
                    'language': 'en', 'processor': processor}
        initial_flow = manager.current_active('profile-a').planner.output.session_flow.flow_revision
        native, request = await operation('session/persona/reaction', reaction('local_on_device'))
        value = native['persona_reaction']
        assert value['speech']['audio_state'] == 'renderer_pending'
        assert (value['persona'], value['mood']) == ('festival_dj', 'party')
        duplicate, _ = await operation('session/persona/reaction', {}, original=request)
        assert not duplicate['result_available'] and 'persona_reaction' not in duplicate
        await operation('session/persona/reaction', reaction('local_on_device'), 409)
        def cancellation(identifier):
            return {'contract_version': 1, 'session_id': sid, 'reaction_id': identifier, 'reason': 'completed'}
        await operation('session/persona/reaction/cancel', cancellation(value['reaction_id']))
        await operation('session/persona/reaction', reaction('ha_configured'), 429)
        # The local rate clock is deliberately advanced: no ten-second listening
        # claim. Real HTTP/SQLite/provider and original lease guards remain real.
        book = hass.data['djconnect']['persona_reaction_book']
        observed = book.now()
        book.now = lambda: observed + 11
        prepared, _ = await operation('session/persona/reaction', reaction('ha_configured'))
        speech = prepared['persona_reaction']['speech']
        assert speech['audio_state'] == 'ready', prepared
        assert syntheses == [prepared['persona_reaction']['text']]
        asset = speech['audio_reference']['asset_id']
        async with client.post(base+'/api/djconnect/v1/speech/audio', headers=headers,
                json={**identity, 'contract_version': 1, 'asset_id': asset}) as response:
            audio = await response.read()
            assert response.status == 200 and audio.startswith(b'RIFF')
            assert response.headers['Cache-Control'] == 'no-store'
        await operation('session/persona/reaction/cancel', cancellation(prepared['persona_reaction']['reaction_id']))
        async with client.post(base+'/api/djconnect/v1/speech/audio', headers=headers,
                json={**identity, 'contract_version': 1, 'asset_id': asset}) as response:
            assert response.status == 404
        current = manager.current_active('profile-a')
        assert current.presence_ledger.total_published == 0
        assert current.planner.output.session_flow.flow_revision == initial_flow
        assert all(hashlib.sha256((root/p).read_bytes()).hexdigest() == pin for p, pin in pins.items())
        result = {'qualification': 'PASS_ISOLATED_REAL_HA_PAIRED_TLS_HTTP_STORE_SQLITE',
            'pairing': 'ordinary_device_token_minted_persisted', 'source_hashes': pins,
            'transport_receipts': rows, 'synthesis_count': len(syntheses),
            'audio': {'bytes': len(audio), 'sha256': hashlib.sha256(audio).hexdigest(),
                      'cancelled_read_status': 404},
            'proactive_publications': 0, 'flow_revision_unchanged': True,
            'provider_boundary': 'Real HA Wyoming entity/TCP; external waveform fixture, not voice or sound acceptance',
            'rate_time': 'modelled eleven-second advance', 'model_calls': 0,
            'native': 'NOT_RUN', 'audible': 'NOT_RUN', 'installed': 'NOT_RUN',
            'elapsed_wall_seconds': round(time.monotonic()-observed, 3)}
        (output/'persona-touch-http.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({'qualification': result['qualification'], 'operations': len(rows), 'syntheses': len(syntheses)}))
    finally:
        if sid and manager.current_active('profile-a'):
            await post('session/end', {**identity, 'session_id': sid})
