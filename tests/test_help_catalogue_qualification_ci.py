"""Adversarial cost/credential boundary tests; no network, Docker or model calls."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import subprocess

from tests.help_catalogue_history import original_catalogue_v1_case

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('exact100_ci', ROOT / 'tools/verification/run_help_catalogue_qualification_20261023.py')
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def context():
    return {'GITHUB_REPOSITORY': 'pcvantol/djconnect', 'GITHUB_REF': 'refs/heads/main',
            'GITHUB_WORKFLOW_REF': RUNNER.WORKFLOW, 'GITHUB_ACTOR': 'pcvantol',
            'GITHUB_TRIGGERING_ACTOR': 'pcvantol', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
            'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1', 'DJC_HELP100_GRANT': RUNNER.GRANT,
            'GITHUB_RUN_ID': '123456', 'GITHUB_SHA': 'a' * 40}



class NewHelpCatalogueTest(unittest.TestCase):
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
            ('DJC_HELP100_GRANT', 'another-grant'), ('GITHUB_RUN_ID', ''),
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

    @original_catalogue_v1_case
    def test_exact_current_manifest_contains_all70_questions_and30_followups(self):
        from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases, manifest_digest
        self.assertEqual((len(cases()), len(chain_cases())), (70, 30))
        self.assertEqual(manifest_digest(), RUNNER.MANIFEST)
        self.assertEqual(RUNNER.MAX_SECONDS, 1800)
        self.assertEqual(RUNNER.LAST_START, datetime(2026, 10, 23, 18, 30, tzinfo=timezone.utc))

    def test_workflow_exposes_no_general_matrix_or_automatic_paid_trigger(self):
        text = (ROOT / '.github/workflows/help-catalogue-qualified100-20261023.yml').read_text()
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


    def test_new_human_grant_does_not_open_old_consumed_slot(self):
        old_spec = importlib.util.spec_from_file_location('old_consumed_help_slot',
            ROOT / 'tools/verification/run_catalogue_exact100_20261023.py')
        old = importlib.util.module_from_spec(old_spec)
        old_spec.loader.exec_module(old)
        self.assertNotEqual(RUNNER.GRANT, old.GRANT)
        self.assertNotEqual(RUNNER.WORKFLOW, old.WORKFLOW)
        self.assertEqual(old.CANDIDATE, '1c5516d51c01c688b595ed2f0cccf28606e1ba13')
        with self.assertRaises(ValueError):
            old.admit_context(context(), RUNNER.START)
        with self.assertRaises(ValueError):
            RUNNER.admit_context({**context(), 'GITHUB_WORKFLOW_REF': old.WORKFLOW,
                'DJC_HELP100_GRANT': old.GRANT}, RUNNER.START)

    def test_duplicate_nested_nonfinite_utf16_and_escaped_secret_fail_closed(self):
        key = 'synthetic-only-key-never-a-real-secret'
        escaped = ''.join('\\u%04x' % ord(c) for c in key)
        values = [b'{"current_case":"PRIVATE_CANARY","current_case":null}',
            b'{"nested":{"value":"PRIVATE_CANARY","value":0}}',
            b'{"value":NaN}', b'{"value":Infinity}', b'{"value":1e999}',
            '{"value":"PRIVATE_CANARY"}'.encode('utf-16'),
            ('{"value":"'+escaped+'"}').encode(),
            ('[' * 50 + '0' + ']' * 50).encode()]
        for value in values:
            with self.subTest(value=value[:30]), self.assertRaises(ValueError):
                RUNNER.report_safe(value, key)

    def test_atomic_publication_preserves_original_fsync_failure(self):
        with TemporaryDirectory() as tmp:
            original = OSError('synthetic-first-fsync-failure')
            secondary = OSError('synthetic-secondary-unlink-failure')
            with patch.object(RUNNER.os, 'fsync', side_effect=original), \
                 patch.object(RUNNER.os, 'unlink', side_effect=secondary), \
                 self.assertRaises(OSError) as caught:
                RUNNER.write_bytes(Path(tmp) / 'receipt.json', b'{}')
            self.assertIs(caught.exception, original)

    def test_publication_is_exclusive_and_work_file_links_are_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / 'receipt.json'
            RUNNER.write_bytes(p, b'{"original":true}')
            with self.assertRaises(FileExistsError):
                RUNNER.write_bytes(p, b'{"replacement":true}')
            self.assertEqual(p.read_bytes(), b'{"original":true}')
            link = root / 'linked.json'
            link.symlink_to(p)
            with self.assertRaises(OSError):
                RUNNER.read_work_file(link, maximum=100)
            RUNNER.os.link(p, root / 'hardlink.json')
            with self.assertRaises(ValueError):
                RUNNER.read_work_file(p, maximum=100)

    def fixture(self, root, *, complete=False):
        from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases
        from scripts.verification.catalogue_progress import CatalogueProgress
        directory, work = root / 'public', root / 'work'
        directory.mkdir()
        work.mkdir()
        ids = [c['id'] for c in cases() + chain_cases()]
        progress = CatalogueProgress(work / 'catalogue-progress.json',
            case_ids=ids, manifest=RUNNER.MANIFEST)
        progress.before_model('catalogue-start')
        progress.completed_response()
        for case in (ids if complete else ids[:1]):
            progress.completed_case(case, passed=True)
        progress.terminal('COMPLETE_NOT_QUALIFIED' if complete else 'FAIL')
        # Wrapper-control fixture only. Actual full profile validator is unchanged.
        profile = SimpleNamespace(cases=cases, chain_cases=chain_cases,
            validate_report=lambda report, **kwargs: True)
        return directory, work, profile

    def finish(self, root, directory, work, profile, *, code=1, absent=True):
        files = {'synthetic.py': '0' * 64}
        with patch.object(RUNNER, 'product_hashes', return_value=files), \
             patch.object(RUNNER, 'git', return_value=RUNNER.CANDIDATE), \
             patch.object(RUNNER, 'profile_source_hashes', return_value=files):
            return RUNNER.finish_execution(root, directory, {}, files, profile,
                'synthetic-only-key-never-a-real-secret', work=work, code=code,
                absent=absent, interrupted=None)

    def test_failed_process_preserves_only_validated_closed_partial_progress(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory, work, profile = self.fixture(root)
            original = json.loads((work / 'catalogue-progress.json').read_text())
            self.assertEqual(self.finish(root, directory, work, profile), 1)
            self.assertEqual(json.loads((directory / 'catalogue-progress.json').read_text()), original)
            summary = json.loads((directory / 'summary.json').read_text())
            self.assertEqual(summary['status'], 'FAIL_OR_INCOMPLETE')
            self.assertEqual(summary['sdk_attempts_reserved'], 1)
            self.assertEqual(summary['external_billing'], 'UNKNOWN_NOT_A_BILLING_RECEIPT')
            self.assertIn('REPORT_MISSING', summary['findings'])

    def test_duplicate_private_canary_never_reaches_public_receipts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory, work, profile = self.fixture(root)
            p = work / 'catalogue-progress.json'
            p.write_bytes(b'{"current_case":"PRIVATE_CANARY",' + p.read_bytes()[1:])
            self.assertEqual(self.finish(root, directory, work, profile), 1)
            self.assertFalse((directory / 'catalogue-progress.json').exists())
            self.assertNotIn(b'PRIVATE_CANARY', (directory / 'summary.json').read_bytes())

    def test_full_validator_alone_cannot_override_missing_progress_or_count_mismatch(self):
        for mode in ('control', 'mismatch', 'missing', 'cleanup_unknown'):
            with self.subTest(mode=mode), TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory, work, profile = self.fixture(root, complete=True)
                ids = [c['id'] for c in profile.cases() + profile.chain_cases()]
                report = {'qualification':'REAL_PAIRED_HA_EXACT_CATALOGUE_QUESTIONS_V1',
                    'manifest_sha256':RUNNER.MANIFEST, 'source_hashes':{'synthetic.py':'0'*64},
                    'source_unchanged':True, 'cases':[{'id':i} for i in ids],
                    'model_calls':[{'completed':True}], 'paid_model_calls':1}
                if mode == 'mismatch':
                    report['model_calls'].append({'completed':True})
                if mode == 'missing':
                    (work / 'catalogue-progress.json').unlink()
                (work / 'catalogue-golden.json').write_text(json.dumps(report))
                result = self.finish(root, directory, work, profile,
                    code=0, absent=mode != 'cleanup_unknown')
                self.assertEqual(result, 0 if mode == 'control' else 1)
                if mode == 'cleanup_unknown':
                    self.assertFalse((directory / 'catalogue-golden.json').exists())

    def test_once_reservation_failure_precedes_any_test_secret_read(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            RUNNER.write_json(root / 'admission.json', {'coordinates':{}, 'product_hashes':{}})
            class DeniedSecret:
                def get(self, *args):
                    raise AssertionError('secret must not be read before durable reservation')
            with patch.object(RUNNER, 'reserve_once', side_effect=OSError('synthetic disk full')), \
                 self.assertRaises(OSError):
                RUNNER.execute(root, root, {}, {}, None, DeniedSecret())

    def test_original_timeout_survives_secondary_summary_failure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            RUNNER.write_json(root / 'admission.json', {'coordinates':{}, 'product_hashes':{}})
            original = subprocess.TimeoutExpired('synthetic-owned-container', 1800)
            def process(command, **kwargs):
                if command[:2] == ['docker','run']:
                    raise original
                return subprocess.CompletedProcess(command, 0)
            with patch.object(RUNNER.subprocess, 'run', side_effect=process), \
                 patch.object(RUNNER, 'container_absent', return_value=True), \
                 patch.object(RUNNER, 'finish_execution', side_effect=OSError('secondary output failure')), \
                 self.assertRaises(subprocess.TimeoutExpired) as caught:
                RUNNER.execute(root, root, {}, {}, None,
                    {'DJCONNECT_GOLDEN_OPENAI_API_KEY':'synthetic-only-key-never-a-real-secret'})
            self.assertIs(caught.exception, original)


if __name__ == '__main__':
    unittest.main()
