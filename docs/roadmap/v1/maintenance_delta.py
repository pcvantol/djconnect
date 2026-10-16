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


def _validate_hybrid(delta, check):
    """Admit only this selected bounded producer; never admit its consumers."""
    r = delta.get("hybrid_receipt", {})
    check(r.get("schema_version") == "djconnect-hybrid-maintenance/1"
          and r.get("assignment_id") == "DJC-CORE-HYBRID-TRANSPORT-CONVERGENCE-V1-20261013"
          and r.get("selection_url") == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6149934177",
          "hybrid owner selection missing")
    check(r.get("base_sha") == "9efd1977768d2574b66c16de9c5d8ba53e9157b1"
          and r.get("branch") == "codex/hybrid-transport-convergence-v1"
          and r.get("ack") == 6185332170 and r.get("material_start") == 6185498845
          and r.get("contract_commit") == "454a470f9eb68fbce667738423c1779a62920162"
          and r.get("material_commit") == "cf5c5adba523c0e799e56f999e2fa243a0df38ec",
          "hybrid admission missing")
    check(r.get("previous_delta") == "history/20261015/current-artist-maintenance-v9.json"
          and r.get("previous_snapshot") == "history/20261015/current-artist-snapshot-v9.json"
          and all(bool(re.fullmatch(r"[a-f0-9]{64}", str(r.get(k, ""))))
                  for k in ("previous_delta_sha256", "previous_snapshot_sha256")),
          "hybrid predecessor preservation missing")
    check(r.get("predecessor_finalization_pr") == "https://github.com/pcvantol/djconnect/pull/1169"
          and r.get("predecessor_closure") == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6185306694"
          and r.get("early_apple_handoff") == "https://github.com/pcvantol/djconnect-app/issues/87#issuecomment-6185756317",
          "hybrid closure or handoff binding missing")
    delivered = r.get("phase") == "SOURCE_PROTECTED_MERGED"
    check(r.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"}
          and r.get("source_delivery") == ("PROTECTED_MERGED" if delivered else "UNPUBLISHED"),
          "hybrid delivery phase invalid")
    check(r.get("native") == "OPEN_APPLE" and r.get("installed") == "NOT_RUN"
          and r.get("hardware") == "NOT_RUN" and r.get("joint_acceptance") == "OPEN"
          and r.get("consumer_writes") is False and r.get("automatic_dispatch") is False
          and r.get("family_acceptance") == "PARTIAL",
          "hybrid consumer/effect overclaim")
    if delivered:
        check(bool(re.fullmatch(r"[a-f0-9]{40}", str(r.get("source_main_sha", ""))))
              and bool(re.fullmatch(r"https://github.com/pcvantol/djconnect/pull/[0-9]+", str(r.get("source_pr", ""))))
              and r.get("source_review") == "PASS" and r.get("required_checks") == "PASS"
              and r.get("protected_merge") is True
              and all(bool(re.fullmatch(r"[a-f0-9]{64}", str(r.get(k, ""))))
                      for k in ("archive_sha256", "formal_evidence_sha256")),
              "hybrid protected delivery evidence missing")
    expected = {"TRANSPORT::CORE::CONTRACT", "TRANSPORT::CORE::RECOVERY",
                "TRANSPORT::CORE::PAIRED-ACTIONS", "TRANSPORT::APPLE::HYBRID", "TRANSPORT::JOINT::HYBRID"}
    nodes = [n for n in delta.get("nodes", []) if str(n.get("id", "")).startswith("TRANSPORT::")]
    check({n.get("id") for n in nodes} == expected, "one bounded hybrid family required")
    check(all(n.get("parent_reference") == "PROJ::ROADMAP::CONNECTIVITY" for n in nodes),
          "hybrid existing connectivity parent missing")
    pairs = {(e.get("producer"), e.get("consumer")) for e in delta.get("edges", [])
             if str(e.get("id", "")).startswith("HYBRID-")}
    check(pairs == {
        ("TRANSPORT::CORE::CONTRACT", "TRANSPORT::CORE::RECOVERY"),
        ("TRANSPORT::CORE::RECOVERY", "TRANSPORT::CORE::PAIRED-ACTIONS"),
        ("TRANSPORT::CORE::CONTRACT", "TRANSPORT::APPLE::HYBRID"),
        ("TRANSPORT::CORE::PAIRED-ACTIONS", "TRANSPORT::JOINT::HYBRID"),
        ("TRANSPORT::APPLE::HYBRID", "TRANSPORT::JOINT::HYBRID"),
    }, "hybrid prerequisite scope invalid")
    return delivered


