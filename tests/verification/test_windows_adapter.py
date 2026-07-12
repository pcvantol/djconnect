"""Tests for the Windows Verification Adapter."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.verification.adapters import AdapterRegistry
from tools.verification.models import PrimitiveAction, Scenario
from tools.verification.scenario.engine import ScenarioEngine
from tools.verification.windows_adapter import (
    WindowsAdapterConfig,
    WindowsRuntimeTarget,
    WindowsVerificationAdapter,
)


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], tuple[int, str]] | None = None) -> None:
        self.responses = responses or {}
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...], *, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
        self.commands.append(command)
        return self.responses.get(command, (0, "ok"))


class WindowsAdapterTests(unittest.TestCase):
    def test_validate_target_identity_fails_closed_without_target(self) -> None:
        adapter = WindowsVerificationAdapter(WindowsAdapterConfig(), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("WindowsTargetUnavailable", result.data["error"])

    def test_remote_target_requires_explicit_opt_in(self) -> None:
        target = WindowsRuntimeTarget(target_id="win", runtime="remote", host="win.local", user="Peter")
        adapter = WindowsVerificationAdapter(WindowsAdapterConfig(target=target), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("LiveWindowsRemoteExecutionNotConfigured", result.data["error"])

    def test_local_launch_stop_and_logs_use_configured_commands(self) -> None:
        target = WindowsRuntimeTarget(
            target_id="win-local",
            runtime="local",
            launch_command="true",
            stop_command="false",
            log_command="printf ok",
        )
        runner = FakeRunner({("false",): (0, "stopped")})
        adapter = WindowsVerificationAdapter(WindowsAdapterConfig(target=target), runner=runner)

        launch = adapter.launch_app()
        logs = adapter.collect_logs()
        stop = adapter.stop_app()

        self.assertTrue(launch.ok)
        self.assertTrue(stop.ok)
        self.assertGreaterEqual(len(logs), 1)
        self.assertTrue(any(log.get("source") == "windows_log_command" for log in logs if isinstance(log, dict)))
        self.assertIn(("true",), runner.commands)
        self.assertIn(("printf", "ok"), runner.commands)
        self.assertIn(("false",), runner.commands)

    def test_screenshot_records_evidence_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = WindowsRuntimeTarget(
                target_id="win-local",
                runtime="local",
                screenshot_command="touch {path}",
            )
            adapter = WindowsVerificationAdapter(
                WindowsAdapterConfig(target=target, evidence_dir=Path(tmp)),
                runner=FakeRunner(),
            )

            result = adapter.capture_screenshot("WIN-001")

            self.assertTrue(result.ok)
            self.assertEqual(1, len(result.evidence))
            self.assertEqual("screenshot", result.evidence[0].kind)
            self.assertTrue(str(result.data["path"]).endswith("WIN-001.png"))

    def test_redacts_sensitive_operation_arguments(self) -> None:
        adapter = WindowsVerificationAdapter(WindowsAdapterConfig(), runner=FakeRunner())

        result = adapter.execute_action(PrimitiveAction("unknown", {"token": "secret-token"}))

        self.assertFalse(result.ok)
        self.assertNotIn("secret-token", str(result.data))

    def test_scenario_engine_executes_windows_only_scenario_through_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_path = Path(tmp) / "DJConnect.Windows.exe"
            app_path.write_text("fixture", encoding="utf-8")
            target = WindowsRuntimeTarget(
                target_id="win-local",
                runtime="local",
                app_path=app_path,
                launch_command="true",
                stop_command="true",
                log_command="printf ok",
            )
            registry = AdapterRegistry()
            registry.register(WindowsVerificationAdapter(WindowsAdapterConfig(target=target), runner=FakeRunner()))
            scenario = Scenario(
                id="WIN-UNIT-001",
                title="Windows adapter primitive smoke",
                description="Adapter-only smoke test fixture.",
                category="Capabilities",
                priority="P1",
                verification_level="V4",
                automation_level="automated",
                required_components=("Windows Native ARM64",),
                raw={
                    "supported_platforms": ["Windows ARM64"],
                    "requires": {"capabilities": ["windows.runtime", "windows.logs"]},
                },
            )

            result = ScenarioEngine(registry).execute([scenario])[0]

            self.assertEqual("PASS", result.state)
            self.assertIn("Windows adapter", result.message)

    def test_shared_ha_windows_scenario_does_not_route_to_windows_adapter_only(self) -> None:
        registry = AdapterRegistry()
        registry.register(WindowsVerificationAdapter(WindowsAdapterConfig(), runner=FakeRunner()))
        scenario = Scenario(
            id="WIN-SHARED-001",
            title="Shared HA Windows product scenario",
            description="Shared backend/client scenario that is not Windows-only.",
            category="Profiles",
            priority="P0",
            verification_level="V3",
            automation_level="environment_dependent",
            required_components=("HA", "Windows Native ARM64"),
            raw={
                "supported_platforms": ["Home Assistant", "Windows ARM64"],
                "requires": {"capabilities": ["djconnect.profile_platform", "ha.runtime", "windows.runtime"]},
            },
        )

        result = ScenarioEngine(registry).execute([scenario])[0]

        self.assertEqual("SKIPPED", result.state)
        self.assertNotIn("Windows adapter", result.message)


if __name__ == "__main__":
    unittest.main()
