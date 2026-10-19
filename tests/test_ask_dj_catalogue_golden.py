"""Golden completeness and truthful acceptance, not passing product answers."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.verification import askdj_example_catalogue_golden as golden


class CatalogueGoldenTest(unittest.TestCase):
    def test_every_catalogue_question_is_an_exact_five_language_golden_input_even_if_pending(self):
        data = json.loads(golden.catalogue_bytes())
        rows = golden.cases()
        self.assertEqual(len(rows), 70)
        self.assertEqual(len({r['id'] for r in rows}), 70)
        self.assertEqual(Counter(r['language'] for r in rows), dict.fromkeys(golden.LANGUAGES, 14))
        indexed = {e['id']:e for e in data['entries']}
        for row in rows:
            entry = indexed[row['entry_id']]
            self.assertEqual(row['question'],entry['templates'][row['language']].format(artist=golden.ARTIST))
            self.assertTrue(row['expected']['answer'])
            self.assertEqual(row['qualification'],'pending_actual_paired_execution')
            self.assertNotIn('{',row['question'])
        self.assertTrue(all(r['id'].startswith('catalogue-') for r in rows))

    def test_new_question_missing_translation_and_duplicate_id_fail_inventory(self):
        original = json.loads(golden.catalogue_bytes())
        for mutate in (
            lambda d:d['entries'].append({**deepcopy(d['entries'][0]),'id':'invented.new.question'}),
            lambda d:d['entries'][0]['templates'].pop('fr'),
            lambda d:d['entries'].append(deepcopy(d['entries'][0])),
        ):
            changed = deepcopy(original)
            mutate(changed)
            with TemporaryDirectory() as directory:
                root = Path(directory)
                target = root/golden.CATALOGUE
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    golden.cases(root)

    def test_both_speaker_continuation_and_full_album_followup_have_all_five_languages_and_dedup(self):
        rows = golden.chain_cases()
        self.assertEqual(len(rows),30)
        self.assertEqual(len({r['id'] for r in rows}),30)
        self.assertEqual(Counter(r['language'] for r in rows),dict.fromkeys(golden.LANGUAGES,6))
        for chain in {r['chain'] for r in rows}:
            steps = [r for r in rows if r['chain'] == chain]
            self.assertEqual([r['operation'] for r in steps],['offer','accept','duplicate'])
            self.assertEqual(steps[-1]['expected']['effect'],'none')
            self.assertEqual(steps[1]['expected']['effect'],
                'album_play' if '-album-' in chain else 'artist_play')

    def response(self, case):
        return {'success':True,'text':'Accepted synthetic response',
            'intent':{'intent':case['expected']['intent']},
            'conversation':{'style':{'language':case['language']}}}

    def album_payload(self):
        rows = [{'kind':'album' if i == 0 else 'track','uri':uri,
            'context_uri':uri if i == 0 else '', 'action_id':str(i),
            'button_label':'Play', 'image_url':'/api/djconnect/v1/image_proxy/fixture'}
            for i,uri in enumerate([golden.ALBUM,*golden.TRACKS[1:]])]
        return {'items':deepcopy(rows), 'playback_actions':deepcopy(rows),
            'result_set':{'result_set_id':'fixture-set','items':deepcopy(rows),
                'presentation':{'kind':'album_tracks','primary_action_id':'0','track_action_ids':['1','2']}},
            'album_track_observation':{'schema_version':1,'state':'complete',
                'album_uri':golden.ALBUM,'current_track_omitted':True,'returned_count':2}}

    def test_generic_confirmation_without_actual_dispatch_cannot_pass_playback(self):
        row = next(r for r in golden.cases() if r['entry_id']=='play.artist' and r['language']=='nl')
        body = self.response(row)
        body['text']='Daar is Volbeat.'
        failures = golden.check_response(row,body,[])
        self.assertIn('exactly_one_play_dispatch_required',failures)
        self.assertIn('real_playback_acceptance_missing',failures)
        self.assertIn('chosen_media_missing',failures)

    def test_track_identity_is_not_its_album_context_and_offset_must_match(self):
        case = next(r for r in golden.cases() if r['id']=='catalogue-discover.artist_tracks-en')
        body = self.response(case)
        body['playback_actions'] = [{'kind':'track','uri':uri,'context_uri':golden.ALBUM,
            'offset_uri':uri,'action_id':str(i)} for i,uri in enumerate(golden.TRACKS)]
        self.assertEqual(golden.check_response(case,body,[]),[])
        for key, wrong in (('uri',golden.TRACKS[1]), ('offset_uri',golden.TRACKS[1]),
                           ('context_uri','spotify:album:'+'x'*22)):
            changed = deepcopy(body)
            changed['playback_actions'][0][key] = wrong
            self.assertIn('actual_artist_recordings_missing',golden.check_response(case,changed,[]))

    def test_readonly_album_list_requires_exact_contained_items_and_observation(self):
        case = next(r for r in golden.cases() if r['id']=='catalogue-listen.album_tracks-en')
        body = self.response(case)
        body.update(self.album_payload())
        self.assertEqual(golden.check_response(case,body,[]),[])
        for key, wrong in (('album_uri','spotify:album:'+'x'*22),('current_track_omitted',False),
                           ('returned_count',True),('state','partial')):
            changed = deepcopy(body)
            changed['album_track_observation'][key] = wrong
            self.assertIn('wrong_album_recordings_or_current_not_excluded',golden.check_response(case,changed,[]))
        changed = deepcopy(body)
        changed['items'][0]['uri'] = golden.TRACKS[0]
        self.assertIn('wrong_album_recordings_or_current_not_excluded',golden.check_response(case,changed,[]))
        for field in ('action_id','button_label','image_url'):
            changed = deepcopy(body)
            changed['items'][1].pop(field)
            self.assertIn('album_header_or_track_play_art_missing',golden.check_response(case,changed,[]))
        changed = deepcopy(body)
        changed['text'] += '\n• Second recording\n• Third recording'
        self.assertIn('duplicate_album_text_list',golden.check_response(case,changed,[]))

    def test_album_request_cannot_pass_with_one_track_even_if_text_claims_whole_album(self):
        row = next(r for r in golden.chain_cases() if r['id']=='catalogue-chain-album-nl-accept')
        body = self.response(row)
        body.update(text='Het hele album speelt.',resolved_media={'uri':golden.ALBUM},
                    playback_outcome={'state':'observed'},is_generated_text=True)
        wrong = [{'accepted':True,'status':204,'method':'PUT','path':'/me/player/play','body':{'uris':[golden.TRACKS[0]]}}]
        self.assertIn('wrong_or_downgraded_context',golden.check_response(row,body,wrong))
        correct = [{'accepted':True,'status':204,'method':'PUT','path':'/me/player/play','body':{'context_uri':golden.ALBUM}}]
        self.assertEqual(golden.check_response(row,body,correct),[])

    def test_current_context_fallback_and_wrong_locale_do_not_count_as_answers(self):
        row = next(r for r in golden.cases() if r['entry_id']=='listen.current' and r['language']=='nl')
        body = self.response(row)
        body['text']='Welke artiest bedoel je?'
        self.assertIn('current_recording_identity_missing',golden.check_response(row,body,[]))
        body['text']=golden.CURRENT+' van '+golden.ARTIST
        body['conversation']['style']['language']='en'
        self.assertIn('wrong_effective_locale',golden.check_response(row,body,[]))

    def test_read_only_catalogue_question_and_duplicate_reject_any_provider_write(self):
        row = next(r for r in golden.cases() if r['entry_id']=='listen.queue')
        body = self.response(row)
        body['queue_observation']={'state':'known_empty'}
        write = [{'accepted':True,'status':204,'method':'PUT','path':'/me/player/volume','body':{}}]
        self.assertIn('unexpected_music_effect',golden.check_response(row,body,write))
        duplicate = next(r for r in golden.chain_cases() if r['operation']=='duplicate')
        body = self.response(duplicate)
        self.assertIn('unexpected_music_effect',golden.check_response(duplicate,body,write))

    def test_release_runner_requires_actual_catalogue_profile_and_content_hash(self):
        root = golden.ROOT
        runner = (root/'tools/verification/run_askdj_release_matrix.py').read_text()
        harness = (root/'scripts/verification/verify_ask_dj_contextual_dialogue_http.py').read_text()
        for source in (runner,harness):
            self.assertIn('askdj_example_catalogue_golden.py',source)
            self.assertIn('ask_dj/examples_v1.json',source)
            self.assertIn('catalogue_golden',source)
        self.assertIn("'catalogue_golden': ('catalogue-golden.json', 1800)",runner)
        self.assertIn('validate_catalogue(raw, source_hashes=expected_source_hashes())',runner)
        self.assertFalse(golden.validate_report({},source_hashes={}))
        self.assertFalse(golden.validate_report({'status':'PASS','cases':[]},source_hashes={}))

    def test_manifest_changes_when_template_or_expectation_changes(self):
        original = golden.manifest_digest()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root/golden.CATALOGUE
            target.parent.mkdir(parents=True)
            target.write_bytes(golden.catalogue_bytes())
            self.assertEqual(golden.manifest_digest(root),original)
            data = json.loads(target.read_text())
            data['entries'][0]['templates']['nl'] += ' graag'
            target.write_text(json.dumps(data,ensure_ascii=False))
            self.assertNotEqual(golden.manifest_digest(root),original)
        self.assertEqual(len(hashlib.sha256(original.encode()).hexdigest()),64)

    def test_release_inventory_rejects_a_silently_missing_or_reworded_catalogue_question(self):
        from tools.verification.askdj_release_inventory import validate_catalogue_rows
        matrix = json.loads((golden.ROOT/'docs/verification/fixtures/askdj_golden_release_matrix_v1.json').read_text())
        self.assertEqual(validate_catalogue_rows(matrix),(70,30))
        for key in ('question','expected_answer','entry_id','language','execution_profile'):
            changed = deepcopy(matrix)
            family = next(f for f in changed['families'] if f['id']=='ASKDJ-FLOW-catalogue-exact-questions')
            family['steps'][0][key]='invented'
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_catalogue_rows(changed)
        changed = deepcopy(matrix)
        changed['catalogue_questions']['manifest_sha256']='stale'
        with self.assertRaises(ValueError):
            validate_catalogue_rows(changed)

    def receipt_fixture(self):
        """Explicit report-validator fixture, never an executed product receipt."""
        rows, http, calls = [], [], []
        for case in golden.cases()+golden.chain_cases():
            body = self.response(case)
            body.update(text=golden.CURRENT+' '+golden.ARTIST+' 2008-05-06',
                is_generated_text=True, knowledge_basis='fetched_public_music_research_v1', resolved_media={'uri':golden.ALBUM},
                playback_outcome={'state':'observed'},
                queue_observation={'state':'known_empty'}, session_forecast={'state':'limited'},
                sources=[{'title':golden.ARTIST,'provider':'Wikipedia','license':'CC-BY-SA-4.0',
                    'revision_url':'https://en.wikipedia.org/w/index.php?oldid=123',
                    'content_hash':'a'*64,'url':'https://en.wikipedia.org/wiki/Volbeat'}])
            uris = {'discover.artist_albums':[golden.ALBUM],
                'discover.artist_tracks':golden.TRACKS,
                'discover.playlists':[golden.PLAYLIST],
                'listen.album_tracks':golden.TRACKS[1:]}.get(case['entry_id'],[])
            body['playback_actions']=[{'uri':uri,'context_uri':uri if ':album:' in uri else None,
                'action_id':str(i),'kind':'album' if ':album:' in uri else 'track'} for i,uri in enumerate(uris)]
            if case['entry_id']=='listen.album_tracks':
                body.update(self.album_payload())
            if case['entry_id']=='listen.outputs' or (case.get('operation')=='offer' and '-speaker-' in case['chain']):
                body['playback_actions']=[{'kind':'output','device_id':'own-speaker','action_id':'output'}]
            body['result_set']={'result_set_id':'fixture-set', 'items':deepcopy(body['playback_actions'])}
            if case['entry_id']=='listen.album_tracks':
                body['result_set'] = self.album_payload()['result_set']
            effect = case['expected']['effect']
            writes = [] if effect=='none' else [{'accepted':True,'status':204,'method':'PUT','path':'/me/player/play','body':
                {'uris':golden.TRACKS} if effect=='artist_play' else
                {'context_uri':golden.ALBUM if effect=='album_play' else golden.PLAYLIST}}]
            if case.get('operation')=='accept' and '-speaker-' in case['chain']:
                writes[0]['path'] += '?device_id=own-speaker'
            paid = 0 if case.get('operation')=='duplicate' else 2 if effect!='none' or case['entry_id']=='listen.artist' else 0
            body['conversation']['metrics']={'agent_calls':paid}
            calls += [{'case_id':case['id'],'model':'gpt-6-luna','attempted':True,
                'completed':True,'input_tokens':100,'output_tokens':50} for _ in range(paid)]
            if case.get('operation') != 'duplicate':
                calls.append({'case_id':case['id'],'model':'gpt-6-luna','attempted':True,
                    'completed':True,'input_tokens':100,'output_tokens':30,
                    'purpose':'answer_language_judge',
                    'answer_sha256':hashlib.sha256(golden.answer_text(body).encode()).hexdigest(),
                    'judge_prompt_sha256':hashlib.sha256(golden.language_prompt(body['text'],case['language']).encode()).hexdigest(),
                    'generated_text':json.dumps({'detected_language':case['language'],'language_ok':True})})
            rows.append({'id':case['id'],'status':'PASS','findings':[],
                'question_sha256':hashlib.sha256(case['question'].encode()).hexdigest(),
                'provider_operations':deepcopy(writes),'provider_writes':writes,
                'paid_attempts':paid+(case.get('operation')!='duplicate')})
            http.append({'case':case['id'],'path':'ask_dj/message','status':200,'cache_control':'no-store',
                'request':{'text':case['question'],'language':case['language'],'audio_response':'never',
                    'client_message_id':case['chain']+'-accept' if case.get('operation')=='duplicate' else case['id'],
                    **({'choice_action':{'result_set_id':'fixture-set','action_id':'output','operation':'play'}}
                       if case.get('operation')=='accept' and '-speaker-' in case.get('chain','') else {})}, 'body':body})
            if case.get('operation')=='duplicate':
                previous = next(t for t in http if t['case']==case['chain']+'-accept')
                http[-1]['request']=deepcopy(previous['request'])
                http[-1]['body']=deepcopy(previous['body'])
        for call in calls:
            call.update(maximum_output_tokens=golden.MAX_OUTPUT_TOKENS, reasoning_effort=golden.REASONING_EFFORT)
        return {'qualification':'REAL_PAIRED_HA_EXACT_CATALOGUE_QUESTIONS_V1',
            'configured_maximum_tokens':golden.MAX_OUTPUT_TOKENS, 'configured_reasoning_effort':golden.REASONING_EFFORT,
            'status':'PASS','source_hashes':{'test':'explicit_fixture'}, 'source_unchanged':True,
            'pairing':'ordinary_device_token_minted_persisted','manifest_sha256':golden.manifest_digest(),
            'cases':rows,'model_calls':calls,'paid_model_calls':len(calls),'core_transports':http}

    def test_receipt_rejects_missing_duplicate_wrong_question_and_unpaid_claims(self):
        raw = self.receipt_fixture()
        pins = {'test':'explicit_fixture'}
        self.assertTrue(golden.validate_report(raw,source_hashes=pins))
        for mutate in (
            lambda r:r['cases'].pop(),
            lambda r:r['cases'].__setitem__(0,deepcopy(r['cases'][1])),
            lambda r:r['core_transports'][0]['request'].update(text='different hidden request'),
            lambda r:r['core_transports'][0]['request'].update(language='fr'),
            lambda r:r['core_transports'].append(deepcopy(r['core_transports'][0])),
            lambda r:r['model_calls'][0].update(completed=False),
            lambda r:r['model_calls'][0].update(input_tokens=0),
            lambda r:r['model_calls'][0].update(model='fixture'),
            lambda r:r['model_calls'][0].update(maximum_output_tokens=700),
            lambda r:r['model_calls'][0].update(reasoning_effort='high'),
            lambda r:r.update(configured_maximum_tokens=700),
            lambda r:r.update(qualification='REAL_PAIRED_HA_SELECTED_CATALOGUE_CASES_V1'),
            lambda r:r.update(selected_case_ids=['catalogue-listen.artist-en']),
            lambda r:r['model_calls'][0].update(case_id='invented_other_case'),
            lambda r:r['model_calls'].clear(),
            lambda r:r.update(manifest_sha256='stale'),
            lambda r:r.update(source_unchanged=False),
        ):
            changed = deepcopy(raw)
            mutate(changed)
            self.assertFalse(golden.validate_report(changed,source_hashes=pins))
        changed = deepcopy(raw)
        changed['model_calls'] += [{**deepcopy(raw['model_calls'][0]),'case_id':'catalogue-start'} for _ in range(3)]
        changed['paid_model_calls']=len(changed['model_calls'])
        self.assertFalse(golden.validate_report(changed,source_hashes=pins))

    def test_wrong_device_query_order_and_foreign_offered_target_fail(self):
        raw = self.receipt_fixture()
        pins = raw['source_hashes']
        identifier = 'catalogue-chain-speaker-nl-accept'
        for path in ('/me/player/play?device_id=foreign-device',
                     '/me/player/play?device_id=own-speaker&device_id=foreign-device',
                     '/me/player/play'):
            changed = deepcopy(raw)
            row = next(r for r in changed['cases'] if r['id']==identifier)
            row['provider_operations'][0]['path']=path
            row['provider_writes'][0]['path']=path
            self.assertFalse(golden.validate_report(changed,source_hashes=pins))
        changed = deepcopy(raw)
        row = next(r for r in changed['cases'] if r['id']==identifier)
        row['provider_writes'][0]['path']='/me/player/play'
        row['provider_writes'].append({'accepted':True,'status':204,'method':'PUT',
            'path':'/me/player','body':{'device_ids':['own-speaker'],'play':False}})
        row['provider_operations']=deepcopy(row['provider_writes'])
        self.assertFalse(golden.validate_report(changed,source_hashes=pins))
        changed = deepcopy(raw)
        offer = next(t for t in changed['core_transports'] if t['case']=='catalogue-chain-speaker-nl-offer')
        offer['body']['result_set']['items'][0]['device_id']='foreign-device'
        self.assertFalse(golden.validate_report(changed,source_hashes=pins))

    def test_duplicate_identity_text_selection_expiry_and_provider_reads_are_frozen(self):
        raw = self.receipt_fixture()
        for key, value in (('text','Different answer'), ('resolved_media',{'uri':golden.TRACKS[0]}),
                           ('result_set',{'result_set_id':'new-id','expires_at':'later'})):
            changed = deepcopy(raw)
            duplicate = next(t for t in changed['core_transports'] if t['case']=='catalogue-chain-album-nl-duplicate')
            duplicate['body'][key]=value
            self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))
        for identifier in ('catalogue-chain-album-nl-duplicate','catalogue-chain-album-nl-accept'):
            changed = deepcopy(raw)
            row = next(r for r in changed['cases'] if r['id']==identifier)
            row['provider_operations'].append({'method':'GET','path':'/search?q=different'})
            self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))

    def test_actual_answer_language_requires_independent_bound_completed_judge_for_all_locales(self):
        raw = self.receipt_fixture()
        for language in golden.LANGUAGES:
            identifier = 'catalogue-listen.current-'+language
            changed = deepcopy(raw)
            body = next(t for t in changed['core_transports'] if t['case']==identifier)['body']
            body['text']='This is '+golden.CURRENT+' by '+golden.ARTIST
            # Locale metadata and every music identity still look correct.
            self.assertEqual(body['conversation']['style']['language'],language)
            self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))
            judge = next(c for c in changed['model_calls'] if c['case_id']==identifier)
            judge.update(answer_sha256=hashlib.sha256(body['text'].encode()).hexdigest(),
                judge_prompt_sha256=hashlib.sha256(golden.language_prompt(body['text'],language).encode()).hexdigest(),
                generated_text=json.dumps({'detected_language':'other' if language=='en' else 'en','language_ok':False}))
            self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))
        changed = deepcopy(raw)
        changed['model_calls']=[c for c in changed['model_calls'] if c.get('purpose')!='answer_language_judge']
        changed['paid_model_calls']=len(changed['model_calls'])
        self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))

    def test_language_judge_rejects_duplicate_keys_wrong_types_and_unbounded_output(self):
        raw = self.receipt_fixture()
        for output in ('{"detected_language":"en","detected_language":"nl","language_ok":false,"language_ok":true}',
                       '{"detected_language":"en","language_ok":1}',
                       '{"detected_language":"en","language_ok":"true"}',
                       '{"detected_language":"en","language_ok":true,"extra":0}',
                       ' '*1025+'{"detected_language":"en","language_ok":true}', None):
            changed = deepcopy(raw)
            judge = next(c for c in changed['model_calls'] if c.get('purpose')=='answer_language_judge')
            judge['generated_text']=output
            self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))

    def test_accepted_mutation_requires_real_success_status(self):
        raw = self.receipt_fixture()
        for status in (404,500,202,True,'204'):
            changed = deepcopy(raw)
            row = next(r for r in changed['cases'] if r['id']=='catalogue-chain-speaker-nl-accept')
            for key in ('provider_operations','provider_writes'):
                row[key][0]['status']=status
            self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))

    def test_no_output_404_exception_still_binds_original_artist_target_and_attempt_budget(self):
        raw = self.receipt_fixture()
        valid = {'accepted':False,'status':404,'method':'PUT','path':'/me/player/play',
                 'body':{'uris':golden.TRACKS}}
        for mutation in ({'path':'/me/player/play?device_id=foreign-device'},
                         {'body':{'uris':['spotify:track:'+'x'*22]}},
                         {'method':'POST'}, {'body':{'context_uri':golden.ALBUM}},
                         {'body':{'uris':golden.TRACKS,'position_ms':1000}},
                         {'path':'https://foreign.test/me/player/play'}, {'status':500}):
            changed = deepcopy(raw)
            row = next(r for r in changed['cases'] if r['id']=='catalogue-chain-speaker-nl-offer')
            invalid = {**deepcopy(valid),**mutation}
            row.update(provider_writes=[invalid],provider_operations=[deepcopy(invalid)])
            self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))
        changed = deepcopy(raw)
        row = next(r for r in changed['cases'] if r['id']=='catalogue-chain-speaker-nl-offer')
        row.update(provider_writes=[deepcopy(valid)],provider_operations=[deepcopy(valid)])
        self.assertTrue(golden.validate_report(changed,source_hashes=raw['source_hashes']))
        row['provider_writes'].append(deepcopy(valid))
        row['provider_operations'].append(deepcopy(valid))
        self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))

    def test_whole_album_cannot_skip_tracks_or_supply_other_play_body_overrides(self):
        raw = self.receipt_fixture()
        for extra in ({'offset':{'position':2}}, {'offset':{'uri':golden.TRACKS[-1]}},
                      {'offset':{'position':False}}, {'uris':golden.TRACKS[:1]},
                      {'position_ms':1000}, {'position_ms':False}, {'unknown':True}):
            changed = deepcopy(raw)
            row = next(r for r in changed['cases'] if r['id']=='catalogue-chain-album-nl-accept')
            for key in ('provider_operations','provider_writes'):
                row[key][0]['body'].update(extra)
            self.assertFalse(golden.validate_report(changed,source_hashes=raw['source_hashes']))
        changed = deepcopy(raw)
        row = next(r for r in changed['cases'] if r['id']=='catalogue-chain-album-nl-accept')
        for key in ('provider_operations','provider_writes'):
            row[key][0]['body'].update(offset={'position':0},position_ms=0)
        self.assertTrue(golden.validate_report(changed,source_hashes=raw['source_hashes']))
