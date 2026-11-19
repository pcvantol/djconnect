"""Frozen owning API vectors, never synthetic role/native admission."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

from tests import test_host_wake_proxy_wire as public

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(public.PACKAGE + ".host_wake_api_wire",
    ROOT / "custom_components/djconnect/host_wake_api_wire.py")
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
REPLY_PATH = ROOT / "tests/fixtures/host_wake_api_private_reply_51f3028.json"
RESOLVE_PATH = ROOT / "tests/fixtures/host_wake_api_private_resolve_51f3028.json"
VECTORS = json.loads(REPLY_PATH.read_bytes())
RESOLVE = json.loads(RESOLVE_PATH.read_bytes())
CHALLENGE = next(c["reply"]["challenge"] for c in VECTORS["cases"] if c["route"] == "native/challenge")


class HostWakeApiWireTests(unittest.TestCase):
    def decode(self, case, value=None, **kwargs):
        return wire.reply(case["route"], case["reply"] if value is None else value,
            case["request"], VECTORS["original"], VECTORS["retained_proof_kind"],
            retained_challenge=CHALLENGE, **kwargs)

    def test_original_frozen_bytes_and_seven_request_hashes(self):
        self.assertEqual(hashlib.sha256(REPLY_PATH.read_bytes()).hexdigest(),
            "3c54207b2bc8d4d41c82b7cca04cfae405041e9b4ed32f129ba68e9686d99d00")
        self.assertEqual(hashlib.sha256(RESOLVE_PATH.read_bytes()).hexdigest(),
            "57d64138a3d13f817e5e59b2c4b20e20f21f66b1b853d7ad4c26fa08351fd360")
        for case in VECTORS["cases"]:
            with self.subTest(route=case["route"]):
                self.assertEqual(wire.request_hash(case["route"], case["request"]), case["request_sha256"])
                self.assertEqual(self.decode(case), case["reply"])
        self.assertEqual(wire.request_hash("authorization/resolve", RESOLVE["request"]), RESOLVE["request_sha256"])
        self.assertEqual(wire.resolved(RESOLVE["reply"], RESOLVE["request"]), RESOLVE["reply"])

    def test_no_caller_policy_hash_or_new_role_from_resolve_metadata(self):
        for field in wire.POLICY:
            bad = deepcopy(RESOLVE["request"])
            bad["scope"][field] = "f" * 64
            with self.subTest(field=field), self.assertRaises(public.wire.RichError):
                wire.request("authorization/resolve", bad)
        for field in ("credential", "private_job_id", "owner_approved", "clock_qualified"):
            with self.subTest(field=field), self.assertRaises(public.wire.RichError):
                wire.resolved(RESOLVE["reply"] | {field: True}, RESOLVE["request"])
        for field in ("request_sha256", "scope_sha256"):
            with self.subTest(field=field), self.assertRaises(public.wire.RichError):
                wire.resolved(RESOLVE["reply"] | {field: "f" * 64}, RESOLVE["request"])

    def test_every_private_reply_missing_unknown_and_original_identity_change_closed(self):
        for case in VECTORS["cases"]:
            for key in case["reply"]:
                bad = {k: v for k, v in case["reply"].items() if k != key}
                with self.subTest(route=case["route"], missing=key), self.assertRaises(public.wire.RichError):
                    self.decode(case, bad)
            for field, value in (("extra", True), ("request_sha256", "f" * 64),
                    ("issuer_operation_id", "another-operation"), ("core_purpose_id", "another-purpose"),
                    ("generation", "another-generation"), ("revision", True), ("original_wake_expires_at_ms", True)):
                with self.subTest(route=case["route"], field=field), self.assertRaises(public.wire.RichError):
                    self.decode(case, case["reply"] | {field: value})

    def test_status_never_returns_credentials_or_replaces_the_original_private_purpose(self):
        case = next(c for c in VECTORS["cases"] if c["route"] == "issuer/status")
        with self.assertRaises(public.wire.RichError):
            self.decode(case, case["reply"] | {"credential": "djchw_" + "A" * 43})
        with self.assertRaises(public.wire.RichError):
            self.decode(case, private_purpose="another-private-purpose")
        for value in ("available", "restored"):
            with self.assertRaises(public.wire.RichError):
                self.decode(case, case["reply"] | {"credential_state": value})

    def test_issued_ack_cannot_join_sent_original_A_to_retained_original_B(self):
        original_case = next(c for c in VECTORS["cases"] if c["route"] == "issuer/issue")
        for field, value in (("owner_binding", "f" * 64), ("source_binding", "e" * 64),
                ("native_token_sha256", "d" * 64)):
            case = deepcopy(original_case)
            case["request"]["original"][field] = value
            # Correlation matches actual request A; ACK original remains B.
            case["reply"]["request_sha256"] = wire.request_hash(case["route"], case["request"])
            with self.subTest(field=field), self.assertRaises(public.wire.RichError):
                self.decode(case)

    def test_native_acks_need_same_known_challenge_and_original_verification_deadline(self):
        for case in (c for c in VECTORS["cases"] if c["route"] in {"native/complete", "native/status"}):
            with self.subTest(route=case["route"]), self.assertRaises(public.wire.RichError):
                wire.reply(case["route"], case["reply"], case["request"], VECTORS["original"],
                    VECTORS["retained_proof_kind"])
            for value in (CHALLENGE["captured_at_ms"] - 1, CHALLENGE["expires_at_ms"], True):
                with self.subTest(route=case["route"], value=value), self.assertRaises(public.wire.RichError):
                    self.decode(case, case["reply"] | {"native_verified_at_ms": value})
            with self.assertRaises(public.wire.RichError):
                self.decode(case, case["reply"] | {"original_sha256": "f" * 64})

    def test_challenge_transcript_kind_and_original_not_replaceable(self):
        case = next(c for c in VECTORS["cases"] if c["route"] == "native/challenge")
        for field, value in (("client_data_sha256", "f" * 64),
                ("canonical_transcript_utf8", case["reply"]["canonical_transcript_utf8"] + " "),
                ("native_proof_kind", "app_attest_attestation")):
            with self.subTest(field=field), self.assertRaises(public.wire.RichError):
                self.decode(case, case["reply"] | {field: value})
        changed = deepcopy(case["reply"])
        changed["original"]["owner_binding"] = "f" * 64
        with self.assertRaises(public.wire.RichError):
            self.decode(case, changed)

    def test_fixed_errors_never_export_internal_exception_or_borrow_an_http_status(self):
        for status, codes in wire.ERRORS.items():
            for code in codes:
                value = {"version": wire.VERSION, "success": False, "error": code}
                self.assertEqual(wire.error(status, value), value)
                for bad in (value | {"error": "private internal text"}, value | {"detail": "secret"}, value | {"success": True}):
                    with self.assertRaises(public.wire.RichError):
                        wire.error(status, bad)
                with self.assertRaises(public.wire.RichError):
                    wire.error(200, value)


class HostWakeFirstAttestationWireTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "tests/fixtures/host_wake_api_first_attestation_03323cd.json"
        self.fixture = json.loads(self.path.read_bytes())
        self.challenge = next(c["reply"]["challenge"] for c in self.fixture["cases"] if c["route"] == "native/challenge")

    def decode(self, case, kind="app_attest_attestation"):
        return wire.reply(case["route"], case["reply"], case["request"], self.fixture["original"], kind,
            retained_challenge=self.challenge)

    def test_original_first_attest_vectors_are_closed_DATA_with_unchanged_transcript_preimages(self):
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),
            "c395c56c81b70017c1feaf687ae683791031d2b678ae3b520027b4c87118cb7f")
        role = self.fixture["resolve"]
        self.assertEqual(wire.request_hash("authorization/resolve", role["request"]), role["request_sha256"])
        self.assertEqual(wire.resolved(role["reply"], role["request"]), role["reply"])
        for case in self.fixture["cases"]:
            with self.subTest(route=case["route"]):
                self.assertEqual(wire.request_hash(case["route"], case["request"]), case["request_sha256"])
                self.assertEqual(self.decode(case), case["reply"])
        failure = self.fixture["invalid_proof_runtime_expectation"]
        self.assertEqual(wire.error(failure["status"], failure["body"]), failure["body"])

    def test_first_kind_cannot_turn_into_assertion_after_prepare_or_from_local_key_existence(self):
        for case in self.fixture["cases"]:
            if case["route"] == "issuer/issue" or case["route"].startswith("native/"):
                with self.subTest(route=case["route"]), self.assertRaises(public.wire.RichError):
                    self.decode(case, kind="app_attest_assertion")
        role = self.fixture["resolve"]
        for changed in (role["reply"] | {"native_proof_kind": "local_key_exists"},
                role["reply"] | {"clock_qualified": True}, role["reply"] | {"enrolled": True}):
            with self.assertRaises(public.wire.RichError):
                wire.resolved(changed, role["request"])

    def test_core_does_not_adopt_operator_policy_or_private_enrollment_writer_from_vectors(self):
        with self.assertRaises(public.wire.RichError):
            wire.request("issuer/issue", self.fixture["policy_request"])
        role = self.fixture["resolve"]
        for field in ("native_key_ref", "public_key_spki_b64", "signed_host_artifact_sha256"):
            with self.subTest(field=field), self.assertRaises(public.wire.RichError):
                wire.resolved(role["reply"] | {field: self.fixture["policy_request"].get(field, "synthetic")}, role["request"])


if __name__ == "__main__":
    unittest.main()
