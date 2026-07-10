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
            plan = self.plan(scenario)
            adapter = self.adapters.get("home_assistant")
            if adapter is not None and _targets_home_assistant(scenario):
                primitive_results = [adapter.execute_action(action) for action in plan.actions]
                state = ResultState.PASS if all(result.ok for result in primitive_results) else ResultState.FAIL
                failed = [result for result in primitive_results if not result.ok]
                message = (
                    "Runtime primitives executed through Home Assistant adapter; "
                    "scenario assertions remain owned by the Scenario Engine."
                )
                if failed:
                    message = f"{message} Failed primitives: {', '.join(result.action for result in failed)}."
                results.append(
                    ScenarioResult(
                        scenario_id=scenario.id,
                        state=state,
                        message=message,
                        evidence=tuple(
                            evidence
                            for result in primitive_results
                            for evidence in result.evidence
                        ),
                        duration_seconds=sum(
                            float(result.data.get("duration_seconds", 0.0))
                            for result in primitive_results
                            if isinstance(result.data, dict)
                        ),
                    )
                )
                continue
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
        if _is_first_profile_adapter_scenario(scenario):
            return [
                PrimitiveAction("collect_environment"),
                PrimitiveAction("health"),
                PrimitiveAction("capabilities"),
                PrimitiveAction(
                    "create_fixture",
                    {
                        "kind": "profile",
                        "name": scenario.id.lower(),
                        "scenario_id": scenario.id,
                    },
                ),
                PrimitiveAction("snapshot_storage", {"key": "djconnect_profile_platform"}),
                PrimitiveAction("collect_logs"),
                PrimitiveAction(
                    "remove_fixture",
                    {"fixture_id": f"verification-profile-{scenario.id.lower()}"},
                ),
            ]
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


def _targets_home_assistant(scenario: Scenario) -> bool:
    platforms = {str(item) for item in scenario.raw.get("supported_platforms") or ()}
    components = set(scenario.required_components)
    return "Home Assistant" in platforms or "HA" in components


def _is_first_profile_adapter_scenario(scenario: Scenario) -> bool:
    return (
        scenario.id in {"PROFILE-001", "PROFILE-002", "PROFILE-003", "PROFILE-004", "PROFILE-005"}
        and scenario.category == "Profiles"
        and _targets_home_assistant(scenario)
        and scenario.source is not None
        and "verification/scenarios/profile" in scenario.source.as_posix()
    )
