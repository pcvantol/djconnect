"""Actual paired HA original-sample late confirmation; no native/live authority."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ForYouLateConfirmationContractTests(unittest.TestCase):
    def test_original_source_sample_confirms_same_mix_without_second_dispatch(self):
        wire = json.loads((ROOT / 'examples/client_contracts/for_you_late_confirmation_v1/actual-ha-wire.json').read_text())
        self.assertTrue(wire['source_before_after_equal'])
        self.assertEqual(len(wire['source_pins']), 315)
        for name, expected in {**wire['source_pins'], **wire['harness_pins']}.items():
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
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)
        receipt = wire['receipt']
        self.assertTrue(receipt['source_unchanged'])
        extension = receipt['extension']
        self.assertEqual(set(extension['cases'].values()), {'PASS'})
        examples = extension['late_confirmation_examples']
        self.assertEqual({x['language'] for x in examples}, {'en', 'nl'})
        for example in examples:
            self.assertEqual(example['actual_original_sample_type'], 'OriginalSample')
            self.assertEqual(example['original_response']['first_play']['state'], 'uncertain')
            self.assertEqual(example['confirmed_projection']['state'], 'confirmed')
            self.assertFalse(example['confirmed_projection']['visible'])
            self.assertEqual(len(example['synthetic_effects']), 1)
        self.assertEqual(extension['real_provider_calls'], 0)
        self.assertEqual(extension['model_provider_calls'], 0)
        self.assertEqual(extension['native_installed_acceptance'], 'NOT_RUN')
