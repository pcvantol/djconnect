"""Local structural tests. Synthetic evidence below is TEST-ONLY, never a receipt."""

import copy
import json
import tempfile
import unittest
import subprocess
import sys
import io
import runpy
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path
from validate_snapshot import load, validate
from render_snapshot import render
from check_freshness import compare

ROOT = Path(__file__).resolve().parent


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.p = load(ROOT / "djconnect-platform-v1.json")

    def errors(self):
        return "\n".join(validate(self.p))

    def n(self, nid):
        return next(x for x in self.p["nodes"] if x["id"] == nid)

    def qualified(self, nid):
        # Synthetic unit fixture, not evidence about the real project.
        n = self.n(nid)
        n.update(
            completion_claim="COMPLETE",
            acceptance_criteria=["test-only criterion"],
            completion_requirements=["test-only exact acceptance"],
        )
        eid = "TEST-ONLY-" + nid
        self.p["evidence"].append(
            dict(
                id=eid,
                kind="TEST_ONLY_FIXTURE",
                scope_node_id=nid,
                subject_sha="0" * 40,
                url="https://example.invalid/test-only",
                observed_date="2000-01-01",
                passed=True,
                acceptance_qualified=True,
                criteria_covered=["test-only criterion"],
            )
        )
        n["evidence_ids"] = [eid]

    def extra_edge(self, eid, a, b, mode="AND"):
        e = copy.deepcopy(self.p["edges"][0])
        e.pop("same_increment_as_consumer", None)
        e.update(id=eid, producer=a, consumer=b, logical_mode=mode)
        self.p["edges"].append(e)
        self.n(b)["prerequisite_groups"].append({"mode": mode, "edge_ids": [eid]})

    def test_real_partial_structure_valid(self):
        self.assertEqual(validate(self.p), [])

    def test_e2e_original_scope_is_not_a_new_execution_frontier(self):
        self.assertEqual(
            self.n("PROJ::ROADMAP::P1-E2E")["selection"],
            "ORIGINAL_SELECTED_SCOPE_COMPLETED; OPTIONAL_EXPANSIONS_DEFERRED",
        )
        self.assertNotIn(
            "Automated Session Intelligence E2E Verification:",
            render(self.p)["diagrams/ready-frontier.mmd"],
        )

    def test_complete_delivery_words_need_all_gates(self):
        self.p["conclusions"]["PLANNING_DELIVERY"] = "COMPLETE / MERGED_RECONCILED / FINALIZED"
        self.assertIn("complete planning claim lacks all delivery gates", self.errors())

    def test_planning_cannot_claim_product_or_execution_ready(self):
        self.p["conclusions"]["PRODUCT_DELIVERY"] = "COMPLETE"
        self.p["conclusions"]["EXECUTION_READY"] = "READY"
        self.assertIn("planning cannot claim product delivery", self.errors())
        self.assertIn("planning cannot grant product pickup", self.errors())

    def test_partial_sources_cannot_be_declared_all_read(self):
        self.p["completeness"]["all_sources_read"] = True
        self.p["sources"][0]["read_complete"] = False
        self.assertIn("source-read claim has partial sources", self.errors())

    def test_unpinned_reference_scan_cannot_contain_pinned_source(self):
        self.p["source_capture"]["reference_scan"]["unmapped_paths"].append(
            "pcvantol/djconnect::PRODUCT_ROADMAP.md"
        )
        self.assertIn("reference scan has invalid, duplicate or already pinned paths", self.errors())

    def test_component_reference_scan_cannot_contain_pinned_source(self):
        self.p["source_capture"]["reference_scan"]["unmapped_paths"].append(
            "pcvantol/djconnect-pi::README.md"
        )
        self.assertIn("reference scan has invalid, duplicate or already pinned paths", self.errors())

    def test_component_reference_scan_rejects_bare_pinned_alias(self):
        scan = self.p["source_capture"]["reference_scan"]
        scan["unmapped_paths"].append("docs/ARCHITECTURE.md")
        scan["triage"]["docs/ARCHITECTURE.md"] = "Ambiguous across component repositories"
        self.assertIn("reference scan has invalid, duplicate or already pinned paths", self.errors())

    def test_finding_evidence_must_exist(self):
        finding = next(f for f in self.p["findings"] if f["id"] == "PI-DOCUMENT-MIRROR-DRIFT")
        finding["evidence_ids"] = ["MISSING"]
        self.assertIn("unknown finding evidence", self.errors())

    def test_finding_source_must_exist(self):
        finding = next(f for f in self.p["findings"] if f["id"] == "CURRENT-WIP")
        finding["source_ids"] = ["MISSING"]
        self.assertIn("unknown finding source", self.errors())

    def test_unpinned_reference_scan_requires_path_dispositions(self):
        scan = self.p["source_capture"]["reference_scan"]
        scan["triage"].pop(scan["unmapped_paths"][0])
        self.assertIn("reference scan needs one disposition for every unpinned path", self.errors())

    def test_tree_census_cannot_overstate_included_markdown(self):
        row = self.p["source_capture"]["tree_census_readback"]["lanes"]["DJC-CORE"]
        row["included_markdown"] += 1
        row["not_individually_included_markdown"] -= 1
        self.assertIn("DJC-CORE: included Markdown count differs from source matrix", self.errors())

    def test_tree_census_requires_one_row_per_lane(self):
        self.p["source_capture"]["tree_census_readback"]["lanes"].pop("DJC-PI")
        self.assertIn("tree census must cover exactly one row per lane", self.errors())

    def test_historical_path_cannot_overlap_fully_read_source(self):
        group = self.p["source_capture"]["historical_path_dispositions"]["groups"][0]
        source = next(s for s in self.p["sources"] if s["repository"] == "pcvantol/djconnect")
        group["entries"][0]["path"] = source["path"]
        self.assertIn("duplicate or already represented historical path", self.errors())

    def test_historical_release_copy_cannot_include_current_version(self):
        group = next(
            g for g in self.p["source_capture"]["historical_path_dispositions"]["groups"]
            if g["category"] == "OLDER_WINDOWS_VERSIONED_RELEASE_COPY"
        )
        group["entries"][0]["path"] = "docs/release-notes/en/v3.3.0.md"
        self.assertIn("invalid historical path/blob or version boundary", self.errors())

    def test_historical_counts_must_match_exact_entries(self):
        row = self.p["source_capture"]["tree_census_readback"]["lanes"]["DJC-APPLE"]
        row["historically_classified_markdown"] += 1
        self.assertIn("historical/unclassified census mismatch", self.errors())

    def test_retained_ep_group_cannot_swallow_release_policy(self):
        group = next(
            g for g in self.p["source_capture"]["historical_path_dispositions"]["groups"]
            if g["category"] == "RETAINED_EMBEDDED_EP_DOCUMENTATION"
        )
        group["entries"][0]["path"] = "docs/release/DEPLOYMENT_WORKFLOW_POLICY.md"
        self.assertIn("invalid historical path/blob or version boundary", self.errors())

    def test_discovery_history_group_cannot_swallow_current_capability_model(self):
        group = next(
            g for g in self.p["source_capture"]["historical_path_dispositions"]["groups"]
            if g["category"] == "EPIC_2_DISCOVERY_HISTORY"
        )
        group["entries"][0]["path"] = "DJCONNECT_CAPABILITY_MODEL.md"
        self.assertIn("invalid historical path/blob or version boundary", self.errors())

    def test_audit_cannot_close_without_receipt(self):
        self.p["audit_obligations"][0]["status"] = "CLOSED"
        self.assertIn("closed audit lacks closure evidence", self.errors())

    def test_independent_review_gate_requires_closed_audit(self):
        self.p["completeness"]["independent_review"] = True
        self.assertIn("supporting audit obligations remain open", self.errors())

    def test_writer_free_claim_needs_exact_receipt(self):
        lane = self.p["lanes"][1]
        lane.update(writer_state="FREE_VERIFIED", writer_free_verified=True)
        self.assertIn("writer-free claim lacks exact receipt", self.errors())

    def test_free_writer_label_cannot_bypass_verification_flag(self):
        self.p["lanes"][1]["writer_state"] = "FREE_VERIFIED"
        self.assertIn("free writer label lacks verification", self.errors())

    def test_full_delivery_must_fail_for_open_audit_and_protection(self):
        e = "\n".join(validate(self.p, True))
        self.assertIn("completion gate open", e)
        self.assertNotIn("owning register not delivered", e)
        self.assertIn("audit obligation open", e)

    def test_five_item_horizon_cannot_lose_a_record(self):
        self.p["execution_horizon"].pop()
        self.assertIn("execution horizon must contain five", self.errors())

    def test_horizon_condition_must_be_in_dependency_graph(self):
        self.n("PROJ::EVOLUTION::APPLE-PUBLIC")["prerequisite_groups"] = []
        self.assertIn("horizon condition absent from dependency graph", self.errors())

    def test_horizon_cannot_duplicate_an_owner_node(self):
        self.p["execution_horizon"][1]["node"] = self.p["execution_horizon"][0]["node"]
        self.assertIn("horizon node missing or duplicated", self.errors())

    def test_same_increment_contract_cannot_be_misread_as_start_gate(self):
        edge = next(e for e in self.p["edges"] if e.get("same_increment_as_consumer"))
        edge["prerequisite_stage"] = "start"
        self.assertIn("same-increment contract must be a hard completion AND gate", self.errors())

    def test_playback_stage2_needs_atomic_continue_adoption(self):
        edge = next(e for e in self.p["edges"] if e["id"] == "REQ-ATOMIC-ADOPTION-PLAYBACK-STAGE2")
        self.p["edges"].remove(edge)
        self.n("PROJ::ROADMAP::PLAYBACK-STAGE2")["prerequisite_groups"] = [
            group for group in self.n("PROJ::ROADMAP::PLAYBACK-STAGE2")["prerequisite_groups"]
            if edge["id"] not in group["edge_ids"]
        ]
        self.assertIn("atomic siblings need identical completion gates", self.errors())

    def test_stage2_siblings_cannot_complete_separately(self):
        self.n("PROJ::ROADMAP::PLAYBACK-STAGE2")["completion_claim"] = "COMPLETE"
        self.assertIn("atomic siblings cannot complete separately", self.errors())

    def test_desktop_waits_for_public_apple_release(self):
        edge = next(e for e in self.p["edges"] if e["id"] == "ROADMAP-DESKTOP-AFTER-APPLE-PUBLIC")
        self.assertEqual(edge["producer"], "PROJ::EVOLUTION::APPLE-PUBLIC")
        self.assertTrue(edge["hard_precedence"])

    def test_community_public_requires_readiness_and_authorization(self):
        required = {
            e["producer"]
            for e in self.p["edges"]
            if e["consumer"] == "PROJ::ROADMAP::P7-PUBLIC" and e["hard_precedence"]
        }
        self.assertTrue(
            {
                "PROJ::ROADMAP::P5-PRODUCTIZATION",
                "PROJ::ROADMAP::P6-COMMUNITY-READINESS",
                "AUTH::CORE::COMMUNITY-PUBLIC",
            }
            <= required
        )

    def test_website_install_copy_needs_published_asset(self):
        for platform in ("APPLE", "WINDOWS"):
            edge = next(e for e in self.p["edges"] if e["id"] == f"DEP-{platform}-WEBSITE")
            self.assertEqual(edge["producer"], f"QUAL::DIST-APPLE::{platform}-PUBLISHED-ASSET")

    def test_internal_apple_consumer_uses_secure_relay_not_optional_handoff(self):
        edge = next(e for e in self.p["edges"] if e["id"] == "HORIZON-APPLE-INTERNAL")
        self.assertEqual(edge["producer"], "QUAL::APPLE::SECURE-RELAY-INSTALL")

    def test_hacs_visibility_observations_gate_completion_not_start(self):
        self.n("HACS-3.3.0-001")["assignment_status"] = "READY"
        self.assertNotIn("missing hard predecessor evidence HORIZON-HACS-VIS", self.errors())

    def test_vibecast_pi_receipt_gates_parent_completion_not_start(self):
        self.n("PROJ::ROADMAP::P2-VIBECAST")["assignment_status"] = "READY"
        self.assertNotIn(
            "missing hard predecessor evidence DEP-PI-REFERENCE-MILESTONE", self.errors()
        )

    def test_selected_reference_scope_is_valid_selection_for_future_admission(self):
        self.n("SLICE::APPLE::OWNER-HANDOFF")["assignment_status"] = "READY"
        self.assertNotIn("READY without selected scope", self.errors())

    def test_register_must_belong_to_owning_repository(self):
        self.p["lanes"][1]["owning_register"] = "https://github.com/pcvantol/djconnect/issues/1101"
        self.assertIn("register belongs to another repository", self.errors())

    def test_source_url_must_match_exact_commit(self):
        self.p["sources"][0]["url"] = (
            "https://github.com/pcvantol/djconnect/blob/main/ROADMAP_INDEX.md"
        )
        self.assertIn("source URL does not bind pinned commit", self.errors())

    def test_backend_alternatives_do_not_form_and_gate(self):
        group = self.n("SLICE::CORE::BACKEND-SESSION")["prerequisite_groups"][0]
        self.assertEqual(group["mode"], "OR")
        self.assertEqual(group["selection_policy"], "PER_INSTALL_USER_BACKEND")
        self.assertIsNone(group["selected_edge_id"])
        self.assertEqual(validate(self.p), [])

    def test_backend_ready_cannot_use_unselected_or(self):
        n = self.n("SLICE::CORE::BACKEND-SESSION")
        n["assignment_status"] = "READY"
        n["selection"] = "SELECTED"
        self.assertIn("READY with unresolved OR choice", self.errors())

    def test_root_type(self):
        self.assertEqual(validate([]), ["root must be an object"])

    def test_malformed_top_lists(self):
        self.p["nodes"] = 42
        self.assertIn("expected list", self.errors())

    def test_duplicate_lane_id(self):
        self.p["lanes"].append(copy.deepcopy(self.p["lanes"][0]))
        self.assertIn("duplicate id", self.errors())

    def test_duplicate_repository_lane(self):
        self.p["lanes"][1]["repository"] = self.p["lanes"][0]["repository"]
        self.assertIn("exactly one lane", self.errors())

    def test_path_traversal_lane_rejected(self):
        self.p["lanes"][0]["id"] = "../../other"
        self.assertIn("unsafe/invalid lane", self.errors())

    def test_bad_baseline_pin(self):
        self.p["lanes"][0]["baseline_sha"] = "main"
        self.assertIn("invalid baseline pin", self.errors())

    def test_bad_source_blob(self):
        self.p["sources"][0]["blob_sha"] = "latest"
        self.assertIn("source blob pin", self.errors())

    def test_bad_source_commit(self):
        self.p["sources"][0]["commit_sha"] = "main"
        self.assertIn("source commit pin", self.errors())

    def test_source_missing_disposition(self):
        del self.p["sources"][0]["disposition"]
        self.assertIn("missing disposition", self.errors())

    def test_orphan_source(self):
        self.p["sources"][0]["mapped_node_ids"] = []
        self.assertIn("orphan source", self.errors())

    def test_inconsistent_source_mapping(self):
        self.p["sources"][0]["mapped_node_ids"].append("does-not-exist")
        self.assertIn("inconsistent source-to-node", self.errors())

    def test_duplicate_node(self):
        self.p["nodes"].append(copy.deepcopy(self.p["nodes"][0]))
        self.assertIn("duplicate id", self.errors())

    def test_wrong_owner(self):
        self.p["nodes"][0]["repository"] = "pcvantol/djconnect-api"
        self.assertIn("invalid owning", self.errors())

    def test_unknown_node_source(self):
        self.p["nodes"][0]["source_ids"].append("NONEXISTENT")
        self.assertIn("missing/inconsistent source", self.errors())

    def test_wrong_canonical_authority(self):
        self.p["nodes"][0]["canonical_authority"] = "NONEXISTENT"
        self.assertIn("single canonical status authority", self.errors())

    def test_duplicate_canonical_id(self):
        self.n("CMB-02")["canonical_id"] = "CMB-01"
        self.assertIn("duplicate canonical", self.errors())

    def test_alias_cannot_be_second_node(self):
        self.p["aliases"][0]["alias"] = "CMB-01"
        self.assertIn("duplicate/invalid alias", self.errors())

    def test_missing_alias_target(self):
        self.p["aliases"][0]["target"] = "NO"
        self.assertIn("missing target", self.errors())

    def test_orphan_edge(self):
        self.p["edges"][0]["producer"] = "NO"
        self.assertIn("orphan edge", self.errors())

    def test_dependency_missing_phase(self):
        self.p["edges"][0]["phase"] = "whenever"
        self.assertIn("invalid dependency phase", self.errors())

    def test_resource_conflict_not_functional(self):
        self.p["edges"][0]["kind"] = "resource_conflict"
        self.assertIn("non-functional order marked hard", self.errors())

    def test_strategy_order_not_functional(self):
        self.p["edges"][0]["kind"] = "strategy_order"
        self.assertIn("non-functional order marked hard", self.errors())

    def test_missing_hard_group(self):
        self.n("PROJ::ROADMAP::PLAYBACK-STAGE2")["prerequisite_groups"] = []
        self.assertIn("hard dependencies missing", self.errors())

    def test_missing_predecessor_evidence(self):
        self.p["edges"][0]["evidence_satisfied"] = True
        self.assertIn("unsupported predecessor evidence", self.errors())

    def test_historical_unsigned_asset_does_not_qualify_current_website_release(self):
        edge = next(e for e in self.p["edges"] if e["id"] == "DEP-APPLE-WEBSITE")
        edge["evidence_ids"] = ["APPLE_IOS_330_ASSET"]
        edge["evidence_satisfied"] = True
        self.assertIn("unsupported predecessor evidence", self.errors())

    def test_hard_cycle(self):
        self.extra_edge(
            "TEST-CYCLE", "PROJ::ROADMAP::PLAYBACK-STAGE2", "PROJ::GATE::PLAYBACK-IDENTITY"
        )
        self.assertIn("cycle in selected hard", self.errors())

    def test_ready_without_selection_or_admission(self):
        self.p["nodes"][0]["assignment_status"] = "READY"
        self.assertIn("READY without selected", self.errors())
        self.assertIn("READY lacks exact", self.errors())

    def test_flags_without_receipts_are_not_ready(self):
        n = self.p["nodes"][0]
        n.update(
            assignment_status="READY",
            selection="SELECTED",
            authority_verified=True,
            writer_free_verified=True,
            resources_verified=True,
            decisions_resolved=True,
        )
        self.assertIn("READY lacks exact authority", self.errors())

    def test_doc_complete_is_not_verified_complete(self):
        self.n("PROJ::E2E::16")["completion_claim"] = "COMPLETE"
        self.assertIn("unproved COMPLETE", self.errors())

    def test_complete_requires_all_criteria(self):
        self.qualified("CMB-01")
        self.n("CMB-01")["acceptance_criteria"].append("uncovered")
        self.assertIn("unproved COMPLETE", self.errors())

    def test_complete_exact_synthetic_fixture(self):
        self.qualified("CMB-01")
        self.assertEqual(validate(self.p), [])

    def test_parent_cannot_hide_incomplete_required_child(self):
        self.qualified("CMB-01")
        self.p["rollups"] = [{"parent": "CMB-01", "children": ["CMB-02"], "rule": "ALL_REQUIRED"}]
        self.assertIn("parent COMPLETE with incomplete", self.errors())

    def test_rollup_duplicate_child(self):
        self.p["rollups"] = [
            {"parent": "CMB-01", "children": ["CMB-02", "CMB-02"], "rule": "ALL_REQUIRED"}
        ]
        self.assertIn("double-counts", self.errors())

    def test_two_running_writers_rejected(self):
        self.n("CMB-01")["assignment_status"] = "RUNNING"
        self.n("CMB-02")["assignment_status"] = "RUNNING"
        self.assertIn("overlapping active", self.errors())

    def test_handoff_wrong_owner(self):
        self.p["handoffs"][0]["consumer_lane"] = "NO"
        self.assertIn("invalid handoff ownership", self.errors())

    def test_handoff_cannot_grant_execution(self):
        self.p["handoffs"][0]["execution_authorized"] = True
        self.assertIn("cannot authorize execution", self.errors())

    def test_checkpoint_cannot_grant_execution(self):
        self.p["execution_authority"] = True
        self.assertIn("must not grant execution", self.errors())

    def test_checkpoint_cannot_dispatch(self):
        self.p["automatic_dispatch"] = True
        self.assertIn("must not dispatch", self.errors())

    def test_unresolved_or_valid_partial_not_ready(self):
        self.extra_edge("TEST-OR-A", "CMB-01", "CMB-02", "OR")
        self.assertEqual(validate(self.p), [])
        self.n("CMB-02")["assignment_status"] = "READY"
        self.assertIn("READY with unresolved OR", self.errors())

    def test_unselected_or_alternative_does_not_become_and(self):
        self.extra_edge("TEST-A", "CMB-01", "CMB-02", "OR")
        e = copy.deepcopy(self.p["edges"][-1])
        e.update(id="TEST-B", producer="CMB-03")
        self.p["edges"].append(e)
        g = self.n("CMB-02")["prerequisite_groups"][-1]
        g.update(edge_ids=["TEST-A", "TEST-B"], selected_edge_id="TEST-A")
        self.extra_edge("TEST-BACK", "CMB-02", "CMB-03")
        self.assertEqual(validate(self.p), [])  # selecting B would create a cycle
        g["selected_edge_id"] = "TEST-B"
        self.assertIn("cycle in selected hard", self.errors())

    def test_invalid_or_selection(self):
        self.extra_edge("TEST-OR", "CMB-01", "CMB-02", "OR")
        self.n("CMB-02")["prerequisite_groups"][-1]["selected_edge_id"] = "NO"
        self.assertIn("not an alternative", self.errors())

    def test_render_is_deterministic(self):
        self.assertEqual(render(self.p), render(copy.deepcopy(self.p)))

    def test_all_views_derived_from_json(self):
        for name, body in render(self.p).items():
            self.assertEqual((ROOT / name).read_text(encoding="utf-8"), body, name)

    def test_or_diagram_shows_choice_not_two_and_arrows(self):
        diagram = render(self.p)["diagrams/hard-dependencies.mmd"]
        self.assertIn("OR: one selected option", diagram)
        self.assertIn("alternative", diagram)

    def test_frontier_shows_node_level_blockers(self):
        diagram = render(self.p)["diagrams/ready-frontier.mmd"]
        self.assertIn("Public Apple distribution: BLOCKED", diagram)
        self.assertIn("Apple paired-owner VibeCast handoff: BLOCKED", diagram)

    def test_human_status_changes_when_data_changes(self):
        self.p["findings"][0]["description"] = "TEST-ONLY changed finding"
        self.assertIn("TEST-ONLY changed finding", render(self.p)["README.md"])

    def test_invalid_snapshot_not_rendered(self):
        self.p["execution_authority"] = True
        with self.assertRaises(ValueError):
            render(self.p)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.json"
            f.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):
                load(f)

    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.json"
            f.write_text('{"a":NaN}')
            with self.assertRaises(ValueError):
                load(f)

    def test_freshness_missing_is_unknown(self):
        r = compare(self.p, {"heads": {}})
        self.assertEqual(r["result"], "INCOMPLETE_OR_CHANGED")
        self.assertTrue(all("UNKNOWN" in x["status"] for x in r["repositories"]))

    def test_moving_remote_does_not_change_offline_validation(self):
        before = json.dumps(self.p, sort_keys=True)
        r = compare(
            self.p,
            {"heads": {"pcvantol/djconnect": {"sha": "f" * 40, "observed_date": "2026-10-03"}}},
        )
        self.assertEqual(r["repositories"][0]["status"], "CHANGED_NEEDS_READONLY_DELTA_AUDIT")
        self.assertEqual(validate(self.p), [])
        self.assertEqual(before, json.dumps(self.p, sort_keys=True))

    def test_freshness_accepts_recorded_core_delta(self):
        r = compare(
            self.p,
            {
                "heads": {
                    "pcvantol/djconnect": {
                        "sha": self.p["observed_core_delta"]["closing_read"],
                        "observed_date": "2026-10-03",
                    }
                }
            },
        )
        self.assertEqual(r["repositories"][0]["status"], "MATCH_RECORDED_HEAD")
        self.assertEqual(r["result"], "INCOMPLETE_OR_CHANGED")  # other eleven not read again

    def test_freshness_bad_pin_rejected(self):
        with self.assertRaises(ValueError):
            compare(
                self.p,
                {"heads": {"pcvantol/djconnect": {"sha": "main", "observed_date": "2026-10-03"}}},
            )


