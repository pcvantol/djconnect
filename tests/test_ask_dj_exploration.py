"""Selected-source exploration: real shared routing, declared external fixtures."""
import json
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


def reviewed_fixture(projection):
    """The declared fixture's closing invitation makes no factual assertion."""
    review=shared._research_assessment_fixture(projection)
    for check in review['claim_checks']:
        if check['text'].endswith('?'):
            check.update(kind='dj_appreciation',evidence_ids=[],quote='')
    return review


class ExplorationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = shared.SharedDialogueTest()
        await self.f.asyncSetUp()

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    def test_research_plan_is_closed_and_selected_public_context_is_authority(self):
        from custom_components.djconnect.ask_dj.semantic_reads import parse_plan
        from custom_components.djconnect.ask_dj.exploration import admitted_subject
        plan = {'read':'research', 'reference':'selected', 'exclude_current':False,
                'subject':'Brian Eno', 'angle':'composition'}
        self.assertIsNotNone(parse_plan(json.dumps(plan)))
        for change in ({'reference':'current'}, {'exclude_current':True}, {'uri':'spotify:track:'+'A'*22},
                       {'angle':'arbitrary private query'}, {'subject':17}):
            self.assertIsNone(parse_plan(json.dumps({**plan, **change})))
        context = {'basis':'cc0_normalized_fields_v1', 'subjects':[
            {'name':'Brian Eno','role':'composer'}, {'name':'Other artist','role':'performer'}]}
        self.assertEqual(admitted_subject('Brian Eno','composition',context),'Brian Eno')
        self.assertIsNone(admitted_subject('Unrelated artist','composition',context))
        self.assertIsNone(admitted_subject('Brian Eno','composition',{**context,'basis':'private_history'}))
        untyped = {'basis':'cc0_normalized_fields_v1', 'qualified_excerpt':'Brian Eno composed music.'}
        self.assertIsNone(admitted_subject('Brian Eno','composition',untyped))
        self.assertIsNone(admitted_subject('Brian','composition',untyped))
        self.assertIsNone(admitted_subject('Brian','composition',{**context,'subjects':context['subjects']}))
        from custom_components.djconnect.ask_dj.exploration import named_in_question
        self.assertTrue(named_in_question('Nirvana','vertel over nirvna en hun concerten'))
        self.assertTrue(named_in_question('Armin van Buuren','wat weet je over armin van buren?'))
        self.assertFalse(named_in_question('Metallica','vertel iets over Nirvana'))
        self.assertFalse(named_in_question('Brian Eno','tell me about Brian'))
        self.assertFalse(named_in_question('Alice','tell me about music'))

    async def test_english_enrichment_reuses_resolved_local_entity_and_rejects_different_entity(self):
        from custom_components.djconnect.ask_dj import public_research as research
        async def guard():
            return None
        local = research._source('Wikipedia','Synthetic group','https://nl.wikipedia.org/wiki/Synthetic_group',
            'Synthetic group is een band.','nl',entity_id='Q1')
        for foreign_id in ('Q1','Q2'):
            observed=[]
            async def wikipedia(fetch,subject,question,locale,**kwargs):
                observed.append((locale,kwargs.get('expected_entity_id')))
                return local if locale=='nl' else research._source('Wikipedia','Synthetic group',
                    'https://en.wikipedia.org/wiki/Synthetic_group','Synthetic group is a band.',
                    'en',entity_id=foreign_id)
            with patch.object(research,'wikipedia',wikipedia):
                sources,_=await research.research('Synthetic Group','Tell me about this band','nl',guard,allow_web=False)
            self.assertEqual(observed,[('nl',''),('en','Q1')])
            self.assertEqual(len(sources),2 if foreign_id=='Q1' else 1)

    async def test_grunge_group_lead_preserves_local_source_and_exact_entity_role_guards(self):
        """Actual NL source was lost at Group admission, before any model call."""
        from custom_components.djconnect.ask_dj import public_research as research
        from urllib.parse import parse_qs, urlsplit
        from unittest.mock import AsyncMock
        leads={
            'en':'Aster Road is an American grunge band.',
            'nl':'Aster Road is een Amerikaanse grungeband.',
            'de':'Aster Road ist eine amerikanische Grungeband.',
            'fr':'Aster Road est un groupe de grunge américain.',
            'es':'Aster Road es un grupo de grunge estadounidense.',
        }
        async def guard():
            return None
        class Fetch:
            async def request(self,url,**kwargs):
                params=parse_qs(urlsplit(url).query)
                self.requests.append((urlsplit(url).hostname,params))
                page={'title':'Aster Road','pageprops':{'wikibase_item':self.qid},
                      'extract':'<p>'+self.lead+'</p>', 'revisions':[{'revid':1234}]}
                return 200,json.dumps({'query':{'pages':[page]}}),url
        fetch=Fetch()
        for locale,lead in leads.items():
            with self.subTest(locale=locale):
                fetch.requests,fetch.qid,fetch.lead=[],'Q1',lead
                source=await research.wikipedia(fetch,'Aster Road','Introduce this artist',locale,
                    expected_roles=('Group',),expected_entity_id='Q1',original_paragraphs=True)
                self.assertIsNotNone(source)
                self.assertEqual(source.language,locale)
                self.assertEqual(source.entity_id,'Q1')
                self.assertEqual(source.text,lead)
                self.assertEqual(len(fetch.requests),1)
                self.assertEqual(source.model_data()['literal_passages'][0]['text'],lead)
        for qid,roles,lead in (
                ('Q2',('Group',),leads['nl']),
                ('Q1',('Person',),leads['nl']),
                ('Q1',('Group',),'Aster Road is a mountain.'),
                ('Q1',('Group',),'Aster Road is een grungebandiet.')):
            with self.subTest(qid=qid,roles=roles,lead=lead):
                fetch.requests,fetch.qid,fetch.lead=[],qid,lead
                with patch.object(research,'_qualified_wikipedia_title',AsyncMock(return_value='')):
                    self.assertIsNone(await research.wikipedia(fetch,'Aster Road','Introduce this artist','nl',
                        expected_roles=roles,expected_entity_id='Q1',original_paragraphs=True))

    async def test_generic_more_researches_selected_composer_and_preserves_follow_up_without_playback(self):
        f = self.f
        _, _, reference = await f.selected_credit()
        calls = []
        answer_text = 'Brian Eno is an English composer. Would you like to explore his music?'
        async def agent(hass, data, **kwargs):
            projection = json.loads(data['text'].split('\nData:\n',1)[1])
            calls.append(projection)
            if 'available' in projection:
                self.assertEqual(projection['qualified_selected_context']['subjects'][0]['role'],'composer')
                text = json.dumps({'read':'research','reference':'selected','exclude_current':False,
                                  'subject':'Brian Eno','angle':'composition'})
            elif 'evidence' in projection:
                text = json.dumps(reviewed_fixture(projection))
            else:
                self.assertIn('follow-up question',data['text'])
                text = answer_text
            return {'response':{'speech':{'plain':{'speech':text}}}}
        with f.research_http(title='Brian Eno',text='Brian Eno is an English composer.'), patch.object(
                f.pipeline,'_call_conversation_process_transport',agent):
            result,status = await f.request('Tell me more',identifier='generic-selected-more',
                context={'selected_entry':reference},language='en')
        self.assertEqual(status,200,result)
        self.assertEqual(result.get('text'),answer_text,result)
        self.assertEqual(result['conversation']['context']['selected_entry'],reference)
        self.assertEqual(len(calls),3)
        self.assertEqual(result['conversation']['metrics']['agent_calls'],3)
        self.assertFalse(result.get('playback_actions'))
        self.assertEqual(f.effects,[])
        self.assertTrue(result.get('sources'))

    def test_generic_affordance_all_locales_and_dynamic_angles(self):
        from custom_components.djconnect.ask_dj.exploration import MORE_TEXT, more_request, capability
        from custom_components.djconnect.ask_dj.dialogue import references_topic
        self.assertEqual(set(MORE_TEXT),{'en','nl','de','fr','es'})
        for text in MORE_TEXT.values():
            self.assertTrue(more_request(text),text)
            self.assertTrue(references_topic(text),text)
        self.assertFalse(capability()['attribute_required'])

    async def test_failed_subject_plan_never_searches_an_unrelated_artist(self):
        f = self.f
        from custom_components.djconnect.ask_dj import public_research
        _,_,reference = await f.selected_credit()
        async def agent(hass,data,**kwargs):
            return {'response':{'speech':{'plain':{'speech':json.dumps({
                'read':'research','reference':'selected','exclude_current':False,
                'subject':'Unrelated artist','angle':'biography'})}}}}
        with patch.object(f.pipeline,'_call_conversation_process_transport',agent), patch.object(
                public_research,
                'research',side_effect=AssertionError('unrelated public query')):
            result,status = await f.request('Tell me more',identifier='unrelated-plan',
                context={'selected_entry':reference})
        self.assertEqual(status,200,result)
        self.assertFalse(result.get('is_generated_text'))
        self.assertEqual(f.effects,[])

    async def test_open_exploration_all_five_locales_preserves_actual_subject_and_style(self):
        f=self.f
        _,_,reference=await f.selected_credit()
        from custom_components.djconnect.ask_dj.exploration import MORE_TEXT
        answers={
            'en':'Brian Eno is an English composer. Would you like to explore his music?',
            'nl':'Brian Eno is een Engelse componist. Zullen we zijn muziek verder verkennen?',
            'de':'Brian Eno ist ein englischer Komponist. Möchtest du seine Musik weiter erkunden?',
            'fr':'Brian Eno est un compositeur anglais. Veux-tu explorer sa musique ?',
            'es':'Brian Eno es un compositor inglés. ¿Te apetece explorar su música?',
        }
        for locale,question in MORE_TEXT.items():
            await f.history.async_clear('profile:profile-a')
            calls=[]
            async def agent(hass,data,**kwargs):
                p=json.loads(data['text'].split('\nData:\n',1)[1])
                calls.append(p)
                if 'available' in p:
                    reply=json.dumps({'read':'research','reference':'selected','exclude_current':False,
                        'subject':'Brian Eno','angle':'live_history'})
                elif 'evidence' in p:
                    reply=json.dumps(reviewed_fixture(p))
                else:
                    self.assertEqual(p['style']['mood'],'groove')
                    reply=answers[locale]
                return {'response':{'speech':{'plain':{'speech':reply}}}}
            with f.research_http(title='Brian Eno',text='Brian Eno is an English composer.'), patch.object(
                    f.pipeline,'_call_conversation_process_transport',agent):
                result,status=await f.request(question,identifier='more-'+locale,
                    context={'selected_entry':reference},language=locale)
            self.assertEqual(status,200,result)
            self.assertEqual(result.get('text'),answers[locale],result)
            self.assertEqual(result['conversation']['style']['language'],locale)
            self.assertEqual(result['conversation']['metrics']['agent_calls'],3)
            self.assertEqual(len(calls),3)
            self.assertFalse(result.get('playback_actions'))
        self.assertEqual(f.effects,[])

    async def test_freeworded_typo_question_uses_llm_and_qualified_context(self):
        f=self.f
        _,_,reference=await f.selected_credit()
        question='kan je me wat meer vertelln over die componist z\'n werk?'
        async def agent(hass,data,**kwargs):
            p=json.loads(data['text'].split('\nData:\n',1)[1])
            if 'available' in p:
                reply=json.dumps({'read':'research','reference':'selected','exclude_current':False,
                    'subject':'Brian Eno','angle':'composition'})
            elif 'evidence' in p:
                reply=json.dumps(reviewed_fixture(p))
            else:
                self.assertIn(question,json.dumps(p,ensure_ascii=False))
                reply='Brian Eno is een Engelse componist. Zullen we zijn muziek verder verkennen?'
            return {'response':{'speech':{'plain':{'speech':reply}}}}
        with f.research_http(title='Brian Eno',text='Brian Eno is an English composer.'), patch.object(
                f.pipeline,'_call_conversation_process_transport',agent):
            result,status=await f.request(question,identifier='composer-typo',
                context={'selected_entry':reference},language='nl')
        self.assertEqual(status,200,result)
        self.assertTrue(result.get('is_generated_text'),result)
        self.assertEqual(result['conversation']['context']['selected_entry'],reference)
        self.assertLessEqual(result['conversation']['metrics']['agent_calls'],3)
        self.assertEqual(f.effects,[])

    async def test_selected_producer_role_does_not_borrow_different_performer(self):
        f=self.f
        _,_,reference=await f.selected_credit('Brian Eno',producer=True)
        async def agent(hass,data,**kwargs):
            p=json.loads(data['text'].split('\nData:\n',1)[1])
            if 'available' in p:
                self.assertEqual(p['qualified_selected_context']['subjects'],[
                    {'name':'Brian Eno','role':'producer'},{'name':'Different performer','role':'vocal'}])
                reply=json.dumps({'read':'research','reference':'selected','exclude_current':False,
                    'subject':'Brian Eno','angle':'production'})
            elif 'evidence' in p:
                reply=json.dumps(reviewed_fixture(p))
            else:
                self.assertNotIn('Different performer',json.dumps(p['public_music_research']))
                reply='Brian Eno is an English record producer. Would you like to explore his work?'
            return {'response':{'speech':{'plain':{'speech':reply}}}}
        with f.research_http(title='Brian Eno',text='Brian Eno is an English record producer.'),patch.object(
                f.pipeline,'_call_conversation_process_transport',agent):
            result,status=await f.request('Tell me more',identifier='producer-exploration',
                context={'selected_entry':reference})
        self.assertEqual(status,200,result)
        self.assertTrue(result.get('is_generated_text'),result)
        self.assertIn('record producer',result['text'])
        self.assertNotIn('Different performer',result['text'])
        self.assertEqual(f.effects,[])

    async def test_multipart_named_story_uses_semantics_and_actual_question_name(self):
        f=self.f
        from scripts.verification.askdj_contextual_quality import QUESTIONS
        questions=['Neem me mee in Nirvana: de bandleden en een bijzonder optreden, niet alleen credits.',
                   QUESTIONS['nl']]
        async def agent(hass,data,**kwargs):
            p=json.loads(data['text'].split('\nData:\n',1)[1])
            if 'available' in p:
                reply=json.dumps({'read':'research','reference':'named','exclude_current':False,
                    'subject':'Nirvana','angle':'live_history'})
            elif 'evidence' in p:
                reply=json.dumps(reviewed_fixture(p))
            else:
                reply='Nirvana is een Amerikaanse band. Wil je hun muziek verder verkennen?'
            return {'response':{'speech':{'plain':{'speech':reply}}}}
        async def playback_tool(hass,runtime,tool,*args,**kwargs):
            self.assertEqual(tool,'djconnect_now_playing')
            return {'playback':{'artist':'Peter Luts','title':'Different current recording'}}
        with f.research_http(title='Nirvana',text='Nirvana is an American band.'),patch.object(
                f.pipeline,'_call_conversation_process_transport',agent),patch.object(
                f.core,'async_call_ai_tool',playback_tool),patch.object(
                f.core,'_fetch_artist_concert_events',side_effect=AssertionError('not a current artist agenda')):
            for index,question in enumerate(questions):
                await f.history.async_clear('profile:profile-a')
                result,status=await f.request(question,identifier='multipart-band-'+str(index),language='nl')
                self.assertEqual(status,200,result)
                self.assertTrue(result.get('is_generated_text'),result)
                self.assertIn('Nirvana',result['text'])
                self.assertNotIn('Peter Luts',result['text'])
                self.assertEqual(result['intent']['intent'],'ask_music_info')
                self.assertEqual(result['action'],'none')
                self.assertFalse(result.get('playback'))
                self.assertEqual(result['conversation']['metrics']['agent_calls'],3)
        self.assertEqual(f.effects,[])
