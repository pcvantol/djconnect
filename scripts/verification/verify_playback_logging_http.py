"""Real owner HTTP regression for diagnostic-only playback logging.

Only Spotify network I/O is fixture. No real account, playback or pairing reset.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', '/candidate'))
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/verification')]
from verify_session_conversation_history_http import entry  # noqa: E402
from aiohttp import ClientSession  # noqa: E402
from aiohttp.test_utils import TestClient, TestServer  # noqa: E402
from homeassistant import auth  # noqa: E402
from homeassistant.components.http import HomeAssistantHTTP  # noqa: E402
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState  # noqa: E402
from homeassistant.core import HomeAssistant, CoreState  # noqa: E402
from homeassistant.helpers import area_registry, device_registry, entity_registry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views, api_handlers  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.ask_dj_history import AskDJHistoryManager  # noqa: E402
from custom_components.djconnect.spotify_backend import SpotifyBackend  # noqa: E402


async def main():
    output = Path(os.environ.get('DJC_LAB_ROOT', '/lab'))
    output.mkdir(parents=True, exist_ok=True)
    config = output / 'config'
    config.mkdir()
    hass = HomeAssistant(str(config))
    hass.state = CoreState.running
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{'type': 'homeassistant'}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ['127.0.0.1'], 0, [], 'modern')
    await hass.http.async_initialize(cors_origins=[], use_x_forwarded_for=False,
        login_threshold=-1, is_ban_enabled=False, use_x_frame_options=True)
    from homeassistant.components import network
    from homeassistant import loader
    from homeassistant.helpers import frame
    hass.config.components.add('http')
    await network.async_setup(hass, {})
    frame.async_setup(hass)
    loader.async_setup(hass)
    identity = {'device_id': 'djconnect-ios-ABCDEF123456', 'client_type': 'ios'}
    client_entry = entry('client-entry', {**identity, 'pair_code': '123456',
        'profile_id': 'profile-a', 'music_backend': 'spotify_direct',
        'music_account_id': 'source-account', 'profile_backend_entry_id': 'source-entry'})
    source_entry = entry('source-entry', {'profile_id': 'profile-a',
        'music_backend': 'spotify_direct', 'music_account_id': 'source-account',
        'spotify_client_id': 'synthetic-client', 'spotify_refresh_token': 'synthetic-not-sent'})
    await ConfigEntryStore(hass).async_save({'entries': [e.as_storage_fragment for e in (client_entry, source_entry)]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    client_entry, source_entry = [hass.config_entries.async_get_entry(e.entry_id) for e in (client_entry, source_entry)]
    for slot in (client_entry, source_entry):
        slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    caller, source = DJConnectRuntime(client_entry), DJConnectRuntime(source_entry)
    caller.device_status.update(identity)
    storage = ProfilePlatformStorage(hass)
    caller.ask_dj_history = AskDJHistoryManager(hass)
    hass.data['djconnect'] = {'client-entry': caller, 'source-entry': source, 'runtime': caller,
        'djconnect_profile_platform': storage, 'ask_dj_history_manager': caller.ask_dj_history}
    await storage.async_upsert_music_backend('spotify_direct', BackendProvider.SPOTIFY_DIRECT, display_name='Fixture')
    profile = await storage.async_create_profile('Synthetic owner', profile_id='profile-a', default_backend_id='spotify_direct')
    await storage.async_upsert_music_account('source-account', 'spotify_direct',
        kind=MusicAccountKind.PERSONAL, linked_profile_ids=frozenset({'profile-a'}), display_name='Fixture')
    await storage.async_update_profile('profile-a', preferences=replace(profile.preferences,
        default_music_account_id='source-account'))
    await storage.async_upsert_device(identity['device_id'], 'ios', linked_profile_id='profile-a')
    register_http_views(hass)
    provider_calls = []
    provider_session = ClientSession()

    async def external_provider(_self, method, path, **kwargs):
        assert method == 'GET', (method, path)
        provider_calls.append({'method': method, 'path': path})
        if path == '/me/player':
            return {'item': {'id': 'A'*22, 'uri': 'spotify:track:'+'A'*22, 'name': 'Synthetic track',
                'artists': [{'id': 'B'*22, 'name': 'Synthetic artist'}],
                'album': {'id': 'C'*22, 'name': 'Synthetic album', 'images': []}, 'duration_ms': 300000},
                'is_playing': True, 'progress_ms': 1000,
                'device': {'id': 'fixture-player', 'name': 'Fixture player', 'is_active': True, 'volume_percent': 40},
                'repeat_state': 'off', 'shuffle_state': False}
        if 'contains?' in path:
            return [False]
        if path == '/me/player/queue':
            return {'currently_playing': None, 'queue': []}
        if path == '/me/player/devices':
            return {'devices': []}
        if 'artists' in path:
            return {'artists': []}
        return {'items': [], 'next': None, 'total': 0}

    cases = []
    original_level = api_handlers._LOGGER.level
    baseline = os.environ.get('DJC_EXPECT_LOGGING_BUG') == '1'
    try:
        with (patch.object(SpotifyBackend, '_request', external_provider),
              patch('custom_components.djconnect.spotify_backend.async_get_clientsession', return_value=provider_session)):
            async with TestClient(TestServer(hass.http.app)) as client:
                paired = await client.post('/api/djconnect/v1/pair', json={**identity, 'pair_code': '123456'})
                pair_body = await paired.json()
                assert paired.status == 200, pair_body
                token = pair_body['device_token']
                assert client_entry.data['device_token'] == token
                headers = {'Authorization': 'Bearer '+token}
                for level in (logging.INFO, logging.DEBUG):
                    api_handlers._LOGGER.setLevel(level)
                    for command in ('status', 'queue', 'playlists'):
                        response = await client.post('/api/djconnect/v1/command', headers=headers,
                            json={**identity, 'command': command})
                        text = await response.text()
                        body = json.loads(text) if response.content_type == 'application/json' else {'non_json_server_error': True}
                        expected = 500 if baseline and level == logging.DEBUG else 200
                        assert response.status == expected, (level, command, response.status, body)
                        cases.append({'level': logging.getLevelName(level), 'command': command,
                            'status': response.status, 'success': body.get('success'), 'error': body.get('error')})
                api_handlers._LOGGER.setLevel(logging.DEBUG)
                before = len(provider_calls)
                denied = await client.post('/api/djconnect/v1/command', json={**identity, 'command': 'status'})
                assert denied.status == 401 and len(provider_calls) == before
                if not baseline:
                    # A real missing provider stays a structured dispatch error;
                    # diagnostics neither hide it nor convert it into500.
                    hass.data['djconnect'].pop('source-entry')
                    errors = []
                    for level in (logging.INFO, logging.DEBUG):
                        api_handlers._LOGGER.setLevel(level)
                        response = await client.post('/api/djconnect/v1/command', headers=headers,
                            json={**identity, 'command': 'status'})
                        body = await response.json()
                        assert response.status in (400, 403, 409, 503), (response.status, body)
                        errors.append({'status': response.status, 'error': body.get('error')})
                    assert errors[0] == errors[1], errors
                    assert len(provider_calls) == before
                    cases.append({'missing_provider_debug_equivalence': errors})
                assert storage.household.devices[identity['device_id']].linked_profile_id == 'profile-a'
                assert client_entry.data['profile_backend_entry_id'] == 'source-entry'
                assert 'spotify_refresh_token' not in client_entry.data
        receipt = {'scope': 'Real isolated HA normal pairing/Profile binding/command dispatch; only Spotify network I/O fixture',
            'baseline_bug_expected': baseline, 'cases': cases, 'unauthorized_status': denied.status,
            'pairing_and_profile_preserved': True, 'provider_calls': provider_calls,
            'source_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT/'custom_components/djconnect').rglob('*.py') if '__pycache__' not in p.parts}}
        (output/'playback-logging-http.json').write_text(json.dumps(receipt, indent=2)+'\n')
        print('PLAYBACK_LOGGING_BASELINE_REPRODUCED' if baseline else 'PLAYBACK_LOGGING_HTTP_PASS', flush=True)
    finally:
        api_handlers._LOGGER.setLevel(original_level)
        await provider_session.close()
        await hass.async_stop()
