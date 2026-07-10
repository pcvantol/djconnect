"""Human and machine-readable reports."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from tools.verification.models import RunResult
from tools.verification.reporting.readiness import PlatformReadinessCalculator


class MarkdownReporter:
    def render(self, result: RunResult) -> str:
        readiness = PlatformReadinessCalculator().calculate(result)
        lines = [
            f"# DJConnect Verification Run {result.run_id}",
            "",
            f"Overall result: {result.state.value}",
            f"Readiness: {readiness['status']} ({readiness['score']}%)",
            "",
            "## Summary",
            "",
            "| Scenario | Result | Message |",
            "| --- | --- | --- |",
        ]
        for scenario_result in result.scenario_results:
            lines.append(
                f"| {scenario_result.scenario_id} | {scenario_result.state.value} | "
                f"{scenario_result.message} |"
            )
        failures = [item for item in result.scenario_results if item.state.value == "FAIL"]
        if failures:
            lines.extend(["", "## Failure Index", ""])
            lines.extend(f"- {item.scenario_id}: {item.message}" for item in failures)
        lines.extend(["", "## History", "", "Trend-ready history is captured in the JSON report metadata."])
        return "\n".join(lines) + "\n"


class JSONReporter:
    def render(self, result: RunResult) -> str:
        return json.dumps(
            {
                "run_id": result.run_id,
                "state": result.state.value,
                "readiness": PlatformReadinessCalculator().calculate(result),
                "scenarios": [
                    {
                        "scenario_id": item.scenario_id,
                        "state": item.state.value,
                        "message": item.message,
                        "duration_seconds": item.duration_seconds,
                        "evidence": [
                            {"kind": evidence.kind, "path": str(evidence.path), "metadata": evidence.metadata}
                            for evidence in item.evidence
                        ],
                    }
                    for item in result.scenario_results
                ],
                "metadata": result.metadata,
                "history": {"schema_version": 1, "trend_ready": True},
            },
            indent=2,
            sort_keys=True,
        )


class JUnitReporter:
    def render(self, result: RunResult) -> str:
        suite = ET.Element("testsuite", name="djconnect-verification")
        suite.set("tests", str(len(result.scenario_results)))
        failures = 0
        skipped = 0
        for item in result.scenario_results:
            case = ET.SubElement(suite, "testcase", name=item.scenario_id, time=str(item.duration_seconds))
            if item.state.value == "FAIL":
                failures += 1
                failure = ET.SubElement(case, "failure", message=item.message)
                failure.text = item.message
            elif item.state.value in {"SKIPPED", "NOT TESTED"}:
                skipped += 1
                ET.SubElement(case, "skipped", message=item.message)
        suite.set("failures", str(failures))
        suite.set("skipped", str(skipped))
        return ET.tostring(suite, encoding="unicode")


class SummaryReporter:
    def render(self, result: RunResult) -> str:
        return f"{result.run_id}: {result.state.value} ({len(result.scenario_results)} scenarios)"
