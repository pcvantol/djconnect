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

    def test_apple_distribution_relay_is_manifest_bound_and_local_only(self) -> None:
        apple = (RELEASE_DOCS / "APPLE_RELEASE_ARCHITECTURE.md").read_text(encoding="utf-8")
        relay = (RELEASE_DOCS / "PRIVATE_NETWORK_DEPLOYMENT_RELAY.md").read_text(encoding="utf-8")

        for token in (
            "qualified Apple build workflow is the sole source of unsigned artifacts",
            "candidate SHA, manifest ID",
            "SHA-256 checksum",
            "explicitly allowlisted `target_device`",
            "never\nstored in GitHub secrets, exported, uploaded or included in evidence",
            "TestFlight, App Store and public distribution remain\ndeferred",
        ):
            self.assertIn(token, apple)
        for token in (
            "Apple Native Build Runner",
            "Private Network Deployment Relay",
            "Apple Secure Distribution Relay",
            "never placed in GitHub secrets, exported, uploaded or included in evidence",
            "cannot compile source, build an IPA or macOS binary",
        ):
            self.assertIn(token, relay)

    def test_runtime_dispatch_contract_contains_artifact_and_target_binding(self) -> None:
        runtime = (RELEASE_DOCS / "PLATFORM_RELEASE_RUNTIME_ARCHITECTURE.md").read_text(encoding="utf-8")

        for token in ("artifact_id", "artifact_sha256", "target", "cannot create tags", "publish GitHub Releases"):
            self.assertIn(token, runtime)
