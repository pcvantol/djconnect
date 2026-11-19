"""Result aggregation."""

from __future__ import annotations

from tools.verification.models import ResultState, RunResult, ScenarioResult
from tools.verification.runtime import runtime_metadata


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
        result_metadata = dict(metadata or {})
        result_metadata.setdefault("verification_runtime", runtime_metadata())
        result_metadata.setdefault("execution_summary", _execution_summary(results, state))
        return RunResult(run_id=run_id, state=state, scenario_results=tuple(results), metadata=result_metadata)


def _execution_summary(results: list[ScenarioResult], state: ResultState) -> dict:
    by_status = {item.value: 0 for item in ResultState}
    for result in results:
        by_status[result.state.value] = by_status.get(result.state.value, 0) + 1
    executed = sum(
        count
        for status, count in by_status.items()
        if status not in {ResultState.SKIPPED.value, ResultState.NOT_TESTED.value}
    )
    total_seconds = sum(float(result.duration_seconds or 0.0) for result in results)
    return {
        "total_scenarios": len(results),
        "executed_scenarios": executed,
        "status": state.value,
        "by_status": by_status,
        "total_execution_seconds": total_seconds,
    }
