"""Tests for the Apple Verification Adapter."""

from __future__ import annotations

import json
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verification.adapters import AdapterRegistry
from tools.verification.apple_adapter import (
    AppleAdapterConfig,
    AppleRuntimeTarget,
    AppleVerificationAdapter,
    parse_simctl_devices,
)
from tools.verification.environment.platforms import AppleDevelopmentEnvironment
from tools.verification.apple_toolchain import AppleToolchainMaintenance
from tools.verification.apple_runtime_qualification import AppleRuntimeQualification
from tools.verification.apple_runtime_qualification import latest_ios_simulator_runtime
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

SIMCTL_MULTI_IOS_JSON = json.dumps(
    {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {
                    "name": "iPhone 17",
                    "udid": "SIM-IOS-26-5",
                    "state": "Shutdown",
                    "isAvailable": True,
                }
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-27-0": [
                {
                    "name": "iPhone 17 Pro",
                    "udid": "SIM-IOS-27-0",
                    "state": "Booted",
                    "isAvailable": True,
                }
            ],
        }
    }
)

SIGNING_IDENTITY_OUTPUT = '  1) ABCDEF1234567890 "Apple Distribution: DJConnect Test (TEAM123456)"\n     1 valid identities found'


def _write_distribution_profile(profiles_dir: Path) -> None:
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "DJConnectRelease.plist").write_bytes(
        plistlib.dumps(
            {
                "Name": "DJConnect Release",
                "UUID": "PROFILE-UUID-123",
                "TeamIdentifier": ["TEAM123456"],
                "Entitlements": {
                    "application-identifier": "TEAM123456.dev.djconnect.ios",
                    "aps-environment": "production",
                    "get-task-allow": False,
                },
            }
        )
    )


def _signing_env(profiles_dir: Path) -> dict[str, str]:
    return {
        "DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY": "Apple Distribution: DJConnect Test",
        "DJCONNECT_VERIFICATION_APPLE_TEAM_ID": "TEAM123456",
        "DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID": "dev.djconnect.ios",
        "DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE": "DJConnect Release",
        "DJCONNECT_VERIFICATION_APPLE_PROFILES_DIR": str(profiles_dir),
    }


