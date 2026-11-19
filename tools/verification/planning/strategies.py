"""Planning strategies for expanding verification assets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanningStrategy:
    id: str
    default_policy: str
    objective: str
    reduction: str
    max_cases: int | None = None


class PlanningStrategyRegistry:
    def __init__(self) -> None:
        self._strategies = {
            strategy.id: strategy
            for strategy in (
                PlanningStrategy("minimal", "smoke", "lowest runtime sanity planning", "mandatory_only", 25),
                PlanningStrategy("smoke", "smoke", "fast confidence on critical paths", "critical_path", 50),
                PlanningStrategy("regression", "regression", "broad platform confidence", "risk_based", None),
                PlanningStrategy("release", "release_candidate", "release gate confidence", "risk_and_mandatory", None),
                PlanningStrategy("security", "security", "hostile input and auth confidence", "security_risk", None),
                PlanningStrategy("localization", "localization", "locale contract confidence", "representative_locale", None),
                PlanningStrategy("accessibility", "accessibility", "inclusive access confidence", "representative_accessibility", None),
                PlanningStrategy("performance", "nightly", "resource and latency signal", "performance_hotspots", None),
                PlanningStrategy("hardware", "hardware", "physical runtime confidence", "resource_limited", None),
                PlanningStrategy("nightly", "nightly", "maximum practical regression signal", "pairwise_and_risk", None),
                PlanningStrategy("research", "research", "experimental non-blocking signal", "exploratory", None),
            )
        }

    def get(self, strategy_id: str | None) -> PlanningStrategy:
        key = strategy_id or "smoke"
        return self._strategies.get(key, self._strategies["smoke"])

    def all(self) -> tuple[PlanningStrategy, ...]:
        return tuple(self._strategies.values())
