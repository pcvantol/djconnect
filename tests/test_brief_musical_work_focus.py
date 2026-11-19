"""Prefer documented musical work without granting factual or temporal authority."""
import copy
import hashlib
import importlib
import unittest

from tests import test_ask_dj_contextual_dialogue as shared


class BriefMusicalWorkFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.research = importlib.import_module('custom_components.djconnect.ask_dj.public_research')
        cls.narration = importlib.import_module('custom_components.djconnect.narration_brief')

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def corpus(self, paragraphs, anchors=('Lantern Sessions',), provider='Wikipedia'):
        excerpt = '\n'.join(paragraphs)
        digest = hashlib.sha256(excerpt.encode()).hexdigest()
        offset, passages = 0, []
        for text in paragraphs:
            passages.append({'text': text, 'original_range': [offset, offset + len(text)]})
            offset += len(text) + 1
        source = {'provider': provider, 'content_hash': digest,
            'untrusted_excerpt': excerpt, 'evidence_schema': 'original_paragraphs_v1',
            'literal_passages': passages, 'original_document_hash': digest,
            'source_anchors': list(anchors), 'title': 'Synthetic ensemble'}
        source['evidence_spans'] = self.research.evidence_spans(source)
        return {'schema_version': 3, 'sources': [source]}

    def focus(self, research, **kwargs):
        return self.research.documented_episode_focus(research, **kwargs)

    def test_five_locale_named_work_activity_precedes_clean_venue(self):
        passages = (
            'A new member recorded guest solos on Lantern Sessions.',
            'Het bandlid speelde gastsolo’s op Lantern Sessions.',
            'Das Mitglied spielte auf Lantern Sessions.',
            'Un membre a enregistré des solos pour Lantern Sessions.',
            'Un miembro grabó solos para Lantern Sessions.',
        )
        for text in passages:
            with self.subTest(text=text):
                research = self.corpus(['The ensemble performed at a festival.', text])
                original = copy.deepcopy(research)
                focus = self.focus(research, brief=True)
                self.assertEqual(focus['episode_span_ids'], [research['sources'][0]['evidence_spans'][1]['id']])
                self.assertEqual(research, original)
                self.assertEqual(focus['authority'], 'telling_focus_only_full_original_context_remains_evidence')

    def test_work_without_activity_and_activity_without_supplied_work_keep_clean_fallback(self):
        for text, anchors in (
            ('A member lists Lantern Sessions in the discography.', ('Lantern Sessions',)),
            ('A member recorded Lantern Sessions.', ()),
            ('A member recorded Lantern Sessions.', ('Different Work',)),
            ('A member recorded an unnamed album.', ('Lantern Sessions',)),
            ('A member described Lantern Sessions as heavy metal.', ('Lantern Sessions',)),
        ):
            with self.subTest(text=text, anchors=anchors):
                research = self.corpus(['The ensemble performed at a festival.', text], anchors)
                self.assertEqual(self.focus(research, brief=True)['episode_span_ids'],
                    [research['sources'][0]['evidence_spans'][0]['id']])

    def test_work_boundary_and_short_title_rules_remain_exact(self):
        for text, anchor, preferred in (
            ('A member recorded Lantern SessionsExtended.', 'Lantern Sessions', False),
            ('A member recorded guest solos for the album “Up”.', 'Up', True),
            ('A member recorded a tune up there.', 'Up', False),
            ('A member recorded guest solos for LANTERN SESSIONS.', 'Lantern Sessions', True),
        ):
            with self.subTest(text=text):
                research = self.corpus(['The ensemble performed at a festival.', text], (anchor,))
                spans = research['sources'][0]['evidence_spans']
                self.assertEqual(self.focus(research, brief=True)['episode_span_ids'],
                    [spans[int(preferred)]['id']])
                required = self.focus(research, require_work=True)
                self.assertEqual(required is not None, preferred)

    def test_membership_and_future_tense_remain_original_review_evidence(self):
        text = ('A guest member is recording solos for Lantern Sessions. '
                'The album will be released later. The guest joined the band.')
        research = self.corpus(['The ensemble performed at a festival.', text])
        original = copy.deepcopy(research)
        before = self.narration.artist_anchor_corpus(research)
        after = self.narration.artist_anchor_corpus({**research, 'editorial_focus': self.focus(research, brief=True)})
        self.assertEqual(after.spans, before.spans)
        self.assertEqual(after.records[0].literal, 'A guest member is recording solos for Lantern Sessions.')
        self.assertIn('will be released', after.spans[1][2])
        self.assertEqual(research, original)
        after.validate()

    def test_equal_work_candidates_keep_source_and_span_order(self):
        research = self.corpus(['The ensemble performed at a festival.',
            'A member recorded Lantern Sessions.', 'Another member recorded Lantern Sessions.'])
        self.assertEqual(self.focus(research, brief=True)['episode_span_ids'],
            [research['sources'][0]['evidence_spans'][1]['id']])

    def test_nonbrief_live_angle_and_require_work_keep_existing_ranking(self):
        research = self.corpus(['The ensemble performed a live concert.',
            'A guest collaborated with the ensemble on Lantern Sessions before becoming a member.'])
        spans = research['sources'][0]['evidence_spans']
        self.assertEqual(self.focus(research)['episode_span_ids'], [spans[1]['id']])
        self.assertEqual(self.focus(research, angle='live_history')['episode_span_ids'], [spans[0]['id']])
        self.assertEqual(self.focus(research, require_work=True)['episode_span_ids'], [spans[1]['id']])
        self.assertEqual(self.focus(research, angle='live_history', require_work=True)['episode_span_ids'], [spans[1]['id']])
        for question in ('When was the album recorded?', 'Who joined this band?',
                         'Tell me about this artist and their live performances'):
            self.assertFalse(self.research.brief_contextual_artist_question(question))

    def test_no_wikipedia_or_no_activity_does_not_invent_topic(self):
        research = self.corpus(['A member recorded Lantern Sessions.'], provider='Wikidata')
        self.assertIsNone(self.focus(research, brief=True))
        research = self.corpus(['The ensemble uses heavy metal and rockabilly.'])
        self.assertEqual(self.focus(research, brief=True), self.focus(research))

    def test_cap_pressure_preserves_full_corpus_and_canonical_selected_records(self):
        for padding in ('x' * 30, 'x' * 300):
            with self.subTest(padding_bytes=len(padding)):
                paragraphs = [' '.join(f'The ensemble performed a concert {group}-{number} with {padding}.'
                    for number in range(10)) for group in range(4)]
                paragraphs.append('A guest member recorded Lantern Sessions with ' + 'y' * 500 + '.')
                research = self.corpus(paragraphs)
                original = copy.deepcopy(research)
                before = self.narration.artist_anchor_corpus(research)
                after = self.narration.artist_anchor_corpus({**research, 'editorial_focus': self.focus(research, brief=True)})
                self.assertEqual(before.spans, after.spans)
                self.assertNotEqual({row.id for row in before.records}, {row.id for row in after.records})
                self.assertEqual(after.records[0].literal, paragraphs[-1])
                self.assertLessEqual(len(after.records), 32)
                self.assertLessEqual(sum(len(row.literal.encode()) for row in after.records), 8192)
                after.validate()
                self.assertEqual(research, original)
                for row in after.records:
                    source_id, identifier, text = next(span for span in after.spans if span[1] == row.evidence_id)
                    self.assertEqual(row.source_id, source_id)
                    self.assertEqual(row.literal, text[row.start:row.end])
                    self.assertEqual(row.id, row.commitment())
