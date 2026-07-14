from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RELEASE_DOCS = ROOT / "docs" / "release"


class PrivateNetworkDeploymentRelayPolicyTest(unittest.TestCase):
    @staticmethod
    def _contract_text(path: Path) -> str:
        return " ".join(path.read_text(encoding="utf-8").split())

    def test_deployment_contract_is_manifest_and_checksum_bound(self) -> None:
        contract = self._contract_text(RELEASE_DOCS / "DEPLOYMENT_INPUT_CONTRACT.md")

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
        self.assertIn("mutable selectors such as `latest` are never valid", contract)

    def test_relay_preserves_build_evidence_and_target_boundaries(self) -> None:
        policy = self._contract_text(RELEASE_DOCS / "DEPLOYMENT_WORKFLOW_POLICY.md")

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
        workflow_policy = self._contract_text(RELEASE_DOCS / "PLATFORM_WORKFLOW_SEPARATION_ARCHITECTURE.md")
        runner_policy = self._contract_text(RELEASE_DOCS / "RUNNER_POLICY.md")

        for capability in ("Apple Native Build Runner", "Private-Network Deployment Relay", "Apple Secure Distribution Relay"):
            self.assertIn(capability, workflow_policy)
        for boundary in (
            "Apple build jobs never inherit deployment credentials",
            "private-network relay never inherits Apple signing credentials",
            "secure-distribution relay never inherits Pi SSH, Home Assistant or ESP32 deployment credentials",
        ):
            self.assertIn(boundary, workflow_policy)
        self.assertIn("the two relay capabilities are Deployment-only", runner_policy)

    def test_ha_artifact_does_not_require_distribution_publication(self) -> None:
        evidence_policy = self._contract_text(RELEASE_DOCS / "ARTIFACT_RELEASE_EVIDENCE_POLICY.md")

        self.assertIn("HA integration may use an immutable,", evidence_policy)
        self.assertIn("without a separate GitHub Release", evidence_policy)

    def test_apple_distribution_relay_is_manifest_bound_and_local_only(self) -> None:
        apple = self._contract_text(RELEASE_DOCS / "APPLE_RELEASE_ARCHITECTURE.md")
        relay = self._contract_text(RELEASE_DOCS / "PRIVATE_NETWORK_DEPLOYMENT_RELAY.md")

        for token in (
            "qualified Apple build workflow is the sole source of unsigned artifacts",
            "candidate SHA, manifest ID",
            "SHA-256 checksum",
            "explicitly allowlisted `target_device`",
            "never stored in GitHub secrets, exported, uploaded or included in evidence",
            "TestFlight, App Store and public distribution remain deferred",
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
        runtime = self._contract_text(RELEASE_DOCS / "PLATFORM_RELEASE_RUNTIME_ARCHITECTURE.md")

        for token in ("artifact_id", "artifact_sha256", "target", "cannot create tags", "publish GitHub Releases"):
            self.assertIn(token, runtime)

    def test_apple_watch_is_embedded_companion_validation_not_direct_target(self) -> None:
        apple = self._contract_text(RELEASE_DOCS / "APPLE_RELEASE_ARCHITECTURE.md")
        relay = self._contract_text(RELEASE_DOCS / "PRIVATE_NETWORK_DEPLOYMENT_RELAY.md")

        for target in ("`macbook`", "`iphone`", "`ipad`"):
            self.assertIn(target, apple)
        self.assertIn("paired_watch_validation=required|optional|disabled", apple)
        self.assertIn("not a direct deployment target, separate artifact, release candidate, signing flow or manifest node", apple)
        self.assertIn("not a direct deployment target, separate artifact, separate manifest node", relay)
