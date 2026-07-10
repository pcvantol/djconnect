"""Reusable verification execution pipeline."""

from __future__ import annotations

from dataclasses import asdict

from tools.verification.adapters import AdapterRegistry
from tools.verification.build import BuildQualification
from tools.verification.environment import EnvironmentSnapshotter, VerificationExecutionEnvironment
from tools.verification.execution import ResultAggregator, ScenarioExecutor
from tools.verification.evidence import RunStore
from tools.verification.hygiene import RepositoryHygiene
from tools.verification.models import HarnessConfig, Scenario
from tools.verification.planning import VerificationPlanningEngine


class VerificationCore:
    def __init__(self, config: HarnessConfig, adapters: AdapterRegistry | None = None) -> None:
        self.config = config
        self.adapters = adapters or AdapterRegistry()
        self.hygiene = RepositoryHygiene(config.root)
        self.builds = BuildQualification()
        self.environment = EnvironmentSnapshotter()
        self.execution_environment = VerificationExecutionEnvironment(config)
        self.executor = ScenarioExecutor(self.adapters)
        self.results = ResultAggregator()
        self.run_store = RunStore(config.evidence_dir)

    def doctor(self) -> list:
        return [*self.hygiene.check(), *self.builds.qualify()]

    def snapshot(self):
        return self.environment.collect(self.config)

    def prepare_environment(self, scenarios: list[Scenario] | None = None):
        return self.execution_environment.prepare(scenarios or [])

    def restore_environment(self, *, dry_run: bool = True, allow_destructive: bool = False):
        return self.execution_environment.restore(dry_run=dry_run, allow_destructive=allow_destructive)

    def dry_run(self, scenarios: list[Scenario]):
        snapshot = self.snapshot()
        return self.results.aggregate(
            "dry-run",
            self.executor.dry_run(scenarios),
            {"environment": asdict(snapshot), "adapters": list(self.adapters.names())},
        )

    def execute(self, scenarios: list[Scenario]):
        snapshot = self.snapshot()
        environment = self.prepare_environment(scenarios)
        plan = VerificationPlanningEngine(self.config).plan(scenarios, strategy_id="smoke", policy_id="smoke")
        run_identity = environment.get("run_identity", {})
        run_id = str(run_identity.get("run_id") or "execute")
        self.run_store.ensure(run_id)
        self.run_store.write_json(run_id, "environment.json", asdict(snapshot))
        self.run_store.write_json(run_id, "qualification.json", environment)
        self.run_store.write_json(run_id, "execution-plan.json", asdict(plan))
        scenario_results = self.executor.execute(scenarios)
        result = self.results.aggregate(
            "execute",
            scenario_results,
            {
                "environment": asdict(snapshot),
                "execution_environment": environment,
                "adapters": list(self.adapters.names()),
                "execution_plan": {
                    "plan_id": plan.plan_id,
                    "strategy": plan.strategy,
                    "policy": plan.policy,
                    "case_count": plan.coverage.case_count,
                    "batches": len(plan.batches),
                    "estimated_seconds": plan.estimated_seconds,
                },
            },
        )
        self.run_store.write_json(run_id, "summary.json", asdict(result))
        for scenario_result in scenario_results:
            case_id = next((case.case_id for case in plan.cases if case.scenario_id == scenario_result.scenario_id), scenario_result.scenario_id)
            self.run_store.write_json(
                run_id,
                f"scenarios/{scenario_result.scenario_id}/{case_id}/result.json",
                asdict(scenario_result),
            )
        self.run_store.finalize(run_id, state=result.state.value, summary={"result_state": result.state.value})
        return result
