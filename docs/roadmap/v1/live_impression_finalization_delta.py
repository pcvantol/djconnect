"""Reconcile merged software only; preserve the exact premerge planning freeze."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

PREFIX = "LIVE-IMPRESSION::"
PATH = "history/20261120/live-impression-freeze-maintenance-v17.json"



def _check_receipt_provenance(receipt, raw, check):
    """Bind the preserved freeze and exact merged source identities."""
    check(receipt.get("predecessor_path") == PATH
          and receipt.get("predecessor_sha256") == hashlib.sha256(raw).hexdigest(), "freeze preservation")
    check(receipt.get("assignment_id") == "DJC-LIVE-IMPRESSION-V1-20261108"
          and receipt.get("source_delivery") == "PROTECTED_MERGED", "bounded source delivery")
    check(receipt.get("core_merge") == "912e1efbd6e9475521779d04f98fd805f0b1f385"
          and receipt.get("core_qualified_head") == "f1b45dbf5363e87986ab5b8bb2354e5682a1995c"
          and receipt.get("core_tree") == "7a7565d985edd97b2427d70b851033f58605faa1"
          and receipt.get("apple_merge") == "8668da1fca60596d99e19c58d9d7c88390c8d21e"
          and receipt.get("apple_qualified_head") == "528ce0be27b61485aefd034c961e5d3f1d98239f", "exact merged provenance")


def _check_source_qualification(receipt, check):
    """Require independent source qualification with strict boolean flags."""
    check(receipt.get("source_tree_equal") is True and receipt.get("apple_tree_equal") is True
          and receipt.get("qualified_product_count") == 318 and receipt.get("product_unchanged") is True
          and receipt.get("core_main_validation") == "PASS"
          and receipt.get("apple_main_validation") == "PASS"
          and receipt.get("apple_durable_publication") == "PASS", "independent source qualification")


def _check_acceptance_boundary(receipt, check):
    """Keep source delivery separate from model, native and installed acceptance."""
    check(receipt.get("live_model") == "NOT_RUN" and receipt.get("native") == "SOURCE_SOFTWARE_ONLY_PHYSICAL_OPEN"
          and receipt.get("installed") == "NOT_RUN" and receipt.get("shared_tv") == "NOT_RUN"
          and receipt.get("overall_acceptance") == "OPEN" and receipt.get("automatic_dispatch") is False,
          "no acceptance or installation promotion")


def _check_readback_binding(receipt, evidence_raw, evidence, check):
    """Bind the readback bytes to the qualified Core merge and main run."""
    check(hashlib.sha256(evidence_raw).hexdigest() == receipt.get("source_readback_sha256")
          and evidence.get("merge_sha") == receipt.get("core_merge")
          and evidence.get("tree_sha") == receipt.get("core_tree")
          and evidence.get("main_workflow_run") == receipt.get("core_main_workflow_run")
          and evidence.get("main_workflow_result") == "PASS", "actual readback binding")


def _check_core_publication(receipt, evidence, check):
    """Verify original Core artifact inventory and durable publication evidence."""
    check(evidence.get("artifact_sha256") == receipt.get("internal_artifact_sha256")
          and evidence.get("durable_qualification_sha256") == receipt.get("durable_evidence_sha256")
          and evidence.get("qualified_product_count") == 318
          and evidence.get("archive_product_count") == 318
          and evidence.get("unexpected_archive_products") == []
          and evidence.get("archive_product_hash_mismatches") == []
          and evidence.get("durable_validator_findings") == [], "published artifact integrity")
    durable = evidence.get("durable_qualification", {})
    check(durable.get("commit_sha") == receipt.get("core_merge")
          and durable.get("qualification", {}).get("outcome") == "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED",
          "exact durable source evidence")


def _check_apple_publication(receipt, evidence, check):
    """Verify the separately owned Apple main and durable publication receipt."""
    apple = evidence.get("apple_source_publication", {})
    check(apple.get("main_sha") == receipt.get("apple_merge")
          and apple.get("ci") == receipt.get("apple_main_workflow_run")
          and apple.get("formal") == receipt.get("apple_publication_workflow_run")
          and apple.get("formal_decision") == "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED"
          and apple.get("canonical_integrity") == "PASS"
          and apple.get("durable_sha256") == receipt.get("apple_durable_evidence_sha256")
          and len(apple.get("required_checks", {})) == 12
          and set(apple.get("required_checks", {}).values()) == {"PASS"}, "exact Apple source evidence")


def _check_publications(receipt, check):
    """Load only the original published source readback; missing proof stays rejected."""
    readback = Path(__file__).parents[3] / receipt.get("source_readback_path", "MISSING")
    if readback.is_file():
        evidence_raw = readback.read_bytes()
        evidence = json.loads(evidence_raw)
        _check_readback_binding(receipt, evidence_raw, evidence, check)
        _check_core_publication(receipt, evidence, check)
        _check_apple_publication(receipt, evidence, check)
    else:
        check(False, "actual readback missing")


def _check_source_leaves(d, check):
    """Close only the three source leaves while joint acceptance remains planned."""
    nodes = [n for n in d["nodes"] if n["id"].startswith(PREFIX)]
    check(all(n["status"] == ("Planned" if n["id"].endswith("ACCEPTANCE") else "Completed") for n in nodes),
          "source leaves only")
    check(all(n.get("source_delivery") == "SOURCE_DELIVERED" for n in nodes if not n["id"].endswith("ACCEPTANCE")),
          "explicit source-only scope")


def _restore_predecessor(d, frozen, check):
    """Reconstruct maintenance17 without hiding unrelated planning changes."""
    restored = deepcopy(d)
    restored["schema_version"] = "djconnect-federated-planning-delta/17"
    restored.pop("live_impression_finalization_receipt", None)
    originals = {n["id"]: n for n in frozen["nodes"]}
    for node in restored["nodes"]:
        if node["id"].startswith(PREFIX) and not node["id"].endswith("ACCEPTANCE"):
            node["status"] = originals[node["id"]]["status"]
            node.pop("source_delivery", None)
    check({k: v for k, v in restored.items() if k != "document_references"}
          == {k: v for k, v in frozen.items() if k != "document_references"}, "unrelated records unchanged")
    return restored


def validate(plan, previous_validator):
    d = plan["planning_maintenance"]
    errors = []

    def check(condition, message):
        if not condition:
            errors.append("maintenance: live impression finalization " + message)

    raw = (Path(__file__).parent / PATH).read_bytes()
    frozen = json.loads(raw)
    receipt = d.get("live_impression_finalization_receipt", {})
    _check_receipt_provenance(receipt, raw, check)
    _check_source_qualification(receipt, check)
    _check_acceptance_boundary(receipt, check)
    _check_publications(receipt, check)
    _check_source_leaves(d, check)
    restored = _restore_predecessor(d, frozen, check)
    prior = deepcopy(plan)
    prior["planning_maintenance"] = restored
    errors.extend(previous_validator(prior))
    return errors
