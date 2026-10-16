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
            "djconnect-federated-planning-delta/15",
        )
        self.assertIn("wire NOT_FROZEN, runtime NOT_IMPLEMENTED", render(self.plan)["README.md"])

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
