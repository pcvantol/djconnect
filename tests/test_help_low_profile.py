"""A separately admitted low profile cannot relabel medium or legacy evidence."""
from copy import deepcopy
import ast
import asyncio
import inspect
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts.verification import askdj_example_catalogue_golden as golden
from tools.verification import help_content_low_preflight as preflight
from tools.verification import help_content_probe_child as child
from tools.verification import help_content_probe as policy
from tools.verification import run_help_content_probe as runner
from tests import test_ask_dj_catalogue_golden as baseline


class NamedLowQualificationTests(unittest.TestCase):
    def report(self):
        # An explicit validator vector, never an original paid/model result.
        value = baseline.CatalogueGoldenTest().receipt_fixture()
        value['qualification_profile'] = golden.LOW_REASONING_PROFILE
        return value

    def env(self):
        return {
            'GITHUB_REPOSITORY': 'pcvantol/djconnect',
            'GITHUB_REF': 'refs/heads/main',
            'GITHUB_WORKFLOW_REF': runner.WORKFLOW,
            'GITHUB_ACTOR': 'pcvantol', 'GITHUB_TRIGGERING_ACTOR': 'pcvantol',
            'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_RUN_ID': '123', 'GITHUB_SHA': 'a' * 40,
            'DJC_CONTROLLER_SHA': 'a' * 40, 'DJC_CANDIDATE_SHA': 'b' * 40,
            'DJC_CONTENT_DIGEST': 'c' * 64, 'DJC_PLAN_DIGEST': 'd' * 64,
            'DJC_CONTENT_MODE': 'target5_artist_v4',
        }

    def test_named_low_requires_its_own_marker_and_trusted_expectation(self):
        legacy = baseline.CatalogueGoldenTest().receipt_fixture()
        named = self.report()
        hashes = named['source_hashes']
        self.assertTrue(golden.validate_report(legacy, source_hashes=hashes))
        self.assertFalse(golden.validate_report(named, source_hashes=hashes))
        self.assertTrue(golden.validate_report(named, source_hashes=hashes,
            expected_profile=golden.LOW_REASONING_PROFILE))
        self.assertFalse(golden.validate_report(legacy, source_hashes=hashes,
            expected_profile=golden.LOW_REASONING_PROFILE))
        self.assertFalse(golden.validate_report(named, source_hashes=hashes,
            expected_profile=golden.MEDIUM_REASONING_PROFILE))

    def test_one_wrong_model_effort_or_budget_cannot_hide_in_low_result(self):
        good = self.report()
        indices = {0, len(good['model_calls']) - 1,
            next(i for i, row in enumerate(good['model_calls'])
                 if row.get('purpose') == 'answer_language_judge')}
        for index in indices:
            for field, bad in [('reasoning_effort', 'medium'), ('reasoning_effort', None),
                               ('model', 'other-model'), ('maximum_output_tokens', 3001)]:
                value = deepcopy(good)
                value['model_calls'][index][field] = bad
                self.assertFalse(golden.validate_report(value,
                    source_hashes=good['source_hashes'], expected_profile=golden.LOW_REASONING_PROFILE))

    def test_claimed_profile_cannot_replace_original_questions_source_or_effects(self):
        good = self.report()
        for change in [lambda r: r['cases'].pop(),
                       lambda r: r['cases'][0].update(question_sha256='0' * 64),
                       lambda r: r.update(source_unchanged=False),
                       lambda r: r['source_hashes'].update(forged='x')]:
            value = deepcopy(good)
            change(value)
            self.assertFalse(golden.validate_report(value,
                source_hashes=good['source_hashes'], expected_profile=golden.LOW_REASONING_PROFILE))

    def test_medium_default_and_old_control_map_remain_exact(self):
        self.assertEqual(policy.execution_profile(), {
            'id': 'help_medium_v1', 'model': 'gpt-6-luna',
            'reasoning_effort': 'medium', 'maximum_output_tokens': 3000})
        self.assertEqual(policy.control_files(), policy.CONTROL_FILES)
        low = policy.execution_profile(policy.LOW_CONTENT_PROFILE_ID)
        self.assertEqual(low, {'id': 'help_low_v1', 'model': 'gpt-6-luna',
            'reasoning_effort': 'low', 'maximum_output_tokens': 3000})
        self.assertEqual(policy.control_files(policy.LOW_CONTENT_PROFILE_ID),
            policy.CONTROL_FILES[:-1] + ('tools/verification/help_content_low_preflight.py',))
        self.assertNotEqual(policy.digest(policy.canonical(low)),
                            policy.digest(policy.canonical(policy.execution_profile())))

    def test_unknown_profile_closes_before_setup_or_secret_io(self):
        for value in [None, True, {}, '', 'low', 'legacy_low', 'help_low_v2', ' help_low_v1']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                runner.context(self.env() | {'DJC_CONTENT_PROFILE': value})
            with self.subTest(value=value), self.assertRaises(ValueError):
                policy.execution_profile(value)
        for value in [None, True, '', 'legacy_low', 'help_medium_v1', 'other']:
            with patch('importlib.util.spec_from_file_location',
                       side_effect=AssertionError('setup must not start')):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    preflight.main(qualification_profile=value)

    def test_profile_change_between_admission_and_execute_closes_before_snapshot_or_secret(self):
        medium = self.env()
        low = medium | {'DJC_CONTENT_PROFILE': policy.LOW_CONTENT_PROFILE_ID}
        self.assertEqual(runner.context(medium), runner.context(medium | {
            'DJC_CONTENT_PROFILE': policy.CONTENT_PROFILE_ID}))
        for admitted_env, execute_env in [(medium, low), (low, medium)]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'admission.json').write_text(json.dumps({
                    'coordinates': runner.context(admitted_env), 'content': {}}))
                args = ['probe', '--candidate-root', directory, '--controller-root', directory,
                        '--report-dir', directory, '--phase', 'execute']
                with patch.dict(os.environ, execute_env, clear=True), patch('sys.argv', args), \
                     patch.object(runner, 'validate_candidate',
                         side_effect=AssertionError('snapshot must not be reached')), \
                     patch.object(runner, 'execute',
                         side_effect=AssertionError('secret-bearing execute must not be reached')):
                    with self.assertRaises(ValueError):
                        runner.main()

    def test_selected_word_proof_cannot_be_replaced_by_a_profile_label(self):
        pin = {'execution_profile': policy.execution_profile(policy.LOW_CONTENT_PROFILE_ID)}
        self.assertFalse(policy.validate_profile_selected_report(self.report(), {}, pin=pin,
            mode='target5_artist_v4', profile=policy.LOW_CONTENT_PROFILE_ID))
        self.assertFalse(policy.validate_medium_selected_report(self.report(), {}, pin=pin,
            mode='target5_artist_v4'))

    def test_child_lost_or_changed_low_selector_closes_before_ha_or_sdk(self):
        low = policy.execution_profile(policy.LOW_CONTENT_PROFILE_ID)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {'DJC_CONTENT_PROFILE': policy.LOW_CONTENT_PROFILE_ID}
            self.assertEqual(child.captured_profile({}, root), policy.CONTENT_PROFILE_ID)
            with self.assertRaises(ValueError):
                child.captured_profile(env, root)
            marker = root / 'execution-profile.json'
            marker.write_text(json.dumps(low))
            self.assertEqual(child.captured_profile(env, root), policy.LOW_CONTENT_PROFILE_ID)
            for wrong in [{}, {'DJC_CONTENT_PROFILE': policy.CONTENT_PROFILE_ID}]:
                with self.assertRaises(ValueError):
                    child.captured_profile(wrong, root)
            for value in [policy.execution_profile(), {**low, 'maximum_output_tokens': 3000.0},
                          {**low, 'extra': True}, {**low, 'reasoning_effort': 'medium'}]:
                marker.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    child.captured_profile(env, root)
            marker.write_text('{"id":"help_low_v1","id":"help_low_v1"}')
            with self.assertRaises(ValueError):
                child.captured_profile(env, root)

    def test_child_cannot_follow_a_profile_symlink_or_unbounded_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'synthetic-only.json'
            target.write_text(json.dumps(policy.execution_profile()))
            marker = root / 'execution-profile.json'
            marker.symlink_to(target)
            with self.assertRaises(OSError):
                child.captured_profile({}, root)
            marker.unlink()
            marker.write_text(' ' * 1025)
            with self.assertRaises(ValueError):
                child.captured_profile({}, root)

    def test_actual_low_rest_boundary_rejects_wrong_token_type_or_limit_before_receipt_io(self):
        # Execute the actual nested transport fence, stopping at its next file
        # read rather than replacing its model/effort/token predicates.
        tree = ast.parse(inspect.getsource(preflight.main))
        deny = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == 'deny')
        namespace = {'json': json, 'Path': Path,
            'qualification_profile': golden.LOW_REASONING_PROFILE,
            'LEGACY_REASONING_PROFILE': golden.LEGACY_REASONING_PROFILE,
            'expected_effort': 'low'}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[deny], type_ignores=[])),
                     '<ACTUAL_LOW_PREFLIGHT_REST_BOUNDARY>', 'exec'), namespace)
        def request(value):
            return SimpleNamespace(method='POST',
                url=SimpleNamespace(host='api.openai.com', path='/v1/responses'),
                content=json.dumps(value).encode())
        good = {'model': 'gpt-6-luna', 'reasoning': {'effort': 'low'},
                'max_output_tokens': 3000}
        for tokens in [None, True, 1, 2999, 3001, 3000.0, '3000']:
            with patch.object(Path, 'read_text',
                    side_effect=RuntimeError('after actual REST token fence')) as reader:
                with self.subTest(tokens=tokens), self.assertRaises(AssertionError):
                    asyncio.run(namespace['deny'](None, request({**good, 'max_output_tokens': tokens})))
                reader.assert_not_called()
        with patch.object(Path, 'read_text',
                side_effect=RuntimeError('after actual REST token fence')) as reader:
            with self.assertRaisesRegex(RuntimeError, 'after actual REST token fence'):
                asyncio.run(namespace['deny'](None, request(good)))
            reader.assert_called_once()


if __name__ == '__main__':
    unittest.main()
