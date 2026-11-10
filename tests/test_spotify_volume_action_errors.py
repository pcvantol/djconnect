"""Offline causal regressions; synthetic Spotify wires, no live volume/provider I/O."""
import asyncio
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_http_voice_helpers as http_tests


class SpotifyVolumeActionErrorTests(unittest.TestCase):
    owner_hass = http_tests.VoiceHttpHelperTest.owner_hass
    response_envelope = staticmethod(http_tests.VoiceHttpHelperTest.response_envelope)

    @classmethod
    def setUpClass(cls):
        http_tests.VoiceHttpHelperTest.setUpClass()
        cls.http = http_tests.VoiceHttpHelperTest.http
        cls.spotify = importlib.import_module('custom_components.djconnect.spotify_backend')
        cls.handlers = importlib.import_module('custom_components.djconnect.api_handlers')
        cls.use_cases = importlib.import_module('custom_components.djconnect.use_cases')

    def test_provider_volume_boolean_survives_output_and_playback_projection_without_heuristics(self):
        for name, kind in [('iPhone', 'Smartphone'), ('Kitchen', 'Speaker')]:
            for value in (False, True, None, 'false', 0):
                with self.subTest(name=name, value=value):
                    raw = {'id': 'synthetic-output', 'name': name, 'type': kind,
                           'is_restricted': False, 'supports_volume': value}
                    expected = value if type(value) is bool else None
                    self.assertIs(self.spotify._normalize_device(raw)['supports_volume'], expected)
                    self.assertIs(self.spotify._normalize_playback({'device': raw})['device']['supports_volume'], expected)
        self.assertIsNone(self.spotify._normalize_device({'is_restricted': False})['supports_volume'])

    def wire_backend(self, status, message):
        calls = []
        class Response:
            headers = {}
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            async def text(self): return json.dumps({'error': {'message': message}})
        Response.status = status
        class Wire:
            def request(self, method, url, **kwargs):
                calls.append((method, url))
                return Response()
        b = object.__new__(self.spotify.SpotifyBackend)
        b.hass, b.runtime, b.session = object(), SimpleNamespace(), Wire()
        b._retire_startup = None
        async def token(**kwargs): return 'synthetic-not-live'
        b._access_token = token
        return b, calls

    def test_specific_spotify_403_becomes_existing_volume_capability_error_at_response_seam(self):
        b, calls = self.wire_backend(403, 'Player command failed: Cannot control device volume')
        with self.assertRaises(self.use_cases.MusicBackendCapabilityError) as caught:
            asyncio.run(b.set_volume(30))
        self.assertEqual(caught.exception.capability, 'supports_volume')
        self.assertEqual(caught.exception.backend, 'spotify_direct')
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1].endswith('/me/player/volume?volume_percent=30'))

    def test_other_403_and_server_errors_are_not_permanent_volume_capability(self):
        for code, message in [(403, 'Insufficient client scope'), (403, 'Premium required'),
                              (503, 'Cannot control device volume'), (500, 'unknown')]:
            with self.subTest(code=code, message=message):
                b, calls = self.wire_backend(code, message)
                with self.assertRaises(self.spotify.SpotifyBackendError) as caught:
                    asyncio.run(b.set_volume(30))
                self.assertNotIsInstance(caught.exception, self.use_cases.MusicBackendCapabilityError)
                self.assertEqual(caught.exception.http_status, code)
                self.assertEqual(len(calls), 1)

    def invoke(self, command, *, exception=None, result=None, fail_status=False, health=True, value=30):
        class Runtime:
            device_token = 'synthetic-not-live'
            device_status = {'device_id': 'djconnect-ios-68B74487726D', 'client_type': 'ios',
                             'backend_available': health, 'voice_supported': True}
            config = {}
            last_error = 'independent-status-sentinel'
            last_dj_text = 'retained-dj-sentinel'
            last_playback = {'title': 'retained-track', 'volume_percent': 30, 'is_playing': True}
            def authorize_device_request(self, *args, **kwargs): return True
            def update(self, **kwargs): self.__dict__.update(kwargs)
        runtime = Runtime()
        hass = self.owner_hass(runtime)
        calls = []
        async def handler(h, r, cmd, command_value=None, **kwargs):
            calls.append(cmd)
            if cmd == 'status' and not fail_status:
                return {'success': True, 'playback': {'volume_percent': 30}}
            if exception is not None:
                raise exception
            return deepcopy(result)
        class Request:
            headers = {'Authorization': 'Bearer synthetic-not-live', 'X-DJConnect-Device-ID': runtime.device_status['device_id']}
            app = {'hass': hass}
            async def json(self):
                return {'device_id': runtime.device_status['device_id'], 'client_type': 'ios',
                        'command': command, 'value': value}
        before = deepcopy(runtime.device_status)
        with patch.object(self.http, 'run_music_command', handler):
            response = self.response_envelope(asyncio.run(self.http.DJConnectCommandView(None).post(Request())))
        self.assertEqual(runtime.device_status, before)
        self.assertEqual(runtime.last_error, 'independent-status-sentinel')
        self.assertEqual(runtime.last_dj_text, 'retained-dj-sentinel')
        self.assertEqual(runtime.last_playback['title'], 'retained-track')
        return response, calls

    def test_favorite_rate_limit_preserves_global_backend_health(self):
        response, calls = self.invoke(
            "set_current_track_favorite",
            exception=self.spotify.SpotifyBackendError("Rate limited", http_status=429, retry_after=120),
            value=True,
        )
        self.assertEqual(calls, ["set_current_track_favorite"])
        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["error"], "spotify_rate_limited")
        self.assertEqual(response["payload"]["retry_after_seconds"], 120)
        self.assertFalse(response["payload"]["retry_automatically"])
        self.assertNotIn("backend_available", response["payload"])

    def test_both_commands_keep_global_health_and_dj_state_for_action_failures(self):
        for command in ('set_volume', 'volume_delta'):
            for health in (True, False):
                for exc in (self.spotify.SpotifyBackendError('private token text', http_status=503),
                            TimeoutError('private raw error'),
                            self.use_cases.MusicBackendCapabilityError('set_volume', 'supports_volume', 'spotify_direct')):
                    with self.subTest(command=command, health=health, error=type(exc).__name__):
                        response, calls = self.invoke(command, exception=exc, health=health)
                        payload = response['payload']
                        self.assertEqual(response['status_code'], 200)
                        capability = isinstance(exc, self.use_cases.MusicBackendCapabilityError)
                        self.assertEqual(payload['error'], 'unsupported_backend_capability' if capability else 'volume_command_failed')
                        self.assertEqual(payload['command'], command)
                        self.assertEqual(payload['error_scope'], 'command')
                        self.assertIs(payload['retry_automatically'], False)
                        self.assertNotIn('private', json.dumps(payload))
                        for key in ('text', 'dj_text', 'audio_url', 'playback'):
                            self.assertNotIn(key, payload)
                        if capability:
                            self.assertIs(payload['backend_available'], True)
                            self.assertEqual(payload['capability'], 'supports_volume')
                        else:
                            self.assertNotIn('backend_available', payload)
                        self.assertEqual(calls, ['status', 'set_volume'] if command == 'volume_delta' else ['set_volume'])

    def test_delta_status_failure_is_scoped_without_attempting_volume(self):
        response, calls = self.invoke('volume_delta', exception=TimeoutError(), fail_status=True)
        self.assertEqual(response['payload']['error'], 'volume_command_failed')
        self.assertEqual(calls, ['status'])

    def test_returned_backend_refusal_is_not_reported_as_delta_success_or_global_outage(self):
        for command in ('set_volume', 'volume_delta'):
            for original in ({'success': False, 'error': 'backend_unavailable', 'backend_available': False},
                             {'success': False, 'error': 'unsupported_backend_capability', 'capability': 'supports_volume', 'backend': 'spotify_direct'}):
                with self.subTest(command=command, original=original['error']):
                    response, _ = self.invoke(command, result=original)
                    self.assertFalse(response['payload']['success'])
                    if original['error'] == 'backend_unavailable':
                        self.assertNotIn('backend_available', response['payload'])
                    else:
                        self.assertTrue(response['payload']['backend_available'])

    def test_invalid_delta_remains_invalid_input_and_never_dispatches(self):
        response, calls = self.invoke('volume_delta', value='invalid')
        self.assertEqual(response['status_code'], 400)
        self.assertEqual(response['payload']['error'], 'invalid_volume_delta')
        self.assertEqual(calls, [])

    def test_delta_returned_status_failure_cannot_dispatch_using_a_cached_volume(self):
        runtime = SimpleNamespace(last_playback={'volume_percent': 30})
        calls = []
        async def handler(h, r, command, *args):
            calls.append(command)
            return {'success': False, 'error': 'backend_unavailable', 'backend_available': False}
        with patch.object(self.http, 'run_music_command', handler):
            result = asyncio.run(self.http._handle_volume_delta_command(object(), runtime, 5))
        self.assertFalse(result['success'])
        self.assertEqual(calls, ['status'])

    def test_independent_status_failure_still_reports_the_existing_global_outage(self):
        runtime = SimpleNamespace(device_status={'backend_available': True}, last_playback={},
                                  update=lambda **kw: None, config={})
        result, status = self.handlers._unexpected_backend_error_result(
            object(), runtime, {}, 'status', 'status', self.spotify.SpotifyBackendError('Unavailable'))
        self.assertEqual(status, 200)
        self.assertEqual(result['error'], 'backend_unavailable')
        self.assertIs(runtime.device_status['backend_available'], False)

    def test_actual_paired_ha_volume_receipt_binds_the_current_product_and_verifier(self):
        import hashlib
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / 'examples/client_contracts/spotify_volume_v1/actual-ha-wire.json').read_text())
        self.assertTrue(proof['source_before_after_equal'])
        self.assertTrue(proof['receipt']['source_unchanged'])
        self.assertEqual(len(proof['source_pins']), 315)
        for path, expected in {**proof['source_pins'], proof['harness']: proof['harness_sha256']}.items():
            self.assertEqual(hashlib.sha256((root / path).read_bytes()).hexdigest(), expected, path)
        extension = proof['receipt']['extension']
        self.assertEqual(len(extension['cases']), 18)
        self.assertEqual(set(extension['cases'].values()), {'PASS'})
        self.assertEqual(extension['harness_sha256'], proof['harness_sha256'])
        self.assertEqual(extension['real_provider_calls'], 0)
        self.assertEqual(extension['native_installed_acceptance'], 'NOT_RUN')
