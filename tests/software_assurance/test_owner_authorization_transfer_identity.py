"""Keep central Owner Authorization bound to Core across its owner transfer."""
import json
import re
import subprocess
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / '.github/workflows/owner-authorization.yml'


class CentralAuthorizationTransferIdentityTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding='utf-8')

    def test_central_dispatch_accepts_only_exact_repository_and_id(self):
        match = re.search(r'const centralDispatch = (.*);', self.workflow)
        self.assertIsNotNone(match)
        expression = match.group(1)
        cases = [
            ('pcvantol', 'djconnect', '1258575431', True),
            ('djconnect-music-dj', 'djconnect', '1258575431', True),
            ('other', 'djconnect', '1258575431', False),
            ('pcvantol', 'djconnect', '1', False),
            ('djconnect-music-dj', 'djconnect', '1', False),
            ('djconnect-music-dj', 'other', '1258575431', False),
            ('pcvantol', 'djconnect', '', False),
        ]
        script = ('const f = new Function("context", "process", "return (" + process.argv[1] + ")"); '
                  'const cases = JSON.parse(process.argv[2]); '
                  'console.log(JSON.stringify(cases.map(([owner,repo,id]) => '
                  'f({repo:{owner,repo}}, {env:{GITHUB_REPOSITORY_ID:id}}))));')
        actual = subprocess.run(['node', '-e', script, expression, json.dumps(cases)],
                                check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(actual.stdout), [case[3] for case in cases])

    def test_risk_status_requires_trusted_actions_identity_and_exact_state(self):
        match = re.search(r'const authorizationClass = (.*);', self.workflow)
        self.assertIsNotNone(match)
        cases = [
            ({'creator': {'id': 41898282}, 'state': 'failure', 'description': 'HIGH_RISK authorization required for this exact SHA'}, 'HIGH_RISK'),
            ({'creator': {'id': 41898282}, 'state': 'success', 'description': 'Not required for LOW_RISK or NORMAL_RISK'}, 'LOW_OR_NORMAL_RISK'),
            ({'creator': {'id': 1}, 'state': 'success', 'description': 'Not required for LOW_RISK or NORMAL_RISK'}, None),
            ({'creator': {'id': 41898282}, 'state': 'failure', 'description': 'Not required for LOW_RISK or NORMAL_RISK'}, None),
            ({'creator': {'id': 41898282}, 'state': 'success', 'description': 'HIGH_RISK authorization required for this exact SHA'}, None),
            (None, None),
        ]
        script = ('const f = new Function("ownerStatus", "return (" + process.argv[1] + ")"); '
                  'console.log(JSON.stringify(JSON.parse(process.argv[2]).map(([s]) => f(s))));')
        actual = subprocess.run(['node', '-e', script, match.group(1), json.dumps(cases)],
                                check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(actual.stdout), [expected for _, expected in cases])
        self.assertIn('trustedDelivery.conclusion !== "SUCCESS"', self.workflow)
        self.assertIn('classification: authorizationClass', self.workflow)
        self.assertIn('LOW/NORMAL risk verified for this exact SHA', self.workflow)

    def test_token_steps_require_the_same_core_identity_and_fixed_target(self):
        conditions = re.findall(r'^        if: (.*)$', self.workflow, re.MULTILINE)
        for target in ('pcvantol', 'djconnect-music-dj'):
            candidates = [line for line in conditions
                          if line.endswith("steps.target.outputs.repository_owner == '" + target + "'")]
            self.assertEqual(len(candidates), 1)
            condition = candidates[0]
            self.assertIn("github.repository_id == '1258575431'", condition)
            self.assertIn("github.repository == 'pcvantol/djconnect'", condition)
            self.assertIn("github.repository == 'djconnect-music-dj/djconnect'", condition)
        self.assertIn('djconnect-music-dj/djconnect)', self.workflow)
        self.assertIn('process.env.TARGET_REPOSITORY === "djconnect-music-dj/djconnect" '
                      '&& pr.data.base.repo.id !== 1258575431', self.workflow)
        self.assertIn('if (!centralDispatch && process.env.TARGET_REPOSITORY !== '
                      'process.env.GITHUB_REPOSITORY)', self.workflow)
        self.assertIn('pr.data.head.sha !== process.env.TARGET_SHA', self.workflow)
        self.assertIn('context.actor !== process.env.OWNER_LOGIN', self.workflow)


if __name__ == '__main__':
    unittest.main()
