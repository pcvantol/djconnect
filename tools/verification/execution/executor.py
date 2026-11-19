"""Scenario executor that delegates all platform work to adapters."""

from __future__ import annotations

import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from tools.verification.adapters import AdapterRegistry
from tools.verification.models import ResultState, Scenario, ScenarioResult
from tools.verification.scenario import ScenarioEngine


@dataclass(frozen=True)
class ParallelExecutionOptions:
    enabled: bool = False
    max_workers: int = 1
    sandbox_root: Path | None = None


class ScenarioExecutor:
    def __init__(self, adapters: AdapterRegistry, *, parallel: ParallelExecutionOptions | None = None) -> None:
        self.adapters = adapters
        self.engine = ScenarioEngine(adapters)
        self.parallel = parallel or ParallelExecutionOptions()

    def dry_run(self, scenarios: list[Scenario]) -> list[ScenarioResult]:
        return self.engine.dry_run(scenarios)

    def execute(self, scenarios: list[Scenario]) -> list[ScenarioResult]:
        if self.parallel.enabled and len(scenarios) > 1:
            return self._execute_parallel(scenarios)
        return self.engine.execute(scenarios)

    def _execute_parallel(self, scenarios: list[Scenario]) -> list[ScenarioResult]:
        max_workers = _bounded_workers(self.parallel.max_workers)
        if max_workers <= 1:
            return self.engine.execute(scenarios)
        ordered = list(scenarios)
        by_id = {scenario.id: scenario for scenario in ordered}
        completed: set[str] = set()
        results: dict[str, ScenarioResult] = {}
        pending = set(by_id)
        sandbox_root = self.parallel.sandbox_root or Path(tempfile.gettempdir()) / "djconnect-verification-sandboxes"
        sandbox_root.mkdir(parents=True, exist_ok=True)
        while pending:
            ready = [
                by_id[scenario_id]
                for scenario_id in ordered_ids(ordered, pending)
                if set(_depends_on(by_id[scenario_id])).issubset(completed)
            ]
            if not ready:
                for scenario_id in ordered_ids(ordered, pending):
                    scenario = by_id[scenario_id]
                    results[scenario_id] = ScenarioResult(
                        scenario_id=scenario.id,
                        state=ResultState.FAIL,
                        message="Scenario dependency graph is cyclic or references unavailable dependencies.",
                        diagnostics={"depends_on": list(_depends_on(scenario)), "completed": sorted(completed)},
                    )
                    completed.add(scenario_id)
                    pending.remove(scenario_id)
                break
            wave = _resource_compatible_wave(ready, max_workers)
            started = time.time()
            with ThreadPoolExecutor(max_workers=min(max_workers, len(wave)), thread_name_prefix="djv-scenario") as pool:
                future_map = {
                    pool.submit(self._execute_one_sandboxed, scenario, sandbox_root, index): scenario
                    for index, scenario in enumerate(wave, start=1)
                }
                for future in as_completed(future_map):
                    scenario = future_map[future]
                    results[scenario.id] = future.result()
                    completed.add(scenario.id)
                    pending.remove(scenario.id)
            for scenario in wave:
                result = results[scenario.id]
                diagnostics = dict(result.diagnostics)
                diagnostics["parallel_wave"] = {
                    "wave_scenario_ids": [item.id for item in wave],
                    "wave_duration_seconds": time.time() - started,
                    "max_workers": max_workers,
                }
                results[scenario.id] = ScenarioResult(
                    scenario_id=result.scenario_id,
                    state=result.state,
                    message=result.message,
                    evidence=result.evidence,
                    duration_seconds=result.duration_seconds,
                    diagnostics=diagnostics,
                )
        return [results[scenario.id] for scenario in ordered if scenario.id in results]

    def _execute_one_sandboxed(self, scenario: Scenario, sandbox_root: Path, worker_index: int) -> ScenarioResult:
        sandbox = sandbox_root / _safe_name(scenario.id)
        sandbox.mkdir(parents=True, exist_ok=True)
        result = self.engine.execute([scenario])[0]
        diagnostics = dict(result.diagnostics)
        diagnostics["sandbox"] = {
            "path": str(sandbox),
            "worker_index": worker_index,
            "process_id": os.getpid(),
            "resources": sorted(_resources_for(scenario)),
            "depends_on": list(_depends_on(scenario)),
        }
        return ScenarioResult(
            scenario_id=result.scenario_id,
            state=result.state,
            message=f"{result.message} Executed in sandboxed parallel worker.",
            evidence=result.evidence,
            duration_seconds=result.duration_seconds,
            diagnostics=diagnostics,
        )


def ordered_ids(scenarios: list[Scenario], ids: set[str]) -> list[str]:
    return [scenario.id for scenario in scenarios if scenario.id in ids]


def _depends_on(scenario: Scenario) -> tuple[str, ...]:
    value = scenario.raw.get("depends_on") or scenario.raw.get("dependencies") or ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return ()


def _resource_compatible_wave(ready: list[Scenario], max_workers: int) -> list[Scenario]:
    wave: list[Scenario] = []
    used_exclusive: set[str] = set()
    for scenario in ready:
        resources = _exclusive_resources_for(scenario)
        if resources & used_exclusive:
            continue
        wave.append(scenario)
        used_exclusive.update(resources)
        if len(wave) >= max_workers:
            break
    return wave or ready[:1]


def _exclusive_resources_for(scenario: Scenario) -> set[str]:
    raw = scenario.raw.get("resources")
    resources: set[str] = set()
    if isinstance(raw, dict):
        exclusive = raw.get("exclusive") or raw.get("exclusive_resources") or ()
        if isinstance(exclusive, str):
            resources.add(exclusive)
        elif isinstance(exclusive, (list, tuple)):
            resources.update(str(item) for item in exclusive)
        if raw.get("persistent_storage"):
            resources.add("persistent_storage")
    requires = scenario.raw.get("requires")
    if isinstance(requires, dict):
        exclusive = requires.get("exclusive_resources") or ()
        if isinstance(exclusive, str):
            resources.add(exclusive)
        elif isinstance(exclusive, (list, tuple)):
            resources.update(str(item) for item in exclusive)
    cleanup = scenario.raw.get("cleanup") or ()
    if cleanup:
        resources.add("cleanup")
    return resources


def _resources_for(scenario: Scenario) -> set[str]:
    resources = set(_exclusive_resources_for(scenario))
    requires = scenario.raw.get("requires")
    if isinstance(requires, dict):
        resources.update(str(item) for item in requires.get("capabilities") or ())
    return resources


def _bounded_workers(value: int) -> int:
    return max(1, min(int(value), 32))


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value).strip("-") or "scenario"
