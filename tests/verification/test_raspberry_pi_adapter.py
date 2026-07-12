"""Tests for the Raspberry Pi Verification Adapter."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.verification.adapters import AdapterRegistry
from tools.verification.models import PrimitiveAction, Scenario
from tools.verification.raspberry_pi_adapter import (
    RaspberryPiAdapterConfig,
    RaspberryPiRuntimeTarget,
    RaspberryPiVerificationAdapter,
)
from tools.verification.scenario.engine import ScenarioEngine


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], tuple[int, str]] | None = None) -> None:
        self.responses = responses or {}
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...], *, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
        self.commands.append(command)
        return self.responses.get(command, (0, "ok"))


class RaspberryPiAdapterTests(unittest.TestCase):
    def test_validate_target_identity_fails_closed_without_target(self) -> None:
        adapter = RaspberryPiVerificationAdapter(RaspberryPiAdapterConfig(), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("RaspberryPiTargetUnavailable", result.data["error"])

    def test_ssh_target_requires_explicit_opt_in(self) -> None:
        target = RaspberryPiRuntimeTarget(target_id="pi", runtime="ssh", host="pi.local", user="pi")
        adapter = RaspberryPiVerificationAdapter(RaspberryPiAdapterConfig(target=target), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("LiveSshExecutionNotConfigured", result.data["error"])

    def test_local_launch_stop_and_logs_use_configured_commands(self) -> None:
        target = RaspberryPiRuntimeTarget(
            target_id="pi-local",
            runtime="local",
            launch_command="true",
            stop_command="false",
            log_command="printf ok",
        )
        runner = FakeRunner({("false",): (0, "stopped")})
        adapter = RaspberryPiVerificationAdapter(RaspberryPiAdapterConfig(target=target), runner=runner)

        launch = adapter.launch_app()
        logs = adapter.collect_logs()
        stop = adapter.stop_app()

        self.assertTrue(launch.ok)
        self.assertTrue(stop.ok)
        self.assertGreaterEqual(len(logs), 1)
        self.assertTrue(any(log.get("source") == "raspberry_pi_log_command" for log in logs if isinstance(log, dict)))
        self.assertIn(("true",), runner.commands)
        self.assertIn(("printf", "ok"), runner.commands)
        self.assertIn(("false",), runner.commands)

    def test_ssh_launch_uses_ssh_command_when_enabled(self) -> None:
        target = RaspberryPiRuntimeTarget(
            target_id="pi-live",
            runtime="ssh",
            host="pi.local",
            port=2222,
            user="pi",
            launch_command="systemctl --user start djconnect",
        )
        runner = FakeRunner()
        adapter = RaspberryPiVerificationAdapter(
            RaspberryPiAdapterConfig(target=target, allow_live_ssh=True),
            runner=runner,
        )

        result = adapter.launch_app()

        self.assertTrue(result.ok)
        self.assertIn(("ssh", "-p", "2222", "pi@pi.local", "systemctl --user start djconnect"), runner.commands)

    def test_screenshot_records_evidence_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = RaspberryPiRuntimeTarget(
                target_id="pi-local",
                runtime="local",
                screenshot_command="touch {path}",
            )
            adapter = RaspberryPiVerificationAdapter(
                RaspberryPiAdapterConfig(target=target, evidence_dir=Path(tmp)),
                runner=FakeRunner(),
            )

            result = adapter.capture_screenshot("PI-001")

            self.assertTrue(result.ok)
            self.assertEqual(1, len(result.evidence))
            self.assertEqual("screenshot", result.evidence[0].kind)
            self.assertTrue(str(result.data["path"]).endswith("PI-001.png"))

    def test_redacts_sensitive_operation_arguments(self) -> None:
        adapter = RaspberryPiVerificationAdapter(RaspberryPiAdapterConfig(), runner=FakeRunner())

        result = adapter.execute_action(PrimitiveAction("unknown", {"token": "secret-token"}))

        self.assertFalse(result.ok)
        self.assertNotIn("secret-token", str(result.data))

    def test_scenario_engine_executes_pi_only_scenario_through_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_path = Path(tmp) / "djconnect-pi"
            app_path.write_text("fixture", encoding="utf-8")
            target = RaspberryPiRuntimeTarget(
                target_id="pi-local",
                runtime="local",
                app_path=app_path,
                launch_command="true",
                stop_command="true",
                log_command="printf ok",
            )
            registry = AdapterRegistry()
            registry.register(RaspberryPiVerificationAdapter(RaspberryPiAdapterConfig(target=target), runner=FakeRunner()))
            scenario = Scenario(
                id="PI-UNIT-001",
                title="Pi adapter primitive smoke",
                description="Adapter-only smoke test fixture.",
                category="Capabilities",
                priority="P1",
                verification_level="V4",
                automation_level="automated",
                required_components=("Raspberry Pi",),
                raw={
                    "supported_platforms": ["Raspberry Pi"],
                    "requires": {"capabilities": ["pi.runtime", "pi.logs"]},
                },
            )

            result = ScenarioEngine(registry).execute([scenario])[0]

            self.assertEqual("PASS", result.state)
            self.assertIn("Raspberry Pi adapter", result.message)

    def test_scenario_engine_uses_pi_primitives_for_shared_ha_pi_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_path = Path(tmp) / "djconnect-pi"
            app_path.write_text("fixture", encoding="utf-8")
            registry = AdapterRegistry()
            target = RaspberryPiRuntimeTarget(
                target_id="pi-local",
                runtime="local",
                app_path=app_path,
                launch_command="true",
                stop_command="true",
                log_command="printf ok",
            )
            registry.register(RaspberryPiVerificationAdapter(RaspberryPiAdapterConfig(target=target), runner=FakeRunner()))
            scenario = Scenario(
                id="PI-SHARED-001",
                title="Shared Pi product scenario",
                description="Shared backend/client scenario with explicit Pi runtime surface.",
                category="Profiles",
                priority="P0",
                verification_level="V3",
                automation_level="environment_dependent",
                required_components=("HA", "Pi"),
                raw={
                    "supported_platforms": ["Home Assistant", "Raspberry Pi"],
                    "requires": {
                        "capabilities": [
                            "djconnect.profile_platform",
                            "ha.runtime",
                            "pi.runtime",
                            "evidence.storage",
                        ]
                    },
                },
            )

            plan = ScenarioEngine(registry).plan(scenario)
            action_names = [action.name for action in plan.actions]
            result = ScenarioEngine(registry).execute([scenario])[0]

            self.assertEqual(
                ["collect_environment", "validate_target_identity", "collect_app_metadata", "launch_app", "collect_logs", "stop_app"],
                action_names,
            )
            self.assertEqual("PASS", result.state)
            self.assertIn("Raspberry Pi adapter", result.message)


if __name__ == "__main__":
    unittest.main()
