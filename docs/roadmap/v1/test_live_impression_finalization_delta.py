"""Source reconciliation must not rewrite the freeze or promote product acceptance."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from validate_snapshot import load, validate
from render_snapshot import render

ROOT = Path(__file__).resolve().parent


class LiveImpressionFinalizationTests(unittest.TestCase):
    def setUp(self):
        self.plan = load(ROOT / "djconnect-platform-v1.json")

    def test_exact_source_receipt_and_immutable_freeze(self):
        self.assertEqual(validate(self.plan), [])
        d = self.plan["planning_maintenance"]
        receipt = d["live_impression_finalization_receipt"]
        raw = (ROOT / receipt["predecessor_path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt["predecessor_sha256"])
        frozen = json.loads(raw)
        self.assertEqual(frozen["live_impression_receipt"], d["live_impression_receipt"])
        self.assertEqual(frozen["live_impression_receipt"]["source_delivery"], "LOCAL_IMPLEMENTATION_NOT_MERGED")
        self.assertEqual(receipt["source_delivery"], "PROTECTED_MERGED")
        self.assertIn("SOURCE_DELIVERED", render(self.plan)["README.md"])

    def test_no_unqualified_product_installation_or_consumer_promotion(self):
        for key, value in (("overall_acceptance", "PASS"), ("installed", "PASS"),
                           ("live_model", "PASS"), ("native", "PASS"), ("shared_tv", "PASS"),
                           ("automatic_dispatch", True), ("source_tree_equal", False),
                           ("core_main_validation", "PENDING"), ("apple_main_validation", "PENDING"),
                           ("apple_durable_publication", "PENDING"), ("core_merge", "0" * 40), ("source_readback_sha256", "0" * 64)):
            with self.subTest(field=key):
                p = deepcopy(self.plan)
                p["planning_maintenance"]["live_impression_finalization_receipt"][key] = value
                self.assertTrue(validate(p))

    def test_only_three_delivered_source_leaves_change(self):
        d = self.plan["planning_maintenance"]
        source = [n for n in d["nodes"] if n["id"].startswith("LIVE-IMPRESSION::")]
        self.assertEqual(len(source), 4)
        self.assertEqual([n["id"] for n in source if n["status"] == "Planned"], ["LIVE-IMPRESSION::ACCEPTANCE"])
        for identifier in ("LIVE-IMPRESSION::ACCEPTANCE", next(n["id"] for n in d["nodes"] if not n["id"].startswith("LIVE-IMPRESSION::"))):
            p = deepcopy(self.plan)
            node = next(n for n in p["planning_maintenance"]["nodes"] if n["id"] == identifier)
            if identifier.endswith("ACCEPTANCE"):
                node["status"] = "Completed"
            else:
                node["title"] += " unqualified change"
            self.assertTrue(validate(p), identifier)
