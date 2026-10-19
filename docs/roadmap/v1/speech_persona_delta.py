"""Bounded selected speech/Persona implementation delta over delivered artwork."""

from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re

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
    check(r.get("integration_main_sha") == "58205056c235a73488591591dd3d83f80f7bf847", "documentary integration base missing")
    check(r.get("previous_delta") == "history/20261016/pre-speech-main582-maintenance-v11.json",
          "wrong predecessor snapshot path")
    previous_file = (
        Path(__file__).parent / "history/20261016/pre-speech-main582-maintenance-v11.json"
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
    delivered = r.get("phase") == "SOURCE_PROTECTED_MERGED"
    check(
        r.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"}
        and r.get("source_delivery") == ("PROTECTED_MERGED" if delivered else "UNPUBLISHED"),
        "unproved delivery",
    )
    if delivered:
        check(
            r.get("source_candidate") == "50cbae2665a7f7e25d4744136f64ba0e8f16def7"
            and r.get("source_main_sha") == "3535c97c3b50e9a126d0f22fcc5ce50d81851499"
            and r.get("source_pr") == "https://github.com/pcvantol/djconnect/pull/1177"
            and r.get("source_review") == "PASS"
            and r.get("required_checks") == "PASS"
            and r.get("protected_merge") is True
            and r.get("owner_authorization_run") == 38816161823
            and all(re.fullmatch(r"[a-f0-9]{64}", str(r.get(k, "")))
                    for k in ("archive_sha256", "formal_evidence_sha256", "coverage_sha256")),
            "protected delivery evidence missing",
        )
    successor = r.get("selected_successor")
    if successor is not None:
        check(successor == {
            "assignment_id": "DJC-CORE-PASSIVE-SESSION-PROJECTION-V1-20261015",
            "owner_selection": 6199213014,
            "node": "SURFACE::CORE::PROJECTION",
            "admission": "NOT_ADMITTED",
            "start_boundary": "AFTER_VALID_SPEECH_FINALIZATION_AND_FRESH_ADMISSION",
            "same_writer": True,
            "implementation_in_this_slice": False,
            "new_publication_gates_preserved": True,
        }, "successor admission or authority overclaim")
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
            == (("Completed", "CORE_DELIVERED") if name in CORE and delivered
                else ("In progress", "IN_PROGRESS") if name in CORE
                else ("Planned", "NOT_ISSUED")),
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
