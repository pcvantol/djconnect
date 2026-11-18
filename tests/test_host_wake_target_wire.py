"""Original API18ff vectors plus causal drift probes; synthetic DATA only."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from custom_components.djconnect import host_wake_target_wire as wire
from custom_components.djconnect.direct_rich_wire import RichError


class HostWakeTargetWireTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((Path(__file__).parent / "fixtures/host_wake_api_target_18ff8f8.json").read_text())

    def decode(self, case, **changes):
        args = {"route": case["kind"], "status": case["status"], "value": case["reply"],
            "sent": case["request"], "retained": self.fixture["original"],
            "private_purpose": self.fixture["private_purpose_id"]}
        return wire.reply(**(args | changes))

    def test_all_five_original_vector_bodies_hashes_and_replies(self):
        for case in self.fixture["cases"]:
            with self.subTest(kind=case["kind"], status=case["status"]):
                self.assertEqual(wire.request_hash(case["kind"], case["request"]), case["request_sha256"])
                self.assertEqual(self.decode(case), case["reply"])
        terminal = self.decode(self.fixture["cases"][3])
        self.assertEqual((terminal["state"], terminal["operation_state"]), ("withdrawn", "registered"))
        unknown = self.decode(self.fixture["cases"][4])
        self.assertEqual(set(unknown), {"version", "purpose_id", "operation_id", "operation_state"})
        self.assertNotIn("state", unknown)

    def test_request_and_original_drift_never_accept_original_registration_ACK(self):
        case = self.fixture["cases"][0]
        for field, value in (("generation", "different"), ("revision", 2), ("native_token_sha256", "0" * 64),
                ("operation_id", "22222222-2222-4222-8222-222222222222"),
                ("target", {"host_bundle_id": "example.other.host", "installation_id": "other"})):
            original = deepcopy(self.fixture["original"])
            original[field] = value
            with self.subTest(field=field), self.assertRaises(RichError):
                self.decode(case, retained=original)

    def test_closed_reply_shapes_no_202_ready_or_bool_numbers_or_refunded_revision(self):
        for case in self.fixture["cases"]:
            for field, value in (("unexpected", True), ("purpose_id", "another"), ("operation_id", "another")):
                changed = deepcopy(case["reply"])
                changed[field] = value
                with self.subTest(kind=case["kind"], field=field), self.assertRaises(RichError):
                    self.decode(case, value=changed)
        case = self.fixture["cases"][0]
        for field, value in (("revision", True), ("revision", 0), ("generation", None),
                ("expires_at_ms", True), ("transport_expires_at_ms", True), ("provider_status", True)):
            changed = deepcopy(case["reply"])
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(RichError):
                self.decode(case, value=changed)
        unknown = self.fixture["cases"][4]
        with self.assertRaises(RichError):
            self.decode(unknown, status=200)
        with self.assertRaises(RichError):
            self.decode(case, status=202)

    def test_unknown_or_expired_reply_cannot_acknowledge_revoke(self):
        case = self.fixture["cases"][3]
        changed = deepcopy(case["reply"])
        changed["state"] = "expired"
        with self.assertRaises(RichError):
            self.decode(case, value=changed)
        with self.assertRaises(RichError):
            self.decode(case, status=202, value=self.fixture["cases"][4]["reply"])


if __name__ == "__main__":
    unittest.main()
