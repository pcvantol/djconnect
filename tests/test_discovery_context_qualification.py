"""Bind actual paired HA context proof to current product and harness bytes."""

import hashlib
import json
from pathlib import Path
import unittest


class DiscoveryContextQualificationTests(unittest.TestCase):
    def test_current_source_has_actual_original_card_transport_and_diagnosis_evidence(self):
        root = Path(__file__).resolve().parents[1]
        p = json.loads(
            (
                root / "examples/client_contracts/discovery_context_v1/actual-ha-wire.json"
            ).read_text()
        )
        r = p["receipt"]
        self.assertTrue(p["source_before_after_equal"])
        self.assertTrue(r["source_unchanged"])
        self.assertTrue(r["actual_home_assistant"])
        self.assertTrue(r["ordinary_pairing"])
        self.assertTrue(r["aiohttp_default_retry_client"])
        self.assertEqual(len(p["source_pins"]), 309)
        for name, expected in {**p["source_pins"], **p["harness_pins"]}.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(len(r["cases"]), 14)
        self.assertEqual(set(r["cases"].values()), {"PASS"})
        self.assertEqual(
            (r["real_provider_calls"], r["real_model_calls"], r["installed_mutations"]), (0, 0, 0)
        )
        self.assertEqual(p["native_installed_acceptance"], "NOT_RUN")
        wires = r["wire_examples"]
        self.assertTrue(wires["artist_success"]["played"])
        self.assertFalse(wires["artist_success"]["action_outcome"]["retry_automatically"])
        self.assertFalse(wires["artist_success"]["action_outcome"]["queue_replacement_verified"])
        self.assertEqual(wires["connection_lost_after_write"]["action_outcome"]["state"], "unknown")
        self.assertFalse(wires["connection_lost_after_write"]["retry_automatically"])
        self.assertEqual(wires["output_required"]["error"], "music_discovery_output_required")
        self.assertFalse(wires["direct_candidate_read"]["dispatch_authority"])
        self.assertEqual(wires["direct_candidate_denied"]["provider_http_status"], 403)
