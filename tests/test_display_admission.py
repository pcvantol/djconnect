"""B authority contract invariants; unit clocks are not live HA acceptance."""
import importlib.util
from pathlib import Path
import secrets
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("display_state_unit", Path(__file__).resolve().parents[1] /
                                            "custom_components/djconnect/display_admission.py")
state = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = state
spec.loader.exec_module(state)


class DisplayAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.live = {"one": True, "two": True}
        self.manager = state.DisplayAdmissionState(lambda: self.now)
        self.owner = self.owner_for("one")

    def owner_for(self, entry, profile="profile", session="session"):
        return state.DisplayOwnerBinding(profile, session, entry, "stamp-" + entry, lambda: self.live.get(entry, True))

    def claim(self, source="source"):
        nonce = secrets.token_urlsafe(32)
        result = self.manager.create_claim(source=source, browser_nonce=nonce)
        return result, {key: result[key] for key in ("issuer_epoch", "claim_id", "claim_secret", "browser_generation")} | {"browser_nonce": nonce}

    def approve(self, claim, owner=None, share=None):
        return self.manager.approve(owner=owner or self.owner, issuer_epoch=claim["issuer_epoch"],
            claim_id=claim["claim_id"], browser_generation=claim["browser_generation"], code=claim["code"],
            share=share or {"mode": "create", "consent": True, "lifetime_seconds": 7200})

    @staticmethod
    def share(approval):
        return {"mode": "existing", "share_id": approval["share_id"], "share_generation": 1}

    @staticmethod
    def grant(admitted):
        return {"token": admitted["grant_token"], "display_id": admitted["display_id"], "issuer_epoch": admitted["issuer_epoch"]}

    def test_code_is_not_authority_and_collection_is_secret_bound_once(self):
        claim, browser = self.claim()
        self.assertEqual(self.manager.collect(**browser), {"success": True, "state": "pending"})
        for key in browser:
            with self.subTest(field=key), self.assertRaises(state.DisplayAdmissionError):
                self.manager.collect(**(browser | {key: secrets.token_urlsafe(32)}))
        resolved = self.manager.resolve(code=claim["code"], owner=self.owner)
        self.assertEqual(resolved["claim_id"], claim["claim_id"])
        self.assertNotIn("claim_secret", resolved)
        approval = self.approve(claim)
        self.assertNotIn("grant_token", approval)
        admitted = self.manager.collect(**browser)
        self.assertFalse(admitted["capabilities"]["session_end"])
        self.assertFalse(admitted["capabilities"]["audience_signals"])
        self.assertNotIn("end_grant", admitted)
        self.assertNotIn("broadcast_token", admitted)
        self.assertNotIn(admitted["grant_token"], repr(self.manager._displays))
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.collect(**browser)

    def test_approval_retry_before_and_after_collection_does_not_create_or_extend(self):
        claim, browser = self.claim()
        approval = self.approve(claim)
        deadline = self.manager._shares[approval["share_id"]].deadline
        self.now += 10
        self.assertEqual(self.approve(claim)["display_id"], approval["display_id"])
        self.manager.collect(**browser)
        self.now += 10
        self.assertEqual(self.approve(claim)["display_id"], approval["display_id"])
        self.assertEqual(self.manager._shares[approval["share_id"]].deadline, deadline)
        self.assertEqual(len(self.manager._displays), 1)

    def test_expiry_equality_cancel_and_new_epoch_never_retarget_old_claim(self):
        claim, browser = self.claim()
        self.now += 120
        with self.assertRaises(state.DisplayAdmissionError):
            self.approve(claim)
        self.assertFalse(self.manager._shares)
        claim, browser = self.claim()
        self.manager.cancel(**browser)
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.collect(**browser)
        claim, browser = self.claim()
        old_epoch = self.manager.issuer_epoch
        self.manager.clear()
        self.assertNotEqual(self.manager.issuer_epoch, old_epoch)
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.collect(**browser)

    def test_claim_capacity_denies_without_evicting_existing_receiver(self):
        claims = [self.claim()[0] for _ in range(3)]
        with self.assertRaises(state.DisplayAdmissionError) as failure:
            self.claim()
        self.assertEqual(failure.exception.status, 429)
        for number in range(61):
            self.claim("source-" + str(number))
        self.assertEqual(len(self.manager._claims), 64)
        with self.assertRaises(state.DisplayAdmissionError):
            self.claim("new-source")
        self.assertTrue(all(c["claim_id"] in self.manager._claims for c in claims))

    def test_failed_attempts_are_bounded_by_claim_and_authenticated_owner(self):
        for number in range(2):
            claim, _browser = self.claim("source-" + str(number))
            wrong = "000000" if claim["code"] != "000000" else "999999"
            for _ in range(5):
                with self.assertRaises(state.DisplayAdmissionError):
                    self.manager.approve(owner=self.owner, issuer_epoch=claim["issuer_epoch"],
                        claim_id=claim["claim_id"], browser_generation=claim["browser_generation"], code=wrong,
                        share={"mode": "create", "consent": True})
            self.assertNotIn(claim["claim_id"], self.manager._claims)
        with self.assertRaises(state.DisplayAdmissionError) as failure:
            self.manager.resolve(code="123456", owner=self.owner)
        self.assertEqual(failure.exception.status, 429)
        self.now += 60
        claim, _browser = self.claim()
        self.assertEqual(self.manager.resolve(code=claim["code"], owner=self.owner)["claim_id"], claim["claim_id"])

    def test_explicit_consent_bounded_lifetime_and_no_effect_fields(self):
        claim, _browser = self.claim()
        for change in ({"consent": False}, {"lifetime_seconds": True}, {"lifetime_seconds": 119},
                       {"lifetime_seconds": 28801}, {"end_grant": "no"}):
            with self.subTest(change=change), self.assertRaises(state.DisplayAdmissionError):
                self.approve(claim, share={"mode": "create", "consent": True, "lifetime_seconds": 120} | change)
            self.assertFalse(self.manager._shares)
        self.approve(claim)

    def test_profile_session_share_and_issuer_fences(self):
        claim, browser = self.claim()
        approval = self.approve(claim)
        admitted = self.manager.collect(**browser)
        for owner in (self.owner_for("two", profile="other"), self.owner_for("two", session="other")):
            other, _b = self.claim("new-" + owner.profile_id + owner.session_id)
            with self.assertRaises(state.DisplayAdmissionError):
                self.approve(other, owner=owner, share=self.share(approval))
        for change in ({"token": "broadcast-token"}, {"issuer_epoch": "other"}, {"display_id": "other"}, {"token": None}):
            with self.subTest(change=change), self.assertRaises(state.DisplayAdmissionError):
                self.manager.authorize(**(self.grant(admitted) | change))

    def test_reservations_count_toward_share_capacity_before_collection(self):
        claim, _browser = self.claim()
        approval = self.approve(claim)
        for number in range(7):
            other, _b = self.claim("source-" + str(number))
            self.approve(other, share=self.share(approval))
        other, _b = self.claim("ninth")
        with self.assertRaises(state.DisplayAdmissionError) as failure:
            self.approve(other, share=self.share(approval))
        self.assertEqual(failure.exception.status, 429)
        self.assertIsNone(self.manager._claims[other["claim_id"]].owner)

    def test_read_is_pure_and_renew_retry_preserves_committed_deadline(self):
        claim, browser = self.claim()
        self.approve(claim)
        admitted = self.manager.collect(**browser)
        binding = self.grant(admitted)
        self.now += 20
        first = self.manager.renew(renew_sequence=1, **binding)
        self.assertEqual(first["lease_expires_in"], 60)
        self.now += 5
        duplicate = self.manager.renew(renew_sequence=1, **binding)
        self.assertEqual(duplicate["lease_expires_in"], 55)
        display = self.manager.authorize(**binding)
        deadline = display.lease_deadline
        for _ in range(5):
            self.manager.authorize(**binding)
        self.assertEqual(display.lease_deadline, deadline)
        for sequence in (0, 3, True):
            with self.assertRaises(state.DisplayAdmissionError):
                self.manager.renew(renew_sequence=sequence, **binding)
        self.now = deadline
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.renew(renew_sequence=2, **binding)

    def test_share_absolute_deadline_cannot_be_renewed(self):
        claim, browser = self.claim()
        self.approve(claim, share={"mode": "create", "consent": True, "lifetime_seconds": 120})
        admitted = self.manager.collect(**browser)
        binding = self.grant(admitted)
        for sequence in range(1, 6):
            self.now = 100 + sequence * 20
            self.manager.renew(renew_sequence=sequence, **binding)
            self.assertLessEqual(self.manager.authorize(**binding).lease_deadline, 220)
        self.now = 220
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.authorize(**binding)
        self.assertFalse(self.manager._shares)

    def test_approver_revocation_only_own_displays_creator_revokes_share(self):
        claim, browser = self.claim()
        approval = self.approve(claim)
        first = self.manager.collect(**browser)
        other, second_browser = self.claim("another-source")
        self.approve(other, owner=self.owner_for("two"), share=self.share(approval))
        second = self.manager.collect(**second_browser)
        self.manager.revoke_entry("two")
        self.manager.authorize(**self.grant(first))
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.authorize(**self.grant(second))
        self.manager.revoke_entry("one")
        self.assertFalse(self.manager._shares)
        self.assertFalse(self.manager._displays)

    def test_leave_and_transport_failure_never_end_owner_or_share(self):
        claim, browser = self.claim()
        approval = self.approve(claim)
        first = self.manager.collect(**browser)
        def broken_transport():
            raise RuntimeError("synthetic failed writer wake")
        self.manager.authorize(**self.grant(first)).invalidated = broken_transport
        self.manager.leave(**self.grant(first))
        self.assertIn(approval["share_id"], self.manager._shares)
        self.assertTrue(self.owner.valid())
        self.assertFalse(self.manager._displays)

    def test_same_profile_other_device_may_explicitly_close_share(self):
        claim, browser = self.claim()
        approval = self.approve(claim)
        self.manager.collect(**browser)
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.revoke(owner=self.owner_for("two", profile="other"), share_id=approval["share_id"])
        self.manager.revoke(owner=self.owner_for("two"), share_id=approval["share_id"])
        self.assertFalse(self.manager._shares)
        self.assertFalse(self.manager._displays)

    def test_session_end_and_source_binding_loss_invalidate_without_restore(self):
        claim, browser = self.claim()
        self.approve(claim)
        admitted = self.manager.collect(**browser)
        self.live["one"] = False
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.authorize(**self.grant(admitted))
        self.live["one"] = True
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.authorize(**self.grant(admitted))
        claim, browser = self.claim()
        self.approve(claim)
        self.manager.revoke_session("session")
        with self.assertRaises(state.DisplayAdmissionError):
            self.manager.collect(**browser)

    def test_entropy_failure_before_commit_does_not_open_share(self):
        claim, _browser = self.claim()
        with patch.object(state.secrets, "token_urlsafe", side_effect=["share-id", RuntimeError("fixture")]):
            with self.assertRaises(RuntimeError):
                self.approve(claim)
        self.assertFalse(self.manager._shares)
        self.assertIsNone(self.manager._claims[claim["claim_id"]].owner)
