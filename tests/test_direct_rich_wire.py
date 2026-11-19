"""Causal closed-wire checks; no permission, HA, provider or native factory."""
import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

_PATH = Path(__file__).resolve().parents[1] / "custom_components/djconnect/direct_rich_wire.py"
_SPEC = importlib.util.spec_from_file_location("djc_direct_rich_wire_under_test", _PATH)
wire = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(wire)


class DirectRichWireTests(unittest.TestCase):
    def setUp(self):
        self.operation = "4cf66d62-d59f-4093-9e39-4c101ee0351b"
        self.purpose = "63506d46-eeaf-409c-8d82-e6d01cc9e2fb"
        self.authorize = {"contract_version": 1,
            "device_id": "djconnect-ios-ABCDEF012345", "client_type": "ios",
            "session_id": "session-original", "surface": "live_activity",
            "operation_id": self.operation, "enabled": True,
            "os_snapshot_cache": True, "locked_display": True}

    def raw(self, value):
        return json.dumps(value, separators=(",", ":")).encode()

    def test_exact_new_namespace_intentions_do_not_import_old_grants(self):
        manage = {k: v for k, v in self.authorize.items() if k not in wire.CONSENT}
        requests = {"authorize": self.authorize, "status": manage, "withdraw": manage,
            "read": {"contract_version": 1, "purpose_id": self.purpose},
            "asset": {"contract_version": 1, "purpose_id": self.purpose,
                "frame_id": "a" * 64, "asset_id": "a" * 32}}
        for kind, payload in requests.items():
            with self.subTest(kind=kind):
                self.assertEqual(wire.parse(kind, self.raw(payload)), payload)
            for legacy in ("grant_id", "context_handle", "registration_id", "epoch", "lease"):
                with self.subTest(kind=kind, legacy=legacy), self.assertRaises(wire.RichError):
                    wire.parse(kind, self.raw(payload | {legacy: "not-a-rich-authority"}))
        with self.assertRaises(wire.RichError):
            wire.parse("register", self.raw(self.authorize))

    def test_missing_and_unknown_fields_are_rejected_on_actual_raw_request(self):
        for key in self.authorize:
            missing = {k: v for k, v in self.authorize.items() if k != key}
            with self.subTest(missing=key), self.assertRaises(wire.RichError):
                wire.parse("authorize", self.raw(missing))
        for payload in (self.authorize | {"owner_attested": True}, [], None, True):
            with self.subTest(payload=type(payload)), self.assertRaises(wire.RichError):
                wire.parse("authorize", self.raw(payload))

    def test_duplicate_and_escape_equivalent_keys_never_accept_last_wins(self):
        raw = self.raw(self.authorize)
        for insertion in (b'"contract_version":1,', b'"\\u0063ontract_version":1,',
                b'"enabled":false,', b'"enabled":true,'):
            with self.subTest(insertion=insertion), self.assertRaises(wire.RichError):
                wire.parse("authorize", b"{" + insertion + raw[1:])
        with self.assertRaises(wire.RichError):
            wire.parse("authorize", raw[:-1] + b',"extra":{"x":1,"x":2}}')

    def test_bool_float_unsafe_and_null_versions_are_not_coerced(self):
        for value in (True, False, 1.0, "1", None, -1, 2, 9007199254740992):
            with self.subTest(value=value), self.assertRaises(wire.RichError):
                wire.parse("authorize", self.raw(self.authorize | {"contract_version": value}))
        for key in wire.CONSENT:
            for value in (1, 0, "true", None, []):
                with self.subTest(key=key, value=value), self.assertRaises(wire.RichError):
                    wire.parse("authorize", self.raw(self.authorize | {key: value}))

    def test_bad_utf8_surrogates_nonfinite_recursion_and_byte_limit_close(self):
        for raw in (b"\xff", b'\xef\xbb\xbf{}', b'{"x":NaN}', b'{"x":Infinity}',
                b'{"x":-Infinity}', b'{"x":"\\ud800"}',
                b"[" * 2000 + b"0" + b"]" * 2000, b" " * 8193):
            with self.subTest(size=len(raw)), self.assertRaises(wire.RichError):
                wire.parse("authorize", raw)
        raw = self.raw(self.authorize)
        self.assertEqual(wire.parse("authorize", raw + b" " * (8192 - len(raw))), self.authorize)
        with self.assertRaises(wire.RichError):
            wire.parse("authorize", raw + b" " * (8193 - len(raw)))

    def test_real_platform_identity_and_original_uuid_domain_are_closed(self):
        bad = [{"device_id": "djconnect-ios-ABCDEF012345 "}, {"client_type": "macos"},
            {"client_type": "macos", "device_id": "djconnect-macos-ABCDEF012345"},
            {"surface": "status_activity"}, {"session_id": "private/session"},
            {"session_id": "a" * 129}, {"operation_id": self.operation.upper()},
            {"operation_id": "00000000-0000-7000-8000-000000000001"},
            {"operation_id": "00000000-0000-4000-0000-000000000001"}]
        for patch in bad:
            with self.subTest(patch=patch), self.assertRaises(wire.RichError):
                wire.parse("authorize", self.raw(self.authorize | patch))
        widget = self.authorize | {"surface": "widget", "client_type": "macos",
            "device_id": "djconnect-macos-ABCDEF012345"}
        self.assertEqual(wire.parse("authorize", self.raw(widget)), widget)

    def test_read_and_asset_credential_families_cannot_substitute(self):
        suffix = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
        for family in ("read", "asset"):
            secret = "djcrich" + family + "_" + suffix
            self.assertEqual(wire.credential({"Authorization": "Bearer " + secret}, family), secret)
            other = "asset" if family == "read" else "read"
            for bad in (secret.replace(family, other, 1), "ordinary-owner-bearer",
                    "djcsurface_" + suffix, secret + "=", secret + " ",
                    secret[:-1] + "B"):
                with self.subTest(family=family, bad_length=len(bad)), self.assertRaises(wire.RichError):
                    wire.credential({"Authorization": "Bearer " + bad}, family)

    def test_duplicate_authorization_header_is_not_first_or_last_selected(self):
        class Headers:
            def getall(self, key, default):
                return ["Bearer owner", "Bearer another"]
        with self.assertRaises(wire.RichError):
            wire.one_header(Headers(), "Authorization")

    def test_canonical_hash_domain_has_no_delivery_time_or_numeric_reencoding(self):
        self.assertEqual(wire.canonical({"z": "é", "a": 1}), b'{"a":1,"z":"\xc3\xa9"}')
        first = {"z": "é", "a": 1}
        self.assertEqual(wire.digest(first), wire.digest({"a": 1, "z": "é"}))
        self.assertNotEqual(wire.digest(first), wire.digest({"a": 1, "z": "e\u0301"}))
        for value in (1.0, float("nan"), float("inf"), wire.SAFE + 1, {"é": 1}, "\ud800"):
            with self.subTest(kind=type(value)), self.assertRaises(wire.RichError):
                wire.canonical(value)
        nested = "leaf"
        for _ in range(9):
            nested = [nested]
        with self.assertRaises(wire.RichError):
            wire.canonical(nested)

    def test_only_consent_intention_is_decoded_not_an_affirmative_permission(self):
        # False intentions are valid negative inputs; no source/native permission
        # is returned by the decoder and no legacy grant/SDK action is involved.
        negative = deepcopy(self.authorize)
        negative.update(enabled=False, os_snapshot_cache=False, locked_display=False)
        self.assertEqual(wire.parse("authorize", self.raw(negative)), negative)

    def test_published_cross_client_vectors_keep_exact_original_intention_bytes(self):
        root = _PATH.parents[2] / "docs/verification/fixtures"
        packet = json.loads((root / "direct_rich_session_request_vectors_v1.json").read_text())
        self.assertEqual(len({v["id"] for v in packet["vectors"]}), 13)
        accepted = rejected = 0
        for vector in packet["vectors"]:
            with self.subTest(vector=vector["id"]):
                raw = vector["raw_utf8"].encode()
                if vector["expected"] == "ACCEPT_INTENTION_ONLY":
                    parsed = wire.parse(vector["kind"], raw)
                    self.assertEqual(wire.canonical(parsed), raw)
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), vector["canonical_sha256"])
                    accepted += 1
                else:
                    self.assertEqual(vector["expected"], "REJECT_INVALID_REQUEST")
                    with self.assertRaises(wire.RichError):
                        wire.parse(vector["kind"], raw)
                    rejected += 1
        self.assertEqual((accepted, rejected), (5, 8))

    def test_request_schema_keysets_match_each_distinct_actual_operation(self):
        root = _PATH.parents[2] / "docs/verification/fixtures"
        schema = json.loads((root / "direct_rich_session_runtime_v1.schema.json").read_text())
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        definitions = schema["$defs"]
        self.assertEqual({entry["$ref"] for entry in schema["oneOf"]},
            {"#/$defs/" + name for name in ("authorize_request", "read_request",
                "asset_request", "manage_request", "authorize_response", "read_response",
                "manage_response", "error_response", "frame")})
        self.assertEqual(set(schema["x-operation-bindings"]),
            {"authorize", "read", "asset", "status", "withdraw"})
        for operation, binding in schema["x-operation-bindings"].items():
            self.assertEqual(binding["request"], "#/$defs/" +
                ("manage_request" if operation in {"status", "withdraw"} else operation + "_request"))
        for name, expected in (("authorize_request", wire.MANAGE | wire.CONSENT),
                ("manage_request", wire.MANAGE), ("read_request", {"contract_version", "purpose_id"}),
                ("asset_request", {"contract_version", "purpose_id", "frame_id", "asset_id"})):
            with self.subTest(schema=name):
                selected = definitions[name]
                self.assertEqual(set(selected["properties"]), expected)
                self.assertEqual(set(selected["required"]), expected)
                self.assertIs(selected["additionalProperties"], False)


if __name__ == "__main__":
    unittest.main()
