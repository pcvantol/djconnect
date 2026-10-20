"""Selected-source exploration: real shared routing, declared external fixtures."""
import json
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


def reviewed_fixture(projection, *, id_wire=True):
    """The declared fixture's closing invitation makes no factual assertion."""
    from custom_components.djconnect.ask_dj.public_research import evidence_spans, _sentences
    if id_wire and projection['evidence']['public_music_research']['schema_version']==3:
        spans=[span for source in projection['evidence']['public_music_research']['sources']
               for span in source.get('evidence_spans',evidence_spans(source))]
        review={'supported':True,'language_ok':True,'style_ok':True,
                'review_schema':'source_id_review_v1','claim_checks':[
                    {'text':sentence,'kind':'fact','evidence_ids':[spans[0]['id']]}
                    for sentence in _sentences(projection['answer'])]}
    else:
        review=shared._research_assessment_fixture(projection)
    for check in review['claim_checks']:
        if check['text'].endswith('?'):
            check.update(kind='dj_appreciation',evidence_ids=[],quote='')
    if id_wire and projection['evidence']['public_music_research']['schema_version']==3:
        review.update(language_ok=True,style_ok=True,review_schema='source_id_review_v1')
        for check in review['claim_checks']:
            check.pop('quote',None)
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

    async def test_named_and_selected_research_cannot_publish_an_unreviewed_style_or_partial_story(self):
        """Real shared owner/history; model and public source are explicit fixtures."""
        f=self.f
        _,_,reference=await f.selected_credit()
        first='Brian Eno is an English composer.'
        full=first+' Would you like to explore his music?'
        for mode in ('named','selected'):
            for scenario in ('style_rejected','language_rejected','quality_missing','partial'):
                with self.subTest(mode=mode,scenario=scenario):
                    await f.history.async_clear('profile:profile-a')
                    projections=[]
                    async def agent(hass,data,**kwargs):
                        projection=json.loads(data['text'].split('\nData:\n',1)[1])
                        projections.append(projection)
                        if 'available' in projection:
                            reply={'read':'research','reference':mode,'exclude_current':False,
                                   'subject':'Brian Eno','angle':'composition'}
                        elif 'evidence' in projection:
                            # Speak the requested review wire; this is not a
                            # test-side upgrade of the old production reviewer.
                            strict='Also return language_ok and style_ok booleans' in data['text']
                            reply=reviewed_fixture({**projection,'answer':first if scenario=='partial' else full},id_wire=strict)
                            if strict:
                                reply.update(language_ok=scenario!='language_rejected',
                                             style_ok=scenario!='style_rejected')
                                if scenario=='quality_missing':
                                    reply.pop('style_ok',None)
                                if projection['evidence']['public_music_research']['schema_version']==3:
                                    reply['review_schema']='source_id_review_v1'
                                    for check in reply['claim_checks']:
                                        check.pop('quote',None)
                            if scenario=='partial':
                                reply.update(supported=False,unsupported_claims=['He built every instrument.'],
                                    supported_prefix=first,prefix_supported=True,prefix_answers_question=True)
                        else:
                            reply=first+' He built every instrument.' if scenario=='partial' else full
                        return {'response':{'speech':{'plain':{'speech':json.dumps(reply) if isinstance(reply,dict) else reply}}}}
                    context={'selected_entry':reference} if mode=='selected' else None
                    question='Tell me more' if mode=='selected' else 'Tell me about Brian Eno: his music and recordings.'
                    with f.research_http(title='Brian Eno',text=first),patch.object(
                            f.pipeline,'_call_conversation_process_transport',agent):
                        answer,status=await f.request(question,identifier=f'story-review-{mode}-{scenario}',
                            context=context,language='en')
                    self.assertEqual(status,200,answer)
                    self.assertEqual(len(projections),3,projections)
                    self.assertFalse(answer.get('is_generated_text'),answer)
                    self.assertNotEqual(answer.get('text'),first)
                    self.assertTrue(all(s.get('claim_scope')=='qualified_credit_only'
                                        for s in answer.get('sources',[])))
                    self.assertNotIn('research_answer_qualification',answer)
                    self.assertFalse(answer.get('playback_actions'))
                    stored=await f.history.async_history('profile:profile-a')
                    assistant=[m for m in stored['messages'] if m.get('role')=='assistant']
                    self.assertEqual(len(assistant),1,stored)
                    self.assertEqual(assistant[0]['text'],answer['text'])
                    self.assertNotIn(first,assistant[0]['text'])
                    self.assertEqual(f.effects,[])

    async def test_selected_original_credit_has_its_own_review_id_without_biography_credit_substitution(self):
        """Shared publication/open/history path; model and HTTP are declared fixtures."""
        f = self.f
        _, _, reference = await f.selected_credit()
        credit = 'Brian Eno is a composer of the work behind this recording.'
        biography = 'Brian Eno is an English musician.'
        follow_up = 'Would you like to explore more?'
        answer_text = ' '.join((credit, biography, follow_up))
        calls = []

        async def agent(hass, data, **kwargs):
            projection = json.loads(data['text'].split('\nData:\n', 1)[1])
            calls.append(projection)
            if 'available' in projection:
                reply = {'read':'research', 'reference':'selected', 'exclude_current':False,
                         'subject':'Brian Eno', 'angle':'composition'}
            elif 'evidence' in projection:
                selected = projection['evidence']['qualified_context'].get('evidence_spans')
                if not selected:
                    # A source-ID assessor cannot cite an absent original-credit
                    # span. Refuse the whole answer, as the actual probe did.
                    rejected = {'supported':False, 'language_ok':True, 'style_ok':True,
                                'unsupported_claims':[credit]}
                    return {'response':{'speech':{'plain':{'speech':json.dumps(rejected)}}}}
                self.assertEqual(len(selected), 1)
                self.assertEqual(selected[0]['text'], 'Composers of the work behind this recording: Brian Eno.')
                self.assertIn(selected[0]['id'], projection['allowed_evidence_ids'])
                public = projection['evidence']['public_music_research']['sources'][0]['evidence_spans'][0]
                self.assertNotEqual(public['id'], selected[0]['id'])
                self.assertEqual(public['text'], biography)
                reply = {'supported':True, 'language_ok':True, 'style_ok':True,
                         'review_schema':'source_id_review_v1', 'claim_checks':[
                             {'text':credit, 'kind':'relationship', 'evidence_ids':[selected[0]['id']]},
                             {'text':biography, 'kind':'fact', 'evidence_ids':[public['id']]},
                             {'text':follow_up, 'kind':'dj_appreciation', 'evidence_ids':[]}]}
            else:
                reply = answer_text
            return {'response':{'speech':{'plain':{'speech':json.dumps(reply) if isinstance(reply,dict) else reply}}}}

        with f.research_http(title='Brian Eno', text=biography), patch.object(
                f.pipeline, '_call_conversation_process_transport', agent):
            result, status = await f.request('Tell me more', identifier='selected-credit-evidence-id',
                                            context={'selected_entry':reference}, language='en')
        self.assertEqual(status, 200, result)
        self.assertEqual(result['text'], answer_text, result)
        self.assertTrue(result['is_generated_text'])
        self.assertEqual(len(calls), 3)
        self.assertEqual(f.effects, [])
        self.assertFalse(result.get('playback_actions'))
        credit_sources = [s for s in result['sources'] if s.get('claim_scope') == 'qualified_credit_only']
        self.assertEqual(len(credit_sources), 1)
        self.assertEqual(credit_sources[0]['provider'], 'MusicBrainz')
        stored = await f.history.async_history('profile:profile-a')
        self.assertEqual([m['text'] for m in stored['messages'] if m.get('role') == 'assistant'], [answer_text])

    def test_selected_credit_id_cannot_be_authorized_by_plain_json_or_generated_body(self):
        from copy import deepcopy
        from types import SimpleNamespace
        from custom_components.djconnect.ask_dj import public_research as research
        from custom_components.djconnect.ask_dj.dialogue import model_source
        from custom_components.djconnect.public_artist_narration import complete_review_projection, resolve_review_quotes

        entry = {'archive_basis':'cc0_normalized_fields_v1',
                 'text':'A generated presentation is not evidence.',
                 'qualified_fact_text':'Composers of the work behind this recording: Brian Eno.',
                 'dialogue_subjects':[{'name':'Brian Eno', 'role':'composer'}],
                 'source_attribution':{'provider':'MusicBrainz', 'license':'CC0-1.0',
                    'url':'https://musicbrainz.org/work/11111111-1111-1111-1111-111111111111'}}
        def build(candidate, *, interpreted=True, subject='Brian Eno', change_source=False):
            source = model_source(candidate)
            if change_source:
                source['qualified_excerpt'] = 'A forged credit.'
            context = {'public_music_research':{'schema_version':3, 'resolved_public_subject':subject, 'sources':[]},
                       'qualified_context':source}
            turn = SimpleNamespace(selected_read_context=candidate, source_context=source,
                                   interpreted_context_research=interpreted)
            return context, research.selected_credit_context(context, turn)
        _, bound = build(entry)
        span = research.selected_credit_spans(bound)[0]
        review = {'review_schema':'source_id_review_v1', 'claim_checks':[
            {'text':'Brian Eno is credited.', 'kind':'fact', 'evidence_ids':[span['id']]}]}
        self.assertEqual(resolve_review_quotes(review, bound)['claim_checks'][0]['quote'], entry['qualified_fact_text'])
        wire = complete_review_projection(bound)
        self.assertEqual(wire['qualified_context']['evidence_spans'][0], span)
        for forged in (dict(bound), json.loads(json.dumps(wire))):
            self.assertEqual(research.selected_credit_spans(forged), [])
            with self.assertRaises(ValueError):
                resolve_review_quotes(review, forged)
        candidates = []
        for field in ('qualified_fact_text', 'dialogue_subjects'):
            candidate = deepcopy(entry)
            candidate.pop(field)
            candidates.append(candidate)
        for role in ('performer', 'user_named_subject'):
            candidate = deepcopy(entry)
            candidate['dialogue_subjects'][0]['role'] = role
            candidates.append(candidate)
        candidate = deepcopy(entry)
        candidate['source_attribution']['url'] += '?credit=untrusted'
        candidates.append(candidate)
        for candidate in candidates:
            original, result = build(candidate)
            self.assertIs(result, original)
        for kwargs in ({'interpreted':False}, {'subject':'Different artist'}, {'change_source':True}):
            original, result = build(entry, **kwargs)
            self.assertIs(result, original)

    async def test_more_on_reopened_older_contribution_uses_original_subject_and_current_style(self):
        """Actual owner/SQLite/shared route; source and model I/O are fixtures."""
        from custom_components.djconnect.session_conversation import query_service
        from custom_components.djconnect.session_runtime import DJPersona
        f=self.f
        older,moment,reference=await f.selected_credit()
        await f.fixture.manager.async_end(owner_profile_id='profile-a',session_id=older.session_id)
        await f.fixture.service.async_close()
        await f.fixture.service.async_initialize()
        query=query_service(f.hass,f.history)
        raw_before=await query._repository.async_entry_record('profile-a',older.session_id,reference['entry_id'])
        current=await f.fixture.manager.async_start(owner_profile_id='profile-a',locale='nl',
            selected_mood='party',dj_persona=DJPersona.FESTIVAL_DJ,music_backend='spotify_direct')
        await f.fixture.manager.async_update_playback_projection(owner_profile_id='profile-a',
            session_id=current.session_id,state='playing',media_identity='spotify:track:'+'Z'*22,
            title='Different current recording',artist='Different current performer')
        playback_before=current.broadcast.state.playback.as_dict()
        calls=[]
        answer='Brian Eno is een Engelse componist. Zullen we zijn muziek verder verkennen?'
        async def agent(hass,data,**kwargs):
            payload=json.loads(data['text'].split('\nData:\n',1)[1])
            calls.append(payload)
            if 'available' in payload:
                self.assertEqual(payload['qualified_selected_context']['subjects'],[
                    {'name':'Brian Eno','role':'composer'}])
                reply=json.dumps({'read':'research','reference':'selected','exclude_current':False,
                    'subject':'Brian Eno','angle':'composition'})
            elif 'evidence' in payload:
                reply=json.dumps(reviewed_fixture(payload))
            else:
                self.assertEqual(payload['style']['persona'],'festival_dj')
                self.assertEqual(payload['style']['mood'],'party')
                self.assertNotIn('Different current performer',json.dumps(payload))
                self.assertIn('Brian Eno',json.dumps(payload['public_music_research']))
                reply=answer
            return {'response':{'speech':{'plain':{'speech':reply}}}}
        context={'session_id':current.session_id,'selected_entry':reference}
        with f.research_http(title='Brian Eno',text='Brian Eno is an English composer.'),patch.object(
                f.pipeline,'_call_conversation_process_transport',agent):
            result,status=await f.request('Vertel meer',identifier='older-entry-current-style',
                context=context,language='nl')
        self.assertEqual(status,200,result)
        self.assertEqual(result['text'],answer)
        self.assertEqual(result['conversation']['context']['selected_entry'],reference)
        self.assertEqual(result['conversation']['context']['session_id'],current.session_id)
        self.assertEqual(len(calls),3)
        self.assertTrue(result.get('sources'))
        self.assertFalse(result.get('playback_actions'))
        self.assertEqual(f.effects,[])
        self.assertEqual(current.broadcast.state.playback.as_dict(),playback_before)
        self.assertEqual(await query._repository.async_entry_record(
            'profile-a',older.session_id,reference['entry_id']),raw_before)
        old_page=await query.async_timeline_page('profile-a',older.session_id)
        self.assertEqual(next(e['text'] for e in old_page['entries'] if e.get('moment_id')==moment.moment_id),moment.content)
        current_page=await query.async_timeline_page('profile-a',current.session_id)
        self.assertTrue(any(e.get('text')==answer for e in current_page['entries']))
        # Accept the final invitation as a normal next turn, without resending
        # selected_entry. Current playback must not steal the historical subject.
        with f.research_http(title='Brian Eno',text='Brian Eno is an English composer.'),patch.object(
                f.pipeline,'_call_conversation_process_transport',agent):
            followed,status=await f.request('En wat maakt zijn werk interessant?',
                identifier='older-entry-follow-up',context={'session_id':current.session_id},language='nl')
        self.assertEqual(status,200,followed)
        self.assertEqual(followed['text'],answer,followed)
        self.assertEqual(followed['conversation']['metrics']['agent_calls'],2)
        self.assertEqual(len(calls),5)
        self.assertTrue(followed.get('sources'))
        self.assertFalse(followed.get('playback_actions'))
        self.assertEqual(current.broadcast.state.playback.as_dict(),playback_before)
        self.assertEqual(await query._repository.async_entry_record(
            'profile-a',older.session_id,reference['entry_id']),raw_before)
        await f.fixture.repo.async_remove_entry_records('profile-a',[reference['entry_id']])
        forgotten=[]
        async def no_subject(hass,data,**kwargs):
            payload=json.loads(data['text'].split('\nData:\n',1)[1])
            forgotten.append(payload)
            return {'response':{'speech':{'plain':{'speech':json.dumps({
                'read':'none','reference':'none','exclude_current':False})}}}}
        # Removal invalidates the dialogue frame immediately. With no explicit
        # reference the next question is fresh and may clarify; it cannot reuse
        # the old subject or accept the model's unchecked prose.
        from custom_components.djconnect.ask_dj import public_research
        with patch.object(f.pipeline,'_call_conversation_process_transport',no_subject),patch.object(
                public_research,'research',side_effect=AssertionError('Withdrawn subject cannot be researched')) as lookup:
            withdrawn,status=await f.request('En zijn andere werk?',identifier='older-follow-up-removed',
                context={'session_id':current.session_id},language='nl')
        lookup.assert_not_called()
        self.assertEqual(status,200,withdrawn)
        self.assertFalse(withdrawn.get('is_generated_text'))
        self.assertEqual(withdrawn['knowledge_basis'],'public_subject_required')
        self.assertFalse(withdrawn.get('sources'))
        self.assertFalse(withdrawn.get('playback_actions'))
        self.assertEqual(len(forgotten),1)
        for payload in forgotten:
            # Keep assertions outside the transport callback: an agent-error
            # catch must not turn a failing privacy assertion into a green test.
            self.assertNotIn('Brian Eno',json.dumps(payload))
            self.assertNotIn(moment.content,json.dumps(payload))
            self.assertFalse(payload.get('available',{}).get('selected'))
            self.assertFalse(payload.get('qualified_selected_context'))
        self.assertEqual(current.broadcast.state.playback.as_dict(),playback_before)
        self.assertEqual(f.effects,[])
        self.assertEqual(len(calls),5)
        with patch.object(f.pipeline,'_call_conversation_process_transport',
                side_effect=AssertionError('Removed selected history must not become current-artist research')):
            denied,status=await f.request('Vertel meer',identifier='older-entry-removed',
                context=context,language='nl')
        self.assertEqual(status,404,denied)
        self.assertEqual(current.broadcast.state.playback.as_dict(),playback_before)
        self.assertEqual(f.effects,[])
        self.assertEqual(len(calls),5)

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
