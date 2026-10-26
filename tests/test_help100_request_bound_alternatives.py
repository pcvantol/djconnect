"""Cost-free new-source admission negatives; consumed executions stay immutable."""
from datetime import timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests.help_catalogue_history import original_catalogue_v1_case

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools/verification/run_help100_request_bound_alternatives_20261025.py'
SPEC = importlib.util.spec_from_file_location('request_bound_alternatives_help100_runner', RUNNER)
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)



class RequestBoundAlternativesOnceAdmissionTests(unittest.TestCase):
    def context(self):
        return {'GITHUB_REPOSITORY': 'pcvantol/djconnect', 'GITHUB_REF': 'refs/heads/main',
            'GITHUB_WORKFLOW_REF': r.WORKFLOW, 'GITHUB_ACTOR': 'pcvantol',
            'GITHUB_TRIGGERING_ACTOR': 'pcvantol', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
            'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1', 'DJC_HELP100_GRANT': r.GRANT,
            'GITHUB_RUN_ID': '123456', 'GITHUB_SHA': 'a' * 40, 'DJC_EXPECTED_MAIN_SHA': 'a' * 40}

    def test_only_new_grant_once_original_actor_main_sha_and_window(self):
        context = self.context()
        self.assertEqual(r.admit(context, r.START)['source'], 'a' * 40)
        for field, wrong in [('DJC_HELP100_GRANT', 'DJC-CORE-HELP100-ARTIST-ENVELOPE-20261025-ONCE'),
                ('DJC_HELP100_GRANT', 'DJC-CORE-HELP100-VERIFIED-DRAFTS-20261025-ONCE'),
                ('DJC_HELP100_GRANT', 'DJC-CORE-HELP100-DIRECT-HUMAN-20261024-FRESH'),
                ('GITHUB_RUN_NUMBER', '2'), ('GITHUB_RUN_ATTEMPT', '2'),
                ('GITHUB_REF', 'refs/heads/unreviewed'), ('GITHUB_ACTOR', 'another-actor'),
                ('DJC_EXPECTED_MAIN_SHA', 'b' * 40)]:
            with self.subTest(field=field, wrong=wrong), self.assertRaises(ValueError):
                r.admit(context | {field: wrong}, r.START)
        for stamp in (r.START - timedelta(seconds=1), r.LAST_START):
            with self.assertRaises(ValueError):
                r.admit(context, stamp)

    def test_actual_new_source_maps_and_original_base_seam_never_substitute_old_execution(self):
        # Unit CI is shallow; actual paid admission must independently verify
        # every original full-history Git blob before secret access.
        frozen = json.loads(RUNNER.with_name('help100_request_bound_alternatives_content_20261025.json').read_text())
        with patch.object(r, 'verify_original_base'), \
             patch.object(r.safe, 'product_hashes', return_value=frozen['product_hashes']), \
             patch.object(r, 'profile_source_hashes', return_value=frozen['profile_hashes']):
            pin = r.maps(ROOT)
        self.assertEqual(pin['source_base'], '3a71037097275c23366624564acb52e509f97f0a')
        self.assertEqual(len(pin['product_hashes']), 264)
        self.assertEqual(len(pin['profile_hashes']), 242)
        self.assertEqual(len(pin['reviewed_product_changes']), 2)
        changed = dict(pin['product_hashes'])
        changed[next(iter(changed))] = '0' * 64
        with patch.object(r, 'verify_original_base'), patch.object(r.safe, 'product_hashes', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'PRODUCT_CHANGED'):
                r.maps(ROOT)

    @original_catalogue_v1_case
    def test_artist_wire_requires_one_original_case_and_locale_not_any_five_records(self):
        from copy import deepcopy
        cases = [c for c in r.profile(ROOT).cases() if c['entry_id'] == 'listen.artist']
        rows = [{'case_id': c['id'], 'artist_generation_wire': {'research_schema': 3,
            'language': c['language'], 'drafts_requested': True, 'wire_contract_first': True,
            'trusted_instructions_sha256': str(i) * 64}} for i, c in enumerate(cases)]
        self.assertTrue(r.artist_wire_complete({'model_calls': rows}, cases))
        bad = [rows[:-1], rows + rows[:1], rows[:4] + rows[:1]]
        swapped = deepcopy(rows)
        swapped[0]['artist_generation_wire'], swapped[1]['artist_generation_wire'] = (
            swapped[1]['artist_generation_wire'], swapped[0]['artist_generation_wire'])
        bad.append(swapped)
        unknown = deepcopy(rows)
        unknown[0]['case_id'] = 'catalogue-play.artist-en'
        bad.append(unknown)
        for field, value in [('extra', True), ('research_schema', True), ('language', 'unknown'),
                ('drafts_requested', 1), ('wire_contract_first', 1), ('trusted_instructions_sha256', None)]:
            changed = deepcopy(rows)
            changed[-1]['artist_generation_wire'][field] = value
            bad.append(changed)
        for entries in bad:
            with self.subTest(entries=entries):
                self.assertFalse(r.artist_wire_complete({'model_calls': entries}, cases))
        self.assertFalse(r.artist_wire_complete({'model_calls': rows}, cases[:-1]))

    @original_catalogue_v1_case
    def test_previous_consumed_runner_workflow_and_map_remain_exact(self):
        expected = {'.github/workflows/help100-verified-drafts-20261025.yml': 'aa190966baeeb3ab1ed2295af15a5d8c1501c5c5d89330200b14ad66fd4c38db', 'tools/verification/run_help100_verified_drafts_20261025.py': 'f0467ae78fd6f1eddc6e42f34a8ff27740dce3de8a2be51b8f19468c416312f5', 'tools/verification/help100_verified_drafts_content_20261025.json': '2dadc11ec13fdaaff935c959a514ceaa7ca8dbbeb8abf81371034fec6cb3de14'}
        expected.update({'.github/workflows/help100-artist-envelope-20261025.yml': 'ee92043ac8a25d7df4458d017bb1c9d139d253f8e10733f7ec693ff58a3957aa', 'tools/verification/run_help100_artist_envelope_20261025.py': '6dca712899d882f01108a88dc91489078591919b4e39f0b36e4b1511e5d52f4f', 'tools/verification/help100_artist_envelope_content_20261025.json': 'a17e5500f8e13d8aa9bb1042ca33d702277024c544ce05b82330781e3801094f'})
        expected.update({'tools/verification/run_help100_artist_evidence_first_20261025.py': '84def98969f1921a47f8dbec1d89b13aa776198098cdc4c777eeb727a0e7aec8', '.github/workflows/help100-artist-evidence-first-20261025.yml': '159e417eff0b07534f26e6d76a76fae37894229dadada09676ffae8bd09c0810', 'tools/verification/help100_artist_evidence_first_content_20261025.json': '156d7f888fbf8398e658567237c03c939e130bb6a91b9506884e0306ca724abe'})
        expected.update({'.github/workflows/help100-public-source-witness-20261025.yml': 'ed3e3212f498780bda2ab708e82b0275f7c1f0f761d02180ab4dc74ff312b8e7', 'tools/verification/run_help100_public_source_witness_20261025.py': 'e0b05b5e45deefed574825a8b6e7f5b0b7a55a38395f2ef3bda23484478da674', 'tools/verification/help100_public_source_witness_content_20261025.json': '2e217c9446a18c5cb877c79d067e8b6719760757810d9d39972fe4403e3f8676'})
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)
        text = (ROOT / '.github/workflows/help100-request-bound-alternatives-20261025.yml').read_text()
        self.assertEqual(text.count('ref: ${{ github.sha }}'), 2)
        self.assertEqual(text.count('secrets.DJCONNECT_GOLDEN_OPENAI_API_KEY'), 1)
        self.assertNotIn('continue-on-error', text)
        self.assertNotIn('private.log\n', text)
        self.assertNotIn('private-work', text)
        self.assertNotIn('\n  push:', text)
        self.assertEqual(r.MAX_SECONDS, 1800)
        self.assertEqual(r.profile(ROOT).MAX_MODEL_CALLS, 392)
        self.assertEqual(r.profile(ROOT).MAX_OUTPUT_TOKENS, 3000)


if __name__ == '__main__':
    unittest.main()
