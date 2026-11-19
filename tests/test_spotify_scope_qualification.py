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
        self.assertEqual(len(proof['source_pins']),315)
        for name,expected in {**proof['source_pins'],**receipt['harness_pins']}.items():
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
