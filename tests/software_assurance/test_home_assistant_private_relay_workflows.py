from __future__ import annotations

from pathlib import Path
import os
import subprocess
import tempfile
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

    def test_deployment_preserves_previous_integration_outside_components(self) -> None:
        workflow = self._workflow("deploy-home-assistant-private-network.yml")
        self.assertIn(r'backup=\"/config/.djconnect-rollback-${GITHUB_RUN_ID}\"', workflow)
        self.assertIn(r'test ! -e \"\$backup\"', workflow)
        self.assertIn(r'test ! -L \"\$backup\"', workflow)
        self.assertIn(r'mv \"\$target\" \"\$backup\"', workflow)
        self.assertNotIn("-name '.djconnect-pre-*' -exec rm -rf", workflow)
        self.assertNotIn(r'rm -rf \"\$backup\"', workflow)

    def test_swap_and_restart_failures_restore_existing_integration(self) -> None:
        workflow = (WORKFLOWS / "deploy-home-assistant-private-network.yml").read_text()
        start = workflow.index("          test ! -e ", workflow.index("# Keep the previous integration"))
        end = workflow.index('\n      - name: Publish redacted deployment evidence', start)
        script = workflow[start:end].replace("\\", "")
        # The final quote closes the outer ssh command in the actual workflow.
        script = script.rstrip().removesuffix('"')
        for failure in ("none", "swap", "restart", "existing", "symlink", "missing"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); target = root / "target"; stage = root / "stage"; backup = root / "backup"
                target.mkdir(); (target / "version").write_text("old")
                stage.mkdir(); (stage / "version").write_text("new")
                if failure == "existing":
                    backup.mkdir(); (backup / "version").write_text("earlier")
                if failure == "symlink":
                    backup.symlink_to(root / "nonexistent")
                if failure == "missing":
                    (target / "version").unlink(); target.rmdir()
                bindir = root / "bin"; bindir.mkdir()
                mv = bindir / "mv"
                mv.write_text('#!/bin/sh\nif [ "$FAIL" = swap ] && [ "$1" = "$staging" ]; then exit 1; fi\nexec /bin/mv "$@"\n')
                ha = bindir / "ha"
                ha.write_text('#!/bin/sh\nif [ "$FAIL" = restart ] && [ "$2" = restart ] && [ ! -e "$MARKER" ]; then touch "$MARKER"; exit 1; fi\nexit 0\n')
                mv.chmod(0o755); ha.chmod(0o755)
                env = dict(os.environ, PATH=f"{bindir}:/usr/bin:/bin", target=str(target), staging=str(stage), backup=str(backup), FAIL=failure, MARKER=str(root / "marker"))
                result = subprocess.run(["sh", "-eu", "-c", script], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, failure == "none", result.stderr)
                if failure == "missing":
                    self.assertFalse(target.exists())
                else:
                    self.assertEqual((target / "version").read_text(), "new" if failure == "none" else "old")
                if failure == "none":
                    self.assertEqual((backup / "version").read_text(), "old")
                if failure == "existing":
                    self.assertEqual((backup / "version").read_text(), "earlier")

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
            "Error occurred loading flow for integration djconnect",
            "ha core logs -n 5000",
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
