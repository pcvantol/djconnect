"""Actual isolated HA paired HTTP/WS withdrawal; external waveform is a fixture."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path


async def run(hass, runtime, client, post, identity, output, headers, manager, storage, base, processor):
    from scripts.verification.persona_touch_reaction_lab import run as baseline
    from scripts.verification.verify_hybrid_transport_http import new_id
    from custom_components.djconnect.hybrid_service import operations
    from custom_components.djconnect.playback_observation import playback_observation_manager
    from homeassistant.components.assist_pipeline.pipeline import KEY_ASSIST_PIPELINE

    await baseline(hass, runtime, client, post, identity, output, headers, manager, storage, base, processor)
    root = Path(__file__).resolve().parents[2]
    pins = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*sorted((root / 'custom_components/djconnect').rglob('*.py')),
                      Path(__file__), Path(__file__).with_name('verify_hybrid_transport_http.py')]}
    rows = []
    sid = None
    epoch = operations(hass).journal.epoch
    async def operation(name, payload, expected=200, request=None):
        request = request or {'identity': identity, 'contract_version': 1,
            'operation_id': new_id(), 'operation_epoch': epoch, 'operation': name, 'payload': payload}
        result = await post('transport/operation', request, expected)
        rows.append({'request': request, 'status': expected, 'result': result})
        return result, request
    try:
        session = await post('session/start', {**identity, 'locale': 'en'}, 201)
        sid = session['session']['session_id']
        await playback_observation_manager(hass).async_stop('profile-a', sid)
        async with client.get(base + '/api/djconnect/v1/profile/settings',
                params={**identity, 'contract_version': '3'}, headers=headers) as response:
            settings = (await response.json())['snapshot']['session']
        context = {k: settings[k] for k in ('session_id', 'generation', 'revision')}
        def reaction(processor='local_on_device'):
            return {'contract_version': 1, 'session': context, 'kind': 'check_in',
                    'language': 'en', 'processor': processor}
        for processor_kind in ('local_on_device', 'ha_configured'):
            original = {'identity': identity, 'contract_version': 1, 'operation_id': new_id(),
                        'operation_epoch': epoch, 'operation': 'session/persona/reaction',
                        'payload': reaction(processor_kind)}
            count = len(processor[1])
            await operation('session/persona/reaction/cancel', {'contract_version': 1,
                'session_id': sid, 'reaction_id': original['operation_id'], 'reason': 'dismissed'})
            denied, _ = await operation('session/persona/reaction', {}, 409, request=original)
            assert denied['operation_receipt']['phase'] == 'cancelled'
            assert 'persona_reaction' not in denied and len(processor[1]) == count

        first, original = await operation('session/persona/reaction', reaction())
        denied, _ = await operation('session/persona/reaction/cancel', {'contract_version': 1,
            'session_id': 'wrong-session', 'reaction_id': original['operation_id'], 'reason': 'dismissed'}, 404)
        assert denied['error'] == 'persona_reaction_unavailable'
        assert 'persona_reaction_cancelled' not in denied
        frames = []
        async with client.ws_connect(base + '/api/djconnect/v1/actions/paired') as ws:
            assert (await ws.receive_json())['type'] == 'auth_required'
            await ws.send_json({'type': 'auth', 'protocol_version': 1, 'audience': 'paired_owner_actions',
                **identity, 'device_token': headers['Authorization'].removeprefix('Bearer ')})
            assert (await ws.receive_json())['type'] == 'auth_ok'
            async def observe(identifier, rid):
                await ws.send_json({'type': 'djconnect/persona/reaction/observe', 'id': rid,
                    'contract_version': 1, 'operation_id': identifier, 'operation_epoch': epoch,
                    'session_id': sid})
                frame = await asyncio.wait_for(ws.receive_json(), 2)
                frames.append(frame)
                assert frame['type'] == 'result' and frame['id'] == rid, frame
                value = frame['result']['reaction_observation']
                assert value['state'] == 'valid' and value['reaction_id'] == identifier
                return value
            async def withdrawn(identifier):
                frame = await asyncio.wait_for(ws.receive_json(), 2)
                frames.append(frame)
                assert frame['type'] == 'event' and frame['event'] == 'session/persona/reaction/withdrawn', frame
                value = frame['reaction_observation']
                assert (value['reaction_id'], value['session_id'], value['state']) == (identifier, sid, 'withdrawn')
                assert 'text' not in value and 'segments' not in value
                return value

            value = await observe(original['operation_id'], 1)
            assert value['expires_at'] == first['persona_reaction']['expires_at']
            await operation('speech/preview', {'contract_version': 1, 'language': 'en'})
            await withdrawn(original['operation_id'])
            receipt = await post('transport/operation/status', {'identity': identity,
                **{k: original[k] for k in ('contract_version', 'operation_id', 'operation_epoch')}})
            assert receipt['operation_receipt']['phase'] == 'confirmed' and not receipt['result_available']

            # Only rate spacing is modelled; delivery and withdrawal use real TLS/WS.
            book = hass.data['djconnect']['persona_reaction_book']
            now = book.now()
            book.now = lambda: now + 11
            prepared, request = await operation('session/persona/reaction', reaction('ha_configured'))
            asset = prepared['persona_reaction']['speech']['audio_reference']['asset_id']
            audio_request = {**identity, 'contract_version': 1, 'asset_id': asset}
            async with client.post(base + '/api/djconnect/v1/speech/audio', headers=headers, json=audio_request) as response:
                assert response.status == 200 and (await response.read()).startswith(b'RIFF')
            await observe(request['operation_id'], 2)
            pipelines = hass.data[KEY_ASSIST_PIPELINE].pipeline_store
            update = asdict(pipelines.data['own-speech-pipeline'])
            update.pop('id')
            update['tts_voice'] = 'changed-after-delivery'
            await pipelines.async_update_item('own-speech-pipeline', update)
            await withdrawn(request['operation_id'])
            async with client.post(base + '/api/djconnect/v1/speech/audio', headers=headers, json=audio_request) as response:
                assert response.status == 404

            now += 11
            local, request = await operation('session/persona/reaction', reaction())
            await observe(request['operation_id'], 3)
            lease = next(s.lease for s in book.rows.values() if s.lease and s.lease.identifier == request['operation_id'])
        await asyncio.wait_for(lease.cancelled.wait(), 2)
        assert lease.observer is None
        assert all(hashlib.sha256((root / p).read_bytes()).hexdigest() == pin for p, pin in pins.items())
        result = {'qualification': 'PASS_ISOLATED_REAL_HA_PAIRED_HTTP_WS_WITHDRAWAL',
            'source_hashes': pins, 'operations': rows, 'frames': frames,
            'cancel_before_admission_processors': ['local_on_device', 'ha_configured'],
            'withdrawal': ['accepted_preview_after_delivery', 'actual_pipeline_change_after_download', 'observer_disconnect'],
            'rate_spacing': 'modelled eleven-second increments', 'provider': 'real HA Wyoming TCP entity; external fixture waveform',
            'model_calls': 0, 'installed': 'NOT_RUN', 'native': 'NOT_RUN', 'audible': 'NOT_RUN'}
        (output / 'persona-touch-withdrawal.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'qualification': result['qualification'], 'operations': len(rows), 'frames': len(frames)}))
    finally:
        if sid and manager.current_active('profile-a'):
            await post('session/end', {**identity, 'session_id': sid})
