"""Join the original actual HA proof to this exact candidate, not installation."""
import hashlib
import json
from pathlib import Path
import unittest


class DirectRichOriginalActualHATests(unittest.TestCase):
    def test_actual_host_wake_HTTP_Broadcast_SQL_originals_bind_current_source(self):
        root = Path(__file__).resolve().parents[1]
        value = json.loads((root / 'examples/client_contracts/direct_rich_v1/actual-ha-host-wake-runtime.json').read_bytes())
        receipt = value['original_receipt']
        self.assertEqual(receipt['status'], 'PASS')
        self.assertEqual(receipt['schema_version'], 21)
        self.assertEqual(len(receipt['source_sha256']), 301)
        for name, expected in receipt['source_sha256'].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(hashlib.sha256((root / value['harness']).read_bytes()).hexdigest(), value['harness_sha256'])
        self.assertEqual(hashlib.sha256((json.dumps(receipt, indent=2) + '\n').encode()).hexdigest(),
            value['original_receipt_sha256'])
        actual = receipt['host_wake_runtime']
        self.assertEqual(actual['actual_http_operations'], 7)
        self.assertEqual(actual['wakes'], actual['durable_wakes'])
        self.assertEqual(actual['durable_wakes'], 1)
        self.assertEqual(actual['external_API_native_provider'], 'MODELED_ONLY')
        self.assertTrue(value['all301_before_inside_after_equal'])
        self.assertEqual(value['own_container'], 'VERIFIED_ABSENT')
        self.assertEqual(value['installed'], 'NOT_RUN')
        self.assertFalse(value['actual_native_operator_or_APNs_qualification'])

    def test_original_actual_HTTP_SQL_and_asset_proof_matches_entire_current_product(self):
        root = Path(__file__).resolve().parents[1]
        value = json.loads((root / 'examples/client_contracts/direct_rich_v1/actual-ha-original-purpose-and-assets.json').read_bytes())
        receipt = value['original_receipt']
        self.assertEqual(value['classification'], 'ACTUAL_ISOLATED_HA_DIRECT_RICH_SOURCE_ONLY')
        self.assertEqual(receipt['classification'], 'DIRECT_RICH_ACTUAL_ISOLATED_HA_SOURCE_ONLY')
        self.assertEqual(receipt['status'], 'PASS')
        self.assertEqual(receipt['schema_version'], 21)
        self.assertEqual(receipt['original_prepared_covers'], 1)
        self.assertEqual(receipt['read_reissues'], 0)
        self.assertEqual(receipt['model_calls'], 0)
        self.assertTrue(receipt['ordinary_pairing'])
        self.assertEqual(receipt['ha_credentials_issued'], 0)
        self.assertEqual(len(receipt['source_sha256']), 301)
        for name, expected in receipt['source_sha256'].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(hashlib.sha256((root / value['harness']).read_bytes()).hexdigest(), value['harness_sha256'])
        self.assertEqual(hashlib.sha256((json.dumps(receipt, indent=2) + '\n').encode()).hexdigest(),
            value['original_receipt_sha256'])
        self.assertTrue(value['all301_before_inside_after_equal'])
        self.assertEqual(value['own_container'], 'VERIFIED_ABSENT')
        self.assertEqual(value['installed'], 'NOT_RUN')
        self.assertFalse(value['actual_native_clock_or_provider_or_iPhone_qualification'])
        self.assertIn('actual_prepared_cover_original_bytes_digest_and_asset_role', receipt['cases'])
        self.assertIn('actual_Session_end_synchronous_secret_scrub_and_original_negative_history', receipt['cases'])
        self.assertEqual(receipt['host_wake_management']['after'], 'withdrawn')
        self.assertFalse(receipt['host_wake_management']['remote_API_or_native_ack'])
        self.assertFalse(receipt['host_wake_management']['actual_issuer_operator_enrollment_clock_or_provider_permission'])
