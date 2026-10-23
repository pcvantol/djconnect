"""Pinned public API issuer bytes, closed grammar and tamper rejection.

Crypto execution uses the actual isolated HA harness, not a homemade verifier.
These expired public vectors carry no enrolment or current grant.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from tests.test_profile_dj_settings_persistence import operation
from custom_components.djconnect import surface_issuer_wire as wire
from custom_components.djconnect.surface_push_contract import SurfacePushError


class SurfaceIssuerWireTests(unittest.TestCase):
    def setUp(self):
        self.raw = (Path(__file__).parent / "fixtures/surface_push/api_2a6_issuer_public_vectors.json").read_bytes()
        self.fixture = json.loads(self.raw)
        self.v = self.fixture["vectors"][0]

    def test_original_public_vectors_are_byte_equal_to_owning_api_source(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),
            "aa64043ad7f65681a55c694b0635d898703a7632c2e8dfdd5b0647b6815e5c6e")
        self.assertEqual(wire.public_key_thumbprint(self.fixture["public_key"]),
            self.fixture["key_thumbprint"])
        for vector in self.fixture["vectors"]:
            self.assertEqual(wire.signing_bytes(vector["path"], vector["payload"]),
                vector["signing_bytes_utf8"].encode())
            self.assertEqual(len(wire.decoded(vector["signature"], 64)), 64)

    def test_exact_route_action_cannot_be_crossed_or_normalized(self):
        for path in (self.v["path"] + "/", self.v["path"] + "?x=1",
                     self.v["path"] + "#fragment", self.v["path"].replace("challenge", "status"),
                     self.v["path"].replace("issuer", "%69ssuer"), "https://example.test" + self.v["path"], None, []):
            with self.subTest(path=path), self.assertRaises(SurfacePushError):
                wire.signing_bytes(path, self.v["payload"])

    def test_unknown_fields_versions_bool_revision_and_non_uuid_operations_closed(self):
        for patch in ({"contract_version": True}, {"contract_version": 2},
                      {"delegation_revision": True}, {"delegation_revision": 2},
                      {"purpose": "other"}, {"operation_id": "new-retry"},
                      {"operation_id": []}, {"owner": "private"}, {"nonce": "A" * 43},
                      {"delegation_id": "space separated"}, {"key_thumbprint": "F" * 64}):
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                wire.signing_bytes(self.v["path"], self.v["payload"] | patch)

    def test_issue_is_closed_and_requires_canonical_nonce_and_scope(self):
        vector = self.fixture["vectors"][1]
        for patch in ({"nonce": "A" * 43 + "="}, {"nonce": "A" * 42 + "B"},
                      {"nonce": "A" * 42}, {"scope_digest": None}, {"challenge_id": ""}):
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                wire.signing_bytes(vector["path"], vector["payload"] | patch)
        bad = deepcopy(vector["payload"])
        del bad["nonce"]
        with self.assertRaises(SurfacePushError):
            wire.signing_bytes(vector["path"], bad)

    def test_no_private_or_algorithm_fields_or_wrong_key_size(self):
        key = self.fixture["public_key"]
        for patch in ({"d": "secret"}, {"alg": "ES256"}, {"crv": "P-384"},
                      {"x": key["x"] + "="}, {"y": "A" * 42}, {"kty": "RSA"}):
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                wire.public_key_thumbprint(key | patch)

    def test_signature_is_canonical_raw64_not_padded_or_der(self):
        for signature in (self.v["signature"] + "=", "AA", "A" * 87,
                          "A" * 85 + "B", "M" * 96, None):
            with self.subTest(signature=signature), self.assertRaises(SurfacePushError):
                wire.decoded(signature, 64)

    def test_crypto_envelope_grammar_is_checked_before_optional_ha_import(self):
        envelope = {"payload": self.v["payload"], "signature": self.v["signature"]}
        for value in (envelope | {"Authorization": "Bearer djci_test"},
                      envelope | {"signature": "A" * 43}, {"payload": self.v["payload"]}):
            with self.assertRaises(SurfacePushError):
                wire.verify_envelope(self.v["path"], value, self.fixture["public_key"])

    def test_byte_serializer_does_not_create_http_client_or_credentials(self):
        self.assertFalse(hasattr(wire, "enrol"))
        self.assertFalse(hasattr(wire, "issue"))
        self.assertFalse(hasattr(wire, "SurfacePurposeCredential"))
        self.assertFalse(hasattr(wire, "private_key"))

    def test_original_uuid_is_retained_without_synthesizing_a_fresh_operation(self):
        payload = self.v["payload"] | {"operation_id": operation(1792700000000)}
        result = wire.signing_bytes(self.v["path"], payload)
        self.assertIn(payload["operation_id"].encode(), result)
        self.assertEqual(wire.signing_bytes(self.v["path"], payload), result)
