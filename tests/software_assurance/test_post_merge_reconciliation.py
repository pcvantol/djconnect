from __future__ import annotations

import copy
import unittest

from tools.trusted_delivery.post_merge_reconciliation import reconcile, validate_release_evidence


MAIN = "a" * 40
PR = "b" * 40
PARENT = "c" * 40


def request() -> dict[str, object]:
    return {
        "repository": "example/repository",
        "main_sha": MAIN,
        "main_parents": [PARENT],
        "timestamp": "2026-07-13T00:00:00Z",
        "originating_pr": {
            "number": 17,
            "state": "MERGED",
            "base_ref": "main",
            "head_sha": PR,
            "merge_commit_sha": MAIN,
            "merge_strategy": "SQUASH",
            "merge_actor": "maintainer",
            "merged_at": "2026-07-13T00:00:00Z",
            "changed_files": ["one.py", "two.py"],
            "main_changed_files": ["two.py", "one.py"],
        },
        "pre_merge": {
            "candidate_sha": PR,
            "risk_classification": "HIGH_RISK",
            "owner_authorization": "PASS",
            "verification": "PASS",
            "software_assurance": "PASS",
            "trusted_delivery": "PASS",
            "workflow_integrity": "PASS",
            "required_checks": "PASS",
        },
        "post_merge": {
            "sha": MAIN,
            "ci": "PASS",
            "tests": "PASS",
            "lint": "PASS",
            "static_analysis": "PASS",
            "build_validation": "PASS",
            "governance": "PASS",
            "coverage": "PASS",
            "coverage_report_sha": MAIN,
            "coverage_artifact_sha": "d" * 64,
            "workflow_run_ids": ["123"],
        },
    }


class PostMergeReconciliationTest(unittest.TestCase):
    def test_qualified_squash_merge_creates_exact_main_sha_evidence(self) -> None:
        evidence = reconcile(request())
        self.assertEqual(evidence["decision"], "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED")
        self.assertEqual(evidence["main_sha"], MAIN)
        self.assertEqual(evidence["source_qualified_pr_sha"], PR)
        self.assertNotEqual(evidence["main_sha"], evidence["source_qualified_pr_sha"])
        self.assertEqual(validate_release_evidence(evidence, "example/repository", MAIN), [])

    def test_changed_candidate_sha_rejects_stale_pre_merge_evidence(self) -> None:
        data = request()
        data["originating_pr"]["head_sha"] = "e" * 40  # type: ignore[index]
        self.assertIn("stale", " ".join(reconcile(data)["findings"]))

    def test_unrelated_main_content_blocks_reconciliation(self) -> None:
        data = request()
        data["originating_pr"]["main_changed_files"] = ["one.py", "two.py", "injected.py"]  # type: ignore[index]
        self.assertIn("changed-file", " ".join(reconcile(data)["findings"]))

    def test_missing_provenance_and_direct_push_fail_closed(self) -> None:
        data = request()
        data.pop("originating_pr")
        self.assertEqual(reconcile(data)["decision"], "POST_MERGE_RELEASE_EVIDENCE_NOT_QUALIFIED")

    def test_missing_trusted_delivery_owner_authorization_main_ci_and_coverage_fail_closed(self) -> None:
        data = request()
        data["pre_merge"]["trusted_delivery"] = "MISSING"  # type: ignore[index]
        data["pre_merge"]["owner_authorization"] = "MISSING"  # type: ignore[index]
        data["post_merge"]["ci"] = "MISSING"  # type: ignore[index]
        data["post_merge"]["coverage_report_sha"] = PR  # type: ignore[index]
        findings = " ".join(reconcile(data)["findings"])
        self.assertIn("trusted_delivery", findings)
        self.assertIn("owner authorization", findings)
        self.assertIn("post-merge ci", findings)
        self.assertIn("coverage", findings)

    def test_evidence_validation_rejects_pr_only_or_other_sha(self) -> None:
        evidence = reconcile(request())
        self.assertIn("main SHA", " ".join(validate_release_evidence(evidence, "example/repository", PR)))
        pr_only = copy.deepcopy(evidence)
        pr_only["main_sha"] = PR
        self.assertIn("incorrectly claims", " ".join(validate_release_evidence(pr_only, "example/repository", PR)))

    def test_reconciliation_is_idempotent_for_same_read_back(self) -> None:
        self.assertEqual(reconcile(request()), reconcile(request()))
