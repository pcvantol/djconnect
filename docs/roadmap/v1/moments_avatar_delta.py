"""Bounded user-selected Interactive DJMoments; preserve maintenance18 exactly."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

PREFIX = "ASK-DJ-MOMENTS::"
PATH = "history/20261120/moments-avatar-predecessor-maintenance-v18.json"
DOCS = {"docs/product/ASK_DJ_MOMENTS_V1.md", "docs/technical/ASK_DJ_MOMENTS_AVATAR_CONTRACT_V1.md"}


def _scope(d, receipt, check):
    check(
        receipt.get("assignment_id") == "ASK-DJ-MOMENTS-AVATARCARD-V1"
        and receipt.get("owner_comment")
        == "https://github.com/djconnect-music-dj/djconnect/issues/1101#issuecomment-6849511889"
        and receipt.get("source_base") == "616bad88015a8a1bc413781fc49d97532ef7383a",
        "owner and source",
    )
    check(
        receipt.get("automatic_dispatch") is False
        and receipt.get("source_delivery") == "LOCAL_IMPLEMENTATION_NOT_MERGED"
        and receipt.get("installed") == "NOT_RUN"
        and receipt.get("live_model") == "NOT_RUN"
        and receipt.get("native") == "OPEN_APPLE"
        and receipt.get("overall_acceptance") == "OPEN",
        "acceptance boundary",
    )
    check(
        receipt.get("selection") == "USER_SELECTED_INTERACTIVE_MOMENTS_SUPERSEDES_SETTINGS_HORIZON"
        and receipt.get("parent_reference") == "PROJ::ROADMAP::INTERACTIVE",
        "explicit selection",
    )
    nodes = [n for n in d["nodes"] if n["id"].startswith(PREFIX)]
    check(
        {n["id"] for n in nodes}
        == {PREFIX + x for x in ("CONTRACT", "PRODUCER", "APPLE", "ACCEPTANCE")}
        and len(nodes) == 4,
        "bounded leaves",
    )
    check(
        all(
            n["status"] == ("Planned" if n["id"].endswith("ACCEPTANCE") else "In progress")
            and n["parent_reference"] == "PROJ::ROADMAP::INTERACTIVE"
            and n["lane"] == ("DJC-APPLE" if n["id"].endswith("::APPLE") else "DJC-CORE")
            for n in nodes
        ),
        "leaf ownership and state",
    )


def _dependencies(d, check):
    edges = [e for e in d["edges"] if e["id"].startswith("ASK-DJ-MOMENTS-")]
    check(
        len(edges) == 4
        and {(e["producer"], e["consumer"]) for e in edges}
        == {
            (PREFIX + a, PREFIX + b)
            for a, b in [
                ("CONTRACT", "PRODUCER"),
                ("CONTRACT", "APPLE"),
                ("PRODUCER", "ACCEPTANCE"),
                ("APPLE", "ACCEPTANCE"),
            ]
        }
        and all(e["hard_precedence"] is True for e in edges),
        "functional dependencies",
    )
    refs = [r for r in d["document_references"] if r["path"] in DOCS]
    check(
        len(refs) == 2
        and {r["path"] for r in refs} == DOCS
        and all(
            hashlib.sha256((Path(__file__).parents[3] / r["path"]).read_bytes()).hexdigest()
            == r["sha256"]
            for r in refs
        ),
        "exact design documents",
    )
    return refs


def validate(plan, previous_validator):
    d = plan["planning_maintenance"]
    errors = []

    def check(ok, message):
        if not ok:
            errors.append("maintenance: Moments avatar " + message)

    receipt = d.get("moments_avatar_receipt", {})
    raw = (Path(__file__).parent / PATH).read_bytes()
    check(
        receipt.get("predecessor_path") == PATH
        and receipt.get("predecessor_sha256") == hashlib.sha256(raw).hexdigest(),
        "predecessor preservation",
    )
    _scope(d, receipt, check)
    refs = _dependencies(d, check)
    restored = deepcopy(d)
    restored["schema_version"] = "djconnect-federated-planning-delta/18"
    restored.pop("moments_avatar_receipt", None)
    restored["nodes"] = [n for n in restored["nodes"] if not n["id"].startswith(PREFIX)]
    restored["edges"] = [e for e in restored["edges"] if not e["id"].startswith("ASK-DJ-MOMENTS-")]
    restored["document_references"] = [r for r in restored["document_references"] if r not in refs]
    frozen = json.loads(raw)
    check(
        {k: v for k, v in restored.items() if k != "document_references"}
        == {k: v for k, v in frozen.items() if k != "document_references"},
        "unrelated predecessor records unchanged",
    )
    check(
        [r["path"] for r in restored["document_references"]]
        == [r["path"] for r in frozen["document_references"]],
        "prior document references preserved",
    )
    prior = deepcopy(plan)
    prior["planning_maintenance"] = restored
    errors.extend(previous_validator(prior))
    return errors
