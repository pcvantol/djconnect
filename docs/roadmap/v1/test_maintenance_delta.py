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

    def test_generated_local_links_resolve(self):
        for name, body in render(self.p).items():
            for link in re.findall(r"\]\(([^)]+)\)", body):
                if not link.startswith(("https://", "http://", "#")):
                    self.assertTrue((ROOT / name).parent.joinpath(link).exists(), (name, link))

    def test_only_selected_core_nodes_in_progress_and_joint_stays_planned(self):
        d=self.p["planning_maintenance"]
        self.assertFalse(d["execution_authority"])
        self.assertFalse(d["automatic_dispatch"])
        selected={"SLICE::CORE::DJ-PRESENCE-CONTRACT","SLICE::CORE::DJ-PRESENCE-POLICY"}
        for n in d["nodes"]:
            if n["id"] in selected:
                delivered=d["implementation_receipt"]["source_delivery"]=="PROTECTED_MERGED"
                self.assertEqual((n["status"],n["assignment_status"]), ("Completed","CORE_DELIVERED") if delivered else ("In progress","IN_PROGRESS"))
            elif "ACTIVE-SESSION-MOOD" not in n["id"]:
                self.assertEqual((n["status"],n["assignment_status"]),("Planned","NOT_ISSUED"))
        receipt=d["implementation_receipt"]
        prior=(ROOT/receipt["previous_delta"]).read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(),receipt["previous_delta_sha256"])
        import json
        old=copy.deepcopy(self.p)
        old["planning_maintenance"]=json.loads(prior)
        self.assertEqual(validate(old),[])
        self.assertTrue(all(n["status"]=="Planned" for n in old["planning_maintenance"]["nodes"]
                            if "ACTIVE-SESSION-MOOD" not in n["id"]))

    def test_consumer_dispatch_and_unproven_delivery_rejected(self):
        for mutate in [
            lambda d:d["implementation_receipt"].update(selection_url="wrong"),
            lambda d:d["implementation_receipt"].update(native="PASS"),
            lambda d:d["implementation_receipt"].update(source_delivery="MERGED"),
            lambda d:d["implementation_receipt"].update(joint_product_acceptance="COMPLETE"),
            lambda d:next(n for n in d["nodes"] if n["lane"]=="DJC-APPLE").update(assignment_status="IN_PROGRESS"),
        ]:
            p=copy.deepcopy(self.p)
            mutate(p["planning_maintenance"])
            self.assertTrue(validate(p))

    def test_delivery_requires_exact_receipts_and_preserves_joint_gate(self):
        p=copy.deepcopy(self.p)
        d=p["planning_maintenance"]
        r=d["implementation_receipt"]
        r.update(phase="SOURCE_PROTECTED_MERGED",source_delivery="PROTECTED_MERGED")
        for n in d["nodes"]:
            if n["id"] in {"SLICE::CORE::DJ-PRESENCE-CONTRACT","SLICE::CORE::DJ-PRESENCE-POLICY"}:
                n.update(status="Completed",assignment_status="CORE_DELIVERED")
        self.assertTrue(validate(p))
        r.update(source_main_sha="a"*40,source_pr="https://github.com/pcvantol/djconnect/pull/9999",
                 source_review="PASS",required_checks="PASS",protected_merge=True,
                 archive_sha256="b"*64,formal_evidence_sha256="c"*64)
        self.assertEqual(validate(p),[])  # Structural fixture, never remote acceptance.
        joint=next(n for n in d["nodes"] if n["id"]=="QUAL::PRODUCT::DJ-PRESENCE-V1")
        joint["status"]="Completed"
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
                        "producer": d["nodes"][0]["id"],
                        "consumer": d["nodes"][-1]["id"],
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


if __name__ == "__main__":
    unittest.main()
