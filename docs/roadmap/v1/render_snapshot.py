"""Deterministic human views of the pinned federated planning snapshot."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from validate_snapshot import load, validate


def clean(value: Any) -> str:
    return str(value).replace("|", "/").replace("\n", " ")


def mermaid(value: Any) -> str:
    return clean(value).replace('"', "'").replace("<", "(").replace(">", ")")[:100]


def render(p: dict[str, Any]) -> dict[str, str]:
    errors = validate(p)
    if errors:
        raise ValueError("Cannot render invalid snapshot: " + "; ".join(errors))
    out: dict[str, str] = {}
    nodes = {n["id"]: n for n in p["nodes"]}
    intro = (
        "This is a pinned planning projection for assignment `" + p["assignment_id"] + "`. "
        "Owning roadmap, backlog, code and qualification records remain authoritative. "
        "It grants no product pickup, release, deployment or resource lease.\n\n"
    )
    done = sum(o["status"] == "CLOSED" for o in p["audit_obligations"])
    lines = [
        "# DJConnect federated delivery planning v1\n\n",
        intro,
        f"Portfolio: {p['durable_delivery']['portfolio_register']}. Pinned on {p['created_at']}.\n\n",
        "## Delivery state\n\n",
        "| Boundary | State |\n|---|---|\n",
    ]
    for k, v in p["conclusions"].items():
        lines.append(f"| `{k}` | `{clean(v)}` |\n")
    census = p.get("source_capture", {}).get("tree_census_readback", {})
    lines += [
        "\n",
        f"The snapshot has {len(p['lanes'])} repository lanes, {len(p['sources'])} pinned sources, "
        f"{len(p['nodes'])} records and {len(p['edges'])} typed relations. Records are not a feature count. "
        f"{done} of {len(p['audit_obligations'])} audit/delivery obligations are closed.\n\n",
    ]
    if census:
        rows = census["lanes"].values()
        tracked = sum(row["tracked_markdown"] for row in rows)
        included = sum(row["included_markdown"] for row in rows)
        classified = sum(row.get("historically_classified_markdown", 0) for row in rows)
        unclassified = tracked - included - classified
        lines.append(
            f"Exact observed main trees contain {tracked} tracked Markdown paths; {included} paths have individual source rows. "
            f"Another {classified} have exact path/blob historical classifications without full-text reads; "
            f"{unclassified} paths remain unclassified. No path count alone grants current authority.\n\n"
        )
    lines += [
        "## Current five-item Execution Horizon\n\n",
        "This distribution order is retained from the current management/engineering records. Each item remains subject to its own evidence and explicit authorization.\n\n",
        "| Order | Planned item | Owning node | Direct condition |\n|---:|---|---|---|\n",
    ]
    for h in p["execution_horizon"]:
        lines.append(
            f"| {h['order']} | {clean(h['title'])} | `{h['node']}` | {clean(h['disposition'])} |\n"
        )
    lines += [
        "\n## Product sequence and parallel work\n\n",
        "DJ Intelligence Evolution → Reference Experience → Apple Premium Experience → Public Release Readiness → Productization → Product & Community Readiness → Community Public Release. "
        "The dotted milestone arrows show product priority. Independent contract, source and test preparation may proceed; an integrated consumer claim waits for its exact predecessor evidence.\n\n",
        "The selected VibeCast reference increment still needs the Apple-owner to physical portrait-Pi active-Session receipt. The Cast receiver is a later feasibility step. "
        "The original selected E2E verification path is recorded complete in the candidate owning roadmap and backlog; optional additions remain deferred.\n\n",
        "## Current admission\n\n",
        f"Host verification: `{p['host_readiness']['command']}` exited `{p['host_readiness']['exit_code']}` with `{p['host_readiness']['verdict']}` and onboarding `{p['host_readiness']['onboarding']}`. "
        "This does not grant future product pickup. Current local ESP32 and Windows WIP is outside this planning writer.\n\n",
        "## Findings\n\n",
    ]
    evidence = {e["id"]: e for e in p["evidence"]}
    for f in p["findings"]:
        receipts = " ".join(
            f"[{eid}]({evidence[eid]['url']})" for eid in f.get("evidence_ids", [])
        )
        lines.append(
            f"- **{f['id']} ({f['status']}):** {f['description']} Sources: {', '.join('`' + x + '`' for x in f['source_ids'])}."
            + (f" Evidence: {receipts}." if receipts else "") + "\n"
        )
    lines += [
        "\n## Files and checks\n\n",
        "[SOURCES.md](SOURCES.md) is the source-to-node completeness matrix. [CATALOGUE.md](CATALOGUE.md) preserves existing IDs and dispositions. "
        "[DEPENDENCIES.md](DEPENDENCIES.md), [HANDOFFS.md](HANDOFFS.md) and [LANES.md](LANES.md) are generated from the same JSON. "
        "[OPEN_WORK.md](OPEN_WORK.md) lists exact unclosed obligations.\n\n",
        "```sh\npython3 validate_snapshot.py djconnect-platform-v1.json --check-rendered\n"
        "python3 -m unittest -v test_snapshot\n"
        "python3 validate_snapshot.py djconnect-platform-v1.json --require-complete\n```\n\n",
        "The offline validator checks internal consistency, not whether a remote source or receipt is true. Freshness is a separate read-only head check. "
        "A complete-delivery result requires closed source, review, protected merge and Finalization evidence.\n",
    ]
    out["README.md"] = "".join(lines)

    lines = [
        "# Source-to-node completeness matrix\n\n",
        intro,
        "| Source ID | Owning repository / exact source | Pin | Read boundary | Disposition / mapped destination | Remaining |\n|---|---|---|---|---|---|\n",
    ]
    for s in p["sources"]:
        target = ", ".join("`" + x + "`" for x in s["mapped_node_ids"]) or clean(
            s.get("exclusion_reason", "—")
        )
        lines.append(
            f"| `{s['id']}` | `{s['repository']}` / [{clean(s['path'])}]({s['url']}) | `{s['commit_sha'] or 'UNKNOWN'}` / `{s['blob_sha']}` | {clean(s['read_boundary'])} | `{s['disposition']}`: {target} | {clean(s['remaining'])} |\n"
        )
    if census:
        lines += [
            "\n## Exact observed main-tree Markdown census\n\n",
            clean(census["boundary"]) + "\n\n",
            "| Lane | Observed tree | Tracked Markdown | Individually read / represented | Historical path-only classification | Unclassified frontier |\n|---|---|---:|---:|---:|---:|\n",
        ]
        for lid, row in census["lanes"].items():
            lines.append(
                f"| `{lid}` | `{row['commit_sha']}` | {row['tracked_markdown']} | {row['included_markdown']} | {row.get('historically_classified_markdown', 0)} | {row.get('unclassified_markdown', row['not_individually_included_markdown'])} |\n"
            )
    historical = p.get("source_capture", {}).get("historical_path_dispositions", {})
    if historical:
        lines += [
            "\n## Path-only historical dispositions\n\n",
            clean(historical["method"]) + "\n\n",
            "| Lane | Category | Paths | Authority | Disposition |\n|---|---|---:|---|---|\n",
        ]
        for group in historical["groups"]:
            authorities = ", ".join(f"`{sid}`" for sid in group["authority_source_ids"])
            lines.append(
                f"| `{group['lane']}` | `{group['category']}` | {len(group['entries'])} | {authorities} | {clean(group['reason'])} |\n"
            )
        lines.append("\nExact path/blob entries are in the machine-readable snapshot; their contents were not fully read.\n")
    scan = p.get("source_capture", {}).get("reference_scan", {})
    if scan:
        lines += [
            "\n## Relative Markdown links awaiting source triage\n\n",
            clean(scan["method"]) + "\n\n",
            clean(scan["disposition"]) + "\n\n",
        ]
        triage = scan.get("triage", {})
        lines.extend(
            f"- `{path}` — {clean(triage.get(path, 'UNTRIAGED'))}\n"
            for path in scan["unmapped_paths"]
        )
    out["SOURCES.md"] = "".join(lines)

    lines = [
        "# Included records and existing identities\n\n",
        intro,
        "A `PROJ::` or `INV::` key is a projection reference; it does not replace an existing source ID or authorize work.\n\n",
    ]
    for family in sorted({n["family"] for n in p["nodes"]}):
        lines += [
            f"## {family}\n\n",
            "| ID | Outcome | Selection | Evidence | Owner | Authority |\n|---|---|---|---|---|---|\n",
        ]
        for n in p["nodes"]:
            if n["family"] == family:
                lines.append(
                    f"| `{n['id']}` | {clean(n['title'])} | `{n['selection']}` | `{n['evidence_state']}` | `{n['lane']}` | `{n['canonical_authority']}` |\n"
                )
        lines.append("\n")
    out["CATALOGUE.md"] = "".join(lines).rstrip() + "\n"

    lines = [
        "# Repository lanes and entrypoints\n\n",
        intro,
        "| Lane | Repository | Role | Owning register | Entrypoint |\n|---|---|---|---|---|\n",
    ]
    for lane in p["lanes"]:
        reg = lane["owning_register"] or "PENDING"
        lines.append(
            f"| `{lane['id']}` | `{lane['repository']}` | {clean(lane['role'])} | {reg} | [{lane['id']}](lanes/{lane['id']}.md) |\n"
        )
        relevant = [
            h for h in p["handoffs"] if lane["id"] in (h["producer_lane"], h["consumer_lane"])
        ]
        selected = [
            n
            for n in p["nodes"]
            if n["lane"] == lane["id"]
            and n["selection"] in {"SELECTED", "SELECTED_REFERENCE_INCREMENT"}
            and n["assignment_status"] == "NOT_ISSUED"
        ]
        sl = [
            f"# {lane['id']} — {lane['repository']}\n\n",
            intro,
            f"**Owns:** {lane['inventory_scope']}. Profiles: {lane['profiles']}.\n\n",
            f"**Baseline main:** `{lane['baseline_sha']}`. **Owning register:** {reg}. **Portfolio:** {lane['portfolio_register']}.\n\n",
            f"**Current assignment/WIP:** {lane['writer_state']}. Product pickup: `{lane['product_pickup']}`. Capacity: `{lane['resource_capacity']}`.\n\n",
            "## Selected and proposed outcome\n\n",
        ]
        if selected:
            sl.append(
                "Selected in an owning source, without a new execution assignment: "
                + ", ".join("`" + n["id"] + "`" for n in selected)
                + ".\n\n"
            )
        else:
            sl.append(
                "No new selected product execution is established for this lane by this planning assignment.\n\n"
            )
        sl += [
            f"Planning continuation: {lane['proposed_documentary_next_step']}\n\n",
            "## Owning backlog and handoffs\n\n",
            f"Read the local `REPOSITORY_STATUS.md` and existing TODO/ISSUES or release metadata that this repository actually owns. Local backlog audit: {lane['local_backlog_audit']}.\n\n",
        ]
        for h in relevant:
            sl.append(
                f"- `{h['id']}`: {h['producer_lane']} → {h['consumer_lane']}; {h['subset']}. Phase `{h['phase']}`; exact artifact `{h['exact_artifact']}`; acceptance owner `{h['acceptance_owner']}`.\n"
            )
        sl += [
            "\n## DoR, DoD and resource boundary\n\n",
            "DoR for a future product pickup: selected owning scope, exact phase-specific producer receipt, authority, free writer slot and measured capacity. "
            "UNKNOWN is not FREE. No issue or prompt alone starts a writer.\n\n",
            "DoD for a future authorized vertical assignment: contract and user-facing acceptance, applicable five-language UX, tests, independent review, "
            "required CI, fixes, protected merge, exact-main readback and owning Finalization; any release/install acceptance requires separate explicit release scope.\n\n",
            f"Workflow effect audit: {lane['release_effect_audit']}. Shared signer, HA lab and devices are not reserved by this plan. "
            "A delegated publication requires both source and receiving distribution writer coordination.\n\n",
            "## Copyable continuation prompt\n\n```text\n",
            f"Continue assignment {p['assignment_id']} in {lane['repository']} / {lane['id']}.\n",
            f"Read {lane['portfolio_register']} and {reg}; keep the current WIP/assignment intact: {lane['writer_state']}.\n",
            f"Use the existing owning backlog, exact source pins and local bootstrap. Planning outcome: {lane['proposed_documentary_next_step']}\n",
            "Selected owning node IDs (no new pickup): "
            + (
                ", ".join(n["id"] for n in selected)
                if selected
                else "none established for this lane"
            )
            + ".\n",
            f"Local test-policy audit: {lane['local_test_policy']}. Workflow effects: {lane['release_effect_audit']}.\n",
            "This is documentary planning only. Do not infer product selection, writer availability, resource capacity or release authority.\n",
            "For any later selected vertical work, first prove DoR, then include UX, tests, review, fixes, protected merge and finalization in the same assignment.\n",
            "Coordinate these exact handoff IDs and acceptance owners through the owning registers:\n",
        ]
        for h in relevant:
            sl.append(
                f"- {h['id']}: {h['producer_lane']} -> {h['consumer_lane']}; {h['subset']}; phase {h['phase']}; acceptance owner {h['acceptance_owner']}; exact artifact {h['exact_artifact']}.\n"
            )
        sl += [
            "Do not start a release or deployment from this prompt.\n",
            "Report PLANNING_DELIVERY, PRODUCT_DELIVERY and EXECUTION_READY separately. Stop after this planning delivery.\n```\n",
        ]
        out[f"lanes/{lane['id']}.md"] = "".join(sl)
    out["LANES.md"] = "".join(lines)

    lines = [
        "# Federated dependencies\n\n",
        intro,
        "Only `hard_precedence=true` enters the execution DAG. Strategy order, publication handoff and temporary resource conflicts stay distinct. "
        "All new cross-repository acceptance edges are phase-specific and currently lack exact joint receipts.\n\n",
        "| ID | Producer → consumer | Kind / phase | Gate at | AND/OR | Required subset | Exact evidence | Hard? |\n|---|---|---|---|---|---|---|---|\n",
    ]
    for e in p["edges"]:
        lines.append(
            f"| `{e['id']}` | `{e['producer']}` → `{e['consumer']}` | `{e['kind']}` / `{e['phase']}` | `{e.get('prerequisite_stage', 'start')}` | `{e['logical_mode']}` | {clean(e['required_subset'])} | {clean(e['contract_or_evidence'])} | {'yes' if e['hard_precedence'] else 'no'} |\n"
        )
    lines += ["\n## Choices and parent rollups\n\n"]
    for c in p.get("choice_constraints", []):
        detail = c.get("description") or c.get("reason") or c.get("notes") or ""
        alternatives = ", ".join("`" + str(x) + "`" for x in c.get("alternatives", []))
        lines.append(
            f"- `{c['id']}`: `{c['mode']}`; {clean(detail)}"
            + (f" Alternatives: {alternatives}." if alternatives else "")
            + (f" Required: {clean(c['required'])}." if c.get("required") else "")
            + "\n"
        )
    for r in p.get("rollups", []):
        lines.append(
            f"- `{r['parent']}` uses `{r['rule']}` for {', '.join('`' + x + '`' for x in r['children'])}. {clean(r['scope'])}\n"
        )
    lines += [
        "\nNo parent completion is inferred from a child source commit, mock, tag or report. Exact consumer evidence is required.\n"
    ]
    out["DEPENDENCIES.md"] = "".join(lines)

    lines = [
        "# Producer and consumer handoffs\n\n",
        intro,
        "| Handoff | Producer → consumer | Phase | Subset | Artifact | Compatibility | Acceptance owner | State |\n|---|---|---|---|---|---|---|---|\n",
    ]
    for h in p["handoffs"]:
        lines.append(
            f"| `{h['id']}` | `{h['producer_lane']}` → `{h['consumer_lane']}` | `{h['phase']}` | {clean(h['subset'])} | `{h['exact_artifact']}` | {clean(h['compatibility'])} | `{h['acceptance_owner']}` | {clean(h['status'])} |\n"
        )
    lines += [
        "\n## Resource and follow-up policy\n\n",
        "One repository has at most one mutating assignment. A waiting assignment is not a free writer slot. "
        "Shared machines, signer, HA lab, API budget and devices require measured, bounded reservations and real quiescence evidence.\n\n",
    ]
    for r in p.get("resource_constraints", []):
        lines.append(
            f"- `{r['id']}`: capacity `{r['capacity']}`; state `{r['current']}`; release condition: {r['release_evidence']}.\n"
        )
    lines += [
        "\nFuture monitoring uses fresh source and consumer evidence, names exact blockers, avoids duplicate comments and treats two unchanged checks as an investigation signal. No monitor is installed by this assignment.\n"
    ]
    out["HANDOFFS.md"] = "".join(lines)

    lines = [
        "# Open audit and delivery obligations\n\n",
        intro,
        "| ID | Status | Scope | Exact remaining action or closure evidence |\n|---|---|---|---|\n",
    ]
    for o in p["audit_obligations"]:
        lines.append(
            f"| `{o['id']}` | `{o['status']}` | {clean(o['scope'])} | {clean(o['reason'])} |\n"
        )
    out["OPEN_WORK.md"] = "".join(lines)

    ids = {nid: "n" + str(i) for i, nid in enumerate(nodes)}
    for file, edgeset, title in [
        (
            "milestones",
            [e for e in p["edges"] if e["kind"] == "strategy_order"],
            "Product sequence; no global implementation barrier",
        ),
        (
            "hard-dependencies",
            [e for e in p["edges"] if e["hard_precedence"]],
            "Phase-specific hard predecessors; exact acceptance still required",
        ),
    ]:
        seen = {e[k] for e in edgeset for k in ("producer", "consumer")}
        m = ["flowchart LR", f'  note["{title}"]']
        for nid in nodes:
            if nid in seen:
                m.append(f'  {ids[nid]}["{mermaid(nodes[nid]["title"])}"]')
        or_edge_ids = set()
        if file == "hard-dependencies":
            choice_number = 0
            edge_index = {e["id"]: e for e in edgeset}
            for n in p["nodes"]:
                for group in n.get("prerequisite_groups", []):
                    if group["mode"] != "OR":
                        continue
                    choice = "choice" + str(choice_number)
                    choice_number += 1
                    m.append(f'  {choice}{{"OR: one selected option"}}')
                    for eid in group["edge_ids"]:
                        e = edge_index[eid]
                        or_edge_ids.add(eid)
                        m.append(f"  {ids[e['producer']]} -.->|alternative| {choice}")
                    m.append(
                        f"  {choice} -->|{mermaid(group.get('selection_policy', 'exact choice required'))}| {ids[n['id']]}"
                    )
        for e in edgeset:
            if e["id"] in or_edge_ids:
                continue
            stage = e.get("prerequisite_stage", "start")
            m.append(
                f"  {ids[e['producer']]} {'-->' if e['hard_precedence'] else '-.->'}|{e['phase']} / {stage}| {ids[e['consumer']]}"
            )
        out[f"diagrams/{file}.mmd"] = "\n".join(m) + "\n"
    mids = {lane["id"]: "l" + str(i) for i, lane in enumerate(p["lanes"])}
    m = ["flowchart LR", '  note["Source and receiving writer slots coordinate at publication"]']
    for lane in p["lanes"]:
        m.append(f'  {mids[lane["id"]]}["{lane["id"]}"]')
    for h in p["handoffs"]:
        m.append(f"  {mids[h['producer_lane']]} -.->|{h['id']}| {mids[h['consumer_lane']]}")
    out["diagrams/cross-repository.mmd"] = "\n".join(m) + "\n"
    m = ["flowchart LR", '  portfolio["Planning frontier: exact nodes, no new product pickup"]']
    frontier = {h["node"] for h in p["execution_horizon"]}
    frontier.update(n["id"] for n in p["nodes"] if str(n["selection"]).startswith("SELECTED"))
    for nid in nodes:
        if nid not in frontier:
            continue
        n = nodes[nid]
        if n["assignment_status"] in {"READY", "RUNNING"}:
            state = n["assignment_status"]
        elif nid == "HACS-3.3.0-001":
            state = "BLOCKED: planned investigation; no assessment pickup"
        elif not str(n["selection"]).startswith("SELECTED"):
            state = "BLOCKED: planned; no selection or release authority"
        else:
            unsatisfied = [
                e["id"]
                for e in p["edges"]
                if e["consumer"] == nid
                and e["hard_precedence"]
                and e.get("prerequisite_stage", "start") == "start"
                and not e["evidence_satisfied"]
            ]
            state = "BLOCKED: " + (
                unsatisfied[0] if unsatisfied else "no product pickup / writer and capacity unknown"
            )
        m.append(f'  {ids[nid]}["{mermaid(n["title"])}: {mermaid(state)}"]')
        m.append(f"  portfolio -.-> {ids[nid]}")
    out["diagrams/ready-frontier.mmd"] = "\n".join(m) + "\n"
    return out


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "djconnect-platform-v1.json").resolve()
    views = render(load(path))
    for name, body in views.items():
        target = path.parent / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    print(f"Generated {len(views)} views from the pinned JSON.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
