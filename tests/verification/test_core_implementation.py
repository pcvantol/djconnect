"""Tests for the platform-independent verification core."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.verification.adapters import AdapterRegistry, VerificationAdapter
from tools.verification.build import BuildQualification
from tools.verification.cli import build_parser, main
from tools.verification.config import load_config
from tools.verification.configuration import SecretLoader
from tools.verification.environment import EnvironmentSnapshotter
from tools.verification.evidence import EvidenceCollector, LogManager
from tools.verification.hygiene import RepositoryHygiene
from tools.verification.models import ArtifactMetadata, EvidenceKind, GateState, ResultState, ScenarioResult
from tools.verification.reporting import JSONReporter, JUnitReporter, PlatformReadinessCalculator
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
                ScenarioResult("A-001", ResultState.PASS, "ok"),
                ScenarioResult("B-001", ResultState.FAIL, "bad"),
            ],
        )

        self.assertEqual("not_ready", PlatformReadinessCalculator().calculate(result)["status"])
        self.assertEqual("FAIL", json.loads(JSONReporter().render(result))["state"])
        self.assertIn("failure", JUnitReporter().render(result))

    def test_cli_parses_phase_five_commands(self) -> None:
        parser = build_parser()

        self.assertEqual("doctor", parser.parse_args(["doctor"]).command)
        self.assertEqual("schema", parser.parse_args(["schema"]).command)
        self.assertEqual("config", parser.parse_args(["config"]).command)

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
            scenario for scenario in ScenarioLoader(load_config(root)).load() if scenario.id == "PROFILE-001"
        )

        plan = ScenarioEngine(AdapterRegistry()).plan(scenario)

        self.assertEqual("PROFILE-001", plan.scenario_id)
        self.assertEqual(2, len(plan.actions))
        self.assertIn("backend", plan.assertions)
        self.assertIn("machine", plan.expected_results)
        self.assertEqual({"mode": "NONE", "max_attempts": 1}, plan.retry_policy)
        self.assertEqual(10, plan.timeouts["execution_seconds"])


if __name__ == "__main__":
    unittest.main()
