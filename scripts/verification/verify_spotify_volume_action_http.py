"""Actual paired isolated HA/HTTP/SQLite; only Spotify responses/token are fixtures."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/verification')]


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import DJConnectRuntime, spotify_backend
    from custom_components.djconnect.profile_context import profile_storage
    storage = profile_storage(hass)
    profile = storage.household.profiles['profile-a']
    await storage.async_update_profile('profile-a', preferences=replace(profile.preferences,
        default_backend_id='source-spotify', default_music_account_id='source-account'))
    entry = hass.config_entries.async_get_entry('source-entry')
    hass.config_entries.async_update_entry(entry, data={**entry.data, 'profile_id': 'profile-a',
        'music_backend': 'source-spotify', 'spotify_client_id': 'synthetic-volume-provider'})
    source = DJConnectRuntime(entry, device_token='')
    hass.data['djconnect']['source-entry'] = source
    owner_entry = hass.config_entries.async_get_entry('owner-entry')
    hass.config_entries.async_update_entry(owner_entry, data={**owner_entry.data,
        'profile_backend_entry_id': 'source-entry', 'music_backend': 'source-spotify',
        'music_account_id': 'source-account'})
    owner = hass.data['djconnect']['owner-entry']
    state = {'mode': 'refused', 'supports_volume': False, 'volume': 30}
    calls = []
    cases = {}

    class Response:
        headers = {}
        def __init__(self, body, status=200):
            self.body, self.status = body, status
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def json(self, **kwargs): return self.body
        async def text(self): return json.dumps(self.body)

    def device():
        return {'id': 'synthetic-volume-output', 'name': 'Synthetic iPhone', 'type': 'Smartphone',
                'is_active': True, 'is_restricted': False, 'supports_volume': state['supports_volume'],
                'volume_percent': state['volume']}

    class Wire:
        def request(self, method, url, **kwargs):
            parsed = urlsplit(url)
            assert parsed.hostname == 'api.spotify.com'
            path = parsed.path.removeprefix('/v1')
            calls.append((method, path))
            if method == 'GET':
                if path == '/me/player':
                    return Response({'is_playing': True, 'device': device(), 'item': None})
                if path == '/me/player/devices':
                    return Response({'devices': [device()]})
                raise AssertionError(('unexpected provider read', path))
            assert method == 'PUT' and path == '/me/player/volume', (method, path)
            if state['mode'] == 'timeout':
                raise TimeoutError('synthetic_private_error_never_public')
            if state['mode'] != 'success':
                message = 'Player command failed: Cannot control device volume' if state['mode'] == 'refused' else 'synthetic_private_error_never_public'
                return Response({'error': {'message': message}}, 503 if state['mode'] == 'server' else 403)
            state['volume'] = int(parse_qs(parsed.query)['volume_percent'][0])
            return Response({}, 204)

    async def token(self, **kwargs): return 'synthetic-not-live'

    def session_pin():
        active = manager.current_active('profile-a')
        return hashlib.sha256(json.dumps(asdict(active) if active else None, sort_keys=True, default=str).encode()).hexdigest()

    with patch.object(spotify_backend, 'async_get_clientsession', lambda h: Wire()), \
            patch.object(spotify_backend.SpotifyBackend, '_access_token', token):
        for supported in (False, True, None):
            state['supports_volume'] = supported
            status, code = await request('POST', '/api/djconnect/v1/command', {'command': 'status'})
            assert code == 200 and status['success'], status
            assert status['playback']['device']['supports_volume'] is supported, status
            outputs, code = await request('POST', '/api/djconnect/v1/command', {'command': 'devices'})
            assert code == 200 and outputs['success'], outputs
            assert outputs['devices'][0].get('supports_volume') is supported, outputs
        cases['provider_boolean_and_unknown_preserved_in_actual_status_and_outputs'] = 'PASS'
        original_session = session_pin()
        for language in ('en', 'nl'):
            for command in ('set_volume', 'volume_delta'):
                for mode in ('refused', 'server', 'timeout', 'scope'):
                    state.update(mode=mode, supports_volume=False)
                    owner.last_dj_text = 'synthetic-retained-dj'
                    before = {r.entry.entry_id if hasattr(r, 'entry') else str(i):
                              (r.device_status.get('backend_available'), r.last_error)
                              for i, r in enumerate((owner, source))}
                    calls.clear()
                    body, code = await request('POST', '/api/djconnect/v1/command',
                        {'command': command, 'value': 20 if command == 'set_volume' else -5, 'language': language})
                    assert code == 200 and body['success'] is False, (code, body)
                    assert body['error'] == ('unsupported_backend_capability' if mode == 'refused' else 'volume_command_failed'), body
                    assert body['command'] == command and body['error_scope'] == 'command' and body['retry_automatically'] is False
                    if mode == 'refused':
                        assert body['capability'] == 'supports_volume' and body['backend_available'] is True, body
                    else:
                        assert 'backend_available' not in body, body
                    assert not any(k in body for k in ('text', 'dj_text', 'audio_url', 'playback')), body
                    assert 'synthetic_private' not in json.dumps(body), body
                    after = {r.entry.entry_id if hasattr(r, 'entry') else str(i):
                             (r.device_status.get('backend_available'), r.last_error)
                             for i, r in enumerate((owner, source))}
                    assert before == after, (before, after)
                    assert owner.last_dj_text == 'synthetic-retained-dj' and session_pin() == original_session
                    assert sum(m == 'PUT' for m, p in calls) == 1, calls
                    cases[language + '_' + command + '_' + mode + '_action_only_no_retry_or_global_state_write'] = 'PASS'
        state.update(mode='success', supports_volume=True)
        calls.clear()
        success, code = await request('POST', '/api/djconnect/v1/command', {'command': 'set_volume', 'value': 25})
        assert code == 200 and success['success'] and success['playback']['volume_percent'] == 25, success
        assert sum(m == 'PUT' for m, p in calls) == 1
        cases['supported_volume_success_is_unchanged'] = 'PASS'
    return {'qualification': 'ACTUAL_ISOLATED_HA_PAIRED_HTTP_SYNTHETIC_SPOTIFY_ONLY', 'cases': cases,
            'real_provider_calls': 0, 'model_provider_calls': 0, 'native_installed_acceptance': 'NOT_RUN',
            'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
