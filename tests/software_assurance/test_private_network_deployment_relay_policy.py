from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RELEASE_DOCS = ROOT / "docs" / "release"


class PrivateNetworkDeploymentRelayPolicyTest(unittest.TestCase):
    def test_deployment_contract_is_manifest_and_checksum_bound(self) -> None:
        contract = (RELEASE_DOCS / "DEPLOYMENT_INPUT_CONTRACT.md").read_text(encoding="utf-8")

        for token in (
            "candidate_sha",
            "platform_version",
            "manifest_id",
            "artifact_id",
            "artifact_sha256",
            "target",
            "release_profile",
            "action",
            "execution_mode",
            "action=deployment",
            "execution_mode=execute",
            "PRIVATE_NETWORK_DEPLOYMENT_NOT_AUTHORIZED",
        ):
            self.assertIn(token, contract)
        self.assertIn("mutable selectors such\nas `latest` are never valid", contract)

    def test_relay_preserves_build_evidence_and_target_boundaries(self) -> None:
        policy = (RELEASE_DOCS / "DEPLOYMENT_WORKFLOW_POLICY.md").read_text(encoding="utf-8")

        for token in (
            "may not compile HA, Pi or ESP32 source",
            "create tags or GitHub Releases",
            "publish artifacts",
            "alter qualification",
            "Home Assistant Update entity",
            "production Home Assistant Pi 5",
            "Each target has separate least-privilege credentials",
            "preserves qualification evidence",
            "redacted deployment evidence",
        ):
            self.assertIn(token, policy)

    def test_workflow_roles_and_credentials_are_isolated(self) -> None:
        workflow_policy = (RELEASE_DOCS / "PLATFORM_WORKFLOW_SEPARATION_ARCHITECTURE.md").read_text(encoding="utf-8")
        runner_policy = (RELEASE_DOCS / "RUNNER_POLICY.md").read_text(encoding="utf-8")

        self.assertIn("separate workflow jobs,\npermissions, secrets and workspaces", workflow_policy)
        self.assertIn("never inherits Apple signing\ncredentials", workflow_policy)
        self.assertIn("not a general-purpose\n   private-network automation runner", runner_policy)

    def test_ha_artifact_does_not_require_distribution_publication(self) -> None:
        evidence_policy = (RELEASE_DOCS / "ARTIFACT_RELEASE_EVIDENCE_POLICY.md").read_text(encoding="utf-8")

        self.assertIn("HA integration may use an immutable,", evidence_policy)
        self.assertIn("without a separate GitHub Release", evidence_policy)
