"""Tests for the ESP32 Verification Adapter."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.verification.adapters import AdapterRegistry
from tools.verification.esp32_adapter import ESP32AdapterConfig, ESP32RuntimeTarget, ESP32VerificationAdapter
from tools.verification.models import PrimitiveAction, Scenario
from tools.verification.scenario.engine import ScenarioEngine


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], tuple[int, str]] | None = None) -> None:
        self.responses = responses or {}
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...], *, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
        self.commands.append(command)
        return self.responses.get(command, (0, "ok"))


class ESP32AdapterTests(unittest.TestCase):
    def test_validate_target_identity_fails_closed_without_target(self) -> None:
        adapter = ESP32VerificationAdapter(ESP32AdapterConfig(), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("ESP32TargetUnavailable", result.data["error"])

    def test_serial_target_requires_explicit_opt_in(self) -> None:
        target = ESP32RuntimeTarget(target_id="esp", runtime="serial", serial_port="/dev/tty.usbmodem101")
        adapter = ESP32VerificationAdapter(ESP32AdapterConfig(target=target), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("LiveSerialExecutionNotConfigured", result.data["error"])

    def test_local_build_reset_and_logs_use_configured_commands(self) -> None:
        target = ESP32RuntimeTarget(
            target_id="esp-local",
            runtime="local",
            build_command="true",
            reset_command="false",
            serial_command="printf ok",
        )
        runner = FakeRunner({("false",): (0, "reset")})
        adapter = ESP32VerificationAdapter(ESP32AdapterConfig(target=target), runner=runner)

        build = adapter.build_firmware()
        logs = adapter.collect_logs()
        reset = adapter.reset_device()

        self.assertTrue(build.ok)
        self.assertTrue(reset.ok)
        self.assertGreaterEqual(len(logs), 1)
        self.assertTrue(any(log.get("source") == "esp32_serial_log_command" for log in logs if isinstance(log, dict)))
        self.assertIn(("true",), runner.commands)
        self.assertIn(("printf", "ok"), runner.commands)
        self.assertIn(("false",), runner.commands)

    def test_flash_requires_destructive_opt_in(self) -> None:
        target = ESP32RuntimeTarget(target_id="esp-local", runtime="local", flash_command="pio run --target upload")
        adapter = ESP32VerificationAdapter(ESP32AdapterConfig(target=target), runner=FakeRunner())

        result = adapter.flash_firmware()

        self.assertFalse(result.ok)
        self.assertEqual("DestructiveExecutionNotConfigured", result.data["error"])

    def test_redacts_sensitive_operation_arguments(self) -> None:
        adapter = ESP32VerificationAdapter(ESP32AdapterConfig(), runner=FakeRunner())

        result = adapter.execute_action(PrimitiveAction("unknown", {"token": "secret-token"}))

        self.assertFalse(result.ok)
        self.assertNotIn("secret-token", str(result.data))

    def test_scenario_engine_executes_esp32_scenario_through_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            firmware_path = Path(tmp) / "firmware.bin"
            firmware_path.write_text("fixture", encoding="utf-8")
            target = ESP32RuntimeTarget(
                target_id="djconnect-lilygo-t-embed-s3-ABCDEF123456",
                runtime="local",
                app_path=firmware_path,
                reset_command="true",
                serial_command="printf ok",
            )
            registry = AdapterRegistry()
            registry.register(ESP32VerificationAdapter(ESP32AdapterConfig(target=target), runner=FakeRunner()))
            scenario = Scenario(
                id="ESP-UNIT-001",
                title="ESP32 adapter primitive smoke",
                description="Adapter-only smoke test fixture.",
                category="Hardware",
                priority="P1",
                verification_level="V5",
                automation_level="semi_automated",
                required_components=("ESP32",),
                raw={
                    "supported_platforms": ["ESP32"],
                    "requires": {"capabilities": ["esp32.runtime", "esp32.logs"]},
                },
            )

            result = ScenarioEngine(registry).execute([scenario])[0]

            self.assertEqual("PASS", result.state)
            self.assertIn("ESP32 adapter", result.message)


if __name__ == "__main__":
    unittest.main()
