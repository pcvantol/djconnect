from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.engineering.managed_autonomy import terminal_snapshot
from tools.engineering.storage import (
    record_run_qualification_lineage, record_submission, record_validation_control,
    record_validation_profile,
)
from tools.engineering.validation_profile import PROFILE_VERSION, classify


class RunQualificationEvidenceTests(unittest.TestCase):
    def _submission(self, root: Path, run_id: str = "inbox-evidence") -> None:
        record_submission(root, submission_id="submission-evidence", producer_id="test", producer_type="HUMAN",
            prompt_content="bounded", prompt_metadata={}, target_identity={}, original_envelope={},
            received_at="2026-08-27T00:00:00+00:00", link_run_id=run_id)

    def test_fresh_lineage_is_immutable_and_pre_provider_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._submission(root)
            record_run_qualification_lineage(root, run_id="inbox-evidence", submission_id="submission-evidence", observed_at="2026-08-27T00:00:01+00:00")
            from tools.engineering.storage import load_run_lineage
            lineage = load_run_lineage(root, "inbox-evidence")
        self.assertEqual(lineage["submission_id"], "submission-evidence")
        self.assertTrue(lineage["fresh_submission"])
        self.assertIsNone(lineage["retry_parent"])
        self.assertIsNone(lineage["resume_parent"])

    def test_retry_and_resume_cannot_be_fresh_or_dual_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._submission(root, "inbox-retry")
            record_run_qualification_lineage(root, run_id="inbox-retry", submission_id="submission-evidence", retry_parent_run_id="inbox-parent", observed_at="2026-08-27T00:00:01+00:00")
            from tools.engineering.storage import load_run_lineage, EngineeringStorageError
            self.assertFalse(load_run_lineage(root, "inbox-retry")["fresh_submission"])
            with self.assertRaises(EngineeringStorageError):
                record_run_qualification_lineage(root, run_id="inbox-resume", submission_id="submission-evidence", retry_parent_run_id="a", resume_parent_run_id="b", observed_at="2026-08-27T00:00:01+00:00")

    def test_required_validation_resolves_only_with_all_required_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._submission(root)
            profile = classify(["docs/engineering/a.md"])
            record_validation_profile(root, run_id="inbox-evidence", tier=profile.tier, profile_version=PROFILE_VERSION, required_controls=profile.required_controls, selected_at="2026-08-27T00:00:00+00:00")
            incomplete = terminal_snapshot(root, run_id="inbox-evidence", execution_outcome="COMPLETE", implementation_pr=None, finalization_pr=None, repository_state="UNAVAILABLE", workspace_state="UNAVAILABLE", main_origin_sync="UNAVAILABLE", worktree_state="UNAVAILABLE", active_blocker="UNAVAILABLE", recovery_required="UNAVAILABLE")
            self.assertEqual(incomplete["required_validation_state"], "UNRESOLVED")
            record_validation_control(root, run_id="inbox-evidence", validation_id="documentation_contract", required_for_profile=True, execution_status="EXECUTED", result="PASS", currentness=1, observed_at="2026-08-27T00:01:00+00:00", evidence_ref="test")
            complete = terminal_snapshot(root, run_id="inbox-evidence", execution_outcome="COMPLETE", implementation_pr=None, finalization_pr=None, repository_state="UNAVAILABLE", workspace_state="UNAVAILABLE", main_origin_sync="UNAVAILABLE", worktree_state="UNAVAILABLE", active_blocker="UNAVAILABLE", recovery_required="UNAVAILABLE")
        self.assertEqual(complete["required_validation_state"], "PASS")

    def test_full_profile_missing_control_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self._submission(root)
            profile = classify(["custom_components/djconnect/__init__.py"])
            record_validation_profile(root, run_id="inbox-evidence", tier=profile.tier, profile_version=PROFILE_VERSION, required_controls=profile.required_controls, selected_at="2026-08-27T00:00:00+00:00")
            snapshot = terminal_snapshot(root, run_id="inbox-evidence", execution_outcome="COMPLETE", implementation_pr=None, finalization_pr=None, repository_state="UNAVAILABLE", workspace_state="UNAVAILABLE", main_origin_sync="UNAVAILABLE", worktree_state="UNAVAILABLE", active_blocker="UNAVAILABLE", recovery_required="UNAVAILABLE")
        self.assertEqual(profile.tier, "FULL")
        self.assertEqual(snapshot["required_validation_state"], "UNRESOLVED")
