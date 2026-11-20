"""Protect exact source reconciliation without inventing product acceptance."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from validate_snapshot import load, validate
from render_snapshot import render
from moments_avatar_finalization_delta import PREFIX, READBACK

ROOT = Path(__file__).resolve().parent


class MomentsFinalizationTests(unittest.TestCase):
    def setUp(self):
        self.plan = load(ROOT / "djconnect-platform-v1.json")

    def test_exact_pair_source_and_complete_source_freeze(self):
        self.assertEqual(validate(self.plan), [])
        d = self.plan["planning_maintenance"]
        receipt = d["moments_avatar_finalization_receipt"]
        raw = (ROOT / receipt["predecessor_path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt["predecessor_sha256"])
        frozen = json.loads(raw)
        self.assertEqual(d["moments_avatar_receipt"], frozen["moments_avatar_receipt"])
        self.assertEqual(
            frozen["moments_avatar_receipt"]["source_delivery"], "LOCAL_IMPLEMENTATION_NOT_MERGED"
        )
        leaves = [n for n in d["nodes"] if n["id"].startswith(PREFIX)]
        self.assertEqual(len(leaves), 4)
        self.assertEqual(
            {n["id"] for n in leaves if n["status"] == "Planned"}, {PREFIX + "ACCEPTANCE"}
        )
        self.assertEqual(receipt["tde_assessment"], "FAIL")
        self.assertIn("SOURCE_DELIVERED", render(self.plan)["README.md"])

    def test_strict_owner_source_and_effect_booleans_cannot_be_coerced(self):
        for key, value in [
            ("automatic_dispatch", 0),
            ("automatic_dispatch", True),
            ("source_tree_equal", 1),
            ("source_tree_equal", False),
            ("apple_tree_equal", 1),
            ("product_unchanged", 1),
            ("qualified_product_count", True),
        ]:
            with self.subTest(key=key, value=value):
                p = deepcopy(self.plan)
                p["planning_maintenance"]["moments_avatar_finalization_receipt"][key] = value
                self.assertTrue(validate(p))

    def test_missing_wrong_original_provenance_or_publication_is_rejected(self):
        for field in (
            "core_qualified_head",
            "core_merge",
            "core_tree",
            "apple_qualified_head",
            "apple_merge",
            "apple_tree",
            "internal_artifact_sha256",
            "durable_evidence_sha256",
            "apple_durable_evidence_sha256",
            "source_readback_path",
            "source_readback_sha256",
            "predecessor_sha256",
        ):
            for value in (None, "unqualified"):
                with self.subTest(field=field, value=value):
                    p = deepcopy(self.plan)
                    p["planning_maintenance"]["moments_avatar_finalization_receipt"][field] = value
                    self.assertTrue(validate(p))

    def test_software_completion_does_not_close_operational_or_joint_acceptance(self):
        for field in (
            "overall_acceptance",
            "installed",
            "live_model",
            "deployment",
            "native",
            "tde_assessment",
            "tde_qualification",
            "tde_maintainability_risk",
        ):
            with self.subTest(field=field):
                p = deepcopy(self.plan)
                p["planning_maintenance"]["moments_avatar_finalization_receipt"][field] = "PASS"
                self.assertTrue(validate(p))

    def test_rehashed_wrong_main_readback_does_not_become_authority(self):
        path = ROOT.parents[2] / READBACK
        original = Path.read_bytes
        evidence = json.loads(original(path))
        evidence["merge_sha"] = "0" * 40
        raw = json.dumps(evidence, indent=2).encode()
        p = deepcopy(self.plan)
        d = p["planning_maintenance"]
        digest = hashlib.sha256(raw).hexdigest()
        d["moments_avatar_finalization_receipt"]["source_readback_sha256"] = digest
        with patch.object(
            Path, "read_bytes", lambda current: raw if current == path else original(current)
        ):
            self.assertTrue(validate(p))

    def test_joint_and_unrelated_work_cannot_change_with_source_reconciliation(self):
        d = self.plan["planning_maintenance"]
        targets = (
            PREFIX + "ACCEPTANCE",
            next(n["id"] for n in d["nodes"] if not n["id"].startswith(PREFIX)),
        )
        for identifier in targets:
            with self.subTest(identifier=identifier):
                p = deepcopy(self.plan)
                node = next(n for n in p["planning_maintenance"]["nodes"] if n["id"] == identifier)
                node["status"] = "Completed"
                node["title"] += " unauthorized"
                self.assertTrue(validate(p))

    def assert_rehashed_readback_rejected(self, evidence):
        path = ROOT.parents[2] / READBACK
        original = Path.read_bytes
        raw = json.dumps(evidence, indent=2).encode()
        digest = hashlib.sha256(raw).hexdigest()
        p = deepcopy(self.plan)
        d = p["planning_maintenance"]
        d["moments_avatar_finalization_receipt"]["source_readback_sha256"] = digest
        with patch.object(
            Path, "read_bytes", lambda current: raw if current == path else original(current)
        ):
            self.assertTrue(validate(p))

    def test_qualified_outcome_cannot_hide_one_failed_canonical_core_check(self):
        evidence = json.loads((ROOT.parents[2] / READBACK).read_bytes())
        qualification = evidence["durable_qualification"]["qualification"]
        self.assertEqual(qualification["outcome"], "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED")
        qualification["required_checks"]["post_merge_tests"] = "FAIL"
        self.assert_rehashed_readback_rejected(evidence)

    def test_same_count_all_pass_wrong_apple_check_names_are_rejected(self):
        evidence = json.loads((ROOT.parents[2] / READBACK).read_bytes())
        checks = evidence["apple_source_publication"]["required_checks"]
        original = checks.pop("post_merge_tests")
        checks["unrelated_check"] = original
        self.assertEqual(len(checks), 12)
        self.assertEqual(set(checks.values()), {"PASS"})
        self.assert_rehashed_readback_rejected(evidence)
