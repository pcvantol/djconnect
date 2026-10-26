"""Tamper controls over extracted actual HA provider-format witnesses."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.verification.artist_typed_receipts import complete, canonical
from tools.verification.help_content_probe import EN_NL_ARTIST2


class ArtistTypedWitnessTests(unittest.TestCase):
    def setUp(self):
        value = json.loads((Path(__file__).parent / 'fixtures/help_public_task/en-nl2-actual-sdk-typed-v2.json').read_text())
        self.assertEqual(value['scope'], 'EXTRACTED_COSTFREE_ACTUAL_HA_TYPED_SDK_BOUNDARY_ONLY_NOT_CONTENT_OR_CURRENT_SOURCE_GO')
        self.report = value['report']

    def good(self, value):
        return complete(value, expected_cases=EN_NL_ARTIST2)

    def test_actual_four_original_typed_sdk_calls_join_but_not_another_scope(self):
        self.assertTrue(self.good(self.report))
        self.assertEqual(len(self.report['model_calls']), 4)
        self.assertFalse(complete(self.report, expected_cases=EN_NL_ARTIST2[:1]))

    def test_missing_duplicate_swapped_boolean_identity_and_unknown_operation_fail(self):
        variants = []
        for field in ('structured_artist_operation', 'structured_artist_input', 'structured_output_format',
                      'provider_store_false', 'provider_tools_absent'):
            value = deepcopy(self.report)
            value['model_calls'][0].pop(field)
            variants.append(value)
        value = deepcopy(self.report)
        value['model_calls'].append(deepcopy(value['model_calls'][0]))
        variants.append(value)
        for key, bad in [('schema_version', True), ('operation', 'future_operation'),
                         ('prompt_sha256', '0' * 64), ('binding_sha256', '0' * 64)]:
            value = deepcopy(self.report)
            value['model_calls'][0]['structured_artist_operation'][key] = bad
            variants.append(value)
        value = deepcopy(self.report)
        first, second = value['model_calls'][:2]
        first['structured_artist_input'], second['structured_artist_input'] = (
            second['structured_artist_input'], first['structured_artist_input'])
        variants.append(value)
        for value in variants:
            self.assertFalse(self.good(value))

    def test_schema_cannot_force_positive_booleans_or_drop_bounds_or_allow_extras(self):
        for field in ('supported', 'style_ok', 'language_ok'):
            value = deepcopy(self.report)
            call = next(c for c in value['model_calls']
                        if c['structured_artist_operation']['operation'] == 'artist_word_review_v1')
            fields = call['structured_output_format']['schema']['properties']['draft_reviews']['items']['properties']['review']['properties']
            self.assertEqual(fields[field], {'type': 'boolean'})
            fields[field]['const'] = True
            self.assertFalse(self.good(value))
        for mutation in ('extra', 'max', 'strict'):
            value = deepcopy(self.report)
            fmt = value['model_calls'][0]['structured_output_format']
            if mutation == 'extra':
                fmt['schema']['additionalProperties'] = 0
            elif mutation == 'max':
                fmt['schema']['properties']['drafts']['maxItems'] = 2
            else:
                fmt['strict'] = 1
            self.assertFalse(self.good(value))
        # Even syntactically matching known schema must bind the original text.
        value = deepcopy(self.report)
        call = next(c for c in value['model_calls'] if 'artist_answer_review' in c)
        call['structured_artist_input']['drafts'][0]['text'] += ' changed'
        self.assertFalse(self.good(value))
        self.assertNotEqual(canonical(False), canonical(0))


if __name__ == '__main__':
    unittest.main()
