"""Regression coverage for Golden Scenario governance records."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GoldenScenarioGovernanceTest(unittest.TestCase):
    """Keep product-behavior and no-duplicate-path governance explicit."""

    def test_policy_covers_required_relationships_and_boundaries(self) -> None:
        contents = (
            ROOT / "docs/verification/GOLDEN_SCENARIO_GOVERNANCE.md"
        ).read_text()

        for required in (
            "Observable product behavior",
            "enable",
            "execute",
            "capture",
            "validate",
            "protect",
            "preserves",
            "extends",
            "introduces",
            "second Runtime",
            "second Runtime, Scenario Driver or verification path",
            "Quality metrics stay advisory",
            "user-visible behavior needs protection?",
        ):
            self.assertIn(required, contents)

    def test_canonical_preflight_records_require_governance_check(self) -> None:
        template = (ROOT / "docs/governance/PROMPT_TEMPLATE.md").read_text()
        initialization = (ROOT / "PROMPT_INITIALIZATION.md").read_text()

        self.assertIn("Golden Scenario Governance:", template)
        self.assertIn("Behavioral Contract Preservation:", template)
        self.assertIn("Golden Scenario Governance Check", initialization)
        self.assertIn("duplicate Runtime, Scenario Driver", initialization)

    def test_navigation_and_existing_policy_link_the_canonical_policy(self) -> None:
        for name in (
            "ROADMAP_INDEX.md",
            "docs/product/DEVELOPER_EXPERIENCE_ROADMAP.md",
            "docs/verification/SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md",
            "docs/verification/SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md",
            "docs/verification/03_SCENARIO_CATALOG.md",
        ):
            self.assertIn(
                "GOLDEN_SCENARIO_GOVERNANCE.md", (ROOT / name).read_text(), name
            )


if __name__ == "__main__":
    unittest.main()
