"""Current producer joins original actual HA proof; no quality/install claim."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AnnouncementContractTests(unittest.TestCase):
    def test_current_producer_and_manual_replay_match_original_actual_ha(self):
        record = json.loads((ROOT/'examples/client_contracts/music_announcement_v1/actual-ha-wire.json').read_text())
        self.assertTrue(record['source_before_after_equal'])
        self.assertEqual(len(record['source_pins']), 308)
        for name, digest in record['source_pins'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((ROOT/record['harness']).read_bytes()).hexdigest(), record['harness_sha256'])
        receipt = record['receipt']
        self.assertTrue(receipt['source_unchanged'])
        extension = receipt['extension']
        self.assertEqual(set(extension['cases'].values()), {'PASS'})
        self.assertEqual(extension['synthetic_model_response_calls'], 43)
        self.assertEqual(extension['real_model_provider_calls'], 0)
        self.assertEqual(extension['real_spotify_calls'], 0)
        self.assertEqual(extension['music_or_audio_effects'], 0)
        self.assertEqual(extension['native_installed_audible_acceptance'], 'NOT_RUN')
        self.assertIn('actual_text_only_local_manual_archive_replay_without_generation_or_session_restart', extension['cases'])
        self.assertIn('six_second_generation_preserves_original_UTC_deadline', extension['cases'])
        self.assertIn('metadata_only_realization_becomes_one_persona_intro_with_manual_replay', extension['cases'])
        examples = extension['examples']
        self.assertEqual(len({e['moment']['moment_id'] for e in examples}), 20)
        self.assertTrue(all(e['moment']['type'] == 'music_announcement' for e in examples))
        self.assertTrue(all(e['moment']['title'] == 'Muziek aankondiging' for e in examples))
