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

    def test_new_nodes_stay_planned_and_no_dispatch(self):
        self.assertFalse(self.p["planning_maintenance"]["execution_authority"])
        for n in self.p["planning_maintenance"]["nodes"]:
            if "ACTIVE-SESSION-MOOD" not in n["id"]:
                self.assertEqual(n["status"], "Planned")

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
