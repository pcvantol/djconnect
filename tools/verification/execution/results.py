"""Result aggregation."""

from __future__ import annotations

from tools.verification.models import ResultState, RunResult, ScenarioResult


class ResultAggregator:
    def aggregate(self, run_id: str, results: list[ScenarioResult], metadata: dict | None = None) -> RunResult:
        state = ResultState.PASS
        if any(result.state == ResultState.FAIL for result in results):
            state = ResultState.FAIL
        elif any(result.state == ResultState.WARNING for result in results):
            state = ResultState.WARNING
        elif any(result.state == ResultState.SKIPPED for result in results):
            state = ResultState.SKIPPED
        elif not results or all(result.state == ResultState.NOT_TESTED for result in results):
            state = ResultState.NOT_TESTED
        return RunResult(run_id=run_id, state=state, scenario_results=tuple(results), metadata=metadata or {})
