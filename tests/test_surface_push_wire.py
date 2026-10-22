"""Cross-language API vectors and adversarial original-operation ACK fences."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from tests.test_profile_dj_settings_persistence import operation
from custom_components.djconnect import surface_push_wire as wire
from custom_components.djconnect.surface_push_contract import SurfacePushError


class SurfacePushWireTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((Path(__file__).parent / "fixtures/surface_push/api_a45_wire_vectors.json").read_text())
        self.vector = self.fixture["vectors"][0]
        self.now = self.vector["now_ms"]
        self.coordinate = {k: self.vector["payload"][k] for k in wire.COORDINATE}
        self.registration = {k: self.vector["payload"][k] for k in wire.REGISTER}

    def test_actual_api_decoded_vectors_have_identical_canonical_bytes_and_operation_digest(self):
        self.assertEqual(self.fixture["source_head"], "a45fef1c692ef766af4696e013c450d1b63a0d31")
        for vector in self.fixture["vectors"]:
            with self.subTest(kind=vector["kind"], role=vector["payload"].get("token_role")):
                self.assertEqual(wire.canonical(vector["payload"]), vector["canonical"])
                self.assertEqual(wire.request_digest(vector["kind"], vector["payload"]), vector["digest"])
                if vector["kind"] == "event":
                    continue  # Event admission/serializer is not delivered by this test.
                kwargs = {"now_ms": vector["now_ms"]}
                if vector["kind"] == "register":
                    kwargs["registration"] = {k: vector["payload"][k] for k in wire.REGISTER}
                body = wire.operation_body(vector["kind"], self.coordinate, **kwargs)
                self.assertEqual(body, vector["payload"])
        u = self.fixture["unicode"]
        self.assertEqual(wire.canonical(u["payload"]), u["canonical"])

    def test_canonical_domain_rejects_ambiguous_numbers_keys_and_invalid_utf8(self):
        for value in (1.0, float("nan"), float("inf"), 9007199254740992,
                      {"nonascii-🎵": 1}, {1: "key"}, "\ud800", set()):
            with self.subTest(type=type(value).__name__), self.assertRaises(SurfacePushError):
                wire.canonical(value)

    def test_write_age_is_original_uuid_but_status_does_not_renew_or_replace_it(self):
        for now in (self.now - 30001, self.now + 300000):
            with self.assertRaises(SurfacePushError):
                wire.operation_body("revoke", self.coordinate, now_ms=now)
        self.assertEqual(wire.operation_body("status", self.coordinate,
            now_ms=self.now + 800000)["operation_id"], self.coordinate["operation_id"])

    def test_closed_coordinate_rejects_bool_revision_aliases_and_identity_exports(self):
        for patch in ({"revision": True}, {"revision": wire.SAFE_INTEGER},
                      {"contract_version": True}, {"operation_id": "retry"},
                      {"binding_id": "A" * 64}, {"ha_install_id": "private"},
                      {"owner_binding": []}, {"registration_id": "a" * 129}):
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                wire.operation_body("register", self.coordinate | patch,
                    now_ms=self.now, registration=self.registration)

    def test_registration_is_closed_and_does_not_turn_wire_validation_into_native_authority(self):
        for patch in ({"expires_at_ms": True}, {"expires_at_ms": self.now},
                      {"expires_at_ms": self.now + 28800001}, {"apns_token": "AA" * 16},
                      {"apns_token": "a" * 31}, {"platform": "tvos"},
                      {"token_role": []}, {"apns_environment": "development"},
                      {"owner": "private"}, {"target": self.registration["target"] | {"activity_id": "wrong-role"}},
                      {"target": self.registration["target"] | {"widget_kind": "w" * 129}}):
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                wire.operation_body("register", self.coordinate, now_ms=self.now,
                    registration=self.registration | patch)
        with self.assertRaises(SurfacePushError):
            wire.operation_body("revoke", self.coordinate, now_ms=self.now, registration={})

    def ack(self):
        return {"contract_version": 1, "success": True,
            **{k: self.coordinate[k] for k in ("registration_id", "generation", "revision", "operation_id")},
            "state": "registered", "operation_state": "registered", "replayed": False,
            "expires_at_ms": self.registration["expires_at_ms"], "current_revision": 1,
            "provider_status": None}

    def accepted(self, ack, kind="register"):
        return wire.acknowledged(ack, self.coordinate, original_kind=kind,
            original_expiry_ms=self.registration["expires_at_ms"])

    def test_status_success_requires_original_operation_and_current_revision_not_just_http200(self):
        self.assertTrue(self.accepted(self.ack()))
        self.assertTrue(self.accepted(self.ack() | {"replayed": True}))
        for patch in ({"success": False}, {"current_revision": 2}, {"current_revision": None},
                      {"state": "withdrawn"}, {"state": "expired"},
                      {"operation_state": "unknown"}, {"operation_state": "conflict"},
                      {"expires_at_ms": self.registration["expires_at_ms"] + 1},
                      {"provider_status": 200}):
            with self.subTest(patch=patch):
                self.assertFalse(self.accepted(self.ack() | patch))
        for patch in ({"operation_id": operation(self.now, 2)}, {"revision": 2},
                      {"generation": "rotated"}, {"registration_id": "different"}):
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                self.accepted(self.ack() | patch)

    def test_strict_ack_types_and_unknown_fields_cannot_be_truthy_success(self):
        for patch in ({"contract_version": True}, {"success": 1}, {"replayed": 0},
                      {"revision": True}, {"current_revision": True},
                      {"provider_status": True}, {"state": []}, {"operation_state": []},
                      {"expires_at_ms": True}, {"token": "must-not-return"}):
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                self.accepted(self.ack() | patch)
        missing = self.ack()
        del missing["operation_id"]
        with self.assertRaises(SurfacePushError):
            self.accepted(missing)

    def test_revoke_and_provider_acceptance_have_distinct_original_outcomes(self):
        ack = self.ack() | {"state": "revoked", "operation_state": "revoked", "expires_at_ms": 0}
        self.assertTrue(self.accepted(ack, "revoke"))
        self.assertFalse(self.accepted(ack))
        self.assertFalse(self.accepted(ack | {"current_revision": 2}, "revoke"))
        event = self.ack() | {"operation_state": "provider_accepted", "provider_status": 200}
        self.assertTrue(self.accepted(event, "event"))  # Transport acceptance only.
        self.assertFalse(self.accepted(event))
        self.assertFalse(self.accepted(event | {"provider_status": 201}, "event"))
        original = deepcopy(self.coordinate)
        original["operation_id"] = operation(self.now, 2)
        with self.assertRaises(SurfacePushError):
            wire.acknowledged(event, original, original_kind="event",
                original_expiry_ms=self.registration["expires_at_ms"])
