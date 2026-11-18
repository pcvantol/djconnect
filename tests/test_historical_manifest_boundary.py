"""Regression for the stated scope of historical HA source receipts."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_ask_dj_help_live_observation as help_observation_tests


class HistoricalManifestBoundaryTests(unittest.TestCase):
    def test_non_manifest_source_mismatch_remains_a_failure(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / "examples/client_contracts/ask_dj_help_context_v1/actual-ha-wire-bulletin-diagnostics-current.json").read_text())
        manifest = "custom_components/djconnect/manifest.json"
        candidate = next(name for name in proof["source_hashes"] if name != manifest)
        target = root / candidate
        original = Path.read_bytes

        def altered(path):
            data = original(path)
            return data + b"\nsynthetic mismatch" if path == target else data

        case = help_observation_tests.HelpObservationTests(
            "test_historical_ha_receipt_binds_non_manifest_sources_without_native_claim"
        )
        result = unittest.TestResult()
        with patch.object(Path, "read_bytes", altered):
            case.run(result)
        self.assertEqual(len(result.failures), 1)
        self.assertFalse(result.errors)
        self.assertIn(candidate, result.failures[0][1])
