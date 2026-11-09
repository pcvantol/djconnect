"""Original private catalogue wire and Session fences, without archival authority."""

import hashlib
import json
from pathlib import Path
import unittest


class SessionPrivateCatalogueQualificationTests(unittest.TestCase):
    def test_actual_original_session_wire_omits_partial_history_objects(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / "examples/client_contracts/session_private_catalogue_v1/actual-ha-wire.json").read_text())
        self.assertTrue(proof["source_before_after_equal"])
        self.assertEqual(len(proof["source_pins"]), 309)
        for name, expected in {**proof["source_pins"], **proof["harness_pins"]}.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        receipt = proof["receipt"]
        self.assertTrue(receipt["actual_home_assistant"])
        self.assertTrue(receipt["ordinary_pairing"])
        self.assertTrue(receipt["fresh_session_with_no_current_playback"])
        self.assertTrue(receipt["source_unchanged"])
        self.assertEqual((receipt["accepted_settings_contract"], receipt["requested_history_contract"], receipt["requested_speech_contract"]), (3, 2, 3))
        self.assertEqual(len(receipt["cases"]), 7)
        self.assertEqual(set(receipt["cases"].values()), {"PASS"})
        self.assertEqual((receipt["real_model_calls"], receipt["real_provider_calls"], receipt["installed_mutations"]), (0, 0, 0))
        self.assertEqual(receipt["native_acceptance"], "NOT_RUN")
        for locale in ("nl", "en"):
            for surface in ("session", "general"):
                body = receipt["examples"][surface + "_" + locale]
                self.assertTrue(body["success"])
                self.assertFalse(body["history_persisted"])
                self.assertTrue(body["owner_profile_id"])
                self.assertTrue(body["client_message_id"])
                confirmation = body["conversation"]
                self.assertEqual(confirmation["schema_version"], 1)
                self.assertEqual(confirmation["history_scope"], "private_ephemeral")
                self.assertTrue(confirmation["turn_id"])
                self.assertEqual(confirmation["entry_ids"], [])
                self.assertEqual(bool(confirmation["context"].get("session_id")), surface == "session")
                for key in ("assistant_message", "user_message", "messages", "history_revision", "clear_revision"):
                    self.assertNotIn(key, body)
                self.assertEqual(len(body["items"]), 10)
                self.assertEqual(len(body["playback_actions"]), 10)
                self.assertTrue(all(row.get("action_id") for row in body["playback_actions"]))
