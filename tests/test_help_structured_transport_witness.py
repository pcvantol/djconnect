"""Tamper controls over extracted actual cost-free SDK transport evidence."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from tools.verification import help_content_probe as policy
from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases

ROOT = Path(__file__).resolve().parents[1]


class StructuredTransportWitnessTests(unittest.TestCase):
    def setUp(self):
        fixture = json.loads((ROOT / 'tests/fixtures/help_public_task/selected24-actual-sdk-transport.json').read_text())
        self.assertEqual(fixture['scope'], 'EXTRACTED_COSTFREE_ACTUAL_SDK_TRANSPORT_ONLY_NOT_MODEL_QUALITY')
        self.report = fixture['report']
        self.original = cases() + chain_cases()
        self.selected = [row for row in self.original if row['id'] in policy.TARGET24_DELIVERY_V3]

    def good(self, report):
        return policy.structured_playback_inputs_complete(report, cases=self.selected)

    def typed(self, report):
        return [row for row in report['model_calls'] if 'structured_output_format' in row]

    def test_original_sdk_witness_covers_all_original_effects_but_is_not_full100_or_content_proof(self):
        self.assertTrue(self.good(self.report))
        self.assertEqual(len(self.typed(self.report)), 12)
        self.assertEqual(sum(row['expected']['effect'] in {'artist_play', 'playlist_play', 'album_play'}
                             for row in self.original), 25)
        self.assertFalse(policy.structured_playback_inputs_complete(self.report, cases=self.original))
        self.assertFalse(policy.validate_selected_report(self.report, {}, pin={}, mode='target24_delivery_v3'))

    def test_missing_partial_duplicate_extra_and_swapped_original_witnesses_are_denied(self):
        mutations = []
        missing = deepcopy(self.report)
        missing.pop('playback_generation_transport')
        mutations.append(missing)
        for key in ('structured_output_format', 'structured_playback_generation', 'structured_playback_input',
                    'provider_tools_absent', 'provider_store_false'):
            changed = deepcopy(self.report)
            self.typed(changed)[0].pop(key)
            mutations.append(changed)
        stripped = deepcopy(self.report)
        for row in stripped['model_calls']:
            for key in list(row):
                if key.startswith(('structured_', 'provider_')):
                    row.pop(key)
        mutations.append(stripped)
        duplicate = deepcopy(self.report)
        duplicate['model_calls'].append(deepcopy(self.typed(duplicate)[0]))
        mutations.append(duplicate)
        extra = deepcopy(self.report)
        row = deepcopy(self.typed(extra)[0])
        row['case_id'] = 'catalogue-listen.artist-en'
        extra['model_calls'].append(row)
        mutations.append(extra)
        swapped = deepcopy(self.report)
        left, right = self.typed(swapped)[:2]
        left['structured_playback_generation'], right['structured_playback_generation'] = (
            right['structured_playback_generation'], left['structured_playback_generation'])
        mutations.append(swapped)
        for changed in mutations:
            self.assertFalse(self.good(changed))

    def test_closed_schema_roles_hash_and_json_scalar_domains_cannot_be_weakened(self):
        mutations = []
        for bad in (1, 'true', False):
            changed = deepcopy(self.report)
            self.typed(changed)[0]['structured_output_format']['strict'] = bad
            mutations.append(changed)
        for bad in (True, 1.0, 0, 3):
            changed = deepcopy(self.report)
            self.typed(changed)[0]['structured_output_format']['schema']['properties']['drafts']['minItems'] = bad
            mutations.append(changed)
        for path in ('root', 'draft', 'gaps'):
            changed = deepcopy(self.report)
            schema = self.typed(changed)[0]['structured_output_format']['schema']
            if path != 'root':
                schema = schema['properties']['drafts']['items']
            if path == 'gaps':
                schema = schema['properties']['gaps']
            schema['additionalProperties'] = 0  # False==0 must not admit this.
            mutations.append(changed)
        for marker in ('structured_playback_generation', 'structured_playback_input'):
            changed = deepcopy(self.report)
            self.typed(changed)[0][marker]['prompt_sha256'] = '0' * 64
            mutations.append(changed)
            changed = deepcopy(self.report)
            self.typed(changed)[0][marker]['role_order'].append('unowned_role')
            mutations.append(changed)
        for changed in mutations:
            self.assertFalse(self.good(changed))


if __name__ == '__main__':
    unittest.main()
