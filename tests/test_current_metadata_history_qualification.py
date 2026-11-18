"""Bind cross-device Session producer evidence to actual current source bytes."""

import hashlib
import json
from pathlib import Path
import unittest


class CurrentMetadataHistoryQualificationTests(unittest.TestCase):
    def test_current_source_has_real_paired_cross_device_store_proof(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads(
            (
                root / "examples/client_contracts/current_metadata_history_v1/actual-ha-wire.json"
            ).read_text()
        )
        self.assertTrue(proof["source_before_after_equal"])
        self.assertEqual(len(proof["source_pins"]), 315)
        for name, expected in {**proof["source_pins"], **proof["harness_pins"]}.items():
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
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        receipt = proof["receipt"]
        self.assertTrue(receipt["actual_home_assistant"])
        self.assertTrue(receipt["ordinary_pairing"])
        self.assertTrue(receipt["source_unchanged"])
        self.assertEqual(len(receipt["cases"]), 10)
        self.assertEqual(receipt["cases"]["first_playing_after_paused_anchors_once_even_after_resume"], "PASS")
        self.assertEqual(receipt["cases"]["history_disabled_resume_stays_private_ephemeral"], "PASS")
        self.assertEqual(set(receipt["cases"].values()), {"PASS"})
        self.assertEqual(
            (
                receipt["real_provider_calls"],
                receipt["real_model_calls"],
                receipt["installed_mutations"],
            ),
            (0, 0, 0),
        )
        self.assertTrue(receipt["declared_stt_transcript_fixture"])
        self.assertEqual(receipt["stt_engine_acceptance"], "NOT_RUN")
        self.assertEqual(receipt["native_acceptance"], "NOT_RUN")
        self.assertTrue(all(call["method"] == "GET" for call in receipt["provider_fixture_calls"]))
        examples = receipt["examples"]
        ids = set(
            examples["mac_text"]["conversation"]["entry_ids"]
            + examples["watch_voice"]["conversation"]["entry_ids"]
        )
        self.assertEqual(len(ids), 4)
        for client in ("macos", "ios", "watchos"):
            rows = examples[client + "_tail"]["entries"]
            self.assertEqual(
                {row["entry_id"] for row in rows if row["kind"].startswith("conversation_")}, ids
            )
