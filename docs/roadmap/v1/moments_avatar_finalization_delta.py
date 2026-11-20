"""Reconcile only proven Moments source delivery; preserve the complete source freeze."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

PREFIX = "ASK-DJ-MOMENTS::"
PATH = "history/20261120/moments-avatar-freeze-maintenance-v19.json"
READBACK = "docs/roadmap/v1/history/20261120/moments-avatar-source-publication-readback.json"
DOCS = {
    "docs/history/prompts/2026-11-20-ask-dj-moments-finalization.md",
    "docs/technical/ASK_DJ_MOMENTS_SOURCE_FINALIZATION_20261120.md",
}
CORE_HEAD = "373e324e736b884e181f95dc2274bbb7ea15baaa"
CORE_MERGE = "948dbb8f7575df76a39e31335953fa53024b0831"
CORE_TREE = "7f5b032c6e54b4e9a2d2b912c35059a757365ab3"
APPLE_HEAD = "9b95eb553b300ef85697e747fa75d1c735263d25"
APPLE_MERGE = "83e2f03822deac1c52cc1dbedd8623d4a0e09b06"
APPLE_TREE = "439b950ed45c8f398782b5feb81de77c98a8e127"
CORE_ARCHIVE_SHA = "4f5cca7eb115edd92d5ffd40e943a8f56df0e6b7e559d043d747e8cf1fd19b16"
CORE_DURABLE_SHA = "0f80ddfc1185e7fd9f5c17ea2778e09c71946e6abc03b2ea7618aacf0bd4a51e"
APPLE_DURABLE_SHA = "65133af677b0e503b01731f0a15437138e02b8fe4c364f5a62224b02b8025484"

REQUIRED_CHECKS = frozenset(
    {
        "post_merge_build_validation",
        "post_merge_ci",
        "post_merge_coverage",
        "post_merge_governance",
        "post_merge_lint",
        "post_merge_static_analysis",
        "post_merge_tests",
        "required_checks",
        "software_assurance",
        "trusted_delivery",
        "verification",
        "workflow_integrity",
    }
)


def _canonical_checks(value):
    return (
        type(value) is dict
        and set(value) == REQUIRED_CHECKS
        and all(result == "PASS" for result in value.values())
    )


def _provenance(receipt, raw, check):
    check(
        receipt.get("predecessor_path") == PATH
        and receipt.get("predecessor_sha256") == hashlib.sha256(raw).hexdigest(),
        "immutable source freeze",
    )
    check(
        receipt.get("assignment_id") == "ASK-DJ-MOMENTS-AVATARCARD-V1"
        and receipt.get("source_delivery") == "PROTECTED_MERGED",
        "selected source scope",
    )
    check(
        receipt.get("core_qualified_head") == CORE_HEAD
        and receipt.get("core_merge") == CORE_MERGE
        and receipt.get("core_tree") == CORE_TREE
        and receipt.get("apple_qualified_head") == APPLE_HEAD
        and receipt.get("apple_merge") == APPLE_MERGE
        and receipt.get("apple_tree") == APPLE_TREE,
        "exact merged provenance",
    )
    check(
        receipt.get("source_tree_equal") is True
        and receipt.get("apple_tree_equal") is True
        and receipt.get("product_unchanged") is True
        and type(receipt.get("qualified_product_count")) is int
        and receipt.get("qualified_product_count") == 321,
        "software identity",
    )


def _acceptance(receipt, check):
    check(
        receipt.get("internal_artifact_sha256") == CORE_ARCHIVE_SHA
        and receipt.get("durable_evidence_sha256") == CORE_DURABLE_SHA
        and receipt.get("apple_durable_evidence_sha256") == APPLE_DURABLE_SHA,
        "exact published source digests",
    )
    check(
        receipt.get("overall_acceptance") == "OPEN"
        and receipt.get("installed") == "NOT_RUN"
        and receipt.get("live_model") == "NOT_RUN"
        and receipt.get("deployment") == "NOT_RUN"
        and receipt.get("native") == "SOURCE_SOFTWARE_ONLY_PHYSICAL_OPEN"
        and receipt.get("automatic_dispatch") is False,
        "no operational or joint promotion",
    )
    check(
        receipt.get("tde_assessment") == "FAIL"
        and receipt.get("tde_qualification") == "FAILED"
        and receipt.get("tde_maintainability_risk") == "OPEN_NEW_AND_INHERITED",
        "honest observe-only debt",
    )


def _core_publication(receipt, evidence, check):
    check(
        evidence.get("merge_sha") == CORE_MERGE
        and evidence.get("qualified_head") == CORE_HEAD
        and evidence.get("tree_sha") == CORE_TREE
        and evidence.get("tree_equal_to_qualified_head") is True
        and evidence.get("main_workflow_result") == "PASS",
        "actual Core main readback",
    )
    check(
        evidence.get("artifact_sha256") == receipt.get("internal_artifact_sha256")
        and evidence.get("durable_qualification_sha256") == receipt.get("durable_evidence_sha256")
        and evidence.get("archive_product_count") == 321
        and evidence.get("qualified_product_count") == 321
        and evidence.get("archive_product_hash_mismatches") == []
        and evidence.get("unexpected_archive_products") == []
        and evidence.get("durable_validator_findings") == [],
        "Core publication integrity",
    )
    durable = evidence.get("durable_qualification", {})
    check(
        hashlib.sha256((json.dumps(durable, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        == CORE_DURABLE_SHA,
        "embedded original Core durable bytes",
    )
    check(
        durable.get("commit_sha") == CORE_MERGE
        and durable.get("qualification", {}).get("outcome")
        == "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED",
        "exact durable Core outcome",
    )
    check(
        _canonical_checks(durable.get("qualification", {}).get("required_checks")),
        "Core canonical proof checks",
    )


def _apple_publication(receipt, evidence, check):
    apple = evidence.get("apple_source_publication", {})
    check(
        apple.get("main_sha") == APPLE_MERGE
        and apple.get("qualified_head") == APPLE_HEAD
        and apple.get("tree_sha") == APPLE_TREE
        and apple.get("tree_equal_to_qualified_head") is True
        and apple.get("main_validation") == "PASS"
        and apple.get("formal_decision") == "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED"
        and apple.get("canonical_integrity") == "PASS"
        and apple.get("durable_sha256") == receipt.get("apple_durable_evidence_sha256"),
        "actual Apple main publication",
    )
    durable = apple.get("durable_qualification", {})
    check(
        hashlib.sha256((json.dumps(durable, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        == APPLE_DURABLE_SHA
        and durable.get("commit_sha") == APPLE_MERGE,
        "embedded original Apple durable bytes",
    )
    checks = apple.get("required_checks", {})
    check(
        _canonical_checks(checks)
        and checks == durable.get("qualification", {}).get("required_checks"),
        "Apple canonical proof checks",
    )


def _readback(d, receipt, check):
    path = Path(__file__).parents[3] / READBACK
    if not path.is_file():
        check(False, "source readback missing")
        return
    raw = path.read_bytes()
    check(
        receipt.get("source_readback_path") == READBACK
        and hashlib.sha256(raw).hexdigest() == receipt.get("source_readback_sha256"),
        "source readback binding",
    )
    evidence = json.loads(raw)
    _core_publication(receipt, evidence, check)
    _apple_publication(receipt, evidence, check)
    refs = [r for r in d["document_references"] if r["path"] in DOCS]
    check(
        len(refs) == 2
        and {r["path"] for r in refs} == DOCS
        and all(
            hashlib.sha256((Path(__file__).parents[3] / r["path"]).read_bytes()).hexdigest()
            == r["sha256"]
            for r in refs
        ),
        "exact Finalization records",
    )


def _restore(d, frozen, check):
    restored = deepcopy(d)
    restored["schema_version"] = "djconnect-federated-planning-delta/19"
    restored.pop("moments_avatar_finalization_receipt", None)
    originals = {n["id"]: n for n in frozen["nodes"]}
    for n in restored["nodes"]:
        if n["id"].startswith(PREFIX) and not n["id"].endswith("ACCEPTANCE"):
            check(
                n["status"] == "Completed" and n.get("source_delivery") == "SOURCE_DELIVERED",
                "source leaves only",
            )
            n["status"] = originals[n["id"]]["status"]
            n.pop("source_delivery", None)
    restored["document_references"] = [
        r for r in restored["document_references"] if r["path"] not in DOCS
    ]
    check(restored == frozen, "unrelated records and joint Planned unchanged")
    return restored


def validate(plan, previous_validator):
    d = plan["planning_maintenance"]
    errors = []

    def check(ok, message):
        if not ok:
            errors.append("maintenance: Moments Finalization " + message)

    raw = (Path(__file__).parent / PATH).read_bytes()
    receipt = d.get("moments_avatar_finalization_receipt", {})
    _provenance(receipt, raw, check)
    _acceptance(receipt, check)
    _readback(d, receipt, check)
    prior = deepcopy(plan)
    prior["planning_maintenance"] = _restore(d, json.loads(raw), check)
    errors.extend(previous_validator(prior))
    return errors
