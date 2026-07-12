"""Tests for the Verification Execution Environment."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.verification.cli import main
from tools.verification.config import load_config
from tools.verification.environment import (
    CleanupManager,
    DependencyInspector,
    GitHubInspector,
    HomeAssistantEnvironment,
    RunIdentityManager,
    ToolchainInspector,
    VerificationExecutionEnvironment,
)
from tools.verification.environment.cleanup import CleanupTarget
from tools.verification.environment.execution import _requires_docker_runtime, _requires_home_assistant
from tools.verification.environment.host_preflight import HostPreflight, HostPreflightConfig
from tools.verification.environment.platforms import CommandRunner
from tools.verification.environment.runtime_image import RuntimeImagePuller
from tools.verification.hygiene import RepositoryHygiene
from tools.verification.models import CleanupMode, GateState, ResourceState, Scenario


class FakeRunner(CommandRunner):
    def __init__(self, code: int = 0, output: str = "ok") -> None:
        self.code = code
        self.output = output
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...], *, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
        self.commands.append(command)
        return self.code, self.output


class FakeDocker:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok
        self.commands: list[tuple[str, ...]] = []

    def run(self, *args: str, env: dict[str, str] | None = None, timeout: int = 30):
        from tools.verification.environment.docker_ha import DockerCommandResult

        self.commands.append(tuple(args))
        return DockerCommandResult(
            self.ok,
            stdout="pulled" if self.ok else "",
            stderr="" if self.ok else "pull failed",
            returncode=0 if self.ok else 1,
        )


class ExecutionEnvironmentTests(unittest.TestCase):
    def test_run_identity_is_traceable_and_unique(self) -> None:
        scenario = Scenario(
            id="PROFILE-001",
            title="Profile",
            description="Profile",
            category="Profiles",
            priority="P0",
            verification_level="V2",
            automation_level="FULL",
            required_components=("HA",),
            raw={},
        )

        first = RunIdentityManager().create([scenario])
        second = RunIdentityManager().create([scenario])

        self.assertNotEqual(first.run_id, second.run_id)
        self.assertEqual(("PROFILE-001",), first.scenario_ids)
        self.assertTrue(first.artifact_prefix.startswith(first.run_id))

    def test_toolchain_inspector_reports_missing_without_failure(self) -> None:
        info = ToolchainInspector().inspect("definitely_missing", ("definitely-missing-tool", "--version"))

        self.assertEqual(ResourceState.MISSING, info.state)
        self.assertIsNone(info.executable)

    def test_dependency_inspector_finds_manifest_and_lockfile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "package.json").write_text(
                json.dumps({"dependencies": {"a": "1.0.0"}, "devDependencies": {"b": "2.0.0"}}),
                encoding="utf-8",
            )
            (root / "package-lock.json").write_text("{}", encoding="utf-8")

            inspections = DependencyInspector().inspect(root)

            self.assertEqual(1, len(inspections))
            self.assertEqual("npm", inspections[0].ecosystem)
            self.assertEqual(2, inspections[0].package_count)
            self.assertEqual(root / "package-lock.json", inspections[0].lockfile)

    def test_runtime_image_puller_downloads_published_docker_hub_image(self) -> None:
        docker = FakeDocker()

        gate = RuntimeImagePuller(docker).pull()

        self.assertEqual(GateState.PASS, gate.state)
        self.assertEqual(("pull", "pcvantol/djconnect-verification-platform:1.0.0"), docker.commands[0])
        self.assertEqual("pcvantol/djconnect-verification-platform:1.0.0", gate.metadata["reference"])

    def test_github_workflow_discovery_is_local_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workflow_dir = root / ".github/workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "validate.yml").write_text("name: Validate\non:\n  pull_request:\n", encoding="utf-8")

            workflows = GitHubInspector(root).workflows()

            self.assertEqual(1, len(workflows))
            self.assertEqual("Validate", workflows[0].name)
            self.assertIn("pull_request", workflows[0].triggers)

    def test_cleanup_blocks_destructive_targets_without_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "danger"
            target.mkdir()
            manager = CleanupManager(root)

            gate = manager.clean(
                dry_run=False,
                targets=(CleanupTarget("danger", target, destructive=True),),
            )

            self.assertEqual(GateState.WARNING, gate.state)
            self.assertTrue(target.exists())

    def test_cleanup_removes_soft_targets_when_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "soft"
            target.mkdir()
            manager = CleanupManager(root)

            gate = manager.clean(
                mode=CleanupMode.SOFT,
                dry_run=False,
                targets=(CleanupTarget("soft", target),),
            )

            self.assertEqual(GateState.PASS, gate.state)
            self.assertFalse(target.exists())

    def test_platform_controller_only_reports_environment_state(self) -> None:
        env = HomeAssistantEnvironment(FakeRunner())
        state = env.health("http://localhost:8123")

        self.assertEqual("home_assistant", state.name)
        self.assertFalse(state.metadata["adapter_logic"])

    def test_execution_environment_prepare_collects_metadata_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            secrets = root / "secrets.json"
            secrets.write_text(json.dumps({"ha_token": "super-secret"}), encoding="utf-8")
            config = load_config(root, secrets_file=secrets)

            prepared = VerificationExecutionEnvironment(config).prepare([])

            self.assertIn("run_identity", prepared)
            self.assertIn("snapshot", prepared)
            self.assertIn("toolchains", prepared)
            self.assertEqual(["ha_token"], prepared["gates"][-1]["metadata"]["names"])
            self.assertNotIn("super-secret", repr(prepared))

    def test_apple_only_scenario_does_not_require_ha_or_docker_gates(self) -> None:
        scenario = Scenario(
            id="APPLE-001",
            title="Apple",
            description="Apple",
            category="Capabilities",
            priority="P0",
            verification_level="V4",
            automation_level="ENVIRONMENT_DEPENDENT",
            required_components=("Apple",),
            raw={
                "supported_platforms": ["iOS"],
                "requires": {"capabilities": ["apple.runtime", "evidence.storage"]},
            },
        )

        self.assertFalse(_requires_home_assistant([scenario]))
        self.assertFalse(_requires_docker_runtime([scenario]))

    def test_home_assistant_scenario_requires_ha_gates(self) -> None:
        scenario = Scenario(
            id="PROFILE-001",
            title="Profile",
            description="Profile",
            category="Profiles",
            priority="P0",
            verification_level="V2",
            automation_level="FULL",
            required_components=("HA",),
            raw={
                "supported_platforms": ["Home Assistant"],
                "requires": {"capabilities": ["ha.runtime", "djconnect.loaded"]},
            },
        )

        self.assertTrue(_requires_home_assistant([scenario]))
        self.assertFalse(_requires_docker_runtime([scenario]))

    def test_host_preflight_passes_with_free_port_and_disk(self) -> None:
        usage = Mock(free=30 * 1024 * 1024 * 1024, total=100 * 1024 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "tools.verification.environment.host_preflight.shutil.disk_usage",
            return_value=usage,
        ), patch("tools.verification.environment.host_preflight._port_bind_available", return_value=True), patch(
            "tools.verification.environment.host_preflight._lsof",
            return_value=[],
        ), patch("tools.verification.environment.host_preflight._process_check", return_value=[]):
            gate = HostPreflight(Path(temp_dir), HostPreflightConfig(ports=(18123,), lab_root=Path(temp_dir))).check()

        self.assertEqual(GateState.PASS, gate.state)

    def test_host_preflight_blocks_port_process_and_disk_conflicts(self) -> None:
        usage = Mock(free=1 * 1024 * 1024 * 1024, total=100 * 1024 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "tools.verification.environment.host_preflight.shutil.disk_usage",
            return_value=usage,
        ), patch("tools.verification.environment.host_preflight._port_bind_available", return_value=False), patch(
            "tools.verification.environment.host_preflight._lsof",
            return_value=[{"command": "Python", "pid": "123", "name": "127.0.0.1:18123"}],
        ), patch(
            "tools.verification.environment.host_preflight._process_check",
            return_value=[{"pid": "456", "command": "hass --config ./config", "blocking": True}],
        ):
            gate = HostPreflight(Path(temp_dir), HostPreflightConfig(ports=(18123,), lab_root=Path(temp_dir))).check()

        self.assertEqual(GateState.FAIL, gate.state)
        self.assertFalse(gate.metadata["disk"]["ok"])
        self.assertTrue(gate.metadata["ports"][0]["blocked"])
        self.assertTrue(gate.metadata["processes"][0]["blocking"])

    def test_repository_hygiene_exposes_fetch_and_prune_dry_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            hygiene = RepositoryHygiene(Path(temp_dir))

            self.assertEqual(GateState.PASS, hygiene.fetch(dry_run=True).state)
            self.assertEqual(GateState.PASS, hygiene.prune(dry_run=True).state)

    def test_cli_prepare_and_restore_use_existing_cli_namespace(self) -> None:
        root = Path(__file__).resolve().parents[2]

        self.assertEqual(0, main(["--root", str(root), "prepare", "--scenario-id", "PROFILE-001"]))
        self.assertEqual(0, main(["--root", str(root), "restore"]))

    def test_config_accepts_future_beta_test_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_config(Path(temp_dir), overrides={"test_mode": "future_beta"})

        self.assertEqual("future_beta", config.test_mode)

    def test_config_enables_parallel_by_default_with_dynamic_cpu_workers(self) -> None:
        def fake_run(command, **kwargs):
            values = {
                ("sysctl", "-n", "hw.perflevel0.physicalcpu"): "10\n",
                ("sysctl", "-n", "hw.perflevel1.physicalcpu"): "4\n",
            }
            return Mock(returncode=0, stdout=values[tuple(command)])

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "tools.verification.configuration.loader.os.cpu_count",
            return_value=16,
        ), patch("tools.verification.configuration.loader.subprocess.run", side_effect=fake_run):
            config = load_config(Path(temp_dir))

        self.assertTrue(config.parallel_execution)
        self.assertEqual(16, config.parallel_workers)

    def test_config_can_disable_parallel_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_config(Path(temp_dir), overrides={"parallel_execution": "false"})

        self.assertFalse(config.parallel_execution)
        self.assertEqual(1, config.parallel_workers)

    def test_config_uses_logical_cpu_fallback_when_perflevel_metadata_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "tools.verification.configuration.loader.os.cpu_count",
            return_value=12,
        ), patch("tools.verification.configuration.loader.subprocess.run", return_value=Mock(returncode=1, stdout="")):
            config = load_config(Path(temp_dir))

        self.assertTrue(config.parallel_execution)
        self.assertEqual(10, config.parallel_workers)

    def test_cli_config_reports_parallel_defaults_and_no_parallel_override(self) -> None:
        root = Path(__file__).resolve().parents[2]

        def fake_run(command, **kwargs):
            values = {
                ("sysctl", "-n", "hw.perflevel0.physicalcpu"): "8\n",
                ("sysctl", "-n", "hw.perflevel1.physicalcpu"): "4\n",
            }
            return Mock(returncode=0, stdout=values[tuple(command)])

        with patch("tools.verification.configuration.loader.os.cpu_count", return_value=12), patch(
            "tools.verification.configuration.loader.subprocess.run",
            side_effect=fake_run,
        ), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(["--root", str(root), "config"]))

        data = json.loads(output.getvalue())
        self.assertTrue(data["parallel_execution"])
        self.assertEqual(12, data["parallel_workers"])
        self.assertEqual("djconnect-verification-platform", data["verification_runtime"]["name"])

        with patch("tools.verification.configuration.loader.os.cpu_count", return_value=12), patch(
            "tools.verification.configuration.loader.subprocess.run",
            side_effect=fake_run,
        ), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(["--root", str(root), "--no-parallel", "config"]))

        disabled = json.loads(output.getvalue())
        self.assertFalse(disabled["parallel_execution"])
        self.assertEqual(1, disabled["parallel_workers"])

    def test_docker_release_dry_run_tags_runtime_and_release_sha(self) -> None:
        root = Path(__file__).resolve().parents[2]

        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(
                0,
                main(
                    [
                        "--root",
                        str(root),
                        "docker",
                        "release",
                        "--image",
                        "example/verification-platform",
                        "--release-sha",
                        "abcdef1234567890",
                        "--dry-run",
                    ]
                ),
            )

        text = output.getvalue()
        self.assertIn("docker build", text)
        self.assertIn("VERIFICATION_RUNTIME_VERSION=1.0.0", text)
        self.assertIn("RELEASE_SHA=abcdef1234567890", text)
        self.assertIn("example/verification-platform:1.0.0", text)
        self.assertIn("example/verification-platform:1.0.0-abcdef123456", text)

    def test_verification_platform_dockerfile_excludes_repository_scenarios(self) -> None:
        root = Path(__file__).resolve().parents[2]
        dockerfile = root / "docker/verification-platform/Dockerfile"
        dockerignore = root / "docker/verification-platform/Dockerfile.dockerignore"

        dockerfile_text = dockerfile.read_text(encoding="utf-8")
        dockerignore_text = dockerignore.read_text(encoding="utf-8")

        self.assertIn("COPY tools/verification", dockerfile_text)
        self.assertNotIn("COPY verification", dockerfile_text)
        self.assertIn("verification/scenarios", dockerignore_text)
        self.assertIn("custom_components", dockerignore_text)


if __name__ == "__main__":
    unittest.main()