def validate_delta(plan: dict[str, Any]) -> list[str]:
    d = plan.get(KEY)
    if not isinstance(d, dict):
        return ["maintenance: expected object"]
    errors = []

    def check(condition, reason):
        if not condition:
            errors.append("maintenance: " + reason)

    version = d.get("schema_version")
    if version == "djconnect-federated-planning-delta/15":
        from display_admission_delta import validate
        return validate(plan, validate_delta)
    if version == "djconnect-federated-planning-delta/14":
        from settings_consolidation_delta import validate
        return validate(plan, validate_delta)
    if version == "djconnect-federated-planning-delta/13":
        from passive_surface_delta import validate
        return validate(plan, validate_delta)
    if version == "djconnect-federated-planning-delta/12":
        from speech_persona_delta import validate
        return validate(plan, validate_delta)
    if "web_first_receipt" in d:
        from web_first_delta import validate
        return validate(plan, validate_delta)
    if version == "djconnect-federated-planning-delta/11":
        from session_artwork_delta import validate
        return validate(plan, validate_delta)
    implementation = version in {
        "djconnect-federated-planning-delta/2",
        "djconnect-federated-planning-delta/3",
        "djconnect-federated-planning-delta/4",
        "djconnect-federated-planning-delta/5",
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10",
    }
    artwork = version in {
        "djconnect-federated-planning-delta/3",
        "djconnect-federated-planning-delta/4",
        "djconnect-federated-planning-delta/5",
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10",
    }
    narrative = version in {
        "djconnect-federated-planning-delta/4",
        "djconnect-federated-planning-delta/5",
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10",
    }
    forecast = version in {
        "djconnect-federated-planning-delta/5",
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10",
    }
    ambient = version in {
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10",
    }
    dialogue = version in {"djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10"}
    hybrid = version == "djconnect-federated-planning-delta/10"
    hybrid_delivered = False
    if hybrid:
        hybrid_delivered = _validate_hybrid(d, check)
    dialogue_delivered = False
    if dialogue:
        r = d.get("dialogue_receipt", {})
        observed = r.get("consumer_reconciliation")
        if observed is not None:
            check(isinstance(observed, dict) and observed == {
                "presence_node": "SLICE::APPLE::DJ-PRESENCE-CONTROL",
                "apple_checkpoint": "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6168870771",
                "core_presence": "DELIVERED_CLOSED",
                "installed_advertisement": "ABSENT_IN_OWNER_READBACK",
                "native_mac": "BLOCKED_HOST_AUTOMATION",
                "dialogue_adoption": "OPEN",
                "intra_track_visibility": "OPEN",
                "consumer_writes": False,
                "observed_status": "In progress",
                "scope": "EXISTING_APPLE_WRITER_REGISTER_READBACK_NOT_CORE_ADMISSION",
            }, "consumer readback must not grant admission or acceptance")
        check(
            r.get("schema_version") == "djconnect-shared-dialogue-maintenance/1"
            and r.get("assignment_id") == "DJC-CORE-ASKDJ-CONTEXTUAL-DIALOGUE-V1-20261013"
            and r.get("selection_url") == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6145537044"
            and r.get("added_requirement") == "DJC-MOMENT-TRACK-INSIGHT-DRILLDOWN-V1-20261013"
            and r.get("extension_url") == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6146489526",
            "shared dialogue owner binding missing",
        )
        check(
            r.get("base_sha") == "c955ec80407f4ab0237bc4e9381761d3c9274617"
            and r.get("branch") == "codex/askdj-contextual-dialogue-v1"
            and r.get("contract_commit") == "592953ce4eb48aafcd1d0c17761a5ac4fda1bfd1"
            and r.get("material_commit") == "d672ddf5e4fce9013498a37d37c3599f39868b18"
            and r.get("extension_contract") == "4eb814a43f532d305e42fdbcc2af658259b94e64"
            and (r.get("ack"), r.get("material_start"), r.get("extension_ack")) == (6145812752, 6146387187, 6149786410),
            "shared dialogue admission missing",
        )
        check(
            r.get("previous_delta") == "history/20261013/history-summary-maintenance-v8.json"
            and bool(re.fullmatch(r"[a-f0-9]{64}", str(r.get("previous_delta_sha256", "")))),
            "shared dialogue predecessor binding missing",
        )
        check(r.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"}, "shared dialogue phase invalid")
        dialogue_delivered = r.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(r.get("source_delivery") == ("PROTECTED_MERGED" if dialogue_delivered else "UNPUBLISHED"), "shared dialogue delivery invalid")
        check(
            r.get("native") == "NOT_RUN" and r.get("hardware") == "NOT_RUN"
            and r.get("installed") == "NOT_RUN" and r.get("joint_acceptance") == "OPEN"
            and r.get("consumer_writes") is False and r.get("automatic_dispatch") is False,
            "shared dialogue consumer or effect overclaim",
        )
        if dialogue_delivered:
            check(
                bool(re.fullmatch(r"[a-f0-9]{40}", str(r.get("source_main_sha", ""))))
                and bool(re.fullmatch(r"https://github.com/pcvantol/djconnect/pull/[0-9]+", str(r.get("source_pr", ""))))
                and r.get("source_review") == "PASS" and r.get("required_checks") == "PASS"
                and r.get("protected_merge") is True
                and all(bool(re.fullmatch(r"[a-f0-9]{64}", str(r.get(k, "")))) for k in ("archive_sha256", "formal_evidence_sha256")),
                "shared dialogue protected delivery evidence missing",
            )
        families = {n.get("id") for n in d.get("nodes", []) if str(n.get("id", "")).startswith(("CONVERSATION::", "INSIGHT::"))}
        check(families == {"CONVERSATION::CORE::SHARED-DIALOGUE", "CONVERSATION::APPLE::SHARED-ADOPTION", "INSIGHT::CORE::MOMENT-DRILLDOWN", "INSIGHT::APPLE::MOMENT-DRILLDOWN", "CONVERSATION::PRODUCT::JOINT"}, "one bounded shared dialogue family required")
        for n in d.get("nodes", []):
            if n.get("id") in families:
                check(n.get("parent_reference") in {"PROJ::ROADMAP::LIFECYCLE", "PROJ::ROADMAP::INTERACTIVE"}, "shared dialogue parent missing")

    ambient_delivered = False
    forecast_delivered = False
    check(
        version
        in {
            "djconnect-federated-planning-delta/1",
            "djconnect-federated-planning-delta/2",
            "djconnect-federated-planning-delta/3",
            "djconnect-federated-planning-delta/4",
            "djconnect-federated-planning-delta/5",
            "djconnect-federated-planning-delta/6",
            "djconnect-federated-planning-delta/7",
            "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10",
        },
        "unsupported schema",
    )
    if version in {"djconnect-federated-planning-delta/8", "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10"}:
        r = d.get("summary_receipt", {})
        check(
            r.get("schema_version") == "djconnect-summary-maintenance/1"
            and r.get("assignment_id") == "DJC-CORE-SESSION-HISTORY-SUMMARY-V1-20261013"
            and r.get("base_sha") == "06e04d9996a8909337b6eb78b8568e1e2ddead5f"
            and r.get("branch") == "codex/session-history-summary-v1",
            "summary admission missing",
        )
        check(
            r.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"},
            "summary phase invalid",
        )
        check(
            all(r.get(k) == "NOT_RUN" for k in ("native", "installed", "hardware"))
            and r.get("joint_acceptance") == "OPEN",
            "summary consumer overclaim",
        )
        complete = r.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(
            r.get("source_delivery") == ("PROTECTED_MERGED" if complete else "UNPUBLISHED"),
            "summary delivery invalid",
        )
        if complete:
            check(
                bool(re.fullmatch(r"[a-f0-9]{40}", str(r.get("source_main_sha", ""))))
                and r.get("required_checks") == "PASS"
                and r.get("source_review") == "PASS"
                and r.get("protected_merge") is True,
                "summary merge proof missing",
            )
    delivered = False
    if implementation:
        receipt = d.get("implementation_receipt", {})
        delivered = receipt.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(
            receipt.get("assignment_id") == "DJC-CORE-DJ-PRESENCE-V1-20261011",
            "implementation assignment binding missing",
        )
        check(
            receipt.get("selection_url")
            == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6111222122",
            "implementation owner binding missing",
        )
        check(
            receipt.get("joint_product_acceptance") == "OPEN",
            "joint acceptance remains Planned without native receipts",
        )
        check(
            receipt.get("native") == "NOT_RUN"
            and receipt.get("installed") == "NOT_RUN"
            and receipt.get("hardware") == "NOT_RUN",
            "unqualified consumer effect",
        )
        check(
            receipt.get("phase")
            in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"},
            "unqualified delivery phase",
        )
        check(
            receipt.get("source_delivery") == ("PROTECTED_MERGED" if delivered else "UNPUBLISHED"),
            "unqualified delivery phase",
        )
        if delivered:
            check(
                bool(re.fullmatch(r"[a-f0-9]{40}", str(receipt.get("source_main_sha", "")))),
                "exact source main receipt missing",
            )
            check(
                bool(
                    re.fullmatch(
                        r"https://github.com/pcvantol/djconnect/pull/[0-9]+",
                        str(receipt.get("source_pr", "")),
                    )
                ),
                "source PR receipt missing",
            )
            check(
                receipt.get("source_review") == "PASS"
                and receipt.get("required_checks") == "PASS"
                and receipt.get("protected_merge") is True,
                "protected delivery evidence missing",
            )
            check(
                all(
                    bool(re.fullmatch(r"[a-f0-9]{64}", str(receipt.get(k, ""))))
                    for k in ("archive_sha256", "formal_evidence_sha256")
                ),
                "exact artifact readback missing",
            )
        check(
            receipt.get("previous_delta") == "history/20261011/presence-design-maintenance-v1.json"
            and len(str(receipt.get("previous_delta_sha256", ""))) == 64,
            "previous version binding missing",
        )
    correction_delivered = False
    if artwork:
        corrections = d.get("correction_receipts", [])
        check(
            isinstance(corrections, list) and len(corrections) == 1,
            "one bounded correction required",
        )
        c = corrections[0] if isinstance(corrections, list) and len(corrections) == 1 else {}
        correction_delivered = c.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(
            c.get("assignment_id") == "DJC-CORE-DISCOVERY-ARTWORK-CONTINUITY-V1-20261012",
            "correction assignment binding missing",
        )
        check(
            c.get("selection_url")
            == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6117357579",
            "correction owner binding missing",
        )
        check(
            c.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"},
            "unqualified correction phase",
        )
        check(
            c.get("source_delivery")
            == ("PROTECTED_MERGED" if correction_delivered else "UNPUBLISHED"),
            "unqualified correction delivery",
        )
        check(
            all(c.get(k) == "NOT_RUN" for k in ("native", "installed", "live_provider"))
            and c.get("joint_product_acceptance") == "OPEN",
            "unqualified correction consumer acceptance",
        )
        check(
            c.get("previous_delta")
            == "history/20261012/presence-implementation-maintenance-v2.json"
            and bool(re.fullmatch(r"[a-f0-9]{64}", str(c.get("previous_delta_sha256", "")))),
            "correction history binding missing",
        )
        if correction_delivered:
            check(
                bool(re.fullmatch(r"[a-f0-9]{40}", str(c.get("source_main_sha", ""))))
                and bool(
                    re.fullmatch(
                        r"https://github.com/pcvantol/djconnect/pull/[0-9]+",
                        str(c.get("source_pr", "")),
                    )
                ),
                "correction source receipt missing",
            )
            check(
                c.get("source_review") == "PASS"
                and c.get("required_checks") == "PASS"
                and c.get("protected_merge") is True,
                "correction protected checks missing",
            )
            check(
                all(
                    bool(re.fullmatch(r"[a-f0-9]{64}", str(c.get(k, ""))))
                    for k in ("archive_sha256", "formal_evidence_sha256")
                ),
                "correction artifact receipt missing",
            )
    narrative_delivered = False
    if narrative:
        r = d.get("narrative_receipt", {})
        narrative_delivered = r.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(
            r.get("assignment_id") == "DJC-CORE-NARRATIVE-ALBUM-CONTINUITY-V1-20261012",
            "narrative assignment binding missing",
        )
        check(
            r.get("selection_url")
            == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6121336412"
            and r.get("selection_authority") == "DIRECT_HUMAN_INSTRUCTION",
            "narrative admission binding missing",
        )
        check(
            r.get("base_sha") == "0f37b53cc56f89109a1adcbcf39dd454ba52c72d"
            and r.get("branch") == "codex/narrative-album-continuity-v1",
            "narrative base/branch missing",
        )
        check(
            r.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"}
            and r.get("source_delivery")
            == ("PROTECTED_MERGED" if narrative_delivered else "UNPUBLISHED"),
            "unqualified narrative phase",
        )
        check(
            all(r.get(k) == "NOT_RUN" for k in ("native", "installed", "hardware"))
            and r.get("joint_product_acceptance") == "OPEN"
            and r.get("stage4_status") == "PARTIAL",
            "narrative consumer/stage overclaim",
        )
        check(
            r.get("previous_delta") == "history/20261012/artwork-continuity-maintenance-v3.json"
            and bool(re.fullmatch(r"[a-f0-9]{64}", str(r.get("previous_delta_sha256", "")))),
            "narrative history binding missing",
        )
        if narrative_delivered:
            check(
                bool(re.fullmatch(r"[a-f0-9]{40}", str(r.get("source_main_sha", ""))))
                and bool(
                    re.fullmatch(
                        r"https://github.com/pcvantol/djconnect/pull/[0-9]+",
                        str(r.get("source_pr", "")),
                    )
                ),
                "narrative source receipt missing",
            )
            check(
                r.get("source_review") == "PASS"
                and r.get("required_checks") == "PASS"
                and r.get("protected_merge") is True,
                "narrative protected checks missing",
            )
            check(
                all(
                    bool(re.fullmatch(r"[a-f0-9]{64}", str(r.get(k, ""))))
                    for k in ("archive_sha256", "formal_evidence_sha256")
                ),
                "narrative artifact receipt missing",
            )
    if forecast:
        f = d.get("forecast_receipt", {})
        forecast_delivered = f.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(
            f.get("assignment_id") == "DJC-CORE-SESSION-FORECAST-V1-20261012"
            and f.get("selection_url")
            == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6123328620",
            "forecast owner binding missing",
        )
        check(
            f.get("base_sha") == "e26888fc164fac1e5cb41908fd922d5f9a05e0bd"
            and f.get("branch") == "codex/session-forecast-v1",
            "forecast base/branch mismatch",
        )
        check(
            f.get("parent_node") == "PROJ::ROADMAP::DIRECTION", "existing direction parent required"
        )
        check(
            f.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"}
            and f.get("source_delivery")
            == ("PROTECTED_MERGED" if forecast_delivered else "UNPUBLISHED"),
            "unqualified forecast delivery",
        )
        check(
            all(f.get(k) == "NOT_RUN" for k in ("native", "installed", "hardware"))
            and f.get("joint_product_acceptance") == "OPEN"
            and f.get("visible_vibecast") == "PLANNED"
            and f.get("upcoming_media") == "UNQUALIFIED_ABSENT",
            "forecast consumer/upcoming overclaim",
        )
        check(
            f.get("artist_imagery_roles") == ["current", "contextual", "qualified_upcoming"]
            and f.get("artist_imagery_admission") == "CURRENT_ONLY_DISPLAY_BASIS",
            "imagery admission missing",
        )
        check(
            f.get("previous_delta") == "history/20261012/album-continuity-maintenance-v4.json"
            and bool(re.fullmatch(r"[a-f0-9]{64}", str(f.get("previous_delta_sha256", "")))),
            "forecast predecessor binding missing",
        )
        if forecast_delivered:
            check(
                bool(re.fullmatch(r"[a-f0-9]{40}", str(f.get("source_main_sha", ""))))
                and bool(
                    re.fullmatch(
                        r"https://github.com/pcvantol/djconnect/pull/[0-9]+",
                        str(f.get("source_pr", "")),
                    )
                ),
                "forecast source receipt missing",
            )
            check(
                f.get("source_review") == "PASS"
                and f.get("required_checks") == "PASS"
                and f.get("protected_merge") is True,
                "forecast protected delivery missing",
            )
            check(
                all(
                    bool(re.fullmatch(r"[a-f0-9]{64}", str(f.get(k, ""))))
                    for k in ("archive_sha256", "formal_evidence_sha256")
                ),
                "forecast artifact receipt missing",
            )
    if ambient:
        a = d.get("ambient_receipt", {})
        ambient_delivered = a.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(
            a.get("assignment_id") == "DJC-CORE-AMBIENT-FACT-MOMENT-CONVERGENCE-V1-20261012"
            and a.get("selection_url")
            == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6125691006",
            "ambient owner binding missing",
        )
        check(
            a.get("parent_node") == "PROJ::ROADMAP::P2-SESSION"
            and a.get("disposition") == "RETIREMENT_ONLY_QUALIFIED_SESSION_REUSE",
            "ambient scope mismatch",
        )
        check(
            a.get("phase") in {"LOCAL_IMPLEMENTATION_AND_QUALIFICATION", "SOURCE_PROTECTED_MERGED"}
            and a.get("source_delivery")
            == ("PROTECTED_MERGED" if ambient_delivered else "UNPUBLISHED"),
            "unqualified ambient delivery",
        )
        check(
            all(a.get(k) == "NOT_RUN" for k in ("native", "installed", "hardware"))
            and a.get("joint_product_acceptance") == "OPEN",
            "ambient consumer overclaim",
        )
        check(
            a.get("previous_delta") == "history/20261012/forecast-maintenance-v5.json"
            and bool(re.fullmatch(r"[a-f0-9]{64}", str(a.get("previous_delta_sha256", "")))),
            "ambient predecessor missing",
        )
        if ambient_delivered:
            check(
                bool(re.fullmatch(r"[a-f0-9]{40}", str(a.get("source_main_sha", ""))))
                and bool(
                    re.fullmatch(
                        r"https://github.com/pcvantol/djconnect/pull/[0-9]+",
                        str(a.get("source_pr", "")),
                    )
                ),
                "ambient source receipt missing",
            )
            check(
                a.get("source_review") == "PASS"
                and a.get("required_checks") == "PASS"
                and a.get("protected_merge") is True,
                "ambient protected checks missing",
            )
            check(
                all(
                    bool(re.fullmatch(r"[a-f0-9]{64}", str(a.get(k, ""))))
                    for k in ("archive_sha256", "formal_evidence_sha256")
                ),
                "ambient artifact receipt missing",
            )
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
    check(
        d.get("scope")
        == (
            "DOCUMENTARY_DELTA_ONLY"
            if version == "djconnect-federated-planning-delta/7"
            else "SELECTED_CORE_IMPLEMENTATION_DELTA"
            if implementation
            else "DOCUMENTARY_DELTA_ONLY"
        ),
        "invalid scope",
    )
    for field in ["nodes", "edges", "document_references"]:
        check(
            isinstance(d.get(field), list) and all(isinstance(x, dict) for x in d.get(field, [])),
            "invalid " + field,
        )
    if version in {"djconnect-federated-planning-delta/7", "djconnect-federated-planning-delta/8", "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10"}:
        r = d.get("documentary_receipt", {})
        check(
            r.get("assignment_id") == "DJC-SESSION-ENTRY-LIFECYCLE-HISTORY-DESIGN-V1-20261012"
            and r.get("addendum_id") == "DJC-APPLE-SESSION-NATIVE-SURFACES-DESIGN-V1-20261012"
            and r.get("selection_url")
            == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131363097"
            and r.get("ab_url")
            == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131072407"
            and r.get("c_url")
            == "https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6131317807",
            "combined documentary owner binding missing",
        )
        check(
            r.get("base_sha") == "e8bb982f148ac7a22b6991ee6f54d10188849ee0"
            and r.get("branch") == "codex/session-entry-lifecycle-history-design-v1"
            and r.get("previous_delta")
            == "history/20261012/ambient-convergence-maintenance-v6.json"
            and bool(re.fullmatch(r"[a-f0-9]{64}", str(r.get("previous_delta_sha256", "")))),
            "documentary predecessor/admission binding missing",
        )
        check(
            r.get("product_implementation") == "Planned"
            and all(r.get(k) == "NOT_RUN" for k in ("native", "installed", "hardware")),
            "documentary product overclaim",
        )
        check(
            r.get("phase") in {"LOCAL_DOCUMENTARY_QUALIFICATION", "SOURCE_PROTECTED_MERGED"},
            "invalid documentary delivery phase",
        )
        complete = r.get("phase") == "SOURCE_PROTECTED_MERGED"
        check(
            r.get("source_delivery") == ("PROTECTED_MERGED" if complete else "UNPUBLISHED"),
            "unqualified documentary delivery",
        )
        if complete:
            check(
                bool(re.fullmatch(r"[a-f0-9]{40}", str(r.get("source_main_sha", ""))))
                and bool(
                    re.fullmatch(
                        r"https://github.com/pcvantol/djconnect/pull/[0-9]+",
                        str(r.get("source_pr", "")),
                    )
                )
                and r.get("source_review") == "PASS"
                and r.get("required_checks") == "PASS"
                and r.get("protected_merge") is True
                and all(
                    bool(re.fullmatch(r"[a-f0-9]{64}", str(r.get(k, ""))))
                    for k in ("archive_sha256", "formal_evidence_sha256")
                ),
                "documentary protected delivery evidence missing",
            )
        for n in d.get("nodes", []):
            if str(n.get("id", "")).startswith(
                ("ENTRY::", "HISTORY::", "SURFACE::", "CONTINUATION::")
            ):
                check(
                    (n.get("status") == "Planned" and n.get("assignment_status") == "NOT_ISSUED")
                    or (
                        version in {"djconnect-federated-planning-delta/8", "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10"}
                        and n.get("id") == "HISTORY::CORE::SUMMARY"
                    ),
                    "documentary subset must remain Planned",
                )
                check(
                    n.get("parent_reference")
                    in {
                        "PROJ::ROADMAP::LIFECYCLE",
                        "PROJ::ROADMAP::P2-SESSION",
                        "PROJ::QUAL::CMB12-LIFECYCLE",
                        "CMB-12",
                        "PROJ::ROADMAP::CONTINUATION",
                    },
                    "documentary existing parent missing",
                )
    if errors:
        return errors
    inherited = {n["id"]: n for n in plan["nodes"]}
    nodes = {n.get("id"): n for n in d["nodes"]}
    if ambient:
        ambient_nodes = {
            nid for nid in nodes if isinstance(nid, str) and nid.startswith("AMBIENT::")
        }
        check(
            ambient_nodes
            == {"AMBIENT::CORE::CONVERGENCE", "AMBIENT::APPLE::JOIN", "AMBIENT::PRODUCT::JOINT"},
            "one Core convergence, Apple join and joint acceptance required",
        )
        check(
            all(
                nodes[nid].get("parent_reference") == "PROJ::ROADMAP::P2-SESSION"
                for nid in ambient_nodes
            ),
            "ambient existing Session content parent required",
        )
        ambient_edges = [
            e
            for e in d["edges"]
            if e.get("consumer") in ambient_nodes or e.get("producer") in ambient_nodes
        ]
        check(
            {(e.get("producer"), e.get("consumer")) for e in ambient_edges}
            == {
                ("AMBIENT::CORE::CONVERGENCE", "AMBIENT::APPLE::JOIN"),
                ("AMBIENT::CORE::CONVERGENCE", "AMBIENT::PRODUCT::JOINT"),
                ("AMBIENT::APPLE::JOIN", "AMBIENT::PRODUCT::JOINT"),
            },
            "ambient may not invent unrelated prerequisite gates",
        )
    check(
        len(nodes) == len(d["nodes"]) and None not in nodes and not (set(nodes) & set(inherited)),
        "duplicate or inherited node",
    )
    if artwork:
        check(
            {nid for nid in nodes if isinstance(nid, str) and nid.startswith("CORRECTION::")}
            == {
                "CORRECTION::CORE::DISCOVERY-ARTWORK",
                "CORRECTION::APPLE::DISCOVERY-ARTWORK-ACCEPTANCE",
            },
            "one existing-capability correction boundary required",
        )
    lanes = {lane["id"]: lane["repository"] for lane in plan["lanes"]}
    for nid, n in nodes.items():
        check(lanes.get(n.get("lane")) == n.get("repository"), "unknown owning lane/repository")
        presence_admitted = implementation and nid in {
            "SLICE::CORE::DJ-PRESENCE-CONTRACT",
            "SLICE::CORE::DJ-PRESENCE-POLICY",
        }
        correction_admitted = artwork and nid == "CORRECTION::CORE::DISCOVERY-ARTWORK"
        narrative_admitted = narrative and nid == "RELATION::CORE::ALBUM-CONTINUITY"
        forecast_admitted = forecast and nid in {
            "FORECAST::CORE::CONTRACT",
            "FORECAST::CORE::PROJECTION",
            "FORECAST::VIBECAST::COMPAT",
        }
        ambient_admitted = ambient and nid == "AMBIENT::CORE::CONVERGENCE"
        summary_admitted = (
            version in {"djconnect-federated-planning-delta/8", "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10"} and nid == "HISTORY::CORE::SUMMARY"
        )
        summary_delivered = d.get("summary_receipt", {}).get("phase") == "SOURCE_PROTECTED_MERGED"
        dialogue_admitted = dialogue and nid in {"CONVERSATION::CORE::SHARED-DIALOGUE", "INSIGHT::CORE::MOMENT-DRILLDOWN"}
        hybrid_admitted = hybrid and nid in {"TRANSPORT::CORE::CONTRACT", "TRANSPORT::CORE::RECOVERY", "TRANSPORT::CORE::PAIRED-ACTIONS"}
        admitted = (
            hybrid_admitted
            or dialogue_admitted
            or summary_admitted
            or ambient_admitted
            or presence_admitted
            or correction_admitted
            or narrative_admitted
            or forecast_admitted
        )
        node_delivered = (
            hybrid_delivered
            if hybrid_admitted
            else dialogue_delivered
            if dialogue_admitted
            else summary_delivered
            if summary_admitted
            else ambient_delivered
            if ambient_admitted
            else forecast_delivered
            if forecast_admitted
            else narrative_delivered
            if narrative_admitted
            else correction_delivered
            if correction_admitted
            else delivered
        )
        check(
            n.get("status")
            in (
                {"Completed" if node_delivered else "In progress"}
                if admitted
                else {"Planned", "Completed"}
            ),
            "invalid node status",
        )
        check(
            n.get("status") == "Planned" or admitted or nid == "SLICE::CORE::ACTIVE-SESSION-MOOD",
            "unadmitted implementation must remain Planned",
        )
        check(
            n.get("assignment_status")
            == (
                ("CORE_DELIVERED" if node_delivered else "IN_PROGRESS")
                if admitted
                else "NOT_ISSUED"
            ),
            "unadmitted assignment may not start",
        )
        check(
            all(
                n.get(k)
                for k in ["title", "scope", "acceptance_boundary", "contract_binding", "source_ids"]
            ),
            "node criteria/provenance missing",
        )
        check(
            n.get("source_ids")
            == (
                ["OWNER-HYBRID-TRANSPORT-20261013"]
                if hybrid and nid.startswith("TRANSPORT::")
                else ["OWNER-SHARED-DIALOGUE-20261013"]
                if dialogue and nid.startswith(("CONVERSATION::", "INSIGHT::"))
                else ["OWNER-SESSION-ENTRY-ABC-20261012"]
                if version
                in {"djconnect-federated-planning-delta/7", "djconnect-federated-planning-delta/8", "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10"}
                and nid.startswith(("ENTRY::", "HISTORY::", "SURFACE::", "CONTINUATION::"))
                else ["OWNER-AMBIENT-CONVERGENCE-20261012"]
                if ambient and nid.startswith("AMBIENT::")
                else ["OWNER-SESSION-FORECAST-20261012"]
                if forecast and nid.startswith("FORECAST::")
                else ["OWNER-NARRATIVE-ALBUM-20261012"]
                if narrative and nid.startswith("RELATION::")
                else ["OWNER-DISCOVERY-ARTWORK-20261012"]
                if artwork and nid.startswith("CORRECTION::")
                else ["OWNER-DJ-PRESENCE-20261011"]
            ),
            "unqualified provenance",
        )
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
        check(
            e.get("source_ids")
            == (
                ["OWNER-HYBRID-TRANSPORT-20261013"]
                if hybrid and str(e.get("id", "")).startswith("HYBRID-")
                else ["OWNER-SHARED-DIALOGUE-20261013"]
                if dialogue and str(e.get("id", "")).startswith("SHARED-DIALOGUE-")
                else ["OWNER-SESSION-ENTRY-ABC-20261012"]
                if version
                in {"djconnect-federated-planning-delta/7", "djconnect-federated-planning-delta/8", "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10"}
                and str(e.get("id", "")).startswith("ENTRY-ABC-")
                else ["OWNER-AMBIENT-CONVERGENCE-20261012"]
                if ambient and str(e.get("id", "")).startswith("AMBIENT-")
                else ["OWNER-SESSION-FORECAST-20261012"]
                if forecast and str(e.get("id", "")).startswith("FORECAST-")
                else ["OWNER-NARRATIVE-ALBUM-20261012"]
                if narrative and str(e.get("id", "")).startswith("ALBUM-")
                else ["OWNER-DISCOVERY-ARTWORK-20261012"]
                if artwork and str(e.get("id", "")).startswith("ARTWORK-")
                else ["OWNER-DJ-PRESENCE-20261011"]
            ),
            "edge provenance mismatch",
        )
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
    current = d.get("schema_version") in {
        "djconnect-federated-planning-delta/2",
        "djconnect-federated-planning-delta/3",
        "djconnect-federated-planning-delta/4",
        "djconnect-federated-planning-delta/5",
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11",
    }
    artwork = d.get("schema_version") in {
        "djconnect-federated-planning-delta/3",
        "djconnect-federated-planning-delta/4",
        "djconnect-federated-planning-delta/5",
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11",
    }
    delivery = d.get("implementation_receipt", {}).get("source_delivery", "UNPUBLISHED")
    intro = (
        "Generated from djconnect-platform-v1.json, maintenance " + d["decision_id"] + ".\n\n"
        "The original3October snapshot/audit/source pins and projections are immutable history in [history/20261003](history/20261003/README.md). "
        "Only this bounded delta is current here; inherited premerge statuses are not current blockers. "
        + (
            "Current admission is documentary only, using the existing Core writer; all new product subsets remain Planned/NOT_ISSUED. Closed implementation receipts are retained as evidence, not new admission.\n\n"
            if d.get("schema_version") == "djconnect-federated-planning-delta/7"
            else "Only the selected existing Core writer is admitted by implementation receipt; no automatic dispatch, second writer or native/installed/hardware acceptance.\n\n"
            if current
            else "No portfolio-wide refresh, writer reservation, product dispatch or runtime acceptance is claimed.\n\n"
        )
    )
    if artwork:
        intro += "Current bounded artwork correction: [owner6117357579](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6117357579). Existing Discovery capability only; source/Finalization gates remain separate, native/installed/live acceptance remains open. Presence source1150/Finalization1151 stays closed. Prior version2 is preserved in history/20261012.\n\n"
    if d.get("schema_version") in {
        "djconnect-federated-planning-delta/4",
        "djconnect-federated-planning-delta/5",
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11",
    }:
        r = d["narrative_receipt"]
        intro += f"Selected bounded Album→Track continuity: [{r['assignment_id']}]({r['selection_url']}); source {r['source_delivery']}, Stage4 PARTIAL, joint/native/installed/hardware acceptance open. Artwork1152/1153 is terminal at admitted0f37; prior version3 is preserved in history/20261012. No automatic consumer dispatch or new Core writer.\n\n"
    if d.get("schema_version") in {
        "djconnect-federated-planning-delta/5",
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11",
    }:
        f = d["forecast_receipt"]
        intro += f"Selected Session Forecast: [{f['assignment_id']}]({f['selection_url']}); existing Direction parent, source {f['source_delivery']}, current-only qualified artist imagery, native/visible/upcoming/joint acceptance open. Album1154/1155 terminal before this writer admission; previous version4 preserved in history/20261012. Early contract fixtures allow independently admitted consumer source integration; no automatic dispatch.\n\n"
    if d.get("schema_version") in {
        "djconnect-federated-planning-delta/6",
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11",
    }:
        a = d["ambient_receipt"]
        intro += f"Selected ambient convergence: [{a['assignment_id']}]({a['selection_url']}); source {a['source_delivery']}, qualified Session reuse and passive producer retirement; native/joint acceptance open. Forecast1156/1157 stays closed; version5 preserved in history/20261012. No new source/model/consumer dispatch.\n\n"
    if d.get("schema_version") in {
        "djconnect-federated-planning-delta/7",
        "djconnect-federated-planning-delta/8",
        "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11",
    }:
        r = d["documentary_receipt"]
        intro += f"Combined Session entry/history/native-surface documentary design: [{r['assignment_id']}]({r['selection_url']}); documentation {r['source_delivery']}. Documentary delivery does not itself admit product execution; Continuation is independent and rich passive rights are not inherited. Ambient1158/1159 remains terminal; version6 is preserved in history/20261012. No new product writer or native/APNs/installed/hardware PASS.\n\n"
    if d.get("schema_version") in {"djconnect-federated-planning-delta/8", "djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11"}:
        r = d["summary_receipt"]
        intro += f"Selected connected Core history summary: {r['assignment_id']}; source {r['source_delivery']}. Reuses HISTORY::CORE::SUMMARY, with Apple adoption Planned and native/installed/joint acceptance open. Predecessor version7 is preserved byte-for-byte.\n\n"
    if d.get("schema_version") in {"djconnect-federated-planning-delta/9", "djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11"}:
        r = d["dialogue_receipt"]
        intro += f"Selected one-pipeline Ask DJ + exact Moment Track Insight: [{r['assignment_id']}]({r['selection_url']}); source {r['source_delivery']}. Both screens use the same service with optional qualified context. Native Apple and joint acceptance remain Planned/open; no consumer writes or automatic dispatch. History summary1162/1163 stays closed; version8 is preserved in history/20261013. Owner-requested HA-dev/prod updates follow qualified delivery and installed readback.\n\n"
        observed = r.get("consumer_reconciliation")
        if observed:
            intro += f"Existing Apple Presence execution: {observed['observed_status']} ([owning readback]({observed['apple_checkpoint']})); native Mac/installed acceptance and protected Apple delivery remain open. This observation updates no historical planning node and grants no Core/consumer admission. Installed Presence advertisement is absent in the owner readback; completed Core policy remains closed. Dialogue adoption and intra-track visibility remain distinct open joint findings.\n\n"
    if d.get("schema_version") in {"djconnect-federated-planning-delta/10", "djconnect-federated-planning-delta/11"}:
        r = d["hybrid_receipt"]
        intro += f"Selected bounded Hybrid transport: [{r['assignment_id']}]({r['selection_url']}); source {r['source_delivery']}. Existing connectivity parent retained; protocol, journal/recovery and paired actions share current Core owners. Apple adoption and joint/native transitions remain Planned/open; no consumer writes, installation or automatic dispatch. Current-artist1168/1169 closed before admission; version9 and its whole snapshot are preserved byte-for-byte.\n\n"
    if d.get("schema_version") == "djconnect-federated-planning-delta/11":
        r = d["session_artwork_receipt"]
        intro += f"Selected subject-bound Session artwork: {r['assignment_id']}; source {r['source_delivery']}. Three bounded Core subsets; native Apple and joint acceptance remain Planned/open. Prior delivered v10 is preserved; no transport functional prerequisite or automatic consumer dispatch.\n\n"
    successor = d.get("session_artwork_receipt", {}).get("selected_successor")
    if successor and not d.get("speech_persona_receipt"):
        intro += f"Owner-selected queued successor: {successor['assignment_id']} ([selection](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-{successor['owner_selection']}), [autonomous-next](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-{successor['autonomous_next']})). Not admitted or implemented here; starts only after valid artwork closure and fresh sole-writer admission. Separate exact publication gates remain.\n\n"
    if d.get("speech_persona_receipt"):
        r = d["speech_persona_receipt"]
        intro += f"Selected and freshly admitted speech/Persona implementation: {r['assignment_id']}; source {r['source_delivery']}. Four bounded Core leaves reuse existing Voice/Speech/Audio Renderer architecture; Apple/native audible/joint acceptance remains Planned/open. Delivered artwork v11 and historical snapshots preserved; no new provider/model/cost route or consumer writer.\n\n"
    if d.get("passive_surface_receipt"):
        r = d["passive_surface_receipt"]
        intro += f"Selected passive Session projection: {r['assignment_id']}; source {r['source_delivery']}. Existing SURFACE::CORE::PROJECTION only; native rich adoption OPEN_APPLE, background SURFACE::APPLE::QUIET-TRANSPORT separately Planned, Watch NOT_QUALIFIED and joint OPEN. Original publication/source deadlines, explicit purpose grants and pure reads; no client writes, provider or automatic dispatch. Delivered v12 and all prior receipts preserved.\n\n"
    if d.get("settings_consolidation_receipt"):
        r = d["settings_consolidation_receipt"]
        state = ('protected source delivered contract3 (Core producer only)' if r['source_delivery'] == 'PROTECTED_MERGED'
                 else 'implemented local contract3 (runtime checkpoint3, unpublished until protected delivery)')
        intro += f"Selected shared Profile/Session settings consolidation: {r['assignment_id']}; six shared Persona/voice/gender/Mood/Presence/announcement_output, {state}, last explicit accepted choice becomes default, atomic active+default acceptance. Source {r['source_delivery']}; Core producer and migration work only; Apple/other consumers/joint separately open, no automatic dispatch or whole-family completion. Delivered v13 preserved.\n\n"
    if d.get("display_admission_receipt"):
        r = d["display_admission_receipt"]
        intro += f"Selected Core display-admission: {r['assignment_id']}; existing WEB::TRUST and WEB::DISPLAY only. TRUST anchor OPEN_JOINT_REVIEW, wire NOT_FROZEN, runtime {r['runtime']}; source UNPUBLISHED, native/TV/joint open. Independently reviewed B may be implemented/qualified in isolation while A stays unavailable; no runtime acceptance inferred. Original settings delivery and all prior receipts remain preserved; no consumer dispatch or deployment.\n\n"
    out = {}
    out["README.md"] = (
        "# Federated roadmap — versioned maintenance\n\n"
        + intro
        + f"[Owner decision]({d['decision_url']}); documentary design date {d['design_date']}.\n\n"
        + "Joint presence acceptance remains Planned; delivered Core policy remains closed. Mood, Persona and presence are independent. Corepolicy + Applecontrol + local/static VibeCast receipts form joint acceptance. Richer narrative is later, not a v1 gate.\n\n"
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
        + (
            "\nCore policy/ownercontract status follows the exact implementation receipt. Native/installed/hardware acceptance remains open.\n"
            if current
            else "\nPolicy values/budgets/default and exact presence route/schema remain unqualified design details. No runtime/native/browser/installed/hardware PASS.\n"
        )
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
        + (
            "Core → existing Apple87: exact Discovery feed/scoped image/TTL/error/source fixtures; visible attribution, cached pixels and lifecycle require separate native evidence. No Swift/receiver writer or new provider.\n\n"
            if artwork
            else ""
        )
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
    if "web_first_receipt" in d:
        from web_first_delta import add_views
        return add_views(out, p)
    return out
