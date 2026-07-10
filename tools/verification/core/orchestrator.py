"""Reusable verification execution pipeline."""

from __future__ import annotations

from dataclasses import asdict

from tools.verification.adapters import AdapterRegistry
from tools.verification.build import BuildQualification
from tools.verification.environment import EnvironmentSnapshotter, VerificationExecutionEnvironment
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
        self.execution_environment = VerificationExecutionEnvironment(config)
        self.executor = ScenarioExecutor(self.adapters)
        self.results = ResultAggregator()

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
        return self.results.aggregate(
            "execute",
            self.executor.execute(scenarios),
            {
                "environment": asdict(snapshot),
                "execution_environment": environment,
                "adapters": list(self.adapters.names()),
            },
        )
