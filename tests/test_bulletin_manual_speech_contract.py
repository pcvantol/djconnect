"""Current paired HA proof of bounded private headline manual speech."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BulletinManualSpeechContractTests(unittest.TestCase):
    def test_actual_paired_manual_use_denial_and_withdrawal_join_current_source(self):
        wire = json.loads((ROOT / "examples/client_contracts/bulletin_manual_speech_v1/actual-ha-wire.json").read_text())
        self.assertTrue(wire["source_before_after_equal"])
        self.assertEqual(len(wire["source_pins"]), 309)
        for name, digest in wire["source_pins"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        for name, digest in wire["harness_pins"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        proof = wire["receipt"]["extension"]
        self.assertEqual(proof["state"], "PASS")
        self.assertEqual(proof["manual_ha_synthesis_calls"], 2)
        for key in ("automatic_ha_denied", "late_source_withdrawal_discards_waveform",
                    "source_withdrawal_audio_denied", "shared_tls_snapshot_excludes_moment"):
            self.assertTrue(proof[key], key)
        self.assertEqual(proof["visibility"], "owner_only")
        self.assertEqual(proof["model_provider_calls"], 0)
        self.assertEqual(proof["external_RSS_calls"], 0)
        self.assertEqual(proof["installed_or_native_acceptance"], "NOT_RUN")
