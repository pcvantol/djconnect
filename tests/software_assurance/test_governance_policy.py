from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.software_assurance.policy import (  # noqa: E402
    PolicyValidationError,
    load_canonical_policy,
    validate_artifact_selection,
    validate_permission_declaration,
    validate_policy,
    validate_repository_override,
    validate_rollout_candidate,
    validate_runner_selection,
    validate_retention_selection,
)


class GovernancePolicyTest(unittest.TestCase):
    def test_canonical_policy_is_valid_and_rollout_is_disabled(self) -> None:
        policy = load_canonical_policy()

        self.assertFalse(policy["ownership"]["workflow_rollout_enabled"])
        self.assertEqual(set(policy["execution_profiles"]), {"economy", "balanced", "release"})
        self.assertEqual(
            set(policy["repository_governance"]["validation"]),
            {
                "policy",
                "workflow",
                "permissions",
                "runner",
                "retention",
                "artifact",
                "repository_rollout",
            },
        )

    def test_policy_rejects_rollout_enablement(self) -> None:
        policy = copy.deepcopy(load_canonical_policy())
        policy["ownership"]["workflow_rollout_enabled"] = True

        with self.assertRaisesRegex(PolicyValidationError, "must not enable workflow rollout"):
            validate_policy(policy)

    def test_rollout_candidate_reports_reusable_governance_failures(self) -> None:
        findings = validate_rollout_candidate(
            {
                "name": "example",
                "execution_profile": "economy",
                "policy_version": "1.0.0",
                "timeout_minutes": 30,
                "permissions": "read-write",
                "action_pinning": "v4",
            }
        )

        self.assertIn("permissions must be explicitly declared and least-privilege", findings)
        self.assertIn("concurrency_group is required", findings)
        self.assertIn("action_pinning must use full_length_commit_sha", findings)

    def test_compliant_candidate_is_accepted(self) -> None:
        findings = validate_rollout_candidate(
            {
                "name": "example",
                "execution_profile": "balanced",
                "policy_version": "1.0.0",
                "timeout_minutes": 30,
                "permissions": {"contents": "read"},
                "concurrency_group": "software-assurance-example-main",
                "action_pinning": "full_length_commit_sha",
            }
        )

        self.assertEqual(findings, [])

    def test_component_validators_reject_unsafe_or_incomplete_metadata(self) -> None:
        self.assertEqual(
            validate_permission_declaration({"actions": "write"}),
            ["permission actions is not approved for write access"],
        )
        self.assertIn(
            "self-hosted runner must be qualified and healthy",
            validate_runner_selection({"type": "self_hosted", "labels": ["docker"]}),
        )
        self.assertEqual(
            validate_retention_selection({"class": "release", "days": 30}),
            ["retention days are outside canonical bounds"],
        )
        self.assertEqual(
            validate_artifact_selection({"category": "build", "redacted": False}),
            ["artifact must be redacted before upload"],
        )
        self.assertEqual(
            validate_repository_override(
                {"reason": "test", "owner": "maintainer", "relaxes": ["permissions"]}
            ),
            ["repository override may not relax: permissions"],
        )
