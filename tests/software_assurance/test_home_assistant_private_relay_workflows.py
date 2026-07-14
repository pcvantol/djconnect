from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


class HomeAssistantPrivateRelayWorkflowTest(unittest.TestCase):
    @staticmethod
    def _workflow(name: str) -> str:
        return " ".join((WORKFLOWS / name).read_text(encoding="utf-8").split())

    def test_deployment_is_typed_artifact_bound_and_refuses_missing_manifest(self) -> None:
        workflow = self._workflow("deploy-home-assistant-private-network.yml")

        for token in (
            "action:",
            "candidate_sha:",
            "execution_mode:",
            "manifest_id:",
            "artifact_id:",
            "artifact_sha256:",
            "target:",
            "home_assistant_pi5",
            "private-network-deployment",
            "Verify immutable artifact provenance",
            "PRIVATE_NETWORK_DEPLOYMENT_NOT_AUTHORIZED",
            "shasum -a 256",
            "DEPLOYED_PENDING_SMOKE",
        ):
            self.assertIn(token, workflow)

    def test_smoke_is_separate_read_only_evidence_and_fails_closed(self) -> None:
        workflow = self._workflow("smoke-home-assistant-private-network.yml")

        for token in (
            "deployment_workflow_run:",
            "Download deployment evidence",
            "Read bounded Home Assistant health",
            "Authorization: Bearer $HA_API_TOKEN",
            '"websocket_result": "NOT_IMPLEMENTED"',
            '"startup_marker_result": "NOT_IMPLEMENTED"',
            '"crash_log_result": "NOT_IMPLEMENTED"',
            '"final_result": "SMOKE_INCONCLUSIVE"',
            "Fail closed until the complete Home Assistant smoke contract exists",
            "exit 1",
        ):
            self.assertIn(token, workflow)
