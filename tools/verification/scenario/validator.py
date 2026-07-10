"""Scenario schema validation."""

from __future__ import annotations

import re

from tools.verification.models import Scenario, ValidationIssue
from tools.verification.lab import LabCatalog

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
    "requires",
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
    def __init__(self, root=None) -> None:
        self.root = root
        self._lab_catalog = LabCatalog(root) if root else None

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
        lab_catalog = self._lab_catalog
        if lab_catalog is None and scenario.source:
            lab_catalog = LabCatalog(scenario.source.parents[3])
        if lab_catalog:
            for message in lab_catalog.validate_scenario(scenario):
                issues.append(ValidationIssue("error", message, scenario.source))
        return issues
