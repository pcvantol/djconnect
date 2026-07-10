"""Executable Verification Investigator inside the Verification Core."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


CLASSIFICATIONS = {
    "scenario_defect",
    "scenario_ambiguity",
    "data_generator_defect",
    "matrix_defect",
    "mode_defect",
    "policy_defect",
    "planning_engine_defect",
    "verification_core_defect",
    "execution_environment_defect",
    "ha_adapter_defect",
    "product_implementation_defect",
    "technical_design_mismatch",
    "foundation_mismatch",
    "environment_issue",
    "ci_qualification_issue",
    "documentation_issue",
    "unknown",
}


@dataclass(frozen=True)
class InvestigationResult:
    failure_id: str
    run_id: str
    scenario_id: str
    test_case_id: str
    classification: str
    confidence: float
    evidence_references: tuple[str, ...]
    probable_owner: str
    owning_repository: str
    blocking_status: str
    recommended_action: str
    rerun_scope: str
    regression_scope: str
    human_review_required: bool
    notes: str = ""


class VerificationInvestigator:
    def investigate_bundle(
        self,
        bundle: dict[str, Any],
        *,
        scenario_id: str | None = None,
        failure_id: str | None = None,
    ) -> tuple[InvestigationResult, ...]:
        run_id = str(bundle.get("run_id") or bundle.get("metadata", {}).get("run_id") or "unknown-run")
        failures = _failure_items(bundle)
        results: list[InvestigationResult] = []
        for index, item in enumerate(failures, start=1):
            current_failure_id = str(item.get("failure_id") or f"failure-{index:03d}")
            current_scenario_id = str(item.get("scenario_id") or "")
            if scenario_id and current_scenario_id != scenario_id:
                continue
            if failure_id and current_failure_id != failure_id:
                continue
            results.append(self._classify(run_id, current_failure_id, item))
        if not results and not (scenario_id or failure_id):
            results.append(
                InvestigationResult(
                    failure_id="failure-001",
                    run_id=run_id,
                    scenario_id="",
                    test_case_id="",
                    classification="unknown",
                    confidence=0.2,
                    evidence_references=("bundle",),
                    probable_owner="Verification Core",
                    owning_repository="pcvantol/djconnect",
                    blocking_status="needs_human_review",
                    recommended_action="Add more evidence or inspect the failed run manually.",
                    rerun_scope="none",
                    regression_scope="verification",
                    human_review_required=True,
                    notes="No explicit failure item was found in the evidence bundle.",
                )
            )
        return tuple(results)

    def investigate_file(
        self,
        path: Path,
        *,
        scenario_id: str | None = None,
        failure_id: str | None = None,
    ) -> tuple[InvestigationResult, ...]:
        return self.investigate_bundle(json.loads(path.read_text(encoding="utf-8")), scenario_id=scenario_id, failure_id=failure_id)

    def _classify(self, run_id: str, failure_id: str, item: dict[str, Any]) -> InvestigationResult:
        text = json.dumps(item, sort_keys=True).lower()
        scenario_id = str(item.get("scenario_id") or "")
        test_case_id = str(item.get("test_case_id") or "")
        evidence_refs = tuple(str(ref) for ref in item.get("evidence_references") or ("summary",))
        if "github" in text or "ci_" in text or "ci auth" in text or "gh auth" in text:
            return _result(run_id, failure_id, scenario_id, test_case_id, "ci_qualification_issue", 0.9, evidence_refs, "Verification Execution Environment", "Re-authenticate GitHub CLI or configure an approved token source.", "qualification")
        if "docker" in text or "home assistant runtime" in text or "ha runtime" in text or "storage_dir" in text:
            return _result(run_id, failure_id, scenario_id, test_case_id, "environment_issue", 0.85, evidence_refs, "Verification Execution Environment", "Start and qualify the intended Docker Home Assistant development runtime.", "affected_scenario")
        if "websocket" in text:
            return _result(run_id, failure_id, scenario_id, test_case_id, "ha_adapter_defect", 0.8, evidence_refs, "Home Assistant Verification Adapter", "Qualify or inject a live websocket transport and rerun the affected scenario.", "affected_scenario")
        if "snapshot_storage" in text or "storage" in text:
            return _result(run_id, failure_id, scenario_id, test_case_id, "environment_issue", 0.75, evidence_refs, "Verification Execution Environment", "Configure approved HA storage path and rerun storage probe.", "affected_scenario")
        if "plan" in text and "selection" in text:
            return _result(run_id, failure_id, scenario_id, test_case_id, "planning_engine_defect", 0.75, evidence_refs, "Verification Planning Engine", "Fix scenario selection or matrix/data expansion.", "planning")
        if "assertion" in text or "expected" in text:
            return _result(run_id, failure_id, scenario_id, test_case_id, "product_implementation_defect", 0.55, evidence_refs, "DJConnect Implementation", "Review product behavior against Technical Design.", "affected_scenario", human_review=True)
        if "ambiguous" in text:
            return _result(run_id, failure_id, scenario_id, test_case_id, "scenario_ambiguity", 0.7, evidence_refs, "Scenario Catalog", "Clarify scenario wording without changing accepted behavior.", "scenario_validation", human_review=True)
        return _result(run_id, failure_id, scenario_id, test_case_id, "unknown", 0.25, evidence_refs, "Verification Core", "Collect additional evidence and classify manually.", "none", human_review=True)


def _failure_items(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(bundle.get("failures"), list):
        return [item for item in bundle["failures"] if isinstance(item, dict)]
    items: list[dict[str, Any]] = []
    for result in bundle.get("scenario_results") or []:
        if isinstance(result, dict) and result.get("state") not in {None, "PASS", "SKIPPED", "NOT TESTED"}:
            items.append(result)
    return items


def _result(
    run_id: str,
    failure_id: str,
    scenario_id: str,
    test_case_id: str,
    classification: str,
    confidence: float,
    evidence_refs: tuple[str, ...],
    owner: str,
    action: str,
    rerun_scope: str,
    *,
    human_review: bool | None = None,
) -> InvestigationResult:
    return InvestigationResult(
        failure_id=failure_id,
        run_id=run_id,
        scenario_id=scenario_id,
        test_case_id=test_case_id,
        classification=classification if classification in CLASSIFICATIONS else "unknown",
        confidence=confidence,
        evidence_references=evidence_refs,
        probable_owner=owner,
        owning_repository="pcvantol/djconnect",
        blocking_status="blocking" if confidence >= 0.7 else "needs_human_review",
        recommended_action=action,
        rerun_scope=rerun_scope,
        regression_scope="tests/verification",
        human_review_required=(confidence < 0.7) if human_review is None else human_review,
    )


def investigation_to_dicts(results: tuple[InvestigationResult, ...]) -> list[dict[str, Any]]:
    return [asdict(result) for result in results]
