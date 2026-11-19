"""Tests for the Voice Assistant Verification Adapter."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.verification.adapters import AdapterRegistry
from tools.verification.models import PrimitiveAction, Scenario
from tools.verification.scenario.engine import ScenarioEngine
from tools.verification.voice_assistant_adapter import (
    VoiceAssistantAdapterConfig,
    VoiceAssistantRuntimeTarget,
    VoiceAssistantVerificationAdapter,
)


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], tuple[int, str]] | None = None) -> None:
        self.responses = responses or {}
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...], *, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
        self.commands.append(command)
        return self.responses.get(command, (0, "ok"))


class VoiceAssistantAdapterTests(unittest.TestCase):
    def test_validate_target_identity_fails_closed_without_target(self) -> None:
        adapter = VoiceAssistantVerificationAdapter(VoiceAssistantAdapterConfig(), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("VoiceAssistantTargetUnavailable", result.data["error"])

    def test_live_target_requires_explicit_opt_in(self) -> None:
        target = VoiceAssistantRuntimeTarget(target_id="voice-preview", runtime="live", ha_url="http://ha.local:8123")
        adapter = VoiceAssistantVerificationAdapter(VoiceAssistantAdapterConfig(target=target), runner=FakeRunner())

        result = adapter.validate_target_identity()

        self.assertFalse(result.ok)
        self.assertEqual("LiveVoiceAssistantExecutionNotConfigured", result.data["error"])

    def test_local_target_collects_metadata_health_and_logs(self) -> None:
        target = VoiceAssistantRuntimeTarget(
            target_id="voice-local",
            runtime="local",
            endpoint_id="assist-satellite-1",
            assist_pipeline_id="preferred",
            metadata_command="printf metadata",
            health_command="printf healthy",
            log_command="printf logs",
        )
        runner = FakeRunner()
        adapter = VoiceAssistantVerificationAdapter(VoiceAssistantAdapterConfig(target=target), runner=runner)

        metadata = adapter.collect_assist_metadata()
        probe = adapter.probe_voice_endpoint()
        logs = adapter.collect_logs()

        self.assertTrue(metadata.ok)
        self.assertTrue(probe.ok)
        self.assertGreaterEqual(len(logs), 1)
        self.assertTrue(any(log.get("source") == "voice_assistant_log_command" for log in logs if isinstance(log, dict)))
        self.assertIn(("printf", "metadata"), runner.commands)
        self.assertIn(("printf", "healthy"), runner.commands)
        self.assertIn(("printf", "logs"), runner.commands)

    def test_redacts_sensitive_operation_arguments(self) -> None:
        adapter = VoiceAssistantVerificationAdapter(VoiceAssistantAdapterConfig(), runner=FakeRunner())

        result = adapter.execute_action(PrimitiveAction("unknown", {"raw_audio": "private-bytes"}))

        self.assertFalse(result.ok)
        self.assertNotIn("private-bytes", str(result.data))

    def test_scenario_engine_executes_voice_scenario_through_adapter(self) -> None:
        target = VoiceAssistantRuntimeTarget(target_id="voice-local", runtime="local")
        registry = AdapterRegistry()
        registry.register(VoiceAssistantVerificationAdapter(VoiceAssistantAdapterConfig(target=target), runner=FakeRunner()))
        scenario = Scenario(
            id="VOICE-UNIT-001",
            title="Voice adapter primitive smoke",
            description="Adapter-only smoke test fixture.",
            category="Identity",
            priority="P0",
            verification_level="V3",
            automation_level="environment_dependent",
            required_components=("HA", "Voice Endpoint"),
            raw={
                "supported_platforms": ["Home Assistant", "Voice Endpoint"],
                "requires": {"capabilities": ["ha.runtime", "voice_endpoint.runtime", "ha.logs"]},
            },
        )

        result = ScenarioEngine(registry).execute([scenario])[0]

        self.assertEqual("PASS", result.state)
        self.assertIn("Voice Assistant adapter", result.message)

    def test_missing_target_fails_before_live_mutation(self) -> None:
        registry = AdapterRegistry()
        registry.register(VoiceAssistantVerificationAdapter(VoiceAssistantAdapterConfig(), runner=FakeRunner()))
        scenario = Scenario(
            id="VOICE-UNIT-002",
            title="Voice adapter missing target",
            description="Adapter target must be configured before runtime probes.",
            category="Identity",
            priority="P0",
            verification_level="V3",
            automation_level="environment_dependent",
            required_components=("HA", "Voice Endpoint"),
            raw={
                "supported_platforms": ["Home Assistant", "Voice Endpoint"],
                "requires": {"capabilities": ["voice_endpoint.runtime"]},
            },
        )

        result = ScenarioEngine(registry).execute([scenario])[0]

        self.assertEqual("FAIL", result.state)
        self.assertIn("validate_target_identity", result.message)


if __name__ == "__main__":
    unittest.main()
