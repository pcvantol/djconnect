"""Current original isolated-HA receipt integrity, not installed prose quality."""
import hashlib
import json
from pathlib import Path
import unittest


class PersonaStoryActualHATest(unittest.TestCase):
    def fixture(self):
        root = Path(__file__).resolve().parents[1]
        return root, json.loads((root/'examples/client_contracts/personal_dj_artist_story_v1/actual-ha-current.json').read_text())

    def test_current_source_and_verifiers_are_bound_to_the_original_actual_ha_trace(self):
        root, receipt = self.fixture()
        current = json.loads((root / 'examples/client_contracts/personal_dj_artist_story_v1/actual-ha-requalification-1439-after-1429.json').read_text())
        self.assertTrue(current['source_before_after_equal'])
        self.assertEqual(current['harness'], receipt['harness'])
        self.assertEqual(current['harness_sha256'], receipt['harness_sha256'])
        self.assertEqual(len(current['source_pins']), 305)
        for name, digest in {**current['source_pins'], **current['receipt']['source_files_sha256'],
                             receipt['harness']: receipt['harness_sha256']}.items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest, name)
        self.assertTrue(receipt['all304_before_inside_after_equal'])
        self.assertTrue(receipt['own_container_verified_absent'])
        self.assertIn('NOT_REAL_PROSE_OR_INSTALLED', receipt['classification'])
        self.assertEqual((receipt['external_network_calls'], receipt['paid_model_calls']), (0, 0))
        extension = current['receipt']['extension']
        self.assertEqual(len(extension['cases']), 20)
        self.assertEqual({row['state'] for row in extension['cases']}, {'PASS'})
        self.assertEqual((extension['external_network_calls'], extension['paid_model_calls']), (0, 0))

    def test_all_persona_locale_pairs_include_success_and_closed_failure_without_metadata_publication(self):
        _, receipt = self.fixture()
        rows = receipt['cases']
        self.assertEqual({(r['persona'], r['locale']) for r in rows},
            {(persona, locale) for persona in ('home_dj', 'radio_dj', 'club_dj', 'festival_dj')
             for locale in ('en', 'nl', 'de', 'fr', 'es')})
        self.assertEqual(len(rows), 20)
        self.assertEqual({r['state'] for r in rows}, {'PASS'})
        for row in rows:
            self.assertEqual(row['accepted_moments'], int(row['mode'] == 'accepted'))
            self.assertEqual(row['declared_synthetic_model_responses'], 1 if row['mode'] == 'failure' else 2)
        self.assertEqual({r['mode'] for r in rows}, {'accepted', 'failure', 'rejected'})
        self.assertEqual(receipt['declared_synthetic_model_responses'], 39)
        self.assertEqual(receipt['independent_artist_source_reads'], 60)
