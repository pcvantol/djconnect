"""Gate policy regressions; no credentials or paid calls in unit CI."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

GOLDEN = load('contextual_golden', 'scripts/verification/askdj_contextual_golden.py')
RUNNER = load('contextual_gate', 'tools/verification/run_askdj_contextual_release_gate.py')


class ContextualReleaseGateTest(unittest.TestCase):
    def test_publication_only_probe_never_submits_followup_or_qualifies_complete_case(self):
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import patch
        from scripts.verification.askdj_contextual_quality import run
        calls=[]
        async def start(label,**kwargs):
            calls.append('start')
            return SimpleNamespace(session_id='fixture-session'),SimpleNamespace(
                moment_id='fixture-moment',content='Explicit fixture publication.'),None
        async def end(*args):
            calls.append('end')
        async def forbidden(*args,**kwargs):
            self.fail('A publication-only probe must not submit Ask DJ, clear or read chat history')
        env={'DJC_QUALITY_LOCALES':'nl','DJC_QUALITY_KINDS':'selected','DJC_QUALITY_SEED_ONLY':'1'}
        with patch.dict('os.environ',env):
            report=asyncio.run(run(ask=forbidden,call=forbidden,start=start,end=end,
                get_history=forbidden,mutations=[],model_receipts=[]))
        self.assertEqual(calls,['start','end'])
        self.assertEqual(report['selected_seed_publication']['moment_id'],'fixture-moment')
        self.assertEqual(report['selected_probe_scope'],'publication_only_partial')
        self.assertEqual(report['cases'][0]['findings'],['selected_followup_not_exercised'])
        self.assertEqual(report['mechanical_status'],'FAIL')
        for change in ({'DJC_QUALITY_KINDS':'band'},{'DJC_QUALITY_LOCALES':'nl,en'},
                       {'DJC_QUALITY_SEED_ONLY':'true'}):
            with patch.dict('os.environ',{**env,**change}),self.assertRaises(ValueError):
                asyncio.run(run(ask=forbidden,call=forbidden,start=start,end=end,
                    get_history=forbidden,mutations=[],model_receipts=[]))

    def test_actual_quality_budget_is_durable_across_runs_and_rejects_budget_increase(self):
        import ast
        import json
        import os
        from tempfile import TemporaryDirectory
        path=ROOT/'scripts/verification/verify_ask_dj_contextual_dialogue_http.py'
        node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)
                  and n.name=='reserve_quality_attempt')
        namespace={'json':json,'os':os}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
        reserve=namespace['reserve_quality_attempt']
        with TemporaryDirectory() as directory:
            ledger=Path(directory)/'budget.json'
            ledger.write_text(json.dumps({'limit':40,'attempts':[]}))
            for run in range(2):
                for case in range(20):
                    reserve(ledger,f'run-{run}-case-{case}','fixture-model')
            self.assertEqual(len(json.loads(ledger.read_text())['attempts']),40)
            with self.assertRaisesRegex(RuntimeError,'exhausted'):
                reserve(ledger,'forty-first','fixture-model')
            ledger.write_text(json.dumps({'limit':80,'attempts':[]}))
            with self.assertRaisesRegex(RuntimeError,'invalid'):
                reserve(ledger,'raised-budget','fixture-model')
            with self.assertRaisesRegex(RuntimeError,'required'):
                reserve(None,'missing-ledger','fixture-model')

    def test_actual_answer_pilot_covers_five_languages_and_cannot_qualify_a_fallback(self):
        from scripts.verification.askdj_contextual_quality import cases,check_answer
        rows=cases()
        self.assertEqual(len(rows),15)
        self.assertEqual(len({r['id'] for r in rows}),15)
        for kind in ('selected','band','mood'):
            self.assertEqual({r['language'] for r in rows if r['kind']==kind},{'en','nl','de','fr','es'})
        case=next(r for r in rows if r['kind']=='band')
        fallback={'success':True,'text':'I could not verify enough information.','sources':[]}
        self.assertIn('generated_answer_missing',check_answer(case,fallback))
        self.assertIn('researched_answer_unqualified',check_answer(case,fallback))
        self.assertIn('closing_question_missing',check_answer(case,fallback))

    def test_semantic_release_gate_requires_every_real_model_case_and_source_binding(self):
        matrix = load('semantic_release_matrix', 'tools/verification/run_askdj_release_matrix.py')
        from scripts.verification.askdj_semantic_read_golden import cases, manifest_digest, expected_plan
        expected = cases()
        good = {'status': 'PASS', 'qualification': 'REAL_HA_SEMANTIC_CONTEXT_READS',
                'source_hashes': matrix.expected_source_hashes(), 'source_unchanged': True,
                'pairing': 'ordinary_device_token_minted_persisted', 'manifest_sha256': manifest_digest(),
                'effects': [], 'paid_model_calls': len(expected), 'setup_paid_model_calls': 0,
                'cases': [{**c, 'status': 'PASS', 'findings': [], 'metrics': {'agent_calls': 1}} for c in expected],
                'model_calls': [{'case_id': c['id'], 'attempted': True, 'completed': True, 'generated_text': __import__('json').dumps(expected_plan(c))} for c in expected],
                'core_transports': [{'case': c['id'], 'status': 200, 'expected_status': 200,
                                     'path': 'ask_dj/message', 'cache_control': 'no-store',
                                     'body': {'interpretation_basis': 'ha_semantic_read_v1',
                                              'playback_actions': [{'uri': 'spotify:track:' + char * 22,
                                                  'title': 'Synthetic named recording ' + str(i + 2),
                                                  'action_id': 'frozen-' + char} for i, char in enumerate(('e', 'f'))]
                                              if c['read'] == 'artist_tracks' else []}} for c in expected]}
        self.assertTrue(matrix.validate_semantic_report(good))
        for change in (
            lambda r: r['cases'].pop(),
            lambda r: r['model_calls'][0].update(attempted=False),
            lambda r: r['model_calls'][0].update(completed=False),
            lambda r: r['model_calls'][0].update(generated_text='{}'),
            lambda r: r['model_calls'][0].update(generated_text=__import__('json').dumps(
                {**expected_plan(expected[0]), 'exclude_current': 0})),
            lambda r: r['model_calls'][0].update(generated_text='{"read":"play",' +
                __import__('json').dumps(expected_plan(expected[0]))[1:]),
            lambda r: r['model_calls'][-1].update(generated_text=__import__('json').dumps(
                {**expected_plan(expected[-1]), 'exclude_current': False})),
            lambda r: r['core_transports'][-1]['body']['playback_actions'][0].update(uri='spotify:track:' + 'x' * 22),
            lambda r: r['cases'][0]['metrics'].update(agent_calls=0),
            lambda r: r.update(effects=[{'method': 'PUT'}]),
            lambda r: r.update(source_hashes={}),
            lambda r: r['source_hashes'].pop('scripts/verification/source_fixture_urls.py'),
            lambda r: r.update(manifest_sha256='wrong'),
        ):
            broken = deepcopy(good)
            change(broken)
            self.assertFalse(matrix.validate_semantic_report(broken))

    def test_source_fixture_classifier_is_pinned_by_actual_harness_and_release_hashes(self):
        import ast
        import hashlib
        matrix = load('fixture_hash_release_matrix', 'tools/verification/run_askdj_release_matrix.py')
        harness = ROOT/'scripts/verification/verify_ask_dj_contextual_dialogue_http.py'
        tree = ast.parse(harness.read_text())
        actual_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                               and node.name == 'hashes')
        namespace = {'ROOT': ROOT, 'Path': Path, 'hashlib': hashlib, '__file__': str(harness)}
        exec(compile(ast.Module(body=[actual_function], type_ignores=[]), str(harness), 'exec'), namespace)
        actual = namespace['hashes']()
        self.assertEqual(actual, matrix.expected_source_hashes())
        helper = 'scripts/verification/source_fixture_urls.py'
        self.assertEqual(actual[helper], hashlib.sha256((ROOT/helper).read_bytes()).hexdigest())

    def test_research_outcomes_never_promote_prefix_fallback_or_denial_to_full(self):
        classifier = load('research_outcomes', 'tools/verification/askdj_research_outcomes.py')
        full = {'success': True, 'text': 'A useful answer.', 'sources': [{'provider': 'Wikipedia'}],
                'knowledge_basis': 'fetched_public_music_research_v1'}
        self.assertEqual(classifier.classify_answer(full), 'full_answer_supported')
        self.assertEqual(classifier.classify_answer({**full,
            'research_answer_qualification': 'supported_prefix_v1'}), 'supported_prefix')
        self.assertEqual(classifier.classify_answer({**full,
            'knowledge_basis': 'public_research_unqualified'}), 'core_fallback')
        self.assertEqual(classifier.classify_answer({**full, 'error': 'access_revoked'}), 'denied')
        self.assertEqual(classifier.classify_answer(full, http_status=403), 'denied')
        for changed in ({**full, 'sources': []}, {**full, 'text': ''},
                        {**full, 'research_answer_qualification': 'future_unknown'}, {}):
            self.assertEqual(classifier.classify_answer(changed), 'unqualified')

    def test_five_languages_unique_full_manifest(self):
        rows = GOLDEN.cases()
        self.assertEqual(len(rows), 20)
        self.assertEqual(len({r['id'] for r in rows}), 20)
        self.assertEqual({r['language'] for r in rows}, {'en', 'nl', 'de', 'fr', 'es'})

    def response(self):
        return {'success': True, 'text': 'Peter Luts is a Belgian producer.', 'action': 'none',
                'conversation': {'context': {'selected_moment': {'session_id': 's', 'moment_id': 'm'}},
                                 'metrics': {'agent_calls': 1}},
                'sources': [{'url': 'https://en.wikipedia.org/wiki/Peter_Luts', 'claim_scope': 'person_biography',
                             'subject': {'kind': 'person', 'name': 'Peter Luts'}}]}

    def test_lost_selection_credit_only_fake_source_zero_agent_and_actions_rejected(self):
        row = GOLDEN.cases()[0]
        selection = {'session_id': 's', 'moment_id': 'm'}
        self.assertEqual(GOLDEN.check_response(row, self.response(), selection), [])
        for change, expected in (
            (lambda r: r['conversation']['context'].clear(), 'selected_context_boundary'),
            (lambda r: r['sources'][0].update(claim_scope='qualified_credit_only'), 'qualified_biography_source_missing'),
            (lambda r: r['sources'][0].update(url='https://www.wikidata.org.attacker.invalid/Q1'), 'qualified_biography_source_missing'),
            (lambda r: r['conversation']['metrics'].update(agent_calls=0), 'real_model_path_missing'),
            (lambda r: r.update(text='Which Peter do you mean?'), 'wrong_or_missing_person'),
            (lambda r: r.update(text='Peter Luts is not a musician.'), 'contradictory_biography'),
            (lambda r: r['sources'][0].update(url='https://en.wikipedia.org/wiki/Miles_Davis'), 'qualified_biography_source_missing'),
            (lambda r: r['sources'][0].update(subject={'kind': 'person', 'name': 'Someone Else'}), 'qualified_biography_source_missing'),
            (lambda r: r.update(playback_actions=[{'command': 'play'}]), 'unexpected_action'),
        ):
            response = self.response()
            change(response)
            self.assertIn(expected, GOLDEN.check_response(row, response, selection))

    def report(self):
        return {'schema_version': 1, 'suite': 'askdj_contextual_golden_v1', 'candidate_sha': 'a'*40,
                'manifest_sha256': GOLDEN.manifest_digest(), 'status': 'PASS',
                'cases': [{'id': c['id'], 'status': 'PASS', 'findings': [], 'paid_attempts': 1} for c in GOLDEN.cases()],
                'paid_model_calls': 20,
                'usage': [{'case_id': c['id'], 'model': 'gpt-6-luna', 'attempted': True, 'completed': True,
                           'input_tokens': 200, 'output_tokens': 50} for c in GOLDEN.cases()]}

    def test_incomplete_stale_zero_paid_and_failed_evidence_never_pass(self):
        good = self.report()
        self.assertTrue(RUNNER.validate_report(good, 'a'*40))
        for mutate in (
            lambda r: r.update(candidate_sha='b'*40),
            lambda r: r.update(manifest_sha256='old'),
            lambda r: r['cases'].pop(),
            lambda r: r['cases'].append(None),
            lambda r: r['cases'][0].update(status='FAIL'),
            lambda r: r.update(paid_model_calls=0),
            lambda r: r.update(paid_model_calls=41),
            lambda r: r['usage'][0].update(model='fixture'),
            lambda r: r['usage'][0].update(input_tokens=None),
        ):
            changed = deepcopy(good)
            mutate(changed)
            self.assertFalse(RUNNER.validate_report(changed, 'a'*40))

    def test_release_publication_waits_and_formal_job_cannot_race_tag(self):
        publication = (ROOT/'.github/workflows/home-assistant-release-artifact.yml').read_text()
        self.assertIn('needs: paid-contextual-golden', publication)
        self.assertIn('uses: ./.github/workflows/askdj-contextual-release-gate.yml', publication)
        self.assertFalse((ROOT/'.github/workflows/post-merge-release-evidence-dispatch.yml').exists())
        self.assertIn('needs: [paid-contextual-golden, package]', publication)
        gate = (ROOT/'.github/workflows/askdj-contextual-release-gate.yml').read_text()
        self.assertNotIn('continue-on-error', gate)
        self.assertNotIn('pull_request', gate)
        self.assertIn('internal-ha-*', gate)
        self.assertIn('git merge-base --is-ancestor', gate)

    def test_overlapping_main_events_keep_original_candidate_for_all_jobs(self):
        # workflow_run's outer GITHUB_SHA may already be B; its event payload
        # still names CI(A). No second workflow_run hop is introduced.
        workflow = (ROOT/'.github/workflows/home-assistant-release-artifact.yml').read_text()
        self.assertIn('CANDIDATE_SHA: ${{ github.event.workflow_run.head_sha }}', workflow)
        self.assertIn('candidate_sha: ${{ github.event.workflow_run.head_sha }}', workflow)
        self.assertNotIn('candidate_sha: ${{ github.sha }}', workflow)
        policy = (ROOT/'.github/workflows/post-merge-release-evidence.yml').read_text()
        self.assertIn('MAIN_SHA: ${{ github.event.workflow_run.head_sha }}', policy)
        for source, current_main in [('a'*40, 'b'*40), ('b'*40, 'b'*40)]:
            event = {'workflow_run': {'head_sha': source}}
            selected = event['workflow_run']['head_sha']
            self.assertEqual(selected, source)
            self.assertEqual({'gate': selected, 'package': selected, 'formal': selected},
                             dict.fromkeys(['gate', 'package', 'formal'], source))

    def test_every_help_template_is_instantiated_without_changing_help_copy(self):
        import json
        from tests.ask_dj_e2e_contract import materialize_case
        rows=json.loads((ROOT/'examples/ask_dj_e2e_cases.json').read_text())
        help_rows=[row for row in rows if row['id'].startswith('help_prompt_')]
        self.assertEqual(len(help_rows),60)
        for row in help_rows:
            resolved=materialize_case(row)
            self.assertNotIn('[',resolved['request']['text'])
            self.assertNotIn('fixture_bindings',resolved['request'])
        seed=next(r for r in help_rows if r['id'].startswith('help_prompt_seed_mix'))
        self.assertEqual(materialize_case(seed)['request']['text'],
                         'Maak een mix op basis van Radiohead, Massive Attack en Bon Iver')
        unbound=deepcopy(seed)
        unbound.pop('fixture_bindings')
        with self.assertRaises(ValueError):
            materialize_case(unbound)

    def test_all_literal_core_routes_and_owner_bindings_are_accounted_for(self):
        inventory=load('djc_release_inventory','tools/verification/askdj_release_inventory.py')
        proof=inventory.validate()
        self.assertEqual(proof['literal_core_routes'],48)
        self.assertEqual(proof['executable_help_cases'],60)
        self.assertEqual(proof['conversation_families'],42)
        self.assertEqual(proof['conversation_steps'],320)
        self.assertEqual(proof['reported_issues'],75)
        self.assertEqual(len(proof['open_core_findings']),30)
        self.assertEqual(proof['proactive_golden_cases'],560)
        self.assertEqual(proof['catalogue_questions'],70)
        self.assertEqual(proof['catalogue_conversation_steps'],30)

    def test_every_golden_owning_file_is_scheduled_before_provider_work(self):
        import json
        runner=load('owner_schedule_matrix','tools/verification/run_askdj_release_matrix.py')
        matrix=json.loads((ROOT/'docs/verification/fixtures/askdj_golden_release_matrix_v1.json').read_text())
        runner.validate_owner_pattern_coverage(matrix)
        for file in ('test_session_forecast.py','test_passive_session.py','test_voice_preview.py','test_session_opening.py','test_persona_reactions.py','test_config_flow_helpers.py','test_device_speech.py'):
            with self.subTest(file=file),self.assertRaisesRegex(ValueError,'required_owning_file_not_scheduled'):
                runner.validate_owner_pattern_coverage(matrix,
                    tuple(pattern for pattern in runner.TEST_PATTERNS if pattern!=file))

    def test_renderer_owner_requires_node_and_never_inherits_paid_credentials(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from types import SimpleNamespace
        runner=load('host_renderer_matrix','tools/verification/run_askdj_release_matrix.py')
        with TemporaryDirectory() as folder:
            directory=Path(folder)
            with patch.object(runner.shutil,'which',return_value=None), \
                    patch.object(runner.subprocess,'run') as process:
                self.assertEqual(runner.host_renderer_run(directory),127)
                process.assert_not_called()
            with patch.dict(runner.os.environ,{'DJCONNECT_GOLDEN_OPENAI_API_KEY':'synthetic-private-key',
                    'OPENAI_API_KEY':'synthetic-private-key','HA_TOKEN':'synthetic-private-token'}), \
                    patch.object(runner.shutil,'which',return_value='/synthetic/node'), \
                    patch.object(runner.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as process:
                self.assertEqual(runner.host_renderer_run(directory),0)
                env=process.call_args.kwargs['env']
                for name in ('DJCONNECT_GOLDEN_OPENAI_API_KEY','OPENAI_API_KEY','HA_TOKEN'):
                    self.assertNotIn(name,env)
                self.assertNotIn('synthetic-private',str(process.call_args))
                self.assertEqual(env['PYTHONPATH'],str(ROOT))

    def test_reported_issue_without_family_or_open_disposition_cannot_pass_release(self):
        import json
        inventory=load('issue_inventory','tools/verification/askdj_release_inventory.py')
        matrix=json.loads((ROOT/'docs/verification/fixtures/askdj_golden_release_matrix_v1.json').read_text())
        self.assertIn('ASKDJ-ISSUE-research-unsupported-fact',inventory.release_blockers(matrix))
        for change in ('missing','duplicate','unbound','invalid','step_unbound','step_duplicate','step_unknown'):
            changed=deepcopy(matrix)
            if change=='missing':
                changed.pop('reported_issues')
            elif change=='duplicate':
                changed['reported_issues'].append(changed['reported_issues'][0])
            elif change=='unbound':
                changed['reported_issues'][0]['family_id']='unexecuted_invented_family'
            elif change=='step_unbound':
                changed['families'][0]['steps'][0]['owning_tests']=[]
            elif change=='step_duplicate':
                changed['families'][0]['steps'][1]['id']=changed['families'][0]['steps'][0]['id']
            elif change=='step_unknown':
                changed['families'][0]['steps'][0]['acceptance_status']='PASS_WITHOUT_EXECUTION'
            else:
                changed['reported_issues'][0]['core_qualification']='PASS_WITHOUT_EXECUTION'
            with self.subTest(change=change),self.assertRaises(ValueError):
                inventory.release_blockers(changed)
        # The actual Nirvana causal regressions must be release bindings, not
        # merely helper/test functions discoverable in a separate local suite.
        bindings=inventory.required_bindings(matrix)
        required={
            'test_voice_request_and_speaker_choice_keep_exact_artist_and_never_resume_old_queue',
            'test_track_choice_is_producer_frozen_despite_injected_selection_and_changed_search',
            'test_compound_speaker_timeout_is_uncertain_and_single_use_without_music_start',
        }
        self.assertTrue(required <= {row['method'] for row in bindings})

    def test_empty_and_anonymous_full_or_local_receipts_never_pass(self):
        matrix=load('djc_release_matrix','tools/verification/run_askdj_release_matrix.py')
        self.assertFalse(matrix.validate_local_report('previous',{}))
        forged={'core_transports':[{'case':'one','status':200,'expected_status':200}],
                'model_calls':[{'case_id':'one','model':'gpt-6-luna','completed':True}],
                'mixed_chains':[{}]*3,'style_cases':[{}]*20}
        self.assertEqual(matrix.redacted_full_report(forged)['status'],'FAIL')

    def test_publication_is_serialized_and_existing_assets_are_not_overwritten(self):
        workflow=(ROOT/'.github/workflows/home-assistant-release-artifact.yml').read_text()
        self.assertIn('group: ha-release-${{ github.event.workflow_run.head_sha }}',workflow)
        self.assertNotIn('--clobber',workflow)
        self.assertIn('gh release download',workflow)
        self.assertIn('--sort=name --mtime=@0',workflow)
        self.assertIn('gzip -n',workflow)

    def test_known_owner_denial_is_expected_but_missing_status_never_passes(self):
        matrix=load('djc_release_matrix','tools/verification/run_askdj_release_matrix.py')
        ids=['artist-old-clarification-seed','artist-selected-earlier','artist-state-invariant',
             'artist-pending-proposal','artist-not-confirmation','artist-provider-unavailable','artist-end-race','artist-other-profile']
        rows=[]
        for case in ids:
            status=403 if case=='artist-other-profile' else 409 if case=='artist-end-race' else 200
            rows.append({'case':case,'path':'ask_dj/message','request':{},'body':{'error':'denied'} if status>=400 else {'success':True},
                         'status':status,'expected_status':status,'cache_control':'no-store'})
        raw={'qualification':'ISOLATED_REAL_HA_TEXT_STT_CURRENT_ARTIST_ZERO_EFFECTS',
             'source_hashes':matrix.expected_source_hashes(),'pairing':'ordinary_device_token_minted_persisted',
             'core_transports':rows,'model_calls':[],'paid_model_calls':0}
        self.assertTrue(matrix.validate_local_report('current_artist',raw))
        missing=deepcopy(raw)
        missing['core_transports'][0].pop('status')
        missing['core_transports'][0].pop('expected_status')
        self.assertFalse(matrix.validate_local_report('current_artist',missing))
        unexpected=deepcopy(raw)
        unexpected['core_transports'][0].update(status=403,expected_status=403,body={'error':'denied'})
        self.assertFalse(matrix.validate_local_report('current_artist',unexpected))

    def test_album_release_gate_rejects_missing_art_buttons_header_and_single_track_album_dispatch(self):
        from tests import test_ask_dj_catalogue_golden as fixtures
        from scripts.verification import askdj_example_catalogue_golden as golden
        matrix=load('djc_album_release_matrix','tools/verification/run_askdj_release_matrix.py')
        ids=[*[f'album-current-artist-{i}' for i in range(5)],
            *[f'album-tracks-{i}' for i in range(5)], 'album-header-play','album-recording-play',
            'album-offer','album-play','album-play-duplicate',
            *['album-offer-'+locale for locale in ('en','de','fr','es')]]
        rows=[{'case':case,'path':'ask_dj/message','request':{},
            'status':409 if case=='album-play-duplicate' else 200,
            'expected_status':409 if case=='album-play-duplicate' else 200,
            'cache_control':'no-store','body':{'error':'choice_expired'} if case=='album-play-duplicate'
                else {'success':True}} for case in ids]
        fixture=fixtures.CatalogueGoldenTest()
        for i,locale in enumerate(('nl','en','de','fr','es')):
            case=next(c for c in golden.cases() if c['entry_id']=='listen.album_tracks' and c['language']==locale)
            body=fixture.response(case)
            body.update(fixture.album_payload())
            next(row for row in rows if row['case']==f'album-tracks-{i}')['body']=body
        raw={'qualification':'CORE_PAIRED_ALBUM_TRACKS_AND_FROZEN_ALBUM_PLAY',
            'source_hashes':matrix.expected_source_hashes(),'pairing':'ordinary_device_token_minted_persisted',
            'core_transports':rows,'model_calls':[],'paid_model_calls':0,
            'provider_calls':[{'method':'PUT','path':'/me/player/play','body':body} for body in (
                {'context_uri':golden.ALBUM},{'uris':[golden.TRACKS[-1]]},
                {'context_uri':'spotify:album:'+'c'*22})]}
        self.assertTrue(matrix.validate_local_report('album_context',raw))
        for field in ('image_url','button_label','action_id'):
            changed=deepcopy(raw)
            changed['core_transports'][5]['body']['items'][1].pop(field)
            self.assertFalse(matrix.validate_local_report('album_context',changed),field)
        wrong=deepcopy(raw)
        wrong['provider_calls'][0]['body']={'uris':[golden.TRACKS[0]]}
        self.assertFalse(matrix.validate_local_report('album_context',wrong))
        missing=deepcopy(raw)
        missing['core_transports'][5]['body']['result_set'].pop('presentation')
        self.assertFalse(matrix.validate_local_report('album_context',missing))

    def test_prosody_gate_requires_all_moods_languages_and_real_paired_audio_receipt(self):
        import hashlib
        from tempfile import TemporaryDirectory
        matrix = load('prosody_matrix', 'tools/verification/run_askdj_release_matrix.py')
        rows = [{'language': language, 'locale': language + '-XX', 'mood': mood, 'voice': 'marin',
                 'bytes': 1000, 'text_sha256': hashlib.sha256(language.encode()).hexdigest(),
                 'sha256': hashlib.sha256(bytes(1000)).hexdigest()}
                for language in ('en', 'nl', 'de', 'fr', 'es')
                for mood in ('chill', 'groove', 'energy', 'party')]
        transports = [{'case': case, 'path': path, 'status': status, 'expected_status': status}
                      for case, path, status in (
                          ('literal-tts-start', 'session/start', 201),
                          ('literal-tts-prepare', 'speech/prepare', 200),
                          ('literal-tts-repeat', 'speech/prepare', 200),
                          ('literal-tts-end', 'session/end', 200))]
        audio = {'status': 200, 'bytes': 1000, 'content_type': 'audio/mpeg', 'sha256': 'a' * 64}
        raw = {'qualification': 'ISOLATED_REAL_HA_PAIRED_OPENAI_LITERAL_TTS',
               'pairing': 'ordinary_device_token_minted_persisted', 'tts_model': 'gpt-4o-mini-tts',
               'source_hashes': matrix.expected_source_hashes(),
               'source_hashes_before': matrix.expected_source_hashes(),
               'status': 'PASS', 'source_unchanged': True, 'paid_tts_attempts': 21,
               'mood_prosody': rows, 'core_transports': transports, 'audio_reads': [audio, audio],
               'synthesis': [{'attempted': True, 'text_sha256': 'b' * 64}]}
        with TemporaryDirectory() as directory:
            for r in rows:
                (Path(directory) / f"prosody-{r['language']}-{r['mood']}.mp3").write_bytes(bytes(1000))
            self.assertTrue(matrix.validate_prosody_report(raw, directory))
            for changed in (
                {**raw, 'mood_prosody': rows[:-1]}, {**raw, 'paid_tts_attempts': 0},
                {**raw, 'source_unchanged': False}, {**raw, 'source_hashes': {}},
                {**raw, 'audio_reads': []}, {**raw, 'core_transports': [{}]},
                {**raw, 'mood_prosody': [{**r, 'voice': r['mood']} for r in rows]},
                {**raw, 'mood_prosody': [{**r, 'text_sha256': r['mood']} for r in rows]},
                {'status': 'PASS', 'source_unchanged': True, 'paid_tts_attempts': 21,
                 'mood_prosody': rows, 'core_transports': [{}], 'audio_reads': [{}, {}]},
            ):
                self.assertFalse(matrix.validate_prosody_report(changed, directory))
            (Path(directory) / 'prosody-en-party.mp3').write_bytes(b'corrupted')
            self.assertFalse(matrix.validate_prosody_report(raw, directory))
