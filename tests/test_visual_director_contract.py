"""Actual producer decoder joins, preserved old artifacts and private omissions."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "examples/client_contracts/vibescape_visual_director_v1"


class VisualDirectorContractTests(unittest.TestCase):
    def fixture(self):
        return json.loads((DIRECTORY / "actual-ha-wire-story-recovery-20261022.json").read_text())

    def test_actual_registered_wire_pins_current_producer_and_declares_boundary(self):
        data = self.fixture()
        for relative, expected in data["source_pins"].items():
            self.assertEqual(
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative
            )
        self.assertEqual(data["ha_sdk_version"], "2026.10.0")
        self.assertEqual(data["model_provider_calls"], 0)
        self.assertEqual(data["consumer_adoption"], "NOT_RUN")
        self.assertEqual(data["installed"], "NOT_RUN")
        self.assertIn("SYNTHETIC_PROVIDER_IO", data["qualification"])
        self.assertIn(
            "initial_unavailable_context_no_SQL_Profile_history_access_after_task_drain",
            data["cases"],
        )
        self.assertIn("different_output_ids_with_same_name_fence_original_lease", data["cases"])

    def test_interpret_echoes_original_admission_without_application_or_identity_leak(self):
        examples = self.fixture()["examples"]
        request, answer = examples["interpret_request"], examples["interpret_response"]
        context = next(
            row["body"]
            for row in self.fixture()["visual_receipts"]
            if row["kind"] == "context"
            and row["status"] == 200
            and row["body"]["context_lease_id"] == request["context_lease_id"]
        )
        for key in (
            "visit_id",
            "client_turn_id",
            "base_scene_revision",
            "context_lease_id",
            "observed_occurrence_id",
        ):
            self.assertEqual(answer[key], request[key])
        self.assertEqual(answer["expires_at"], context["expires_at"])
        duration = (
            datetime.fromisoformat(context["expires_at"])
            - datetime.fromisoformat(context["issued_at"])
        ).total_seconds()
        self.assertGreater(duration, 0)
        self.assertLessEqual(duration, 15)
        self.assertAlmostEqual(duration * 1000, context["lease_duration_ms"])
        self.assertEqual(answer["status"], "interpreted")
        self.assertNotIn("applied", answer)
        self.assertNotIn("text", answer)
        self.assertNotIn("synthetic-exact-output", json.dumps(context))
        self.assertIsNone(context["music_context"]["audio_features"])

    def test_actual_action_union_and_error_receipts_have_no_fallback_success(self):
        kinds = set()
        errors = 0
        for row in self.fixture()["visual_receipts"]:
            body = row["body"]
            self.assertEqual(body["schema_version"], 1)
            if row["status"] != 200:
                errors += 1
                self.assertEqual(set(body), {"success", "schema_version", "error"})
                self.assertFalse(body["success"])
            elif row["kind"] == "interpret":
                kind = body["directive"]["kind"]
                kinds.add(kind)
                self.assertEqual(body["effect_code"], "visual_" + kind)
                if kind == "patch":
                    self.assertTrue(body["directive"]["patch"])
                    self.assertNotIn("dynamics_bias", body["directive"]["patch"])
        self.assertEqual(kinds, {"patch", "undo", "reset", "variant", "hold"})
        self.assertGreaterEqual(errors, 10)
