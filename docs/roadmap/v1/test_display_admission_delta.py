"""Selected review is real WIP, not a trust/crypto/runtime completion receipt."""

from copy import deepcopy
from pathlib import Path
import unittest
from validate_snapshot import load, validate
from render_snapshot import render

ROOT = Path(__file__).resolve().parent


class DisplayAdmissionMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.plan = load(ROOT / "djconnect-platform-v1.json")

    def test_exact_selected_existing_core_nodes_and_preserved_predecessor(self):
        self.assertEqual(validate(self.plan), [])
        self.assertEqual(
            self.plan["planning_maintenance"]["schema_version"],
            "djconnect-federated-planning-delta/16",
        )
        self.assertIn("wire NOT_FROZEN, runtime B_SOFTWARE_QUALIFIED_NOT_INSTALLED", render(self.plan)["README.md"])

    def test_generated_views_follow_receipt_publication_without_promoting_acceptance(self):
        views = render(self.plan)
        for name, body in views.items():
            if "Selected Core display-admission:" in body:
                with self.subTest(view=name):
                    self.assertIn("source DRAFT_PR_PUBLISHED_NOT_MERGED", body)
                    self.assertNotIn("source UNPUBLISHED", body)
                    self.assertIn("native/TV/joint open", body)
                    self.assertIn("does not close A", body)
        p = deepcopy(self.plan)
        receipt = p["planning_maintenance"]["display_admission_receipt"]
        receipt.update(phase="CONTRACT_REVIEW", runtime="NOT_IMPLEMENTED",
                       source_delivery="UNPUBLISHED")
        self.assertEqual(validate(p), [])
        self.assertIn("source UNPUBLISHED", render(p)["README.md"])

    def test_b_implementation_cannot_promote_a_or_replace_its_exact_design_review(self):
        for key, value in [("reviewed_sha", "0" * 40), ("scope", "A_AND_B"),
                           ("runtime_acceptance", "PASS")]:
            with self.subTest(key=key):
                p = deepcopy(self.plan)
                p["planning_maintenance"]["display_admission_receipt"]["b_design_go"][key] = value
                self.assertTrue(validate(p))

    def test_no_unqualified_trust_runtime_or_consumer_promotion(self):
        for key, value in [
            ("trust_anchor", "PASS"),
            ("wire", "FROZEN"),
            ("runtime", "PASS"),
            ("source_delivery", "PROTECTED_MERGED"),
            ("native", "PASS"),
            ("TV", "PASS"),
            ("joint", "PASS"),
            ("consumer_writes", True),
            ("automatic_dispatch", True),
        ]:
            with self.subTest(key=key):
                p = deepcopy(self.plan)
                p["planning_maintenance"]["display_admission_receipt"][key] = value
                self.assertTrue(validate(p))

    def test_B_source_GO_needs_exact_review_and_never_becomes_A_or_install_acceptance(self):
        for key, value in [("reviewed_sha", "0" * 40), ("producer_sha", "0" * 40),
                           ("scope", "A_AND_B"), ("source_sha256", "0" * 64),
                           ("technical_privacy", "PENDING"), ("public_TLS", "PASS"),
                           ("installed", "PASS"), ("native", "PASS")]:
            with self.subTest(key=key):
                p = deepcopy(self.plan)
                p["planning_maintenance"]["display_admission_receipt"]["b_source_go"][key] = value
                self.assertTrue(validate(p))
        p = deepcopy(self.plan)
        p["planning_maintenance"]["display_admission_receipt"].pop("b_source_go")
        self.assertTrue(validate(p))

    def test_limited_owner_choice_does_not_close_technical_or_issuer_gates(self):
        for key, value in [("independent_ha_owner_attestation", True),
                           ("security_review", "GO"), ("key_state", "PASS"),
                           ("wire", "FROZEN"), ("runtime_a", "IMPLEMENTED"),
                           ("selection", "INDEPENDENT_HA_ISSUER")]:
            with self.subTest(key=key):
                p = deepcopy(self.plan)
                p["planning_maintenance"]["display_admission_receipt"]["product_disposition"][key] = value
                self.assertTrue(validate(p))

    def test_no_node_completion_or_unrelated_admission(self):
        for nid in ["WEB::TRUST", "WEB::DISPLAY", "WEB::OWNER-SCANNER", "SETTINGS::CORE::PRODUCER"]:
            p = deepcopy(self.plan)
            n = next(n for n in p["planning_maintenance"]["nodes"] if n["id"] == nid)
            n["status"] = "Completed" if n["status"] != "Completed" else "Planned"
            self.assertTrue(validate(p), nid)

    def test_duplicate_nodes_cyclic_edges_or_missing_history_fail_closed(self):
        for change in ["duplicate", "cycle", "history"]:
            with self.subTest(change=change):
                p = deepcopy(self.plan)
                d = p["planning_maintenance"]
                if change == "duplicate":
                    d["nodes"].append(deepcopy(d["nodes"][0]))
                elif change == "cycle":
                    d["edges"].append(
                        dict(
                            d["edges"][0],
                            id="UNQUALIFIED-CYCLE",
                            producer="WEB::DISPLAY",
                            consumer="WEB::DISPLAY",
                        )
                    )
                else:
                    d["display_admission_receipt"]["previous_delta_sha256"] = "0" * 64
                self.assertTrue(validate(p))
