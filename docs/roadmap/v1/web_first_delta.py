"""Additive docs-only web-first planning extension over the existing delta.

The legacy validator still validates every predecessor field after removing only
this versioned extension. Product code and historical snapshot are untouched.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

PREFIX = "WEB::"
EDGE_PREFIX = "WEB-FIRST-"
ASSIGNMENT = "DJC-VIBECAST-WEB-FIRST-GUEST-EXPERIENCE-DESIGN-V1-20261015"
DOC = "docs/product/VIBECAST_WEB_FIRST_EXPERIENCE_V1.md"
AUTH = "docs/product/VIBECAST_ONBOARDING_GUEST_AUTHORITY_V1.md"
APPLE = "docs/product/APPLE_VIBECAST_GUEST_MODE_V1.md"
# Unique bounded subsets reuse existing parents; no new top-level initiative.
SLICES = {
    "DOCS": ("DJC-CORE", "PROJ::ROADMAP::P2-VIBECAST", "Whole web-first documentary design", DOC),
    "DISPOSITION": (
        "DJC-CORE",
        "PROJ::ROADMAP::P2-VIBECAST",
        "Implement reviewed web-first legacy disposition",
        DOC,
    ),
    "TRUST": (
        "DJC-CORE",
        "PROJ::INNOVATION::GUEST",
        "Qualify browser-bound onboarding and guest trust contract",
        AUTH,
    ),
    "BOOTSTRAP": (
        "DJC-API",
        "PROJ::ROADMAP::P2-VIBECAST",
        "Temporary encrypted rendezvous service",
        AUTH,
    ),
    "DISPLAY": (
        "DJC-CORE",
        "PROJ::ROADMAP::P2-VIBECAST",
        "Separate HA code and readonly display grant",
        AUTH,
    ),
    "OWNER-SCANNER": (
        "DJC-APPLE",
        "PROJ::ROADMAP::P2-VIBECAST",
        "Paired owner scanner and explicit installation confirmation",
        DOC,
    ),
    "SHARED": (
        "DJC-CORE",
        "PROJ::ROADMAP::P2-VIBECAST",
        "Explicit shared Flow NowPlaying Forecast projection",
        AUTH,
    ),
    "MEDIA": (
        "DJC-CORE",
        "PROJ::ROADMAP::P2-VIBECAST",
        "Independent shared artwork and speech grants expiry attribution",
        AUTH,
    ),
    "GUEST": (
        "DJC-CORE",
        "PROJ::INNOVATION::GUEST",
        "Invitation redemption guest principal and revocation",
        AUTH,
    ),
    "BROWSER": (
        "DJC-VIBECAST",
        "PROJ::ROADMAP::P2-VIBECAST",
        "One responsive web UI and accountless browser join",
        DOC,
    ),
    "DISTRIBUTION": (
        "DJC-VIBECAST",
        "PROJ::ROADMAP::P2-VIBECAST",
        "Reviewed generic static bootstrap and browser distribution",
        DOC,
    ),
    "DISCOVERY": (
        "DJC-CORE",
        "PROJ::INNOVATION::GUEST",
        "Admission-scoped HA local discovery announcement",
        APPLE,
    ),
    "APP": (
        "DJC-APPLE",
        "PROJ::INNOVATION::GUEST",
        "Isolated temporary guest shell discovery scanner leave home restore",
        APPLE,
    ),
    "REACTIONS": (
        "DJC-CORE",
        "PROJ::ROADMAP::AUDIENCE",
        "Five subject-bound ephemeral reactions and bounded sparkle",
        DOC,
    ),
    "AGGREGATE": (
        "DJC-CORE",
        "PROJ::ROADMAP::AUDIENCE-OBSERVATION",
        "Temporary audience aggregation and host lock budget policy",
        DOC,
    ),
    "INFLUENCE": (
        "DJC-CORE",
        "PROJ::ROADMAP::AUDIENCE-OBSERVATION",
        "Bounded DJ-led Mood direction influence and owner confirmation",
        DOC,
    ),
    "CHAT": (
        "DJC-CORE",
        "PROJ::INNOVATION::GUEST",
        "Guest Ask DJ isolated thread safe dispatch and spend budgets",
        AUTH,
    ),
    "REQUEST": (
        "DJC-CORE",
        "PROJ::INNOVATION::GUEST",
        "Exact recording clarification and guest proposal dialogue",
        DOC,
    ),
    "EFFECT-POLICY": (
        "DJC-CORE",
        "PROJ::ROADMAP::P2-VIBECAST",
        "DJ request consideration fairness and uncertain-effect policy",
        AUTH,
    ),
    "ENQUEUE": (
        "DJC-CORE",
        "PROJ::INNOVATION::GUEST",
        "Real enqueue reconciliation and observed-recording Persona announcement",
        DOC,
    ),
    "JOINT": (
        "DJC-CORE",
        "PROJ::ROADMAP::P2-VIBECAST",
        "Joint browser native media lifecycle physical five-language acceptance",
        DOC,
    ),
}
PAIRS = {
    ("DOCS", "DISPOSITION"),
    ("DOCS", "TRUST"),
    ("DISPOSITION", "BOOTSTRAP"),
    ("TRUST", "BOOTSTRAP"),
    ("DISPOSITION", "DISPLAY"),
    ("TRUST", "DISPLAY"),
    ("TRUST", "OWNER-SCANNER"),
    ("BOOTSTRAP", "OWNER-SCANNER"),
    ("DISPLAY", "OWNER-SCANNER"),
    ("DISPOSITION", "SHARED"),
    ("TRUST", "SHARED"),
    ("SHARED", "MEDIA"),
    ("TRUST", "GUEST"),
    ("GUEST", "BROWSER"),
    ("SHARED", "BROWSER"),
    ("DISPLAY", "BROWSER"),
    ("BOOTSTRAP", "DISTRIBUTION"),
    ("BROWSER", "DISTRIBUTION"),
    ("GUEST", "DISCOVERY"),
    ("GUEST", "APP"),
    ("DISCOVERY", "APP"),
    ("SHARED", "APP"),
    ("GUEST", "REACTIONS"),
    ("SHARED", "REACTIONS"),
    ("REACTIONS", "AGGREGATE"),
    ("AGGREGATE", "INFLUENCE"),
    ("GUEST", "CHAT"),
    ("SHARED", "CHAT"),
    ("CHAT", "REQUEST"),
    ("REQUEST", "ENQUEUE"),
    ("EFFECT-POLICY", "ENQUEUE"),
    ("TRUST", "EFFECT-POLICY"),
    *{
        (x, "JOINT")
        for x in ("OWNER-SCANNER", "DISTRIBUTION", "MEDIA", "APP", "INFLUENCE", "CHAT", "ENQUEUE")
    },
}
REUSE = {
    "SLICE::CORE::BROADCAST-CONTRACT": "SHARED",
    "SLICE::CORE::AMBIENT-RENDERER": "BROWSER",
    "SLICE::APPLE::OWNER-HANDOFF": "OWNER-SCANNER",
    "FORECAST::CORE::CONTRACT": "SHARED",
    "MEDIA::CORE::SESSION-CONTRACT": "MEDIA",
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def strip(plan):
    old = deepcopy(plan)
    d = old["planning_maintenance"]
    d.pop("web_first_receipt", None)
    d["nodes"] = [n for n in d["nodes"] if not n.get("id", "").startswith(PREFIX)]
    d["edges"] = [e for e in d["edges"] if not e.get("id", "").startswith(EDGE_PREFIX)]
    return old


def validate(plan, previous_validator):
    d = plan["planning_maintenance"]
    r = d["web_first_receipt"]
    old = strip(plan)
    errors = previous_validator(old)

    def check(value, message):
        if not value:
            errors.append("web-first: " + message)

    check(r.get("schema_version") == "djconnect-web-first-design/1", "unknown extension version")
    check(
        r.get("base_delta_version") == "djconnect-federated-planning-delta/11"
        and d.get("schema_version") == r.get("base_delta_version"),
        "unreconciled base version",
    )
    check(
        r.get("assignment_id") == ASSIGNMENT
        and r.get("issue") == "https://github.com/pcvantol/djconnect/issues/1174",
        "authority missing",
    )
    check(
        r.get("product_implementation") == "Planned"
        and r.get("joint_acceptance") == "OPEN"
        and r.get("automatic_dispatch") is False
        and r.get("runtime_writes") is False,
        "implementation or dispatch overclaim",
    )
    check(
        r.get("phase") in {"LOCAL_DOCUMENTARY", "SOURCE_PROTECTED_MERGED"},
        "unknown documentary phase",
    )
    if r.get("phase") == "SOURCE_PROTECTED_MERGED":
        import re

        check(
            bool(re.fullmatch("[a-f0-9]{40}", str(r.get("source_main_sha", ""))))
            and r.get("protected_merge") is True
            and r.get("required_checks") == "PASS",
            "missing protected source evidence",
        )
    check(
        r.get("open_decisions")
        == [
            "short_url",
            "unspecified_exception",
            "five_emoji",
            "crypto_service_browser",
            "shared_media_rights",
            "apple_renderer",
            "budgets_share_policy",
        ],
        "open choices hidden",
    )
    # Baseline structure is immutable; only document hashes may follow deliberate edits.
    check(
        digest(old["planning_maintenance"]["nodes"]) == r.get("predecessor_nodes_sha256"),
        "prior nodes changed",
    )
    check(
        digest(old["planning_maintenance"]["edges"]) == r.get("predecessor_edges_sha256"),
        "prior edges changed",
    )
    nodes = {n.get("id"): n for n in d["nodes"]}
    selected = {nid for nid in nodes if isinstance(nid, str) and nid.startswith(PREFIX)}
    check(
        len(nodes) == len(d["nodes"]) and selected == {PREFIX + x for x in SLICES},
        "duplicate/missing bounded subset",
    )
    lanes = {lane["id"]: lane["repository"] for lane in plan["lanes"]}
    for key, (lane, parent, title, contract) in SLICES.items():
        n = nodes.get(PREFIX + key, {})
        check(
            n.get("lane") == lane
            and n.get("repository") == lanes[lane]
            and n.get("parent_reference") == parent
            and n.get("contract_binding") == contract
            and n.get("source_ids") == ["OWNER-WEB-FIRST-1174"]
            and n.get("scope")
            and n.get("acceptance_boundary"),
            "ownership/provenance " + key,
        )
        check(
            (n.get("status"), n.get("assignment_status"))
            == (("Completed", "DESIGN_AUTHORED") if key == "DOCS" else ("Planned", "NOT_ISSUED")),
            "status overclaim " + key,
        )
    edges = [e for e in d["edges"] if e.get("id", "").startswith(EDGE_PREFIX)]
    expected = {(PREFIX + a, PREFIX + b) for a, b in PAIRS} | {
        (a, PREFIX + b) for a, b in REUSE.items()
    }
    check(
        len(edges) == len(expected)
        and {(e.get("producer"), e.get("consumer")) for e in edges} == expected,
        "dependency set changed",
    )
    check(len({e.get("id") for e in d["edges"]}) == len(d["edges"]), "duplicate edge")
    for e in edges:
        check(
            e.get("hard_precedence") is True
            and e.get("logical_mode") == "AND"
            and e.get("source_ids") == ["OWNER-WEB-FIRST-1174"]
            and e.get("contract_or_evidence") in {DOC, AUTH, APPLE},
            "edge authority",
        )
    for nid in selected:
        groups = nodes[nid].get("prerequisite_groups", [])
        grouped = [eid for g in groups for eid in g.get("edge_ids", [])]
        incoming = {e["id"] for e in edges if e["consumer"] == nid}
        check(
            set(grouped) == incoming
            and len(grouped) == len(incoming)
            and all(g.get("mode") == "AND" for g in groups),
            "prerequisite group " + nid,
        )
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
    check(seen == len(graph), "cycle across frozen and maintained graph")
    refs = d["document_references"]
    paths = [x["path"] for x in refs]
    check(len(paths) == len(set(paths)), "duplicate document binding")
    root = Path(__file__).resolve().parents[3]
    for path in (DOC, AUTH, APPLE):
        ref = next((x for x in refs if x["path"] == path), {})
        check(
            ref.get("sha256") == hashlib.sha256((root / path).read_bytes()).hexdigest(),
            "document hash " + path,
        )
    return errors


def add_views(out, plan):
    r = plan["planning_maintenance"]["web_first_receipt"]
    intro = (
        f"Web-first #1174 documentary extension: {r['phase']}; design authored only, product implementation Planned/NOT_ISSUED and joint acceptance OPEN. "
        "Cast-first/native-TV prerequisites superseded for forward design; original receipts remain historical. URL/exception/emoji OPEN. No automatic dispatch or runtime/publication grant.\n\n"
    )
    for path in out:
        if path.endswith(".md"):
            first, rest = out[path].split("\n", 1)
            out[path] = first + "\n\n" + intro + rest.lstrip("\n")
    out["HANDOFFS.md"] += (
        "\nWEB #1174 → existing Core1101/Apple87/receiver10: canonical experience, guest trust, temporary app isolation; source and Finalization pins separately required. Existing API owner proposed for temporary bootstrap only. No new runtime pickup.\n"
    )
    out["diagrams/cross-repository.mmd"] += (
        "  API -->|temporary bootstrap only| VibeCast\n  Apple -->|explicit owner or guest scanner| VibeCast\n"
    )
    out["diagrams/ready-frontier.mmd"] = (
        'flowchart LR\n  Docs["#1174 designs authored; delivery gates separate"] --> Trust["Trust and legacy disposition qualification Planned"]\n  Trust --> Join["Bootstrap/display/shared guest slices Planned; no dispatch"]\n'
    )
    return out
