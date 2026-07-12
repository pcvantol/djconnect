"""Canonical Verification Planning Engine."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from tools.verification.models import (
    CoverageReport,
    EnvironmentPlan,
    ExecutionPlan,
    HarnessConfig,
    PlanBatch,
    PlanGraph,
    PlannedCase,
    ResourcePlan,
    Scenario,
)
from tools.verification.lab import LabCatalog

from .catalogs import PlanningCatalogs
from .strategies import PlanningStrategyRegistry


CATEGORY_ORDER = {
    "Setup": 0,
    "Profiles": 10,
    "Resolver": 20,
    "Capabilities": 30,
    "Backend": 40,
    "Ask DJ": 50,
    "Music DNA": 60,
    "Discover": 70,
    "Track Insight": 80,
    "Playback": 90,
    "Voice": 100,
    "Networking": 110,
    "Privacy": 120,
    "Localization": 130,
    "Export": 140,
    "Import": 150,
    "Hardware": 160,
    "Release": 170,
}

PLATFORM_ADAPTERS = {
    "Home Assistant": "home_assistant",
    "HA": "home_assistant",
    "Apple": "apple",
    "iOS": "apple",
    "iPadOS": "apple",
    "macOS": "apple",
    "watchOS": "apple",
    "Windows": "windows_native_arm64",
    "Pi": "raspberry_pi",
    "Raspberry Pi": "raspberry_pi",
    "ESP32": "esp32",
    "Voice Endpoint": "voice_endpoint",
    "Website": "website",
    "Release": "release",
}

RUNTIME_SECONDS = {
    "short": 60,
    "medium": 180,
    "medium_long": 300,
    "long": 600,
}


class VerificationPlanningEngine:
    """Expand abstract verification assets into executable plan metadata only."""

    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.catalogs = PlanningCatalogs(config.root)
        self.strategies = PlanningStrategyRegistry()

    def plan(
        self,
        scenarios: list[Scenario],
        *,
        policy_id: str | None = None,
        strategy_id: str | None = None,
    ) -> ExecutionPlan:
        strategy = self.strategies.get(strategy_id)
        policies = self.catalogs.policies()
        modes = self.catalogs.modes()
        policy = policies.get(policy_id or strategy.default_policy) or policies.get(strategy.default_policy) or {}
        resolved_policy_id = str(policy.get("id") or policy_id or strategy.default_policy)
        selected_scenarios = _reduce_scenarios(scenarios, strategy.max_cases)
        cases = self._expand_cases(selected_scenarios, resolved_policy_id, policy, modes)
        cases = self._order_cases(cases)
        graph = self._graph(cases)
        batches = self._batches(cases, policy)
        cases = self._assign_batches(cases, batches)
        resource_plan = self._resource_plan(policy, cases)
        environment_plan = self._environment_plan(policy)
        coverage = self._coverage(selected_scenarios, cases)
        lab_execution_plan = LabCatalog(self.config.root).plan_for_scenarios(selected_scenarios)
        plan_id = f"plan-{resolved_policy_id}-{strategy.id}-{_utc_stamp()}"
        return ExecutionPlan(
            plan_id=plan_id,
            strategy=strategy.id,
            policy=resolved_policy_id,
            cases=cases,
            batches=batches,
            graph=graph,
            resource_plan=resource_plan,
            environment_plan=environment_plan,
            coverage=coverage,
            estimated_seconds=sum(batch.estimated_seconds for batch in batches),
            required_evidence=tuple(_unique(_policy_list(policy, "evidence_level"))),
            expected_reports=("execution_plan", "coverage_report", "resource_plan", "environment_plan"),
            metadata={
                "generated_at": datetime.now(UTC).isoformat(),
                "planner": "canonical_verification_planning_engine",
                "combination_reduction": strategy.reduction,
                "executes": False,
                "evaluates": False,
                "calls_adapters": False,
                "lab_execution_plan": lab_execution_plan.to_dict(),
            },
        )

    def to_dict(self, plan: ExecutionPlan) -> dict[str, Any]:
        return asdict(plan)

    def _expand_cases(
        self,
        scenarios: list[Scenario],
        policy_id: str,
        policy: dict[str, Any],
        modes: dict[str, dict[str, Any]],
    ) -> tuple[PlannedCase, ...]:
        mode_ids = _policy_list(policy, "included_modes") or ["functional"]
        matrix_profiles = _policy_list(policy, "required_matrix_profiles") or ["Smoke Test Profile"]
        data_profiles = _policy_list(policy, "required_data_profiles") or ["smoke"]
        cases: list[PlannedCase] = []
        for scenario in scenarios:
            platform = _platform_for(scenario, policy)
            adapter = PLATFORM_ADAPTERS.get(platform, "unassigned")
            for mode_id in mode_ids:
                mode = modes.get(mode_id, {})
                if not _mode_applies(mode, scenario):
                    continue
                for matrix_profile in matrix_profiles:
                    for data_profile in _data_profiles_for(mode, data_profiles):
                        case_id = _case_id(scenario.id, mode_id, matrix_profile, data_profile)
                        cases.append(
                            PlannedCase(
                                case_id=case_id,
                                scenario_id=scenario.id,
                                scenario_category=scenario.category,
                                mode=mode_id,
                                policy=policy_id,
                                matrix_profile=matrix_profile,
                                data_profile=data_profile,
                                platform=platform,
                                adapter=adapter,
                                batch_id="pending",
                                priority=scenario.priority,
                                estimated_seconds=_estimated_seconds(mode),
                                retry_policy=_retry_policy(policy),
                                traceability={
                                    "scenario": scenario.id,
                                    "source": str(scenario.source) if scenario.source else "",
                                    "verification_matrix": matrix_profile,
                                    "verification_data_profile": data_profile,
                                    "verification_mode": mode_id,
                                    "verification_policy": policy_id,
                                    "execution_environment": _policy_list(policy, "required_environment"),
                                    "expected_evidence": mode.get("evidence", []),
                                },
                            )
                        )
        return tuple(cases)

    def _order_cases(self, cases: tuple[PlannedCase, ...]) -> tuple[PlannedCase, ...]:
        sorted_cases = sorted(
            cases,
            key=lambda case: (CATEGORY_ORDER.get(case.scenario_category, 999), case.priority, case.case_id),
        )
        latest_by_category: dict[str, str] = {}
        ordered: list[PlannedCase] = []
        for case in sorted_cases:
            depends_on = tuple(
                latest_by_category[category]
                for category, order in CATEGORY_ORDER.items()
                if order < CATEGORY_ORDER.get(case.scenario_category, 999) and category in latest_by_category
            )
            updated = PlannedCase(**{**asdict(case), "depends_on": depends_on})
            ordered.append(updated)
            latest_by_category[case.scenario_category] = updated.case_id
        return tuple(ordered)

    def _graph(self, cases: tuple[PlannedCase, ...]) -> PlanGraph:
        nodes = tuple(case.case_id for case in cases)
        edges = tuple((dependency, case.case_id) for case in cases for dependency in case.depends_on)
        return PlanGraph(nodes=nodes, edges=edges)

    def _batches(self, cases: tuple[PlannedCase, ...], policy: dict[str, Any]) -> tuple[PlanBatch, ...]:
        parallelization = str(policy.get("parallelization") or "sequential")
        hardware_limited = "hardware" in parallelization or "limited" in parallelization
        batches: list[PlanBatch] = []
        if hardware_limited:
            for index, case in enumerate(cases, start=1):
                batch_id = f"batch-{index:03d}"
                batches.append(
                    PlanBatch(
                        batch_id=batch_id,
                        case_ids=(case.case_id,),
                        execution="sequential",
                        required_resources=(_resource_for_case(case),),
                        estimated_seconds=case.estimated_seconds,
                    )
                )
        else:
            grouped: dict[str, list[PlannedCase]] = defaultdict(list)
            for case in cases:
                grouped[case.scenario_category].append(case)
            for index, category in enumerate(sorted(grouped, key=lambda item: CATEGORY_ORDER.get(item, 999)), start=1):
                group = grouped[category]
                batch_id = f"batch-{index:03d}"
                batches.append(
                    PlanBatch(
                        batch_id=batch_id,
                        case_ids=tuple(case.case_id for case in group),
                        execution="parallel" if "parallel" in parallelization else "sequential",
                        required_resources=tuple(_unique(_resource_for_case(case) for case in group)),
                        estimated_seconds=max((case.estimated_seconds for case in group), default=0),
                    )
                )
        return tuple(batches)

    def _assign_batches(self, cases: tuple[PlannedCase, ...], batches: tuple[PlanBatch, ...]) -> tuple[PlannedCase, ...]:
        batch_by_case = {
            case_id: batch.batch_id
            for batch in batches
            for case_id in batch.case_ids
        }
        return tuple(
            PlannedCase(**{**asdict(case), "batch_id": batch_by_case.get(case.case_id, "unbatched")})
            for case in cases
        )

    def _resource_plan(self, policy: dict[str, Any], cases: tuple[PlannedCase, ...]) -> ResourcePlan:
        resources = tuple(_unique(_resource_for_case(case) for case in cases))
        hardware = tuple(item for item in resources if item in {"apple_device", "windows_vm", "pi", "esp32", "voice_endpoint"})
        exclusive = tuple(item for item in resources if item in {"serial_port", "windows_vm", "pi", "esp32", "physical_watch"})
        return ResourcePlan(
            required_hardware=hardware,
            required_builds=tuple(_unique(_policy_list(policy, "required_build_types"))),
            required_services=tuple(_unique(_policy_list(policy, "required_environment"))),
            exclusive_resources=exclusive,
        )

    def _environment_plan(self, policy: dict[str, Any]) -> EnvironmentPlan:
        return EnvironmentPlan(
            environments=tuple(_unique(_policy_list(policy, "required_environment") or ["local"])),
            capabilities=(
                "scenario_catalog",
                "verification_matrix",
                "verification_data",
                "verification_modes",
                "verification_policies",
                "execution_environment",
                "adapter_registry",
            ),
            configuration={
                "ci": self.config.ci,
                "dry_run": self.config.dry_run,
                "scenario_paths": [str(path) for path in self.config.scenario_paths],
            },
        )

    def _coverage(self, scenarios: list[Scenario], cases: tuple[PlannedCase, ...]) -> CoverageReport:
        return CoverageReport(
            scenario_count=len({scenario.id for scenario in scenarios}),
            case_count=len(cases),
            by_mode=dict(Counter(case.mode for case in cases)),
            by_platform=dict(Counter(case.platform for case in cases)),
            by_data_profile=dict(Counter(case.data_profile for case in cases)),
            by_matrix_profile=dict(Counter(case.matrix_profile for case in cases)),
            by_policy=dict(Counter(case.policy for case in cases)),
        )


def _policy_list(policy: dict[str, Any], key: str) -> list[str]:
    value = policy.get(key)
    if isinstance(value, list):
        return [str(item) for item in value]
    if value:
        return [str(value)]
    return []


def _reduce_scenarios(scenarios: list[Scenario], max_cases: int | None) -> list[Scenario]:
    ordered = sorted(scenarios, key=lambda scenario: (scenario.priority, scenario.id))
    if max_cases is None or len(ordered) <= max_cases:
        return ordered
    selected = ordered[:max_cases]
    selected_adapters = {_adapter_for(scenario) for scenario in selected}
    for scenario in ordered[max_cases:]:
        adapter = _adapter_for(scenario)
        if adapter in selected_adapters:
            continue
        selected.append(scenario)
        selected_adapters.add(adapter)
        if len(selected) >= max_cases + len(PLATFORM_ADAPTERS):
            break
    return selected


def _mode_applies(mode: dict[str, Any], scenario: Scenario) -> bool:
    categories = {str(item) for item in mode.get("applicable_scenario_categories") or []}
    return not categories or scenario.category in categories


def _data_profiles_for(mode: dict[str, Any], policy_profiles: list[str]) -> tuple[str, ...]:
    recommended = [str(item) for item in mode.get("recommended_data_profiles") or []]
    selected = [profile for profile in policy_profiles if not recommended or profile in recommended]
    return tuple(selected or policy_profiles[:1] or ["smoke"])


def _platform_for(scenario: Scenario, policy: dict[str, Any]) -> str:
    runtime_platform = _platform_for_runtime_capability(scenario)
    if runtime_platform is not None:
        return runtime_platform
    components = list(scenario.required_components) + _policy_list(policy, "included_platforms")
    for component in components:
        for token in PLATFORM_ADAPTERS:
            if token.lower() in component.lower():
                return token
    if scenario.category == "Release":
        return "Release"
    return "Home Assistant"


def _platform_for_runtime_capability(scenario: Scenario) -> str | None:
    required = _required_capabilities(scenario)
    if any(capability.startswith(("pi.", "raspberry_pi.")) for capability in required):
        return "Raspberry Pi"
    components = set(scenario.required_components)
    platforms = {str(item) for item in scenario.raw.get("supported_platforms") or ()}
    targets_windows_only = (
        any(capability.startswith(("windows.", "windows_native_arm64.")) for capability in required)
        and not ({"HA", "Home Assistant"} & components)
        and not ("Home Assistant" in platforms)
    )
    if targets_windows_only:
        return "Windows"
    return None


def _required_capabilities(scenario: Scenario) -> set[str]:
    requires = scenario.raw.get("requires")
    if not isinstance(requires, dict):
        return set()
    return {str(item) for item in requires.get("capabilities") or ()}


def _adapter_for(scenario: Scenario) -> str:
    return PLATFORM_ADAPTERS.get(_platform_for(scenario, {}), "unassigned")


def _estimated_seconds(mode: dict[str, Any]) -> int:
    return RUNTIME_SECONDS.get(str(mode.get("typical_runtime") or "short"), 120)


def _retry_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if "nightly" in str(policy.get("id", "")):
        return {"mode": "controlled_retry", "max_attempts": 2}
    if policy.get("approval_requirement") == "manual_confirmations_required_where_marked":
        return {"mode": "manual_retry", "max_attempts": 1}
    return {"mode": "no_retry", "max_attempts": 1}


def _resource_for_case(case: PlannedCase) -> str:
    return {
        "apple": "apple_device",
        "windows_native_arm64": "windows_vm",
        "raspberry_pi": "pi",
        "esp32": "esp32",
        "voice_endpoint": "voice_endpoint",
        "website": "browser",
        "release": "ci",
    }.get(case.adapter, "ha_development")


def _case_id(scenario_id: str, mode_id: str, matrix_profile: str, data_profile: str) -> str:
    return "-".join(
        [
            scenario_id,
            mode_id,
            _slug(matrix_profile),
            _slug(data_profile),
        ]
    )


def _slug(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")


def _unique(items) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            result.append(str(item))
            seen.add(str(item))
    return result


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
