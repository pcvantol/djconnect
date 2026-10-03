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
            [sys.executable, "-m", "unittest", "-q", "test_snapshot"],
            cwd=PLANNING,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
