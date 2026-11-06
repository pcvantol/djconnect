"""Actual isolated HA catalogue proof, pinned without live/native claims."""

import hashlib
import json
from pathlib import Path
import unittest


class ArtistCollectionsQualificationTests(unittest.TestCase):
    def test_original_paired_http_offer_proof_matches_current_source(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / "examples/client_contracts/artist_collections_v1/actual-ha-wire.json").read_text())
        self.assertTrue(proof["source_before_after_equal"])
        self.assertEqual(len(proof["source_pins"]), 308)
        for name, expected in {**proof["source_pins"], **proof["harness_pins"]}.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        receipt = proof["receipt"]
        self.assertTrue(receipt["actual_home_assistant"])
        self.assertTrue(receipt["ordinary_pairing"])
        self.assertTrue(receipt["source_unchanged"])
        self.assertEqual(len(receipt["cases"]), 6)
        self.assertEqual(set(receipt["cases"].values()), {"PASS"})
        self.assertEqual((receipt["real_provider_calls"], receipt["real_model_calls"], receipt["installed_mutations"]), (0, 0, 0))
        self.assertTrue(receipt["declared_agent_plan_fixture"])
        self.assertTrue(receipt["declared_spotify_wire_fixture"])
        self.assertEqual(receipt["live_provider_acceptance"], "NOT_RUN")
        self.assertEqual(receipt["native_acceptance"], "NOT_RUN")
        self.assertTrue(all(call["method"] == "GET" for call in receipt["provider_fixture_calls"]))
        for locale in ("nl", "en"):
            result = receipt["examples"][locale]
            actions = result["playback_actions"]
            self.assertEqual([row["kind"] for row in actions].count("album"), 5)
            self.assertEqual([row["kind"] for row in actions].count("playlist"), 5)
            self.assertTrue(all(row.get("action_id") for row in actions))
            self.assertEqual(result["action"], "none")
