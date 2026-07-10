"""Scenario schema validation."""

from __future__ import annotations

import re

from tools.verification.models import Scenario, ValidationIssue

SCENARIO_ID_PATTERN = re.compile(r"^[A-Z]+-[0-9]{3}$")
REQUIRED_FIELDS = {
    "id",
    "title",
    "description",
    "purpose",
    "owner",
    "category",
    "priority",
    "risk",
    "verification_level",
    "automation_level",
    "required_components",
    "supported_platforms",
    "required_locales",
    "required_build_types",
    "preconditions",
    "setup",
    "steps",
    "assertions",
    "expected_results",
    "cleanup",
    "timeouts",
    "retry_policy",
    "artifacts",
    "privacy_classification",
    "destructive",
    "tags",
    "estimated_duration",
    "version",
    "schema_version",
}


class ScenarioValidator:
    def validate(self, scenario: Scenario) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for field in sorted(REQUIRED_FIELDS - set(scenario.raw)):
            issues.append(ValidationIssue("error", f"Missing required field: {field}", scenario.source))
        if not SCENARIO_ID_PATTERN.match(scenario.id):
            issues.append(ValidationIssue("error", f"Invalid scenario id: {scenario.id}", scenario.source))
        if not scenario.required_components:
            issues.append(
                ValidationIssue("error", "Scenario must require at least one component", scenario.source)
            )
        for field in ("steps", "artifacts"):
            if field in scenario.raw and not isinstance(scenario.raw[field], list):
                issues.append(ValidationIssue("error", f"{field} must be a list", scenario.source))
        return issues
