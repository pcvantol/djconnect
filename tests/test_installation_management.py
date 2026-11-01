"""Closed management request grammar and original real-HA proof joins."""
import hashlib
import json
from pathlib import Path
import unittest

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()

from custom_components.djconnect import installation_management as management  # noqa: E402


class ManagementGrammarTests(unittest.TestCase):
    def body(self, **changes):
        return {"contract_version": 1,
            "operation_id": "00000000-0000-4000-8000-000000000001",
            "action": "prepare_custody", "policy_id": "software_p256_ha_file_v1",
            "acknowledgement": "preparation_only_no_key_effect", **changes}

    def test_only_closed_preparation_action_and_original_uuid_are_accepted(self):
        request = self.body()
        self.assertEqual(management.parse(json.dumps(request).encode()), request["operation_id"])
        self.assertTrue(management.InstallationManagementPrepareView.requires_auth)
        self.assertFalse(hasattr(management.ManagementPreparations, "generate"))
        self.assertFalse(hasattr(management.ManagementPreparations, "sign"))

    def test_other_actions_authority_fields_and_noncanonical_ids_are_denied(self):
        for change in [{"action": "generate"}, {"policy_id": "caller_policy"},
                       {"acknowledgement": True}, {"contract_version": True},
                       {"contract_version": 1.0}, {"operation_id": 1},
                       {"operation_id": "00000000-0000-1000-8000-000000000001"},
                       {"operation_id": "00000000000040008000000000000001"},
                       {"owner": True}, {"private_key": "SYNTHETIC_NOT_A_KEY"},
                       {"session_id": "must_not_bind_management_to_session"}]:
            with self.subTest(change=change), self.assertRaises(management.ManagementError) as error:
                management.parse(json.dumps(self.body(**change)).encode())
            self.assertEqual(error.exception.status, 400)

    def test_duplicate_keys_nonfinite_utf8_and_wrong_container_are_closed(self):
        encoded = json.dumps(self.body()).encode()
        for raw in [b'{"contract_version":1,' + encoded[1:], b'{"a":NaN}',
                    b'{"a":Infinity}', b'{"a":"\xff"}', b'[]', b'null',
                    b'{"a":{"duplicate":1,"duplicate":2}}', b'[' * 1500]:
            with self.subTest(raw=raw[:32]), self.assertRaises(management.ManagementError) as error:
                management.parse(raw)
            self.assertEqual(error.exception.status, 400)

    def test_original_actual_HA_receipt_binds_current_source_and_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / "examples/client_contracts/installation_management_preparation_v1/actual-ha-management-preparation.json").read_text())
        original = proof["original_receipt"]
        self.assertEqual(len(original["source_sha256"]), 298)
        for name, digest in original["source_sha256"].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((root / proof["harness"]).read_bytes()).hexdigest(), proof["harness_sha256"])
        self.assertEqual(hashlib.sha256((json.dumps(original, indent=2) + "\n").encode()).hexdigest(), proof["original_receipt_sha256"])
        self.assertTrue(original["actual_HA_auth_users_tokens_middleware"])
        self.assertFalse(original["real_service_key_or_custody_effect"])
        self.assertFalse(original["provider_or_device_effect"])
        self.assertFalse(original["native_or_push_acceptance"])
        cases = {case["case"] for case in original["cases"]}
        self.assertIn("real OptionsFlow failed temporary entry ABA retires pending and prepared management", cases)
        self.assertIn("runtime setter ABA retires all siblings despite cleanup failure", cases)
        self.assertEqual(proof["same_test_pre_hook_causal_RED"]["test_sha256"], proof["harness_sha256"])
        self.assertEqual(proof["same_test_pre_hook_causal_RED"]["exit_code"], 1)
        self.assertEqual(proof["installed"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
