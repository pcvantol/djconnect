"""Run the federated planning checks through the repository's existing CI suite."""

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLANNING = ROOT / "docs" / "roadmap" / "v1"


class FederatedPlanningCITest(unittest.TestCase):
    def test_snapshot_validator_and_negative_cases(self):
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-q"],
            cwd=PLANNING,
            capture_output=True,
            text=True,
            # Discover every maintained schema/negative/generation module.
            # The expanded198-case suite exceeds120s on shared Python3.11 CI
            # beside the other three workers. Keep every assertion and allow
            # a bounded five-minute subprocess instead of truncating discovery.
            timeout=300,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
