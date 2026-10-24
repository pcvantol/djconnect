"""Fault injection only: no HA install, model, network, credentials or retry."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases, manifest_digest, run
from scripts.verification.catalogue_progress import CatalogueProgress, validate_progress


IDS = [c['id'] for c in cases() + chain_cases()]
MANIFEST = manifest_digest()


class ProgressTest(unittest.TestCase):
    def progress(self, tmp):
        return CatalogueProgress(Path(tmp) / 'progress.json', case_ids=IDS, manifest=MANIFEST)

    def test_first_write_is_exclusive_and_never_restores_execution_authority(self):
        with TemporaryDirectory() as tmp:
            p = self.progress(tmp)
            original = p.path.read_bytes()
            with self.assertRaises(FileExistsError):
                self.progress(tmp)
            self.assertEqual(p.path.read_bytes(), original)
            self.assertEqual(json.loads(original)['qualification'], 'NOT_QUALIFIED')

    def test_pre_call_failure_stops_sdk_and_keeps_last_durable_prefix(self):
        with TemporaryDirectory() as tmp:
            p = self.progress(tmp)
            p.before_model('catalogue-start')
            p.completed_response()
            prefix = p.path.read_bytes()
            sdk_calls = []
            def invoke():
                p.before_model(IDS[0])
                sdk_calls.append('invoked')
            with patch('scripts.verification.catalogue_progress.os.replace', side_effect=OSError('SECRET_CANARY')):
                with self.assertRaises(OSError):
                    invoke()
            with self.assertRaises(RuntimeError):
                invoke()
            self.assertEqual(sdk_calls, [])
            self.assertEqual(p.path.read_bytes(), prefix)
            self.assertEqual(list(Path(tmp).glob('.catalogue-progress-*')), [])
            self.assertNotIn(b'SECRET_CANARY', prefix)

    def test_attempt_is_reserved_before_lost_response_and_is_not_billing_proof(self):
        with TemporaryDirectory() as tmp:
            p = self.progress(tmp)
            p.before_model(IDS[0])
            p.failure_without_masking_primary()
            row = json.loads(p.path.read_bytes())
            self.assertEqual((row['sdk_attempts_reserved'], row['sdk_completed_responses']), (1, 0))
            self.assertEqual(row['external_billing'], 'UNKNOWN_NOT_A_BILLING_RECEIPT')
            self.assertEqual(row['outcome'], 'FAIL')
            with self.assertRaises(RuntimeError):
                p.before_model(IDS[1])

    def test_bad_schema_and_canaries_never_become_an_artifact_or_pass(self):
        with TemporaryDirectory() as tmp:
            p = self.progress(tmp)
            original = deepcopy(p.value)
            for key, value in [('phase', []), ('outcome', {}), ('current_case', ['secret']),
                               ('sdk_attempts_reserved', True), ('sdk_attempts_reserved', 393),
                               ('qualification', 'PASS'), ('outcome', 'PASS'),
                               ('completed_cases', [IDS[0], IDS[0]]), ('current_case', 'SECRET_CANARY')]:
                with self.subTest(key=key, value=value):
                    self.assertFalse(validate_progress({**original, key: value}, case_ids=IDS, manifest=MANIFEST))
            self.assertFalse(validate_progress({**original, 'exception': 'SECRET_CANARY'}, case_ids=IDS, manifest=MANIFEST))
            self.assertFalse(validate_progress({**original, 'outcome': 'COMPLETE_NOT_QUALIFIED'}, case_ids=IDS, manifest=MANIFEST))
            self.assertFalse(validate_progress({**original, 'phase': 'terminal'}, case_ids=IDS, manifest=MANIFEST))
            self.assertFalse(validate_progress({**original, 'outcome': 'FAIL'}, case_ids=IDS, manifest=MANIFEST))

    def test_running_cannot_be_published_as_a_terminal_and_secondary_unlink_does_not_mask_save_failure(self):
        with TemporaryDirectory() as tmp:
            p = self.progress(tmp)
            original = p.path.read_bytes()
            with self.assertRaises(ValueError):
                p.terminal('RUNNING')
            self.assertEqual(p.path.read_bytes(), original)
            primary = OSError('primary-save')
            with patch('scripts.verification.catalogue_progress.os.replace', side_effect=primary), \
                    patch('scripts.verification.catalogue_progress.os.unlink', side_effect=PermissionError('secondary-unlink')):
                with self.assertRaises(OSError) as raised:
                    p.before_model(IDS[0])
            self.assertIs(raised.exception, primary)
            self.assertEqual(p.path.read_bytes(), original)
            self.assertFalse(p.healthy)

    def test_complete_and_cancelled_are_never_qualification_or_restart_grants(self):
        with TemporaryDirectory() as tmp:
            p = self.progress(tmp)
            for case in IDS:
                p.completed_case(case, passed=True)
            p.terminal('COMPLETE_NOT_QUALIFIED')
            self.assertEqual(json.loads(p.path.read_bytes())['qualification'], 'NOT_QUALIFIED')
            with self.assertRaises(RuntimeError):
                p.terminal('RUNNING')
        with TemporaryDirectory() as tmp:
            p = self.progress(tmp)
            p.failure_without_masking_primary(cancelled=True)
            self.assertEqual(json.loads(p.path.read_bytes())['outcome'], 'CANCELLED')

    def test_late_completion_cannot_mutate_any_terminal_receipt(self):
        for outcome in ('FAIL', 'CANCELLED', 'COMPLETE_NOT_QUALIFIED'):
            with self.subTest(outcome=outcome), TemporaryDirectory() as tmp:
                p = self.progress(tmp)
                p.before_model(IDS[0])
                if outcome == 'COMPLETE_NOT_QUALIFIED':
                    for case in IDS:
                        p.completed_case(case, passed=True)
                p.terminal(outcome)
                original = p.path.read_bytes()
                for callback in (p.completed_response,
                                 lambda: p.completed_case(IDS[-1], passed=True),
                                 lambda: p.before_model(IDS[-1]),
                                 lambda: p.phase('case', IDS[-1])):
                    with self.assertRaises(RuntimeError):
                        callback()
                    self.assertEqual(p.path.read_bytes(), original)


class ActualProfileFaultTest(unittest.IsolatedAsyncioTestCase):
    async def execute(self, progress, *, clear_error=None, end_error=None):
        ended = []
        active = SimpleNamespace(session_id='synthetic')
        observer = SimpleNamespace(_spotify_sessions={'profile-a': object()})
        async def poll(_):
            return None
        observer._async_poll_spotify = poll
        async def start(_):
            return active, None, None
        async def end(*_):
            ended.append(True)
            if end_error:
                raise end_error
        async def call(path, data, **kwargs):
            if clear_error and path == 'ask_dj/history/clear':
                raise clear_error
            return {}
        async def judge(*_):
            raise AssertionError('No answer is supplied; no judge/model may run')
        fake = SimpleNamespace(playback_observation_manager=lambda _: observer)
        try:
            with patch.dict(sys.modules, {'custom_components.djconnect.playback_observation': fake}):
                return await run(hass=object(), call=call, start=start, end=end, state={},
                    provider_calls=[], model_receipts=[], judge_language=judge, progress=progress)
        finally:
            self.assertEqual(ended, [True])

    async def test_primary_setup_failure_survives_secondary_teardown_failure(self):
        with TemporaryDirectory() as tmp:
            p = CatalogueProgress(Path(tmp) / 'progress.json', case_ids=IDS, manifest=MANIFEST)
            primary = ValueError('PRIVATE_PRIMARY_CANARY')
            with self.assertRaises(ValueError) as raised:
                await self.execute(p, clear_error=primary, end_error=RuntimeError('SECONDARY_CANARY'))
            self.assertIs(raised.exception, primary)
            p.failure_without_masking_primary()
            raw = p.path.read_bytes()
            self.assertNotIn(b'CANARY', raw)
            self.assertEqual(json.loads(raw)['outcome'], 'FAIL')

    async def test_all100_observations_survive_failure_before_final_report(self):
        with TemporaryDirectory() as tmp:
            p = CatalogueProgress(Path(tmp) / 'progress.json', case_ids=IDS, manifest=MANIFEST)
            with self.assertRaises(RuntimeError):
                await self.execute(p, end_error=RuntimeError('teardown'))
            p.failure_without_masking_primary()
            row = json.loads(p.path.read_bytes())
            self.assertEqual((len(row['completed_cases']), len(row['failed_cases'])), (100, 100))
            self.assertEqual(row['sdk_attempts_reserved'], 0)
            self.assertEqual(row['outcome'], 'FAIL')

    async def test_cancellation_is_primary_and_cleanup_still_runs(self):
        with TemporaryDirectory() as tmp:
            p = CatalogueProgress(Path(tmp) / 'progress.json', case_ids=IDS, manifest=MANIFEST)
            with self.assertRaises(asyncio.CancelledError):
                await self.execute(p, clear_error=asyncio.CancelledError(), end_error=RuntimeError('secondary'))
            p.failure_without_masking_primary(cancelled=True)
            self.assertEqual(json.loads(p.path.read_bytes())['outcome'], 'CANCELLED')

    async def test_checkpoint_failure_does_not_skip_session_cleanup(self):
        with TemporaryDirectory() as tmp:
            p = CatalogueProgress(Path(tmp) / 'progress.json', case_ids=IDS, manifest=MANIFEST)
            with patch('scripts.verification.catalogue_progress.os.replace', side_effect=OSError('disk')):
                with self.assertRaises(OSError):
                    await self.execute(p)


if __name__ == '__main__':
    unittest.main()
