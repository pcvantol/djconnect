"""Scenario executor that delegates all platform work to adapters."""

from __future__ import annotations

from tools.verification.adapters import AdapterRegistry
from tools.verification.models import Scenario, ScenarioResult
from tools.verification.scenario import ScenarioEngine


class ScenarioExecutor:
    def __init__(self, adapters: AdapterRegistry) -> None:
        self.adapters = adapters
        self.engine = ScenarioEngine(adapters)

    def dry_run(self, scenarios: list[Scenario]) -> list[ScenarioResult]:
        return self.engine.dry_run(scenarios)

    def execute(self, scenarios: list[Scenario]) -> list[ScenarioResult]:
        return self.engine.execute(scenarios)
