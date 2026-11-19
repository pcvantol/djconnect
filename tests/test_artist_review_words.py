"""Addresses remove recopy errors, never the original semantic evidence gate."""
import hashlib
import importlib
import json
import unittest
from dataclasses import replace

from tests import test_ask_dj_contextual_dialogue as shared


class AnswerWordReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.n = importlib.import_module('custom_components.djconnect.narration_brief')
        cls.w = importlib.import_module('custom_components.djconnect.artist_review_words')

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def pool(self, *texts):
        return self.n.verified_drafts(json.dumps({'drafts': texts}, ensure_ascii=False), str.strip)

    def wire(self, capture, *, ranges=None):
        rows = []
        for row in capture.records():
            words = row.pop('answer_words')
            row.pop('text')
            claims = ranges or [(words[0][0], words[-1][0])]
            row['review'] = {'review_schema': self.w.SCHEMA, 'supported': True,
                'language_ok': True, 'style_ok': True, 'unsupported_claims': [],
                'claim_checks': [{'answer_from': start, 'answer_to': end,
                    'kind': 'fact', 'evidence_ids': ['real-source:p0']} for start, end in claims]}
            rows.append(row)
        return {'draft_reviews': rows}

    def test_exact_unicode_slices_original_spaces_punctuation_and_namespaces(self):
        text = 'Één\u00a0🎸 e\u0301én\nwoord.  L’artiste speelt.'
        pool = self.pool(text, 'Otro texto.')
        capture = self.w.AnswerWordReview.capture(pool)
        wire = self.wire(capture)
        wire['draft_reviews'][0]['review']['claim_checks'] = [
            {'answer_from': 'd0w0', 'answer_to': 'd0w3', 'kind': 'fact', 'evidence_ids': ['real-source:p0']},
            {'answer_from': 'd0w4', 'answer_to': 'd0w5', 'kind': 'fact', 'evidence_ids': ['real-source:p0']}]
        reviews = capture.decode(json.dumps(wire), pool)
        self.assertEqual([claim['text'] for claim in json.loads(reviews[0])['claim_checks']],
            ['Één\u00a0🎸 e\u0301én\nwoord.', 'L’artiste speelt.'])
        self.assertEqual(json.loads(reviews[1])['claim_checks'][0]['text'], 'Otro texto.')
        self.assertEqual(capture.records()[1]['answer_words'][0], ['d1w0', 'Otro'])
        prompt = 'Instructions\nData:\n' + json.dumps({'answer': text, 'evidence': {'untouched': True}})
        projected = json.loads(capture.prompt(prompt, pool).split('\nData:\n')[1])
        self.assertEqual(projected['drafts'], capture.records())
        projected['drafts'][0]['answer_words'][0][1] = 'MUTATED'
        self.assertEqual(capture.records()[0]['answer_words'][0][1], 'Één')

    def test_bad_comma_is_not_repaired_but_new_addresses_never_copy_it(self):
        pool = self.pool('Ik vind het boeiend dat Volbeat optrad.')
        capture = self.w.AnswerWordReview.capture(pool)
        wire = self.wire(capture, ranges=[('d0w0', 'd0w3'), ('d0w4', 'd0w6')])
        review = json.loads(capture.decode(json.dumps(wire), pool)[0])
        self.assertEqual(review['claim_checks'][0]['text'], 'Ik vind het boeiend')
        self.assertEqual(review['claim_checks'][1]['text'], 'dat Volbeat optrad.')
        # New wire cannot accept copied text, even when every flag is true.
        wire['draft_reviews'][0]['review']['claim_checks'][0]['text'] = 'Ik vind het boeiend,'
        with self.assertRaises(ValueError):
            capture.decode(json.dumps(wire), pool)
        wire['draft_reviews'][0]['review']['review_schema'] = 'source_id_review_v1'
        with self.assertRaises(ValueError):
            capture.decode(json.dumps(wire), pool)

    def test_all_rows_hash_index_order_original_identity_before_any_verdict(self):
        pool = self.pool('One sentence.', 'Another sentence.')
        capture = self.w.AnswerWordReview.capture(pool)
        for mutation in ('hash', 'index', 'bool', 'extra', 'missing', 'reverse', 'catalog'):
            wire = self.wire(capture)
            if mutation == 'hash':
                wire['draft_reviews'][1]['sha256'] = '0' * 64
            elif mutation == 'index':
                wire['draft_reviews'][1]['index'] = 0
            elif mutation == 'bool':
                wire['draft_reviews'][0]['index'] = False
            elif mutation == 'extra':
                wire['draft_reviews'][1]['extra'] = 0
            elif mutation == 'missing':
                wire['draft_reviews'].pop()
            elif mutation == 'reverse':
                wire['draft_reviews'].reverse()
            else:
                wire['draft_reviews'][1]['answer_words'] = []
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                capture.decode(json.dumps(wire), pool)
        with self.assertRaises(ValueError):
            replace(capture, words=(capture.words[1], capture.words[0])).decode(json.dumps(self.wire(capture)), pool)
        with self.assertRaises(ValueError):
            capture.decode(json.dumps(self.wire(capture)), self.pool('Changed sentence.', 'Another sentence.'))

    def test_unknown_noncanonical_ids_gaps_overlap_reverse_cross_draft_and_types(self):
        pool = self.pool('One two three four.')
        capture = self.w.AnswerWordReview.capture(pool)
        bad_ranges = [[('d0w1', 'd0w3')], [('d0w0', 'd0w2')], [('d0w0', 'd0w1'), ('d0w1', 'd0w3')],
            [('d0w0', 'd0w0'), ('d0w2', 'd0w3')], [('d0w0', 'd0w3'), ('d0w3', 'd0w0')],
            [('d0w0', 'd1w3')], [('d0w00', 'd0w3')], [('D0w0', 'd0w3')],
            [(0, 'd0w3')], [(True, 'd0w3')], [(0.0, 'd0w3')], [('d0w0', [])]]
        for ranges in bad_ranges:
            with self.subTest(ranges=ranges), self.assertRaises(ValueError):
                capture.decode(json.dumps(self.wire(capture, ranges=ranges)), pool)

    def test_closed_negative_and_original_temporal_shape_are_still_required(self):
        pool = self.pool('Invented story.')
        capture = self.w.AnswerWordReview.capture(pool)
        negative = self.wire(capture)
        review = negative['draft_reviews'][0]['review']
        review.update(supported=False, unsupported_claims=['Invented'], claim_checks=[], temporal_claims=[])
        self.assertFalse(json.loads(capture.decode(json.dumps(negative), pool)[0])['supported'])
        for key, value in (('unsupported_claims', ['foreign']), ('claim_checks', self.wire(capture)['draft_reviews'][0]['review']['claim_checks']),
                ('temporal_claims', None), ('supported', 0), ('language_ok', 1), ('unknown', True)):
            bad = json.loads(json.dumps(negative))
            bad['draft_reviews'][0]['review'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                capture.decode(json.dumps(bad), pool)
        review.pop('temporal_claims')
        with self.assertRaises(ValueError):
            capture.decode(json.dumps(negative), pool)

    def test_bounded_raw_duplicate_json_nesting_tokens_and_whole_claim(self):
        pool = self.pool('A whole original sentence.')
        capture = self.w.AnswerWordReview.capture(pool)
        valid = json.dumps(self.wire(capture))
        for raw in (' ' * 8193 + valid, valid.replace('"supported": true', '"supported": true, "supported": false'),
                '[' * 18 + valid + ']' * 18, valid.replace('true', 'NaN', 1)):
            with self.assertRaises((ValueError, RecursionError)):
                capture.decode(raw, pool)
        for text in ('   ', 'w ' * 513, 'x' * 8193):
            with self.assertRaises(ValueError):
                self.w.AnswerWordReview.capture(self.n.VerifiedDrafts((text,), True))
        huge = self.pool('x' * 1201)
        with self.assertRaises(ValueError):
            self.w.AnswerWordReview.capture(huge).decode(json.dumps(self.wire(self.w.AnswerWordReview.capture(huge))), huge)

    def test_valid_addresses_do_not_admit_wrong_roles_years_or_source_ids(self):
        from custom_components.djconnect.ask_dj import public_research
        from custom_components.djconnect.public_artist_narration import resolve_review_quotes
        excerpt = 'Volbeat performed a concert.'
        digest = hashlib.sha256(excerpt.encode()).hexdigest()
        identifier = digest[:16] + ':p0'
        source = {'content_hash': digest, 'untrusted_excerpt': excerpt,
            'evidence_schema': 'original_paragraphs_v1', 'original_document_hash': digest,
            'literal_passages': [{'text': excerpt, 'original_range': [0, len(excerpt)]}],
            'evidence_spans': [{'id': identifier, 'text': excerpt, 'original_range': [0, len(excerpt)]}]}
        context = {'public_music_research': {'schema_version': 3, 'sources': [source]}}
        for text, accepted in ((excerpt, True), ('Volbeat produced a concert.', False),
                ('Volbeat performed a concert in 1999.', False)):
            pool = self.pool(text)
            capture = self.w.AnswerWordReview.capture(pool)
            wire = self.wire(capture)
            wire['draft_reviews'][0]['review']['claim_checks'][0]['evidence_ids'] = [identifier]
            review = json.loads(capture.decode(json.dumps(wire), pool)[0])
            review.pop('language_ok')
            review.pop('style_ok')
            resolved = resolve_review_quotes(review, context)
            self.assertEqual(public_research.supported(json.dumps(resolved), text, context), accepted)
            wire['draft_reviews'][0]['review']['claim_checks'][0]['evidence_ids'] = ['foreign']
            review = json.loads(capture.decode(json.dumps(wire), pool)[0])
            review.pop('language_ok')
            review.pop('style_ok')
            with self.assertRaises(ValueError):
                resolve_review_quotes(review, context)

    def test_independent_actual_sdk_witness_rejects_stripped_or_rehashed_mutations(self):
        from scripts.verification.artist_answer_review_receipts import (
            answer_word_reviews_complete, capture_answer_review)
        pool = self.pool('Volbeat performed.')
        capture = self.w.AnswerWordReview.capture(pool)
        projection = {'drafts': capture.records(), 'private': 'PRIVATE_NEVER_EXPORT'}
        witness = capture_answer_review([{'role': 'user',
            'content': 'Instructions\nData:\n' + json.dumps(projection)}])
        self.assertNotIn('PRIVATE_NEVER_EXPORT', json.dumps(witness))
        case = 'catalogue-listen.artist-en'
        report = {'model_calls': [{'case_id': case, 'completed': True,
            'terminal_event': 'response.completed', 'artist_answer_review': witness,
            'generated_text': json.dumps(self.wire(capture))}]}
        self.assertTrue(answer_word_reviews_complete(report, expected_cases=[case]))
        for mutation in ('missing', 'duplicate', 'case', 'hash', 'text', 'word', 'extra_input',
                'index', 'returned_hash', 'gap', 'overlap', 'old_schema', 'extra_claim',
                'copied_text', 'failed', 'incomplete', 'purpose', 'duplicate_json', 'negative'):
            changed = json.loads(json.dumps(report))
            call = changed['model_calls'][0]
            review = json.loads(call['generated_text'])
            row = call['artist_answer_review']['drafts'][0]
            if mutation == 'missing':
                call.pop('artist_answer_review')
            elif mutation == 'duplicate':
                changed['model_calls'].append(call)
            elif mutation == 'case':
                call['case_id'] = 'catalogue-listen.artist-nl'
            elif mutation == 'hash':
                row['sha256'] = '0' * 64
            elif mutation == 'text':
                row['text'] = 'Volbeat produced.'
                row['sha256'] = hashlib.sha256(row['text'].encode()).hexdigest()
            elif mutation == 'word':
                row['answer_words'][0][0] = 'd0w00'
            elif mutation == 'extra_input':
                row['private'] = 'FORBIDDEN'
            elif mutation == 'index':
                row['index'] = False
            elif mutation == 'returned_hash':
                review['draft_reviews'][0]['sha256'] = '0' * 64
            elif mutation == 'gap':
                review['draft_reviews'][0]['review']['claim_checks'][0]['answer_from'] = 'd0w1'
            elif mutation == 'overlap':
                review['draft_reviews'][0]['review']['claim_checks'] *= 2
            elif mutation == 'old_schema':
                review['draft_reviews'][0]['review']['review_schema'] = 'source_id_review_v1'
            elif mutation in ('extra_claim', 'copied_text'):
                review['draft_reviews'][0]['review']['claim_checks'][0]['text'] = 'Volbeat performed.'
            elif mutation == 'failed':
                call['completed'] = False
            elif mutation == 'incomplete':
                call['terminal_event'] = 'stream_closed_without_terminal'
            elif mutation == 'purpose':
                call['purpose'] = 'answer_language_judge'
            elif mutation == 'negative':
                review['draft_reviews'][0]['review'].update(supported=False, claim_checks=[])
            if mutation == 'duplicate_json':
                call['generated_text'] = call['generated_text'].replace('"supported": true', '"supported": true, "supported": false')
            else:
                call['generated_text'] = json.dumps(review)
            with self.subTest(mutation=mutation):
                self.assertFalse(answer_word_reviews_complete(changed, expected_cases=[case]))
