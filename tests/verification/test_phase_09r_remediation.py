"""Tests for Phase 9R remediation capabilities."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.verification.core.investigator import VerificationInvestigator
from tools.verification.environment.docker_ha import DockerCommandResult, HADockerDiscovery
from tools.verification.environment.github import CI_AUTH_REQUIRED, CI_NO_DATA, CI_PASS, GitHubInspector
from tools.verification.evidence import RunStore, RunStoreError
from tools.verification.models import GateState
from unittest.mock import patch


class FakeDocker:
    def __init__(self, responses: dict[tuple[str, ...], DockerCommandResult]) -> None:
        self.responses = responses

    def run(self, *args: str, env: dict[str, str] | None = None, timeout: int = 30) -> DockerCommandResult:
        return self.responses.get(tuple(args), DockerCommandResult(False, stderr="missing fake response", returncode=1))


class Phase09RRemediationTests(unittest.TestCase):
    def test_docker_discovery_blocks_when_daemon_unavailable(self) -> None:
        discovery = HADockerDiscovery(Path.cwd(), FakeDocker({("version", "--format", "{{json .}}"): DockerCommandResult(False, stderr="daemon down")}))

        gate = discovery.qualify()

        self.assertEqual(GateState.FAIL, gate.state)
        self.assertIn("Docker daemon unavailable", gate.message)

    def test_docker_discovery_rejects_ambiguous_containers(self) -> None:
        root = Path.cwd()
        rows = "\n".join(json.dumps({"ID": item}) for item in ("a", "b"))
        inspect = _inspect_payload(root)
        fake = FakeDocker(
            {
                ("version", "--format", "{{json .}}"): DockerCommandResult(True, stdout=json.dumps({"Server": {"Version": "29"}})),
                ("ps", "-a", "--format", "{{json .}}"): DockerCommandResult(True, stdout=rows),
                ("inspect", "a"): DockerCommandResult(True, stdout=json.dumps([inspect | {"Name": "/djconnect-ha-a", "Id": "a"}])),
                ("inspect", "b"): DockerCommandResult(True, stdout=json.dumps([inspect | {"Name": "/djconnect-ha-b", "Id": "b"}])),
            }
        )

        gate = HADockerDiscovery(root, fake).qualify()

        self.assertEqual(GateState.FAIL, gate.state)
        self.assertIn("Multiple candidate", gate.message)

    def test_docker_discovery_accepts_safe_single_container(self) -> None:
        root = Path.cwd()
        inspect = _inspect_payload(root)
        fake = FakeDocker(
            {
                ("version", "--format", "{{json .}}"): DockerCommandResult(True, stdout=json.dumps({"Server": {"Version": "29"}})),
                ("ps", "-a", "--format", "{{json .}}"): DockerCommandResult(True, stdout=json.dumps({"ID": "abc"})),
                ("inspect", "abc"): DockerCommandResult(True, stdout=json.dumps([inspect])),
            }
        )

        gate = HADockerDiscovery(root, fake).qualify()

        self.assertEqual(GateState.PASS, gate.state)
        self.assertTrue(gate.metadata["runtime"]["safe_for_verification"])

    def test_investigator_classifies_adapter_and_ci_failures(self) -> None:
        results = VerificationInvestigator().investigate_bundle(
            {
                "run_id": "run-1",
                "failures": [
                    {"failure_id": "a", "scenario_id": "PROFILE-001", "message": "websocket_request unavailable"},
                    {"failure_id": "b", "message": "gh auth invalid for CI qualification"},
                ],
            }
        )

        self.assertEqual("ha_adapter_defect", results[0].classification)
        self.assertEqual("ci_qualification_issue", results[1].classification)
        self.assertFalse(results[0].human_review_required)

    def test_investigator_marks_unknown_low_confidence_for_human_review(self) -> None:
        result = VerificationInvestigator().investigate_bundle({"run_id": "run-1", "failures": [{"message": "odd"}]})[0]

        self.assertEqual("unknown", result.classification)
        self.assertTrue(result.human_review_required)

    def test_investigator_extracts_failed_primitive_diagnostics(self) -> None:
        results = VerificationInvestigator().investigate_bundle(
            {
                "run_id": "run-1",
                "scenario_results": [
                    {
                        "scenario_id": "PROFILE-001",
                        "state": "FAIL",
                        "message": "Runtime primitives executed through Home Assistant adapter.",
                        "diagnostics": {
                            "primitive_results": [
                                {"action": "health", "ok": True, "data": {}},
                                {
                                    "action": "http_request",
                                    "ok": False,
                                    "message": "AuthenticationFailed",
                                    "data": {"error": "AuthenticationFailed"},
                                },
                            ]
                        },
                    }
                ],
            }
        )

        self.assertEqual(1, len(results))
        self.assertEqual("PROFILE-001-http_request-2", results[0].failure_id)
        self.assertEqual("execution_environment_defect", results[0].classification)

    def test_run_store_is_immutable_and_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RunStore(Path(temp_dir))
            store.create("run-1")
            store.write_json("run-1", "environment.json", {"api_token": "secret"})
            store.finalize("run-1", state="FAIL")

            with self.assertRaises(RunStoreError):
                store.create("run-1")
            self.assertTrue(store.verify("run-1")["ok"])
            self.assertEqual("djconnect-verification-platform", store.show("run-1")["verification_runtime"]["name"])
            text = (Path(temp_dir) / "run-1" / "environment.json").read_text(encoding="utf-8")
            self.assertIn("[redacted-key]", text)

    def test_run_store_finalize_preserves_existing_summary_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RunStore(Path(temp_dir))
            store.create("run-1")
            store.write_json("run-1", "summary.json", {"run_id": "run-1", "scenario_results": [{"scenario_id": "A-001"}]})

            store.finalize(
                "run-1",
                state="FAIL",
                summary={"result_state": "FAIL", "execution_summary": {"total_execution_seconds": 12.5}},
            )

            summary = store.show("run-1")
            self.assertEqual([{"scenario_id": "A-001"}], summary["scenario_results"])
            self.assertEqual("FAIL", summary["state"])
            self.assertEqual(12.5, summary["execution_summary"]["total_execution_seconds"])
            self.assertEqual("djconnect-verification-platform", summary["verification_runtime"]["name"])

    def test_github_ci_decision_states_from_gh_payloads(self) -> None:
        inspector = GitHubInspector(Path.cwd())
        self.assertEqual(CI_AUTH_REQUIRED, inspector._decision_from_runs(None, "abc")["decision"])
        self.assertEqual(CI_NO_DATA, inspector._decision_from_runs([], "abc")["decision"])
        self.assertEqual(
            CI_PASS,
            inspector._decision_from_runs(
                [{"status": "completed", "conclusion": "success", "headSha": "abc", "name": "ci"}],
                "abc",
            )["decision"],
        )

    def test_github_auth_status_blocks_without_interactive_credentials(self) -> None:
        inspector = GitHubInspector(Path.cwd())
        with patch("tools.verification.environment.github._gh_status") as status:
            status.return_value.returncode = 1
            gate = inspector.auth_status(fix_auth=False, interactive=False)

        self.assertEqual(GateState.FAIL, gate.state)
        self.assertIn("BLOCKED_CI_AUTH", gate.message)


def _inspect_payload(root: Path) -> dict:
    return {
        "Id": "abcdef123456",
        "Name": "/djconnect-homeassistant",
        "Created": "2026-07-10T00:00:00Z",
        "Image": "sha256:image",
        "Config": {
            "Image": "ghcr.io/home-assistant/home-assistant:2026.7.2",
            "Labels": {"djconnect.verification": "true", "djconnect.source_sha": _git_sha(root)},
            "Env": ["TOKEN=secret", "SAFE=value"],
        },
        "State": {"Status": "running", "StartedAt": "2026-07-10T00:01:00Z", "Health": {"Status": "healthy"}},
        "HostConfig": {"NetworkMode": "bridge"},
        "NetworkSettings": {"Ports": {"8123/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8123"}]}},
        "Mounts": [{"Source": str(root), "Destination": "/config/custom_components/djconnect", "Type": "bind"}],
    }


def _git_sha(root: Path) -> str:
    return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()


if __name__ == "__main__":
    unittest.main()
