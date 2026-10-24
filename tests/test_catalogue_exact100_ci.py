"""Adversarial cost/credential boundary tests; no network, Docker or model calls."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('exact100_ci', ROOT / 'tools/verification/run_catalogue_exact100_20261023.py')
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def context():
    return {'GITHUB_REPOSITORY': 'pcvantol/djconnect', 'GITHUB_REF': 'refs/heads/main',
            'GITHUB_WORKFLOW_REF': RUNNER.WORKFLOW, 'GITHUB_ACTOR': 'pcvantol',
            'GITHUB_TRIGGERING_ACTOR': 'pcvantol', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
            'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1', 'DJC_EXACT100_GRANT': RUNNER.GRANT,
            'GITHUB_RUN_ID': '123456', 'GITHUB_SHA': 'a' * 40}


class ExactCatalogueTest(unittest.TestCase):
    def test_only_first_original_main_dispatch_can_reach_paid_admission(self):
        valid = context()
        receipt = RUNNER.admit_context(valid, RUNNER.START)
        self.assertEqual(receipt['candidate'], RUNNER.CANDIDATE)
        for field, value in [
            ('GITHUB_RUN_NUMBER', '2'), ('GITHUB_RUN_ATTEMPT', '2'),
            ('GITHUB_EVENT_NAME', 'push'), ('GITHUB_EVENT_NAME', 'pull_request'),
            ('GITHUB_EVENT_NAME', 'workflow_call'), ('GITHUB_REF', 'refs/heads/feature'),
            ('GITHUB_REF', 'refs/tags/main'), ('GITHUB_REPOSITORY', 'other/djconnect'),
            ('GITHUB_ACTOR', 'other'), ('GITHUB_TRIGGERING_ACTOR', 'other'),
            ('GITHUB_WORKFLOW_REF', RUNNER.WORKFLOW.replace('@refs/heads/main', '@refs/heads/feature')),
            ('DJC_EXACT100_GRANT', 'another-grant'), ('GITHUB_RUN_ID', ''),
            ('GITHUB_RUN_ID', '1\n2'), ('GITHUB_SHA', 'not-a-sha'),
        ]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                RUNNER.admit_context({**valid, field: value}, RUNNER.START)
        for now in (RUNNER.START - timedelta(microseconds=1), RUNNER.LAST_START,
                    RUNNER.LAST_START + timedelta(seconds=1)):
            with self.subTest(now=now), self.assertRaises(ValueError):
                RUNNER.admit_context(valid, now)

    def test_persistent_local_once_reservation_cannot_reset_after_unknown_outcome(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'once.json'
            RUNNER.reserve_once(path, {'run_id': 'first'})
            original = path.read_bytes()
            value = json.loads(original)
            self.assertEqual((value['max_attempts'], value['max_output_tokens'], value['max_seconds']),
                             (392, 3000, 1800))
            with self.assertRaises(FileExistsError):
                RUNNER.reserve_once(path, {'run_id': 'new-run-or-retry'})
            self.assertEqual(path.read_bytes(), original)

    def test_wrong_or_nonterminal_original_qualification_never_becomes_admission(self):
        sha = RUNNER.CANDIDATE
        row = {'context': 'Post-Merge Release Evidence / Reconcile release evidence',
               'state': 'success', 'description': 'POST_MERGE_RELEASE_EVIDENCE_QUALIFIED',
               'target_url': 'https://github.com/pcvantol/djconnect/actions/runs/123'}
        self.assertEqual(RUNNER.qualified_status({'sha': sha, 'statuses': [row]}, sha), row['target_url'])
        for value in [None, {}, {'sha': 'b' * 40, 'statuses': [row]}, {'sha': sha, 'statuses': []},
                      {'sha': sha, 'statuses': [{**row, 'state': 'pending'}]},
                      {'sha': sha, 'statuses': [{**row, 'description': 'not-qualified'}]},
                      {'sha': sha, 'statuses': [{**row, 'state': 'failure'}, row]}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                RUNNER.qualified_status(value, sha)

    def test_secret_contamination_and_oversized_report_fail_before_artifact_copy(self):
        marker = 'synthetic-private-test-key-never-a-real-secret'
        with self.assertRaises(ValueError):
            RUNNER.report_safe(json.dumps({'unexpected': marker}).encode(), marker)
        with self.assertRaises(ValueError):
            RUNNER.report_safe(b'x' * (8 * 1024 * 1024 + 1), marker)
        self.assertEqual(RUNNER.report_safe(b'{"synthetic_only":true}', marker), {'synthetic_only': True})

    def test_exact_current_manifest_contains_all70_questions_and30_followups(self):
        from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases, manifest_digest
        self.assertEqual((len(cases()), len(chain_cases())), (70, 30))
        self.assertEqual(manifest_digest(), RUNNER.MANIFEST)
        self.assertEqual(RUNNER.MAX_SECONDS, 1800)
        self.assertEqual(RUNNER.LAST_START, datetime(2026, 10, 23, 19, 10, tzinfo=timezone.utc))

    def test_workflow_exposes_no_general_matrix_or_automatic_paid_trigger(self):
        text = (ROOT / '.github/workflows/catalogue-exact100-20261023.yml').read_text()
        self.assertIn('on:\n  workflow_dispatch:', text)
        self.assertNotIn('\n  push:', text)
        self.assertNotIn('\n  pull_request:', text)
        self.assertNotIn('\n  workflow_call:', text)
        self.assertNotIn('run_askdj_release_matrix.py', text)
        self.assertEqual(text.count('secrets.DJCONNECT_GOLDEN_OPENAI_API_KEY'), 1)
        self.assertLess(text.index('--admit-only'), text.index('secrets.DJCONNECT_GOLDEN_OPENAI_API_KEY'))
        self.assertIn('cancel-in-progress: false', text)
        self.assertNotIn('private.log\n', text)
        self.assertNotIn('continue-on-error', text)


if __name__ == '__main__':
    unittest.main()
