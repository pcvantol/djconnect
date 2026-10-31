"""Run the complete unittest discovery in bounded, process-isolated module shards.

No test selection flags: the plan and every worker independently discover the
same suite. Class/module fixtures remain together, and reports reconcile every
discovered test ID before success. Only offline unittest suites belong here.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

from coverage import CoverageData


def cases(suite):
    if isinstance(suite, unittest.TestCase):
        yield suite
    elif type(suite) is unittest.TestSuite:
        for child in suite:
            yield from cases(child)
    else:
        raise ValueError(f"Unsupported custom suite: {type(suite).__name__}")


def discover(start):
    sys.path.insert(0, str(Path.cwd()))
    return list(cases(unittest.defaultTestLoader.discover(start)))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def validate_coverage_data(directory, workers):
    expected = {directory / f".coverage.worker-{index}" for index in range(workers)}
    if set(directory.glob(".coverage.*")) != expected:
        raise ValueError("Missing or unexpected worker coverage data")
    modes = set()
    for path in sorted(expected):
        data = CoverageData(basename=str(path))
        data.read()
        if not data.measured_files() or not any(data.lines(name) for name in data.measured_files()):
            raise ValueError("Empty worker coverage data")
        modes.add(data.has_arcs())
    if len(modes) != 1:
        raise ValueError("Incompatible worker coverage modes")


def worker(args):
    plan = json.loads((args.report_dir / "plan.json").read_text())
    discovered = discover(args.start_directory)
    if [test.id() for test in discovered] != plan["discovered"]:
        raise ValueError("Worker discovery differs from original plan")
    selected = plan["shards"][args.worker]
    selected_set = set(selected)
    tests = [test for test in discovered if test.id() in selected_set]
    started = []

    class Result(unittest.TextTestResult):
        def startTest(self, test):
            started.append(test.id())
            super().startTest(test)

    begin = time.monotonic()
    result = unittest.TextTestRunner(resultclass=Result, verbosity=1).run(
        unittest.TestSuite(tests)
    )
    # unittest does not call startTest for a class/module fixture SkipTest.
    fixture_skips = []
    for test, _ in result.skipped:
        if not isinstance(test, unittest.TestCase):
            marker = test.id()
            for kind in ("setUpClass", "setUpModule"):
                if marker.startswith(kind + " (") and marker.endswith(")"):
                    prefix = marker[len(kind) + 2:-1] + "."
                    fixture_skips.extend(test_id for test_id in selected
                                         if test_id.startswith(prefix))
    complete = (Counter(started + fixture_skips) == Counter(selected)
                and result.testsRun == len(started))
    report = {
        "planned": selected, "started": started, "tests_run": result.testsRun,
        "fixture_skips": fixture_skips,
        "skipped": [test.id() for test, _ in result.skipped
                    if isinstance(test, unittest.TestCase)] + fixture_skips,
        "failures": len(result.failures), "errors": len(result.errors),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "elapsed_seconds": time.monotonic() - begin,
        "success": complete and result.wasSuccessful(),
    }
    write_json(args.report_dir / f"worker-{args.worker}.json", report)
    return 0 if report["success"] else 1


def run(args):
    # Exclusive directory prevents stale evidence or coverage from another run.
    args.report_dir.mkdir(parents=True, exist_ok=False)
    tests = discover(args.start_directory)
    ids = [test.id() for test in tests]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Discovery must contain nonempty unique test IDs")
    modules = {}
    for test in tests:
        modules.setdefault(type(test).__module__, []).append(test.id())
    shards = [[] for _ in range(min(args.jobs, len(modules)))]
    # Largest modules first; retain original discovery order within each shard.
    for module in sorted(modules, key=lambda name: (-len(modules[name]), name)):
        min(shards, key=len).extend(modules[module])
    order = {test_id: index for index, test_id in enumerate(ids)}
    for shard in shards:
        shard.sort(key=order.__getitem__)
    write_json(args.report_dir / "plan.json", {"discovered": ids, "shards": shards})
    script = str(Path(__file__).resolve())

    def launch(index):
        temp = args.report_dir / f"tmp-{index}"
        temp.mkdir()
        env = dict(os.environ, TMPDIR=str(temp), TEMP=str(temp), TMP=str(temp))
        command = [sys.executable]
        if args.coverage:
            env["COVERAGE_FILE"] = str(args.report_dir / f".coverage.worker-{index}")
            command += ["-m", "coverage", "run"]
        command += [script, "--start-directory", args.start_directory,
                    "--report-dir", str(args.report_dir), "--worker", str(index)]
        with (args.report_dir / f"worker-{index}.log").open("w") as log:
            completed = subprocess.run(command, env=env, stdout=log, stderr=log, check=False)
        return completed.returncode

    begin = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(shards)) as pool:
        codes = list(pool.map(launch, range(len(shards))))
    reports = []
    for index in range(len(shards)):
        path = args.report_dir / f"worker-{index}.json"
        reports.append(json.loads(path.read_text()) if path.exists() else {})
    started = [test_id for report in reports for test_id in report.get("started", [])]
    accounted = started + [test_id for report in reports
                           for test_id in report.get("fixture_skips", [])]
    success = (all(code == 0 for code in codes)
               and all(report.get("success") for report in reports)
               and Counter(accounted) == Counter(ids))
    summary = {
        "success": success and not args.coverage,
        "tests_success": success, "coverage_requested": args.coverage,
        "discovered": len(ids), "tests_run": len(started), "accounted": len(accounted),
        "workers": len(shards), "exit_codes": codes,
        "skipped": sum(len(report.get("skipped", [])) for report in reports),
        "elapsed_seconds": time.monotonic() - begin,
    }
    write_json(args.report_dir / "summary.json", summary)
    if not success:
        print(json.dumps(summary), flush=True)
        for index, report in enumerate(reports):
            if not report.get("success") or codes[index]:
                print((args.report_dir / f"worker-{index}.log").read_text())
        return 1
    if args.coverage:
        env = dict(os.environ, COVERAGE_FILE=str(args.report_dir / ".coverage"))
        validate_coverage_data(args.report_dir, len(shards))
        subprocess.run([sys.executable, "-m", "coverage", "combine", "--keep",
                        str(args.report_dir)], env=env, check=True)
        subprocess.run([sys.executable, "-m", "coverage", "xml", "--keep-combined",
                        "-o", str(args.report_dir / "coverage.xml")],
                       env=env, check=True)
        summary["success"] = True
        write_json(args.report_dir / "summary.json", summary)
    print(json.dumps(summary), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-directory", default="tests")
    parser.add_argument("--jobs", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--report-dir", type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--worker", type=int, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    return worker(args) if args.worker is not None else run(args)


if __name__ == "__main__":
    raise SystemExit(main())
