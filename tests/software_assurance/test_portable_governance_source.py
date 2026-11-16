"""Verify governance policy checkout stays bound to the immutable Core identity."""
import json
import re
import subprocess
import unittest
from pathlib import Path


class PortableGovernanceSourceTests(unittest.TestCase):
    def test_repository_resolution_accepts_only_the_two_names_for_the_same_public_id(self):
        workflow = (Path(__file__).resolve().parents[2] / '.github/workflows/software-assurance-governance.yml').read_text()
        match = re.search(r'            if \((repo\.id !== .*?)\) throw new Error', workflow)
        self.assertIsNotNone(match)
        cases = [
            ({'id': 1258575431, 'private': False, 'full_name': 'pcvantol/djconnect'}, False),
            ({'id': 1258575431, 'private': False, 'full_name': 'djconnect-music-dj/djconnect'}, False),
            ({'id': 1, 'private': False, 'full_name': 'djconnect-music-dj/djconnect'}, True),
            ({'id': 1258575431, 'private': True, 'full_name': 'pcvantol/djconnect'}, True),
            ({'id': 1258575431, 'private': False, 'full_name': 'other/djconnect'}, True),
        ]
        js = ('const f = new Function("repo", "return (" + process.argv[1] + ")"); '
              'console.log(JSON.stringify(JSON.parse(process.argv[2]).map(([repo]) => f(repo))));')
        actual = subprocess.run(['node', '-e', js, match.group(1), json.dumps(cases)],
                                check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(actual.stdout), [expected for _, expected in cases])
        self.assertIn('repository: ${{ steps.canonical-source.outputs.repository }}', workflow)
        self.assertIn('ref: 3d7d24a84b3aaacb8f2fb229e09c33da85e0545d', workflow)


if __name__ == '__main__':
    unittest.main()
