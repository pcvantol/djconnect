"""Historical preservation and fail-closed versioned planning maintenance."""

import re
import copy
import hashlib
import unittest
from pathlib import Path
from validate_snapshot import load, validate
from render_snapshot import render

ROOT = Path(__file__).resolve().parent


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.p = load(ROOT / "djconnect-platform-v1.json")

    def test_preserved_history_and_current_references(self):
        d = self.p["planning_maintenance"]
        self.assertEqual(validate(self.p), [])
        self.assertEqual(
            hashlib.sha256((ROOT / d["frozen_snapshot"]).read_bytes()).hexdigest(),
            d["frozen_sha256"],
        )
        historical = load(ROOT / d["frozen_snapshot"])
        self.assertEqual(
            {k: v for k, v in self.p.items() if k != "planning_maintenance"}, historical
        )
        for r in d["document_references"]:
            self.assertEqual(
                hashlib.sha256((ROOT.parents[2] / r["path"]).read_bytes()).hexdigest(), r["sha256"]
            )
        for name, body in render(self.p).items():
            self.assertEqual((ROOT / name).read_text(), body)

    def test_queued_successor_does_not_claim_admission_or_implementation(self):
        d = self.p["planning_maintenance"]
        if d["schema_version"] != "djconnect-federated-planning-delta/11":
            self.skipTest("Version11 queue receipt")
        for key, value in (("admission", "ADMITTED"), ("implementation_in_this_slice", True),
                           ("owner_selection", 0), ("new_publication_gates_preserved", False)):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.p)
                bad["planning_maintenance"]["session_artwork_receipt"]["selected_successor"][key] = value
                self.assertTrue(validate(bad))

    def test_documentary_v7_preserves_v6_and_no_product_dispatch(self):
        import json

        d = self.p["planning_maintenance"]
        if d["schema_version"] == "djconnect-federated-planning-delta/11":
            d = json.loads((ROOT / d["session_artwork_receipt"]["previous_delta"]).read_text())
        if d["schema_version"] == "djconnect-federated-planning-delta/10":
            d = json.loads((ROOT / d["hybrid_receipt"]["previous_delta"]).read_text())
        if d["schema_version"] == "djconnect-federated-planning-delta/9":
            d = json.loads((ROOT / d["dialogue_receipt"]["previous_delta"]).read_text())
        if d["schema_version"] == "djconnect-federated-planning-delta/8":
            d = json.loads((ROOT / d["summary_receipt"]["previous_delta"]).read_text())
        receipt = d["documentary_receipt"]
        prior = (ROOT / receipt["previous_delta"]).read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(), receipt["previous_delta_sha256"])
        previous = json.loads(prior)
        old = copy.deepcopy(self.p)
        old["planning_maintenance"] = previous
        self.assertEqual(validate(old), [])
        for key in (
            "implementation_receipt",
            "correction_receipts",
            "narrative_receipt",
            "forecast_receipt",
            "ambient_receipt",
        ):
            self.assertEqual(d[key], previous[key])
        new = [n for n in d["nodes"] if n["id"] not in {x["id"] for x in previous["nodes"]}]
        self.assertEqual(len(new), 15)
        self.assertTrue(
            all((n["status"], n["assignment_status"]) == ("Planned", "NOT_ISSUED") for n in new)
        )

    def test_documentary_scope_and_unproved_publication_rejected(self):
        mutations = [
            lambda d: d["documentary_receipt"].update(product_implementation="Completed"),
            lambda d: d["documentary_receipt"].update(native="PASS"),
            lambda d: d["documentary_receipt"].update(c_url="wrong"),
            lambda d: d["documentary_receipt"].update(
                phase="SOURCE_PROTECTED_MERGED",
                source_delivery="PROTECTED_MERGED",
                protected_merge=False,
            ),
            lambda d: next(n for n in d["nodes"] if n["id"] == "SURFACE::APPLE::ADOPTION").update(
                status="Completed", assignment_status="CORE_DELIVERED"
            ),
        ]
        for mutate in mutations:
            p = copy.deepcopy(self.p)
            mutate(p["planning_maintenance"])
            self.assertTrue(validate(p))

    def test_neutral_navigation_has_no_unrelated_prerequisite(self):
        d = self.p["planning_maintenance"]
        forbidden = {
            "HISTORY::CORE::SUMMARY",
            "HISTORY::APPLE::SUMMARY",
            "CONTINUATION::CORE::POLICY",
            "CONTINUATION::APPLE::ALERT-TRANSPORT",
        }
        incoming = [
            e
            for e in d["edges"]
            if e["consumer"] in {"SURFACE::APPLE::NAVIGATION", "ENTRY::APPLE::NAVIGATION"}
        ]
        self.assertFalse(any(e["producer"] in forbidden for e in incoming))
        for n in d["nodes"]:
            if n["id"].startswith("CONTINUATION::"):
                self.assertEqual(n["parent_reference"], "PROJ::ROADMAP::CONTINUATION")

    def test_generated_local_links_resolve(self):
        for name, body in render(self.p).items():
            for link in re.findall(r"\]\(([^)]+)\)", body):
                if not link.startswith(("https://", "http://", "#")):
                    self.assertTrue((ROOT / name).parent.joinpath(link).exists(), (name, link))

    def test_only_selected_core_nodes_in_progress_and_joint_stays_planned(self):
        d = self.p["planning_maintenance"]
        self.assertFalse(d["execution_authority"])
        self.assertFalse(d["automatic_dispatch"])
        selected = {"SLICE::CORE::DJ-PRESENCE-CONTRACT", "SLICE::CORE::DJ-PRESENCE-POLICY"}
        for n in d["nodes"]:
            if n["id"] in selected:
                delivered = d["implementation_receipt"]["source_delivery"] == "PROTECTED_MERGED"
                self.assertEqual(
                    (n["status"], n["assignment_status"]),
                    ("Completed", "CORE_DELIVERED")
                    if delivered
                    else ("In progress", "IN_PROGRESS"),
                )
            elif n["id"] == "CORRECTION::CORE::DISCOVERY-ARTWORK":
                receipt = d["correction_receipts"][0]
                expected = (
                    ("Completed", "CORE_DELIVERED")
                    if receipt["source_delivery"] == "PROTECTED_MERGED"
                    else ("In progress", "IN_PROGRESS")
                )
                self.assertEqual((n["status"], n["assignment_status"]), expected)
            elif n["id"].startswith("MEDIA::CORE::"):
                delivered = d["session_artwork_receipt"]["source_delivery"] == "PROTECTED_MERGED"
                self.assertEqual((n["status"], n["assignment_status"]),
                                 ("Completed", "CORE_DELIVERED") if delivered else ("In progress", "IN_PROGRESS"))
            elif n["id"].startswith("TRANSPORT::CORE::"):
                delivered = d["hybrid_receipt"]["source_delivery"] == "PROTECTED_MERGED"
                self.assertEqual((n["status"], n["assignment_status"]),
                                 ("Completed", "CORE_DELIVERED") if delivered else ("In progress", "IN_PROGRESS"))
            elif n["id"] in {"CONVERSATION::CORE::SHARED-DIALOGUE", "INSIGHT::CORE::MOMENT-DRILLDOWN"}:
                delivered = d["dialogue_receipt"]["source_delivery"] == "PROTECTED_MERGED"
                self.assertEqual((n["status"], n["assignment_status"]), ("Completed", "CORE_DELIVERED") if delivered else ("In progress", "IN_PROGRESS"))
            elif n["id"] == "HISTORY::CORE::SUMMARY":
                delivered = d["summary_receipt"]["source_delivery"] == "PROTECTED_MERGED"
                self.assertEqual(
                    (n["status"], n["assignment_status"]),
                    ("Completed", "CORE_DELIVERED")
                    if delivered
                    else ("In progress", "IN_PROGRESS"),
                )
            elif n["id"] == "RELATION::CORE::ALBUM-CONTINUITY":
                delivered = d["narrative_receipt"]["source_delivery"] == "PROTECTED_MERGED"
                self.assertEqual(
                    (n["status"], n["assignment_status"]),
                    ("Completed", "CORE_DELIVERED")
                    if delivered
                    else ("In progress", "IN_PROGRESS"),
                )
            elif n["id"] in {
                "FORECAST::CORE::CONTRACT",
                "FORECAST::CORE::PROJECTION",
                "FORECAST::VIBECAST::COMPAT",
            }:
                delivered = d["forecast_receipt"]["source_delivery"] == "PROTECTED_MERGED"
                self.assertEqual(
                    (n["status"], n["assignment_status"]),
                    ("Completed", "CORE_DELIVERED")
                    if delivered
                    else ("In progress", "IN_PROGRESS"),
                )
            elif n["id"] == "AMBIENT::CORE::CONVERGENCE":
                delivered = d["ambient_receipt"]["source_delivery"] == "PROTECTED_MERGED"
                self.assertEqual(
                    (n["status"], n["assignment_status"]),
                    ("Completed", "CORE_DELIVERED")
                    if delivered
                    else ("In progress", "IN_PROGRESS"),
                )
            elif "ACTIVE-SESSION-MOOD" not in n["id"]:
                self.assertEqual((n["status"], n["assignment_status"]), ("Planned", "NOT_ISSUED"))
        receipt = d["implementation_receipt"]
        prior = (ROOT / receipt["previous_delta"]).read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(), receipt["previous_delta_sha256"])
        import json

        old = copy.deepcopy(self.p)
        old["planning_maintenance"] = json.loads(prior)
        self.assertEqual(validate(old), [])
        self.assertTrue(
            all(
                n["status"] == "Planned"
                for n in old["planning_maintenance"]["nodes"]
                if "ACTIVE-SESSION-MOOD" not in n["id"]
            )
        )

    def test_consumer_dispatch_and_unproven_delivery_rejected(self):
        for mutate in [
            lambda d: d["implementation_receipt"].update(selection_url="wrong"),
            lambda d: d["implementation_receipt"].update(native="PASS"),
            lambda d: d["implementation_receipt"].update(source_delivery="MERGED"),
            lambda d: d["implementation_receipt"].update(joint_product_acceptance="COMPLETE"),
            lambda d: next(n for n in d["nodes"] if n["lane"] == "DJC-APPLE").update(
                assignment_status="IN_PROGRESS"
            ),
        ]:
            p = copy.deepcopy(self.p)
            mutate(p["planning_maintenance"])
            self.assertTrue(validate(p))

    def test_delivery_requires_exact_receipts_and_preserves_joint_gate(self):
        p = copy.deepcopy(self.p)
        if p["planning_maintenance"]["schema_version"] == "djconnect-federated-planning-delta/11":
            import json
            path = p["planning_maintenance"]["session_artwork_receipt"]["previous_delta"]
            p["planning_maintenance"] = json.loads((ROOT / path).read_text())
        d = p["planning_maintenance"]
        r = d["implementation_receipt"]
        # The negative fixture must stay missing evidence after real delivery.
        for key in (
            "source_main_sha",
            "source_pr",
            "source_review",
            "required_checks",
            "protected_merge",
            "archive_sha256",
            "formal_evidence_sha256",
        ):
            r.pop(key, None)
        r.update(
            phase="SOURCE_PROTECTED_MERGED",
            source_delivery="PROTECTED_MERGED",
            protected_merge=False,
        )
        for n in d["nodes"]:
            if n["id"] in {"SLICE::CORE::DJ-PRESENCE-CONTRACT", "SLICE::CORE::DJ-PRESENCE-POLICY"}:
                n.update(status="Completed", assignment_status="CORE_DELIVERED")
        self.assertTrue(validate(p))
        r.update(
            source_main_sha="a" * 40,
            source_pr="https://github.com/pcvantol/djconnect/pull/9999",
            source_review="PASS",
            required_checks="PASS",
            protected_merge=True,
            archive_sha256="b" * 64,
            formal_evidence_sha256="c" * 64,
        )
        self.assertEqual(validate(p), [])  # Structural fixture, never remote acceptance.
        joint = next(n for n in d["nodes"] if n["id"] == "QUAL::PRODUCT::DJ-PRESENCE-V1")
        joint["status"] = "Completed"
        self.assertTrue(validate(p))

    def test_duplicate_orphan_cycle_and_false_authority_rejected(self):
        for change, expected in [
            (lambda d: d["nodes"].append(copy.deepcopy(d["nodes"][0])), "duplicate"),
            (lambda d: d["edges"][0].update(producer="missing"), "orphan"),
            (
                lambda d: d["edges"].append(
                    {
                        **d["edges"][0],
                        "id": "CYCLE",
                        "producer": "SLICE::CORE::DJ-PRESENCE-POLICY",
                        "consumer": "SLICE::CORE::DJ-PRESENCE-CONTRACT",
                        "hard_precedence": False,
                    }
                ),
                "cycle",
            ),
            (lambda d: d.update(execution_authority=True), "dispatch"),
            (lambda d: d["nodes"][0].update(status="Completed"), "Planned"),
        ]:
            with self.subTest(expected=expected):
                p = copy.deepcopy(self.p)
                change(p["planning_maintenance"])
                self.assertTrue(any(expected in e for e in validate(p)), validate(p))

    def test_frozen_mutation_rejected(self):
        self.p["created_at"] = "2026-10-11"
        self.assertTrue(any("frozen content changed" in e for e in validate(self.p)))

    def test_artwork_correction_history_and_authority_are_bounded(self):
        d = self.p["planning_maintenance"]
        c = d["correction_receipts"][0]
        prior = (ROOT / c["previous_delta"]).read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(), c["previous_delta_sha256"])
        import json

        old = copy.deepcopy(self.p)
        old["planning_maintenance"] = json.loads(prior)
        self.assertEqual(validate(old), [])
        self.assertEqual(
            old["planning_maintenance"]["implementation_receipt"], d["implementation_receipt"]
        )
        for mutate in (
            lambda x: x["correction_receipts"][0].update(selection_url="wrong"),
            lambda x: x["correction_receipts"][0].update(native="PASS"),
            lambda x: x["correction_receipts"][0].update(
                phase="SOURCE_PROTECTED_MERGED",
                source_delivery="PROTECTED_MERGED",
                source_main_sha="",
            ),
            lambda x: x["nodes"][-1].update(status="In progress", assignment_status="IN_PROGRESS"),
        ):
            changed = copy.deepcopy(self.p)
            mutate(changed["planning_maintenance"])
            self.assertTrue(validate(changed))

    def test_narrative_closed_admission_and_no_full_stage_promotion(self):
        if "narrative_receipt" not in self.p["planning_maintenance"]:
            self.skipTest("Historical delta has no album relation")
        for key, value in (
            ("stage4_status", "Completed"),
            ("native", "PASS"),
            ("base_sha", "0" * 40),
            ("selection_authority", "AUTOMATIC"),
            (
                "source_delivery",
                "UNPUBLISHED"
                if self.p["planning_maintenance"]["narrative_receipt"]["source_delivery"]
                == "PROTECTED_MERGED"
                else "PROTECTED_MERGED",
            ),
        ):
            p = copy.deepcopy(self.p)
            p["planning_maintenance"]["narrative_receipt"][key] = value
            self.assertTrue(validate(p), key)
        p = copy.deepcopy(self.p)
        p["planning_maintenance"]["nodes"].append(
            copy.deepcopy(p["planning_maintenance"]["nodes"][-1])
        )
        self.assertTrue(validate(p))

    def test_forecast_parent_history_and_claim_gates(self):
        d = self.p["planning_maintenance"]
        if "forecast_receipt" not in d:
            self.skipTest("Historical snapshot has no selected Forecast")
        f = d["forecast_receipt"]
        self.assertEqual(
            hashlib.sha256((ROOT / f["previous_delta"]).read_bytes()).hexdigest(),
            f["previous_delta_sha256"],
        )
        self.assertEqual(f["parent_node"], "PROJ::ROADMAP::DIRECTION")
        for key, value in (
            ("native", "PASS"),
            ("joint_product_acceptance", "COMPLETE"),
            ("upcoming_media", "QUALIFIED"),
            ("parent_node", "NEW-PLANNER"),
        ):
            p = copy.deepcopy(self.p)
            p["planning_maintenance"]["forecast_receipt"][key] = value
            self.assertTrue(validate(p), key)
        joined = next(n for n in d["nodes"] if n["id"] == "FORECAST::PRODUCT::JOINT")
        self.assertEqual(len(joined["prerequisite_groups"][0]["edge_ids"]), 3)
        self.assertEqual(joined["prerequisite_groups"][0]["mode"], "AND")


