"""Platform readiness calculation from aggregate results."""

from __future__ import annotations

from tools.verification.models import ResultState, RunResult


class PlatformReadinessCalculator:
    def calculate(self, result: RunResult) -> dict[str, float | int | str]:
        total = len(result.scenario_results)
        passed = sum(1 for item in result.scenario_results if item.state == ResultState.PASS)
        failed = sum(1 for item in result.scenario_results if item.state == ResultState.FAIL)
        tested = sum(
            1
            for item in result.scenario_results
            if item.state not in {ResultState.NOT_TESTED, ResultState.SKIPPED}
        )
        score = 0.0 if total == 0 else round((passed / total) * 100, 2)
        status = "ready" if total and failed == 0 and tested == total else "not_ready"
        return {"status": status, "score": score, "total": total, "tested": tested, "failed": failed}
