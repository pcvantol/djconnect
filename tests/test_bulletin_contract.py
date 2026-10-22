"""Exact actual-HA wire join for the additive Core/Apple bulletin contract."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BulletinWireContractTests(unittest.TestCase):
    def test_actual_wire_pins_current_source_and_original_admissions_without_native_claim(self):
        wire = json.loads((ROOT / "examples/client_contracts/dj_bulletin_v1/actual-ha-wire.json").read_text())
        self.assertEqual(wire["schema_version"], 1)
        self.assertEqual(wire["ha_sdk_version"], "2026.10.0")
        for relative, expected in wire["source_pins"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)
        self.assertEqual(hashlib.sha256((ROOT / wire["harness"]).read_bytes()).hexdigest(), wire["harness_sha256"])
        sample = wire["sample"]
        moment = sample["moment"]
        self.assertEqual(moment["type"], "dj_bulletin")
        self.assertEqual(moment["generation_metadata"]["bulletin_schema"], "1")
        self.assertEqual(moment["visibility"], "owner_only")
        self.assertEqual(moment["delivery_channels"], ["owner"])
        self.assertEqual(len(moment["sources"]), 2)
        self.assertEqual(sample["native_delivery"]["current_moment_id"], moment["moment_id"])
        self.assertTrue(sample["speech_off"]["manual_allowed"])
        self.assertFalse(sample["speech_off"]["autoplay_eligible"])
        self.assertTrue(sample["speech_on"]["autoplay_eligible"])
        self.assertEqual(sample["speech_off"]["expires_at"], sample["speech_on"]["expires_at"])
        self.assertIsNone(wire["revoked_native_delivery"]["current_moment_id"])
        self.assertEqual(wire["model_provider_calls"], 0)
        self.assertEqual(wire["external_RSS_calls"], 0)
        for key in ("native", "audible", "installed", "story_semantic_model_quality"):
            self.assertEqual(wire[key], "NOT_RUN")
