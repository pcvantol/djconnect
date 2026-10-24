"""Normative design/reference models; deliberately no runtime/native claim."""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples/client_contracts/surface_push_v3"


class OriginalClockV3ContractReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(
            (FIXTURES / "original-clock-derived-summary.json").read_text()
        )
        cls.models = json.loads(
            (FIXTURES / "original-clock-model-vectors.json").read_text()
        )

    def test_summary_resolves_exact_full_normative_document(self):
        authority = self.summary["authority"]
        self.assertEqual(
            authority["classification"],
            "DERIVED_NONNORMATIVE_COMPANION_NOT_STANDALONE_CONTRACT",
        )
        path = (ROOT / authority["canonical_document_path"]).resolve()
        self.assertTrue(path.is_relative_to(ROOT))
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            authority["canonical_document_sha256"],
        )
        self.assertFalse(authority["publication_reference_resolution_required"])
        self.assertIn("alone is normative", authority["precedence"])
        self.assertIn("derived nonnormative", self.summary["delivery_guards"]["this_artifact"])

    def test_closed_outer_fieldsets_preserve_widget_predicate(self):
        self.assertEqual(
            set(self.summary["context_request"]["exact_keys"]),
            {"contract_version", "device_id", "client_type", "session_id", "operation_id"},
        )
        self.assertEqual(len(self.summary["register_request"]["exact_keys"]), 14)
        self.assertEqual(len(self.summary["context_success"]["exact_keys"]), 11)
        response = self.summary["register_response"]
        confirmed = set(response["confirmed_exact_keys"])
        unsuccessful = set(response["unsuccessful_exact_keys"])
        self.assertEqual(len(confirmed), 9)
        self.assertEqual(len(unsuccessful), 8)
        self.assertEqual(confirmed - unsuccessful, {"background_read"})
        self.assertEqual(set(response["http_error_exact_keys"]), {"success", "error"})
        self.assertEqual(self.summary["admitted_scope"], "EXISTING_WIDGET_ONLY_GUARDS_UNCHANGED")
        self.assertEqual(response["inner_API_registry_relay_wire_version"], 1)

    def test_outer_integer_domains_are_strict_and_bounded(self):
        rules = self.summary["wire_integer_validation"]
        self.assertTrue(rules["strict_JSON_integer_excluding_boolean"])
        self.assertFalse(rules["numeric_string_or_fraction_or_NaN_Infinity_coercion"])
        domains = self.summary["context_success"]["integer_domains"]
        self.assertEqual(domains["purpose_remaining_at_original_start_ms"], [1, 28_800_000])
        self.assertEqual(domains["context_remaining_at_original_start_ms"], [1, 30_000])
        for limits in domains.values():
            self.assertTrue(all(type(value) is int for value in limits))
            self.assertGreater(limits[0], 0)
            self.assertLessEqual(limits[1], 2**53 - 1)
        constants = self.summary["context_success"]["constants"]
        self.assertIs(type(constants["contract_version"]), int)
        self.assertEqual(constants["contract_version"], 3)
        self.assertIs(constants["success"], True)
        self.assertIs(constants["available"], True)

    def test_reference_budgets_obey_both_original_expiry_bounds(self):
        # Independent exact-rational oracle for declared mathematical examples.
        # It is not a call to, or evidence for, a v3 runtime producer.
        for case in self.models["arithmetic"]:
            with self.subTest(case=case["name"]):
                lifetime = case["original_expiry_ms"] - case["original_wall_ms"]
                remaining = Fraction(lifetime) + 1000 * (
                    Fraction(case["G0"]) - Fraction(case["S0"])
                )
                mono = remaining.numerator // remaining.denominator
                wall = case["original_expiry_ms"] - case["W0_ms"]
                purpose = min(mono, wall)
                submit = min(30_000, purpose, case["uuid_remaining_ms"])
                self.assertEqual(mono, case["expected_M0_ms"])
                self.assertEqual(wall, case["expected_A0_ms"])
                self.assertEqual(purpose, case["expected_P0_ms"])
                self.assertEqual(submit, case["expected_K0_ms"])
                self.assertLessEqual(purpose, mono)
                self.assertLessEqual(purpose, wall)
                self.assertLessEqual(submit, purpose)
                self.assertLessEqual(submit, case["uuid_remaining_ms"])
                if case.get("expected") == "CLOSED":
                    self.assertLessEqual(purpose, 0)

    def test_mapping_examples_remain_conditional_models(self):
        for case in self.models["client_mapping"]:
            with self.subTest(case=case["name"]):
                if case["rho"] is None:
                    self.assertEqual(case["expected"], "CLOSED")
                    continue
                exact = Fraction(case["rho"]) * case["server_budget_ms"]
                mapped = exact.numerator // exact.denominator
                self.assertEqual(mapped, case["expected_mapped_ms"])
                self.assertLessEqual(Fraction(mapped), exact)
        self.assertFalse(self.summary["client_budget"]["rho_wire_field"])
        self.assertEqual(
            self.summary["client_budget"]["unknown_mapping"],
            "CLOSED_NO_POSITIVE_LOCAL_LIFETIME",
        )

    def test_final_timestamp_addition_cannot_round_above_original_budget(self):
        case = self.models["final_addition"]
        origin = float.fromhex(case["C0_float_hex"])
        exact = Fraction.from_float(origin) + Fraction(case["mapped_budget_ms"], 1000)
        naive = origin + case["mapped_budget_ms"] / 1000
        self.assertGreater(Fraction.from_float(naive), exact)
        downward = math.nextafter(naive, -math.inf)
        self.assertLessEqual(Fraction.from_float(downward), exact)
        self.assertEqual(
            (Fraction.from_float(naive) - Fraction.from_float(origin)) * 1000,
            Fraction(case["naive_elapsed_ms"]),
        )
        self.assertEqual(
            (Fraction.from_float(downward) - Fraction.from_float(origin)) * 1000,
            Fraction(case["greatest_downward_elapsed_ms"]),
        )

    def test_declared_same_purpose_history_never_replaces_earlier_minimum(self):
        cases = self.models["history_and_identity"]
        minimum = next(case for case in cases if "candidates_ms" in case)
        self.assertEqual(min(minimum["candidates_ms"]), minimum["expected_minimum_ms"])
        lost = next(case for case in cases if case["name"] == "lost_original_pin")
        self.assertEqual(lost["expected"], "CLOSED_NOT_FIRST_USE")
        self.assertIn("NOT_EXECUTED_PRODUCT_TESTS", self.models["semantic_identity_cases_are"])

    def test_design_samples_do_not_claim_runtime_or_native_qualification(self):
        self.assertIn("NOT_ACTUAL_PRODUCER_HA_NATIVE", self.models["status"])
        self.assertIn("NOT_FULL_CONTRACT_OR_PRODUCT_COVERAGE", self.models["coverage_scope"])
        self.assertEqual(self.models["actual_clock_rate_domain_suspend_acceptance"], "OPEN")
        self.assertEqual(self.models["all_operational_native_acceptance"], "NOT_GRANTED")
        self.assertFalse(self.summary["delivery_guards"]["native_Widget_Activity_VibeCast_GO"])
        self.assertFalse(self.summary["delivery_guards"]["public_dispatch_or_Activity_profiles_added"])


if __name__ == "__main__":
    unittest.main()
