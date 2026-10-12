"""Versioned documentary delta over a byte-preserved historical snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

KEY = "planning_maintenance"


def canonical(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def validate_delta(plan: dict[str, Any]) -> list[str]:
    d = plan.get(KEY)
    if not isinstance(d, dict):
        return ["maintenance: expected object"]
    errors = []

    def check(condition, reason):
        if not condition:
            errors.append("maintenance: " + reason)

    version = d.get("schema_version")
    implementation = version in {"djconnect-federated-planning-delta/2", "djconnect-federated-planning-delta/3"}
    artwork = version == "djconnect-federated-planning-delta/3"
    check(version in {"djconnect-federated-planning-delta/1", "djconnect-federated-planning-delta/2", "djconnect-federated-planning-delta/3"}, "unsupported schema")
    delivered = False
    if implementation:
        receipt = d.get("implementation_receipt", {})
        delivered = receipt.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(receipt.get("assignment_id") == "DJC-CORE-DJ-PRESENCE-V1-20261011", "implementation assignment binding missing")
        check(receipt.get("selection_url") == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6111222122", "implementation owner binding missing")
        check(receipt.get("joint_product_acceptance") == "OPEN", "joint acceptance remains Planned without native receipts")
        check(receipt.get("native") == "NOT_RUN" and receipt.get("installed") == "NOT_RUN" and receipt.get("hardware") == "NOT_RUN", "unqualified consumer effect")
        check(receipt.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"}, "unqualified delivery phase")
        check(receipt.get("source_delivery") == ("PROTECTED_MERGED" if delivered else "UNPUBLISHED"), "unqualified delivery phase")
        if delivered:
            check(bool(re.fullmatch(r"[a-f0-9]{40}", str(receipt.get("source_main_sha", "")))), "exact source main receipt missing")
            check(bool(re.fullmatch(r"https://github.com/pcvantol/djconnect/pull/[0-9]+", str(receipt.get("source_pr", "")))), "source PR receipt missing")
            check(receipt.get("source_review") == "PASS" and receipt.get("required_checks") == "PASS" and receipt.get("protected_merge") is True, "protected delivery evidence missing")
            check(all(bool(re.fullmatch(r"[a-f0-9]{64}", str(receipt.get(k, "")))) for k in ("archive_sha256", "formal_evidence_sha256")), "exact artifact readback missing")
        check(receipt.get("previous_delta") == "history/20261011/presence-design-maintenance-v1.json" and len(str(receipt.get("previous_delta_sha256", ""))) == 64, "previous version binding missing")
    correction_delivered = False
    if artwork:
        corrections = d.get("correction_receipts", [])
        check(isinstance(corrections, list) and len(corrections) == 1, "one bounded correction required")
        c = corrections[0] if isinstance(corrections, list) and len(corrections) == 1 else {}
        correction_delivered = c.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(c.get("assignment_id") == "DJC-CORE-DISCOVERY-ARTWORK-CONTINUITY-V1-20261012", "correction assignment binding missing")
        check(c.get("selection_url") == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6117357579", "correction owner binding missing")
        check(c.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"}, "unqualified correction phase")
        check(c.get("source_delivery") == ("PROTECTED_MERGED" if correction_delivered else "UNPUBLISHED"), "unqualified correction delivery")
        check(all(c.get(k) == "NOT_RUN" for k in ("native", "installed", "live_provider")) and c.get("joint_product_acceptance") == "OPEN", "unqualified correction consumer acceptance")
        check(c.get("previous_delta") == "history/20261012/presence-implementation-maintenance-v2.json" and bool(re.fullmatch(r"[a-f0-9]{64}", str(c.get("previous_delta_sha256", "")))), "correction history binding missing")
        if correction_delivered:
            check(bool(re.fullmatch(r"[a-f0-9]{40}", str(c.get("source_main_sha", "")))) and bool(re.fullmatch(r"https://github.com/pcvantol/djconnect/pull/[0-9]+", str(c.get("source_pr", "")))), "correction source receipt missing")
            check(c.get("source_review") == "PASS" and c.get("required_checks") == "PASS" and c.get("protected_merge") is True, "correction protected checks missing")
            check(all(bool(re.fullmatch(r"[a-f0-9]{64}", str(c.get(k, "")))) for k in ("archive_sha256", "formal_evidence_sha256")), "correction artifact receipt missing")
    check(
        d.get("execution_authority") is False and d.get("automatic_dispatch") is False,
        "no product dispatch authorized",
    )
    check(
        canonical({k: v for k, v in plan.items() if k != KEY}) == d.get("frozen_content_sha256"),
        "frozen content changed",
    )
    check(
        d.get("decision_id") == "DJC-DJ-PRESENCE-ROADMAP-DESIGN-V1-20261011",
        "decision binding missing",
    )
    check(
        d.get("decision_url")
        == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6110375785",
        "owner reference mismatch",
    )
    check(d.get("scope") == ("SELECTED_CORE_IMPLEMENTATION_DELTA" if implementation else "DOCUMENTARY_DELTA_ONLY"), "invalid scope")
    for field in ["nodes", "edges", "document_references"]:
        check(
            isinstance(d.get(field), list) and all(isinstance(x, dict) for x in d.get(field, [])),
            "invalid " + field,
        )
    if errors:
        return errors
    inherited = {n["id"]: n for n in plan["nodes"]}
    nodes = {n.get("id"): n for n in d["nodes"]}
    check(
        len(nodes) == len(d["nodes"]) and None not in nodes and not (set(nodes) & set(inherited)),
        "duplicate or inherited node",
    )
    if artwork:
        check({nid for nid in nodes if isinstance(nid, str) and nid.startswith("CORRECTION::")} == {"CORRECTION::CORE::DISCOVERY-ARTWORK", "CORRECTION::APPLE::DISCOVERY-ARTWORK-ACCEPTANCE"}, "one existing-capability correction boundary required")
    lanes = {lane["id"]: lane["repository"] for lane in plan["lanes"]}
    for nid, n in nodes.items():
        check(lanes.get(n.get("lane")) == n.get("repository"), "unknown owning lane/repository")
        presence_admitted = implementation and nid in {"SLICE::CORE::DJ-PRESENCE-CONTRACT", "SLICE::CORE::DJ-PRESENCE-POLICY"}
        correction_admitted = artwork and nid == "CORRECTION::CORE::DISCOVERY-ARTWORK"
        admitted = presence_admitted or correction_admitted
        node_delivered = correction_delivered if correction_admitted else delivered
        check(n.get("status") in ({"Completed" if node_delivered else "In progress"} if admitted else {"Planned", "Completed"}), "invalid node status")
        check(n.get("status") == "Planned" or admitted or nid == "SLICE::CORE::ACTIVE-SESSION-MOOD", "unadmitted implementation must remain Planned")
        check(n.get("assignment_status") == (("CORE_DELIVERED" if node_delivered else "IN_PROGRESS") if admitted else "NOT_ISSUED"), "unadmitted assignment may not start")
        check(
            all(
                n.get(k)
                for k in ["title", "scope", "acceptance_boundary", "contract_binding", "source_ids"]
            ),
            "node criteria/provenance missing",
        )
        check(n.get("source_ids") == (["OWNER-DISCOVERY-ARTWORK-20261012"] if artwork and nid.startswith("CORRECTION::") else ["OWNER-DJ-PRESENCE-20261011"]), "unqualified provenance")
    refs = d["document_references"]
    paths = [r.get("path") for r in refs]
    check(len(paths) == len(set(paths)), "duplicate document reference")
    for r in refs:
        path = r.get("path")
        check(
            isinstance(path, str)
            and path.endswith(".md")
            and not path.startswith("/")
            and ".." not in path.split("/"),
            "unsafe document reference",
        )
        check(isinstance(r.get("sha256"), str) and len(r["sha256"]) == 64, "document hash missing")
    edges = {e.get("id"): e for e in d["edges"]}
    check(len(edges) == len(d["edges"]) and None not in edges, "duplicate edge")
    allnodes = {**inherited, **nodes}
    grouped = []
    for n in nodes.values():
        for g in n.get("prerequisite_groups", []):
            check(
                g.get("mode") in {"AND", "OR"} and bool(g.get("edge_ids")), "invalid AND/OR group"
            )
            for eid in g.get("edge_ids", []):
                e = edges.get(eid, {})
                check(
                    e.get("consumer") == n["id"]
                    and e.get("hard_precedence") is True
                    and e.get("logical_mode") == g["mode"],
                    "group ownership/mode mismatch",
                )
                grouped.append(eid)
    hard = {eid for eid, e in edges.items() if e.get("hard_precedence")}
    check(
        len(grouped) == len(set(grouped)) and set(grouped) == hard,
        "missing/repeated prerequisite group",
    )
    for e in edges.values():
        check(
            e.get("producer") in allnodes
            and e.get("consumer") in allnodes
            and e.get("producer") != e.get("consumer"),
            "orphan/self edge",
        )
        check(
            e.get("phase") in {"selection", "implementation", "integration_acceptance"}
            and e.get("prerequisite_stage") in {"start", "completion"},
            "phase/gate missing",
        )
        check(e.get("logical_mode") in {"AND", "OR"}, "edge logical mode missing")
        check(e.get("kind") in {x["kind"] for x in plan["edges"]}, "unknown edge vocabulary")
        check(
            all(
                e.get(k)
                for k in ["required_subset", "contract_or_evidence", "reason", "source_ids"]
            ),
            "edge subset/evidence missing",
        )
        check(e.get("source_ids") == (["OWNER-DISCOVERY-ARTWORK-20261012"] if artwork and str(e.get("id", "")).startswith("ARTWORK-") else ["OWNER-DJ-PRESENCE-20261011"]), "edge provenance mismatch")
        if e.get("kind") == "strategy_order":
            check(e.get("hard_precedence") is False, "strategy is not hard dependency")
    # Validate all new edges, including soft order, against inherited hard graph.
    graph = {nid: [] for nid in allnodes}
    degree = {nid: 0 for nid in allnodes}
    for e in [x for x in plan["edges"] if x.get("hard_precedence")] + list(edges.values()):
        a, b = e.get("producer"), e.get("consumer")
        if a in graph and b in graph:
            graph[a].append(b)
            degree[b] += 1
    ready = [n for n, v in degree.items() if not v]
    seen = 0
    while ready:
        n = ready.pop()
        seen += 1
        for target in graph[n]:
            degree[target] -= 1
            if not degree[target]:
                ready.append(target)
    check(seen == len(graph), "cycle in maintained graph")
    return errors


def render_delta(p):
    errors = validate_delta(p)
    if errors:
        raise ValueError("; ".join(errors))
    d = p[KEY]
    nodes = {n["id"]: n for n in d["nodes"]}
    inherited = {n["id"]: n for n in p["nodes"]}
    current = d.get("schema_version") in {"djconnect-federated-planning-delta/2", "djconnect-federated-planning-delta/3"}
    artwork = d.get("schema_version") == "djconnect-federated-planning-delta/3"
    delivery = d.get("implementation_receipt", {}).get("source_delivery", "UNPUBLISHED")
    intro = (
        "Generated from djconnect-platform-v1.json, maintenance " + d["decision_id"] + ".\n\n"
        "The original3October snapshot/audit/source pins and projections are immutable history in [history/20261003](history/20261003/README.md). "
        "Only this bounded delta is current here; inherited premerge statuses are not current blockers. "
        + ("Only the selected existing Core writer is admitted by implementation receipt; no automatic dispatch, second writer or native/installed/hardware acceptance.\n\n" if current else "No portfolio-wide refresh, writer reservation, product dispatch or runtime acceptance is claimed.\n\n")
    )
    if artwork:
        intro += "Current bounded artwork correction: [owner6117357579](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6117357579). Existing Discovery capability only; source/Finalization gates remain separate, native/installed/live acceptance remains open. Presence source1150/Finalization1151 stays closed. Prior version2 is preserved in history/20261012.\n\n"
    out = {}
    out["README.md"] = (
        "# Federated roadmap — versioned maintenance\n\n"
        + intro
        + f"[Owner decision]({d['decision_url']}); documentary design date {d['design_date']}.\n\n"
        + "Presence remains Planned. Mood, Persona and presence are independent. Corepolicy + Applecontrol + local/static VibeCast receipts form joint acceptance. Richer narrative is later, not a v1 gate.\n\n"
        + "[Dependencies](DEPENDENCIES.md), [lanes](LANES.md), [open work](OPEN_WORK.md), [handoffs](HANDOFFS.md), [catalogue](CATALOGUE.md), [source bindings](SOURCES.md) and diagrams are generated by the same maintenance route.\n\n"
        + "Run `python3 validate_snapshot.py djconnect-platform-v1.json --check-rendered` and `python3 -m unittest test_snapshot test_maintenance_delta`. Historical complete-delivery flags concern only the frozen snapshot, never presence product completion.\n"
    )
    out["CATALOGUE.md"] = (
        "# Maintained node catalogue\n\n"
        + intro
        + "| Node | Owner | Status | Outcome |\n|---|---|---|---|\n"
        + "".join(
            f"| `{n['id']}` | {n['lane']} | {n['status']} | {n['title']} |\n"
            for n in nodes.values()
        )
    )
    out["DEPENDENCIES.md"] = (
        "# Maintained dependencies\n\n"
        + intro
        + "| Producer → consumer | Kind / phase / gate | Hard | AND/OR | Required subset | Evidence |\n|---|---|---|---|---|---|\n"
        + "".join(
            f"| `{e['producer']}` → `{e['consumer']}` | {e['kind']} / {e['phase']} / {e['prerequisite_stage']} | {e['hard_precedence']} | {e['logical_mode']} | {e['required_subset']} | {e['contract_or_evidence']} |\n"
            for e in d["edges"]
        )
    )
    out["OPEN_WORK.md"] = (
        "# Planned product work — no dispatch\n\n"
        + intro
        + "".join(
            f"- `{n['id']}` — {n['status']}: {n['acceptance_boundary']}.\n"
            for n in nodes.values()
            if n["status"] != "Completed"
        )
        + ("\nCore policy/ownercontract status follows the exact implementation receipt. Native/installed/hardware acceptance remains open.\n" if current else "\nPolicy values/budgets/default and exact presence route/schema remain unqualified design details. No runtime/native/browser/installed/hardware PASS.\n")
    )
    if current:
        intro += f"Selected implementation [{d['implementation_receipt']['assignment_id']}]({d['implementation_receipt']['selection_url']}); early local contract `{d['implementation_receipt']['early_contract_pin']}`; source delivery {delivery}.\n\n"
    out["SOURCES.md"] = (
        "# Maintenance source bindings\n\n"
        + intro
        + f"Authority: [{d['decision_id']}]({d['decision_url']}).\n\nFrozen raw SHA256 `{d['frozen_sha256']}`; canonical frozen content `{d['frozen_content_sha256']}`.\n\n"
        + "| Local design source | SHA256 |\n|---|---|\n"
        + "".join(
            f"| [{r['path']}](../../../{r['path']}) | `{r['sha256']}` |\n"
            for r in d["document_references"]
        )
    )
    out["LANES.md"] = "# Owning lanes — planning only\n\n" + intro
    for lane in p["lanes"]:
        lid = lane["id"]
        selected = [n for n in nodes.values() if n["lane"] == lid]
        body = (
            "# "
            + lid
            + " presence projection\n\n"
            + intro
            + (
                "".join(f"- `{n['id']}` — {n['status']}; {n['scope']}\n" for n in selected)
                if selected
                else "No presence implementation assigned to this lane.\n"
            )
            + "\nFresh owner/writer/resource admission is separate from functional prerequisites. Historical writer observations are not current leases.\n"
        )
        out["lanes/" + lid + ".md"] = body.replace(
            "(history/20261003/README.md)", "(../history/20261003/README.md)"
        )
        out["LANES.md"] += (
            f"- [{lid}](lanes/{lid}.md) — {len(selected)} bounded records; no new writer.\n"
        )
    out["HANDOFFS.md"] = (
        "# Planned handoffs\n\n"
        + intro
        + ("Core → existing Apple87: exact Discovery feed/scoped image/TTL/error/source fixtures; visible attribution, cached pixels and lifecycle require separate native evidence. No Swift/receiver writer or new provider.\n\n" if artwork else "")
        + "Core → Apple: pinned early presence contract/policy fixtures permit contract integration before all Finalization docs. Independent UX preparation is not integrated acceptance.\n\nCore shared renderer → VibeCast: actual authorized varied Broadcast traces on both existing builds; no second renderer.\n\nCore + Apple owning receipts → joint product acceptance, no extra writerlane. Physical/native/installed effects stay separately qualified.\n"
    )
    ids = {nid: "n" + str(i) for i, nid in enumerate([*inherited, *nodes])}

    def diagram(edges, title):
        seen = {e[k] for e in edges for k in ["producer", "consumer"]}
        lines = ["flowchart LR", f'  note["{title}"]']
        for nid in sorted(seen):
            lines.append(f'  {ids[nid]}["{(nodes.get(nid) or inherited[nid])["title"]}"]')
        for e in edges:
            lines.append(
                f"  {ids[e['producer']]} {'-->' if e['hard_precedence'] else '-.->'}|{e['kind']} / {e['phase']} / {e['prerequisite_stage']}| {ids[e['consumer']]}"
            )
        return "\n".join(lines) + "\n"

    out["diagrams/hard-dependencies.mmd"] = diagram(
        [e for e in d["edges"] if e["hard_precedence"]],
        "AND prerequisites; exact subset receipts required",
    )
    out["diagrams/milestones.mmd"] = diagram(
        d["edges"], "Versioned bounded maintenance; no implicit consumer dispatch"
    )
    out["diagrams/cross-repository.mmd"] = (
        "flowchart LR\n  Core -->|early pinned contract| Apple\n  Core -->|both build traces| VibeCast\n  Core --> Product\n  Apple --> Product\n  VibeCast --> Product\n"
    )
    out["diagrams/ready-frontier.mmd"] = (
        'flowchart LR\n  Planned["All presence product work Planned; no dispatch"]\n'
    )
    return out
