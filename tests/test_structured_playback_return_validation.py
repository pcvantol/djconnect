"""Returned task data is checked without trusting validator transformations."""
from copy import deepcopy
import importlib
import json
import unittest

from tests import test_ask_dj_contextual_dialogue as shared


class ReturnedTypedValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.module = importlib.import_module('custom_components.djconnect.structured_playback')

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def value(self):
        return {'schema': 'playback_role_gaps_v3', 'drafts': [
            {'gaps': {'title': 'I am handing you ', 'status': '. '}},
            {'gaps': {'title': 'I am bringing you ', 'status': '. '}}]}

    def test_original_wire_and_provider_object_survive_validation_and_dict_reordering(self):
        value = self.value()
        before = deepcopy(value)
        seen = []

        def validate(copy):
            self.assertIsNot(copy, value)
            self.assertIsNot(copy['drafts'], value['drafts'])
            seen.append(copy)
            return dict(reversed(list(copy.items())))

        wire = self.module.validate_typed_reply(value, validate)
        self.assertEqual(wire, self.module.freeze_typed_reply(before))
        self.assertEqual(value, before)
        self.assertEqual(json.loads(wire), before)
        self.assertEqual(len(seen), 1)

    def test_in_place_validator_mutation_cannot_change_its_own_baseline(self):
        for change in ('text', 'strip', 'list_order', 'new_field'):
            value = self.value()
            before = deepcopy(value)

            def validate(copy):
                if change == 'text':
                    copy['drafts'][0]['gaps']['title'] = 'Rewritten words '
                elif change == 'strip':
                    copy['drafts'][0]['gaps']['title'] = copy['drafts'][0]['gaps']['title'].strip()
                elif change == 'list_order':
                    copy['drafts'].reverse()
                else:
                    copy['default_added'] = True
                return copy

            with self.subTest(change=change), self.assertRaisesRegex(ValueError, '^structured_playback_result$'):
                self.module.validate_typed_reply(value, validate)
            self.assertEqual(value, before)

    def test_equal_python_scalars_do_not_hide_type_changes(self):
        for before, after in ((True, 1), (1, 1.0), (False, 0), (None, 'None')):
            with self.subTest(before=before, after=after):
                with self.assertRaises(ValueError):
                    self.module.validate_typed_reply({'value': before}, lambda value: {'value': after})

    def test_size_and_top_level_guards_run_before_validator(self):
        calls = []
        for value in ({'text': 'x' * 8193}, [], {'number': float('nan')}):
            with self.subTest(kind=type(value)), self.assertRaises(ValueError):
                self.module.validate_typed_reply(value, lambda copy: calls.append(copy) or copy)
        self.assertEqual(calls, [])

    def test_schema_rejection_is_generic_and_does_not_return_a_repair(self):
        def reject(value):
            raise ValueError('MODEL_BODY_CANARY')

        with self.assertRaises(ValueError) as caught:
            self.module.validate_typed_reply(self.value(), reject)
        self.assertEqual(str(caught.exception), 'structured_playback_result')
        self.assertTrue(caught.exception.__suppress_context__)


if __name__ == '__main__':
    unittest.main()
