"""Regression coverage for the canonical Capability Completion Lifecycle."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CapabilityCompletionLifecycleTest(unittest.TestCase):
    """Keep the cross-document governance contract internally consistent."""

    def test_method_requires_complete_lifecycle_and_repository_state_gate(self) -> None:
        contents = (ROOT / "ENGINEERING_METHOD.md").read_text()

        for required in (
            "Capability Completion Lifecycle",
            "PRE-FLIGHT",
            "IMPLEMENTATION",
            "VALIDATION",
            "FINALIZATION",
            "MERGED_UNRECONCILED",
            "MERGED_RECONCILED",
            "GO",
            "NO-GO",
            "permits only the dedicated Finalization increment",
        ):
            self.assertIn(required, contents)

    def test_prompt_template_requires_the_canonical_sections(self) -> None:
        contents = (ROOT / "docs/governance/PROMPT_TEMPLATE.md").read_text()

        for required in (
            "PRE-FLIGHT",
            "IMPLEMENTATION:",
            "VALIDATION:",
            "Finalization:",
            "MERGED_RECONCILED",
            "NO-GO",
        ):
            self.assertIn(required, contents)

    def test_operational_contracts_allow_finalization_only_when_unreconciled(self) -> None:
        for name in (
            "BOOTSTRAP.md",
            "PROMPT_INITIALIZATION.md",
            "PROMPT_GOVERNANCE.md",
            "PROMPT_FINALIZATION.md",
            "REPOSITORY_SYNCHRONIZATION.md",
        ):
            contents = (ROOT / name).read_text()
            self.assertIn("MERGED_UNRECONCILED", contents, name)
            self.assertIn("MERGED_RECONCILED", contents, name)

        expected_finalization_gate = {
            "BOOTSTRAP.md": "only the dedicated Finalization",
            "PROMPT_INITIALIZATION.md": "dedicated Finalization increment may reconcile",
            "PROMPT_GOVERNANCE.md": "only its dedicated Finalization",
        }
        for name, required in expected_finalization_gate.items():
            self.assertIn(required, (ROOT / name).read_text(), name)

    def test_finalization_validation_requires_current_rolling_record_evidence(self) -> None:
        """Make stale status/index references fail the focused lifecycle gate."""
        engineering_status = (ROOT / "ENGINEERING_STATUS.md").read_text()
        current_section = re.search(
            r"## Current engineering increment\n\n(?P<contents>.*?)(?=\n## |\Z)",
            engineering_status,
            re.DOTALL,
        )
        self.assertIsNotNone(current_section)
        assert current_section is not None
        current_increment = re.search(
            r"PR \[#(?P<number>\d+)\].*?merged as\s+`(?P<commit>[0-9a-f]{40})`",
            current_section.group("contents"),
            re.DOTALL,
        )
        self.assertIsNotNone(current_increment)
        assert current_increment is not None

        for name in (
            "REPOSITORY_STATUS.md",
            "MANAGEMENT_SUMMARY.md",
            "PROMPT_INDEX.md",
        ):
            contents = (ROOT / name).read_text()
            self.assertIn(f"PR [#{current_increment.group('number')}]", contents, name)
            self.assertIn(current_increment.group("commit"), contents, name)

    def test_rendered_execution_horizons_are_consistent(self) -> None:
        """Keep the two canonical rendered horizons from drifting apart."""
        horizons = {}
        for name, heading_level in (
            ("ENGINEERING_STATUS.md", "####"),
            ("MANAGEMENT_SUMMARY.md", "###"),
        ):
            contents = (ROOT / name).read_text()
            section = re.search(
                rf"^{heading_level} Rolling Horizon \(Execution Horizon — Next 5 Planned\)\n"
                r"\n(?P<contents>.*?)(?=\n" + heading_level + r" |\Z)",
                contents,
                re.DOTALL | re.MULTILINE,
            )
            self.assertIsNotNone(section, name)
            assert section is not None
            horizons[name] = re.findall(
                r"^\d+\. \*\*(?P<item>.+?) —",
                section.group("contents"),
                re.MULTILINE,
            )
            self.assertEqual(5, len(horizons[name]), name)

        self.assertEqual(
            horizons["ENGINEERING_STATUS.md"],
            horizons["MANAGEMENT_SUMMARY.md"],
        )

    def test_finalization_requires_the_canonical_rolling_horizon(self) -> None:
        method = (ROOT / "ENGINEERING_METHOD.md").read_text()
        template = (ROOT / "docs/governance/PROMPT_TEMPLATE.md").read_text()

        for required in (
            "Rolling Horizon (Next 5 Planned)",
            "Blocked Items",
            "Deferred Items",
            "next five actually authorized execution items",
            "Deferred`, `Blocked`, `Completed`",
            "derived afresh from the canonical repository backlog records",
            "advances automatically",
        ):
            self.assertIn(required, method)
        self.assertIn("Finalization Rolling Horizon standard", template)
        self.assertIn("exclude Deferred and Blocked items", template)

    def test_finalization_requires_pre_push_consistency_validation(self) -> None:
        method = (ROOT / "ENGINEERING_METHOD.md").read_text()
        finalization = (ROOT / "PROMPT_FINALIZATION.md").read_text()
        template = (ROOT / "docs/governance/PROMPT_TEMPLATE.md").read_text()

        for contents, name in (
            (method, "ENGINEERING_METHOD.md"),
            (finalization, "PROMPT_FINALIZATION.md"),
            (template, "PROMPT_TEMPLATE.md"),
        ):
            self.assertIn("Finalization pre-push consistency check", contents, name)
            self.assertIn("tests.test_capability_completion_lifecycle", contents, name)


if __name__ == "__main__":
    unittest.main()
