"""Exact-base/candidate Runtime software evidence; no live provider claim."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.test_shared_producer_continuity import SharedProducerContinuityTest  # noqa: E402

BASE = "7c67352ec94adef25d7825a10eefeab132affdca"
FILES = ("custom_components/djconnect/session_runtime.py", "custom_components/djconnect/session_facts.py",
         "custom_components/djconnect/vibecast.html")


def capture():
    SharedProducerContinuityTest.setUpClass()
    try:
        fixture = SharedProducerContinuityTest()
        after = {}
        for locale in fixture.facts.LANGUAGES:
            fixture.run_pair(locale=locale)
            after[locale] = fixture.last_capture
        for relative, module in ((FILES[1], fixture.facts), (FILES[0], fixture.runtime)):
            original = subprocess.check_output(["git", "show", f"{BASE}:{relative}"], cwd=ROOT, text=True)
            exec(compile(original, f"{BASE}:{relative}", "exec"), module.__dict__)
        before = {}
        for locale in fixture.facts.LANGUAGES:
            fixture.run_pair(locale=locale)
            before[locale] = fixture.last_capture
        return {"simulator": True, "base": BASE,
                "candidate_files": {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES},
                "before":before, "after":after}
    finally:
        SharedProducerContinuityTest.tearDownClass()


if __name__ == "__main__":
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(capture(), ensure_ascii=False, indent=2)+"\n")
    print(target)
