import base64
import json
import unittest
from tools.verification.ghcr_write_scope_probe import REPOSITORY, granted_push


def token(claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "header." + payload + ".signature"


class GHCRWriteScopeProbeTests(unittest.TestCase):
    def test_accepts_only_correct_repository_push_claim(self):
        self.assertTrue(granted_push(token({"access": [{"type": "repository", "name": REPOSITORY, "actions": ["pull", "push"]}]})))
        for item in ({"type": "repository", "name": REPOSITORY, "actions": ["pull"]},
                     {"type": "repository", "name": "other/repo", "actions": ["push"]},
                     {"type": "other", "name": REPOSITORY, "actions": ["push"]}):
            with self.subTest(item=item):
                self.assertFalse(granted_push(token({"access": [item]})))
        for actions in ("push", None, {"push": True}, ["push", 1]):
            with self.subTest(actions=actions):
                self.assertFalse(granted_push(token({"access": [{"type": "repository", "name": REPOSITORY, "actions": actions}]})))
        self.assertFalse(granted_push("malformed"))
