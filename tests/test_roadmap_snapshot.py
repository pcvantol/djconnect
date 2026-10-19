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
            [sys.executable, "-m", "unittest", "-q", "test_snapshot", "test_maintenance_delta"],
            cwd=PLANNING,
            capture_output=True,
            text=True,
            # The maintained graph now validates all historical deltas plus
            # 171 schema/negative/generation cases. Shared Python3.11 runners
            # exceed30s; retain every assertion with a bounded execution limit.
            timeout=120,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
