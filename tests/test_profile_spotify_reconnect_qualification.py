"""Exact isolated HA reconnect evidence; no installed or real grant claim."""
import hashlib
import json
from pathlib import Path
import unittest


class ProfileSpotifyReconnectQualificationTests(unittest.TestCase):
    def test_current_source_has_profile_owned_callback_and_shared_caller_proof(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / 'examples/client_contracts/profile_spotify_reconnect_v1/actual-ha-wire.json').read_text())
        self.assertTrue(proof['source_before_after_equal'])
        self.assertEqual(len(proof['source_pins']), 315)
        for name, expected in {**proof['source_pins'], **proof['harness_pins']}.items():
            # The historical renderer digest is not a claim about the current 4.1 renderer.
            if name == "custom_components/djconnect/vibecast.html":
                self.assertEqual(expected, "308e916366caac9bab737eed3352979159138946091fbcb8f7b7387310de4da9")
                continue
            if name == "custom_components/djconnect/vibecast_display.html":
                self.assertEqual(expected, "bd63f6301314fb381ac08424c4d3669752d0d0f48be2c54522196af731647c4c")
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
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        receipt = proof['receipt']
        self.assertTrue(receipt['source_unchanged'])
        self.assertTrue(receipt['actual_ha_store_readback'])
        self.assertTrue(receipt['token_exchange_reload_options_completion_are_fixtures'])
        self.assertEqual(len(receipt['cases']), 10)
        self.assertEqual(set(receipt['cases'].values()), {'PASS'})
        self.assertEqual((receipt['real_oauth_calls'], receipt['installed_mutations']), (0, 0))
        probe = proof['canonical_view_probe']
        self.assertTrue(probe['registered_caller_authority_valid'])
        self.assertTrue(probe['canonical_view_is_not_registry_runtime'])
        self.assertTrue(probe['result']['success'])
        self.assertTrue(probe['result']['read_only'])
        self.assertFalse(probe['result']['dispatch_authority'])
        self.assertEqual(probe['real_provider_calls'], 0)
        self.assertEqual(proof['native_installed_acceptance'], 'NOT_RUN')
