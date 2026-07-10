"""Tests for the Home Assistant Verification Adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.verification.adapters import AdapterRegistry
from tools.verification.config import load_config
from tools.verification.execution import ScenarioExecutor
from tools.verification.home_assistant_adapter import (
    HTTPResult,
    HomeAssistantAdapterConfig,
    HomeAssistantVerificationAdapter,
)
from tools.verification.models import ResultState
from tools.verification.scenarios import ScenarioLoader


class MockHomeAssistantTransport:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict | None]] = []

    def request(self, method: str, path: str, payload: dict | None = None, headers: dict | None = None) -> HTTPResult:
        self.requests.append((method, path, payload))
        body = {"message": "ok"}
        if path == "/api/config":
            body = {"version": "2026.7.0", "components": ["djconnect"]}
        return HTTPResult(
            status=200,
            headers={"x-test": "ok", "authorization": "secret"},
            body=body,
            duration_seconds=0.01,
            url=f"http://ha.local{path}",
            method=method,
        )

    def websocket(self, message: dict) -> dict:
        return {
            "success": True,
            "result": {
                "commands": ["djconnect/capabilities"],
                "capabilities": {"profiles": True, "request_context": True},
            },
            "echo": message,
        }


class HomeAssistantAdapterTests(unittest.TestCase):
    def test_health_uses_rest_and_redacts_headers(self) -> None:
        adapter = HomeAssistantVerificationAdapter(
            HomeAssistantAdapterConfig(base_url="http://ha.local", token="secret-token"),
            transport=MockHomeAssistantTransport(),
        )

        result = adapter.execute_rest("GET", "/api/config")

        self.assertTrue(result.ok)
        self.assertEqual(200, result.data["status"])
        self.assertEqual("<redacted>", result.data["headers"]["authorization"])

    def test_fixture_namespace_blocks_non_verification_cleanup(self) -> None:
        adapter = HomeAssistantVerificationAdapter(
            HomeAssistantAdapterConfig(),
            transport=MockHomeAssistantTransport(),
        )

        created = adapter.create_fixture("profile", "PROFILE-001")
        blocked = adapter.remove_fixture("production-profile")

        self.assertTrue(created.ok)
        self.assertFalse(blocked.ok)
        self.assertEqual("FixtureFailed", blocked.data["error"])

    def test_snapshot_storage_allows_only_approved_djconnect_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = Path(temp_dir)
            (storage / "djconnect_profile_platform").write_text(
                json.dumps({"profile_token": "secret", "profiles": []}),
                encoding="utf-8",
            )
            adapter = HomeAssistantVerificationAdapter(
                HomeAssistantAdapterConfig(storage_dir=storage),
                transport=MockHomeAssistantTransport(),
            )

            allowed = adapter.snapshot_storage("djconnect_profile_platform")
            blocked = adapter.snapshot_storage("core.config_entries")

            self.assertTrue(allowed.ok)
            self.assertEqual("<redacted>", allowed.data["data"]["profile_token"])
            self.assertFalse(blocked.ok)
            self.assertEqual("StorageUnavailable", blocked.data["error"])

    def test_profile_scenarios_execute_through_home_assistant_adapter(self) -> None:
        root = Path(__file__).resolve().parents[2]
        config = load_config(root, overrides={"scenario_paths": ["verification/scenarios/profile"]})
        scenarios = [
            scenario
            for scenario in ScenarioLoader(config).load()
            if scenario.id in {"PROFILE-001", "PROFILE-002", "PROFILE-003", "PROFILE-004", "PROFILE-005"}
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = Path(temp_dir)
            (storage / "djconnect_profile_platform").write_text(
                json.dumps({"profiles": [], "devices": []}),
                encoding="utf-8",
            )
            registry = AdapterRegistry()
            registry.register(
                HomeAssistantVerificationAdapter(
                    HomeAssistantAdapterConfig(base_url="http://ha.local", storage_dir=storage),
                    transport=MockHomeAssistantTransport(),
                )
            )

            results = ScenarioExecutor(registry).execute(scenarios)

        self.assertEqual(5, len(results))
        self.assertEqual({ResultState.PASS}, {result.state for result in results})
        self.assertTrue(all("Home Assistant adapter" in result.message for result in results))


if __name__ == "__main__":
    unittest.main()
