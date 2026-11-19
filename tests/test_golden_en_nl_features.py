"""Reject incomplete, wrong-language or effectful functional Golden receipts."""
from copy import deepcopy
import unittest
from scripts.verification.golden_en_nl_features import HTTP_CASES, findings


class GoldenFeatureReceiptTests(unittest.TestCase):
    def receipt(self, harness, locale):
        return {'source_unchanged': True, 'extension': {'language': locale,
            'cases': {name.format(locale=locale): 'PASS' for name in HTTP_CASES[harness]},
            'real_provider_calls': 0, 'model_provider_calls': 0,
            'real_model_provider_calls': 0, 'real_spotify_calls': 0, 'music_or_audio_effects': 0}}

    def test_every_required_negative_scenario_must_actually_execute(self):
        for harness in HTTP_CASES:
            for locale in ('en', 'nl'):
                receipt = self.receipt(harness, locale)
                self.assertEqual(findings(harness, locale, receipt), [])
                for case in receipt['extension']['cases']:
                    missing = deepcopy(receipt)
                    del missing['extension']['cases'][case]
                    self.assertTrue(findings(harness, locale, missing), case)
                    missing['extension']['cases'][case] = 'FAIL'
                    self.assertTrue(findings(harness, locale, missing), case)

    def test_english_receipt_cannot_stand_in_for_dutch(self):
        harness = 'verify_music_announcement_http'
        self.assertIn('wrong_language', findings(harness, 'nl', self.receipt(harness, 'en')))
        self.assertEqual(findings(harness, 'de', self.receipt(harness, 'de')), ['unexpected_scope'])

    def test_mutated_source_and_real_provider_effect_are_not_fixture_qualification(self):
        harness = 'verify_music_announcement_http'
        receipt = self.receipt(harness, 'nl')
        receipt['source_unchanged'] = False
        self.assertEqual(findings(harness, 'nl', receipt), ['source_not_stable'])
        receipt = self.receipt(harness, 'nl')
        for counter in ('real_model_provider_calls', 'real_spotify_calls', 'music_or_audio_effects'):
            changed = deepcopy(receipt)
            changed['extension'][counter] = 1
            self.assertIn('unexpected_external_effect', findings(harness, 'nl', changed))
