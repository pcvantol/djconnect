from __future__ import annotations

import copy
import unittest

from tools.trusted_delivery.evidence_preservation import (
    EvidencePreservationError,
    build_record,
    publication_asset_name,
    validate_record,
)


SHA = "a" * 40
POLICY = "b" * 40
DIGEST = "c" * 64


def source() -> dict[str, object]:
    return {
        "repository": "example/djconnect",
        "repository_role": "active_source",
        "main_sha": SHA,
        "decision": "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED",
        "evidence_digest": DIGEST,
        "pre_merge": {
            "verification": "PASS", "software_assurance": "PASS",
            "trusted_delivery": "PASS", "workflow_integrity": "PASS",
            "required_checks": "PASS",
        },
        "post_merge": {
            "sha": SHA, "ci": "PASS", "tests": "PASS", "lint": "PASS",
            "static_analysis": "PASS", "build_validation": "PASS",
            "governance": "PASS", "coverage": "PASS",
            "coverage_report_sha": SHA, "coverage_artifact_sha": "d" * 64,
            "workflow_run_ids": ["123"],
        },
    }


class EvidencePreservationTest(unittest.TestCase):
    def build(self) -> dict[str, object]:
        return build_record(source(), policy_source_revision=POLICY, timestamp="2026-07-27T00:00:00Z", workflow_run_id="456")

    def test_deterministic_schema_complete_redacted_record(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(validate_record(first), [])
        self.assertEqual(first["redaction"]["status"], "REDACTED")  # type: ignore[index]
        self.assertEqual(first["integrity"]["algorithm"], "sha256-canonical-json")  # type: ignore[index]

    def test_rejects_sensitive_source_content(self) -> None:
        data = source()
        data["repository"] = "example/djconnect?token=synthetic-only"
        with self.assertRaisesRegex(EvidencePreservationError, "forbidden sensitive"):
            build_record(data, policy_source_revision=POLICY, timestamp="2026-07-27T00:00:00Z", workflow_run_id="456")

    def test_missing_check_invalid_status_and_digest_fail_closed(self) -> None:
        data = source()
        data["pre_merge"]["verification"] = "FAIL"  # type: ignore[index]
        with self.assertRaisesRegex(EvidencePreservationError, "verification is not PASS"):
            build_record(data, policy_source_revision=POLICY, timestamp="2026-07-27T00:00:00Z", workflow_run_id="456")
        record = self.build()
        record["integrity"]["digest"] = "0" * 64  # type: ignore[index]
        self.assertIn("integrity digest", " ".join(validate_record(record)))

    def test_append_only_collision_name_is_sha_bound(self) -> None:
        self.assertEqual(publication_asset_name(SHA), f"qualification-evidence-{SHA}.json")
        with self.assertRaises(EvidencePreservationError):
            publication_asset_name("not-a-sha")

    def test_mutated_published_record_is_detected(self) -> None:
        record = copy.deepcopy(self.build())
        record["qualification"]["required_checks"]["post_merge_ci"] = "FAIL"  # type: ignore[index]
        findings = " ".join(validate_record(record))
        self.assertIn("required formal check", findings)
        self.assertIn("integrity digest", findings)
