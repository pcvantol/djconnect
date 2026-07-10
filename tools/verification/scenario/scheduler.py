"""Scenario selection and deterministic scheduling."""

from __future__ import annotations

from tools.verification.models import Scenario


class ScenarioScheduler:
    def select(
        self,
        scenarios: list[Scenario],
        *,
        ids: set[str] | None = None,
        tags: set[str] | None = None,
        components: set[str] | None = None,
    ) -> list[Scenario]:
        selected = scenarios
        if ids:
            selected = [scenario for scenario in selected if scenario.id in ids]
        if tags:
            selected = [
                scenario
                for scenario in selected
                if tags.intersection(set(scenario.raw.get("tags") or ()))
            ]
        if components:
            selected = [
                scenario
                for scenario in selected
                if components.intersection(set(scenario.required_components))
            ]
        return sorted(selected, key=lambda scenario: (scenario.priority, scenario.id))
