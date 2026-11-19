"""A trusted medium lab profile cannot relabel historical low evidence."""
from copy import deepcopy
import inspect
import json
from pathlib import Path
from unittest.mock import patch
import unittest

from scripts.verification import askdj_example_catalogue_golden as golden
from tools.verification import help_content_probe as policy
from tools.verification import help_content_medium_preflight
from tests import test_ask_dj_catalogue_golden as baseline
from tests import test_playback_slot_drafts as slots


class MediumQualificationProfileTests(unittest.TestCase):
    def fixture(self):
        # Explicit synthetic validator vector; never an original medium/model run.
        return baseline.CatalogueGoldenTest().receipt_fixture()

    def medium(self):
        report = self.fixture()
        report['qualification_profile'] = golden.MEDIUM_REASONING_PROFILE
        report['configured_reasoning_effort'] = 'medium'
        for row in report['model_calls']:
            row['reasoning_effort'] = 'medium'
        return report

    def test_legacy_default_and_current_medium_are_distinct_trusted_expectations(self):
        low, medium = self.fixture(), self.medium()
        pins = low['source_hashes']
        self.assertEqual(golden.REASONING_EFFORT, 'low')
        self.assertTrue(golden.validate_report(low, source_hashes=pins))
        self.assertFalse(golden.validate_report(medium, source_hashes=pins))
        self.assertTrue(golden.validate_report(medium, source_hashes=pins,
            expected_profile=golden.MEDIUM_REASONING_PROFILE))
        self.assertFalse(golden.validate_report(low, source_hashes=pins,
            expected_profile=golden.MEDIUM_REASONING_PROFILE))

    def test_report_marker_cannot_select_expected_effort_or_hide_one_bad_sdk_call(self):
        good = self.medium()
        mutations = []
        for marker in (None, '', True, 'medium', 'legacy_low'):
            changed = deepcopy(good)
            changed['qualification_profile'] = marker
            mutations.append(changed)
        for effort in ('low', True, None, 'HIGH'):
            changed = deepcopy(good)
            changed['configured_reasoning_effort'] = effort
            mutations.append(changed)
        for index in (0, len(good['model_calls']) - 1,
                      next(i for i, row in enumerate(good['model_calls'])
                           if row.get('purpose') == 'answer_language_judge')):
            for field, value in (('reasoning_effort', 'low'), ('model', 'other-model'),
                                 ('maximum_output_tokens', 3001)):
                changed = deepcopy(good)
                changed['model_calls'][index][field] = value
                mutations.append(changed)
        for changed in mutations:
            with self.subTest(changed=changed.get('qualification_profile')):
                self.assertFalse(golden.validate_report(changed, source_hashes=good['source_hashes'],
                    expected_profile=golden.MEDIUM_REASONING_PROFILE))

    def test_closed_profile_rejects_unknowns_before_preflight_setup_or_secret_io(self):
        for value in (None, True, {}, 'medium', 'legacy', 'help_medium_v2', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                golden.reasoning_effort_for_profile(value)
            report = self.medium()
            self.assertFalse(golden.validate_report(report, source_hashes=report['source_hashes'],
                expected_profile=value))
            with patch('importlib.util.spec_from_file_location', side_effect=AssertionError('setup forbidden')):
                with self.assertRaises(ValueError):
                    help_content_medium_preflight.main(qualification_profile=value)

    def test_current_controller_profile_is_fresh_fixed_and_hash_bound(self):
        expected = {'id': 'help_medium_v1', 'model': 'gpt-6-luna',
                    'reasoning_effort': 'medium', 'maximum_output_tokens': 3000}
        self.assertEqual(policy.execution_profile(), expected)
        changed = policy.execution_profile()
        changed['reasoning_effort'] = 'low'
        self.assertEqual(policy.execution_profile(), expected)
        self.assertIn('tools/verification/help_content_medium_preflight.py', policy.CONTROL_FILES)
        self.assertEqual(len(policy.CONTROL_FILES), 5)
        self.assertNotIn('expected_profile', inspect.signature(policy.validate_medium_selected_report).parameters)
        self.assertFalse(policy.validate_medium_selected_report({}, {}, pin={'execution_profile': changed}))
        self.assertEqual(policy.mode_policy('target24_delivery_v3')[1:], (82, 900))
        self.assertEqual(policy.mode_policy('full100')[1:], (392, 1800))

    def test_original_actual_medium_sdk_fixture_is_separate_and_transport_only(self):
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root / 'tests/fixtures/help_public_task/selected24-actual-sdk-medium-v1.json').read_text())
        self.assertEqual(fixture['scope'], 'EXTRACTED_COSTFREE_ACTUAL_SDK_MEDIUM_PROFILE_ONLY_NOT_MODEL_QUALITY')
        self.assertEqual(fixture['original_synthetic_content_digest'], 'a' * 64)
        report = fixture['report']
        self.assertEqual(report['qualification_profile'], golden.MEDIUM_REASONING_PROFILE)
        self.assertEqual(report['configured_reasoning_effort'], 'medium')
        self.assertEqual(len(report['model_calls']), 65)
        self.assertTrue(all(row['model'] == 'gpt-6-luna' and row['reasoning_effort'] == 'medium'
            and row['maximum_output_tokens'] == 3000 for row in report['model_calls']))
        selected = [row for row in golden.cases() + golden.chain_cases()
                    if row['id'] in policy.TARGET24_DELIVERY_V3]
        self.assertTrue(policy.structured_playback_inputs_complete(report, cases=selected))
        # This stripped transport artifact never claims case/content acceptance.
        self.assertFalse(policy.validate_medium_selected_report(report, {},
            pin={'execution_profile': policy.execution_profile()}, mode='target24_delivery_v3'))
        bad = deepcopy(report)
        next(row for row in bad['model_calls'] if 'structured_output_format' in row).pop('structured_playback_input')
        self.assertFalse(policy.structured_playback_inputs_complete(bad, cases=selected))

    def test_medium_profile_preserves_original_case_source_effect_and_budget_checks(self):
        good = self.medium()
        for mutate in (
            lambda r: r['cases'].pop(),
            lambda r: r['source_hashes'].update(extra='forged'),
            lambda r: r.update(source_unchanged=False),
            lambda r: r['cases'][0].update(question_sha256='0' * 64),
            lambda r: r['core_transports'][0]['request'].update(language='wrong'),
        ):
            changed = deepcopy(good)
            mutate(changed)
            self.assertFalse(golden.validate_report(changed, source_hashes=good['source_hashes'],
                expected_profile=golden.MEDIUM_REASONING_PROFILE))


class ConditionalPlaybackPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        slots.PlaybackSlotDraftTests.setUpClass()
        cls.p = slots.PlaybackSlotDraftTests.p
        cls.n = slots.PlaybackSlotDraftTests.n

    @classmethod
    def tearDownClass(cls):
        slots.PlaybackSlotDraftTests.tearDownClass()

    def brief(self):
        return slots.PlaybackSlotDraftTests.brief(self)

    def collection_brief(self, *args, **kwargs):
        return slots.PlaybackSlotDraftTests.collection_brief(self, *args, **kwargs)

    def test_all80_inventories_have_truthful_kind_advice_and_exact_interleaving(self):
        count = 0
        for locale in ('en', 'nl', 'de', 'fr', 'es'):
            for kind in ('track', 'artist_tracks', 'album', 'playlist'):
                for observed in (False, True):
                    for rich in (False, True):
                        brief = self.collection_brief(kind, locale, observed=observed, rich=rich)
                        prompt = brief.prompt(verified_drafts=True)
                        instructions, body = prompt.split('\nData:\n', 1)
                        data = json.loads(body)
                        roles = brief.literal_gap_slots()
                        example_text = prompt.split('named gap before each Core role: ', 1)[1]
                        example, _ = json.JSONDecoder().raw_decode(example_text)
                        self.assertEqual(example['schema'], 'playback_role_gaps_v3')
                        self.assertEqual(len(example['drafts']), 1)
                        self.assertEqual(list(example['drafts'][0]['gaps']), roles)
                        self.assertIn('Write exactly ONE complete reply', instructions)
                        self.assertNotIn('TWO complete alternative replies', instructions)
                        self.assertEqual(data['gap_compilation_order'],
                            [part for name in roles for part in
                             ({'gap_before': name}, {'opaque_core_role': name})])
                        self.assertEqual(data['gap_compilation_order'][-1], {'opaque_core_role': 'status'})
                        self.assertNotIn('PRIVATE_', prompt)
                        self.assertNotIn('Do not write a media kind as literal prose:', instructions)
                        self.assertIn('LAST music name', instructions)
                        if 'media_kind' in roles:
                            self.assertIn('This shape has a media_kind Core role:', instructions)
                            self.assertNotIn('This shape has NO separate media_kind', instructions)
                        else:
                            self.assertIn('This shape has NO separate media_kind Core role.', instructions)
                            self.assertNotIn('This shape has a media_kind Core role:', instructions)
                        legacy = brief.prompt()
                        self.assertNotIn('gap_compilation_order', legacy)
                        self.assertNotIn('This shape has ', legacy)
                        self.assertIn('Return only {"text":"your reply"}', legacy)
                        count += 1
        self.assertEqual(count, 80)
