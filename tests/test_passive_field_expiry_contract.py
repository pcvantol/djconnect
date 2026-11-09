"""Current paired-HA natural-expiry source proof, never native acceptance."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PassiveFieldExpiryContractTests(unittest.TestCase):
    def test_actual_original_frame_survives_only_shorter_field_expiry(self):
        wire = json.loads((ROOT / 'examples/client_contracts/passive_field_expiry_v1/actual-ha-wire.json').read_text())
        self.assertTrue(wire['source_before_after_equal'])
        self.assertEqual(len(wire['source_pins']), 309)
        for name, digest in {**wire['source_pins'], **wire['harness_pins']}.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        r = wire['receipt']
        self.assertEqual(set(r['cases'].values()), {'PASS'})
        self.assertTrue(r['same_original_grant'] and r['same_binding'] and r['same_generation'])
        self.assertTrue(r['same_delivery_sequence'] and r['root_still_unexpired'])
        self.assertTrue(r['contribution_before'])
        self.assertFalse(r['contribution_after'])
        a, b = r['before']['passive_session'], r['after']['passive_session']
        for key in ('revision', 'delivery_sequence', 'observed_at', 'expires_at'):
            self.assertEqual(a[key], b[key])
        self.assertGreater(r['waited_real_seconds'], 0)
        self.assertTrue(r['no_new_backend_observation'])
        self.assertFalse(r['original_live_wire_reconstructed'])
        self.assertEqual(r['real_provider_calls'], 0)
        self.assertEqual(r['installed_mutations'], 0)
        self.assertEqual(r['native_acceptance'], 'NOT_RUN')
