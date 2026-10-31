"""Hermetic process/coverage regressions for the offline CI runner."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.run_parallel_unittest import CoverageData, validate_coverage_data


RUNNER = Path(__file__).resolve().parents[1] / "tools/run_parallel_unittest.py"


class ParallelRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tests = self.root / "cases"
        self.tests.mkdir()

    def module(self, name, body):
        (self.tests / f"test_{name}.py").write_text(body)

    def run_suite(self, *flags, name="report"):
        report = self.root / name
        env = dict(os.environ)
        # A coverage test nested in an instrumented CI worker must own its data.
        env.pop("COVERAGE_FILE", None)
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--start-directory", str(self.tests),
             "--jobs", "2", "--report-dir", str(report), *flags],
            cwd=self.root, env=env, capture_output=True, text=True, timeout=30,
        )
        return result, report

    def test_parallel_overlap_temp_isolation_and_module_fixtures(self):
        for name in ("a", "b"):
            self.module(name, f'''
import json, os, tempfile, time, unittest
from pathlib import Path
root = Path({str(self.root)!r})
def setUpModule():
    (root / "{name}.ready").touch()
    deadline = time.monotonic() + 10
    while not all((root / (n + ".ready")).exists() for n in ("a", "b")):
        if time.monotonic() > deadline:
            raise RuntimeError("workers did not overlap")
        time.sleep(.01)
    (root / "{name}.temp").write_text(tempfile.gettempdir())
class Cases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = []
    def test_first(self):
        self.state.append("first")
    def test_second(self):
        self.assertEqual(self.state, ["first"])
''')
        result, report = self.run_suite()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads((report / "summary.json").read_text())
        self.assertEqual((summary["discovered"], summary["tests_run"], summary["workers"]),
                         (4, 4, 2))
        temps = [(self.root / f"{name}.temp").read_text() for name in ("a", "b")]
        self.assertNotEqual(*temps)
        self.assertTrue(all(Path(value).parent == report for value in temps))
        plan = json.loads((report / "plan.json").read_text())
        started = [test_id for index in range(2) for test_id in
                   json.loads((report / f"worker-{index}.json").read_text())["started"]]
        self.assertCountEqual(started, plan["discovered"])

    def test_failure_skip_expected_failure_and_subtest_are_not_hidden(self):
        self.module("outcomes", '''
import unittest
class Cases(unittest.TestCase):
    def test_bad(self):
        with self.subTest("failure"):
            self.fail("synthetic failure")
    @unittest.skip("existing synthetic skip")
    def test_skip(self): pass
    @unittest.expectedFailure
    def test_expected(self): self.fail("expected")
''')
        result, report = self.run_suite()
        self.assertEqual(result.returncode, 1)
        summary = json.loads((report / "summary.json").read_text())
        self.assertFalse(summary["success"])
        self.assertEqual((summary["tests_run"], summary["skipped"]), (3, 1))
        worker = json.loads((report / "worker-0.json").read_text())
        self.assertEqual((worker["failures"], worker["expected_failures"]), (1, 1))
        self.assertIn("synthetic failure", result.stdout)

    def test_import_error_and_process_crash_fail_closed(self):
        for name, body in (("import", 'raise RuntimeError("discovery failed")'),
                           ("crash", 'import os, unittest\nclass Cases(unittest.TestCase):\n'
                            '    def test_crash(self): os._exit(23)\n')):
            with self.subTest(name=name):
                self.module("broken", body)
                result, report = self.run_suite(name=name)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(json.loads((report / "summary.json").read_text())["success"])

    def test_empty_discovery_and_reused_evidence_directory_are_rejected(self):
        result, _ = self.run_suite()
        self.assertNotEqual(result.returncode, 0)
        self.module("ok", 'import unittest\nclass Cases(unittest.TestCase):\n'
                    '    def test_ok(self): pass\n')
        result, report = self.run_suite(name="fresh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        before = (report / "summary.json").read_bytes()
        result, _ = self.run_suite(name="fresh")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((report / "summary.json").read_bytes(), before)

    def test_class_and_module_fixture_skip_account_for_all_selected_tests(self):
        self.module("class_skip", '''
import unittest
class Cases(unittest.TestCase):
    @classmethod
    def setUpClass(cls): raise unittest.SkipTest("class fixture skip")
    def test_one(self): self.fail("must not run")
    def test_two(self): self.fail("must not run")
''')
        self.module("module_skip", '''
import unittest
def setUpModule(): raise unittest.SkipTest("module fixture skip")
class Cases(unittest.TestCase):
    def test_one(self): self.fail("must not run")
''')
        result, report = self.run_suite()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads((report / "summary.json").read_text())
        self.assertEqual((summary["discovered"], summary["tests_run"],
                          summary["accounted"], summary["skipped"]), (3, 0, 3, 3))

    def test_coverage_combines_both_workers_and_preserves_raw_data(self):
        for name in ("a", "b"):
            self.module(name, 'import unittest\nclass Cases(unittest.TestCase):\n'
                        f'    def test_{name}(self):\n        self.assertTrue(True)\n')
        result, report = self.run_suite("--coverage")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        names = {item.attrib["filename"] for item in
                 ET.parse(report / "coverage.xml").iter("class")}
        self.assertTrue({"cases/test_a.py", "cases/test_b.py"}.issubset(names), names)
        for item in ET.parse(report / "coverage.xml").iter("class"):
            if item.attrib["filename"] in {"cases/test_a.py", "cases/test_b.py"}:
                self.assertTrue(any(line.attrib["number"] == "4" and int(line.attrib["hits"]) > 0
                                    for line in item.iter("line")), item.attrib)
        self.assertEqual(len(list(report.glob(".coverage.*"))), 2)
        self.assertTrue((report / ".coverage").is_file())

    def test_missing_corrupt_and_incompatible_worker_coverage_fail_closed(self):
        for index in range(2):
            data = CoverageData(basename=str(self.root / f".coverage.worker-{index}"))
            data.add_lines({f"synthetic-{index}.py": {1}})
            data.write()
        validate_coverage_data(self.root, 2)
        raw = self.root / ".coverage.worker-1"
        original = raw.read_bytes()
        raw.unlink()
        with self.assertRaises(ValueError):
            validate_coverage_data(self.root, 2)
        raw.write_bytes(b"not coverage SQLite")
        with self.assertRaises(Exception):
            validate_coverage_data(self.root, 2)
        raw.write_bytes(original)
        raw.unlink()
        data = CoverageData(basename=str(raw))
        data.add_arcs({"synthetic-1.py": {(1, 2)}})
        data.write()
        with self.assertRaises(ValueError):
            validate_coverage_data(self.root, 2)
