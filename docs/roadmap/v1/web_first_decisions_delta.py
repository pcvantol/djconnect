"""Version2 decisions and selected public-distribution subset; no runtime dispatch."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

ASSIGNMENT = "DJC-VIBECAST-WEB-FIRST-DECISIONS-DELTA-V1-20261015"
SELECTION = "DJC-VIBECAST-TV-BOOTSTRAP-CLOUDFLARE-V1-20261015"
ISSUE = "https://github.com/pcvantol/djconnect/issues/1174#issuecomment-6201605985"
RECEIVER = "https://github.com/pcvantol/djconnect-vibecast-receiver/issues/16"
DOC = "docs/product/VIBECAST_WEB_ENTRY_DISTRIBUTION_V1.md"
PRIOR = "history/20261015/web-first-design-before-decisions.json"
PRIOR_HASH = "a35482a0c2cbf04781fc27d90b664e51a9f795bf27df5e8daa42568acc444dcb"
OPEN = [
    "reaction_set_count_labels_rocket",
    "crypto_service_browser",
    "shared_media_rights",
    "apple_renderer",
    "budgets_share_policy",
    "actual_account_domain_tls",
    "cast_continuity_qualification",
]
RESOLVED = {
    "entry_url": "https://vibecast.tv/",
    "domain_evidence": "OWNER_REPORTED_PURCHASE_NOT_DNS_TLS_PROOF",
    "web_first_exception": "EXISTING_APP_GUEST_JOIN",
}
PUBLIC = {
    "assignment_id": SELECTION,
    "issue": RECEIVER,
    "selection_state": "SELECTED_QUEUED",
    "executor_ack": "PENDING",
    "status": "Planned",
    "prerequisites": [
        "DECISIONS_DELTA_PROTECTED_DELIVERY_AND_FINALIZATION",
        "OWN_PREVIOUS_WIP_CLOSED",
        "FRESH_RECEIVER_ADMISSION",
    ],
    "autonomous_pickup_after_prerequisites": True,
    "new_general_start_permission_required": False,
    "integration_or_hardware_pass": False,
}
INTEGRATION = {
    "status": "Planned",
    "assignment_status": "SELECTED_CONTRACT_GATED",
    "assignment_id": SELECTION,
    "executor_ack": "PENDING",
    "required_nodes": ["WEB::TRUST", "WEB::BOOTSTRAP"],
    "public_build_blocker": False,
    "full_onboarding_acceptance": "OPEN",
}
SHARED = {
    "status": "Planned",
    "assignment_status": "NOT_ISSUED",
    "required_nodes": ["WEB::BROWSER"],
    "public_build_blocker": False,
}
E2E = {
    "status": "OPEN",
    "required_nodes": ["WEB::DISPLAY", "WEB::OWNER-SCANNER"],
    "required_subsets": ["PUBLIC_WEB_DELIVERY", "RENDEZVOUS_INTEGRATION"],
    "public_build_blocker": False,
}


def load_prior():
    return json.loads((Path(__file__).parent / PRIOR).read_text())


def pin_edge():
    return {
        "id": "WEB-FIRST-DECISIONS-PIN",
        "producer": "WEB::DOCS",
        "consumer": "WEB::DISTRIBUTION",
        "kind": "documentary_predecessor",
        "phase": "public_web_delivery",
        "prerequisite_stage": "protected_delivery_and_finalization",
        "consumer_subset": "PUBLIC_WEB_DELIVERY",
        "hard_precedence": True,
        "logical_mode": "AND",
        "required_subset": ASSIGNMENT
        + " actual source and Finalization design/DAG pin; previous1175/1176 alone insufficient",
        "contract_or_evidence": DOC,
        "reason": "Explicit receiver16 selection waits for this new documentary delta; no API or Cast prerequisite for independent public frontend/build/CD",
        "source_ids": ["OWNER-WEB-FIRST-DECISIONS-6201605985"],
    }


def expected_edges(prior):
    edges = deepcopy(prior["edges"])
    for edge in edges:
        if edge["consumer"] == "WEB::DISTRIBUTION":
            subset = (
                "FULL_SHARED_GUEST_ACCEPTANCE"
                if edge["producer"] == "WEB::BROWSER"
                else "RENDEZVOUS_INTEGRATION"
            )
            edge.update(
                consumer_subset=subset,
                phase="integration_acceptance",
                prerequisite_stage="qualified_integration_contract",
                required_subset="Qualified "
                + edge["producer"]
                + " for "
                + subset
                + "; no prerequisite for independent PUBLIC_WEB_DELIVERY",
            )
    edges.append(pin_edge())
    for key in ("DISPLAY", "OWNER-SCANNER"):
        edge = pin_edge()
        edge.update(
            id="WEB-FIRST-DECISIONS-E2E-" + key,
            producer="WEB::" + key,
            kind="joint_acceptance",
            phase="onboarding_e2e",
            prerequisite_stage="qualified_producer_and_consumer",
            consumer_subset="APPLE_HA_ONBOARDING_E2E",
            required_subset="Qualified "
            + key
            + " with public frontend and rendezvous connected; not a public build or adapter source prerequisite",
            reason="Full two-step onboarding acceptance requires actual HA display admission and Apple scanner; do not absorb producer implementation into receiver16",
        )
        edges.append(edge)
    return edges


def expected_distribution(prior):
    node = deepcopy(next(n for n in prior["nodes"] if n["id"] == "WEB::DISTRIBUTION"))
    edges = expected_edges(prior)
    node.update(
        assignment_status="SELECTED_QUEUED",
        selected_assignment=SELECTION,
        selected_issue=RECEIVER,
        title="Receiver public bootstrap selected; serviceadapter conditionally selected; full E2E separately gated",
        scope="Receiver16 PUBLIC_WEB_DELIVERY and conditionally RENDEZVOUS_INTEGRATION alongside pinned Cast output; API/Core/Apple producers not selected",
        acceptance_boundary="Public website/CI/Pages/domain, service adapter, Apple/HA onboarding and full shared guest acceptance are distinct; no executor ACK or product PASS",
        delivery_subsets={
            "PUBLIC_WEB_DELIVERY": deepcopy(PUBLIC),
            "RENDEZVOUS_INTEGRATION": deepcopy(INTEGRATION),
            "APPLE_HA_ONBOARDING_E2E": deepcopy(E2E),
            "FULL_SHARED_GUEST_ACCEPTANCE": deepcopy(SHARED),
        },
        prerequisite_groups=[
            {
                "mode": "AND",
                "consumer_subset": subset,
                "edge_ids": [
                    e["id"]
                    for e in edges
                    if e["consumer"] == "WEB::DISTRIBUTION" and e.get("consumer_subset") == subset
                ],
            }
            for subset in (
                "PUBLIC_WEB_DELIVERY",
                "RENDEZVOUS_INTEGRATION",
                "APPLE_HA_ONBOARDING_E2E",
                "FULL_SHARED_GUEST_ACCEPTANCE",
            )
        ],
    )
    return node


def validate(plan, legacy_validator, previous_validator):
    d = plan["planning_maintenance"]
    r = d["web_first_receipt"]
    delta = r.get("decisions_delta", {})
    errors = []

    def check(value, message):
        if not value:
            errors.append("web decisions: " + message)

    path = Path(__file__).parent / PRIOR
    check(
        hashlib.sha256(path.read_bytes()).hexdigest() == PRIOR_HASH,
        "historical design snapshot changed",
    )
    prior = load_prior()
    # Delegate all predecessor checks to the unchanged version1 semantics with
    # only this declared WEB delta restored; document hashes still validate current docs.
    old = deepcopy(plan)
    od = old["planning_maintenance"]
    od["web_first_receipt"] = deepcopy(prior["receipt"])
    od["nodes"] = [n for n in od["nodes"] if not n["id"].startswith("WEB::")] + deepcopy(
        prior["nodes"]
    )
    od["edges"] = [e for e in od["edges"] if not e["id"].startswith("WEB-FIRST-")] + deepcopy(
        prior["edges"]
    )
    errors.extend(legacy_validator(old, previous_validator))
    allowed = {"schema_version", "open_decisions", "resolved_decisions", "decisions_delta"}
    check(
        {k: v for k, v in r.items() if k not in allowed}
        == {k: v for k, v in prior["receipt"].items() if k not in allowed},
        "original delivery receipt overwritten",
    )
    check(
        r.get("schema_version") == "djconnect-web-first-design/2"
        and r.get("resolved_decisions") == RESOLVED
        and r.get("open_decisions") == OPEN,
        "resolved/open decision drift",
    )
    check(
        delta.get("assignment_id") == ASSIGNMENT
        and delta.get("authority") == ISSUE
        and delta.get("prior_snapshot") == PRIOR
        and delta.get("prior_snapshot_sha256") == PRIOR_HASH,
        "delta authority/provenance",
    )
    check(delta.get("phase") in {"LOCAL_DOCUMENTARY", "SOURCE_PROTECTED_MERGED"}, "delta phase")
    if delta.get("phase") == "SOURCE_PROTECTED_MERGED":
        check(
            bool(re.fullmatch("[a-f0-9]{40}", str(delta.get("source_main_sha", ""))))
            and delta.get("protected_merge") is True
            and delta.get("required_checks") == "PASS",
            "missing exact protected delivery",
        )
    check(
        delta.get("selected_receiver") == PUBLIC
        and delta.get("runtime_writes") is False
        and delta.get("ci_config_writes") is False
        and delta.get("deployment") is False
        and delta.get("other_product_admission") is False,
        "selection or effect overclaim",
    )
    nodes = {n["id"]: n for n in d["nodes"]}
    web = [n for n in d["nodes"] if n["id"].startswith("WEB::")]
    check(
        len(nodes) == len(d["nodes"])
        and {n["id"] for n in web} == {n["id"] for n in prior["nodes"]},
        "duplicate/missing nodes",
    )
    for before in prior["nodes"]:
        expected = expected_distribution(prior) if before["id"] == "WEB::DISTRIBUTION" else before
        check(
            nodes.get(before["id"]) == expected,
            "unselected node overwritten or subset drift " + before["id"],
        )
    edges = [e for e in d["edges"] if e["id"].startswith("WEB-FIRST-")]
    check(edges == expected_edges(prior), "phase-bound dependency drift")
    check(len({e["id"] for e in d["edges"]}) == len(d["edges"]), "duplicate edge")
    allnodes = {n["id"] for n in plan["nodes"]} | set(nodes)
    degree = dict.fromkeys(allnodes, 0)
    graph = {n: [] for n in allnodes}
    for e in [*plan["edges"], *d["edges"]]:
        a, b = e.get("producer"), e.get("consumer")
        check(a in allnodes and b in allnodes, "dangling reference")
        if a in allnodes and b in allnodes and e.get("hard_precedence"):
            graph[a].append(b)
            degree[b] += 1
    ready = [n for n in degree if degree[n] == 0]
    seen = 0
    while ready:
        node = ready.pop()
        seen += 1
        for target in graph[node]:
            degree[target] -= 1
            if degree[target] == 0:
                ready.append(target)
    check(seen == len(graph), "cycle")
    root = Path(__file__).resolve().parents[3]
    ref = next((x for x in d["document_references"] if x["path"] == DOC), {})
    check(
        ref.get("sha256") == hashlib.sha256((root / DOC).read_bytes()).hexdigest(),
        "decision contract hash",
    )
    return errors
