"""Whole before/after editorial sequences from the actual source/Runtime path."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.test_expressive_dj_persona import ExpressiveDJPersonaTest  # noqa: E402

BASE = "b32deedd0cc2bbaca862c8cd63dd25b017203c3f"
FILES = (
    "custom_components/djconnect/session_facts.py",
    "custom_components/djconnect/session_runtime.py",
    "custom_components/djconnect/presentation_composer.py",
    "custom_components/djconnect/moment_expression.py",
    "custom_components/djconnect/vibecast.html",
)


def capture():
    ExpressiveDJPersonaTest.setUpClass()
    try:
        fixture = ExpressiveDJPersonaTest()
        after = {}
        for locale in fixture.facts.LANGUAGES:
            after[locale] = {}
            for persona in fixture.runtime.DJPersona:
                fixture.run_sequence(persona, locale)
                after[locale][persona.value] = fixture.last_capture
        from custom_components.djconnect import presentation_composer

        # Load all relevant exact-base owners, not an approximation of old prose.
        for path, module in (
            (FILES[0], fixture.facts),
            (FILES[2], presentation_composer),
            (FILES[1], fixture.runtime),
        ):
            source = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)
            exec(compile(source, f"{BASE}:{path}", "exec"), module.__dict__)
        before = {}
        for locale in fixture.facts.LANGUAGES:
            before[locale] = {}
            for persona in fixture.runtime.DJPersona:
                fixture.run_sequence(persona, locale)
                before[locale][persona.value] = fixture.last_capture
        return {
            "simulator": True,
            "base": BASE,
            "candidate_files": {
                f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES
            },
            "before": before,
            "after": after,
        }
    finally:
        ExpressiveDJPersonaTest.tearDownClass()


def editorial(evidence):
    lines = [
        "# Expressive persona — actual software Runtime sequences",
        "",
        "Source-shaped fixtures, not live provider/HA/Pi output. Same qualified cores on both sides.",
        "",
    ]
    for locale in evidence["after"]:
        lines.extend([f"## {locale}", ""])
        for persona in evidence["after"][locale]:
            lines.extend([f"### {persona}", ""])
            for phase in ("before", "after"):
                lines.extend([f"**{phase}**", ""])
                for index, m in enumerate(evidence[phase][locale][persona]["receipts"]):
                    if m:
                        lines.extend(
                            [
                                f"{index + 1}. {m['content']}",
                                f"   Sources: {m['source_attribution']['url']}"
                                + (
                                    " / " + m["source_attribution"]["url_previous"]
                                    if m["source_attribution"].get("url_previous")
                                    else ""
                                ),
                                "",
                            ]
                        )
                    else:
                        lines.extend([f"{index + 1}. Silence", ""])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    evidence = capture()
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    target.with_name("editorial-before-after.md").write_text(editorial(evidence))
    print(target)
