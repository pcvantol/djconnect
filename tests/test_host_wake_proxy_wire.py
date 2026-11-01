"""Original public cross-language vectors and hostile raw HTTP body controls."""
import base64
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "djc_host_wake_wire_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components/djconnect")]
sys.modules[PACKAGE] = package
spec = importlib.util.spec_from_file_location(PACKAGE + ".host_wake_proxy_wire",
    ROOT / "custom_components/djconnect/host_wake_proxy_wire.py")
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
VECTORS = json.loads((ROOT / "docs/verification/fixtures/host_wake_core_proxy_v1_vectors.json").read_text())


class HostWakeProxyWireTests(unittest.TestCase):
    def test_original_cross_language_preimages_all_seven_routes(self):
        cases = VECTORS["positive_shape_vectors"]
        self.assertEqual({case["route"] for case in cases}, wire.OPERATIONS)
        for case in cases:
            operation, request = case["route"], case["request"]
            with self.subTest(operation=operation):
                self.assertEqual(wire.parse(operation, wire.request_bytes(operation, request)), request)
                preimage = wire.canonical(["DJC-HOST-WAKE-CORE-REQUEST-V1", "POST", wire.BASE + operation, request])
                self.assertEqual(preimage.decode(), case["request_sha256_preimage_utf8"])
                self.assertEqual(wire.request_sha256(operation, request), case["reply"]["request_sha256"])

    def test_missing_unknown_private_and_cross_route_bodies_rejected(self):
        for case in VECTORS["positive_shape_vectors"]:
            operation, request = case["route"], case["request"]
            for key in request:
                with self.subTest(operation=operation, missing=key), self.assertRaises(wire.RichError):
                    wire.parse(operation, wire.canonical({k: v for k, v in request.items() if k != key}))
            for key in ("owner", "authorization_id", "issuer_operation_id", "credential", "clock_qualified"):
                with self.subTest(operation=operation, added=key), self.assertRaises(wire.RichError):
                    wire.parse(operation, wire.canonical(request | {key: "caller-data"}))
        request = VECTORS["positive_shape_vectors"][0]["request"]
        for operation in ("../prepare", "prepare?x=1", "prepare/", "authorize", "", "PREPARE"):
            with self.subTest(operation=operation), self.assertRaises(wire.RichError):
                wire.parse(operation, wire.canonical(request))

    def test_untrusted_raw_numeric_utf8_duplicate_depth_and_size(self):
        raw = wire.canonical(VECTORS["positive_shape_vectors"][0]["request"])
        cases = [raw.replace(b'"contract_version":1', b'"contract_version":' + value)
            for value in (b'true', b'1.0', b'1e0', b'-0', b'9007199254740992', b'NaN')]
        cases += [b'\xef\xbb\xbf' + raw, raw + b'\xff', raw + b'{}', b' ' * 16385,
            b'{' + b'"contract_version":1,' + raw[1:],
            b'{' + b'"\\u0063ontract_version":1,' + raw[1:],
            b'[' * 500 + b'0' + b']' * 500,
            raw[:-1] + b',"bad":"\\ud800"}',
            raw.replace(b'"target":{', b'"target":{"host_bundle_id":"duplicate",')]
        for index, value in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(wire.RichError):
                wire.parse("prepare", value)

    def test_canonical_base64_size_pad_bits_and_proof_type(self):
        for minimum, maximum in ((1, 1024), (1, 9216), (16, 2048)):
            for size in (minimum, maximum):
                data = bytes(range(256)) * (size // 256) + bytes(range(size % 256))
                self.assertEqual(wire.decoded_base64(base64.b64encode(data).decode(), minimum, maximum), data)
            for size in (minimum - 1, maximum + 1):
                with self.assertRaises(wire.RichError):
                    wire.decoded_base64(base64.b64encode(b'x' * size).decode(), minimum, maximum)
        for encoded in ("AB==", "AA=", "AA===", "AA==\n", "_w==", "é", True, []):
            with self.subTest(encoded=encoded), self.assertRaises(wire.RichError):
                wire.decoded_base64(encoded, 1, 1024)
        request = next(c["request"] for c in VECTORS["positive_shape_vectors"] if c["route"] == "native/complete")
        for kind in ("assertion", "app_attest_assertion ", True, []):
            invalid = deepcopy(request)
            invalid["native_proof"]["kind"] = kind
            with self.subTest(kind=kind), self.assertRaises(wire.RichError):
                wire.parse("native/complete", wire.canonical(invalid))

    def test_same_body_has_route_bound_correlation_and_is_not_authority(self):
        request = next(c["request"] for c in VECTORS["positive_shape_vectors"] if c["route"] == "status")
        hashes = {wire.request_sha256(route, request) for route in ("status", "withdraw", "native/challenge")}
        self.assertEqual(len(hashes), 3)
        # Pure DATA decoder cannot manufacture the context/permission it lacks.
        self.assertFalse(hasattr(wire, "authorize"))


if __name__ == "__main__":
    unittest.main()
