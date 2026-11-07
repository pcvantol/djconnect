"""Current real paired HA proof; no original native response or new authority."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PassiveObservationContractTests(unittest.TestCase):
    def test_original_grant_frames_and_nonrenewing_reads_match_current_source(self):
        wire = json.loads((ROOT / 'examples/client_contracts/passive_observation_sequence_v1/actual-ha-wire.json').read_text())
        self.assertTrue(wire['source_before_after_equal'])
        self.assertEqual(len(wire['source_pins']), 308)
        for name, digest in {**wire['source_pins'], **wire['harness_pins']}.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        receipt = wire['receipt']
        self.assertTrue(receipt['normal_pair_source_admission'])
        self.assertEqual(set(receipt['cases'].values()), {'PASS'})
        for state, pair in receipt['examples'].items():
            a, b = pair['before'], pair['after']
            self.assertEqual(a['grant_id'], b['grant_id'])
            a, b = a['passive_session'], b['passive_session']
            self.assertGreater(b['delivery_sequence'], a['delivery_sequence'])
            self.assertEqual(a['binding_id'], b['binding_id'])
            self.assertEqual(a['generation'], b['generation'])
            self.assertEqual(a['playback_state'], state)
            self.assertEqual(b['playback_state'], state)
        self.assertEqual(receipt['real_provider_calls'], 0)
        self.assertEqual(receipt['installed_mutations'], 0)
        self.assertFalse(receipt['original_live_response_reconstructed'])
        self.assertEqual(receipt['native_audible_apns_acceptance'], 'NOT_RUN')
