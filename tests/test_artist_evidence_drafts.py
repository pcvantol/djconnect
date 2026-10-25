"""Literal membership is steering; only the original independent review admits prose."""
import asyncio
from dataclasses import replace
import hashlib
import importlib
import json
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


class ArtistEvidenceDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.n = importlib.import_module('custom_components.djconnect.narration_brief')

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def research(self, texts=None):
        texts = texts or ('Volbeat performed a concert with another band.',
                         'Volbeat released a studio album with original songs.')
        excerpt = '\n'.join(texts)
        digest = hashlib.sha256(excerpt.encode()).hexdigest()
        position, passages = 0, []
        for text in texts:
            passages.append({'text': text, 'original_range': [position, position + len(text)]})
            position += len(text) + 1
        return {'schema_version': 3, 'status': {'state': 'available', 'wikipedia': 'fetched', 'web': 'unavailable', 'requests': 7},
            'sources': [{'content_hash': digest,
            'untrusted_excerpt': excerpt, 'evidence_schema': 'original_paragraphs_v1',
            'literal_passages': passages, 'original_document_hash': digest,
            'evidence_spans': [{'id': digest[:16] + ':p' + str(i), **passage}
                for i, passage in enumerate(passages)]}]}

    def corpus(self):
        return self.n.artist_anchor_corpus(self.research())

    def wire(self, corpus):
        return {'schema': 'artist_evidence_drafts_v1', 'drafts': [
            {'anchors': [row['id']], 'text': text} for row, text in zip(corpus.projection(),
                ('First complete supported telling.', 'Second complete supported telling.'), strict=True)]}

    def test_literal_codepoint_hash_commitment_and_whole_text_selection(self):
        corpus = self.corpus()
        corpus.validate()
        self.assertEqual(len(corpus.records), 2)
        for record in corpus.records:
            source = next(s for s in corpus.spans if s[0] == record.source_id and s[1] == record.evidence_id)
            self.assertEqual(record.literal, source[2][record.start:record.end])
            self.assertEqual(record.literal_sha256, hashlib.sha256(record.literal.encode()).hexdigest())
            self.assertEqual(len(record.id), 64)
        pool = self.n.artist_evidence_drafts(json.dumps(self.wire(corpus)), corpus, str.strip)
        self.assertTrue(pool.batch)
        self.assertEqual(pool.texts[1], 'Second complete supported telling.')
        # Literal membership does not assert either generated sentence is true.
        self.assertNotEqual(pool.texts[0], corpus.records[0].literal)
        for field, value in [('start', True), ('end', 9999), ('literal', 'invented'),
                ('literal_sha256', '0' * 64), ('id', '0' * 64)]:
            corrupted = replace(corpus, records=(replace(corpus.records[0], **{field: value}), *corpus.records[1:]))
            with self.subTest(field=field), self.assertRaises(ValueError):
                corrupted.validate()

    def test_unknown_duplicate_malformed_and_same_literal_sets_never_salvage_a_draft(self):
        corpus = self.corpus()
        good = self.wire(corpus)
        values = [
            {'drafts': ['legacy answer']}, {'schema': 'wrong', 'drafts': good['drafts']},
            {**good, 'extra': True}, {**good, 'drafts': good['drafts'] * 2},
            {**good, 'drafts': [good['drafts'][0], {'anchors': ['0' * 64], 'text': 'Bad.'}]},
            {**good, 'drafts': [good['drafts'][0], {'anchors': good['drafts'][0]['anchors'], 'text': 'Different words.'}]},
            {**good, 'drafts': [{'anchors': good['drafts'][0]['anchors'] * 2, 'text': 'Bad.'}]},
            {**good, 'drafts': [good['drafts'][0], {'anchors': None, 'text': 'Bad.'}]},
        ]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.n.artist_evidence_drafts(json.dumps(value), corpus, str.strip)
        with self.assertRaises(ValueError):
            self.n.artist_evidence_drafts('plain legacy answer', corpus, str.strip)

    def test_inconsistent_derived_span_cannot_override_original_excerpt_or_generation(self):
        research = self.research()
        for mutation in ('text', 'id', 'range', 'digest'):
            broken = json.loads(json.dumps(research))
            source = broken['sources'][0]
            if mutation == 'digest':
                source['content_hash'] = '0' * 64
            elif mutation == 'range':
                source['evidence_spans'][0]['original_range'][0] += 1
            else:
                source['evidence_spans'][0][mutation] = 'invented derived passage'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.n.artist_anchor_corpus(broken)
        from custom_components.djconnect.ask_dj.public_research import generation_projection
        corpus = self.n.artist_anchor_corpus(research)
        generation = generation_projection(research, 'Tell me about this artist')
        self.assertEqual([text for _, _, text in corpus.spans],
            [span['text'] for span in generation['sources'][0]['evidence_spans']])

    def test_unicode_codepoints_resource_bounds_and_duplicate_literal_identity(self):
        research = self.research(('Één 🎸 speelde met de muzikant. Daarna speelde zij opnieuw.',))
        corpus = self.n.artist_anchor_corpus(research)
        self.assertEqual(corpus.records[1].start, 31)
        self.assertNotEqual(corpus.records[1].start, len(research['sources'][0]['untrusted_excerpt'][:31].encode()))
        # Byte offsets, normalization and swapped Unicode literals cannot bind.
        bad = replace(corpus.records[1], start=34)
        with self.assertRaises(ValueError):
            replace(corpus, records=(bad,)).validate()
        self.assertEqual(len(self.n.artist_anchor_corpus(self.research(('x' * 1400 + '.', 'A complete bounded public passage.'))).records), 1)
        with self.assertRaises(ValueError):
            self.n.artist_anchor_corpus(self.research(('x' * 66000,)))
        duplicate = self.n.artist_anchor_corpus(self.research(('An identical full literal passage.',) * 2))
        self.assertEqual(len(duplicate.records), 2)
        wire = {'schema': 'artist_evidence_drafts_v1', 'drafts': [
            {'anchors': [record.id], 'text': 'Different telling ' + str(index) + '.'}
            for index, record in enumerate(duplicate.records)]}
        with self.assertRaises(ValueError):
            self.n.artist_evidence_drafts(json.dumps(wire), duplicate, str.strip)

    def test_public_sdk_receipts_capture_original_inputs_before_any_failed_reply(self):
        from scripts.verification.artist_public_input_receipts import (
            append_artist_public_input, artist_public_inputs_complete, canonical,
            resolved_literal_commitments)
        from custom_components.djconnect.ask_dj.public_research import generation_projection
        records, calls = [], []
        for language in ('en', 'nl', 'de', 'fr', 'es'):
            research = self.research()
            generation = {'artist_draft_schema': 'artist_evidence_drafts_v1',
                'public_music_research': generation_projection(research, 'Tell me about this artist'),
                'literal_anchors': self.n.artist_anchor_corpus(research).projection(),
                'style': {'language': language}, 'question': 'PRIVATE_NEVER_EXPORT',
                'recent_turns': ['PRIVATE_NEVER_EXPORT'], 'qualified_context': {'private': 'PRIVATE_NEVER_EXPORT'}}
            assessment = {'drafts': [{'text': 'A future malformed reply is not needed for input proof.'}],
                'evidence': {'public_music_research': research, 'private': 'PRIVATE_NEVER_EXPORT'}, 'language': language}
            for phase, projection in (('generation', generation), ('assessment', assessment)):
                case = 'catalogue-listen.artist-' + language
                digest = append_artist_public_input(records,
                    [{'role': 'user', 'content': 'Instructions\nData:\n' + json.dumps(projection)}], case_id=case)
                calls.append({'case_id': case, 'artist_public_input_sha256': digest})
                self.assertEqual(records[-1]['phase'], phase)
                # Caller mutation never changes the original SDK witness.
                projection['private'] = 'NOT_EXPORTED'
        report = {'artist_public_inputs': records, 'model_calls': calls}
        self.assertTrue(artist_public_inputs_complete(report))
        self.assertNotIn('PRIVATE_NEVER_EXPORT', json.dumps(records))
        frozen = records[0]
        commitments = resolved_literal_commitments(frozen['public_music_research'], frozen['literal_anchors'])
        self.assertEqual(commitments[0]['literal'], frozen['literal_anchors'][0]['literal'])
        for change in ('missing', 'duplicate', 'locale', 'case', 'digest', 'anchor', 'private',
                'root_authority', 'source_authority', 'oversize', 'call'):
            altered = json.loads(json.dumps(report))
            row = altered['artist_public_inputs'][0]
            if change == 'missing':
                altered['artist_public_inputs'].pop()
            elif change == 'duplicate':
                altered['artist_public_inputs'][-1] = row
            elif change == 'locale':
                row['language'] = 'fr'
            elif change == 'case':
                row['case_id'] = 'unknown'
            elif change == 'digest':
                row['sha256'] = '0' * 64
            elif change == 'anchor':
                row['literal_anchors'][0]['literal'] = 'An invented full public literal.'
            elif change == 'private':
                row['public_music_research']['headers'] = {'Authorization': 'SECRET_NEVER_EXPORT'}
            elif change == 'root_authority':
                row['public_music_research']['authority'] = {'name': 'PRIVATE_AUTHORITY_CANARY'}
            elif change == 'source_authority':
                row['public_music_research']['sources'][0]['authority'] = {'name': 'PRIVATE_AUTHORITY_CANARY'}
            elif change == 'oversize':
                row['public_music_research']['sources'][0]['title'] = 'x' * 140000
            else:
                altered['model_calls'][-1]['artist_public_input_sha256'] = calls[0]['artist_public_input_sha256']
            if change in {'anchor', 'private', 'root_authority', 'source_authority', 'oversize'}:
                row['sha256'] = hashlib.sha256(canonical({k: v for k, v in row.items() if k != 'sha256'})).hexdigest()
                altered['model_calls'][0]['artist_public_input_sha256'] = row['sha256']
            with self.subTest(change=change):
                self.assertFalse(artist_public_inputs_complete(altered))
            if change in {'root_authority', 'source_authority', 'oversize'}:
                with self.assertRaises(ValueError):
                    append_artist_public_input([], [{'role': 'user', 'content': 'Instructions\nData:\n' + json.dumps({
                        'artist_draft_schema': 'artist_evidence_drafts_v1', 'public_music_research': row['public_music_research'],
                        'literal_anchors': row['literal_anchors'], 'style': {'language': 'en'}})}], case_id=row['case_id'])
        for case in ('unknown', 'catalogue-listen.artist-en'):
            with self.assertRaises(ValueError):
                append_artist_public_input(records, [], case_id=case)

    def test_nonparagraph_web_witness_keeps_full_original_and_canonical_sentence_addresses(self):
        from custom_components.djconnect.ask_dj.public_research import generation_projection, evidence_spans
        from scripts.verification.artist_public_input_receipts import resolved_literal_commitments
        # Ordinary web sources have sentence addresses, not Wikipedia paragraph
        # ranges. Keep even the original suffix beyond the 24 addressed sentences.
        excerpt = '\n'.join('Public musical activity number ' + str(i) + '.' for i in range(26))
        source = {'provider': 'Public web', 'kind': 'source', 'untrusted_excerpt': excerpt,
            'content_hash': hashlib.sha256(excerpt.encode()).hexdigest(), 'source_anchors': []}
        source['evidence_spans'] = evidence_spans(source)
        research = self.research()
        research['sources'].append(source)
        corpus = self.n.artist_anchor_corpus(research)
        projection = generation_projection(research, 'Tell me about this artist',
            preserve_nonparagraph_sources=True)
        self.assertEqual(projection['sources'][1]['untrusted_excerpt'], excerpt)
        self.assertEqual(len(projection['sources'][1]['evidence_spans']), 24)
        self.assertTrue(resolved_literal_commitments(projection, corpus.projection()))
        from custom_components.djconnect.public_artist_narration import complete_review_projection
        for candidate in (research, {**research, 'sources': research['sources'][:1] + [{
                **source, 'untrusted_excerpt': source['evidence_spans'][0]['text'],
                'content_hash': hashlib.sha256(source['evidence_spans'][0]['text'].encode()).hexdigest(),
                'evidence_spans': []}]}):
            # Exercise both a source with an unaddressed suffix and one whose
            # complete original text could otherwise be whitespace-compacted.
            web = candidate['sources'][1]
            web['evidence_spans'] = evidence_spans(web)
            reviewed = complete_review_projection({'public_music_research': candidate,
                'qualified_context': {}}, preserve_nonparagraph_sources=True)
            self.assertEqual(reviewed['public_music_research']['sources'][1]['untrusted_excerpt'],
                web['untrusted_excerpt'])
        for change in ('missing_original', 'suffix', 'span', 'id', 'unknown_schema'):
            broken = json.loads(json.dumps(projection))
            web = broken['sources'][1]
            if change == 'missing_original':
                del web['untrusted_excerpt']
            elif change == 'suffix':
                web['untrusted_excerpt'] += '\nUncommitted suffix.'
            elif change == 'span':
                web['evidence_spans'][0]['text'] = 'Invented music fact.'
            elif change == 'id':
                web['evidence_spans'][0]['id'] = web['evidence_spans'][1]['id']
            else:
                web['evidence_schema'] = 'unrecognized_schema'
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolved_literal_commitments(broken, corpus.projection())

    def test_failed_informational_generation_uses_the_accepted_turn_language(self):
        from types import SimpleNamespace
        from custom_components.djconnect.ask_dj import _fallback_info_text
        from custom_components.djconnect.ask_dj.dialogue import current_turn
        from custom_components.djconnect.ask_dj.public_research import unavailable_answer
        for locale in ('en', 'nl', 'de', 'fr', 'es'):
            token = current_turn.set(SimpleNamespace(style={'language': locale}))
            try:
                self.assertEqual(_fallback_info_text('Tell me about this artist', {}, {}),
                    unavailable_answer(locale))
            finally:
                current_turn.reset(token)

    def test_new_closed_negative_does_not_admit_facts_or_allow_positive_empty_ids(self):
        pool = self.n.verified_drafts('{"drafts":["An unsupported story.","A supported story."]}', str.strip)
        negative = {'review_schema': 'source_id_review_v1', 'supported': False,
            'language_ok': True, 'style_ok': True, 'unsupported_claims': ['unsupported story'],
            'claim_checks': [], 'temporal_claims': []}
        positive = {'review_schema': 'source_id_review_v1', 'supported': True,
            'language_ok': True, 'style_ok': True, 'unsupported_claims': [],
            'claim_checks': [{'text': pool.texts[1], 'kind': 'fact', 'evidence_ids': ['actual-id']}]}
        def envelope(first=negative, second=positive):
            return json.dumps({'draft_reviews': [{**{k: v for k, v in row.items() if k != 'text'},
                'review': review} for row, review in zip(pool.records(), [first, second], strict=True)]})
        reviews = self.n.bound_draft_reviews(envelope(), pool, public_story=True, closed_negative=True)
        self.assertFalse(json.loads(reviews[0])['supported'])
        self.assertTrue(json.loads(reviews[1])['supported'])
        for bad in [{**negative, 'unsupported_claims': ['foreign text']},
                    {**negative, 'claim_checks': [{'text': 'bad', 'kind': 'fact', 'evidence_ids': []}]},
                    {**negative, 'extra': True}, {**negative, 'temporal_claims': None}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.n.bound_draft_reviews(envelope(first=bad), pool, public_story=True, closed_negative=True)
        bad = {**positive, 'claim_checks': [{'text': 'Bei', 'kind': 'fact', 'evidence_ids': []}]}
        with self.assertRaises(ValueError):
            self.n.bound_draft_reviews(envelope(second=bad), pool, public_story=True, closed_negative=True)


class ArtistEvidencePairedTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def test_actual_paired_route_requires_literal_wire_and_closed_negative_before_second_acceptance(self):
        from tests.test_ask_dj_semantic_reads import id_review_fixture
        f = shared.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            for mode in ('second', 'bad_anchor', 'bad_negative', 'positive_empty'):
                await f.history.async_clear('profile:profile-a')
                calls = []
                bad, good = 'Volbeat invented every instrument.', 'Volbeat performed a concert.'
                async def agent(hass, data, **kwargs):
                    projection = json.loads(data['text'].split('\nData:\n', 1)[1])
                    calls.append(projection)
                    if set(projection) == {'question', 'language', 'available'}:
                        reply = {'read': 'artist_story', 'reference': 'current', 'exclude_current': False}
                    elif 'evidence' not in projection:
                        self.assertEqual(projection['artist_draft_schema'], 'artist_evidence_drafts_v1')
                        anchors = projection['literal_anchors']
                        self.assertGreaterEqual(len(anchors), 2)
                        reply = {'schema': 'artist_evidence_drafts_v1', 'drafts': [
                            {'anchors': [anchors[0]['id']], 'text': bad},
                            {'anchors': ['0' * 64 if mode == 'bad_anchor' else anchors[1]['id']], 'text': good}]}
                    else:
                        first = {'review_schema': 'source_id_review_v1', 'supported': False,
                            'language_ok': True, 'style_ok': True, 'unsupported_claims': [bad],
                            'claim_checks': [], 'temporal_claims': []}
                        second = id_review_fixture({**projection, 'answer': good})
                        second['unsupported_claims'] = []
                        if mode == 'bad_negative':
                            first.pop('temporal_claims')
                        if mode == 'positive_empty':
                            second['claim_checks'] = [{'text': 'Bei', 'kind': 'fact', 'evidence_ids': []}]
                        reply = {'draft_reviews': [{**{k: v for k, v in row.items() if k != 'text'}, 'review': review}
                            for row, review in zip(projection['drafts'], [first, second], strict=True)]}
                    await asyncio.sleep(0)
                    return {'response': {'speech': {'plain': {'speech': json.dumps(reply)}}}}
                async def status(*args, **kwargs):
                    return {'success': True, 'playback': {'uri': 'spotify:track:' + 'N' * 22,
                        'artist': 'Volbeat', 'title': 'Private current recording'}}
                with f.research_http(title='Volbeat', text='Volbeat is a Danish band. ' + good), patch.object(
                        f.pipeline, '_call_conversation_process_transport', agent), patch.object(f.core, 'run_music_command', status):
                    answer, code = await f.request('tell me about this artist', identifier='literal-' + mode)
                if mode == 'bad_anchor':
                    self.assertEqual(code, 502, answer)
                    self.assertEqual(len(calls), 2)
                else:
                    self.assertEqual(code, 200, answer)
                    self.assertEqual(len(calls), 3)
                    self.assertEqual(answer['is_generated_text'], mode == 'second', answer)
                    if mode == 'second':
                        self.assertEqual(answer['text'], good)
                        self.assertEqual(answer['knowledge_basis'], 'fetched_public_music_research_v1')
                self.assertEqual(f.effects, [])
                self.assertNotIn(bad, json.dumps((await f.history.async_history('profile:profile-a'))['messages']))
        finally:
            await f.asyncTearDown()


if __name__ == '__main__':
    unittest.main()
