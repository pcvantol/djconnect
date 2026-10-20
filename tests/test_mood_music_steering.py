"""Real owner/Flow acceptance; backend and HA model are explicit fixtures."""
import asyncio
import json
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared
from tests import test_profile_settings_owner as settings_fixture


class MoodMusicSteeringTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = shared.SharedDialogueTest()
        await self.f.asyncSetUp()
        from custom_components.djconnect import mood_music_steering
        self.steering = mood_music_steering
        self.session,_,_ = await self.f.selected_credit()
        from custom_components.djconnect.domain.profile import ProfilePreferences
        await self.f.handlers.profile_storage(self.f.hass).async_update_profile('profile-a',
            preferences=ProfilePreferences(default_backend_id='source-spotify',default_music_account_id='source-account'))
        self.f.runtime.config['music_backend'] = 'spotify_direct'
        self.f.runtime.config['profile_backend_entry_id'] = 'source-entry'
        from custom_components.djconnect.session_conversation import async_qualify_history_source
        self.f.fixture.queries._source_validator = lambda owner,row: async_qualify_history_source(self.f.hass,owner,row)
        self.calls=[]
        self.models=[]

    async def asyncTearDown(self):
        tasks=list(getattr(self.f.fixture.manager,'_mood_music_tasks',{}).values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        await self.f.asyncTearDown()

    async def backend(self,hass,runtime,command,value=None,**kwargs):
        self.calls.append(command)
        if command=='queue':
            return {'success':True,'queue':[], 'currently_playing':{'uri':'spotify:track:'+'C'*22}}
        if command=='playlists':
            return {'success':True,'playlists':[{'uri':'spotify:playlist:'+'L'*22,
                'name':'Private library evening groove party','owner':'Owner'}]}
        raise AssertionError('no automatic playback or unrelated backend call: '+command)

    async def agent(self,hass,data,**kwargs):
        projection=json.loads(data['text'].split('\nData:\n',1)[1])
        self.models.append(projection)
        if 'allowed' in projection:
            reply={'decision':'selected','genre':'soul'}
        elif 'frame' in projection:
            reply={'language_ok':True,'style_ok':True,'meaning_ok':True}
        else:
            reply=({'frame':'I need a little more direction before choosing music: {choices}. Which sounds good to you?',
                    'genres':['soul','indie','electronic']} if projection.get('clarification_required') else
                   {'frame':'These names suggest a fresh direction, without guaranteeing the sound: {choices}. Shall I start one?',
                    'genres':[]})
        return {'response':{'speech':{'plain':{'speech':json.dumps(reply)}}}}

    async def request(self,identifier='mood-test',**extra):
        f=self.f
        active=f.fixture.manager.current_active('profile-a')
        transition=self.steering.Transition('profile-a',active.session_id,active.settings_generation,
                                          active.mood_revision,active.selected_mood)
        return await f.handlers.async_handle_ask_dj_message_payload(f.hass,{
            **f.identity,'client_message_id':identifier,'text':'Suggest music for my new session mood',
            'language':'en','audio_response':'never','conversation_context':{'session_id':active.session_id},
            **extra},headers=f.headers,_mood_transition=transition)

    async def test_feedback_uses_real_library_and_flow_without_automatic_playback_or_metadata_in_model(self):
        f=self.f
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend), patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent):
            result,status=await self.request()
        self.assertEqual(status,200,result)
        self.assertEqual(self.calls,['queue','playlists'])
        self.assertEqual(len(self.models),2)
        self.assertNotIn('Private library',json.dumps(self.models))
        self.assertEqual(result['origin'],'mood_change')
        self.assertIn('Private library evening groove party',result['text'])
        action=result['playback_actions'][0]
        self.assertEqual(action['kind'],'playlist')
        self.assertEqual(action['label'],'Start now')
        self.assertEqual(action['queue_effect'],'start_context_now')
        self.assertIn('replace_queue_mix',result['music_steering']['unavailable_actions'])
        self.assertEqual(result['user_message']['message_kind'],'system')
        self.assertEqual(result['user_message']['origin'],'mood_change')
        self.assertEqual(f.effects,[])
        history=await f.history.async_history('profile:profile-a')
        self.assertEqual(history['messages'][-1]['text'],result['text'])
        again=await f.history.async_saved_exchange('profile:profile-a','mood-test')
        self.assertIsNotNone(again)

    async def test_second_request_identity_deduplicates_feedback_and_agent_calls(self):
        f=self.f
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend), patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent):
            first,status=await self.request('mood-repeat')
            second,status2=await self.request('mood-repeat')
        self.assertEqual((status,status2),(200,200),(first,second))
        self.assertTrue(second['deduplicated'])
        self.assertEqual(len(self.models),2)
        self.assertEqual(self.calls,['queue','playlists'])

    async def test_changed_mood_rejects_old_proposal_before_effect(self):
        f=self.f
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend), patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent):
            first,status=await self.request('mood-offer')
            self.assertEqual(status,200,first)
            await f.fixture.manager.async_update_mood(owner_profile_id='profile-a',
                session_id=self.session.session_id,selected_mood='party')
            selected=first['playback_actions'][0]
            result,status=await f.request('Play that',identifier='mood-old-choice',
                choice_action={'result_set_id':selected['result_set_id'],
                               'action_id':selected['action_id'],'operation':'play'})
        self.assertEqual(status,409,result)
        self.assertEqual(result['error'],'mood_proposal_changed')
        self.assertEqual(f.effects,[])

    def test_frames_cannot_change_effects_through_extra_placeholders(self):
        valid=self.steering.valid_frame
        self.assertTrue(valid('Ready for {choices}; shall I start it now?'))
        for frame in ('Ready for {choices.name}; shall I start?', 'Ready for {choices!r}; shall I start?',
                      'Ready for {choices}{choices}; shall I start?', 'Music is already playing.',
                      '{choices} {private_history}?'):
            self.assertFalse(valid(frame),frame)

    async def test_client_cannot_forge_server_mood_feedback_origin(self):
        for n,fields in enumerate(({'_setting_feedback':True}, {'identity':{'_setting_feedback':True}})):
            result,status=await self.f.request('help',identifier='fake-setting-'+str(n),**fields)
            self.assertEqual(status,200,result)
            self.assertNotEqual(result['user_message'].get('origin'),'mood_change')

    async def test_queue_changed_rejects_offer_without_playback(self):
        f=self.f
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend), patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent):
            result,status=await self.request('queue-offer')
        self.assertEqual(status,200,result)
        selected=result['playback_actions'][0]
        async def changed(*args,**kwargs):
            return {'queue':[{'uri':'spotify:track:'+'Q'*22}]}
        with patch('custom_components.djconnect.use_cases.run_music_command',changed):
            rejected,status=await f.request('Play that',identifier='changed-queue-choice',
                choice_action={'result_set_id':selected['result_set_id'],
                               'action_id':selected['action_id'],'operation':'play'})
        self.assertEqual((status,rejected.get('error')),(409,'mood_proposal_queue_changed'),rejected)
        self.assertEqual(f.effects,[])

    async def test_history_clear_during_generation_withdraws_text_and_actions(self):
        f=self.f
        entered,release=asyncio.Event(),asyncio.Event()
        async def held(*args,**kwargs):
            entered.set()
            await release.wait()
            return await self.agent(*args,**kwargs)
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend), patch.object(
                f.pipeline,'_call_conversation_process_transport',held):
            pending=asyncio.create_task(self.request('clear-generating'))
            await asyncio.wait_for(entered.wait(),2)
            await f.history.async_clear('profile:profile-a')
            release.set()
            result,status=await asyncio.wait_for(pending,2)
        self.assertEqual((status,result.get('error')),(409,'conversation_history_changed'),result)
        self.assertEqual((await f.history.async_history('profile:profile-a'))['messages'],[])
        self.assertEqual(f.effects,[])

    async def test_clear_during_debounce_does_not_repopulate_flow(self):
        f=self.f
        previous=f.fixture.manager.current_active('profile-a')
        await f.fixture.manager.async_update_mood(owner_profile_id='profile-a',
            session_id=previous.session_id,selected_mood='party')
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend), patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent):
            self.steering.schedule(f.hass,f.runtime,f.fixture.manager,'profile-a',previous,
                identity=f.identity,headers=f.headers,authorize=lambda:True)
            task=f.fixture.manager._mood_music_tasks['profile-a']
            await f.history.async_clear('profile:profile-a')
            await asyncio.wait_for(task,2)
        self.assertEqual((await f.history.async_history('profile:profile-a'))['messages'],[])
        self.assertEqual(self.calls,[])
        self.assertEqual(f.history._pending_session_requests,{})

    async def test_rapid_mood_changes_coalesce_to_last_accepted_revision(self):
        f=self.f
        first=f.fixture.manager.current_active('profile-a')
        await f.fixture.manager.async_update_mood(owner_profile_id='profile-a',
            session_id=first.session_id,selected_mood='energy')
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend), patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent):
            self.steering.schedule(f.hass,f.runtime,f.fixture.manager,'profile-a',first,
                identity=f.identity,headers=f.headers,authorize=lambda:True)
            superseded=f.fixture.manager._mood_music_tasks['profile-a']
            second=f.fixture.manager.current_active('profile-a')
            await f.fixture.manager.async_update_mood(owner_profile_id='profile-a',
                session_id=first.session_id,selected_mood='party')
            self.steering.schedule(f.hass,f.runtime,f.fixture.manager,'profile-a',second,
                identity=f.identity,headers=f.headers,authorize=lambda:True)
            await asyncio.wait_for(f.fixture.manager._mood_music_tasks['profile-a'],2)
            await asyncio.gather(superseded,return_exceptions=True)
        self.assertTrue(superseded.cancelled())
        self.assertEqual(self.calls,['queue','playlists'])
        messages=(await f.history.async_history('profile:profile-a'))['messages']
        self.assertEqual(len(messages),2)
        self.assertEqual(messages[-1]['session_turn']['effective_style']['mood'],'party')
        self.assertEqual(f.history._pending_session_requests,{})

    async def test_unavailable_candidates_do_not_invent_recommendations(self):
        from custom_components.djconnect.spotify_backend import SpotifyBackendError
        async def unavailable(*args,**kwargs):
            raise SpotifyBackendError('fixture_provider_unavailable')
        with patch('custom_components.djconnect.use_cases.run_music_command',unavailable), patch.object(
                self.f.pipeline,'_call_conversation_process_transport',self.agent):
            result,status=await self.request('no-candidates')
        self.assertEqual(status,200,result)
        self.assertFalse(result.get('playback_actions'))
        self.assertTrue(result.get('is_generated_text'))
        self.assertTrue(result['clarification_required'])
        self.assertEqual(len(self.models),2)
        self.assertEqual([g['id'] for g in result['suggested_genres']],['soul','indie','electronic'])
        self.assertEqual(self.f.effects,[])

    async def test_unrelated_library_is_not_a_mood_match_and_prompts_for_genre(self):
        async def unrelated(hass,runtime,command,value=None,**kwargs):
            if command=='queue':
                return {'queue':[]}
            return {'playlists':[{'uri':'spotify:playlist:'+'P'*22,'name':'Private unrelated workout'}]}
        with patch('custom_components.djconnect.use_cases.run_music_command',unrelated),patch.object(
                self.f.pipeline,'_call_conversation_process_transport',self.agent):
            result,status=await self.request('no-suitable-mood-fit')
        self.assertEqual(status,200,result)
        self.assertTrue(result['clarification_required'])
        self.assertFalse(result.get('playback_actions'))
        self.assertNotIn('Private unrelated',result['text'])
        self.assertIn('soul',result['text'])
        self.assertEqual(self.f.effects,[])

    async def test_retained_provider_prose_keeps_source_and_speech_basis_and_withdraws(self):
        f=self.f
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend),patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent):
            result,status=await self.request('retained-provider-proposal')
        self.assertEqual(status,200,result)
        saved=await f.history.async_saved_exchange('profile:profile-a','retained-provider-proposal')
        message=saved['assistant_message']
        self.assertEqual(message['speech_processing_basis'],'spotify_owner_local_read_v1')
        source=message['session_turn']['provider_display_source']
        self.assertEqual(source['provider'],'Spotify')
        self.assertEqual(source['source_context']['music_account_id'],'source-account')
        self.assertEqual(source['source_context']['provider_entry_id'],'source-entry')
        await f.fixture.manager.async_end(owner_profile_id='profile-a',session_id=self.session.session_id)
        from custom_components.djconnect.session_conversation import query_service
        query=query_service(f.hass,f.history)
        page=await query.async_timeline_page('profile-a',self.session.session_id)
        entry=next(e for e in page['entries'] if e.get('origin_message_id')==message['id'])
        self.assertEqual(entry['speech_processing_basis'],'spotify_owner_local_read_v1')
        self.assertTrue(entry['session_speech']['manual_allowed'])
        f.hass.config_entries.async_entries('djconnect')[0].disabled_by='user'
        opened=await query.async_open_entry('profile-a',self.session.session_id,entry['entry_id'])
        self.assertEqual(opened['entry']['text'],'')
        self.assertEqual(opened['entry']['state'],'source_withdrawn')
        self.assertFalse(await query.async_conversation_source_visible('profile-a',message))
        history,status=await f.handlers.async_handle_ask_dj_history_payload(f.hass,{
            **f.identity},headers=f.headers)
        self.assertEqual(status,200,history)
        self.assertFalse(any('Private library' in m.get('text','') for m in history['messages']))
        # Exact body is still retained under its original source binding, never
        # silently requalified by today's defaults or by reading it for speech.
        self.assertIn('Private library',message['text'])

    async def test_source_withdrawal_reaches_quoted_descendants_history_retry_and_speech(self):
        f=self.f
        with patch('custom_components.djconnect.use_cases.run_music_command',self.backend),patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent):
            result,status=await self.request('parent-provider-prose')
        self.assertEqual(status,200,result)
        from custom_components.djconnect.session_conversation import query_service
        query=query_service(f.hass,f.history)
        page=await query.async_timeline_page('profile-a',self.session.session_id)
        parent=next(e for e in page['entries'] if e.get('origin_message_id')==result['assistant_message']['id'])
        context={'session_id':self.session.session_id,'selected_entry':{
            'session_id':self.session.session_id,'entry_id':parent['entry_id']}}
        quoted,status=await f.request('Quote this contribution',identifier='quoted-provider-prose',context=context)
        self.assertEqual(status,200,quoted)
        self.assertIn('Private library',quoted['text'])
        page=await query.async_timeline_page('profile-a',self.session.session_id)
        child=next(e for e in page['entries'] if e.get('origin_message_id')==quoted['assistant_message']['id'])
        self.assertNotIn('provider_display_source',quoted['assistant_message']['session_turn'])
        f.hass.config_entries.async_entries('djconnect')[0].disabled_by='user'
        opened=await query.async_open_entry('profile-a',self.session.session_id,child['entry_id'])
        self.assertEqual((opened['entry']['text'],opened['entry']['state']),('','source_withdrawn'))
        with self.assertRaises(PermissionError):
            await query.async_open_source_entry('profile-a',self.session.session_id,child['entry_id'])
        history,status=await f.handlers.async_handle_ask_dj_history_payload(f.hass,f.identity,headers=f.headers)
        self.assertEqual(status,200,history)
        self.assertFalse(any('Private library' in m.get('text','') for m in history['messages']))
        retry,status=await f.request('Quote this contribution',identifier='quoted-provider-prose',context=context)
        self.assertNotEqual(status,200,retry)
        from custom_components.djconnect.session_speech import resolve_retained
        with self.assertRaises(PermissionError):
            await resolve_retained(f.hass,f.history,'profile-a',{
                'session_id':self.session.session_id,'entry_id':child['entry_id']})

    async def test_rejected_narration_cannot_publish_an_offer(self):
        original=self.agent
        async def rejected(hass,data,**kwargs):
            result=await original(hass,data,**kwargs)
            if '"frame"' in data['text'].split('\nData:\n',1)[1]:
                return {'response':{'speech':{'plain':{'speech':json.dumps(verdict)}}}}
            return result
        verdicts=[{'language_ok':True,'style_ok':False,'meaning_ok':True},
            *({'language_ok':True,'style_ok':True,'meaning_ok':True,'meaning_reason':reason}
              for reason in (None,[],False,'unknown','playback_promise'))]
        for index,verdict in enumerate(verdicts):
            with self.subTest(verdict=verdict), patch('custom_components.djconnect.use_cases.run_music_command',self.backend), patch.object(
                    self.f.pipeline,'_call_conversation_process_transport',rejected):
                result,status=await self.request('bad-narration-'+str(index))
            self.assertEqual((status,result.get('error')),(502,'mood_narration_unqualified'),result)
            self.assertEqual((await self.f.history.async_history('profile:profile-a'))['messages'],[])

    async def test_freeworded_genre_reply_searches_actual_tracks_without_playing(self):
        f=self.f
        async def no_matching_library(*args,**kwargs):
            return {'queue':[],'playlists':[]}
        queries=[]
        async def search(hass,runtime,query,**kwargs):
            queries.append(query)
            return {'success':True,'tracks':[{'uri':'spotify:track:'+'S'*22,
                'name':'Private real catalog choice','artist':'Catalog performer'}]}
        with patch('custom_components.djconnect.use_cases.run_music_command',no_matching_library),patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent),patch.object(f.core,'_spotify_track_search',search):
            first,status=await self.request('genre-question')
            self.assertEqual(status,200,first)
            self.assertTrue(first['clarification_required'])
            reply,status=await f.request('doe maar sowl voor deze sfeer',identifier='genre-reply',
                context={'session_id':self.session.session_id})
        self.assertEqual(status,200,reply)
        self.assertEqual(queries,['genre:soul'])
        self.assertIn('Private real catalog choice',reply['text'])
        self.assertEqual(reply['playback_actions'][0]['uri'],'spotify:track:'+'S'*22)
        self.assertEqual(reply['playback_actions'][0]['fit_basis'],'catalog_genre_query')
        self.assertEqual(reply['conversation']['metrics']['agent_calls'],3)
        self.assertNotIn('Private real catalog choice',json.dumps(self.models))
        self.assertEqual(f.effects,[])

    async def test_genre_clarification_then_explicit_play_dispatches_only_exact_offered_track_once(self):
        """Actual paired choice/grant/Spotify serialization; provider I/O is fake."""
        from custom_components.djconnect import http
        from custom_components.djconnect.spotify_backend import SpotifyBackend
        from custom_components.djconnect.domain.backend import BackendProvider
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.domain.profile import ProfilePreferences
        f=self.f
        storage=f.handlers.profile_storage(f.hass)
        await storage.async_upsert_music_backend('spotify_direct',BackendProvider.SPOTIFY_DIRECT,
            display_name='Synthetic playback provider')
        await storage.async_upsert_music_account('playback-account','spotify_direct',
            kind=MusicAccountKind.PERSONAL,display_name='Synthetic playback account',
            linked_profile_ids=frozenset({'profile-a'}))
        await storage.async_update_profile('profile-a',preferences=ProfilePreferences(
            default_backend_id='spotify_direct',default_music_account_id='playback-account'))
        source=f.hass.config_entries.async_entries('djconnect')[0]
        source.data.update(music_account_id='playback-account')
        # The older retained-source fixture deliberately uses a noncanonical
        # backend ID. This positive playback case needs the actual provider ID.
        await f.fixture.manager.async_end(owner_profile_id='profile-a',session_id=self.session.session_id)
        self.session=await f.fixture.manager.async_start(owner_profile_id='profile-a',
            locale='en',selected_mood='groove',music_backend='spotify_direct',
            history_source_context={'backend_id':'spotify_direct','music_account_id':'playback-account',
                                    'provider_entry_id':'source-entry'})
        f.runtime.config['spotify_refresh_token']='synthetic-never-sent-fixture-grant'
        def update(**values):
            for key,value in values.items():
                setattr(f.runtime,key,value)
        f.runtime.update=update
        uri='spotify:track:'+'S'*22
        async def empty_library(hass,runtime,command,value=None,**kwargs):
            self.assertIn(command,{'queue','playlists'})
            return {'queue':[],'playlists':[]}
        async def search(hass,runtime,query,**kwargs):
            self.assertEqual(query,'genre:soul')
            return {'success':True,'tracks':[{'uri':uri,'name':'Private exact catalog choice',
                'artist':'Catalog performer'}]}
        backend=object.__new__(SpotifyBackend)
        backend.hass,backend.runtime=f.hass,f.runtime
        async def token(**kwargs):
            return 'SYNTHETIC_FIXTURE_TOKEN'
        backend._access_token=token
        sent=[]
        class Response:
            status=204
            async def __aenter__(self):
                return self
            async def __aexit__(self,*args):
                return False
        class Transport:
            def request(self,method,url,**kwargs):
                sent.append((method,url,kwargs.get('json')))
                return Response()
        backend.session=Transport()
        async def playback(hass,runtime,command,value=None,**kwargs):
            if command=='status':
                return {'playback':{'uri':uri,'is_playing':True}}
            self.assertEqual((command,value),('play',uri))
            async def dispatch():
                await backend.play(value)
            return await f.external_effect_probe(command,value,dispatch)
        with patch('custom_components.djconnect.use_cases.run_music_command',empty_library),patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent),patch.object(
                f.core,'_spotify_track_search',search),patch.object(http,'run_music_command',playback):
            question,status=await self.request('complete-genre-question')
            self.assertEqual(status,200,question)
            self.assertTrue(question['clarification_required'])
            offered,status=await f.request('doe maar sowl',identifier='complete-genre-reply',
                context={'session_id':self.session.session_id})
            self.assertEqual(status,200,offered)
            self.assertEqual(sent,[])
            selected=offered['playback_actions'][0]
            self.assertEqual(selected['uri'],uri)
            choice={key:selected[key] for key in ('result_set_id','action_id')}
            choice['operation']='play'
            arguments={'identifier':'complete-explicit-play',
                'context':{'session_id':self.session.session_id},'choice_action':choice}
            accepted,status=await f.request('Play that',**arguments)
            self.assertEqual(status,200,accepted)
            self.assertTrue(accepted['success'],accepted)
            self.assertEqual(accepted['selected_action_id'],selected['action_id'])
            self.assertIn('text',accepted,accepted)
            self.assertIn('Private exact catalog choice',accepted['text'])
            duplicate,status=await f.request('Play that',**arguments)
            self.assertEqual(status,200,duplicate)
            self.assertTrue(duplicate['deduplicated'])
            self.assertEqual(duplicate['text'],accepted['text'])
            saved=await f.history.async_saved_exchange('profile:profile-a','complete-explicit-play')
            self.assertIsNotNone(saved)
            history=await f.history.async_history('profile:profile-a')
            self.assertEqual(history['messages'][-1]['text'],accepted['text'])
        self.assertEqual(len(sent),1)
        self.assertEqual(sent[0][0],'PUT')
        self.assertIn('/me/player/play',sent[0][1])
        self.assertEqual(sent[0][2],{'uris':[uri]})
        self.assertNotIn('Private exact catalog choice',json.dumps(self.models))

    async def test_changed_mood_withdraws_pending_genre_question_before_lookup(self):
        f=self.f
        async def empty(*args,**kwargs):return {'queue':[],'playlists':[]}
        with patch('custom_components.djconnect.use_cases.run_music_command',empty),patch.object(
                f.pipeline,'_call_conversation_process_transport',self.agent),patch.object(
                f.core,'_spotify_track_search',side_effect=AssertionError('stale lookup')):
            result,status=await self.request('old-genre-question')
            self.assertEqual(status,200,result)
            await f.fixture.manager.async_update_mood(owner_profile_id='profile-a',
                session_id=self.session.session_id,selected_mood='party')
            result,status=await f.request('soul',identifier='old-genre-reply',
                context={'session_id':self.session.session_id})
        self.assertEqual((status,result.get('error')),(409,'mood_proposal_changed'),result)
        self.assertEqual(f.effects,[])

    async def test_ambiguous_yes_reasks_admitted_direction_without_effect_or_deadline_renewal(self):
        f=self.f
        async def empty(*args,**kwargs):return {'queue':[],'playlists':[]}
        original=self.agent
        async def ambiguous(hass,data,**kwargs):
            if '"allowed"' in data['text'].split('\nData:\n',1)[1]:
                return {'response':{'speech':{'plain':{'speech':'{"decision":"ambiguous","genre":null}'}}}}
            return await original(hass,data,**kwargs)
        with patch('custom_components.djconnect.use_cases.run_music_command',empty),patch.object(
                f.pipeline,'_call_conversation_process_transport',ambiguous),patch.object(
                f.core,'_spotify_track_search',side_effect=AssertionError('ambiguous reply is no lookup')):
            first,status=await self.request('ambiguous-direction')
            self.assertEqual(status,200,first)
            frame=f.history.dialogue.owners['profile:profile-a']['default']
            deadline=frame.pending['deadline']
            result,status=await f.request('yes',identifier='ambiguous-genre-yes',
                context={'session_id':self.session.session_id})
        self.assertEqual(status,200,result)
        self.assertEqual(result['text'],first['text'])
        self.assertTrue(result['clarification_required'])
        self.assertEqual(frame.pending['deadline'],deadline)
        self.assertEqual(result['conversation']['metrics']['agent_calls'],1)
        self.assertEqual(f.effects,[])

    async def test_declines_in_five_languages_consume_clarification_without_lookup_or_effect(self):
        f=self.f
        async def empty(*args,**kwargs):return {'queue':[],'playlists':[]}
        original=self.agent
        async def decline(hass,data,**kwargs):
            if '"allowed"' in data['text'].split('\nData:\n',1)[1]:
                return {'response':{'speech':{'plain':{'speech':json.dumps({
                    'decision':'rejected','genre':None})}}}}
            return await original(hass,data,**kwargs)
        with patch('custom_components.djconnect.use_cases.run_music_command',empty),patch.object(
                f.pipeline,'_call_conversation_process_transport',decline),patch.object(
                f.core,'_spotify_track_search',side_effect=AssertionError('decline must not lookup')):
            for locale,text in [('en','No thanks, leave it'),('nl','Nee, laat maar'),
                                ('de','Nein, lass mal'),('fr','Non, laisse tomber'),('es','No, déjalo')]:
                with self.subTest(locale=locale):
                    first,status=await self.request('clarify-'+locale,language=locale)
                    self.assertEqual(status,200,first)
                    result,status=await f.request(text,identifier='decline-'+locale,language=locale,
                        context={'session_id':self.session.session_id})
                    self.assertEqual(status,200,result)
                    self.assertEqual(result['text'],self.steering.COPY[locale]['declined'])
                    self.assertEqual(result['intent']['intent'],'music_direction_declined')
                    self.assertIsNone(f.history.dialogue.owners['profile:profile-a']['default'].pending)
                    self.assertEqual(result['conversation']['metrics']['agent_calls'],1)
                    self.assertEqual(result['playback_actions'],[])
        self.assertEqual(f.effects,[])

    async def test_topic_change_returns_to_common_route_and_consumes_clarification(self):
        f=self.f
        async def empty(*args,**kwargs):return {'queue':[],'playlists':[]}
        original=self.agent
        async def unrelated(hass,data,**kwargs):
            if '\nData:\n' in data['text'] and '"allowed"' in data['text'].split('\nData:\n',1)[1]:
                return {'response':{'speech':{'plain':{'speech':json.dumps({
                    'decision':'unrelated','genre':None})}}}}
            return await original(hass,data,**kwargs)
        routed=[]
        async def common(hass,runtime,text,*args,**kwargs):
            routed.append(text)
            return {'success':True,'text':'An ostinato is a repeated musical pattern.',
                'action':'none','playback_actions':[],'intent':{'intent':'ask_music_info'}}
        with patch('custom_components.djconnect.use_cases.run_music_command',empty),patch.object(
                f.pipeline,'_call_conversation_process_transport',unrelated):
            first,status=await self.request('before-new-topic')
            self.assertEqual(status,200,first)
            with patch.object(f.core,'_informational_assist_response',common):
                result,status=await f.request('What does ostinato mean?',identifier='new-topic',
                    context={'session_id':self.session.session_id})
        self.assertEqual(status,200,result)
        self.assertEqual(routed,['What does ostinato mean?'])
        self.assertNotEqual(result['text'],first['text'])
        self.assertIsNone(f.history.dialogue.owners['profile:profile-a']['default'].pending)
        self.assertEqual(f.effects,[])

    async def test_topic_change_preserves_its_new_confirmation_pending(self):
        f=self.f
        async def empty(*args,**kwargs):return {'queue':[],'playlists':[]}
        original=self.agent
        async def unrelated(hass,data,**kwargs):
            if '\nData:\n' in data['text'] and '"allowed"' in data['text'].split('\nData:\n',1)[1]:
                return {'response':{'speech':{'plain':{'speech':json.dumps({
                    'decision':'unrelated','genre':None})}}}}
            return await original(hass,data,**kwargs)
        replacement={'type':'playback_confirmation','deadline':f.history.dialogue.clock()+50,
                     'question':'Keep the current playlist?'}
        async def common(*args,**kwargs):
            from custom_components.djconnect.ask_dj.dialogue import current_turn
            current_turn.get().pending=replacement
            return {'success':True,'text':replacement['question'],'action':'none','playback_actions':[],
                    'intent':{'intent':'clarification_needed'}}
        with patch('custom_components.djconnect.use_cases.run_music_command',empty),patch.object(
                f.pipeline,'_call_conversation_process_transport',unrelated):
            first,status=await self.request('before-confirmation')
            self.assertEqual(status,200,first)
            with patch.object(f.core,'_informational_assist_response',common):
                result,status=await f.request('What should we listen to later?',identifier='replacement-pending',
                    context={'session_id':self.session.session_id})
        self.assertEqual(status,200,result)
        frame=f.history.dialogue.owners['profile:profile-a']['default']
        self.assertEqual(frame.pending,replacement)
        self.assertEqual(f.effects,[])

    async def test_pending_expiry_identity_and_mood_are_rechecked_after_interpretation(self):
        from copy import deepcopy
        import time
        f=self.f
        clock=[time.monotonic()]
        f.history.dialogue.clock=lambda:clock[0]
        async def empty(*args,**kwargs):return {'queue':[],'playlists':[]}
        original=self.agent
        mutation=''
        decision=''
        async def changed(hass,data,**kwargs):
            if '"allowed"' in data['text'].split('\nData:\n',1)[1]:
                frame=f.history.dialogue.owners['profile:profile-a']['default']
                if mutation=='expiry':
                    clock[0]=frame.pending['deadline']+1
                elif mutation=='identity':
                    frame.pending=deepcopy(frame.pending)
                else:
                    active=f.fixture.manager.current_active('profile-a')
                    await f.fixture.manager.async_update_mood(owner_profile_id='profile-a',
                        session_id=active.session_id,selected_mood='party' if active.selected_mood!='party' else 'chill')
                reply={'decision':decision,'genre':'soul' if decision=='selected' else None}
                return {'response':{'speech':{'plain':{'speech':json.dumps(reply)}}}}
            return await original(hass,data,**kwargs)
        with patch('custom_components.djconnect.use_cases.run_music_command',empty),patch.object(
                f.pipeline,'_call_conversation_process_transport',changed),patch.object(
                f.core,'_spotify_track_search',side_effect=AssertionError('withdrawn choice must not lookup')):
            for mutation,error in [('expiry','choice_expired'),('identity','music_direction_changed'),
                                   ('mood','mood_proposal_changed')]:
                for decision in ('selected','ambiguous','rejected'):
                    with self.subTest(mutation=mutation,decision=decision):
                        identifier=mutation+'-'+decision
                        first,status=await self.request('before-'+identifier)
                        self.assertEqual(status,200,first)
                        before=(await f.history.async_history('profile:profile-a'))['messages']
                        result,status=await f.request('soul please',identifier='after-'+identifier,
                            context={'session_id':self.session.session_id})
                        self.assertEqual((status,result.get('error')),(409,error),result)
                        self.assertEqual((await f.history.async_history('profile:profile-a'))['messages'],before)
        self.assertEqual(f.effects,[])

    async def test_genre_lookup_await_rechecks_pending_mood_history_and_session_before_proposal(self):
        """Real owner races after a provider await; no real provider/model I/O."""
        from copy import deepcopy
        import time
        f=self.f
        clock=[time.monotonic()]
        f.history.dialogue.clock=lambda:clock[0]
        async def empty(*args,**kwargs):
            return {'queue':[],'playlists':[]}
        queries=[]
        for mutation,error in [('expiry','choice_expired'),('identity','music_direction_changed'),
                ('mood','mood_proposal_changed'),('clear','conversation_history_changed'),
                ('end','session_context_changed')]:
            with self.subTest(mutation=mutation):
                entered,release=asyncio.Event(),asyncio.Event()
                async def delayed_search(hass,runtime,query,**kwargs):
                    queries.append(query)
                    entered.set()
                    await release.wait()
                    return {'success':True,'tracks':[{'uri':'spotify:track:'+'S'*22,
                        'name':'Stale provider result','artist':'Catalog performer'}]}
                models_before=len(self.models)
                with patch('custom_components.djconnect.use_cases.run_music_command',empty),patch.object(
                        f.pipeline,'_call_conversation_process_transport',self.agent),patch.object(
                        f.core,'_spotify_track_search',delayed_search):
                    first,status=await self.request('before-search-'+mutation)
                    self.assertEqual(status,200,first)
                    frame=f.history.dialogue.owners['profile:profile-a']['default']
                    before=(await f.history.async_history('profile:profile-a'))['messages']
                    pending=asyncio.create_task(f.request('soul please',identifier='during-search-'+mutation,
                        context={'session_id':self.session.session_id}))
                    await asyncio.wait_for(entered.wait(),2)
                    if mutation=='expiry':
                        clock[0]=frame.pending['deadline']+1
                    elif mutation=='identity':
                        frame.pending=deepcopy(frame.pending)
                    elif mutation=='mood':
                        await f.fixture.manager.async_update_mood(owner_profile_id='profile-a',
                            session_id=self.session.session_id,selected_mood='party')
                    elif mutation=='clear':
                        await f.history.async_clear('profile:profile-a')
                    else:
                        await f.fixture.manager.async_end(owner_profile_id='profile-a',session_id=self.session.session_id)
                    release.set()
                    result,status=await asyncio.wait_for(pending,2)
                self.assertEqual((status,result.get('error')),(409,error),result)
                self.assertFalse(result.get('playback_actions'))
                self.assertNotIn('Stale provider result',json.dumps(result))
                self.assertEqual(len(self.models)-models_before,3)
                self.assertEqual((await f.history.async_history('profile:profile-a'))['messages'],
                    [] if mutation=='clear' else before)
                self.assertEqual(f.effects,[])
        self.assertEqual(queries,['genre:soul']*5)

    def test_daypart_uses_home_assistant_timezone_including_overnight(self):
        from types import SimpleNamespace
        for hour,expected in ((0,'night'),(4,'night'),(5,'morning'),(12,'afternoon'),(18,'evening'),(23,'night')):
            with patch.object(self.steering,'datetime') as clock:
                clock.now.return_value=SimpleNamespace(hour=hour)
                self.assertEqual(self.steering.time_context(self.f.hass),expected)


class MoodSettingsTriggerTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        settings_fixture.ProfileSettingsOwnerTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        settings_fixture.ProfileSettingsOwnerTests.tearDownClass()

    async def asyncSetUp(self):
        self.f=settings_fixture.ProfileSettingsOwnerTests()
        await self.f.asyncSetUp()

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def test_only_confirmed_active_mood_changes_schedule_once_and_reads_do_not(self):
        from custom_components.djconnect import mood_music_steering as m
        f=self.f
        scheduled=[]
        def schedule(hass,runtime,manager,profile_id,previous,**kwargs):
            active=manager.current_active(profile_id)
            if previous and active and active.mood_revision!=previous.mood_revision:
                scheduled.append((active.session_id,active.mood_revision))
                return {'version':1,'state':'pending','request_id':'test-feedback'}
            return None
        with patch.object(m,'schedule',schedule):
            before,_=await f.read()
            accepted,status=await f.choose(before,{'mood':'energy'})
            self.assertEqual(status,200,accepted)
            self.assertEqual(scheduled,[])  # Profile-only is not a Session event.
            await f.fixture.manager.async_start(owner_profile_id='profile-a')
            before,_=await f.read()
            accepted,status=await f.choose(before,{'mood':'party'},counter=2)
            self.assertEqual(status,200,accepted)
            self.assertEqual(len(scheduled),1)
            self.assertIn('mood_music_feedback',accepted)
            replay,status=await f.choose(before,{'mood':'party'},counter=2)
            self.assertEqual(status,200,replay)
            self.assertTrue(replay['replayed'])
            await f.read()
            self.assertEqual(len(scheduled),1)
