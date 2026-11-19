"""Cost-free adversarial tests for this fresh once-only execution slot."""
from datetime import timedelta
import asyncio
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools/verification/run_help100_20261024.py'
SPEC = importlib.util.spec_from_file_location('fresh_help100_runner', RUNNER)
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def context():
    return {'GITHUB_REPOSITORY': 'pcvantol/djconnect', 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_WORKFLOW_REF': r.WORKFLOW, 'GITHUB_ACTOR': 'pcvantol',
        'GITHUB_TRIGGERING_ACTOR': 'pcvantol', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1', 'DJC_HELP100_GRANT': r.GRANT,
        'GITHUB_RUN_ID': '123456', 'GITHUB_SHA': 'a' * 40, 'DJC_EXPECTED_MAIN_SHA': 'a' * 40}


class FreshHelp100Test(unittest.TestCase):
    def test_late_async_transport_stays_closed_after_main_returns(self):
        spec = importlib.util.spec_from_file_location('fresh_help100_closed_async',
            ROOT / 'tools/verification/help100_child.py')
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        calls = []
        class Client:
            async def send(self, request):
                calls.append('original-send')
                return 'real-transport-result'
        transport = SimpleNamespace(AsyncClient=Client)
        async def actual_main():
            self.assertEqual(await Client().send(None), 'real-transport-result')
        module = SimpleNamespace(main=actual_main)
        loader = SimpleNamespace(exec_module=lambda module: None)
        async def scenario():
            loop = asyncio.get_running_loop()
            with patch.object(child, 'checkpoint'), \
                 patch.object(child.importlib.util, 'spec_from_file_location', return_value=SimpleNamespace(loader=loader)), \
                 patch.object(child.importlib.util, 'module_from_spec', return_value=module), \
                 patch.dict(child.sys.modules, {'httpx': transport}), \
                 patch.dict(child.os.environ, {'DJC_HELP100_WALL_END': str(child.time.time() + 60),
                     'DJC_HELP100_MONO_END': str(child.time.monotonic() + 60)}), \
                 patch.object(loop, 'add_signal_handler'):
                await child.execute()
                with self.assertRaises(TimeoutError):
                    await Client().send(None)
        asyncio.run(scenario())
        self.assertEqual(calls, ['original-send'])

    def test_provider_failure_classifier_never_exports_exception_text_or_names(self):
        spec = importlib.util.spec_from_file_location('fresh_help100_error_classifier',
            ROOT / 'tools/verification/help100_child.py')
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        auth_type = type('AuthenticationError', (Exception,), {'__module__': 'openai'})
        wrapped = RuntimeError('PRIVATE_CANARY_NEVER_EXPORT')
        wrapped.__cause__ = auth_type('PRIVATE_KEY_OR_RESPONSE')
        self.assertEqual(child.classify(wrapped), 'MODEL_AUTHENTICATION_FAILED')
        self.assertEqual(child.classify(AssertionError('PRIVATE_CASE_CONTENT')), 'ASSERTION_FAILED')
        self.assertEqual(child.classify(RuntimeError('PRIVATE_CANARY_NEVER_EXPORT')), 'ACTUAL_TEST_FAILED')

    def test_original_wall_and_monotonic_deadlines_never_reanchor(self):
        spec = importlib.util.spec_from_file_location('fresh_help100_child',
            ROOT / 'tools/verification/help100_child.py')
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        with patch.object(child.time, 'time', return_value=100), \
             patch.object(child.time, 'monotonic', return_value=10):
            self.assertEqual(child.remaining(150, 40), 30)
        # Either clock crossing its original limit closes future transport.
        for wall, mono in [(151, 11), (101, 41), (20, 41)]:
            with patch.object(child.time, 'time', return_value=wall), \
                 patch.object(child.time, 'monotonic', return_value=mono), \
                 self.assertRaises(TimeoutError):
                child.remaining(150, 40)

    def test_containerd_index_requires_selected_original_platform_manifest(self):
        row = {'Id': 'a' * 64, 'Image': r.IMAGE.split('@')[1],
            'Config': {'Image': r.IMAGE, 'Labels': {'djc.help100': '123456'}},
            'ImageManifestDescriptor': {'digest': 'sha256:' + 'b' * 64,
                'platform': {'architecture': 'amd64', 'os': 'linux'}}}
        r.validate_identity(row, 'a' * 64, 'sha256:' + 'b' * 64, '123456')
        for field, value in [('digest', 'sha256:' + 'c' * 64),
                             ('platform', {'architecture': 'arm64', 'os': 'linux'})]:
            altered = {**row, 'ImageManifestDescriptor': {**row['ImageManifestDescriptor'], field: value}}
            with self.assertRaises(ValueError):
                r.validate_identity(altered, 'a' * 64, 'sha256:' + 'b' * 64, '123456')

    def test_restriction_sha_is_not_caller_target_selection(self):
        valid = context()
        self.assertEqual(r.admit(valid, r.START)['source'], 'a' * 40)
        for name, value in [('DJC_EXPECTED_MAIN_SHA', 'b' * 40), ('GITHUB_SHA', 'b' * 40),
            ('GITHUB_RUN_NUMBER', '2'), ('GITHUB_RUN_ATTEMPT', '2'),
            ('GITHUB_REF', 'refs/heads/feature'), ('GITHUB_EVENT_NAME', 'push'),
            ('GITHUB_ACTOR', 'other'), ('GITHUB_TRIGGERING_ACTOR', 'other'),
            ('DJC_HELP100_GRANT', r.safe.GRANT), ('GITHUB_RUN_ID', '1\n2')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                r.admit({**valid, name: value}, r.START)
        for now in (r.START - timedelta(microseconds=1), r.LAST_START):
            with self.assertRaises(ValueError):
                r.admit(valid, now)

    def test_durable_once_and_journal_cannot_reenter_or_overwrite_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            r.safe.reserve_once(directory / 'once.json', {'grant': r.GRANT})
            original = (directory / 'once.json').read_bytes()
            with self.assertRaises(FileExistsError):
                r.safe.reserve_once(directory / 'once.json', {'grant': r.GRANT})
            self.assertEqual((directory / 'once.json').read_bytes(), original)
            journal = r.Journal(directory)
            journal.write('terminal', outcome='FAIL')
            with self.assertRaises(ValueError):
                journal.write('later', outcome='PASS')
            self.assertFalse((directory / 'later.json').exists())

    def test_failed_diagnostic_write_poison_stops_future_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = r.Journal(Path(tmp))
            with patch.object(r.safe, 'write_json', side_effect=OSError('synthetic-disk-full')):
                with self.assertRaises(OSError):
                    journal.write('reserved')
            self.assertFalse(journal.healthy)
            with self.assertRaises(ValueError):
                journal.write('container-created')

    def test_inspect_failure_does_not_prevent_stopping_owned_task(self):
        calls = []
        def docker(*args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, '', '')
        with patch.object(r, 'state', side_effect=ValueError('synthetic-inspect-unavailable')), \
             patch.object(r, 'docker', side_effect=docker), \
             patch.object(r.safe, 'container_absent', return_value=True):
            before, after, absent = r.cleanup('a' * 64, 'image', '123456')
        self.assertEqual((before, after, absent), (None, None, True))
        self.assertEqual([args[0] for args in calls], ['stop', 'kill', 'rm'])
        self.assertTrue(all(args[-1] == 'a' * 64 for args in calls))

    def test_exit137_is_not_relabelled_as_oom(self):
        row = {'Id': 'a' * 64, 'Image': 'image', 'Config': {'Image': r.IMAGE, 'Labels': {'djc.help100': '123456'}},
            'State': {'Status': 'exited', 'Running': False, 'ExitCode': 137, 'OOMKilled': False}}
        for oom in (False, True):
            row['State']['OOMKilled'] = oom
            with patch.object(r, 'docker', return_value=subprocess.CompletedProcess([], 0, json.dumps([row]), '')):
                result = r.state('a' * 64, 'image', '123456')
            self.assertEqual(result['oom_killed'], oom)
            self.assertEqual(result['exit_code'], 137)
        del row['State']['OOMKilled']
        with patch.object(r, 'docker', return_value=subprocess.CompletedProcess([], 0, json.dumps([row]), '')):
            with self.assertRaises(KeyError):
                r.state('a' * 64, 'image', '123456')

    def test_key_failure_after_reservation_always_attempts_summary_and_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            coordinate = {'source': 'a' * 40, 'run_id': '123456'}
            pin = {'product_hashes': {}}
            (directory / 'admission.json').write_text(json.dumps({'coordinates': coordinate, 'content': pin}))
            (directory / 'setup-preflight.json').write_text(json.dumps({'status': 'PASS_SETUP_ONLY_NOT_QUALIFIED', 'own_container': 'VERIFIED_ABSENT'}))
            image = subprocess.CompletedProcess([], 0, json.dumps([{'Id': 'sha256:' + 'a' * 64, 'RepoDigests': [r.IMAGE], 'Os': 'linux', 'Architecture': 'amd64'}]), '')
            with patch.object(r, 'docker', return_value=image), \
                 patch.object(r, 'admit', return_value=coordinate), \
                 patch.object(r, 'finish', side_effect=ValueError('synthetic-profile-import-failure')):
                with self.assertRaises(ValueError):
                    r.execute(ROOT, directory, coordinate, pin, {}, r.Journal(directory))
            self.assertTrue((directory / 'once-reservation.json').exists())
            self.assertEqual(json.loads((directory / 'cleanup.json').read_text())['state'], 'VERIFIED_ABSENT')
            result = json.loads((directory / 'summary.json').read_text())
            self.assertEqual(result['error'], 'REPORT_VALIDATION_FAILED')
            self.assertEqual(result['sdk_attempts_reserved'], None)
            self.assertEqual(json.loads((directory / 'terminal.json').read_text())['outcome'], 'FAIL_OR_INCOMPLETE')

    def test_workflow_uses_trusted_sha_both_checkouts_and_explicit_allowlist(self):
        text = (ROOT / '.github/workflows/help100-direct-human-20261024.yml').read_text()
        self.assertEqual(text.count('ref: ${{ github.sha }}'), 2)
        self.assertEqual(text.count('secrets.DJCONNECT_GOLDEN_OPENAI_API_KEY'), 1)
        self.assertNotIn('private.log\n', text)
        self.assertNotIn('private-work', text)
        self.assertNotIn('continue-on-error', text)
        self.assertNotIn('\n  push:', text)
        self.assertNotIn('--rm', RUNNER.read_text())


if __name__ == '__main__':
    unittest.main()