def _no_cross_device_targets_env() -> dict[str, str]:
    return {"DJCONNECT_VERIFICATION_APPLE_TARGETS_JSON": ""}


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

    def test_phase_10e_runtime_qualification_fails_closed_without_target_and_build_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "djconnect"
            apple_repo = Path(tmp) / "djconnect-app"
            (root / "artifacts" / "verification" / "evidence").mkdir(parents=True)
            (apple_repo / "DJConnectApp.xcodeproj").mkdir(parents=True)
            (apple_repo / "App.entitlements").write_text("<plist/>", encoding="utf-8")
            (apple_repo / "release.sh").write_text("#!/bin/sh\n", encoding="utf-8")

            with patch.dict(
                "os.environ",
                {
                    "DJCONNECT_VERIFICATION_APPLE_TARGET_JSON": "",
                    "DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND": "",
                    "DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA": "",
                    "DJCONNECT_VERIFICATION_APPLE_UI_DRIVER": "",
                    "DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND": "",
                    **_no_cross_device_targets_env(),
                },
                clear=False,
            ):
                result = AppleRuntimeQualification(root, apple_repo=apple_repo).run()

            self.assertEqual("BLOCKED", result.state)
            self.assertFalse(result.broad_scenario_execution_allowed)
            states = {check.name: check.state for check in result.checks}
            self.assertEqual("BLOCKED", states["release_equivalent_build"])
            self.assertEqual("BLOCKED", states["simulator_target"])
            self.assertEqual("SKIPPED", states["physical_device_target"])
            self.assertTrue((Path(result.evidence_dir) / "summary.json").exists())

    def test_latest_ios_simulator_runtime_selects_highest_available_ios_runtime(self) -> None:
        runner = FakeRunner({("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_MULTI_IOS_JSON)})

        runtime = latest_ios_simulator_runtime(runner)

        self.assertIsNotNone(runtime)
        self.assertEqual("27.0", runtime["version"])
        self.assertEqual(["SIM-IOS-27-0"], runtime["udids"])

    def test_phase_10e_runtime_qualification_blocks_non_latest_ios_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "djconnect"
            apple_repo = Path(tmp) / "djconnect-app"
            app_path = Path(tmp) / "DJConnect.app"
            profiles_dir = Path(tmp) / "profiles"
            _write_distribution_profile(profiles_dir)
            (root / "artifacts" / "verification" / "evidence").mkdir(parents=True)
            (apple_repo / "DJConnectApp.xcodeproj").mkdir(parents=True)
            (apple_repo / "App.entitlements").write_text("<plist/>", encoding="utf-8")
            app_path.write_text("fixture", encoding="utf-8")
            target_json = json.dumps(
                {
                    "target_id": "old-ios",
                    "variant": "ios",
                    "runtime": "simulator",
                    "name": "iPhone 17",
                    "udid": "SIM-IOS-26-5",
                    "bundle_id": "dev.djconnect.ios",
                    "app_path": str(app_path),
                }
            )
            with patch.dict(
                "os.environ",
                {
                    "DJCONNECT_VERIFICATION_APPLE_TARGET_JSON": target_json,
                    "DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND": "true",
                    "DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA": str(root / "artifacts" / "verification" / "DerivedData"),
                    "DJCONNECT_VERIFICATION_APPLE_UI_DRIVER": "XCTest",
                    "DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND": "true",
                    **_signing_env(profiles_dir),
                    **_no_cross_device_targets_env(),
                },
                clear=False,
            ), patch("tools.verification.apple_runtime_qualification.CommandRunner", lambda: FakeRunner({
                ("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_MULTI_IOS_JSON),
                ("security", "find-identity", "-v", "-p", "codesigning"): (0, SIGNING_IDENTITY_OUTPUT),
            })):
                result = AppleRuntimeQualification(root, apple_repo=apple_repo).run()

            simulator = next(check for check in result.checks if check.name == "simulator_target")
            self.assertEqual("BLOCKED", simulator.state)
            self.assertIn("latest locally available iOS runtime", simulator.message)

    def test_phase_10e_runtime_qualification_blocks_when_latest_ios_runtime_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "djconnect"
            apple_repo = Path(tmp) / "djconnect-app"
            app_path = Path(tmp) / "DJConnect.app"
            profiles_dir = Path(tmp) / "profiles"
            _write_distribution_profile(profiles_dir)
            (root / "artifacts" / "verification" / "evidence").mkdir(parents=True)
            (apple_repo / "DJConnectApp.xcodeproj").mkdir(parents=True)
            (apple_repo / "App.entitlements").write_text("<plist/>", encoding="utf-8")
            app_path.write_text("fixture", encoding="utf-8")
            target_json = json.dumps(
                {
                    "target_id": "ios-target",
                    "variant": "ios",
                    "runtime": "simulator",
                    "name": "iPhone 17",
                    "udid": "SIM-IOS-27-0",
                    "bundle_id": "dev.djconnect.ios",
                    "app_path": str(app_path),
                }
            )
            with patch.dict(
                "os.environ",
                {
                    "DJCONNECT_VERIFICATION_APPLE_TARGET_JSON": target_json,
                    "DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND": "true",
                    "DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA": str(root / "artifacts" / "verification" / "DerivedData"),
                    "DJCONNECT_VERIFICATION_APPLE_UI_DRIVER": "XCTest",
                    "DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND": "true",
                    **_signing_env(profiles_dir),
                    **_no_cross_device_targets_env(),
                },
                clear=False,
            ), patch("tools.verification.apple_runtime_qualification.CommandRunner", lambda: FakeRunner({
                ("xcrun", "simctl", "list", "devices", "available", "--json"): (1, "simctl failed"),
                ("security", "find-identity", "-v", "-p", "codesigning"): (0, SIGNING_IDENTITY_OUTPUT),
            })):
                result = AppleRuntimeQualification(root, apple_repo=apple_repo).run()

            simulator = next(check for check in result.checks if check.name == "simulator_target")
            self.assertEqual("BLOCKED", simulator.state)
            self.assertIn("could not be determined", simulator.message)

    def test_phase_10e_runtime_qualification_cleans_derived_data_before_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "djconnect"
            apple_repo = Path(tmp) / "djconnect-app"
            app_path = Path(tmp) / "DJConnect.app"
            derived_data = root / "artifacts" / "verification" / "DerivedData"
            stale_file = derived_data / "stale-build-output"
            profiles_dir = Path(tmp) / "profiles"
            _write_distribution_profile(profiles_dir)
            (root / "artifacts" / "verification" / "evidence").mkdir(parents=True)
            derived_data.mkdir(parents=True)
            stale_file.write_text("old", encoding="utf-8")
            (apple_repo / "DJConnectApp.xcodeproj").mkdir(parents=True)
            (apple_repo / "App.entitlements").write_text("<plist/>", encoding="utf-8")
            app_path.write_text("fixture", encoding="utf-8")
            target_json = json.dumps(
                {
                    "target_id": "ios-target",
                    "variant": "ios",
                    "runtime": "simulator",
                    "name": "iPhone 17 Pro",
                    "udid": "SIM-IOS-27-0",
                    "bundle_id": "dev.djconnect.ios",
                    "app_path": str(app_path),
                }
            )
            with patch.dict(
                "os.environ",
                {
                    "DJCONNECT_VERIFICATION_APPLE_TARGET_JSON": target_json,
                    "DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND": f"test ! -e {stale_file}",
                    "DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA": str(derived_data),
                    "DJCONNECT_VERIFICATION_APPLE_UI_DRIVER": "XCTest",
                    "DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND": "true",
                    **_signing_env(profiles_dir),
                    **_no_cross_device_targets_env(),
                },
                clear=False,
            ), patch("tools.verification.apple_runtime_qualification.CommandRunner", lambda: FakeRunner({
                ("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_MULTI_IOS_JSON),
                ("security", "find-identity", "-v", "-p", "codesigning"): (0, SIGNING_IDENTITY_OUTPUT),
            })):
                result = AppleRuntimeQualification(root, apple_repo=apple_repo).run()

            states = {check.name: check.state for check in result.checks}
            derived_check = next(check for check in result.checks if check.name == "derived_data_isolation")
            self.assertEqual("PASS", states["derived_data_isolation"])
            self.assertEqual("PASS", states["distribution_signing_assets"])
            self.assertEqual("PASS", states["release_equivalent_build"])
            self.assertTrue(derived_check.data["cleaned_before_build"])
            self.assertFalse(stale_file.exists())

    def test_phase_10e_runtime_qualification_blocks_without_distribution_signing_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "djconnect"
            apple_repo = Path(tmp) / "djconnect-app"
            app_path = Path(tmp) / "DJConnect.app"
            (root / "artifacts" / "verification" / "evidence").mkdir(parents=True)
            (apple_repo / "DJConnectApp.xcodeproj").mkdir(parents=True)
            (apple_repo / "App.entitlements").write_text("<plist/>", encoding="utf-8")
            app_path.write_text("fixture", encoding="utf-8")
            target_json = json.dumps(
                {
                    "target_id": "ios-target",
                    "variant": "ios",
                    "runtime": "simulator",
                    "name": "iPhone 17 Pro",
                    "udid": "SIM-IOS-27-0",
                    "bundle_id": "dev.djconnect.ios",
                    "app_path": str(app_path),
                }
            )
            with patch.dict(
                "os.environ",
                {
                    "DJCONNECT_VERIFICATION_APPLE_TARGET_JSON": target_json,
                    "DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND": "false",
                    "DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA": str(root / "artifacts" / "verification" / "DerivedData"),
                    "DJCONNECT_VERIFICATION_APPLE_UI_DRIVER": "XCTest",
                    "DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND": "true",
                    "DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY": "",
                    "DJCONNECT_VERIFICATION_APPLE_TEAM_ID": "",
                    "DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID": "",
                    "DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE": "",
                    "DJCONNECT_VERIFICATION_APPLE_PROFILES_DIR": "",
                    **_no_cross_device_targets_env(),
                },
                clear=False,
            ), patch("tools.verification.apple_runtime_qualification.CommandRunner", lambda: FakeRunner({
                ("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_MULTI_IOS_JSON),
            })):
                result = AppleRuntimeQualification(root, apple_repo=apple_repo).run()

            states = {check.name: check.state for check in result.checks}
            signing_check = next(check for check in result.checks if check.name == "distribution_signing_assets")
            self.assertEqual("BLOCKED", states["distribution_signing_assets"])
            self.assertEqual("BLOCKED", states["release_equivalent_build"])
            self.assertIn("DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY", signing_check.data["missing"])

    def test_phase_10e_runtime_qualification_passes_configured_cross_device_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "djconnect"
            apple_repo = Path(tmp) / "djconnect-app"
            app_path = Path(tmp) / "DJConnect.app"
            profiles_dir = Path(tmp) / "profiles"
            _write_distribution_profile(profiles_dir)
            (root / "artifacts" / "verification" / "evidence").mkdir(parents=True)
            (apple_repo / "DJConnectApp.xcodeproj").mkdir(parents=True)
            (apple_repo / "App.entitlements").write_text("<plist/>", encoding="utf-8")
            app_path.write_text("fixture", encoding="utf-8")
            primary_target = {
                "target_id": "ios-27-primary",
                "variant": "ios",
                "runtime": "simulator",
                "name": "iPhone 17 Pro",
                "udid": "SIM-IOS-27-0",
                "bundle_id": "dev.djconnect.ios",
                "app_path": str(app_path),
            }
            cross_targets = [
                primary_target | {"ios_version": "27.0"},
                {
                    "target_id": "ios-26-secondary",
                    "variant": "ios",
                    "runtime": "simulator",
                    "name": "iPhone 17",
                    "udid": "SIM-IOS-26-5",
                    "bundle_id": "dev.djconnect.ios",
                    "app_path": str(app_path),
                    "ios_version": "26.5",
                },
            ]
            with patch.dict(
                "os.environ",
                {
                    "DJCONNECT_VERIFICATION_APPLE_TARGET_JSON": json.dumps(primary_target),
                    "DJCONNECT_VERIFICATION_APPLE_TARGETS_JSON": json.dumps(cross_targets),
                    "DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND": "true",
                    "DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA": str(root / "artifacts" / "verification" / "DerivedData"),
                    "DJCONNECT_VERIFICATION_APPLE_UI_DRIVER": "XCTest",
                    "DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND": "true",
                    **_signing_env(profiles_dir),
                },
                clear=False,
            ), patch("tools.verification.apple_runtime_qualification.CommandRunner", lambda: FakeRunner({
                ("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_MULTI_IOS_JSON),
                ("security", "find-identity", "-v", "-p", "codesigning"): (0, SIGNING_IDENTITY_OUTPUT),
            })):
                result = AppleRuntimeQualification(root, apple_repo=apple_repo).run()

            cross_check = next(check for check in result.checks if check.name == "cross_device_simulator_targets")
            self.assertEqual("PASS", cross_check.state)
            self.assertEqual(2, len(cross_check.data["targets"]))

    def test_phase_10e_runtime_qualification_blocks_missing_cross_device_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "djconnect"
            apple_repo = Path(tmp) / "djconnect-app"
            app_path = Path(tmp) / "DJConnect.app"
            profiles_dir = Path(tmp) / "profiles"
            _write_distribution_profile(profiles_dir)
            (root / "artifacts" / "verification" / "evidence").mkdir(parents=True)
            (apple_repo / "DJConnectApp.xcodeproj").mkdir(parents=True)
            (apple_repo / "App.entitlements").write_text("<plist/>", encoding="utf-8")
            app_path.write_text("fixture", encoding="utf-8")
            primary_target = {
                "target_id": "ios-27-primary",
                "variant": "ios",
                "runtime": "simulator",
                "name": "iPhone 17 Pro",
                "udid": "SIM-IOS-27-0",
                "bundle_id": "dev.djconnect.ios",
                "app_path": str(app_path),
            }
            cross_targets = [
                primary_target | {"ios_version": "27.0"},
                {
                    "target_id": "missing-ios",
                    "variant": "ios",
                    "runtime": "simulator",
                    "name": "Missing iPhone",
                    "udid": "SIM-MISSING",
                    "bundle_id": "dev.djconnect.ios",
                    "app_path": str(app_path),
                    "ios_version": "26.5",
                },
            ]
            with patch.dict(
                "os.environ",
                {
                    "DJCONNECT_VERIFICATION_APPLE_TARGET_JSON": json.dumps(primary_target),
                    "DJCONNECT_VERIFICATION_APPLE_TARGETS_JSON": json.dumps(cross_targets),
                    "DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND": "true",
                    "DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA": str(root / "artifacts" / "verification" / "DerivedData"),
                    "DJCONNECT_VERIFICATION_APPLE_UI_DRIVER": "XCTest",
                    "DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND": "true",
                    **_signing_env(profiles_dir),
                },
                clear=False,
            ), patch("tools.verification.apple_runtime_qualification.CommandRunner", lambda: FakeRunner({
                ("xcrun", "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_MULTI_IOS_JSON),
                ("security", "find-identity", "-v", "-p", "codesigning"): (0, SIGNING_IDENTITY_OUTPUT),
            })):
                result = AppleRuntimeQualification(root, apple_repo=apple_repo).run()

            cross_check = next(check for check in result.checks if check.name == "cross_device_simulator_targets")
            self.assertEqual("BLOCKED", cross_check.state)
            self.assertEqual("SIM-MISSING", cross_check.data["missing"][0]["target"]["udid"])

    def test_apple_toolchain_blocks_xcode_beta_outside_future_beta_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "DJCONNECT_VERIFICATION_TEST_MODE": "stable",
                "DJCONNECT_VERIFICATION_XCODE_CHANNEL": "beta",
                "DJCONNECT_VERIFICATION_XCODE_BETA_DEVELOPER_DIR": str(Path(tmp) / "Xcode-beta.app/Contents/Developer"),
            },
            clear=False,
        ):
            result = AppleToolchainMaintenance(Path(tmp), runner=FakeRunner()).ensure_ios_runtime()

        self.assertEqual("BLOCKED", result.state)
        self.assertEqual("xcode_beta_requires_future_beta_test_mode", result.xcode_selection["reason"])

    def test_apple_toolchain_uses_xcode_beta_tools_in_future_beta_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            developer_dir = Path(tmp) / "Xcode-beta.app/Contents/Developer"
            xcodebuild = str(developer_dir / "usr/bin/xcodebuild")
            xcrun = str(developer_dir / "usr/bin/xcrun")
            runner = FakeRunner(
                {
                    (xcodebuild, "-version"): (0, "Xcode 27.0 beta\nBuild version 18A1"),
                    ("softwareupdate", "--list"): (0, "No new software available."),
                    (xcodebuild, "-downloadPlatform", "iOS"): (0, "downloaded"),
                    (xcrun, "simctl", "list", "devices", "available", "--json"): (0, SIMCTL_MULTI_IOS_JSON),
                }
            )
            with patch.dict(
                "os.environ",
                {
                    "DJCONNECT_VERIFICATION_TEST_MODE": "future_beta",
                    "DJCONNECT_VERIFICATION_XCODE_CHANNEL": "beta",
                    "DJCONNECT_VERIFICATION_XCODE_BETA_DEVELOPER_DIR": str(developer_dir),
                },
                clear=False,
            ):
                result = AppleToolchainMaintenance(Path(tmp), runner=runner).ensure_ios_runtime()

        self.assertEqual("PASS", result.state)
        self.assertEqual("beta", result.xcode_selection["channel"])
        self.assertIn((xcodebuild, "-downloadPlatform", "iOS"), runner.commands)
        self.assertIn((xcrun, "simctl", "list", "devices", "available", "--json"), runner.commands)


if __name__ == "__main__":
    unittest.main()
