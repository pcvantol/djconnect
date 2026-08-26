"""Regression coverage for the Engineering Platform coverage quality gate."""

from __future__ import annotations

from pathlib import Path
import unittest


class EngineeringPlatformCoverageContractTests(unittest.TestCase):
    """Keep the CI contract aligned with the explicit quality threshold."""

    def test_coverage_gate_requires_strictly_more_than_eighty_percent(self) -> None:
        workflow = Path(".github/workflows/engineering-platform-validation.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("minimum = 80.20", workflow)
        self.assertIn('minimum 80.20%', workflow)
        self.assertIn("covered is None or covered < minimum", workflow)

    def test_browser_dashboard_validation_uses_four_parallel_shards(self) -> None:
        workflow = Path(".github/workflows/engineering-platform-validation.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn('shard: "1/4"', workflow)
        self.assertIn('shard: "4/4"', workflow)
        self.assertIn("max-parallel: 4", workflow)
        self.assertIn("--shard=${{ matrix.shard }}", workflow)
        self.assertIn("engineering-status-browser-screenshots-${{ matrix.artifact_suffix }}", workflow)
