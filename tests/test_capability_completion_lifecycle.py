"""Regression coverage for the canonical Capability Completion Lifecycle."""

from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
