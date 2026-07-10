"""Reusable verification execution pipeline."""

from __future__ import annotations

from dataclasses import asdict

from tools.verification.adapters import AdapterRegistry
from tools.verification.build import BuildQualification
from tools.verification.environment import EnvironmentSnapshotter
from tools.verification.execution import ResultAggregator, ScenarioExecutor
from tools.verification.hygiene import RepositoryHygiene
from tools.verification.models import HarnessConfig, Scenario


class VerificationCore:
    def __init__(self, config: HarnessConfig, adapters: AdapterRegistry | None = None) -> None:
        self.config = config
        self.adapters = adapters or AdapterRegistry()
        self.hygiene = RepositoryHygiene(config.root)
        self.builds = BuildQualification()
        self.environment = EnvironmentSnapshotter()
        self.executor = ScenarioExecutor(self.adapters)
        self.results = ResultAggregator()

    def doctor(self) -> list:
        return [*self.hygiene.check(), *self.builds.qualify()]

    def snapshot(self):
        return self.environment.collect(self.config)

    def dry_run(self, scenarios: list[Scenario]):
        snapshot = self.snapshot()
        return self.results.aggregate(
            "dry-run",
            self.executor.dry_run(scenarios),
            {"environment": asdict(snapshot), "adapters": list(self.adapters.names())},
        )

    def execute(self, scenarios: list[Scenario]):
        snapshot = self.snapshot()
        return self.results.aggregate(
            "execute",
            self.executor.execute(scenarios),
            {"environment": asdict(snapshot), "adapters": list(self.adapters.names())},
        )
