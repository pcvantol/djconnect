"""Exact-base/current Runtime sequences, mocked producer replies and time only."""

import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
ContextualFactPlanningTest = importlib.import_module("tests.test_contextual_fact_planning").ContextualFactPlanningTest

BASE = "4c30399294b56aff89b962a53b37ea91a2d1762f"
RUNTIME = "custom_components/djconnect/session_runtime.py"
FACTS = "custom_components/djconnect/session_facts.py"


def capture():
    ContextualFactPlanningTest.setUpClass()
    try:
        fixture = ContextualFactPlanningTest()
        pool = fixture.pool()
        scenarios = {
            "manual": (pool, {}),
            "reversed": (tuple(reversed(pool)), {}),
            "discover": (pool, {"discover": True}),
            "calm": (pool, {"mood": "chill"}),
            "short_fit": (tuple(reversed(fixture.pool(long=True)[:2])), {"duration": 50000, "positions": (0,)}),
        }
        after = {}
        for name, (facts, args) in scenarios.items():
            fixture.run_session(facts, **{"positions": (0, 15000, 30000, 45000, 50000, 60000, 75000, 90000, 100000), **args})
            after[name] = fixture.last_capture
        # Execute the exact original Runtime and fact qualifier, not a rebuilt
        # approximation of its selection helper. Dependencies remain stubbed by
        # the existing Runtime test harness; only valid producer fields are used.
        for relative, module in ((FACTS, fixture.facts), (RUNTIME, fixture.runtime)):
            original = subprocess.check_output(["git", "show", f"{BASE}:{relative}"], cwd=ROOT, text=True)
            exec(compile(original, f"{BASE}:{relative}", "exec"), module.__dict__)
        before = {}
        for name, (_, args) in scenarios.items():
            pool = fixture.pool(long=name == "short_fit")
            facts = tuple(reversed(pool)) if name == "reversed" else pool
            if name == "short_fit":
                facts = (pool[1], pool[0])
            fixture.run_session(facts, **{"positions": (0, 15000, 30000, 45000, 50000, 60000, 75000, 90000, 100000), **args})
            before[name] = fixture.last_capture
        return {"simulator": True, "base": BASE,
                "candidate_files": {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() for relative in (RUNTIME, FACTS)},
                "before": before, "after": after}
    finally:
        ContextualFactPlanningTest.tearDownClass()


if __name__ == "__main__":
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(capture(), ensure_ascii=False, indent=2) + "\n")
    print(f"Exact-base/current software Runtime sequences: {target}")
