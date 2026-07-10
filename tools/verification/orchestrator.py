"""Verification orchestration lifecycle."""

from __future__ import annotations

from .adapters import AdapterManager
from .gates import BuildQualification, EnvironmentManager, RepositoryHygiene
from .models import HarnessConfig, ResultState, Scenario, ScenarioResult
from .results import ResultManager


class VerificationOrchestrator:
    def __init__(self, config: HarnessConfig, adapters: AdapterManager | None = None) -> None:
        self.config = config
        self.adapters = adapters or AdapterManager()
        self.hygiene = RepositoryHygiene(config.root)
        self.environment = EnvironmentManager(config.root)
        self.builds = BuildQualification()
        self.results = ResultManager()

    def dry_run(self, scenarios: list[Scenario]):
        scenario_results = [
            ScenarioResult(
                scenario_id=scenario.id,
                state=ResultState.NOT_TESTED,
                message="Dry run only; scenario was validated but not executed.",
            )
            for scenario in scenarios
        ]
        return self.results.aggregate("dry-run", scenario_results)

    def execute(self, scenarios: list[Scenario]):
        """Reserve the canonical lifecycle without implementing adapters yet."""

        scenario_results = [
            ScenarioResult(
                scenario_id=scenario.id,
                state=ResultState.SKIPPED,
                message="Execution requires a platform adapter implementation.",
            )
            for scenario in scenarios
        ]
        return self.results.aggregate("execute-scaffold", scenario_results)
