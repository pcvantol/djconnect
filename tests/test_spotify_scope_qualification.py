"""Actual isolated HA grant/Repair receipt; never a real OAuth or native claim."""
import hashlib
import json
from pathlib import Path
import unittest


class SpotifyScopeQualificationTests(unittest.TestCase):
    def test_actual_callback_configflow_refresh_and_store_bind_current_source(self):
        root=Path(__file__).resolve().parents[1]
        proof=json.loads((root/'examples/client_contracts/spotify_scope_evidence_v1/actual-ha-wire.json').read_text())
        receipt=proof['receipt']
        self.assertTrue(proof['source_before_after_equal'])
        self.assertTrue(receipt['source_unchanged'])
        self.assertTrue(receipt['actual_ha_store_readback'])
        self.assertEqual(len(proof['source_pins']),309)
        for name,expected in {**proof['source_pins'],**receipt['harness_pins']}.items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),expected,name)
        self.assertEqual(len(receipt['cases']),14)
        self.assertEqual(set(receipt['cases'].values()),{'PASS'})
        self.assertEqual((receipt['real_oauth_calls'],receipt['installed_mutations']),(0,0))
        self.assertEqual(proof['native_installed_acceptance'],'NOT_RUN')
        rows={e['case']:e['scope_status'] for e in receipt['scope_examples']}
        self.assertIn('user-modify-playback-state',rows['grant_partial']['missing_granted_scopes'])
        self.assertEqual(rows['grant_full']['missing_granted_scopes'],[])
        self.assertIsNone(rows['grant_missing']['granted_scopes'])
        self.assertEqual(rows['refresh_partial']['granted_scope_evidence'],rows['refresh_missing']['granted_scope_evidence'])
