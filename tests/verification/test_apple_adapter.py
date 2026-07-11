"""Tests for the Apple Verification Adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.verification.adapters import AdapterRegistry
from tools.verification.apple_adapter import (
    AppleAdapterConfig,
    AppleRuntimeTarget,
    AppleVerificationAdapter,
    parse_simctl_devices,
)
from tools.verification.environment.platforms import AppleDevelopmentEnvironment
from tools.verification.models import PrimitiveAction, Scenario
from tools.verification.scenario.engine import ScenarioEngine


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], tuple[int, str]] | None = None) -> None:
        self.responses = responses or {}
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...], *, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
        self.commands.append(command)
        return self.responses.get(command, (0, "ok"))


SIMCTL_JSON = json.dumps(
    {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-0": [
                {
                    "name": "iPhone 17",
                    "udid": "SIM-IPHONE",
                    "state": "Booted",
                    "isAvailable": True,
                }
            ],
            "com.apple.CoreSimulator.SimRuntime.watchOS-26-0": [
                {
                    "name": "Apple Watch",
                    "udid": "SIM-WATCH",
                    "state": "Shutdown",
                    "isAvailable": True,
                }
            ],
        }
    }
)


class AppleAdapterTests(unittest.TestCase):
    def test_simulator_discovery_parses_simctl_json(self) -> None:
        devices = parse_simctl_devices(SIMCTL_JSON)

        self.assertEqual(2, len(devices))
        self.assertEqual("SIM-IPHONE", devices[0]["udid"])
        self.assertEqual("ios", devices[0]["variant"])
        self.assertTrue(devices[0]["booted"])
        self.assertEqual("watchos", devices[1]["variant"])

    def test_adapter_discovers_simulators_with_mocked_runner(self) -> None:
        runner = FakeRunner({("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_JSON)})
        adapter = AppleVerificationAdapter(AppleAdapterConfig(), runner=runner)

        result = adapter.discover_simulators()

        self.assertTrue(result.ok)
        self.assertEqual("SIM-IPHONE", result.data["devices"][0]["udid"])
        self.assertIn(("xcrun", "simctl", "list", "devices", "available", "--json"), runner.commands)

    def test_validate_target_identity_fails_closed_without_target(self) -> None:
        adapter = AppleVerificationAdapter(AppleAdapterConfig(), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("AppleTargetUnavailable", result.data["error"])

    def test_physical_device_requires_explicit_opt_in(self) -> None:
        target = AppleRuntimeTarget(target_id="iphone", runtime="physical", variant="ios", udid="DEVICE")
        adapter = AppleVerificationAdapter(AppleAdapterConfig(target=target), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("PhysicalDeviceExecutionNotConfigured", result.data["error"])

    def test_install_launch_terminate_use_simctl_primitives(self) -> None:
        target = AppleRuntimeTarget(
            target_id="iphone-sim",
            runtime="simulator",
            variant="ios",
            udid="SIM-IPHONE",
            bundle_id="dev.djconnect.ios",
            app_path=Path("/tmp/DJConnect.app"),
        )
        runner = FakeRunner()
        adapter = AppleVerificationAdapter(AppleAdapterConfig(target=target), runner=runner)

        install = adapter.install_app()
        launch = adapter.launch_app()
        terminate = adapter.terminate_app()

        self.assertTrue(install.ok)
        self.assertTrue(launch.ok)
        self.assertTrue(terminate.ok)
        self.assertIn(("xcrun", "simctl", "install", "SIM-IPHONE", "/tmp/DJConnect.app"), runner.commands)
        self.assertIn(("xcrun", "simctl", "launch", "SIM-IPHONE", "dev.djconnect.ios"), runner.commands)
        self.assertIn(("xcrun", "simctl", "terminate", "SIM-IPHONE", "dev.djconnect.ios"), runner.commands)

    def test_screenshot_requires_evidence_directory(self) -> None:
        target = AppleRuntimeTarget(target_id="iphone-sim", runtime="simulator", variant="ios", udid="SIM-IPHONE")
        adapter = AppleVerificationAdapter(AppleAdapterConfig(target=target), runner=FakeRunner())

        result = adapter.capture_screenshot("PROFILE-001")

        self.assertFalse(result.ok)
        self.assertEqual("EvidenceDirectoryUnavailable", result.data["error"])

    def test_screenshot_records_evidence_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = AppleRuntimeTarget(target_id="iphone-sim", runtime="simulator", variant="ios", udid="SIM-IPHONE")
            adapter = AppleVerificationAdapter(
                AppleAdapterConfig(target=target, evidence_dir=Path(tmp)),
                runner=FakeRunner(),
            )

            result = adapter.capture_screenshot("PROFILE-001")

            self.assertTrue(result.ok)
            self.assertEqual(1, len(result.evidence))
            self.assertEqual("screenshot", result.evidence[0].kind)

    def test_redacts_sensitive_operation_arguments(self) -> None:
        adapter = AppleVerificationAdapter(AppleAdapterConfig(), runner=FakeRunner())

        result = adapter.execute_action(PrimitiveAction("unknown", {"token": "secret-token"}))

        self.assertFalse(result.ok)
        self.assertNotIn("secret-token", str(result.data))

    def test_scenario_engine_executes_apple_only_scenario_through_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_path = Path(tmp) / "DJConnect.app"
            app_path.write_text("fixture", encoding="utf-8")
            target = AppleRuntimeTarget(
                target_id="iphone-sim",
                runtime="simulator",
                variant="ios",
                udid="SIM-IPHONE",
                bundle_id="dev.djconnect.ios",
                app_path=app_path,
            )
            registry = AdapterRegistry()
            registry.register(AppleVerificationAdapter(AppleAdapterConfig(target=target), runner=FakeRunner({
                ("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_JSON),
            })))
            scenario = Scenario(
                id="APPLE-UNIT-001",
                title="Apple adapter primitive smoke",
                description="Adapter-only smoke test fixture.",
                category="Capabilities",
                priority="P1",
                verification_level="V4",
                automation_level="automated",
                required_components=("Apple",),
                raw={
                    "supported_platforms": ["iOS"],
                    "requires": {"capabilities": ["apple.runtime"]},
                },
            )

            result = ScenarioEngine(registry).execute([scenario])[0]

            self.assertEqual("PASS", result.state)
            self.assertIn("Apple adapter", result.message)

    def test_execution_environment_summarizes_simulator_metadata(self) -> None:
        runner = FakeRunner(
            {
                ("xcodebuild", "-version"): (0, "Xcode 26.0\nBuild version 17A1"),
                ("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_JSON),
            }
        )

        platform = AppleDevelopmentEnvironment(runner).simulators()

        self.assertEqual("available", platform.state)
        self.assertEqual("SIM-IPHONE", platform.metadata["devices"][0]["udid"])


if __name__ == "__main__":
    unittest.main()
