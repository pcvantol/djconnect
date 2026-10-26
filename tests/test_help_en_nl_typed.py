"""Original scope, immutable bindings and negative verdict preservation."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
import unittest

from tests import test_ask_dj_contextual_dialogue as shared
from tools.verification import help_content_probe as policy
from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases, manifest_digest


class EnNlScopeTests(unittest.TestCase):
    def test_closed_original_scope_keeps_questions_effects_order_and_historical_manifest(self):
        original = cases() + chain_cases()
        full = tuple(c['id'] for c in original if c['language'] in ('en', 'nl'))
        self.assertEqual(policy.EN_NL_FULL40, full)
        self.assertEqual(len(full), 40)
        for locale in ('en', 'nl'):
            self.assertEqual(sum(c['language'] == locale for c in original if c['id'] in full), 20)
        self.assertEqual(policy.EN_NL_DELIVERY13, tuple(c['id'] for c in original
            if c['id'] in policy.TARGET24_DELIVERY_V3 and c['language'] in ('en', 'nl')))
        self.assertEqual(policy.EN_NL_ARTIST2, tuple(c['id'] for c in original
            if c['entry_id'] == 'listen.artist' and c['language'] in ('en', 'nl')))
        self.assertEqual(manifest_digest(), policy.MANIFEST)
        for mode, count, maximum, seconds in [('en_nl_artist2_v1', 2, 10, 300),
                ('en_nl_delivery13_v1', 13, 52, 600), ('en_nl_full40_v1', 40, 160, 900)]:
            selected, attempts, duration = policy.mode_policy(mode)
            self.assertEqual((len(selected), attempts, duration), (count, maximum, seconds))
            self.assertTrue(selected)  # Never reuse the historical full100 sentinel.
        self.assertEqual(policy.mode_policy('full100'), ((), 392, 1800))


class ArtistTaskBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.a = importlib.import_module('custom_components.djconnect.structured_artist')
        cls.n = importlib.import_module('custom_components.djconnect.narration_brief')
        cls.w = importlib.import_module('custom_components.djconnect.artist_review_words')
        cls.transport = importlib.import_module('custom_components.djconnect.structured_playback')

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def capture(self):
        drafts = self.n.verified_drafts(json.dumps({'drafts':['Volbeat performed a concert.']}), str.strip)
        words = self.w.AnswerWordReview.capture(drafts)
        prompt = 'Instructions\nData:\n' + json.dumps({'drafts': words.records(),
            'evidence': {'original_sources': ['Not trimmed or simplified']}})
        return drafts, words, prompt, self.a.review(prompt, words, drafts)

    def test_original_text_whitespace_unicode_word_addresses_and_hash_bound_before_await(self):
        drafts, words, prompt, operation = self.capture()
        original = deepcopy(words.records())
        self.assertEqual(operation.drafts, ((0, hashlib.sha256(drafts.texts[0].encode()).hexdigest(),
                                             tuple(row[0] for row in original[0]['answer_words'])),))
        self.assertEqual(operation.prompt_sha256, hashlib.sha256(prompt.encode()).hexdigest())
        witness = operation.witness()
        witness['drafts'][0][2][0] = 'foreign-word'
        self.assertEqual(words.records(), original)
        self.assertEqual(operation.witness()['drafts'][0][2][0], 'd0w0')
        for mutation in ('text', 'hash', 'word', 'index', 'extra'):
            data = json.loads(prompt.split('\nData:\n')[1])
            row = data['drafts'][0]
            if mutation == 'text':
                row['text'] += ' changed'
            elif mutation == 'hash':
                row['sha256'] = '0' * 64
            elif mutation == 'word':
                row['answer_words'][0][1] = 'invented'
            elif mutation == 'index':
                row['index'] = False
            else:
                row['extra'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.a.review('Instructions\nData:\n' + json.dumps(data), words, drafts)
        with self.assertRaises(ValueError):
            self.a.review(prompt, replace(words, texts=('Changed original.',)), drafts)

    def test_completed_malformed_nl_json_cannot_be_salvaged_from_positive_booleans(self):
        drafts, words, _, _ = self.capture()
        review = {'draft_reviews':[{'index':0,'sha256':drafts.records()[0]['sha256'],
            'review':{'review_schema':self.w.SCHEMA,'supported':True,'language_ok':True,
                'style_ok':True,'unsupported_claims':[], 'claim_checks':[
                    {'answer_from':'d0w0','answer_to':'d0w3','kind':'fact','evidence_ids':['real:p0']}],
                'temporal_claims':[]}}]}
        valid = json.dumps(review)
        self.assertEqual(len(words.decode(valid, drafts)), 1)
        # Same missing enclosing array boundary as the original completed NL failure.
        broken = valid[:-2] + '}'
        with self.assertRaises(ValueError):
            words.decode(broken, drafts)
        # A typed dictionary is prospective input, never a repair of that raw body.
        wire = self.transport.validate_typed_reply(review, lambda value: value)
        self.assertEqual(json.loads(wire), review)
        for flag in ('supported', 'language_ok', 'style_ok'):
            negative = deepcopy(review)
            negative['draft_reviews'][0]['review'][flag] = False
            if flag == 'supported':
                negative['draft_reviews'][0]['review'].update(unsupported_claims=[drafts.texts[0]],
                                                            claim_checks=[])
            wire = self.transport.validate_typed_reply(negative, lambda value: value)
            self.assertFalse(json.loads(words.decode(wire, drafts)[0])[flag])


if __name__ == '__main__':
    unittest.main()
