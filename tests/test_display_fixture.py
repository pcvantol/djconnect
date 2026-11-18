"""Public transport examples must retain shape without retaining authority."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import unittest


class DisplayFixturePrivacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / "scripts/verification/verify_display_admission_http.py"
        tree = ast.parse(source.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "public_transport_fixture")
        namespace = {"json": json, "base64": base64, "hashlib": hashlib}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
        cls.clean = staticmethod(namespace["public_transport_fixture"])

    def test_actual_exporter_preserves_cross_response_binding_but_removes_credentials(self):
        original = [{"request": {"claim_secret": "S" * 43, "browser_nonce": "N" * 43, "code": "135790"},
            "response": {"issuer_epoch": "E" * 43, "grant_token": "djcd_" + "T" * 43}},
            {"request": {"issuer_epoch": "E" * 43}, "response": {"lease_revision": 0}}]
        encoded = self.clean(original)
        for private in ("S" * 43, "N" * 43, "E" * 43, "djcd_" + "T" * 43, "135790"):
            self.assertNotIn(private, encoded)
        result = json.loads(encoded)["examples"]
        self.assertEqual(result[0]["response"]["issuer_epoch"], result[1]["request"]["issuer_epoch"])
        self.assertRegex(result[0]["response"]["grant_token"], r"^djcd_[A-Za-z0-9_-]{43}$")
        self.assertEqual(result[1]["response"]["lease_revision"], 0)

    def test_replacements_depend_on_shape_and_position_not_actual_secret_bytes(self):
        self.assertEqual(self.clean([{"claim_secret": "one"}]), self.clean([{"claim_secret": "two"}]))

    def test_unknown_private_fields_and_oversized_exports_fail_closed(self):
        for name in ("device_token", "authorization", "owner_secret", "raw_audio", "prompt", "history", "memory"):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                self.clean([{"response": {name: "must never become public"}}])
        with self.assertRaises(AssertionError):
            self.clean([{"padding": "x" * (1024 * 1024)}])
