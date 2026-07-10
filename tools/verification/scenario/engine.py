"""Scenario interpretation and core-owned verification behavior."""

from __future__ import annotations

from tools.verification.adapters import AdapterRegistry
from tools.verification.models import (
    PrimitiveAction,
    ResultState,
    Scenario,
    ScenarioExecutionPlan,
    ScenarioResult,
)


class ScenarioEngine:
    """Owns scenario behavior while adapters execute only primitive actions."""

    def __init__(self, adapters: AdapterRegistry) -> None:
        self.adapters = adapters

    def plan(self, scenario: Scenario) -> ScenarioExecutionPlan:
        return ScenarioExecutionPlan(
            scenario_id=scenario.id,
            actions=tuple(self._actions(scenario)),
            assertions=dict(scenario.raw.get("assertions") or {}),
            expected_results=dict(scenario.raw.get("expected_results") or {}),
            evidence_requirements=tuple(scenario.raw.get("artifacts") or ()),
            cleanup_policy=tuple(scenario.raw.get("cleanup") or ()),
            retry_policy=dict(scenario.raw.get("retry_policy") or {}),
            timeouts=dict(scenario.raw.get("timeouts") or {}),
        )

    def dry_run(self, scenarios: list[Scenario]) -> list[ScenarioResult]:
        results: list[ScenarioResult] = []
        for scenario in scenarios:
            plan = self.plan(scenario)
            results.append(
                ScenarioResult(
                    scenario_id=scenario.id,
                    state=ResultState.NOT_TESTED,
                    message=(
                        "Dry run only; scenario interpreted by the Scenario Engine "
                        f"with {len(plan.actions)} primitive actions."
                    ),
                )
            )
        return results

    def execute(self, scenarios: list[Scenario]) -> list[ScenarioResult]:
        results: list[ScenarioResult] = []
        for scenario in scenarios:
            self.plan(scenario)
            results.append(
                ScenarioResult(
                    scenario_id=scenario.id,
                    state=ResultState.SKIPPED,
                    message=(
                        "Execution requires a platform adapter; pass/fail remains owned "
                        "by the Scenario Engine."
                    ),
                )
            )
        return results

    def _actions(self, scenario: Scenario) -> list[PrimitiveAction]:
        actions: list[PrimitiveAction] = []
        timeout = None
        timeouts = scenario.raw.get("timeouts")
        if isinstance(timeouts, dict):
            value = timeouts.get("execution_seconds")
            timeout = float(value) if isinstance(value, int | float) else None
        for step in scenario.raw.get("steps") or ():
            if isinstance(step, dict):
                actions.append(
                    PrimitiveAction(
                        name=str(step.get("action", "")),
                        parameters={key: value for key, value in step.items() if key != "action"},
                        timeout_seconds=timeout,
                    )
                )
        return actions