if __name__ == "__main__":
    unittest.main()


class AmbientMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.plan = load(ROOT / "djconnect-platform-v1.json")

    def test_ambient_previous_delta_and_scope(self):
        d = self.plan["planning_maintenance"]
        a = d["ambient_receipt"]
        prior = (ROOT / a["previous_delta"]).read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(), a["previous_delta_sha256"])
        import json

        old = copy.deepcopy(self.plan)
        old["planning_maintenance"] = json.loads(prior)
        self.assertEqual(validate(old), [])
        self.assertEqual(old["planning_maintenance"]["forecast_receipt"], d["forecast_receipt"])
        nodes = {n["id"] for n in d["nodes"] if n["id"].startswith("AMBIENT::")}
        self.assertEqual(
            nodes, {"AMBIENT::CORE::CONVERGENCE", "AMBIENT::APPLE::JOIN", "AMBIENT::PRODUCT::JOINT"}
        )
        self.assertFalse(
            any(
                e["producer"].startswith("FORECAST::") and e["consumer"] in nodes
                for e in d["edges"]
            )
        )

    def test_unqualified_ambient_delivery_and_scope_rejected(self):
        for key, value in (
            (
                "source_delivery",
                "UNPUBLISHED"
                if self.plan["planning_maintenance"]["ambient_receipt"]["source_delivery"]
                == "PROTECTED_MERGED"
                else "PROTECTED_MERGED",
            ),
            ("parent_node", "PROJ::ROADMAP::DIRECTION"),
            ("disposition", "NEW_PROVIDER"),
            ("native", "PASS"),
            ("joint_product_acceptance", "PASS"),
            ("selection_url", "wrong"),
        ):
            p = copy.deepcopy(self.plan)
            p["planning_maintenance"]["ambient_receipt"][key] = value
            self.assertTrue(validate(p), (key, value))

class DialogueMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.p = load(ROOT / "djconnect-platform-v1.json")
        if self.p["planning_maintenance"]["schema_version"] == "djconnect-federated-planning-delta/11":
            import json
            path = self.p["planning_maintenance"]["session_artwork_receipt"]["previous_delta"]
            self.p["planning_maintenance"] = json.loads((ROOT / path).read_text())
        if self.p["planning_maintenance"]["schema_version"] == "djconnect-federated-planning-delta/10":
            import json
            path = self.p["planning_maintenance"]["hybrid_receipt"]["previous_delta"]
            self.p["planning_maintenance"] = json.loads((ROOT / path).read_text())

    def test_dialogue_v9_preserves_v8_and_has_only_one_core_admission(self):
        import json
        d = self.p["planning_maintenance"]
        r = d["dialogue_receipt"]
        prior = (ROOT / r["previous_delta"]).read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(), r["previous_delta_sha256"])
        previous = json.loads(prior)
        for key in ("implementation_receipt", "correction_receipts", "narrative_receipt", "forecast_receipt", "ambient_receipt", "documentary_receipt", "summary_receipt"):
            self.assertEqual(d[key], previous[key])
        for node in previous["nodes"]:
            self.assertEqual(next(n for n in d["nodes"] if n["id"] == node["id"]), node)
        self.assertEqual(d["edges"][:len(previous["edges"])], previous["edges"])
        self.assertEqual(len(d["nodes"]) - len(previous["nodes"]), 5)
        self.assertEqual(len(d["edges"]) - len(previous["edges"]), 7)
        self.assertFalse(r["consumer_writes"])
        self.assertFalse(r["automatic_dispatch"])

    def test_dialogue_unproved_delivery_and_consumer_admission_fail_closed(self):
        mutations = [
            lambda d: d["dialogue_receipt"].update(native="PASS"),
            lambda d: d["dialogue_receipt"].update(consumer_writes=True),
            lambda d: d["dialogue_receipt"].update(added_requirement="unapproved"),
            lambda d: d["dialogue_receipt"].update(base_sha="0" * 40),
            lambda d: d["dialogue_receipt"].update(phase="SOURCE_PROTECTED_MERGED", source_delivery="PROTECTED_MERGED", source_review="UNPROVED"),
            lambda d: next(n for n in d["nodes"] if n["id"] == "CONVERSATION::APPLE::SHARED-ADOPTION").update(status="Completed", assignment_status="CORE_DELIVERED"),
            lambda d: d["nodes"].append(copy.deepcopy(d["nodes"][-1])),
            lambda d: d["edges"][-1].update(consumer=d["edges"][-1]["producer"]),
            lambda d: d["edges"][-1].update(consumer="unknown-node"),
        ]
        for mutate in mutations:
            p = copy.deepcopy(self.p)
            mutate(p["planning_maintenance"])
            self.assertTrue(validate(p))

    def test_consumer_readback_projects_actual_work_without_admitting_a_writer(self):
        r = self.p["planning_maintenance"]["dialogue_receipt"]["consumer_reconciliation"]
        self.assertEqual(r["observed_status"], "In progress")
        self.assertFalse(r["consumer_writes"])
        self.assertEqual(validate(self.p), [])
        self.assertIn("Existing Apple Presence execution: In progress", render(self.p)["README.md"])
        for key, value in (("native_mac", "PASS"), ("consumer_writes", True), ("scope", "ADMIT_NEW_WRITER")):
            p = copy.deepcopy(self.p)
            p["planning_maintenance"]["dialogue_receipt"]["consumer_reconciliation"][key] = value
            self.assertTrue(validate(p))


class HybridMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.p = load(ROOT / "djconnect-platform-v1.json")
        if self.p["planning_maintenance"]["schema_version"] == "djconnect-federated-planning-delta/11":
            import json
            path = self.p["planning_maintenance"]["session_artwork_receipt"]["previous_delta"]
            self.p["planning_maintenance"] = json.loads((ROOT / path).read_text())

    def test_hybrid_preserves_complete_previous_snapshot_and_delta(self):
        import json

        d = self.p["planning_maintenance"]
        r = d["hybrid_receipt"]
        prior = (ROOT / r["previous_delta"]).read_bytes()
        snapshot = (ROOT / r["previous_snapshot"]).read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(), r["previous_delta_sha256"])
        self.assertEqual(hashlib.sha256(snapshot).hexdigest(), r["previous_snapshot_sha256"])
        previous = json.loads(prior)
        self.assertEqual(json.loads(snapshot)["planning_maintenance"], previous)
        for key in previous.keys() - {"schema_version", "nodes", "edges", "document_references"}:
            self.assertEqual(d[key], previous[key], key)
        self.assertEqual(d["nodes"][: len(previous["nodes"])], previous["nodes"])
        self.assertEqual(d["edges"][: len(previous["edges"])], previous["edges"])
        self.assertEqual(len(d["nodes"]) - len(previous["nodes"]), 5)
        self.assertEqual(len(d["edges"]) - len(previous["edges"]), 5)
        old = copy.deepcopy(self.p)
        old["planning_maintenance"] = previous
        self.assertEqual(validate(old), [])

    def test_hybrid_missing_admission_or_fabricated_acceptance_is_rejected(self):
        # Genuine protected delivery is valid after Finalization. Flip the live
        # flag so this remains a negative phase/delivery consistency check.
        current = self.p["planning_maintenance"]["hybrid_receipt"]["source_delivery"]
        wrong_delivery = "UNPUBLISHED" if current == "PROTECTED_MERGED" else "PROTECTED_MERGED"
        for key, value in [
            ("assignment_id", "wrong"),
            ("ack", 1),
            ("base_sha", "0" * 40),
            ("native", "PASS"),
            ("installed", "PASS"),
            ("consumer_writes", True),
            ("family_acceptance", "Completed"),
            ("previous_delta_sha256", ""),
            ("phase", "COMPLETED"),
            ("source_delivery", wrong_delivery),
        ]:
            p = copy.deepcopy(self.p)
            p["planning_maintenance"]["hybrid_receipt"][key] = value
            self.assertTrue(validate(p), (key, value))

    def test_hybrid_duplicate_or_unadmitted_consumer_nodes_are_rejected(self):
        p = copy.deepcopy(self.p)
        d = p["planning_maintenance"]
        d["nodes"].append(copy.deepcopy(d["nodes"][-1]))
        self.assertTrue(validate(p))
        p = copy.deepcopy(self.p)
        d = p["planning_maintenance"]
        next(n for n in d["nodes"] if n["id"] == "TRANSPORT::APPLE::HYBRID").update(
            status="In progress", assignment_status="IN_PROGRESS"
        )
        self.assertTrue(validate(p))

    def test_hybrid_cycle_and_unrelated_prerequisite_are_rejected(self):
        p = copy.deepcopy(self.p)
        d = p["planning_maintenance"]
        edge = next(e for e in d["edges"] if e["id"] == "HYBRID-1")
        edge["producer"] = "TRANSPORT::JOINT::HYBRID"
        self.assertTrue(validate(p))
        p = copy.deepcopy(self.p)
        d = p["planning_maintenance"]
        next(n for n in d["nodes"] if n["id"] == "TRANSPORT::CORE::CONTRACT")[
            "parent_reference"
        ] = "PROJ::ROADMAP::INTERACTIVE"
        self.assertTrue(validate(p))

    def test_hybrid_unproved_protected_delivery_is_rejected(self):
        p = copy.deepcopy(self.p)
        p["planning_maintenance"]["hybrid_receipt"].update(
            phase="SOURCE_PROTECTED_MERGED",
            source_delivery="PROTECTED_MERGED",
            protected_merge=False,
        )
        self.assertTrue(validate(p))


class SessionArtworkMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.p = load(ROOT / "djconnect-platform-v1.json")

    def test_live_version_preserves_delivered_predecessor_and_is_valid(self):
        self.assertEqual(self.p['planning_maintenance']['schema_version'], 'djconnect-federated-planning-delta/11')
        self.assertEqual(validate(self.p), [])

    def test_missing_admission_source_or_fabricated_consumer_acceptance_rejected(self):
        for key,value in [('ack',1),('material_commit','0'*40),('native','PASS'),
                          ('joint_acceptance','PASS'),('automatic_dispatch',True),('installed','PASS'),('hardware','PASS'),
                          ('previous_delta_sha256','0'*64),('source_delivery','PROTECTED_MERGED')]:
            p=copy.deepcopy(self.p)
            p['planning_maintenance']['session_artwork_receipt'][key]=value
            self.assertTrue(validate(p),(key,value))

    def test_duplicate_and_unadmitted_consumer_rejected(self):
        p=copy.deepcopy(self.p)
        p['planning_maintenance']['nodes'].append(copy.deepcopy(p['planning_maintenance']['nodes'][-1]))
        self.assertTrue(validate(p))
        p=copy.deepcopy(self.p)
        next(n for n in p['planning_maintenance']['nodes'] if n['id']=='MEDIA::APPLE::SESSION-ARTWORK')['status']='Completed'
        self.assertTrue(validate(p))

    def test_cycle_or_transport_prerequisite_rejected(self):
        for producer in ('MEDIA::JOINT::SESSION-ARTWORK','TRANSPORT::CORE::PAIRED-ACTIONS'):
            p=copy.deepcopy(self.p)
            next(e for e in p['planning_maintenance']['edges'] if e['id']=='SESSION-MEDIA-1')['producer']=producer
            self.assertTrue(validate(p))

    def test_existing_producer_state_cannot_be_rewritten(self):
        p=copy.deepcopy(self.p)
        next(n for n in p['planning_maintenance']['nodes'] if n['id']=='TRANSPORT::CORE::CONTRACT')['status']='Planned'
        self.assertTrue(validate(p))
