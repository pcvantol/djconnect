"""Cross-parser admission decision corpus, without pretending to prove live trust."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('display_route_review', ROOT/'scripts/verification/vibecast_display_route_contract.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class DisplayRouteReviewTests(unittest.TestCase):
    def test_python_parser_matches_every_explicit_review_decision(self):
        corpus = json.loads((ROOT/'examples/client_contracts/vibecast_display_admission_v1/route-cases.json').read_text())
        self.assertEqual(corpus['status'], 'REVIEW_CANDIDATE_NOT_FROZEN')
        self.assertFalse(corpus['network_fetches'])
        ids = [c['id'] for c in corpus['cases']]
        self.assertEqual(len(ids), len(set(ids)))
        for case in corpus['cases']:
            with self.subTest(case=case['id']):
                self.assertEqual(policy.lexical_route_allowed(case['entry_url'], case['selected_origin']), case['allowed'])

    def test_independent_whatwg_consumer_agrees_without_fetching_destinations(self):
        result = subprocess.run(['node', str(ROOT/'scripts/verification/vibecast_display_route_contract.mjs')],
                                check=True, capture_output=True, text=True, timeout=10)
        result = json.loads(result.stdout)
        self.assertEqual(result['result'], 'PASS_WHATWG_LEXICAL_CORPUS_ONLY')
        self.assertFalse(result['network_fetches'])

    def test_bounded_invalid_input_fails_closed(self):
        for value in (None, 1, {}, [], 'https://[invalid', 'https://ha.example.org:bad/djconnect/vibecast/display',
                      'https://'+('a'*2049)):
            with self.subTest(value_type=type(value).__name__):
                self.assertFalse(policy.lexical_route_allowed(value, 'https://ha.example.org'))
