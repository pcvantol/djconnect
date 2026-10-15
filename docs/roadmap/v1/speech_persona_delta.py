"""Bounded selected speech/Persona implementation delta over delivered artwork."""

from copy import deepcopy
from pathlib import Path
import hashlib
import json

CORE = {
    "SPEECH::CORE::CONTRACT",
    "SPEECH::CORE::PERSONA",
    "SPEECH::CORE::REALIZATION",
    "SPEECH::CORE::DELIVERY",
}
CONSUMERS = {"SPEECH::APPLE::ADOPTION", "SPEECH::JOINT::ACCEPTANCE"}
PAIRS = {("SPEECH::CORE::CONTRACT", n) for n in CORE - {"SPEECH::CORE::CONTRACT"}} | {
    ("SPEECH::CORE::CONTRACT", "SPEECH::APPLE::ADOPTION"),
    *((n, "SPEECH::JOINT::ACCEPTANCE") for n in CORE - {"SPEECH::CORE::CONTRACT"}),
    ("SPEECH::APPLE::ADOPTION", "SPEECH::JOINT::ACCEPTANCE"),
}


def validate(plan, previous_validator):
    d = plan["planning_maintenance"]
    r = d.get("speech_persona_receipt", {})
    errors = []

    def check(value, message):
        if not value:
            errors.append("maintenance: speech/Persona " + message)

    check(
        r.get("assignment_id") == "DJC-SESSION-SPEECH-PERSONA-VOICE-20261015"
        and r.get("owner_selection") == 6189231491
        and r.get("autonomous_next") == 6189912293,
        "selection missing",
    )
    check(
        r.get("base_sha") == "70c0a3009910db8763e65949d0a10eade7d006dc"
        and r.get("branch") == "codex/session-speech-persona-voice-v1"
        and r.get("ack") == 6191876871
        and r.get("contract_commit") == "e2072d8025056089b3bf403366307be70dd53ae8"
        and r.get("material_commit") == "03634bf7a8bcdc904505a4a22dc23fbae4dabd1b",
        "actual admission missing",
    )
    previous_file = (
        Path(__file__).parent / "history/20261015/artwork-finalization-maintenance-v11.json"
    )
    raw = previous_file.read_bytes()
    check(r.get("previous_delta_sha256") == hashlib.sha256(raw).hexdigest(), "prior bytes changed")
    previous = json.loads(raw)
    stripped = deepcopy(d)
    stripped.pop("speech_persona_receipt", None)
    stripped["schema_version"] = previous["schema_version"]
    stripped["nodes"] = [n for n in d["nodes"] if not n["id"].startswith("SPEECH::")]
    stripped["edges"] = [e for e in d["edges"] if not e["id"].startswith("SPEECH-")]
    for key in previous.keys() - {"document_references"}:
        check(stripped.get(key) == previous[key], "delivered predecessor changed: " + key)
    old = deepcopy(plan)
    old["planning_maintenance"] = stripped
    errors.extend(previous_validator(old))
    check(
        r.get("phase") == "LOCAL_IMPLEMENTATION_AND_QUALIFICATION"
        and r.get("source_delivery") == "UNPUBLISHED",
        "unproved delivery",
    )
    check(
        r.get("native") == "OPEN_APPLE"
        and r.get("joint") == "OPEN"
        and r.get("installed") == "NOT_RUN"
        and r.get("hardware") == "NOT_RUN"
        and r.get("audible") == "NOT_RUN"
        and r.get("consumer_writes") is False,
        "acceptance overclaim",
    )
    nodes = {n["id"]: n for n in d["nodes"]}
    check(len(nodes) == len(d["nodes"]), "duplicate nodes")
    selected = {n for n in nodes if n.startswith("SPEECH::")}
    check(selected == CORE | CONSUMERS, "bounded nodes changed")
    for name in selected:
        n = nodes[name]
        check(
            (n.get("status"), n.get("assignment_status"))
            == (("In progress", "IN_PROGRESS") if name in CORE else ("Planned", "NOT_ISSUED")),
            "state/consumer admission",
        )
        check(
            n.get("parent_reference") in {"PROJ::ROADMAP::VOICE", "PROJ::ROADMAP::P2-REFERENCE"}
            and n.get("contract_binding") == "docs/product/SESSION_SPEECH_PERSONA_V1.md",
            "existing architecture binding missing",
        )
    edges = [e for e in d["edges"] if e["id"].startswith("SPEECH-")]
    check(
        len(edges) == len(PAIRS) and {(e["producer"], e["consumer"]) for e in edges} == PAIRS,
        "dependency scope",
    )
    for name in selected:
        incoming = {e["id"] for e in edges if e["consumer"] == name}
        grouped = [
            e for g in nodes[name].get("prerequisite_groups", []) for e in g.get("edge_ids", [])
        ]
        check(incoming == set(grouped) and len(grouped) == len(incoming), "prerequisite groups")
    graph = {n["id"]: [] for n in plan["nodes"] + d["nodes"]}
    degree = dict.fromkeys(graph, 0)
    for e in plan["edges"] + d["edges"]:
        if e.get("hard_precedence"):
            a, b = e["producer"], e["consumer"]
            if a not in graph or b not in graph:
                check(False, "dangling dependency")
                continue
            graph[a].append(b)
            degree[b] += 1
    pending = [n for n, v in degree.items() if not v]
    seen = 0
    while pending:
        n = pending.pop()
        seen += 1
        for target in graph[n]:
            degree[target] -= 1
            if not degree[target]:
                pending.append(target)
    check(seen == len(graph), "cycle")
    return errors
