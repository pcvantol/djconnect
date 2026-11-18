"""Regression for the stated scope of historical HA source receipts."""
import ast
import json
import re
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_ask_dj_help_live_observation as help_observation_tests


class HistoricalManifestBoundaryTests(unittest.TestCase):
    def test_receipt_exception_is_limited_to_explicit_migration_files(self):
        expected = {
            "custom_components/djconnect/manifest.json",
            "custom_components/djconnect/artist_photo.py",
            "custom_components/djconnect/ask_dj/public_research.py",
            "custom_components/djconnect/const.py",
            "custom_components/djconnect/session_facts.py",
        }
        marker = "# Historical receipts do not qualify the current migration-edited files."
        pattern = re.compile(re.escape(marker) + r"\s+if \w+ in (\([^)]*\)):")
        root = Path(__file__).resolve().parent
        count = 0
        for file in root.rglob("test_*.py"):
            text = file.read_text()
            if file == Path(__file__):
                continue
            matches = pattern.findall(text)
            self.assertEqual(len(matches), text.count(marker), str(file))
            for value in matches:
                self.assertEqual(set(ast.literal_eval(value)), expected, str(file))
                count += 1
        self.assertGreater(count, 0)

    def test_non_manifest_source_mismatch_remains_a_failure(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / "examples/client_contracts/ask_dj_help_context_v1/actual-ha-wire-bulletin-diagnostics-current.json").read_text())
        manifest = "custom_components/djconnect/manifest.json"
        deferred = {manifest, "custom_components/djconnect/artist_photo.py",
                    "custom_components/djconnect/ask_dj/public_research.py",
                    "custom_components/djconnect/const.py", "custom_components/djconnect/session_facts.py"}
        candidate = next(name for name in proof["source_hashes"] if name not in deferred)
        target = root / candidate
        original = Path.read_bytes

        def altered(path):
            data = original(path)
            return data + b"\nsynthetic mismatch" if path == target else data

        case = help_observation_tests.HelpObservationTests(
            "test_original_actual_ha_wire_binds_all_current_products_without_native_claim"
        )
        result = unittest.TestResult()
        with patch.object(Path, "read_bytes", altered):
            case.run(result)
        self.assertEqual(len(result.failures), 1)
        self.assertFalse(result.errors)
        self.assertIn(candidate, result.failures[0][1])
