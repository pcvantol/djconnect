"""Semantic read plans exercise actual shared-owner routes; not model-quality proof."""

import json
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


def id_review_fixture(projection):
    """A reviewer selects the actual compact wire IDs; no copied quote in wire."""
    if 'drafts' in projection and 'answer' not in projection:
        return {'draft_reviews': [{'index': row['index'], 'sha256': row['sha256'],
            'review': id_review_fixture({**projection, 'answer': row['text']})} for row in projection['drafts']]}
    from custom_components.djconnect.ask_dj.public_research import _sentences
    spans = [span for source in projection['evidence']['public_music_research']['sources']
             for span in source.get('evidence_spans', [])]
    return {'supported':True,'language_ok':True,'style_ok':True,'unsupported_claims':[], 'review_schema':'source_id_review_v1','claim_checks':[
        {'text':sentence,'kind':'fact','evidence_ids':[spans[0]['id']]}
        for sentence in _sentences(projection['answer'])]}


class SemanticReadTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_artist_story_paraphrases_reuse_public_research_and_assessment_in_all_locales(self):
        f = self.f
        questions = ('tell me a bit about this artist', 'vertel eens over deze artiest',
            'erzähl mir etwas über diesen Künstler', 'parle-moi de cet artiste',
            'cuéntame algo sobre este artista')
        answers = ('Volbeat is a Danish band.', 'Volbeat is een Deense band.',
            'Volbeat ist eine dänische Band.', 'Volbeat est un groupe danois.',
            'Volbeat es una banda danesa.')
        from pathlib import Path
        catalogue = json.loads((Path(__file__).resolve().parents[1] /
            'custom_components/djconnect/ask_dj/examples_v1.json').read_text())
        canonical = next(row['templates'] for row in catalogue['entries'] if row['id']=='listen.artist')
        locales = ('en','nl','de','fr','es')
        cases = list(zip(locales, questions, answers, strict=True))
        cases += [(locale, canonical[locale], text) for locale,text in zip(locales,answers,strict=True)]
        for sequence, (locale, question, text) in enumerate(cases):
            await f.history.async_clear('profile:profile-a')
            calls, commands = [], []
            async def agent(hass, data, **kwargs):
                projection = json.loads(data['text'].split('\nData:\n', 1)[1])
                calls.append(projection)
                if set(projection) == {'question', 'language', 'available'}:
                    reply = json.dumps({'read':'artist_story','reference':'current','exclude_current':False})
                elif 'evidence' in projection:
                    self.assertEqual(projection['language'],locale)
                    review = (id_review_fixture(projection)
                        if projection['evidence']['public_music_research']['schema_version'] == 3
                        else shared._research_assessment_fixture(projection))
                    reply = json.dumps(review)
                else:
                    reply = shared._research_generation_fixture(projection, text)
                return {'response': {'speech': {'plain': {'speech': reply}}}}
            async def status(hass, runtime, command, *args, **kwargs):
                commands.append(command)
                return {'success': True, 'playback': {'uri':'spotify:track:'+'N'*22,
                    'artist':'Volbeat', 'title':'Private current recording'}}
            with f.research_http(title='Volbeat', text='Volbeat is a Danish band.'), patch.object(
                    f.pipeline, '_call_conversation_process_transport', agent), patch.object(f.core, 'run_music_command', status):
                answer, code = await f.request(question, identifier=f'artist-story-{locale}-{sequence}', language=locale)
            self.assertEqual(code, 200, answer)
            self.assertEqual(answer.get('knowledge_basis'), 'fetched_public_music_research_v1', answer)
            self.assertTrue(answer.get('is_generated_text'), answer)
            self.assertEqual(answer['conversation']['metrics']['agent_calls'], 3)
            self.assertEqual(len(calls), 3)
            self.assertEqual(set(commands), {'status'})
            self.assertNotIn('Private current recording', json.dumps(calls))
            self.assertFalse(answer.get('playback_actions'))

    async def test_actual_artist_route_brief_focus_preserves_broader_scope_and_private_boundary(self):
        # An intentional before-generation stop observes the actual route; it is
        # not a model-quality pass or a fabricated accepted telling.
        from custom_components.djconnect.ask_dj.dialogue import DialogueError
        f = self.f
        title = 'Arbor Circuit'
        original_text = ('Arbor Circuit is a musical group.\n'
            'A guest collaborated with the ensemble on a recording before being asked to join as a full-time member.\n'
            'Arbor Circuit performed a concert with another ensemble.')
        questions = (
            ('en', 'Tell me about this artist', True),
            ('nl', 'Vertel iets over deze artiest', True),
            ('de', 'Erzähl etwas über diesen Künstler', True),
            ('fr', 'Parle-moi de cet artiste', True),
            ('es', 'Cuéntame sobre este artista', True),
            ('en', 'Tell me about this artist and the production work', False),
            ('nl', 'Vertel iets over deze artiest en wanneer hij bij de band kwam', False),
            ('de', 'Erzähl etwas über diesen Künstler und seine Karriere', False),
            ('fr', 'Parle-moi de cet artiste et des membres du groupe', False),
            ('es', 'Cuéntame sobre este artista y su trabajo de producción', False),
        )
        captured, commands = [], []
        async def agent(hass, data, **kwargs):
            projection = json.loads(data['text'].split('\nData:\n', 1)[1])
            if set(projection) == {'question', 'language', 'available'}:
                reply = json.dumps({'read': 'artist_story', 'reference': 'current',
                    'exclude_current': False})
                return {'response': {'speech': {'plain': {'speech': reply}}}}
            self.assertEqual(projection.get('artist_draft_schema'), 'artist_evidence_drafts_v1')
            captured.append(projection)
            raise DialogueError('costfree_probe_stopped_before_generation', 409)
        async def status(hass, runtime, command, *args, **kwargs):
            commands.append(command)
            return {'success': True, 'playback': {'uri': 'spotify:track:' + 'N' * 22,
                'artist': title, 'title': 'PRIVATE_RECORDING_CANARY'}}
        with f.research_http(title=title, text=original_text), patch.object(
                f.pipeline, '_call_conversation_process_transport', agent), patch.object(
                f.core, 'run_music_command', status):
            for index, (locale, question, expected_brief) in enumerate(questions):
                await f.history.async_clear('profile:profile-a')
                before = len(captured)
                body, code = await f.request(question, identifier=f'activity-route-{index}',
                    language=locale)
                self.assertEqual(code, 409, body)
                self.assertEqual(body.get('error'), 'costfree_probe_stopped_before_generation')
                self.assertEqual(len(captured), before + 1)
                projection = captured[-1]
                self.assertEqual(projection['question'], question)
                research = projection['public_music_research']
                focus = research['editorial_focus']
                selected = [span for source in research['sources']
                    for span in source['evidence_spans'] if span['id'] in focus['episode_span_ids']]
                self.assertEqual(len(selected), 1)
                self.assertEqual('performed a concert' in selected[0]['text'], expected_brief)
                full = [span['text'] for source in research['sources'] for span in source['evidence_spans']]
                self.assertTrue(any('full-time member' in text for text in full))
                self.assertTrue(any('performed a concert' in text for text in full))
                self.assertNotIn('PRIVATE_RECORDING_CANARY', json.dumps(projection))
        self.assertEqual(set(commands), {'status'})
        self.assertEqual(f.effects, [])

    async def test_artist_story_does_not_publish_across_changed_playback(self):
        f = self.f
        changed = [False]
        async def status(hass, runtime, command, *args, **kwargs):
            return {'success': True, 'playback': {'uri':'spotify:track:'+('M' if changed[0] else 'N')*22,
                'artist':'Volbeat','title':'Private current recording'}}
        original = f.pipeline._call_conversation_process_transport
        async def agent(hass, data, **kwargs):
            projection = json.loads(data['text'].split('\nData:\n',1)[1])
            if set(projection) == {'question','language','available'}:
                return {'response': {'speech': {'plain': {'speech': json.dumps({
                    'read':'artist_story','reference':'current','exclude_current':False})}}}}
            if 'evidence' in projection:
                changed[0] = True
                review = (id_review_fixture(projection)
                    if projection['evidence']['public_music_research']['schema_version'] == 3
                    else shared._research_assessment_fixture(projection))
                return {'response': {'speech': {'plain': {'speech':json.dumps(review)}}}}
            return await original(hass, data, **kwargs)
        with f.research_http(title='Volbeat', text='Volbeat is a Danish band.'), patch.object(
                f.pipeline, '_call_conversation_process_transport', agent), patch.object(f.core,'run_music_command',status):
            answer, code = await f.request('tell me about the artist playing now', identifier='artist-story-race')
        self.assertEqual(code,409,answer)
        self.assertEqual(answer.get('error'),'playback_context_changed')
        self.assertEqual(f.effects, [])

    def test_intro_passage_selection_keeps_literal_episode_offsets_and_identity(self):
        from custom_components.djconnect.ask_dj.public_research import paragraph_excerpt
        identity='Example Group is a musical group.'
        listing='Its releases include Studio One, Studio Two, Studio Three and Studio Four.'
        episode='The group performed on the soundtrack for the film Example Picture.'
        source='\n'.join((identity,listing,episode))
        budget=len(identity)+len(episode)+1
        selected,ranges=paragraph_excerpt(source,'tell me about this artist',budget,prefer_artist_episode=True)
        self.assertEqual(selected,identity+'\n'+episode)
        self.assertEqual(selected,'\n'.join(source[start:end] for start,end in ranges))
        self.assertEqual(ranges,((0,len(identity)),(source.index(episode),len(source))))

    def test_named_work_inside_appreciation_still_needs_its_factual_source_receipt(self):
        from custom_components.djconnect.ask_dj import public_research as p
        text='Blue Arc is an album by Example Group.'
        source=p._source('Wikipedia','Example Group','https://en.wikipedia.org/wiki/Example_Group',text,'en',
            source_anchors=('Blue Arc',),original_text=text,paragraph_ranges=((0,len(text)),)).model_data()
        context={'public_music_research':{'schema_version':3,'sources':[source]},'qualified_context':{}}
        span=p.evidence_spans(source)[0]
        answer='I’m intrigued by Blue Arc: it is an album by Example Group.'
        proof={'supported':True,'claim_checks':[
            {'text':'I’m intrigued by Blue Arc:','kind':'dj_appreciation','evidence_ids':[],'quote':''},
            {'text':'it is an album by Example Group.','kind':'fact','evidence_ids':[span['id']],'quote':span['text']}]}
        self.assertFalse(p.supported(json.dumps(proof),answer,context))
        proof['claim_checks'][:1]=[
            {'text':'I’m intrigued by ','kind':'dj_appreciation','evidence_ids':[],'quote':''},
            {'text':'Blue Arc:','kind':'fact','evidence_ids':[span['id']],'quote':span['text']}]
        self.assertTrue(p.supported(json.dumps(proof),answer,context))
        # A lexical opinion must not hide a new musical/technique assertion.
        wrong='I’m intrigued by experimental Blue Arc: it is an album by Example Group.'
        proof['claim_checks'][0]['text']='I’m intrigued by experimental '
        self.assertFalse(p.supported(json.dumps(proof),wrong,context))

    def test_translated_production_activity_accepts_explicit_progressive_source_not_guest_credit_alone(self):
        from custom_components.djconnect.ask_dj import public_research as p
        answers=('Sur l’album Blue Arc, Ada Rivers a enregistré des solos invités et participé à la production.',
                 'Ada Rivers produjo y grabó solos invitados para Blue Arc.')
        quotes=('Ada Rivers had been producing and recording guest solos on Blue Arc.',
                'Ada Rivers había estado produciendo y grabando solos invitados en Blue Arc.')
        for answer in answers:
            for quote in quotes:
                source=p._source('Wikipedia','Example Group','https://en.wikipedia.org/wiki/Example_Group',quote,'en',
                    source_anchors=('Blue Arc',),original_text=quote,paragraph_ranges=((0,len(quote)),)).model_data()
                span=p.evidence_spans(source)[0]
                context={'public_music_research':{'schema_version':3,'sources':[source]},'qualified_context':{}}
                proof={'supported':True,'claim_checks':[{'text':answer,'kind':'relationship',
                    'evidence_ids':[span['id']],'quote':span['text']}]}
                self.assertTrue(p.supported(json.dumps(proof),answer,context),(answer,quote))
            self.assertFalse(p._assertions_fit(answer,'Ada Rivers recorded guest solos on Blue Arc.'))
            self.assertFalse(p._assertions_fit(answer,'Ada Rivers played guest guitar on Blue Arc.'))

    def test_work_order_cannot_borrow_a_work_name_to_reverse_or_invent_sequence(self):
        from custom_components.djconnect.ask_dj import public_research as p
        def judge(answer,source_text,anchors=('Blue Arc',)):
            source=p._source('Wikipedia','Example Group','https://en.wikipedia.org/wiki/Example_Group',source_text,'en',
                source_anchors=anchors,original_text=source_text,paragraph_ranges=((0,len(source_text)),)).model_data()
            span=p.evidence_spans(source)[0]
            context={'public_music_research':{'schema_version':3,'sources':[source]},'qualified_context':{}}
            review={'supported':True,'claim_checks':[{'text':answer,'kind':'relationship',
                'evidence_ids':[span['id']],'quote':span['text']}]}
            return p.supported(json.dumps(review),answer,context)
        answer='Ada Rivers recorded guest solos for Blue Arc and subsequently joined Example Group.'
        self.assertTrue(p._UNBOUND_SEQUENCE.search(answer))
        source='Ada Rivers recorded guest solos for Blue Arc before joining Example Group.'
        self.assertFalse(judge(answer,source))
        for wrong in (
                "After leaving Earlier Group, Ada Rivers recorded guest solos for Blue Arc.",
                "Ada Rivers joined Example Group and subsequently recorded guest solos for Blue Arc."):
            self.assertFalse(judge(wrong,source),wrong)
        self.assertFalse(judge(answer,'Ada Rivers recorded guest solos for Blue Arc. Ada Rivers joined Example Group.'))
        self.assertFalse(judge(answer.replace('Blue Arc','Red Arc'),source+' Ada Rivers also recorded Red Arc.',('Blue Arc','Red Arc')))
        relative='Ada Rivers recorded Blue Arc and that same year joined Example Group.'
        self.assertFalse(judge(relative,source))

    async def test_artist_story_requires_independent_style_and_language_acceptance(self):
        f = self.f
        for index, quality in enumerate(({'style_ok':False,'language_ok':True},
                                        {'style_ok':True,'language_ok':False},
                                        {'style_ok':'true','language_ok':True}, {})):
            await f.history.async_clear('profile:profile-a')
            async def agent(hass, data, **kwargs):
                projection = json.loads(data['text'].split('\nData:\n',1)[1])
                if set(projection)=={'question','language','available'}:
                    reply=json.dumps({'read':'artist_story','reference':'current','exclude_current':False})
                elif 'evidence' in projection:
                    review=id_review_fixture(projection)
                    reviews = [row['review'] for row in review['draft_reviews']] if 'draft_reviews' in review else [review]
                    for item in reviews:
                        item.pop('style_ok')
                        item.pop('language_ok')
                        item.update(quality)
                    reply=json.dumps(review)
                else:
                    reply=shared._research_generation_fixture(projection, 'Volbeat is a Danish band.')
                return {'response': {'speech': {'plain': {'speech':reply}}}}
            async def status(hass,runtime,command,*args,**kwargs):
                self.assertEqual(command,'status')
                return {'success':True,'playback':{'uri':'spotify:track:'+'N'*22,
                    'title':'Current recording','artist':'Volbeat'}}
            with f.research_http(title='Volbeat',text='Volbeat is a Danish band.'), patch.object(
                    f.pipeline,'_call_conversation_process_transport',agent), patch.object(f.core,'run_music_command',status):
                answer,code=await f.request('tell me about this artist',identifier='artist-quality-'+str(index))
            self.assertEqual(code,200,answer)
            self.assertFalse(answer.get('is_generated_text'))
            self.assertEqual(answer.get('knowledge_basis'),'public_research_unqualified')
            self.assertEqual(answer['public_research_status']['answer_state'],'drafts_unqualified')
        self.assertEqual(f.effects,[])

    async def test_album_followups_keep_full_context_exact_title_receipt_and_duplicate(self):
        f = self.f
        from custom_components.djconnect.domain.profile import ProfilePreferences
        await f.handlers.profile_storage(f.hass).async_update_profile('profile-a',
            preferences=ProfilePreferences(default_backend_id='source-spotify'))
        f.runtime.config['music_backend'] = 'spotify_direct'
        f.runtime.update = lambda **values: f.runtime.__dict__.update(values)
        from custom_components.djconnect import http
        from custom_components.djconnect.playback_request import outcome
        album = 'spotify:album:'+'B'*22
        track = 'spotify:track:'+'T'*22
        languages = ('en','nl','de','fr','es')
        questions = ('Yes, I want to play that album.', 'Ja, die wil ik afspelen.',
            'Ja, dieses Album möchte ich hören.', 'Oui, je veux écouter cet album.',
            'Sí, quiero escuchar ese álbum.')
        async def offer(*args, **kwargs):
            return {'success':True,'text':'One exact synthetic album.',
                'playback_actions':[{'kind':'album','uri':album,'context_uri':album,
                    'title':'Exact requested album','artist':'Volbeat'}]}
        for locale, question in zip(languages,questions,strict=True):
            await f.history.async_clear('profile:profile-a')
            writes = []
            observed = {'uri':track,'context_uri':album,'is_playing':True,
                        'title':'Wrong first-track label','artist':'Volbeat'}
            async def command(hass, runtime, name, value=None, **kwargs):
                if name == 'play':
                    writes.append(value)
                    selection = {'kind':'album','context_uri':album,'uris':[], 'media':{'uri':album}}
                    return {'success':True,'playback':observed,'playback_outcome':outcome(selection,observed)}
                self.assertEqual(name, 'status')
                return {'success':True,'playback':observed}
            with patch.object(f.core, '_handle_informational', offer):
                result, code = await f.request('Which albums by Volbeat?', identifier='frozen-offer-'+locale, language=locale)
                self.assertEqual(code,200,result)
            with patch.object(http,'run_music_command',command):
                answer, code = await f.request(question, identifier='frozen-accept-'+locale, language=locale)
                duplicate, status = await f.request(question, identifier='frozen-accept-'+locale, language=locale)
            self.assertEqual(code,200,answer)
            self.assertEqual(status,200,duplicate)
            self.assertEqual(writes,[album], (locale, answer.get('error'),answer.get('text'),answer.get('intent'),answer.get('result_set')))
            self.assertEqual(answer['playback_outcome']['state'],'observed')
            self.assertEqual(answer['resolved_media']['uri'],album)
            self.assertIn('Exact requested album',answer['text'])
            self.assertNotIn('Wrong first-track label',answer['text'])
            self.assertEqual(answer['text'],duplicate['text'])

    async def test_unlisted_typo_is_interpreted_then_answered_from_fresh_provider(self):
        f = self.f
        prompts, reads = [], []

        async def agent(hass, data, **kwargs):
            prompts.append(json.loads(data["text"].split("\nData:\n", 1)[1]))
            return {"response": {"speech": {"plain": {"speech": json.dumps({
                "read": "artist", "reference": "current", "exclude_current": False
            })}}}}

        async def status(hass, runtime, command, *args, **kwargs):
            reads.append(command)
            return {"success": True, "playback": {"uri": "spotify:track:" + "N" * 22,
                    "artist": "Actual provider artist", "title": "Actual provider recording"}}

        with patch.object(f.pipeline, "_call_conversation_process_transport", agent), patch.object(
            f.core, "run_music_command", status
        ):
            answer, code = await f.request("hee wie zingdt er eigelijk wat nu opstaat?")
        self.assertEqual(code, 200, answer)
        self.assertEqual(answer["intent"]["intent"], "current_artist_information")
        self.assertIn("Actual provider artist", answer["text"])
        self.assertEqual(answer["conversation"]["metrics"]["agent_calls"], 1)
        self.assertGreaterEqual(len(reads), 2)
        self.assertEqual(set(reads), {"status"})
        self.assertEqual(set(prompts[0]), {"question", "language", "available"})
        self.assertNotIn("Actual provider", json.dumps(prompts))
        self.assertFalse(answer.get("playback_actions"))
        self.assertFalse(answer["history_persisted"])

    def test_plan_is_closed_duplicate_safe_and_never_an_effect(self):
        from custom_components.djconnect.ask_dj.semantic_reads import parse_plan
        valid = {"read": "artist", "reference": "current", "exclude_current": False}
        self.assertEqual(parse_plan(json.dumps(valid)).read, "artist")
        for raw in (
            '{"read":"artist","read":"play","reference":"current","exclude_current":false}',
            json.dumps({**valid, "uri": "spotify:track:" + "N" * 22}),
            json.dumps({**valid, "read": "play"}),
            json.dumps({**valid, "reference": "previous"}),
            json.dumps({**valid, "exclude_current": 0}),
            json.dumps({**valid, "exclude_current": True}),
            "```json\n" + json.dumps(valid) + "\n```",
            "x" * 2049,
        ):
            with self.subTest(raw=raw[:100]):
                self.assertIsNone(parse_plan(raw))

    async def test_reported_short_artist_and_singers_questions_read_context_without_claiming_vocal_roles(self):
        async def source(hass, runtime, command, *args, **kwargs):
            self.assertEqual(command, "status")
            return {"success": True, "playback": {"uri": "spotify:track:" + "N" * 22,
                "artist": "Actual credited artists", "title": "Actual recording"}}
        for index, question in enumerate(("wie is de artiest", "wie zijn de zangers")):
            with self.agent({"read": "artist", "reference": "current", "exclude_current": False}), patch.object(
                self.f.core, "run_music_command", source
            ):
                answer, code = await self.f.request(question, language="nl", identifier="short-artist-" + str(index))
            self.assertEqual(code, 200, answer)
            self.assertIn("Actual credited artists", answer["text"])
            self.assertIn("Actual recording", answer["text"])
            self.assertNotIn("zangers", answer["text"])
            self.assertEqual(self.f.effects, [])

    def agent(self, plan, *, inspect=None):
        async def response(hass, data, **kwargs):
            projection = json.loads(data["text"].split("\nData:\n", 1)[1])
            self.f.prompts.append(projection)
            if inspect:
                await inspect(projection)
            return {"response": {"speech": {"plain": {"speech": json.dumps(plan)}}}}
        return patch.object(self.f.pipeline, "_call_conversation_process_transport", response)

    async def test_selected_recording_survives_unrecognized_wording_and_does_not_use_current(self):
        session = await self.f.fixture.observed_session()
        from custom_components.djconnect.session_conversation import query_service
        page = await query_service(self.f.hass, self.f.history).async_timeline_page(
            "profile-a", session.session_id
        )
        observed = next(e for e in page["entries"] if e["kind"] == "playback_observed")
        context = {"session_id": session.session_id,
                   "selected_entry": {"session_id": session.session_id, "entry_id": observed["entry_id"]}}
        with self.agent({"read": "artist", "reference": "selected", "exclude_current": False}):
            answer, code = await self.f.request("even checken, wie maakt de musiek hierbij eigelijk?",
                                                context=context)
        self.assertEqual(code, 200, answer)
        self.assertIn("Metallica", answer["text"])
        self.assertEqual(answer["conversation"]["context"]["selected_entry"], context["selected_entry"])
        self.assertTrue(self.f.prompts[0]["available"]["selected"])
        self.assertNotIn("Metallica", json.dumps(self.f.prompts))

    async def test_invalid_effect_or_missing_selection_never_dispatches_or_retries(self):
        for index, plan in enumerate((
            {"read": "play", "reference": "current", "exclude_current": False},
            {"read": "artist", "reference": "selected", "exclude_current": False},
            {"read": "artist", "reference": "current", "exclude_current": False, "command": "play"},
        )):
            before = len(self.f.prompts)
            with self.agent(plan):
                answer, code = await self.f.request("hee wie zingdt er eigelijk wat nu opstaat?",
                                                    identifier="invalid-" + str(index))
            self.assertEqual(code, 200, answer)
            self.assertEqual(len(self.f.prompts) - before, 1)
            self.assertEqual(answer["knowledge_basis"], "public_subject_required")
            self.assertFalse(answer.get("playback_actions"))
        self.assertEqual(self.f.effects, [])

    async def test_clear_during_interpretation_rejects_before_read(self):
        async def clear(projection):
            await self.f.history.async_clear("profile:profile-a")
        with self.agent({"read": "artist", "reference": "current", "exclude_current": False}, inspect=clear):
            answer, code = await self.f.request("hee wie zingdt er eigelijk wat nu opstaat?")
        self.assertEqual(code, 409, answer)
        self.assertFalse(answer.get("success"))
        self.assertEqual(self.f.effects, [])

    async def test_session_end_during_interpretation_cannot_rebind_to_new_context(self):
        session = await self.f.fixture.observed_session()
        async def end(projection):
            await self.f.fixture.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        with self.agent({"read": "artist", "reference": "current", "exclude_current": False}, inspect=end):
            answer, code = await self.f.request("hee wie zingdt er eigelijk wat nu opstaat?")
        self.assertEqual(code, 409, answer)
        self.assertEqual(self.f.effects, [])

    async def test_inherited_cc0_subject_does_not_override_semantic_current_artist(self):
        session, moment, selection = await self.f.selected_credit("Brian Eno")
        async def status(hass, runtime, command, *args, **kwargs):
            self.assertEqual(command, "status")
            return {"success": True, "playback": {"uri": "spotify:track:0123456789abcdefghijkL",
                    "artist": "Actual current performer", "title": "Actual current recording"}}
        plan = {"read": "artist", "reference": "current", "exclude_current": False}
        with patch.object(self.f.core, "run_music_command", status), self.agent(plan):
            answer, code = await self.f.request("wie maakt dit nu eigelijk?",
                                                context={"selected_entry": selection}, language="nl")
        self.assertEqual(code, 200, answer)
        self.assertIn("Actual current performer", answer["text"])
        self.assertNotIn("Brian Eno", answer["text"])
        self.assertEqual(len(self.f.prompts), 1)
        self.assertIn("read_context_available", self.f.prompts[0])
        self.assertEqual(answer["conversation"]["metrics"]["agent_calls"], 1)

    async def test_no_session_to_new_session_during_forecast_interpretation_is_rejected(self):
        async def start(projection):
            await self.f.fixture.observed_session()
        with self.agent({"read": "forecast", "reference": "none", "exclude_current": False}, inspect=start):
            answer, code = await self.f.request("hoe ziet jouw dj plan voor dit luisterblok eruit?")
        self.assertEqual(code, 409, answer)
        self.assertEqual(answer["error"], "session_context_changed")
        self.assertEqual(self.f.effects, [])

    def test_golden_case_vocabulary_never_becomes_runtime_recognition(self):
        from scripts.verification.askdj_semantic_read_golden import cases
        from custom_components.djconnect.ask_dj.dialogue import requests_lookup
        from custom_components.djconnect.ask_dj.public_research import explicit_public_subject, safe_subject
        from collections import Counter
        rows = cases()
        self.assertEqual(Counter(c["language"] for c in rows), dict.fromkeys(("en", "nl", "de", "fr", "es"), 11))
        for case in rows:
            self.assertEqual(self.f.core.classify_ask_dj(case["question"]).intent, "ask_music_info", case)
            self.assertFalse(requests_lookup(case["question"]), case)
            named = explicit_public_subject(case["question"])
            if case["unqualified_subject_capture"]:
                self.assertTrue(named, case)
                self.assertFalse(safe_subject(named), case)
            else:
                self.assertFalse(named, case)

    async def test_question_clause_captured_as_name_does_not_block_semantic_interpretation(self):
        from scripts.verification.askdj_semantic_read_golden import cases
        async def status(hass, runtime, command, *args, **kwargs):
            return {"success": True, "playback": {"uri": "spotify:track:" + "N" * 22,
                    "artist": "Actual performer", "title": "Actual recording"}}
        with patch.object(self.f.core, "run_music_command", status), self.agent(
            {"read": "artist", "reference": "current", "exclude_current": False}
        ):
            for case in (c for c in cases() if c["unqualified_subject_capture"]):
                answer, code = await self.f.request(case["question"], identifier=case["id"], language=case["language"])
                self.assertEqual(code, 200, answer)
                self.assertIn("Actual performer", answer["text"])
                self.assertEqual(answer["conversation"]["metrics"]["agent_calls"], 1)

    async def test_unqualified_name_capture_keeps_selected_recording(self):
        session = await self.f.fixture.observed_session()
        from custom_components.djconnect.session_conversation import query_service
        page = await query_service(self.f.hass, self.f.history).async_timeline_page("profile-a", session.session_id)
        entry = next(e for e in page["entries"] if e["kind"] == "playback_observed")
        context = {"selected_entry": {"session_id": session.session_id, "entry_id": entry["entry_id"]}}
        with self.agent({"read": "artist", "reference": "selected", "exclude_current": False}):
            answer, code = await self.f.request("Wie is degene die dit hier zo mooi zingt?", context=context, language="nl")
        self.assertEqual(code, 200, answer)
        self.assertIn("Metallica", answer["text"])
        self.assertEqual(answer["conversation"]["context"]["selected_entry"], context["selected_entry"])

    async def test_recording_question_on_artist_only_selection_never_claims_artist_is_a_title(self):
        from custom_components.djconnect import session_facts
        uri = "spotify:track:" + "A" * 22
        manager = self.f.fixture.manager
        session = await manager.async_start(owner_profile_id="profile-a", locale="nl",
                                           selected_mood="groove", music_backend="spotify_direct")
        await manager.async_update_playback_projection(owner_profile_id="profile-a", session_id=session.session_id,
            state="playing", media_identity=uri, title="Recording", artist="Selected group", duration_ms=300000, position_ms=1000)
        fact = session_facts._fact("artist_begin", {"uri": uri}, "artist_story", ["Selected group"] * 5,
            ["Selected group formed in 2000.", "Selected group is opgericht in 2000.",
             "Selected group wurde 2000 gegründet.", "Selected group a été formé en 2000.",
             "Selected group se formó en 2000."], "MusicBrainz",
            "https://musicbrainz.org/artist/11111111-1111-1111-1111-111111111111",
            session_facts.DisplayFactCore("artist_begin", "Selected group", date="2000", precision="year", entity_type="Group"))
        async def facts():
            return {"_qualified_facts": (fact,)}
        moment = await manager.async_process_track_started(owner_profile_id="profile-a", session_id=session.session_id,
            media_identity=uri, insight_provider=facts, require_current_playback=True, allow_initial_facts=True)
        context = {"selected_moment": {"session_id": session.session_id, "moment_id": moment.moment_id}}
        with self.agent({"read": "recording", "reference": "selected", "exclude_current": False}):
            answer, code = await self.f.request("hoe heet het liedjuh hierbij nou?", context=context, language="nl")
        self.assertEqual(code, 200, answer)
        self.assertIn("opname", answer["text"])
        self.assertNotEqual(answer["text"], "Dit is Selected group.")
        self.assertEqual(answer["conversation"]["context"]["selected_moment"], context["selected_moment"])
        self.assertFalse(answer.get("playback_actions"))
