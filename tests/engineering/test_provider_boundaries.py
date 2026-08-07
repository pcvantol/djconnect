from __future__ import annotations

from pathlib import Path
import unittest


class ProviderBoundaryTest(unittest.TestCase):
    def test_execution_lifecycle_modules_do_not_spawn_processes_directly(self) -> None:
        engineering = Path(__file__).parents[2] / "tools" / "engineering"
        for name in ("execution_host.py", "inbox_watcher.py"):
            source = (engineering / name).read_text(encoding="utf-8")
            self.assertNotIn("subprocess.run(", source, name)
            self.assertNotIn("subprocess.Popen(", source, name)
