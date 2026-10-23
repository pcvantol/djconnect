"""Synthetic local values only. No network, key, credential adoption or owner."""

import unittest
from dataclasses import replace
from copy import deepcopy

from tests.test_profile_dj_settings_persistence import operation
from custom_components.djconnect.surface_push_contract import SurfacePushError

from custom_components.djconnect import surface_issuer_responses as m

START = 1792700000000


class ReplyTests(unittest.TestCase):
    def test_api_server_deadline_after_network_latency_is_locally_capped_not_renewed(self):
        # API2a6 starts its120s at its own receipt, after the original Core
        # reservation/sign/transport. A valid deadline is not necessarily <=
        # Core's pre-await request+120s. Core must retain that earlier cap.
        reply = self.challenge | {'expires_at_ms': START + 120125}
        result = self.challenge_call(reply, now_ms=START + 250, monotonic=100.25)
        self.assertEqual(result.expires_at_ms, START + 120000)
        self.assertEqual(result.request_monotonic, 100.0)

    def setUp(self):
        self.e = m.ExpectedIssuerReply(
            "synthetic_delegation",
            operation(START),
            "a" * 64,
            "b" * 64,
            START + 3600000,
            START,
            100.0,
        )
        self.base = {
            "contract_version": 1,
            "success": True,
            "operation_id": self.e.operation_id,
            "delegation_id": self.e.delegation_id,
            "delegation_revision": 1,
            "expires_at_ms": self.e.original_grant_expires_ms,
            "replayed": False,
        }
        self.challenge = self.base | {
            "scope_digest": self.e.scope_digest,
            "key_thumbprint": self.e.key_thumbprint,
            "challenge_id": "synthetic_challenge",
            "nonce": "A" * 43,
            "state": "challenge",
            "expires_at_ms": START + 120000,
        }
        self.issue = self.base | {
            "scope_digest": self.e.scope_digest,
            "capability_id": "synthetic_capability",
            "credential": "djcs_" + "A" * 43,
            "state": "issued",
        }
        self.status = self.base | {
            "success": False,
            "scope_digest": self.e.scope_digest,
            "capability_id": None,
            "credential_state": "unavailable",
            "state": "unknown",
        }
        self.withdraw = self.base | {"state": "withdrawn"}

    def challenge_call(self, reply=None, **kw):
        args = {
            "status": 200,
            "request_wall_ms": START,
            "request_monotonic": 100.0,
            "now_ms": START + 1000,
            "monotonic": 101.0,
        } | kw
        return m.challenge_winner(reply or self.challenge, self.e, **args)

    def issue_call(self, reply=None, **kw):
        challenge = m.ChallengeSecret(
            self.e, "synthetic_challenge", "A" * 43, START + 120000, START, 100.0
        )
        return m.issue_winner(
            reply or self.issue,
            self.e,
            **(
                {"challenge": challenge, "status": 200, "now_ms": START + 1000, "monotonic": 101.0}
                | kw
            ),
        )

    def test_exact_winners_and_secret_free_repr(self):
        c = self.challenge_call()
        i = self.issue_call()
        self.assertEqual(c.challenge_id, "synthetic_challenge")
        self.assertEqual(i.capability_id, "synthetic_capability")
        self.assertNotIn(c.nonce, repr(c))
        self.assertNotIn(i.bearer, repr(i))

    def test_expired_status_and_withdrawal_stay_unavailable(self):
        self.assertEqual(
            m.status_unavailable(self.status, self.e), {"available": False, "state": "unknown"}
        )
        self.assertEqual(
            m.withdrawal_ack(self.withdraw, self.e), {"available": False, "state": "withdrawn"}
        )

    def test_status_and_duplicate_can_never_be_issue_winner(self):
        for reply in [
            self.status,
            self.issue | {"replayed": True},
            self.issue | {"success": False},
            self.issue | {"state": "withdrawn"},
        ]:
            with self.subTest(reply=tuple(reply)), self.assertRaises(SurfacePushError):
                self.issue_call(reply)
        with self.assertRaises(SurfacePushError):
            self.issue_call(status=202)

    def test_closed_variants_no_default_fields_or_extra_keys(self):
        for good, call in [
            (self.challenge, self.challenge_call),
            (self.issue, self.issue_call),
            (self.status, lambda r: m.status_unavailable(r, self.e)),
            (self.withdraw, lambda r: m.withdrawal_ack(r, self.e)),
        ]:
            for key in good:
                bad = deepcopy(good)
                del bad[key]
                with self.subTest(field=key), self.assertRaises((SurfacePushError, KeyError)):
                    call(bad)
            with self.assertRaises(SurfacePushError):
                call(good | {"unexpected": True})

    def test_exact_identity_scope_and_boolean_integer_types(self):
        for patch in [
            {"contract_version": True},
            {"delegation_revision": True},
            {"delegation_id": "other"},
            {"operation_id": operation(START + 1)},
            {"scope_digest": "c" * 64},
            {"replayed": 0},
            {"success": 1},
            {"expires_at_ms": True},
        ]:
            with self.subTest(patch=patch), self.assertRaises(SurfacePushError):
                self.issue_call(self.issue | patch)

    def test_issue_expiry_is_exact_original_grant_and_monotonic(self):
        with self.assertRaises(SurfacePushError):
            self.issue_call(self.issue | {"expires_at_ms": self.e.original_grant_expires_ms + 1})
        with self.assertRaises(SurfacePushError):
            self.issue_call(now_ms=self.e.original_grant_expires_ms)
        with self.assertRaises(SurfacePushError):
            self.issue_call(monotonic=3700.0)

    def test_challenge_original_pre_effect_window_not_response_time(self):
        capped = self.challenge_call(self.challenge | {"expires_at_ms": START + 121000})
        self.assertEqual(capped.expires_at_ms, START + 120000)
        # A server deadline beyond even receipt+120s remains invalid.
        with self.assertRaises(SurfacePushError):
            self.challenge_call(self.challenge | {"expires_at_ms": START + 121001})
        with self.assertRaises(SurfacePushError):
            self.challenge_call(now_ms=START + 120000)
        with self.assertRaises(SurfacePushError):
            self.challenge_call(monotonic=220.0)
        late = self.challenge | {"expires_at_ms": START + 120000}
        with self.assertRaises(SurfacePushError):
            self.challenge_call(late, now_ms=START + 119000, monotonic=220.0)

    def test_clock_rollback_cannot_extend_original_phase(self):
        with self.assertRaises(SurfacePushError):
            self.challenge_call(now_ms=START - 1, monotonic=99.0)
        with self.assertRaises(SurfacePushError):
            self.issue_call(now_ms=START - 1, monotonic=99.0)

    def test_issue_response_after_original_challenge_window_cannot_adopt(self):
        with self.assertRaises(SurfacePushError):
            self.issue_call(now_ms=START + 120000, monotonic=219.0)
        with self.assertRaises(SurfacePushError):
            self.issue_call(now_ms=START + 119000, monotonic=220.0)

    def test_nonce_cannot_move_to_another_original_capture(self):
        other = replace(self.e)
        challenge = m.ChallengeSecret(
            other, "synthetic_challenge", "A" * 43, START + 120000, START, 100.0
        )
        with self.assertRaises(SurfacePushError):
            self.issue_call(challenge=challenge)

    def test_canonical_nonce_and_bearer_only(self):
        for nonce in ["A" * 43 + "=", "A" * 42 + "B", "A" * 42, None]:
            with self.subTest(nonce=nonce), self.assertRaises(SurfacePushError):
                self.challenge_call(self.challenge | {"nonce": nonce})
        for token in ["djci_" + "A" * 43, "djcs_" + "A" * 43 + "=", "djcs_" + "A" * 42 + "B", None]:
            with self.subTest(token=token), self.assertRaises(SurfacePushError):
                self.issue_call(self.issue | {"credential": token})

    def test_expired_metadata_does_not_accept_bearer_or_true_success(self):
        for patch in [
            {"credential": "djcs_" + "A" * 43},
            {"success": True},
            {"credential_state": "available"},
            {"expires_at_ms": self.e.original_grant_expires_ms + 1},
        ]:
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                m.status_unavailable(self.status | patch, self.e)

    def test_future_uuid_boundary_is_original_thirty_seconds_for_challenge(self):
        for offset in (30000, 30001):
            self.e = replace(self.e, operation_id=operation(START + offset))
            self.challenge["operation_id"] = self.e.operation_id
            if offset == 30000:
                self.challenge_call(now_ms=START, monotonic=100.0)
            else:
                with self.assertRaises(SurfacePushError):
                    self.challenge_call(now_ms=START, monotonic=100.0)

    def test_future_uuid_boundary_cannot_bypass_original_anchor_in_issue(self):
        for offset in (30000, 30001):
            self.e = replace(self.e, operation_id=operation(START + offset))
            self.issue["operation_id"] = self.e.operation_id
            if offset == 30000:
                self.issue_call(now_ms=START, monotonic=100.0)
            else:
                with self.assertRaises(SurfacePushError):
                    self.issue_call(now_ms=START, monotonic=100.0)

    def test_no_runtime_or_effect_owner_supplied(self):
        for key in [
            "post_once",
            "SurfacePurposeCredential",
            "enrol",
            "sign",
            "async_get_clientsession",
        ]:
            self.assertFalse(hasattr(m, key))


if __name__ == "__main__":
    unittest.main()
