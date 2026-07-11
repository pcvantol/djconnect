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
from tools.verification.environment.platforms import CommandRunner
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

        with patch("tools.verification.configuration.loader.os.cpu_count", return_value=12), patch(
            "tools.verification.configuration.loader.subprocess.run",
            side_effect=fake_run,
        ), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(["--root", str(root), "--no-parallel", "config"]))

        disabled = json.loads(output.getvalue())
        self.assertFalse(disabled["parallel_execution"])
        self.assertEqual(1, disabled["parallel_workers"])


if __name__ == "__main__":
    unittest.main()
