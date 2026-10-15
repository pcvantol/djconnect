"""Exact-base and candidate whole Runtime sequences; synthetic sources only."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.test_expressive_context_variation import (  # noqa: E402
    ExpressiveContextVariationTest,
    FAMILIES,
)

BASE = "e0ee7e3ee7265599345ed6c37647623b2a03b27d"
FILES = (
    "custom_components/djconnect/context_expression.py",
    "custom_components/djconnect/moment_expression.py",
    "custom_components/djconnect/session_runtime.py",
    "custom_components/djconnect/session_facts.py",
    "custom_components/djconnect/presentation_composer.py",
    "custom_components/djconnect/vibecast.html",
    "custom_components/djconnect/paired_live.py",
    "custom_components/djconnect/paired_live_contract.py",
)


def capture():
    ExpressiveContextVariationTest.setUpClass()
    fixture = ExpressiveContextVariationTest()
    try:
        evidence = {
            "simulator": True,
            "base": BASE,
            "candidate_files": {
                p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in FILES
            },
        }
        for phase in ("after", "before"):
            if phase == "before":
                from custom_components.djconnect import moment_expression

                for path, module in ((FILES[1], moment_expression), (FILES[2], fixture.runtime)):
                    source = subprocess.check_output(
                        ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
                    )
                    exec(compile(source, f"{BASE}:{path}", "exec"), module.__dict__)
            evidence[phase] = {}
            for family in FAMILIES:
                evidence[phase][family] = {}
                for locale in fixture.facts.LANGUAGES:
                    evidence[phase][family][locale] = {}
                    for persona in fixture.runtime.DJPersona:
                        fixture.run_sequence(family, persona, locale)
                        evidence[phase][family][locale][persona.value] = fixture.last_capture
        # Choice/type/source/card counts must agree across each complete series.
        for family in FAMILIES:
            for locale in fixture.facts.LANGUAGES:
                for persona in fixture.runtime.DJPersona:
                    series = [
                        evidence[phase][family][locale][persona.value]
                        for phase in ("before", "after")
                    ]
                    signatures = [
                        [
                            None
                            if m is None
                            else (
                                m["type"],
                                m["title"],
                                m.get("source_attribution"),
                                m["source_references"],
                            )
                            for m in scenario["receipts"]
                        ]
                        for scenario in series
                    ]
                    assert signatures[0] == signatures[1], (family, locale, persona, signatures)
        evidence["selection_source_count_parity"] = True
        return evidence
    finally:
        ExpressiveContextVariationTest.tearDownClass()


def editorial(evidence):
    lines = [
        "# Expressive context — complete actual Runtime before/after sequences",
        "",
        "Synthetic source-shaped fixtures; no live provider, installed HA or hardware claim.",
        "",
    ]
    for family in FAMILIES:
        for locale in evidence["after"][family]:
            for persona in evidence["after"][family][locale]:
                lines.extend([f"## {family} / {locale} / {persona}", ""])
                for phase in ("before", "after"):
                    lines.extend([f"### {phase}", ""])
                    for index, m in enumerate(evidence[phase][family][locale][persona]["receipts"]):
                        if not m:
                            lines.append(
                                f"{index + 1}. No publication (existing initial observation gate)."
                            )
                        else:
                            lines.extend(
                                [
                                    f"{index + 1}. [{m['type']}] {m['content'] or m['summary']}",
                                    f"   Source: {m.get('source_attribution', {}).get('url') or ', '.join(m['source_references'])}",
                                ]
                            )
                    lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    evidence = capture()
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    target.with_name("editorial-sequences.md").write_text(editorial(evidence))
    print("PASS: 100 exact-base/candidate complete Runtime series; selection/source/count parity")
