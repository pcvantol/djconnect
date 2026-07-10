"""Human and machine-readable verification reports."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from .models import RunResult


class MarkdownReporter:
    def render(self, result: RunResult) -> str:
        lines = [
            f"# DJConnect Verification Run {result.run_id}",
            "",
            f"Overall result: {result.state.value}",
            "",
            "| Scenario | Result | Message |",
            "| --- | --- | --- |",
        ]
        for scenario_result in result.scenario_results:
            lines.append(
                f"| {scenario_result.scenario_id} | {scenario_result.state.value} | "
                f"{scenario_result.message} |"
            )
        return "\n".join(lines) + "\n"


class JSONReporter:
    def render(self, result: RunResult) -> str:
        return json.dumps(
            {
                "run_id": result.run_id,
                "state": result.state.value,
                "scenarios": [
                    {
                        "scenario_id": scenario_result.scenario_id,
                        "state": scenario_result.state.value,
                        "message": scenario_result.message,
                    }
                    for scenario_result in result.scenario_results
                ],
                "metadata": result.metadata,
            },
            indent=2,
            sort_keys=True,
        )


class JUnitReporter:
    def render(self, result: RunResult) -> str:
        suite = ET.Element("testsuite", name="djconnect-verification")
        suite.set("tests", str(len(result.scenario_results)))
        failures = 0
        for scenario_result in result.scenario_results:
            case = ET.SubElement(suite, "testcase", name=scenario_result.scenario_id)
            if scenario_result.state.value == "FAIL":
                failures += 1
                failure = ET.SubElement(case, "failure", message=scenario_result.message)
                failure.text = scenario_result.message
        suite.set("failures", str(failures))
        return ET.tostring(suite, encoding="unicode")


class SummaryReporter:
    def render(self, result: RunResult) -> str:
        return f"{result.run_id}: {result.state.value} ({len(result.scenario_results)} scenarios)"
