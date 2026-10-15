"""Run directed Cast/renderer lifecycle contracts in the regular CI suite."""

from pathlib import Path
import shutil
import subprocess
import unittest


class CastStatusTest(unittest.TestCase):
    def test_cast_status_lifecycle(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required for renderer contract execution")
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [node, "--test", str(root / "tests/browser/vibecast_cast_status.mjs")],
            cwd=root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
