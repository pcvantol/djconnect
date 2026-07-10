"""Tests for Phase 9L local Home Assistant verification lab."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verification.config import load_config
from tools.verification.environment.docker_ha import DockerCommandResult, HADockerDiscovery, HALabConfig, HALocalVerificationLab
from tools.verification.environment.github import GitHubInspector
from tools.verification.models import GateState
from tools.verification.scenarios import ScenarioLoader


class FakeDocker:
    def __init__(self, responses: dict[tuple[str, ...], DockerCommandResult]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def run(self, *args: str, env: dict[str, str] | None = None, timeout: int = 30) -> DockerCommandResult:
        self.calls.append(args)
        return self.responses.get(args, DockerCommandResult(False, stderr="missing fake response", returncode=1))


class Phase09LLocalHALabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]

    def test_default_config_uses_canonical_scenario_catalog(self) -> None:
        config = load_config(self.root)

        self.assertEqual((self.root / "verification/scenarios",), config.scenario_paths)
        self.assertGreater(len(ScenarioLoader(config).load()), 200)

    def test_lab_rejects_production_volume_even_with_verification_label(self) -> None:
        fake = _fake_lab_runtime(self.root, mount_source="/Users/example/docker/homeassistant/config")

        gate = HALocalVerificationLab(self.root, fake, _lab_config(self.root)).qualify()

        self.assertEqual(GateState.FAIL, gate.state)
        self.assertFalse(gate.metadata["checks"]["production_volume"]["ok"])

    def test_lab_accepts_labelled_source_mount_as_safe_before_live_auth(self) -> None:
        fake = _fake_lab_runtime(self.root)

        gate = HALocalVerificationLab(self.root, fake, _lab_config(self.root)).qualify()

        self.assertEqual(GateState.FAIL, gate.state)
        self.assertTrue(gate.metadata["checks"]["labels"]["ok"])
        self.assertTrue(gate.metadata["checks"]["source"]["ok"])
        self.assertTrue(gate.metadata["checks"]["safe"]["ok"])
        self.assertFalse(gate.metadata["checks"]["token"]["ok"])

    def test_wrong_source_sha_fails_source_identity(self) -> None:
        inspect = _inspect_payload(self.root, labels={"djconnect.verification": "true", "djconnect.source_sha": "wrong"})
        fake = _fake_with_inspect(inspect)

        gate = HADockerDiscovery(self.root, fake).qualify(expected_name="djconnect-verification-ha", expected_port=18123)

        self.assertEqual(GateState.FAIL, gate.state)
        self.assertFalse(gate.metadata["runtime"]["source_matches_sha"])

    def test_destroy_requires_destructive_opt_in(self) -> None:
        lab = HALocalVerificationLab(self.root, FakeDocker({}), _lab_config(self.root))

        gate = lab.lifecycle("destroy", allow_destructive=False)

        self.assertEqual(GateState.FAIL, gate.state)
        self.assertIn("requires explicit opt-in", gate.message)

    def test_lifecycle_uses_only_dedicated_compose_file(self) -> None:
        config = _lab_config(self.root)
        fake = FakeDocker({("compose", "-f", str(config.compose_file), "stop"): DockerCommandResult(True, stdout="stopped")})
        lab = HALocalVerificationLab(self.root, fake, config)

        gate = lab.lifecycle("stop")

        self.assertEqual(GateState.PASS, gate.state)
        self.assertEqual(("compose", "-f", str(config.compose_file), "stop"), fake.calls[-1])

    def test_github_auth_accepts_gh_token_noninteractive_as_warning(self) -> None:
        inspector = GitHubInspector(self.root)
        with patch("tools.verification.environment.github._gh_status") as status, patch.dict("os.environ", {"GH_TOKEN": "redacted"}):
            status.return_value.returncode = 1
            gate = inspector.auth_status(fix_auth=False, interactive=False)

        self.assertEqual(GateState.WARNING, gate.state)
        self.assertIn("GH_TOKEN present", gate.message)

    def test_lab_metadata_avoids_absolute_repo_paths(self) -> None:
        metadata = HALocalVerificationLab(self.root, FakeDocker({}), _lab_config(self.root)).metadata()

        self.assertEqual("verification/lab/home_assistant/compose.yaml", metadata["compose_file"])
        self.assertFalse(str(metadata["lab_root"]).startswith("/Users/"))


def _lab_config(root: Path) -> HALabConfig:
    temp_root = Path(tempfile.mkdtemp()) / "lab"
    return HALabConfig(
        name="djconnect-verification-ha",
        port=18123,
        image="ghcr.io/home-assistant/home-assistant:stable",
        compose_file=root / "verification/lab/home_assistant/compose.yaml",
        lab_root=temp_root,
        config_dir=temp_root / "config",
        log_path=temp_root / "config/home-assistant.log",
        repo_root=root,
        source_sha=_git_sha(root),
        source_fingerprint="fingerprint",
    )


def _fake_lab_runtime(root: Path, *, mount_source: str | None = None) -> FakeDocker:
    return _fake_with_inspect(_inspect_payload(root, mount_source=mount_source))


def _fake_with_inspect(inspect: dict) -> FakeDocker:
    return FakeDocker(
        {
            ("version", "--format", "{{json .}}"): DockerCommandResult(True, stdout=json.dumps({"Server": {"Version": "29"}})),
            ("compose", "version", "--format", "json"): DockerCommandResult(True, stdout=json.dumps({"version": "5.1.4"})),
            ("ps", "-a", "--format", "{{json .}}"): DockerCommandResult(True, stdout=json.dumps({"ID": "abc"})),
            ("inspect", "abc"): DockerCommandResult(True, stdout=json.dumps([inspect])),
        }
    )


def _inspect_payload(root: Path, *, labels: dict[str, str] | None = None, mount_source: str | None = None) -> dict:
    source = mount_source or str(root / "custom_components/djconnect")
    return {
        "Id": "abcdef123456",
        "Name": "/djconnect-verification-ha",
        "Created": "2026-07-10T00:00:00Z",
        "Image": "sha256:image",
        "Config": {
            "Image": "ghcr.io/home-assistant/home-assistant:stable",
            "Labels": labels or {"djconnect.verification": "true", "djconnect.source_sha": _git_sha(root)},
            "Env": ["TOKEN=secret", "SAFE=value"],
        },
        "State": {"Status": "running", "StartedAt": "2026-07-10T00:01:00Z", "Health": {"Status": "healthy"}},
        "HostConfig": {"NetworkMode": "bridge"},
        "NetworkSettings": {"Ports": {"8123/tcp": [{"HostIp": "0.0.0.0", "HostPort": "18123"}]}},
        "Mounts": [{"Source": source, "Destination": "/config/custom_components/djconnect", "Type": "bind"}],
    }


def _git_sha(root: Path) -> str:
    import subprocess

    return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()


if __name__ == "__main__":
    unittest.main()
