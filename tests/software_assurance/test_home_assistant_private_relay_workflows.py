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
            "APPROVED_TARGET_DEPLOYMENT_OPERATIONAL",
            "private-network-deployment",
            "Verify immutable artifact provenance",
            "Require approved central operational manifest source",
            "home-assistant-private-relay-smoke-v1",
            "Configure restricted Home Assistant OS SSH transport",
            "DJCONNECT_HA_OS_DEPLOY_HOST",
            "StrictHostKeyChecking=yes",
            "sha256sum",
            "ha core check",
            "ha core restart",
            "shasum -a 256",
            "DEPLOYED_PENDING_SMOKE",
        ):
            self.assertIn(token, workflow)

    def test_smoke_is_separate_read_only_operational_evidence(self) -> None:
        workflow = self._workflow("smoke-home-assistant-private-network.yml")

        for token in (
            "deployment_workflow_run:",
            "APPROVED_TARGET_DEPLOYMENT_OPERATIONAL",
            "Download deployment evidence",
            "Read bounded Home Assistant health and installed integration version",
            "Authorization: Bearer $HA_API_TOKEN",
            "Verify Home Assistant is not in Safe Mode",
            "/api/config",
            'home_assistant_safe_mode=%s',
            "Verify a loaded DJConnect configuration entry",
            "/api/config/config_entries/entry",
            'djconnect_entry_states=%s',
            'loaded_djconnect_config_entries=%s',
            "Verify DJConnect route-registration lifecycle marker",
            "DJConnect HTTP endpoints registered",
            "Verify DJConnect HTTP routes are registered",
            "/api/djconnect/v1/status",
            "/api/djconnect/v1/command",
            "/api/djconnect/v1/voice",
            'test "$status" = 401',
            '.success == false and .error == "unauthorized"',
            "Verify authenticated Home Assistant WebSocket handshake",
            "auth_required",
            "auth_ok",
            "http_response, buffered = response.split",
            "received = bytearray(buffered)",
            "Configure restricted Home Assistant OS SSH transport",
            "DJCONNECT_HA_OS_DEPLOY_HOST",
            "Verify bounded Home Assistant OS Core startup and crash health",
            "ha core info --raw",
            '.result == "ok" and (.data.version | type == "string" and length > 0)',
            "ha core logs -n 500",
            "StrictHostKeyChecking=yes",
            '"websocket_result": "PASS"',
            '"djconnect_http_routes_result": "PASS"',
            '"startup_marker_result": "PASS"',
            '"crash_log_result": "PASS"',
            '"final_result": "SMOKE_PASSED"',
        ):
            self.assertIn(token, workflow)

        self.assertNotIn("DJCONNECT_HA_DEPLOY_CONTAINER", workflow)
        self.assertNotIn("docker inspect", workflow)

    def test_recovery_reloads_only_enabled_djconnect_entries(self) -> None:
        workflow = self._workflow("recover-home-assistant-djconnect-entries.yml")

        for token in (
            "reload_djconnect_entries",
            "home_assistant_pi5",
            "private-network-deployment",
            "DJCONNECT_HA_SMOKE_API_URL",
            "/api/config/config_entries/entry",
            '.domain == "djconnect" and .source == "user" and .disabled_by == null',
            "/reload",
            '.require_restart == false',
            "djconnect_reload_entry=%s http_status=%s result=%s",
            '.state == "loaded"',
        ):
            self.assertIn(token, workflow)
