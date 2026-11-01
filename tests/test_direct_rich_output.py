"""Closed output format controls; fixtures supply DATA, never permission."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import unittest

_PATH = Path(__file__).resolve().parents[1] / 'custom_components/djconnect/direct_rich_output.py'
_SPEC = importlib.util.spec_from_file_location('direct_rich_output_under_test', _PATH)
output = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(output)


def fixture():
    unavailable = {'state': 'unavailable', 'reason': 'no_publication'}
    return {'schema_version': 1, 'binding_id': '12345678-1234-4234-8234-123456789abc',
        'generation': '12345678-1234-4234-8234-123456789abc', 'session_id': 'synthetic-session',
        'delivery_sequence': 1, 'frame_id': 'a' * 64, 'state': 'active', 'observed_at_ms': 900,
        'expires_at_ms': 1000, 'playback_state': 'unknown', 'mood': {'value': None, 'revision': 0},
        'presence': 'balanced', 'persona': 'home_dj', 'contribution': None, 'now_playing': None,
        'artwork': [], 'contribution_status': dict(unavailable), 'now_playing_status': dict(unavailable),
        'artwork_status': dict(unavailable)}


class DirectRichOutputTests(unittest.TestCase):
    def test_compiled_format_remains_bound_to_actual_canonical_schema(self):
        path = Path(__file__).resolve().parents[1] / 'docs/verification/fixtures/direct_rich_session_runtime_v1.schema.json'
        self.assertEqual(output.SCHEMA_SHA256, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_closed_frame_keys_nested_shapes_integers_and_permission_flags(self):
        value = fixture()
        self.assertTrue(output.valid('frame', value))
        for key in value:
            bad = deepcopy(value)
            del bad[key]
            with self.subTest(missing=key):
                self.assertFalse(output.valid('frame', bad))
        for key, replacement in [('extra', True), ('delivery_sequence', True), ('delivery_sequence', 1.0),
                ('expires_at_ms', 2**53), ('playback_state', 'idle'),
                ('mood', {'value': 'invented', 'revision': 1}), ('presence', 'invented'),
                ('contribution_status', {'state': 'available', 'reason': 'unknown'}),
                ('frame_id', 'a' * 64 + '\n')]:
            with self.subTest(key=key, replacement=replacement):
                self.assertFalse(output.valid('frame', {**value, key: replacement}))

    def test_every_optional_music_field_is_bounded_before_emission(self):
        value = {'item_id': 'a' * 24, 'subject_uri': 'spotify:track:' + 'A' * 22,
            'track': 'Synthetic', 'artist': 'Synthetic', 'album': '',
            'observed_at': '2026-10-31T19:00:00+00:00', 'expires_at': '2026-10-31T19:02:00+00:00',
            'source_url': 'https://open.spotify.com/track/' + 'A' * 22,
            'attribution': {'provider': 'Spotify', 'mark': 'spotify', 'url': 'https://open.spotify.com/track/' + 'A' * 22},
            'usage_basis': 'spotify_temporary_passive_metadata'}
        self.assertTrue(output.valid('now_playing', value))
        for key in ('track', 'artist', 'album'):
            self.assertTrue(output.valid('now_playing', {**value, key: 'X' * 512}))
            self.assertFalse(output.valid('now_playing', {**value, key: 'X' * 513}))
            self.assertFalse(output.valid('now_playing', {**value, key: '音' * 200}))
        self.assertFalse(output.valid('now_playing', {**value, 'external_relay': True}))
        self.assertFalse(output.valid('now_playing', {**value, 'attribution': {}}))

    def test_read_and_authorize_response_secrets_cannot_cross_closed_variants(self):
        value = {'success': True, 'contract_version': 1, 'profile_id': 'djconnect-direct-rich-v1',
            'operation_id': '12345678-1234-4234-8234-123456789abc', 'request_sha256': 'b' * 64,
            'purpose_id': '12345678-1234-4234-8234-123456789abc', 'surface': 'widget', 'state': 'active',
            'purpose_issued_at_ms': 1, 'purpose_expires_at_ms': 1000, 'frame': fixture()}
        self.assertTrue(output.valid('read_response', value))
        self.assertFalse(output.valid('authorize_response', value))
        issued = {**value, 'read_credential': 'djcrichread_' + 'A' * 43,
            'asset_credential': 'djcrichasset_' + 'A' * 43}
        self.assertTrue(output.valid('authorize_response', issued))
        self.assertFalse(output.valid('read_response', issued))
        self.assertFalse(output.valid('authorize_response', {**issued, 'read_credential': issued['asset_credential']}))
