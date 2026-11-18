"""Actual paired HA freshness/effect evidence; never native or provider acceptance."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ForYouRefreshContractTests(unittest.TestCase):
    def test_original_ha_fixture_matches_the_current_producer_and_harness(self):
        record = json.loads((ROOT/'examples/client_contracts/session_for_you_v1/actual-ha-mood-refresh-20261106.json').read_text())
        self.assertTrue(record['source_unchanged'])
        for name, digest in record['source_pins'].items():
            # The historical renderer digest is not a claim about the current 4.1 renderer.
            if name == "custom_components/djconnect/vibecast.html":
                self.assertEqual(digest, "308e916366caac9bab737eed3352979159138946091fbcb8f7b7387310de4da9")
                continue
            if name == "custom_components/djconnect/vibecast_display.html":
                self.assertEqual(digest, "bd63f6301314fb381ac08424c4d3669752d0d0f48be2c54522196af731647c4c")
                continue
            # Historical receipts do not qualify the current migration-edited files.
            if name in (
                "custom_components/djconnect/manifest.json",
                "custom_components/djconnect/artist_photo.py",
                "custom_components/djconnect/ask_dj/public_research.py",
                "custom_components/djconnect/const.py",
                "custom_components/djconnect/session_facts.py",
            ):
                continue
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((ROOT/record['harness']).read_bytes()).hexdigest(), record['harness_sha256'])
        self.assertEqual(len(record['cases']), 8)
        self.assertEqual(set(record['cases'].values()), {'PASS'})
        self.assertEqual((record['real_provider_calls'], record['real_model_calls']), (0, 0))
        self.assertEqual(record['installed_native_audible_apns'], 'NOT_RUN')
        self.assertTrue(record['fixture_only'])
        for locale in ('en', 'nl'):
            rows = {e['stage']: e['body'] for e in record['examples'] if e['language']==locale}
            offer = rows['refreshed_offer']['for_you']
            self.assertEqual(offer['language'], locale)
            self.assertEqual(offer['refresh_policy']['schema_version'], 1)
            self.assertEqual(offer['refresh_policy']['execution'], 'server')
            self.assertFalse(offer['refresh_policy']['automatic_playback'])
            self.assertFalse(offer['refresh_policy']['retry_automatically'])
            self.assertFalse(offer['refresh_request']['automatic'])
            selected = rows['original_speaker_continuation']
            continuation = selected['for_you']['continuation']
            self.assertEqual(continuation['first_play']['state'], 'output')
            self.assertEqual(continuation['result_set']['result_set_id'], selected['result_set']['result_set_id'])
            self.assertLessEqual(continuation['result_set']['expires_in'], continuation['expires_in'])
            played = rows['exact_mix_confirmed_once']
            self.assertTrue(played['action_outcome']['readback_confirmed'])
            self.assertFalse(played['for_you']['visible'])

    def test_output_readback_proof_is_exact_and_keeps_unconfirmed_effects_closed(self):
        record = json.loads((ROOT/'examples/client_contracts/session_for_you_v1/actual-ha-output-readback-20261106.json').read_text())
        self.assertTrue(record['source_unchanged'])
        for name, digest in record['source_pins'].items():
            # The historical renderer digest is not a claim about the current 4.1 renderer.
            if name == "custom_components/djconnect/vibecast.html":
                self.assertEqual(digest, "308e916366caac9bab737eed3352979159138946091fbcb8f7b7387310de4da9")
                continue
            if name == "custom_components/djconnect/vibecast_display.html":
                self.assertEqual(digest, "bd63f6301314fb381ac08424c4d3669752d0d0f48be2c54522196af731647c4c")
                continue
            # Historical receipts do not qualify the current migration-edited files.
            if name in (
                "custom_components/djconnect/manifest.json",
                "custom_components/djconnect/artist_photo.py",
                "custom_components/djconnect/ask_dj/public_research.py",
                "custom_components/djconnect/const.py",
                "custom_components/djconnect/session_facts.py",
            ):
                continue
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((ROOT/record['harness']).read_bytes()).hexdigest(), record['harness_sha256'])
        self.assertEqual(len(record['cases']), 6)
        self.assertEqual(set(record['cases'].values()), {'PASS'})
        self.assertEqual((record['real_provider_calls'], record['real_model_calls']), (0, 0))
        self.assertEqual(record['installed_native_audible_apns'], 'NOT_RUN')
        for example in record['examples']:
            effects = example['synthetic_effects']
            if example['case'] == 'confirmed':
                self.assertEqual(example['status'], 200)
                self.assertEqual([effect['kind'] for effect in effects], ['output', 'play'])
                self.assertTrue(example['body']['action_outcome']['readback_confirmed'])
            else:
                self.assertEqual(example['status'], 409)
                self.assertEqual([effect['kind'] for effect in effects], ['output'])
                self.assertEqual(example['body']['error'], 'first_play_output_changed')
