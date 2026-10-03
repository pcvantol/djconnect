"""Deterministic, offline, fail-closed checks for the pinned planning snapshot.

Structural success does not prove external sources, review or protected delivery.
An unselected OR may remain a per-install choice; it cannot grant READY.
No network or repository writes.
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA = re.compile(r"^[0-9a-f]{40}$")
LANE = re.compile(r"^DJC-[A-Z0-9-]+$")
LISTS = (
    "lanes",
    "sources",
    "nodes",
    "edges",
    "evidence",
    "handoffs",
    "aliases",
    "audit_obligations",
)
PHASES = {
    "selection",
    "assessment",
    "implementation",
    "integration_acceptance",
    "release",
    "qualification",
}


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {x}")),
    )


def validate(plan: Any, require_complete: bool = False) -> list[str]:
    errors: list[str] = []

    def check(ok: bool, message: str) -> None:
        if not ok:
            errors.append(message)

    if not isinstance(plan, dict):
        return ["root must be an object"]
    for key in LISTS:
        if not isinstance(plan.get(key), list) or any(
            not isinstance(x, dict) for x in plan.get(key, [])
        ):
            errors.append(f"{key}: expected list of objects")
    if errors:
        return errors
    check(plan.get("schema_version") == "djconnect-federated-planning/1", "unknown schema version")
    check(plan.get("execution_authority") is False, "checkpoint must not grant execution authority")
    check(plan.get("automatic_dispatch") is False, "checkpoint must not dispatch execution")
    conclusions = plan.get("conclusions", {})
    completeness = plan.get("completeness", {})
    check(
        isinstance(conclusions, dict) and isinstance(completeness, dict),
        "delivery claims must be objects",
    )
    if isinstance(conclusions, dict):
        check(
            conclusions.get("PRODUCT_DELIVERY") == "UNCHANGED_BY_PLANNING",
            "planning cannot claim product delivery",
        )
        check(
            conclusions.get("EXECUTION_READY") == "NO_NEW_PRODUCT_PICKUP_AUTHORIZED",
            "planning cannot grant product pickup",
        )
        planning_state = conclusions.get("PLANNING_DELIVERY")
        check(
            planning_state
            in {
                "IN_PROGRESS / PROTECTED_DELIVERY_NOT_YET_DONE",
                "COMPLETE / MERGED_RECONCILED / FINALIZED",
            },
            "unsupported planning delivery claim",
        )
        if planning_state == "COMPLETE / MERGED_RECONCILED / FINALIZED":
            check(
                isinstance(completeness, dict)
                and all(
                    completeness.get(k) is True
                    for k in (
                        "full_platform_audit",
                        "all_sources_read",
                        "all_owning_registers_delivered",
                        "canonical_writes",
                        "independent_review",
                        "protected_delivery",
                        "finalization",
                    )
                ),
                "complete planning claim lacks all delivery gates",
            )
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    for key in ("lanes", "sources", "nodes", "edges", "evidence", "handoffs", "audit_obligations"):
        out: dict[str, dict[str, Any]] = {}
        for item in plan[key]:
            ident = item.get("id")
            if not isinstance(ident, str) or not ident:
                errors.append(f"{key}: invalid id")
                continue
            check(ident not in out, f"{key}: duplicate id {ident}")
            out[ident] = item
        indexes[key] = out
    lanes, sources, nodes, edges, evidence = (
        indexes[k] for k in ("lanes", "sources", "nodes", "edges", "evidence")
    )
    repos = [lane.get("repository") for lane in lanes.values()]
    check(
        all(isinstance(x, str) and "/" in x for x in repos), "lane repositories must be owner/name"
    )
    if all(isinstance(x, str) for x in repos):
        check(len(set(repos)) == len(repos), "one repository must have exactly one lane")
    for lid, lane in lanes.items():
        check(bool(LANE.fullmatch(lid)), f"{lid}: unsafe/invalid lane ID")
        check(
            bool(SHA.fullmatch(str(lane.get("baseline_sha", "")))), f"{lid}: invalid baseline pin"
        )
        register = lane.get("owning_register")
        if register:
            check(
                str(register).startswith(f"https://github.com/{lane['repository']}/issues/"),
                f"{lid}: register belongs to another repository",
            )
        if lane.get("writer_free_verified"):
            check(lane.get("writer_state") == "FREE_VERIFIED", f"{lid}: writer status conflict")
            receipt = lane.get("writer_free_evidence")
            check(
                isinstance(receipt, dict)
                and bool(receipt.get("url"))
                and bool(receipt.get("observed_at"))
                and receipt.get("repository") == lane.get("repository"),
                f"{lid}: writer-free claim lacks exact receipt",
            )
        if lane.get("writer_state") == "FREE_VERIFIED":
            check(
                lane.get("writer_free_verified") is True,
                f"{lid}: free writer label lacks verification",
            )
    registers = [
        lane.get("owning_register") for lane in lanes.values() if lane.get("owning_register")
    ]
    check(len(registers) == len(set(registers)), "multiple lanes share an owning register")
    if isinstance(completeness, dict):
        check(
            completeness.get("all_owning_registers_delivered") is not True
            or len(registers) == len(lanes),
            "register delivery claim has missing lanes",
        )
        check(
            completeness.get("all_sources_read") is not True
            or all(s.get("read_complete") is True for s in plan["sources"]),
            "source-read claim has partial sources",
        )
    scan = plan.get("source_capture", {}).get("reference_scan", {})
    if scan:
        paths = scan.get("unmapped_paths")
        pinned_refs = {
            f"{s.get('repository')}::{s.get('path')}" for s in plan["sources"]
        }
        def valid_reference(path: Any) -> bool:
            if not isinstance(path, str) or path.count("::") != 1:
                return False
            repository, relative_path = path.split("::", 1)
            return (
                repository in repos
                and bool(relative_path)
                and not relative_path.startswith("/")
                and ".." not in relative_path.split("/")
                and relative_path.endswith(".md")
            )

        check(
            isinstance(paths, list)
            and all(valid_reference(x) for x in paths)
            and len(paths) == len(set(paths))
            and not (pinned_refs & set(paths)),
            "reference scan has invalid, duplicate or already pinned paths",
        )
        check(bool(scan.get("method")) and bool(scan.get("disposition")), "reference scan provenance missing")
        triage = scan.get("triage")
        check(
            isinstance(triage, dict)
            and isinstance(paths, list)
            and set(triage) == set(paths)
            and all(isinstance(reason, str) and reason for reason in triage.values()),
            "reference scan needs one disposition for every unpinned path",
        )
    historical = plan.get("source_capture", {}).get("historical_path_dispositions", {})
    classified_by_lane: dict[str, int] = {}
    if historical:
        check(bool(historical.get("method")), "historical path classification method missing")
        groups = historical.get("groups")
        check(isinstance(groups, list) and bool(groups), "historical path groups missing")
        seen_historical: set[tuple[str, str]] = set()
        source_paths = {(s.get("repository"), s.get("path")) for s in sources.values()}
        pattern_by_category = {
            "DATED_PROMPT_HISTORY": re.compile(r"^docs/history/prompts/\d{4}-\d{2}-\d{2}-[^/]+\.md$"),
            "OLDER_APPLE_VERSIONED_RELEASE_COPY": re.compile(r"^docs/release-notes/(?:de|en|es|fr|nl)/v(\d+)\.(\d+)\.(\d+)\.md$"),
            "OLDER_WINDOWS_VERSIONED_RELEASE_COPY": re.compile(r"^docs/release-notes/(?:de|en|es|fr|nl)/v(\d+)\.(\d+)\.(\d+)\.md$"),
            "OLDER_WEBSITE_VERSIONED_RELEASE_COPY": re.compile(r"^wwwroot/release-notes/(?:ios|macos|maccatalyst|windows)/(?:de/|en/|es/|fr/|nl/)?v(\d+)\.(\d+)\.(\d+)\.md$"),
        }
        allowed_lane_category = {
            "DJC-CORE": {"DATED_PROMPT_HISTORY"},
            "DJC-APPLE": {"DATED_PROMPT_HISTORY", "OLDER_APPLE_VERSIONED_RELEASE_COPY"},
            "DJC-WINDOWS": {"DATED_PROMPT_HISTORY", "OLDER_WINDOWS_VERSIONED_RELEASE_COPY"},
            "DJC-WEBSITE": {"OLDER_WEBSITE_VERSIONED_RELEASE_COPY"},
        }
        version_ceiling = {
            "OLDER_APPLE_VERSIONED_RELEASE_COPY": (4, 0, 0),
            "OLDER_WINDOWS_VERSIONED_RELEASE_COPY": (3, 3, 0),
            "OLDER_WEBSITE_VERSIONED_RELEASE_COPY": (3, 3, 0),
        }
        for group in groups if isinstance(groups, list) else []:
            if not isinstance(group, dict):
                errors.append("invalid historical path group")
                continue
            lid, category = group.get("lane"), group.get("category")
            check(
                lid in allowed_lane_category
                and category in allowed_lane_category[lid]
                and bool(group.get("reason")),
                "invalid historical path category/reason",
            )
            refs = group.get("authority_source_ids")
            check(
                isinstance(refs, list)
                and bool(refs)
                and all(sid in sources for sid in refs),
                "historical path classification lacks pinned authority",
            )
            entries = group.get("entries")
            check(isinstance(entries, list) and bool(entries), "historical path group has no entries")
            if lid not in lanes or category not in pattern_by_category:
                continue
            repository = lanes[lid]["repository"]
            for entry in entries if isinstance(entries, list) else []:
                if not isinstance(entry, dict):
                    errors.append("invalid historical path entry")
                    continue
                path, blob = entry.get("path"), entry.get("blob_sha")
                match = pattern_by_category[category].fullmatch(str(path))
                valid = bool(match) and bool(SHA.fullmatch(str(blob)))
                if match and category in version_ceiling:
                    valid = valid and tuple(map(int, match.groups())) < version_ceiling[category]
                check(valid, "invalid historical path/blob or version boundary")
                key = (repository, path)
                check(
                    key not in seen_historical and key not in source_paths,
                    "duplicate or already represented historical path",
                )
                seen_historical.add(key)
                classified_by_lane[lid] = classified_by_lane.get(lid, 0) + 1
    census = plan.get("source_capture", {}).get("tree_census_readback", {})
    if census:
        rows = census.get("lanes")
        check(
            isinstance(rows, dict) and set(rows) == set(lanes),
            "tree census must cover exactly one row per lane",
        )
        check(bool(census.get("observed_at")) and bool(census.get("boundary")), "tree census provenance missing")
        if isinstance(rows, dict):
            latest = plan.get("latest_head_readback", {}).get("heads", {})
            for lid, row in rows.items():
                if lid not in lanes or not isinstance(row, dict):
                    continue
                repo = lanes[lid]["repository"]
                tracked = row.get("tracked_markdown")
                included = row.get("included_markdown")
                remaining = row.get("not_individually_included_markdown")
                check(
                    row.get("repository") == repo
                    and row.get("commit_sha") == latest.get(repo)
                    and bool(row.get("tree_readback")),
                    f"{lid}: tree census identity/provenance mismatch",
                )
                check(
                    all(type(n) is int and n >= 0 for n in (tracked, included, remaining))
                    and tracked == included + remaining,
                    f"{lid}: invalid tree census counts",
                )
                if historical:
                    classified = row.get("historically_classified_markdown")
                    unclassified = row.get("unclassified_markdown")
                    check(
                        all(type(n) is int and n >= 0 for n in (classified, unclassified))
                        and remaining == classified + unclassified
                        and classified == classified_by_lane.get(lid, 0),
                        f"{lid}: historical/unclassified census mismatch",
                    )
                represented = {
                    s.get("path")
                    for s in sources.values()
                    if s.get("repository") == repo and str(s.get("path", "")).endswith(".md")
                }
                check(included == len(represented), f"{lid}: included Markdown count differs from source matrix")
    for sid, source in sources.items():
        check(
            bool(SHA.fullmatch(str(source.get("blob_sha", "")))), f"{sid}: invalid source blob pin"
        )
        if source.get("commit_sha") is not None:
            check(
                bool(SHA.fullmatch(str(source["commit_sha"]))), f"{sid}: invalid source commit pin"
            )
            check(
                source.get("url")
                == f"https://github.com/{source.get('repository')}/blob/{source['commit_sha']}/{source.get('path')}",
                f"{sid}: source URL does not bind pinned commit/path",
            )
        check(
            bool(source.get("read_boundary")) and bool(source.get("status_authority")),
            f"{sid}: provenance incomplete",
        )
        check(
            source.get("disposition") in {"MAPPED", "MAPPED_PARTIAL", "EXCLUDED_WITH_REASON"},
            f"{sid}: missing disposition",
        )
        mapped = source.get("mapped_node_ids", [])
        if not isinstance(mapped, list) or any(not isinstance(x, str) for x in mapped):
            errors.append(f"{sid}: invalid mapping")
            continue
        check(len(mapped) == len(set(mapped)), f"{sid}: duplicate source mapping")
        if source.get("disposition") == "EXCLUDED_WITH_REASON":
            check(bool(source.get("exclusion_reason")), f"{sid}: exclusion needs reason")
        else:
            check(bool(mapped), f"{sid}: orphan source")
        for nid in mapped:
            check(
                nid in nodes and sid in nodes[nid].get("source_ids", []),
                f"{sid}: inconsistent source-to-node mapping {nid}",
            )
    canonical = [n.get("canonical_id") for n in nodes.values() if n.get("canonical_id")]
    check(len(canonical) == len(set(canonical)), "duplicate canonical node identity")
    for nid, node in nodes.items():
        lane = lanes.get(node.get("lane"))
        check(
            lane is not None and lane.get("repository") == node.get("repository"),
            f"{nid}: invalid owning lane/repository",
        )
        refs = node.get("source_ids")
        check(isinstance(refs, list) and bool(refs), f"{nid}: no source references")
        for sid in refs if isinstance(refs, list) else []:
            check(
                sid in sources and nid in sources[sid].get("mapped_node_ids", []),
                f"{nid}: missing/inconsistent source {sid}",
            )
        check(
            node.get("canonical_authority") in (refs or []),
            f"{nid}: no single canonical status authority",
        )
        for field in (
            "type",
            "visible_outcome",
            "scope",
            "non_goals",
            "acceptance_boundary",
            "contract_binding",
            "resume_reference",
        ):
            check(bool(node.get(field)), f"{nid}: missing {field}")
        for eid in node.get("evidence_ids", []):
            check(eid in evidence, f"{nid}: unknown evidence {eid}")
        check(
            node.get("completion_claim") in {"NONE", "COMPLETE"}, f"{nid}: invalid completion claim"
        )
    alias_ids: set[str] = set()
    for alias in plan["aliases"]:
        aid, target = alias.get("alias"), alias.get("target")
        check(
            isinstance(aid, str) and aid not in alias_ids and aid not in nodes,
            "duplicate/invalid alias identity",
        )
        if isinstance(aid, str):
            alias_ids.add(aid)
        check(target in nodes, f"alias {aid}: missing target")
        check(bool(alias.get("reason")), f"alias {aid}: no reason")
    for eid, ev in evidence.items():
        check(
            bool(SHA.fullmatch(str(ev.get("subject_sha", "")))),
            f"{eid}: invalid evidence subject SHA",
        )
        check(
            bool(ev.get("url")) and bool(ev.get("observed_date")),
            f"{eid}: evidence provenance missing",
        )
    for finding in plan["findings"]:
        for sid in finding.get("source_ids", []):
            check(sid in sources, f"{finding['id']}: unknown finding source {sid}")
        for eid in finding.get("evidence_ids", []):
            check(eid in evidence, f"{finding['id']}: unknown finding evidence {eid}")
    obligations = indexes["audit_obligations"]
    for oid, obligation in obligations.items():
        check(obligation.get("status") in {"OPEN", "CLOSED"}, f"{oid}: invalid audit status")
        if obligation.get("status") == "CLOSED":
            check(
                bool(obligation.get("closure_evidence")),
                f"{oid}: closed audit lacks closure evidence",
            )
    if isinstance(completeness, dict):
        audit_ids = {x for x in obligations if x.startswith("AUDIT-")} | {
            "CORE-FOUNDATION",
            "GRAPH-CLOSURE",
            "PRODUCER-EVIDENCE",
            "SOURCE-MATRIX",
        }
        for flag, needed in {
            "full_platform_audit": audit_ids,
            "canonical_writes": {"CANONICAL-WRITES"},
            "independent_review": {"INDEPENDENT-REVIEW"},
            "protected_delivery": {"PROTECTED-DELIVERY"},
            "finalization": {"FINALIZATION"},
        }.items():
            if completeness.get(flag) is True:
                check(
                    all(obligations.get(x, {}).get("status") == "CLOSED" for x in needed),
                    f"{flag}: supporting audit obligations remain open",
                )
    horizon = plan.get("execution_horizon")
    check(
        isinstance(horizon, list) and len(horizon) == 5,
        "execution horizon must contain five recorded items",
    )
    if isinstance(horizon, list):
        check(
            [h.get("order") for h in horizon if isinstance(h, dict)] == [1, 2, 3, 4, 5],
            "execution horizon order invalid",
        )
        ids = [h.get("node") for h in horizon if isinstance(h, dict)]
        check(
            len(ids) == len(set(ids)) and all(x in nodes for x in ids),
            "execution horizon node missing or duplicated",
        )
        for h in horizon:
            if not isinstance(h, dict):
                continue
            check(
                bool(h.get("disposition")) and all(x in sources for x in h.get("source_ids", [])),
                "execution horizon provenance missing",
            )
            if h.get("node") in nodes:
                check(
                    bool(nodes[h["node"]].get("prerequisite_groups")),
                    f"{h['node']}: horizon condition absent from dependency graph",
                )
    for eid, e in edges.items():
        check(e.get("producer") in nodes and e.get("consumer") in nodes, f"{eid}: orphan edge")
        check(e.get("producer") != e.get("consumer"), f"{eid}: self dependency")
        check(e.get("phase") in PHASES, f"{eid}: invalid dependency phase")
        check(e.get("logical_mode") in {"AND", "OR"}, f"{eid}: missing AND/OR semantics")
        check(
            e.get("prerequisite_stage", "start") in {"start", "completion"},
            f"{eid}: invalid prerequisite stage",
        )
        if e.get("same_increment_as_consumer"):
            check(
                e.get("prerequisite_stage") == "completion"
                and e.get("logical_mode") == "AND"
                and e.get("hard_precedence") is True,
                f"{eid}: same-increment contract must be a hard completion AND gate",
            )
        for field in ("required_subset", "reason", "contract_or_evidence", "source_ids"):
            check(bool(e.get(field)), f"{eid}: missing {field}")
        for sid in e.get("source_ids", []):
            check(sid in sources, f"{eid}: unknown dependency source {sid}")
        if e.get("hard_precedence"):
            check(
                e.get("kind") not in {"strategy_order", "resource_conflict", "handoff_reference"},
                f"{eid}: non-functional order marked hard",
            )
        if e.get("evidence_satisfied"):
            check(
                bool(e.get("evidence_ids"))
                and all(
                    x in evidence and evidence[x].get("acceptance_qualified") is True
                    for x in e.get("evidence_ids", [])
                ),
                f"{eid}: unsupported predecessor evidence",
            )
    selected_hard: set[str] = set()
    grouped: set[str] = set()
    unresolved_or: set[str] = set()
    unresolved_without_policy: set[str] = set()
    for nid, node in nodes.items():
        groups = node.get("prerequisite_groups", [])
        if not isinstance(groups, list) or any(not isinstance(g, dict) for g in groups):
            errors.append(f"{nid}: invalid prerequisite groups")
            continue
        for g in groups:
            ids = g.get("edge_ids", [])
            if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids):
                errors.append(f"{nid}: malformed prerequisite group")
                continue
            check(
                g.get("mode") in {"AND", "OR"} and bool(ids),
                f"{nid}: invalid prerequisite group mode/edges",
            )
            check(len(ids) == len(set(ids)), f"{nid}: duplicate prerequisite")
            for eid in ids:
                check(
                    eid in edges
                    and edges[eid].get("consumer") == nid
                    and edges[eid].get("hard_precedence") is True,
                    f"{nid}: wrong prerequisite ownership {eid}",
                )
                check(eid not in grouped, f"{eid}: counted in multiple prerequisite groups")
                grouped.add(eid)
                if eid in edges:
                    check(
                        edges[eid].get("logical_mode") == g.get("mode"),
                        f"{eid}: group/edge logical mode mismatch",
                    )
            if g.get("mode") == "OR":
                selected = g.get("selected_edge_id")
                if selected is None:
                    unresolved_or.add(nid)
                    if g.get("selection_policy") != "PER_INSTALL_USER_BACKEND":
                        unresolved_without_policy.add(nid)
                else:
                    check(selected in ids, f"{nid}: selected OR edge is not an alternative")
                    if selected in ids:
                        selected_hard.add(selected)
            else:
                selected_hard.update(ids)
    expected_hard = {eid for eid, e in edges.items() if e.get("hard_precedence")}
    check(
        grouped == expected_hard,
        "hard dependencies missing or incorrectly repeated in prerequisite groups",
    )
    # Conservative node-level DAG: phase-specific contracts must be separate nodes
    # when mutual producer/consumer phases otherwise form a cycle.
    graph = {nid: [] for nid in nodes}
    indegree = {nid: 0 for nid in nodes}
    for eid in selected_hard:
        e = edges.get(eid, {})
        a, b = e.get("producer"), e.get("consumer")
        if a in nodes and b in nodes:
            graph[a].append(b)
            indegree[b] += 1
    pending = [nid for nid, d in indegree.items() if d == 0]
    visited = 0
    while pending:
        nid = pending.pop()
        visited += 1
        for target in graph[nid]:
            indegree[target] -= 1
            if indegree[target] == 0:
                pending.append(target)
    check(visited == len(nodes), "cycle in selected hard precedence graph")
    for nid, node in nodes.items():
        ready = node.get("assignment_status") in {"READY", "RUNNING"}
        complete = node.get("completion_claim") == "COMPLETE"
        if ready:
            check(
                node.get("selection") in {"SELECTED", "SELECTED_REFERENCE_INCREMENT"},
                f"{nid}: READY without selected scope",
            )
            check(nid not in unresolved_or, f"{nid}: READY with unresolved OR choice")
            for field in (
                "authority_verified",
                "writer_free_verified",
                "resources_verified",
                "decisions_resolved",
            ):
                check(node.get(field) is True, f"{nid}: READY without {field}")
            for kind in ("authority", "writer_slot", "resource_capacity", "decision"):
                records = [
                    evidence[x] for x in node.get("admission_evidence_ids", []) if x in evidence
                ]
                check(
                    any(
                        x.get("kind") == kind
                        and x.get("passed") is True
                        and x.get("scope_node_id") == nid
                        for x in records
                    ),
                    f"{nid}: READY lacks exact {kind} evidence",
                )
        if ready or complete:
            for eid in selected_hard:
                e = edges.get(eid, {})
                if e.get("consumer") == nid and (
                    complete or e.get("prerequisite_stage", "start") == "start"
                ):
                    check(
                        e.get("evidence_satisfied") is True,
                        f"{nid}: missing hard predecessor evidence {eid}",
                    )
        if complete:
            criteria = node.get("acceptance_criteria", [])
            check(
                bool(criteria) and bool(node.get("completion_requirements")),
                f"{nid}: COMPLETE lacks explicit acceptance boundary",
            )
            qualified = [
                evidence[x]
                for x in node.get("evidence_ids", [])
                if x in evidence
                and evidence[x].get("acceptance_qualified") is True
                and evidence[x].get("scope_node_id") == nid
            ]
            covered = {c for ev in qualified for c in ev.get("criteria_covered", [])}
            check(
                bool(qualified) and set(criteria) <= covered,
                f"{nid}: unproved COMPLETE/consumer claim",
            )
            check(nid not in unresolved_or, f"{nid}: COMPLETE with unresolved OR choice")
    atomic_groups: dict[str, list[dict[str, Any]]] = {}
    for node in nodes.values():
        group = node.get("atomic_delivery_group")
        if group is not None:
            check(isinstance(group, str) and bool(group), "invalid atomic delivery group")
            if isinstance(group, str) and group:
                atomic_groups.setdefault(group, []).append(node)
    for group, members in atomic_groups.items():
        check(len(members) >= 2, f"{group}: atomic group needs sibling nodes")
        completion_producers = [
            {
                edge["producer"]
                for edge in plan["edges"]
                if edge.get("consumer") == member["id"]
                and edge.get("hard_precedence")
                and edge.get("prerequisite_stage") == "completion"
            }
            for member in members
        ]
        check(
            bool(completion_producers)
            and bool(completion_producers[0])
            and all(producers == completion_producers[0] for producers in completion_producers),
            f"{group}: atomic siblings need identical completion gates",
        )
        completed = [n for n in members if n.get("completion_claim") == "COMPLETE"]
        if completed:
            check(
                len(completed) == len(members),
                f"{group}: atomic siblings cannot complete separately",
            )
            prs = [n.get("completion_evidence_pr") for n in completed]
            check(
                len(prs) == len(members)
                and all(isinstance(x, str) and "/pull/" in x for x in prs)
                and len(set(prs)) == 1,
                f"{group}: atomic siblings need one exact PR receipt",
            )
    running = [n["repository"] for n in nodes.values() if n.get("assignment_status") == "RUNNING"]
    check(len(running) == len(set(running)), "overlapping active repository writers")
    for h in plan["handoffs"]:
        check(
            h.get("producer_lane") in lanes and h.get("consumer_lane") in lanes,
            f"{h.get('id')}: invalid handoff ownership",
        )
        check(h.get("phase") in PHASES | {"distribution"}, f"{h.get('id')}: invalid handoff phase")
        check(
            h.get("execution_authorized") is False,
            f"{h.get('id')}: planning handoff cannot authorize execution",
        )
    for rollup in plan.get("rollups", []):
        children = rollup.get("children", [])
        check(len(children) == len(set(children)), "parent rollup double-counts children")
        check(
            rollup.get("parent") in nodes and all(c in nodes for c in children),
            "invalid parent rollup reference",
        )
        check(
            rollup.get("rule") in {"ALL_REQUIRED", "REFERENCE_ONLY"}, "invalid parent rollup rule"
        )
        if (
            rollup.get("rule") == "ALL_REQUIRED"
            and nodes.get(rollup.get("parent"), {}).get("completion_claim") == "COMPLETE"
        ):
            check(
                all(nodes.get(c, {}).get("completion_claim") == "COMPLETE" for c in children),
                "parent COMPLETE with incomplete required child",
            )
    if require_complete:
        for key, value in plan.get("completeness", {}).items():
            check(value is True, f"completion gate open: {key}")
        check(bool(plan.get("completeness")), "completeness declaration missing")
        for item in plan["audit_obligations"]:
            check(item.get("status") == "CLOSED", f"audit obligation open: {item.get('id')}")
        for sid, s in sources.items():
            check(s.get("read_complete") is True, f"{sid}: unread source ranges")
            check(s.get("commit_sha") is not None, f"{sid}: commit binding unverified")
        for lid, lane in lanes.items():
            check(bool(lane.get("owning_register")), f"{lid}: owning register not delivered")
        check(
            not unresolved_without_policy,
            "unresolved OR decisions prevent complete graph qualification",
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--check-rendered", action="store_true")
    args = parser.parse_args()
    try:
        data = load(args.snapshot)
        errors = validate(data, args.require_complete)
        if args.check_rendered and not errors:
            from render_snapshot import render

            for name, text in render(data).items():
                target = args.snapshot.parent / name
                if not target.is_file() or target.read_text(encoding="utf-8") != text:
                    errors.append(f"generated view differs or missing: {name}")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"result": "FAIL", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    complete = not errors and not validate(data, True)
    print(
        json.dumps(
            {
                "result": "FAIL" if errors else "PASS_INCLUDED_SNAPSHOT_ONLY",
                "complete_delivery": complete,
                "claim_boundary": "Offline structure does not prove external source truth, independent review or protected delivery.",
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