class CLITests(unittest.TestCase):
    def run_cli(self, script, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / script), *map(str, args)],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def test_validator_cli_check_views(self):
        r = self.run_cli(
            "validate_snapshot.py", ROOT / "djconnect-platform-v1.json", "--check-rendered"
        )
        self.assertEqual(r.returncode, 0)
        self.assertFalse(json.loads(r.stdout)["complete_delivery"])

    def test_validator_cli_strict_is_incomplete(self):
        r = self.run_cli(
            "validate_snapshot.py", ROOT / "djconnect-platform-v1.json", "--require-complete"
        )
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["result"], "FAIL")

    def test_validator_cli_missing_file(self):
        r = self.run_cli("validate_snapshot.py", ROOT / "does-not-exist.json")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["result"], "FAIL")

    def test_view_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text((ROOT / "djconnect-platform-v1.json").read_text())
            r = self.run_cli("validate_snapshot.py", p, "--check-rendered")
            self.assertEqual(r.returncode, 1)
            self.assertIn("generated view differs", r.stdout)

    def test_freshness_cli_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "observations.json"
            p.write_text('{"heads":{}}')
            r = self.run_cli("check_freshness.py", ROOT / "djconnect-platform-v1.json", p)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(json.loads(r.stdout)["result"], "INCOMPLETE_OR_CHANGED")

    def test_freshness_cli_bad_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "observations.json"
            p.write_text("{}")
            r = self.run_cli("check_freshness.py", ROOT / "djconnect-platform-v1.json", p)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(json.loads(r.stdout)["result"], "INVALID_INPUT")

    def test_renderer_cli_in_isolated_output(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text((ROOT / "djconnect-platform-v1.json").read_text())
            r = self.run_cli("render_snapshot.py", p)
            self.assertEqual(r.returncode, 0)
            self.assertTrue((Path(d) / "lanes/DJC-CORE.md").is_file())


class InProcessEntryTests(unittest.TestCase):
    def test_validator_entrypoint(self):
        from validate_snapshot import main

        with (
            patch.object(
                sys,
                "argv",
                ["validate", str(ROOT / "djconnect-platform-v1.json"), "--check-rendered"],
            ),
            redirect_stdout(io.StringIO()) as buf,
        ):
            result = main()
        self.assertEqual(result, 0)
        self.assertFalse(json.loads(buf.getvalue())["complete_delivery"])

    def test_validator_entrypoint_io_failure(self):
        from validate_snapshot import main

        with (
            patch.object(sys, "argv", ["validate", str(ROOT / "does-not-exist")]),
            redirect_stdout(io.StringIO()) as buf,
        ):
            result = main()
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(buf.getvalue())["result"], "FAIL")

    def test_renderer_entrypoint(self):
        from render_snapshot import main

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "p.json"
            p.write_text((ROOT / "djconnect-platform-v1.json").read_text())
            with patch.object(sys, "argv", ["render", str(p)]), redirect_stdout(io.StringIO()):
                result = main()
            self.assertEqual(result, 0)
            self.assertTrue((Path(d) / "diagrams/ready-frontier.mmd").is_file())

    def test_freshness_entrypoint_unknown_and_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "o.json"
            for body, expected in [('{"heads":{}}', 1), ("{}", 2)]:
                p.write_text(body)
                with (
                    patch.object(
                        sys, "argv", ["freshness", str(ROOT / "djconnect-platform-v1.json"), str(p)]
                    ),
                    redirect_stdout(io.StringIO()),
                ):
                    with self.assertRaises(SystemExit) as caught:
                        runpy.run_module("check_freshness", run_name="__main__")
                self.assertEqual(caught.exception.code, expected)

    def test_freshness_schema_failure_in_process(self):
        with self.assertRaises(ValueError):
            compare(load(ROOT / "djconnect-platform-v1.json"), {})


if __name__ == "__main__":
    unittest.main()
