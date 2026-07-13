import unittest

from tools.trusted_delivery.owner_authorization import AuthorizationError, evaluate


def request(**overrides):
    base = {
        "repository": "pcvantol/djconnect",
        "branch": "main",
        "pr_number": 88,
        "candidate_sha": "a" * 40,
        "current_head_sha": "a" * 40,
        "classification": "HIGH_RISK",
        "trusted_delivery_status": "PASS",
        "authorization_status": "REQUIRED",
        "owner": "pcvantol",
        "github_actor": "pcvantol",
        "workflow_run_id": "123",
    }
    base.update(overrides)
    return base


class OwnerAuthorizationTest(unittest.TestCase):
    def test_high_risk_current_candidate_is_authorized(self):
        evidence = evaluate(request())
        self.assertEqual(evidence["result"], "PASS")
        self.assertEqual(evidence["candidate_sha"], "a" * 40)

    def test_low_and_normal_are_not_authorizable(self):
        for classification in ("LOW_RISK", "NORMAL_RISK"):
            with self.assertRaises(AuthorizationError):
                evaluate(request(classification=classification, authorization_status="NOT_REQUIRED"))

    def test_high_risk_blocks_without_technical_qualification(self):
        with self.assertRaises(AuthorizationError):
            evaluate(request(trusted_delivery_status="FAIL"))

    def test_changed_sha_invalidates_authorization(self):
        with self.assertRaises(AuthorizationError):
            evaluate(request(current_head_sha="b" * 40))
