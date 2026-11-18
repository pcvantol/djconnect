"""Draft qualification guards. These do not establish executable suggestion UX."""
import importlib
import unittest
from unittest.mock import patch

from tests.test_http_voice_helpers import install_http_stubs


class ExampleCatalogueDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_http_stubs()
        cls.core = importlib.import_module('custom_components.djconnect.ask_dj')
        cls.catalogue = importlib.import_module('custom_components.djconnect.ask_dj.example_catalogue')

    def test_native_play_requests_route_normally_with_only_en_nl_content_qualification(self):
        rows = {e['id']: e for e in self.catalogue.catalogue()['entries']}
        for language in ('en', 'nl', 'de', 'fr', 'es'):
            for id in ('play.artist', 'play.cooking', 'play.quiet'):
                question = self.catalogue.prompt(rows[id], language, {'artist': 'Volbeat'})
                intent = self.core.classify_ask_dj(question)
                self.assertEqual(intent.intent, 'play_music', (language, question))
                self.assertEqual(intent.category, 'hybrid')
                self.assertTrue(self.core._execution_request(question))
                self.assertEqual(rows[id]['qualification'][language]['state'] == 'qualified_owner_route',
                                 language in {'en', 'nl'})

    def test_native_subject_parser_is_not_a_catalogue_artist_alias(self):
        from custom_components.djconnect.music_intent import parse_spoken_music_request
        from custom_components.djconnect.processor import _request_bound_music_intent
        for prefix in ('Speel', 'Play', 'Spiele', 'Joue', 'Reproduce'):
            for artist in ('Radiohead','Volbet','La Roux','The National'):
                original = prefix+' '+artist
                parsed = parse_spoken_music_request(original)
                self.assertEqual((parsed['type'],parsed['query'],parsed['artist']),('artist',artist,artist))
                bound = _request_bound_music_intent(original,{'type':'artist','artist':'Guns N Roses','query':'Patience'})
                self.assertEqual(bound['artist'],artist)
                self.assertEqual(bound['query'],artist)

    def test_activity_requests_do_not_shortcut_to_an_artist_search(self):
        from custom_components.djconnect.processor import _deterministic_playback_intent
        from custom_components.djconnect.music_intent import parse_spoken_music_request
        examples = ('Play something for cooking', 'Speel iets voor tijdens het koken',
            'Spiele etwas zum Kochen', 'Joue quelque chose pour cuisiner',
            'Reproduce algo para cocinar', 'I want to hear something for dinner',
            'Speel muziek om bij te werken', 'Play some music for reading')
        for question in examples:
            self.assertEqual(_deterministic_playback_intent(question), {}, question)
            self.assertTrue(parse_spoken_music_request(question)['query'])
        for artist in ('DJ Paul Elstak', 'The National', 'Radiohead', 'Something for Kate'):
            question = 'Play "'+artist+'"' if artist.startswith('Something') else 'Play '+artist
            if artist != 'Radiohead':
                self.assertTrue(_deterministic_playback_intent(question), question)

    def test_explicit_local_album_followups_are_grants_but_plain_yes_and_negation_are_not(self):
        from custom_components.djconnect.ask_dj.dialogue import affirmed_play_reference, explicit_play
        examples = ('Yes, I want to play that album.', 'I would like to play this playlist',
            'Ja, dieses Album möchte ich hören.', 'Dieses Lied möchte ich gern abspielen',
            'Ja, die wil ik afspelen.', 'Oui, je veux écouter cet album.',
            'Sí, quiero escuchar ese álbum.')
        for question in examples:
            self.assertTrue(affirmed_play_reference(question), question)
            self.assertTrue(explicit_play(question), question)
            self.assertTrue(self.core._execution_request(question), question)
        for question in ('yes', 'ja', 'oui', 'sí', 'Do not play that album',
                         'I want to play that album later', 'If I want to play that album'):
            self.assertFalse(affirmed_play_reference(question), question)
            self.assertFalse(explicit_play(question), question)

    def test_native_album_and_playlist_keep_kind_and_original_subject(self):
        from custom_components.djconnect.music_intent import parse_spoken_music_request
        for question in ('Spiele das Album Nevermind von Nirvana', 'Joue l’album Nevermind de Nirvana',
                         'Reproduce el álbum Nevermind de Nirvana'):
            parsed = parse_spoken_music_request(question)
            self.assertEqual((parsed['type'],parsed['title'],parsed['artist']),('album','Nevermind','Nirvana'))
        for question, name in (('Starte eine ruhige Playlist','ruhige'),
                               ('Mets une playlist calme','calme'),('Pon una playlist tranquila','tranquila')):
            parsed = parse_spoken_music_request(question)
            self.assertEqual((parsed['type'],parsed['playlist']),('playlist',name))

    def test_music_question_negation_hypothesis_and_quote_never_get_play_authority(self):
        from custom_components.djconnect.ask_dj.dialogue import request_effect_grants
        for text in ('Welche Alben hat Volbeat?', 'Quelles chansons de Volbeat connais-tu ?',
                     '¿Qué discos de Volbeat tienes?', 'Spiele Volbeat nicht', 'Ne joue pas Volbeat',
                     'No reproduce Volbeat', 'Mets Volbeat pas', 'Pon Volbeat no',
                     'Starte die Playlist nicht', 'Starte nicht die Playlist', 'Mets pas Volbeat',
                     'If I say play Volbeat what happens?',
                     '"Joue Volbeat"', 'Erkläre Spiele Volbeat', 'Explica reproduce Volbeat'):
            intent = self.core.classify_ask_dj(text)
            self.assertEqual(request_effect_grants(text,intent),(),text)

    def test_quoted_music_names_keep_negative_words_as_literal_identity(self):
        from custom_components.djconnect.ask_dj.dialogue import request_effect_grants
        from custom_components.djconnect.music_intent import negated_music_command
        for text in ('Play "Not Afraid"', 'Speel "Geen Kind Meer"', 'Spiele „Nicht von dieser Welt“',
                     'Joue "Pas de problème"','Reproduce "No Doubt"'):
            self.assertFalse(negated_music_command(text),text)
            self.assertTrue(request_effect_grants(text,self.core.classify_ask_dj(text)),text)

    def test_all_catalogue_questions_use_their_existing_semantic_owner_not_chip_dispatch(self):
        from scripts.verification.askdj_example_catalogue_golden import cases
        for row in cases():
            self.assertEqual(self.core.classify_ask_dj(row['question']).intent,row['expected']['intent'],row['id'])

    def test_read_presentation_language_is_from_current_turn_and_every_key_has_five_locales(self):
        from types import SimpleNamespace
        from custom_components.djconnect.ask_dj import read_copy
        from custom_components.djconnect.ask_dj.dialogue import current_turn
        for key,values in read_copy.ROWS.items():
            self.assertEqual(len(values),5,key)
            for locale,expected in zip(read_copy.LANGUAGES,values,strict=True):
                token=current_turn.set(SimpleNamespace(style={'language':locale}))
                try:
                    values={'artist':'Volbeat','label':'albums','count':3,'period':'X','kind':'tracks','title':'T','album':'A',
                            'artist_part':' — Volbeat','album_part':' · A'}
                    self.assertEqual(read_copy.text(key,**values),expected.format(**values))
                finally:
                    current_turn.reset(token)

    def test_draft_or_unknown_locale_routes_never_become_qualified_chips_or_help(self):
        context = {'catalogue': self.catalogue.capability(), 'paired': True, 'online': True,
            'backend_available': True, 'supports_search': True, 'supports_playlists': True,
            'supports_queue': True, 'supports_outputs': True, 'supports_recently_played': True,
            'agent_available': True, 'spotify': True, 'current_track': True,
            'current_album': True, 'active_session': True, 'forecast_ready': True,
            'contracts': {'session_forecast': 1}, 'slots': {'artist': 'Volbeat'},
            'entry_configuration': dict.fromkeys((e['id'] for e in self.catalogue.catalogue()['entries']), True)}
        draft = self.catalogue.catalogue()
        draft['status'] = 'draft_not_consumer_qualified'
        with patch.object(self.catalogue, '_CATALOGUE', draft):
            for language in ('en', 'nl', 'de', 'fr', 'es'):
                self.assertEqual(self.catalogue.eligible(context, 'ask_dj', language), [])
                self.assertEqual(self.catalogue.help_sections(language, context), [])
                self.assertEqual(self.catalogue.select(context, 'active_session', language,
                    epoch='one-opening')['suggestions'], [])

    def test_eligibility_is_per_locale_and_uses_same_gate_for_help_and_chips(self):
        draft = self.catalogue.catalogue()
        draft['status']='qualified_v1'
        row = draft['entries'][0]
        row['publication'] = 'qualified_v1'
        row['qualification']['nl'] = {'state': 'qualified_owner_route', 'route': row['route']}
        context = {'catalogue': self.catalogue.capability(), 'paired': True, 'online': True,
            'backend_available': True, 'supports_search': True, 'slots': {'artist': 'Volbeat'}}
        context['catalogue']['qualified']=True
        context['entry_configuration'] = dict.fromkeys((e['id'] for e in draft['entries']), True)
        with patch.object(self.catalogue, '_CATALOGUE', draft):
            self.assertEqual(len(self.catalogue.eligible(context, 'ask_dj', 'nl')), 1)
            self.assertEqual(len(self.catalogue.help_sections('nl', context)), 1)
            self.assertEqual(self.catalogue.eligible(context, 'ask_dj', 'de'), [])
            self.assertEqual(self.catalogue.help_sections('de', context), [])
            context['online'] = False
            self.assertEqual(self.catalogue.eligible(context, 'ask_dj', 'nl'), [])
            self.assertEqual(self.catalogue.help_sections('nl', context), [])

    def test_unknown_version_and_missing_or_unsafe_slot_fail_closed(self):
        draft = self.catalogue.catalogue()
        draft['status']='qualified_v1'
        row = draft['entries'][0]
        row['publication'] = 'qualified_v1'
        row['qualification']['nl'] = {'state':'qualified_owner_route', 'route':row['route']}
        context = {'catalogue':self.catalogue.capability(), 'paired':True, 'online':True,
            'backend_available':True, 'supports_search':True}
        context['catalogue']['qualified']=True
        context['entry_configuration'] = dict.fromkeys((e['id'] for e in draft['entries']), True)
        with patch.object(self.catalogue, '_CATALOGUE', draft):
            self.assertEqual(self.catalogue.eligible(context, 'ask_dj', 'nl'), [])
            context['slots'] = {'artist':'{private value}'}
            self.assertEqual(self.catalogue.eligible(context, 'ask_dj', 'nl'), [])
            context['slots'] = {'artist':'Volbeat'}
            self.assertEqual(len(self.catalogue.eligible(context, 'ask_dj', 'nl')), 1)
            context['catalogue']['schema_version'] = 999
            self.assertEqual(self.catalogue.eligible(context, 'ask_dj', 'nl'), [])

    def test_unknown_locale_malformed_context_and_unqualified_pin_fail_closed(self):
        draft = self.catalogue.catalogue()
        draft['status']='qualified_v1'
        row=draft['entries'][0]
        row['publication']='qualified_v1'
        for locale in ('en','nl'):
            row['qualification'][locale]={'state':'qualified_owner_route','route':row['route']}
        context={'catalogue':self.catalogue.capability(),'paired':True,'online':True,
                 'backend_available':True,'supports_search':True,'slots':{'artist':'Volbeat'}}
        context['catalogue']['qualified']=True
        context['entry_configuration'] = dict.fromkeys((e['id'] for e in draft['entries']), True)
        with patch.object(self.catalogue,'_CATALOGUE',draft):
            self.assertTrue(self.catalogue.eligible(context,'ask_dj','nl-BE'))
            for language in ('it','ja',None,''):
                self.assertEqual(self.catalogue.eligible(context,'ask_dj',language),[])
                self.assertEqual(self.catalogue.help_sections(language,context),[])
                self.assertNotIn('Play Volbeat',self.catalogue.help_text(language,context))
            for key,value in (('contracts',['wrong']),('slots','wrong')):
                changed={**context,key:value}
                self.assertEqual(self.catalogue.eligible(changed,'ask_dj','nl'),[])
            for key,value in (('schema_version',True),('revision',True),('qualified',False),('qualified',None)):
                changed={**context,'catalogue':{**context['catalogue'],key:value}}
                self.assertEqual(self.catalogue.eligible(changed,'ask_dj','nl'),[])
        # A consumer cannot turn a draft producer into a qualified source.
        draft['status'] = 'draft_not_consumer_qualified'
        with patch.object(self.catalogue, '_CATALOGUE', draft):
            self.assertEqual(self.catalogue.eligible(context,'ask_dj','nl'),[])

    def test_runtime_projection_exactly_matches_single_canonical_json_without_runtime_file_read(self):
        from pathlib import Path
        from tools.generate_askdj_example_catalogue import SOURCE,TARGET,projection
        import hashlib
        import json
        self.assertEqual(TARGET.read_text(),projection(SOURCE.read_bytes()))
        self.assertEqual(self.catalogue.catalogue(),json.loads(SOURCE.read_bytes()))
        self.assertEqual(self.catalogue.capability()['sha256'],hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        with patch.object(Path,'read_bytes',side_effect=AssertionError('runtime must not read catalogue file')):
            importlib.reload(self.catalogue)
            self.assertEqual(len(self.catalogue.catalogue()['entries']),14)

    def test_three_stable_diverse_suggestions_and_compact_help_share_every_eligibility_gate(self):
        draft=self.catalogue.catalogue()
        draft['status']='qualified_v1'
        for row in draft['entries']:
            row['publication']='qualified_v1'
            for locale in draft['language_families']:
                row['qualification'][locale]={'state':'qualified_owner_route','route':row['route']}
        context={'catalogue':self.catalogue.capability(),'contracts':{'session_forecast':1},
            'slots':{'artist':'Volbeat'}}
        context.update({key:True for row in draft['entries'] for key in row['requires']})
        context['catalogue']['qualified']=True
        context['entry_configuration'] = dict.fromkeys((e['id'] for e in draft['entries']), True)
        with patch.object(self.catalogue,'_CATALOGUE',draft):
            for locale in draft['language_families']:
                for surface in ('ask_dj','active_session'):
                    selected=self.catalogue.select(context,surface,locale,epoch='surface-open-1')
                    self.assertEqual(selected,self.catalogue.select(context,surface,locale,epoch='surface-open-1'))
                    self.assertEqual(len(selected['suggestions']),3)
                    self.assertEqual(len({s['intent'] for s in selected['suggestions']}),3)
                    self.assertGreaterEqual(len({s['group'] for s in selected['suggestions']}),2)
                    help_sections=self.catalogue.help_sections(locale,context)
                    self.assertEqual(len(help_sections),3)
                    self.assertEqual(sum(len(rows) for _,rows in help_sections),6)
                    self.assertTrue(all(len(rows)<=2 for _,rows in help_sections))
                    self.assertEqual(help_sections[0][0],draft['groups'][-1]['labels'][locale])
                offline={**context,'online':False}
                self.assertEqual(self.catalogue.help_sections(locale,offline),[])
                self.assertEqual(self.catalogue.select(offline,'ask_dj',locale,epoch='open')['suggestions'],[])


class CatalogueSpeechActTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_ask_dj_contextual_dialogue import SharedDialogueTest
        cls.SharedDialogueTest=SharedDialogueTest
        SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f=self.SharedDialogueTest()
        await self.f.asyncSetUp()

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def test_negated_native_requests_do_no_model_provider_or_effect_work_even_with_positive_agent(self):
        cases=(('de','Spiele bitte nicht Volbeat'),('de','Bitte spiele auf keinen Fall Volbeat'),
               ('fr','Joue surtout pas Volbeat'),('es','Reproduce por favor no Volbeat'),
               ('de','Spiele das Album Nevermind von Nirvana nicht ab'),
               ('en','Please do not play Volbeat'),('nl','Speel Volbeat alsjeblieft niet'))
        calls=[]
        async def agent(*args,**kwargs):
            calls.append('model')
            return {'response':{'speech':{'plain':{'speech':'{"intent":"play_music","type":"artist","query":"Volbeat"}'}}}}
        async def provider(*args,**kwargs):
            calls.append('provider')
            raise AssertionError('negation must not reach provider')
        f=self.f
        from custom_components.djconnect.ask_dj.dialogue import request_effect_grants
        with patch.object(f.pipeline,'_call_conversation_process_transport',agent), patch.object(f.core,'run_music_command',provider):
            for index,(locale,question) in enumerate(cases):
                self.assertEqual(request_effect_grants(question,f.core.classify_ask_dj(question)),(),question)
                answer,code=await f.request(question,language=locale,identifier='native-negation-'+str(index))
                self.assertEqual(code,200,answer)
                self.assertEqual(answer['conversation']['metrics']['agent_calls'],0)
                self.assertEqual(answer['action'],'none')
                self.assertFalse(answer.get('playback_actions'))
        self.assertEqual(calls,[])
        self.assertEqual(f.effects,[])

    async def test_paused_current_recording_uses_truthful_state_in_all_five_locales_without_effect(self):
        from custom_components.djconnect.ask_dj import read_copy
        from scripts.verification.askdj_example_catalogue_golden import cases
        calls=[]
        async def provider(hass,runtime,command,*args,**kwargs):
            calls.append(command)
            self.assertEqual(command,'status')
            return {'success':True,'playback':{'uri':'spotify:track:'+'N'*22,'title':'Recording','track_name':'Recording',
                'artist':'Performer','album_name':'Album','has_playback':True,'state':'paused','is_playing':False}}
        f=self.f
        with patch.object(f.core,'run_music_command',provider):
            for row in (row for row in cases() if row['entry_id']=='listen.current'):
                answer,code=await f.request(row['question'],language=row['language'],identifier='paused-'+row['language'])
                self.assertEqual(code,200,answer)
                prefix=read_copy.ROWS['paused'][read_copy.LANGUAGES.index(row['language'])]
                self.assertTrue(answer['text'].startswith(prefix),answer['text'])
                self.assertIn('Recording',answer['text'])
                self.assertIn('Performer',answer['text'])
                self.assertEqual(answer['conversation']['metrics']['agent_calls'],0)
                self.assertEqual(answer['action'],'none')
        self.assertTrue(calls)
        self.assertEqual(f.effects,[])

