"""Current actual paired HA proof; no native/provider admission."""
import hashlib
import json
from pathlib import Path
import unittest


class PassiveRetainedQualificationTests(unittest.TestCase):
    def test_current_receipt_binds_original_purpose_and_all_product_bytes(self):
        root=Path(__file__).resolve().parents[1]
        proof=json.loads((root/'examples/client_contracts/passive_retained_v1/qualification-current.json').read_text())
        receipt=proof['receipt']
        self.assertTrue(proof['source_before_after_equal'])
        self.assertTrue(receipt['source_unchanged'])
        self.assertEqual(len(proof['source_pins']),315)
        self.assertEqual(proof['source_pins'],receipt['source_pins'])
        for name,expected in {**proof['source_pins'],**receipt['harness_pins']}.items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),expected,name)
        self.assertEqual(len(receipt['cases']),10)
        self.assertEqual(set(receipt['cases'].values()),{'PASS'})
        self.assertEqual(receipt['native_installed_acceptance'],'NOT_RUN')
        self.assertEqual((receipt['real_provider_calls'],receipt['model_provider_calls']),(0,0))
        cap=receipt['capability']['retained_latest']
        self.assertEqual((cap['surface'],cap['projection_version'],cap['maximum_publication_seconds']),('widget',4,1800))
