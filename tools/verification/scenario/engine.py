"""Scenario interpretation and core-owned verification behavior."""

from __future__ import annotations

from tools.verification.adapters import AdapterRegistry
from tools.verification.models import (
    PrimitiveAction,
    PrimitiveResult,
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
                attempts = _execute_with_controlled_retry(adapter, plan)
                primitive_results = attempts[-1]
                state = ResultState.PASS if all(result.ok for result in primitive_results) else ResultState.FAIL
                failed = [result for result in primitive_results if not result.ok]
                message = (
                    "Runtime primitives executed through Home Assistant adapter; "
                    "scenario assertions remain owned by the Scenario Engine."
                )
                if len(attempts) > 1:
                    message = f"{message} Controlled transient retry attempts: {len(attempts)}."
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
                        diagnostics={
                            "primitive_results": _primitive_result_dicts(primitive_results),
                            "attempts": [
                                {
                                    "attempt": index,
                                    "primitive_results": _primitive_result_dicts(attempt),
                                }
                                for index, attempt in enumerate(attempts, start=1)
                            ],
                            "retry": _retry_diagnostics(plan, attempts),
                        },
                        duration_seconds=sum(
                            float(result.data.get("duration_seconds", 0.0))
                            for attempt in attempts
                            for result in attempt
                            if isinstance(result.data, dict)
                        ),
                    )
                )
                continue
            adapter = self.adapters.get("apple")
            if adapter is not None and _targets_apple(scenario):
                attempts = _execute_with_controlled_retry(adapter, plan)
                primitive_results = attempts[-1]
                state = ResultState.PASS if all(result.ok for result in primitive_results) else ResultState.FAIL
                failed = [result for result in primitive_results if not result.ok]
                message = (
                    "Runtime primitives executed through Apple adapter; "
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
                        diagnostics={
                            "primitive_results": _primitive_result_dicts(primitive_results),
                            "attempts": [
                                {
                                    "attempt": index,
                                    "primitive_results": _primitive_result_dicts(attempt),
                                }
                                for index, attempt in enumerate(attempts, start=1)
                            ],
                            "retry": _retry_diagnostics(plan, attempts),
                        },
                        duration_seconds=sum(
                            float(result.data.get("duration_seconds", 0.0))
                            for attempt in attempts
                            for result in attempt
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
        if _targets_apple(scenario) and not _targets_home_assistant(scenario):
            return _apple_runtime_actions(scenario)
        if _is_first_profile_adapter_scenario(scenario):
            return _home_assistant_backend_actions(scenario)
        if _is_home_assistant_backend_scenario(scenario):
            return _home_assistant_backend_actions(scenario)
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


def _execute_with_controlled_retry(adapter: object, plan: ScenarioExecutionPlan) -> list[list[PrimitiveResult]]:
    attempts: list[list[PrimitiveResult]] = []
    max_attempts = _max_attempts(plan.retry_policy)
    for attempt in range(1, max_attempts + 1):
        primitive_results = [adapter.execute_action(action) for action in plan.actions]
        attempts.append(primitive_results)
        if all(result.ok for result in primitive_results):
            break
        if attempt >= max_attempts:
            break
        if not _can_retry(plan.retry_policy, primitive_results):
            break
    return attempts


def _max_attempts(retry_policy: dict[str, object]) -> int:
    if str(retry_policy.get("mode") or "").upper() != "CONTROLLED_RETRY":
        return 1
    value = retry_policy.get("max_attempts")
    if not isinstance(value, int):
        return 1
    return max(1, min(value, 3))


def _can_retry(retry_policy: dict[str, object], primitive_results: list[PrimitiveResult]) -> bool:
    if str(retry_policy.get("mode") or "").upper() != "CONTROLLED_RETRY":
        return False
    failed = [result for result in primitive_results if not result.ok]
    return bool(failed) and all(_is_transient_primitive_failure(result) for result in failed)


def _is_transient_primitive_failure(result: PrimitiveResult) -> bool:
    text = f"{result.action} {result.message} {result.data}".lower()
    if "authenticationfailed" in text or "fixturefailed" in text or "storageunavailable" in text:
        return False
    transient_tokens = (
        "timed out",
        "timeout",
        "connectionfailed",
        "connection refused",
        "connection reset",
        "temporarily unavailable",
        "websocketerror",
    )
    return any(token in text for token in transient_tokens)


def _primitive_result_dicts(results: list[PrimitiveResult]) -> list[dict[str, object]]:
    return [
        {
            "action": result.action,
            "ok": result.ok,
            "message": result.message,
            "data": result.data,
        }
        for result in results
    ]


def _retry_diagnostics(plan: ScenarioExecutionPlan, attempts: list[list[PrimitiveResult]]) -> dict[str, object]:
    failed_first_attempt = [result for result in attempts[0] if not result.ok] if attempts else []
    return {
        "mode": plan.retry_policy.get("mode", "NONE"),
        "max_attempts": _max_attempts(plan.retry_policy),
        "attempts": len(attempts),
        "controlled_retry_used": len(attempts) > 1,
        "first_attempt_transient": bool(failed_first_attempt)
        and all(_is_transient_primitive_failure(result) for result in failed_first_attempt),
    }


def _targets_home_assistant(scenario: Scenario) -> bool:
    platforms = {str(item) for item in scenario.raw.get("supported_platforms") or ()}
    components = set(scenario.required_components)
    return "Home Assistant" in platforms or "HA" in components


def _targets_apple(scenario: Scenario) -> bool:
    platforms = {str(item) for item in scenario.raw.get("supported_platforms") or ()}
    components = set(scenario.required_components)
    required = _required_capabilities(scenario)
    return (
        any(platform in {"Apple", "iOS", "iPadOS", "macOS", "watchOS"} for platform in platforms)
        or "Apple" in components
        or any(capability.startswith(("apple.", "ios.", "macos.", "watchos.")) for capability in required)
    )


def _is_home_assistant_backend_scenario(scenario: Scenario) -> bool:
    if not _targets_home_assistant(scenario):
        return False
    required = _required_capabilities(scenario)
    if scenario.category in {"Profiles", "Ask DJ", "Capabilities", "Discover", "Track Insight"}:
        return any(capability.startswith(("ha.", "djconnect.", "evidence.")) for capability in required)
    deferred_prefixes = (
        "apple.",
        "android.",
        "esp32.",
        "firmware.",
        "hardware.",
        "ios.",
        "macos.",
        "pi.",
        "raspberry_pi.",
        "release.",
        "voice_endpoint.",
        "watchos.",
        "windows.",
    )
    if any(capability.startswith(deferred_prefixes) for capability in required):
        return False
    if "spotify.live_api" in required:
        return False
    return any(
        capability.startswith(("ha.", "djconnect.", "evidence.", "fake_music_backend", "music_assistant", "whisper", "piper"))
        for capability in required
    )


def _apple_runtime_actions(scenario: Scenario) -> list[PrimitiveAction]:
    required = _required_capabilities(scenario)
    actions = [
        PrimitiveAction("collect_environment"),
        PrimitiveAction("discover_simulators"),
        PrimitiveAction("validate_target_identity"),
        PrimitiveAction("collect_app_metadata"),
    ]
    if any(capability in required for capability in {"apple.install", "apple.runtime", "ios.runtime", "macos.runtime", "watchos.runtime"}):
        actions.append(PrimitiveAction("install_app"))
    if any(capability in required for capability in {"apple.launch", "apple.runtime", "ios.runtime", "macos.runtime", "watchos.runtime"}):
        actions.append(PrimitiveAction("launch_app"))
    if "apple.screenshot" in required or "evidence.screenshot" in required:
        actions.append(PrimitiveAction("capture_screenshot", {"name": scenario.id.lower()}))
    if "apple.logs" in required or "evidence.logs" in required or "apple.runtime" in required:
        actions.append(PrimitiveAction("collect_logs"))
    if any(capability in required for capability in {"apple.terminate", "apple.runtime", "ios.runtime", "macos.runtime", "watchos.runtime"}):
        actions.append(PrimitiveAction("terminate_app"))
    return actions


def _home_assistant_backend_actions(scenario: Scenario) -> list[PrimitiveAction]:
    required = _required_capabilities(scenario)
    category = scenario.category.lower().replace(" ", "_")
    fixture_kind = _fixture_kind(category)
    fixture_id = f"verification-{fixture_kind}-{scenario.id.lower()}"
    actions = [
        PrimitiveAction("collect_environment"),
        PrimitiveAction("health"),
    ]
    if "ha.websocket" in required or "djconnect.capabilities" in required:
        actions.append(PrimitiveAction("capabilities"))
    if "ha.rest" in required:
        actions.append(PrimitiveAction("http_request", {"method": "GET", "path": "/api/"}))
    if "ha.services" in required:
        actions.append(PrimitiveAction("http_request", {"method": "GET", "path": "/api/services"}))
    actions.append(
        PrimitiveAction(
            "create_fixture",
            {
                "kind": fixture_kind,
                "name": scenario.id.lower(),
                "scenario_id": scenario.id,
                "category": scenario.category,
            },
        )
    )
    for key in _storage_keys_for(scenario, required):
        actions.append(PrimitiveAction("snapshot_storage", {"key": key}))
    if "ha.logs" in required:
        actions.append(PrimitiveAction("collect_logs"))
    actions.append(PrimitiveAction("remove_fixture", {"fixture_id": fixture_id}))
    return actions


def _fixture_kind(category: str) -> str:
    if category in {"profiles", "resolver", "privacy", "music_dna", "ask_dj", "export", "import"}:
        return "profile"
    if category in {"backend", "playback", "track_insight"}:
        return "backend"
    if category in {"capabilities", "setup", "networking"}:
        return "device"
    return "profile"


def _storage_keys_for(scenario: Scenario, required: set[str]) -> tuple[str, ...]:
    category = scenario.category.lower()
    keys: list[str] = []
    if "ha.storage" in required or "ha.persistence" in required or "evidence.storage" in required:
        keys.append("djconnect_profile_platform")
    if "music dna" in category or "music_dna" in category or "djconnect.music_dna" in required:
        keys.append("djconnect_music_dna")
    if "ask dj" in category or "ask_dj" in category or "djconnect.ask_dj" in required:
        keys.append("djconnect_ask_dj_history")
    return tuple(dict.fromkeys(keys))


def _required_capabilities(scenario: Scenario) -> set[str]:
    requires = scenario.raw.get("requires")
    if not isinstance(requires, dict):
        return set()
    return {str(item) for item in requires.get("capabilities") or ()}


def _is_first_profile_adapter_scenario(scenario: Scenario) -> bool:
    return (
        scenario.id in {"PROFILE-001", "PROFILE-002", "PROFILE-003", "PROFILE-004", "PROFILE-005"}
        and scenario.category == "Profiles"
        and _targets_home_assistant(scenario)
        and scenario.source is not None
        and "verification/scenarios/profile" in scenario.source.as_posix()
    )
