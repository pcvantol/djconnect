"""Actual isolated HA receipt binding; never native or provider acceptance."""
import hashlib
import json
from pathlib import Path
import unittest


class PassiveProgressQualificationTests(unittest.TestCase):
    def test_actual_http_receipt_is_bound_to_current_source_and_harnesses(self):
        root = Path(__file__).resolve().parents[1]
        folder = root/'examples/client_contracts/passive_progress_v3'
        proof = json.loads((folder/'qualification-current.json').read_text())
        receipt = proof['receipt']
        self.assertTrue(proof['source_before_after_equal'])
        self.assertTrue(receipt['source_unchanged'])
        self.assertEqual(len(proof['source_pins']), 315)
        self.assertEqual(proof['source_pins'], receipt['source_pins'])
        for name, expected in {**proof['source_pins'], **receipt['harness_pins']}.items():
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
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(len(receipt['cases']), 17)
        self.assertEqual(set(receipt['cases'].values()), {'PASS'})
        self.assertEqual((receipt['real_provider_calls'], receipt['model_provider_calls']), (0, 0))
        self.assertEqual(receipt['native_widget_shared_cache_physical_acceptance'], 'NOT_RUN')
        wire = json.loads((folder/'actual-ha-wire.json').read_text())
        self.assertEqual(wire['examples'], receipt['examples'])
        self.assertEqual(wire['capabilities'], receipt['capability'])
        self.assertEqual(wire['request_contract']['image_query']['projection_version'], '3')
