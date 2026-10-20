"""Directed biography proof; no network, model or installed acceptance."""
from copy import deepcopy
import json
import unittest

from tests import test_ask_dj_contextual_dialogue as shared


class BiographicalDateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        from custom_components.djconnect.ask_dj import public_research, biographical_dates
        cls.research,cls.bio=public_research,biographical_dates

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def context(self,quote, *, provider='Wikipedia',qid='Q1',group='Synthetic Group'):
        source=self.research._source(provider,group,'https://en.wikipedia.org/wiki/Synthetic_Group',
            'Synthetic Group is a rock band. '+quote,'en',entity_id=qid).model_data()
        research=self.research.research_projection(group,[],{})
        research.update(schema_version=2,sources=[source])
        return {'public_music_research':research}

    def receipt(self,context,quote,answer=None, *, event='member_joined',actor='Ada Reed'):
        source=context['public_music_research']['sources'][0]
        span=next(s for s in self.research.evidence_spans(source) if quote in s['text'])
        return dict(schema=self.bio.SCHEMA,event=event,claim=answer or quote,actor=actor,
            group='Synthetic Group',group_id='Q1',year='1990',source_id=source['content_hash'],
            evidence_id=span['id'],quote=quote)

    def assessment(self,context,receipt):
        source=context['public_music_research']['sources'][0]
        return {'supported':True,'unsupported_claims':[],'temporal_claims':[receipt],
            'claim_checks':[{'text':receipt['claim'],'kind':'relationship',
                'evidence_ids':[receipt['evidence_id']],'quote':next(s['text']
                    for s in self.research.evidence_spans(source) if s['id']==receipt['evidence_id'])}]}

    def test_exact_accession_and_founding_dates_translate_across_five_languages(self):
        membership=('Ada Reed joined Synthetic Group in 1990.',
            'Ada Reed trad in 1990 toe tot Synthetic Group.',
            'Ada Reed trat Synthetic Group im Jahr 1990 bei.',
            'Ada Reed a rejoint Synthetic Group en 1990.',
            'Ada Reed se unió a Synthetic Group en 1990.')
        founding=('Synthetic Group was founded in 1990.',
            'Synthetic Group werd in 1990 opgericht.',
            'Synthetic Group wurde im Jahr 1990 gegründet.',
            'Synthetic Group a été fondé en 1990.',
            'Synthetic Group se fundó en 1990.')
        for event,actor,variants in (('member_joined','Ada Reed',membership),
                                     ('group_founded','Synthetic Group',founding)):
            for quote in variants:
                context=self.context(quote)
                self.assertTrue(self.bio.candidates(context['public_music_research']),quote)
                for answer in variants:
                    proof=self.receipt(context,quote,answer,event=event,actor=actor)
                    review=self.assessment(context,proof)
                    with self.subTest(source=quote,answer=answer):
                        self.assertTrue(self.research.supported(json.dumps(review),answer,context))
                        self.assertFalse(self.research.supported(json.dumps({**review,'temporal_claims':[]}),answer,context))
                        self.assertFalse(self.research.supported(json.dumps({**review,'supported':False}),answer,context))

    def test_wrong_person_group_year_event_and_source_never_gain_admission(self):
        quote='Ada Reed joined Synthetic Group in 1990.'
        context=self.context(quote)
        proof=self.receipt(context,quote)
        for change in ({'actor':'Bea Reed'},{'group':'Other Group'},{'year':'1991'},
                {'group_id':'Q2'},{'source_id':'b'*64},{'evidence_id':'missing:0'},
                {'event':'group_founded'},{'schema':'biographical_event_v2'},
                {'quote':'Ada Reed left Synthetic Group in 1990.'},{'extra':'anything'}):
            forged={**proof,**change}
            review=self.assessment(context,proof)
            review['temporal_claims']=[forged]
            with self.subTest(change=change):
                self.assertFalse(self.research.supported(json.dumps(review),quote,context))
        context['public_music_research']['resolved_public_subject']='Other Group'
        self.assertFalse(self.research.supported(json.dumps(self.assessment(context,proof)),quote,context))

    def test_nearby_event_negation_uncertainty_and_pronouns_stay_closed(self):
        for quote in ('Ada Reed left Synthetic Group in 1990.',
                'Ada Reed did not join Synthetic Group in 1990.',
                'Ada Reed reportedly joined Synthetic Group in 1990.',
                'She joined Synthetic Group in 1990.',
                'Ada Reed joined the band in 1990.',
                'Ada Reed joined Synthetic Group after Other Group in 1990.',
                'Ada Reed joined Synthetic Group in 1990 and left in 1991.',
                'Synthetic Group was not founded in 1990.',
                'Synthetic Group was founded in 1990 after Ada Reed left.',
                'Synthetic Group was founded in 1989 and released an album in 1990.',
                'Synthetic Group was a band formed in London and Other Group formed in 1990.',
                'Synthetic Group was a band formed in London And Other Group Formed in 1990.'):
            context=self.context(quote)
            self.assertEqual(self.bio.candidates(context['public_music_research']),[],quote)
            proof=self.receipt(context,quote,'Ada Reed joined Synthetic Group in 1990.')
            self.assertFalse(self.research.supported(json.dumps(self.assessment(context,proof)),proof['claim'],context))
        for change in ({'provider':'Public web'},{'qid':''}):
            context=self.context('Ada Reed joined Synthetic Group in 1990.',**change)
            self.assertEqual(self.bio.candidates(context['public_music_research']),[])
        context=self.context('Synthetic Group was founded in 1990.')
        source=context['public_music_research']['sources'][0]
        source['untrusted_excerpt']=source['untrusted_excerpt'].replace(
            'Synthetic Group is a rock band.','Synthetic Group is a musician in a rock band.')
        self.assertEqual(self.bio.candidates(context['public_music_research']),[])
        quote='Synthetic Group was founded in 1990.'
        context=self.context(quote)
        answer='Synthetic Group was a band formed in London and Other Group formed in 1990.'
        proof=self.receipt(context,quote,answer,event='group_founded',actor='Synthetic Group')
        self.assertFalse(self.research.supported(json.dumps(self.assessment(context,proof)),answer,context))

    def test_split_extra_date_and_prefix_cannot_bypass_original_guards(self):
        quote='Ada Reed joined Synthetic Group in 1990.'
        context=self.context(quote)
        proof=self.receipt(context,quote)
        review=self.assessment(context,proof)
        for tail in (' Synthetic Group released First Work in 1991.',
                ' Synthetic Group formed in that same year.',
                ' Ada Reed subsequently left Synthetic Group.'):
            self.assertFalse(self.research.supported(json.dumps(review),quote+tail,context))
        tail=' Ada Reed left Synthetic Group in 1991.'
        prefix={**review,'supported':False,'unsupported_claims':[tail.strip()],
            'supported_prefix':quote,'prefix_supported':True,'prefix_answers_question':True}
        self.assertEqual(self.research.qualified_prefix(json.dumps(prefix),quote+tail,context),quote)
        prefix['temporal_claims'][0]['year']='1991'
        self.assertIsNone(self.research.qualified_prefix(json.dumps(prefix),quote+tail,context))

    def test_literal_candidates_are_value_only_and_leave_sources_unchanged(self):
        quote='Synthetic Group was an American rock band formed in Aberdeen, Washington, in 1990.'
        context=self.context(quote)
        before=deepcopy(context)
        projection=self.research.generation_projection(context['public_music_research'],'When was this group founded?')
        self.assertEqual(context,before)
        candidates=projection['biographical_date_events']
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]['quote'],quote)
        self.assertEqual(candidates[0]['group_id'],'Q1')
        self.assertNotIn('claim',candidates[0])
        review=json.loads(self.research.assessment_prompt('Synthetic Group was founded in 1990.',context,
            'en','When was the band founded?').split('\nData:\n')[1])
        self.assertEqual(review['biographical_date_events'],candidates)
