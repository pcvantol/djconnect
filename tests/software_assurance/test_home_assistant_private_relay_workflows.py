from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


class HomeAssistantPrivateRelayWorkflowTest(unittest.TestCase):
    @staticmethod
    def _workflow(name: str) -> str:
        return " ".join((WORKFLOWS / name).read_text(encoding="utf-8").split())

    def test_deployment_is_typed_artifact_bound_and_requires_manifest(self) -> None:
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
            "Require approved central operational manifest source",
            "home-assistant-private-relay-smoke-v1",
            "shasum -a 256",
            "DEPLOYED_PENDING_SMOKE",
        ):
            self.assertIn(token, workflow)

    def test_smoke_is_separate_read_only_operational_evidence(self) -> None:
        workflow = self._workflow("smoke-home-assistant-private-network.yml")

        for token in (
            "deployment_workflow_run:",
            "Download deployment evidence",
            "Read bounded Home Assistant health and installed integration version",
            "Authorization: Bearer $HA_API_TOKEN",
            "Verify authenticated Home Assistant WebSocket handshake",
            "auth_required",
            "auth_ok",
            "Verify bounded Home Assistant container startup and crash health",
            '"websocket_result": "PASS"',
            '"startup_marker_result": "PASS"',
            '"crash_log_result": "PASS"',
            '"final_result": "SMOKE_PASSED"',
        ):
            self.assertIn(token, workflow)
