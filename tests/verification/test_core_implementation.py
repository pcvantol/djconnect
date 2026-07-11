"""Tests for the platform-independent verification core."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from tools.verification.adapters import AdapterRegistry, VerificationAdapter
from tools.verification.build import BuildQualification
from tools.verification.cli import build_parser, main
from tools.verification.config import load_config
from tools.verification.configuration import SecretLoader
from tools.verification.environment import EnvironmentSnapshotter
from tools.verification.evidence import EvidenceCollector, LogManager
from tools.verification.execution import ParallelExecutionOptions, ScenarioExecutor
from tools.verification.hygiene import RepositoryHygiene
from tools.verification.models import ArtifactMetadata, EvidenceKind, GateState, PrimitiveResult, ResultState, Scenario, ScenarioResult
from tools.verification.reporting import JSONReporter, JUnitReporter, MarkdownReporter, PlatformReadinessCalculator
from tools.verification.results import ResultManager
from tools.verification.scenario import ScenarioEngine
from tools.verification.scenarios import ScenarioLoader, ScenarioValidator


class VerificationCoreImplementationTests(unittest.TestCase):
    def test_catalog_scenarios_parse_and_validate(self) -> None:
        root = Path(__file__).resolve().parents[2]
        scenarios = ScenarioLoader(load_config(root)).load()

        self.assertTrue(scenarios)
        self.assertFalse(
            [
                issue
                for scenario in scenarios[:5]
                for issue in ScenarioValidator().validate(scenario)
                if issue.severity == "error"
            ]
        )

    def test_configuration_and_secret_loader_do_not_return_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            secrets = root / "secrets.json"
            secrets.write_text(json.dumps({"api_token": "super-secret"}), encoding="utf-8")

            config = load_config(root, secrets_file=secrets)
            bundle = SecretLoader().load(config.secrets_file)

            self.assertEqual(("api_token",), bundle.names)
            self.assertNotIn("super-secret", repr(bundle))

    def test_environment_snapshot_contains_git_and_fingerprint_fields(self) -> None:
        root = Path(__file__).resolve().parents[2]
        snapshot = EnvironmentSnapshotter().collect(load_config(root))

        self.assertTrue(snapshot.timestamp)
        self.assertTrue(snapshot.configuration_fingerprint)
        self.assertIn("python", snapshot.toolchain)
        self.assertEqual("djconnect-verification-platform", snapshot.verification_runtime["name"])

    def test_repository_hygiene_exposes_required_gates(self) -> None:
        root = Path(__file__).resolve().parents[2]
        gates = RepositoryHygiene(root).check()

        names = {gate.name for gate in gates}
        self.assertIn("working_tree_validation", names)
        self.assertIn("open_pr_validation", names)
        self.assertIn("environment_fingerprint", names)

    def test_build_qualification_models_validate_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_path = Path(temp_dir) / "artifact.bin"
            artifact_path.write_text("payload", encoding="utf-8")
            qualification = BuildQualification()
            artifact = qualification.with_checksum(
                ArtifactMetadata(path=artifact_path, name="artifact", version="1.0")
            )

            gates = qualification.qualify([artifact])

            self.assertTrue(artifact.sha256)
            self.assertNotIn(GateState.FAIL, {gate.state for gate in gates})

    def test_evidence_collector_redacts_and_indexes_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = EvidenceCollector(Path(temp_dir))
            item = collector.store_text(
                "run-1",
                EvidenceKind.LOG,
                "log.txt",
                "authorization token raw_audio",
            )

            self.assertIn("[redacted-key]", item.path.read_text(encoding="utf-8"))
            self.assertTrue(item.metadata["sha256"])
            self.assertIn("[redacted-key]", LogManager().redact("secret prompt"))

    def test_reporting_outputs_readiness_and_junit(self) -> None:
        result = ResultManager().aggregate(
            "unit",
            [
                ScenarioResult("A-001", ResultState.PASS, "ok", duration_seconds=1.25),
                ScenarioResult("B-001", ResultState.FAIL, "bad", duration_seconds=2.75),
            ],
        )

        self.assertEqual("not_ready", PlatformReadinessCalculator().calculate(result)["status"])
        rendered = json.loads(JSONReporter().render(result))
        self.assertEqual("FAIL", rendered["state"])
        self.assertEqual("djconnect-verification-platform", rendered["metadata"]["verification_runtime"]["name"])
        self.assertEqual(4.0, rendered["execution_summary"]["total_execution_seconds"])
        self.assertEqual(2, rendered["execution_summary"]["executed_scenarios"])
        markdown = MarkdownReporter().render(result)
        self.assertIn("Verification runtime:", markdown)
        self.assertIn("2 of 2 tests executed, status FAIL", markdown)
        junit = JUnitReporter().render(result)
        self.assertIn('time="4.0"', junit)
        self.assertIn("failure", junit)

    def test_cli_parses_phase_five_commands(self) -> None:
        parser = build_parser()

        self.assertEqual("doctor", parser.parse_args(["doctor"]).command)
        self.assertEqual("schema", parser.parse_args(["schema"]).command)
        self.assertEqual("config", parser.parse_args(["config"]).command)

    def test_cli_parses_parallel_execution_controls(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--parallel", "--workers", "12", "execute"])

        self.assertTrue(args.parallel)
        self.assertEqual(12, args.workers)

        disabled = parser.parse_args(["--no-parallel", "execute"])
        self.assertTrue(disabled.no_parallel)

    def test_cli_validate_catalog_and_report_json(self) -> None:
        root = Path(__file__).resolve().parents[2]

        self.assertEqual(0, main(["--root", str(root), "validate"]))
        self.assertEqual(0, main(["--root", str(root), "report", "--format", "json"]))

    def test_adapter_interface_is_abstract_and_registry_is_platform_neutral(self) -> None:
        with self.assertRaises(TypeError):
            VerificationAdapter()

        registry = AdapterRegistry()

        self.assertEqual((), registry.available())
        self.assertFalse(hasattr(VerificationAdapter, "execute_step"))
        self.assertFalse(hasattr(VerificationAdapter, "qualify_build"))
        self.assertTrue(hasattr(VerificationAdapter, "execute_rest"))
        self.assertTrue(hasattr(VerificationAdapter, "collect_artifact_metadata"))

    def test_scenario_engine_owns_interpretation_metadata(self) -> None:
        root = Path(__file__).resolve().parents[2]
        scenario = next(
            scenario
            for scenario in ScenarioLoader(load_config(root, overrides={"scenario_paths": ["verification/schema/examples"]})).load()
            if scenario.id == "PROFILE-001"
        )

        plan = ScenarioEngine(AdapterRegistry()).plan(scenario)

        self.assertEqual("PROFILE-001", plan.scenario_id)
        self.assertEqual(2, len(plan.actions))
        self.assertIn("backend", plan.assertions)
        self.assertIn("machine", plan.expected_results)
        self.assertEqual({"mode": "NONE", "max_attempts": 1}, plan.retry_policy)
        self.assertEqual(10, plan.timeouts["execution_seconds"])

    def test_parallel_executor_runs_independent_scenarios_in_sandboxed_workers(self) -> None:
        registry = AdapterRegistry()
        registry.register(_SleepyAdapter(delay=0.01))
        scenarios = [
            _ha_scenario("PAR-001"),
            _ha_scenario("PAR-002"),
        ]

        started = time.time()
        results = ScenarioExecutor(
            registry,
            parallel=ParallelExecutionOptions(enabled=True, max_workers=2),
        ).execute(scenarios)

        self.assertLess(time.time() - started, 0.08)
        self.assertEqual(["PAR-001", "PAR-002"], [result.scenario_id for result in results])
        self.assertTrue(all(result.state == ResultState.PASS for result in results))
        self.assertTrue(all("sandbox" in result.diagnostics for result in results))
        self.assertEqual({"PAR-001", "PAR-002"}, set(results[0].diagnostics["parallel_wave"]["wave_scenario_ids"]))

    def test_parallel_executor_respects_dependencies_between_scenarios(self) -> None:
        registry = AdapterRegistry()
        registry.register(_SleepyAdapter(delay=0.0))
        scenarios = [
            _ha_scenario("PAR-A"),
            _ha_scenario("PAR-B", depends_on=["PAR-A"]),
        ]

        results = ScenarioExecutor(
            registry,
            parallel=ParallelExecutionOptions(enabled=True, max_workers=2),
        ).execute(scenarios)

        self.assertEqual(["PAR-A"], results[0].diagnostics["parallel_wave"]["wave_scenario_ids"])
        self.assertEqual(["PAR-B"], results[1].diagnostics["parallel_wave"]["wave_scenario_ids"])

    def test_parallel_executor_separates_exclusive_resource_conflicts(self) -> None:
        registry = AdapterRegistry()
        registry.register(_SleepyAdapter(delay=0.0))
        scenarios = [
            _ha_scenario("PAR-R1", exclusive=["shared-ha-storage"]),
            _ha_scenario("PAR-R2", exclusive=["shared-ha-storage"]),
        ]

        results = ScenarioExecutor(
            registry,
            parallel=ParallelExecutionOptions(enabled=True, max_workers=2),
        ).execute(scenarios)

        self.assertEqual(["PAR-R1"], results[0].diagnostics["parallel_wave"]["wave_scenario_ids"])
        self.assertEqual(["PAR-R2"], results[1].diagnostics["parallel_wave"]["wave_scenario_ids"])


if __name__ == "__main__":
    unittest.main()


class _SleepyAdapter(VerificationAdapter):
    name = "home_assistant"

    def __init__(self, *, delay: float) -> None:
        self.delay = delay

    def initialize(self) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def health(self) -> dict:
        return {"ok": True}

    def prepare_environment(self) -> None:
        return None

    def launch(self, target: str | None = None) -> PrimitiveResult:
        return PrimitiveResult("launch", True)

    def stop(self) -> PrimitiveResult:
        return PrimitiveResult("stop", True)

    def restart(self) -> PrimitiveResult:
        return PrimitiveResult("restart", True)

    def click(self, target: str, **kwargs) -> PrimitiveResult:
        return PrimitiveResult("click", True)

    def type(self, text: str, **kwargs) -> PrimitiveResult:
        return PrimitiveResult("type", True)

    def execute_service(self, name: str, payload: dict | None = None) -> PrimitiveResult:
        return PrimitiveResult("service", True)

    def execute_rest(self, method: str, path: str, payload: dict | None = None, headers: dict | None = None) -> PrimitiveResult:
        return PrimitiveResult("http_request", True)

    def execute_websocket(self, message: dict) -> PrimitiveResult:
        return PrimitiveResult("websocket", True)

    def execute_action(self, action) -> PrimitiveResult:
        time.sleep(self.delay)
        return PrimitiveResult(action.name, True, {"duration_seconds": self.delay})

    def cleanup(self) -> None:
        return None

    def collect_logs(self) -> tuple:
        return ()

    def collect_artifacts(self) -> tuple:
        return ()

    def capture_screenshot(self, name: str | None = None) -> PrimitiveResult:
        return PrimitiveResult("screenshot", True)

    def capture_serial(self) -> tuple:
        return ()

    def collect_environment(self):
        return {}

    def collect_artifact_metadata(self) -> tuple:
        return ()

    def reset(self) -> None:
        return None


def _ha_scenario(scenario_id: str, *, depends_on: list[str] | None = None, exclusive: list[str] | None = None) -> Scenario:
    raw = {
        "supported_platforms": ["Home Assistant"],
        "requires": {"capabilities": ["ha.runtime"]},
    }
    if depends_on:
        raw["depends_on"] = depends_on
    if exclusive:
        raw["requires"]["exclusive_resources"] = exclusive
    return Scenario(
        id=scenario_id,
        title=scenario_id,
        description=scenario_id,
        category="Profiles",
        priority="P1",
        verification_level="V4",
        automation_level="automated",
        required_components=("HA",),
        raw=raw,
    )
