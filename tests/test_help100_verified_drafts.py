"""Cost-free new-source admission negatives; consumed executions stay immutable."""
from datetime import timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools/verification/run_help100_verified_drafts_20261025.py'
SPEC = importlib.util.spec_from_file_location('verified_drafts_help100_runner', RUNNER)
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


class VerifiedDraftsOnceAdmissionTests(unittest.TestCase):
    def context(self):
        return {'GITHUB_REPOSITORY': 'pcvantol/djconnect', 'GITHUB_REF': 'refs/heads/main',
            'GITHUB_WORKFLOW_REF': r.WORKFLOW, 'GITHUB_ACTOR': 'pcvantol',
            'GITHUB_TRIGGERING_ACTOR': 'pcvantol', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
            'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1', 'DJC_HELP100_GRANT': r.GRANT,
            'GITHUB_RUN_ID': '123456', 'GITHUB_SHA': 'a' * 40, 'DJC_EXPECTED_MAIN_SHA': 'a' * 40}

    def test_only_new_grant_once_original_actor_main_sha_and_window(self):
        context = self.context()
        self.assertEqual(r.admit(context, r.START)['source'], 'a' * 40)
        for field, wrong in [('DJC_HELP100_GRANT', 'DJC-CORE-HELP100-REMEDIATION-20261025-ONCE'),
                ('DJC_HELP100_GRANT', 'DJC-CORE-HELP100-DIRECT-HUMAN-20261024-FRESH'),
                ('GITHUB_RUN_NUMBER', '2'), ('GITHUB_RUN_ATTEMPT', '2'),
                ('GITHUB_REF', 'refs/heads/unreviewed'), ('GITHUB_ACTOR', 'another-actor'),
                ('DJC_EXPECTED_MAIN_SHA', 'b' * 40)]:
            with self.subTest(field=field, wrong=wrong), self.assertRaises(ValueError):
                r.admit(context | {field: wrong}, r.START)
        for stamp in (r.START - timedelta(seconds=1), r.LAST_START):
            with self.assertRaises(ValueError):
                r.admit(context, stamp)

    def test_actual_new_source_maps_and_original_base_seam_never_substitute_old_execution(self):
        # Unit CI is shallow; actual paid admission must independently verify
        # every original full-history Git blob before secret access.
        frozen = json.loads(RUNNER.with_name('help100_verified_drafts_content_20261025.json').read_text())
        with patch.object(r, 'verify_original_base'), \
             patch.object(r.safe, 'product_hashes', return_value=frozen['product_hashes']), \
             patch.object(r.safe, 'profile_source_hashes', return_value=frozen['profile_hashes']):
            pin = r.maps(ROOT)
        self.assertEqual(pin['source_base'], 'ec66d96e431d1982a03e76f08536f7bbcd6ed6a1')
        self.assertEqual(len(pin['product_hashes']), 264)
        self.assertEqual(len(pin['profile_hashes']), 241)
        self.assertEqual(len(pin['reviewed_product_changes']), 5)
        changed = dict(pin['product_hashes'])
        changed[next(iter(changed))] = '0' * 64
        with patch.object(r, 'verify_original_base'), patch.object(r.safe, 'product_hashes', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'PRODUCT_CHANGED'):
                r.maps(ROOT)

    def test_previous_consumed_runner_workflow_and_map_remain_exact(self):
        expected = {
            '.github/workflows/help100-remediation-20261025.yml': '70fb67fa660b4a74c3f55e4943d505c7ad62c77e5b687f370e2f872c4e5404c8',
            'tools/verification/run_help100_remediation_20261025.py': '097743e87d1c3960ea0dff8ff89b5788ac12ac5bf27af4c972a51b946d566820',
            'tools/verification/help100_remediation_content_20261025.json': '85feb5dcd13a990f8abff10dbef277c3c6ac7112e0fbd2f014201192f3843c0d'}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)
        text = (ROOT / '.github/workflows/help100-verified-drafts-20261025.yml').read_text()
        self.assertEqual(text.count('ref: ${{ github.sha }}'), 2)
        self.assertEqual(text.count('secrets.DJCONNECT_GOLDEN_OPENAI_API_KEY'), 1)
        self.assertNotIn('continue-on-error', text)
        self.assertNotIn('private.log\n', text)
        self.assertNotIn('private-work', text)
        self.assertNotIn('\n  push:', text)
        self.assertEqual(r.MAX_SECONDS, 1800)
        self.assertEqual(r.profile(ROOT).MAX_MODEL_CALLS, 392)
        self.assertEqual(r.profile(ROOT).MAX_OUTPUT_TOKENS, 3000)


if __name__ == '__main__':
    unittest.main()
