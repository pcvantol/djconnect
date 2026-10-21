"""Full reactive release matrix: deterministic contracts + isolated HA + paid dialogue."""
from __future__ import annotations

import argparse
from collections import Counter
from fnmatch import fnmatchcase
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_askdj_contextual_release_gate import IMAGE, validate_report  # noqa: E402
from askdj_release_inventory import validate as validate_inventory, validate_moment_matrix, required_bindings, release_blockers  # noqa: E402

# Existing owning interpretation/authorization/transport suites. These use explicit
# agent/provider fixtures; their PASS is not paid-model or physical acceptance.
TEST_PATTERNS = (
    'test_pipeline.py', 'test_processor_runtime.py',
    'test_ask_dj*.py', 'test_askdj_contextual_release_gate.py', 'test_voice_intents.py', 'test_http_voice_helpers.py',
    'test_music_dna*.py', 'test_session_conversation*.py', 'test_history_deletion*.py',
    'test_dj_moment_golden_matrix.py', 'test_expressive_dj_persona.py', 'test_expressive_context_variation.py', 'test_silence_live_delivery.py', 'test_native_moment_delivery.py', 'test_session_presence.py', 'test_active_session_mood.py', 'test_session_persona.py',
    'test_personal_dj_narration*.py', 'test_session_facts.py',
    'test_personal_dj_runtime_expression.py', 'test_personal_dj_flow_completion.py',
    'test_track_insight.py', 'test_profile_settings_speech.py', 'test_session_artwork.py', 'test_session_artist_images.py', 'test_session_story_variety.py',
    'test_session_forecast.py', 'test_passive_session.py', 'test_mood_music_steering.py',
    'test_local_settings_speech.py', 'test_presence_four_levels.py', 'test_vibecast_renderer.py', 'test_display_projection.py',
    'test_voice_preview.py', 'test_persona_reactions.py', 'test_transport_operation_journal.py',
    'test_spotify_backend.py', 'test_session_retention_policy.py',
    'test_session_opening.py', 'test_config_flow_helpers.py', 'test_device_speech.py',
)


def validate_owner_pattern_coverage(matrix, patterns=TEST_PATTERNS):
    """Every named Golden owner must be scheduled before container/model work."""
    missing = sorted({binding['file'] for binding in required_bindings(matrix)
                      if not any(fnmatchcase(Path(binding['file']).name, pattern)
                                 for pattern in patterns)})
    if missing:
        raise ValueError('required_owning_file_not_scheduled:' + ','.join(missing))


def host_renderer_run(directory, *, seconds=240):
    """The renderer needs Node; this is a host fixture proof, never real HA.

    Keep paid/provider credentials out of the host test process. The pinned HA
    image remains unchanged and all actual application/protocol profiles still
    execute there. Missing Node fails closed instead of skipping named tests.
    """
    if shutil.which('node') is None:
        return 127
    env = {key: os.environ[key] for key in ('PATH', 'TMPDIR', 'TMP', 'TEMP', 'HOME',
        'SYSTEMROOT', 'LANG', 'LC_ALL') if key in os.environ}
    env.update(PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1')
    args = [sys.executable, str(ROOT/'tools/verification/run_askdj_owner_contracts.py'),
            'test_vibecast_renderer.py', str(directory/'owner-contracts.json')]
    try:
        with (directory/'private.log').open('w') as log:
            return subprocess.run(args, cwd=ROOT, env=env, stdout=log,
                stderr=subprocess.STDOUT, timeout=seconds, check=False).returncode
    except subprocess.TimeoutExpired:
        return 124


PROFILES = {
    'current_artist': ('current-artist.json', 240),
    'previous': ('previous-safety-fixed.json', 240),
    'output': ('output-safety-fixed.json', 240),
    'choice_titles': ('choice-titles.json', 240),
    'release_context': ('release-context.json', 240),
    'album_context': ('album-context.json', 240),
    'semantic_reads': ('semantic-reads.json', 900),
    'catalogue_golden': ('catalogue-golden.json', 1800),
    'catalogue_variations': ('catalogue-variations-golden.json', 1800),
    'silence_signal': ('silence-signal.json', 240),
    'mood_prosody': ('literal-tts.json', 600),
    'full_golden': ('dialogue.json', 1500),
    'contextual_golden': ('golden-contextual.json', 600),
}


def validate_prosody_report(raw, directory):
    """Technical audio gate, never a substitute for audible quality review."""
    if (not isinstance(raw, dict)
            or raw.get('qualification') != 'ISOLATED_REAL_HA_PAIRED_OPENAI_LITERAL_TTS'
            or raw.get('pairing') != 'ordinary_device_token_minted_persisted'
            or raw.get('tts_model') != 'gpt-4o-mini-tts'
            or raw.get('source_hashes') != expected_source_hashes()
            or raw.get('source_hashes_before') != expected_source_hashes()):
        return False
    transports = raw.get('core_transports', [])
    required = {'literal-tts-start': ('session/start', 201),
                'literal-tts-prepare': ('speech/prepare', 200),
                'literal-tts-repeat': ('speech/prepare', 200),
                'literal-tts-end': ('session/end', 200)}
    if not isinstance(transports, list) or not all(isinstance(r, dict) for r in transports):
        return False
    for case, (path, status) in required.items():
        matches = [r for r in transports if r.get('case') == case]
        if len(matches) != 1 or any(matches[0].get(k) != v for k, v in
                                    (('path', path), ('status', status), ('expected_status', status))):
            return False
    audio = raw.get('audio_reads', [])
    synthesis = raw.get('synthesis', [])
    if (not isinstance(audio, list) or len(audio) != 2 or audio[0] != audio[1]
            or not isinstance(audio[0], dict) or audio[0].get('status') != 200
            or audio[0].get('content_type') != 'audio/mpeg'
            or type(audio[0].get('bytes')) is not int or audio[0]['bytes'] < 100
            or not re.fullmatch('[0-9a-f]{64}', audio[0].get('sha256', ''))
            or len(synthesis) != 1 or synthesis[0].get('attempted') is not True
            or not re.fullmatch('[0-9a-f]{64}', synthesis[0].get('text_sha256', ''))):
        return False
    rows = raw.get('mood_prosody', [])
    expected = {(language, mood) for language in ('en', 'nl', 'de', 'fr', 'es')
                for mood in ('chill', 'groove', 'energy', 'party')}
    if (not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows)
            or raw.get('status') != 'PASS' or raw.get('source_unchanged') is not True
            or raw.get('paid_tts_attempts') != 21 or len(rows) != 20
            or {(r.get('language'), r.get('mood')) for r in rows} != expected
            or not raw.get('core_transports') or len(raw.get('audio_reads', [])) != 2):
        return False
    for language in ('en', 'nl', 'de', 'fr', 'es'):
        group = [r for r in rows if r['language'] == language]
        if (len({r.get('text_sha256') for r in group}) != 1
                or len({r.get('voice') for r in group}) != 1
                or any(not r.get('voice') or type(r.get('bytes')) is not int or r['bytes'] <= 0
                       or not re.fullmatch('[0-9a-f]{64}', r.get('sha256', ''))
                       or not re.fullmatch('[0-9a-f]{64}', r.get('text_sha256', ''))
                       or str(r.get('locale', '')).split('-')[0] != language for r in group)):
            return False
    for row in rows:
        path = Path(directory) / f"prosody-{row['language']}-{row['mood']}.mp3"
        if not path.is_file() or path.stat().st_size != row['bytes'] or path.stat().st_size > 2 * 1024 * 1024:
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            return False
    return True


def owned_run(args, *, payload, directory, seconds, network):
    name = 'djc-golden-' + os.urandom(8).hex()
    cmd = ['docker', 'run', '--rm', '-i', '--name', name, '--network', network,
           '--memory', '1g', '--cpus', '2', '--pids-limit', '256',
           '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
           '--workdir', '/candidate', '--entrypoint', 'python',
           '-e', 'PYTHONPATH=/candidate', '-e', 'DJC_SOURCE_ROOT=/candidate',
           '-v', str(ROOT)+':/candidate:ro', '-v', str(directory)+':/lab', *args]
    try:
        with (directory/'private.log').open('w') as log:
            result = subprocess.run(cmd, input=json.dumps(payload), text=True,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=seconds, check=False)
        return result.returncode
    except subprocess.TimeoutExpired:
        return 124
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30, check=False)


def expected_source_hashes():
    files=list((ROOT/'custom_components/djconnect').rglob('*.py'))
    files.append(ROOT/'scripts/verification/verify_ask_dj_contextual_dialogue_http.py')
    files.append(ROOT/'scripts/verification/personal_dj_narration_probe.py')
    files.append(ROOT/'tools/verification/askdj_research_outcomes.py')
    files.append(ROOT/'tools/verification/askdj_catalogue_variations.py')
    files.append(ROOT/'scripts/verification/askdj_semantic_read_golden.py')
    files.append(ROOT/'scripts/verification/askdj_contextual_quality.py')
    files.append(ROOT/'scripts/verification/askdj_example_catalogue_golden.py')
    files.append(ROOT/'scripts/verification/askdj_catalogue_provider_fixture.py')
    files.append(ROOT/'custom_components/djconnect/ask_dj/examples_v1.json')
    files.append(ROOT/'scripts/verification/source_fixture_urls.py')
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def validate_semantic_report(raw):
    from scripts.verification.askdj_semantic_read_golden import cases, manifest_digest, expected_plan
    expected = cases()
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate_plan_key')
            result[key] = value
        return result
    if (not isinstance(raw, dict) or raw.get('status') != 'PASS'
            or raw.get('qualification') != 'REAL_HA_SEMANTIC_CONTEXT_READS'
            or raw.get('source_hashes') != expected_source_hashes()
            or raw.get('source_unchanged') is not True
            or raw.get('pairing') != 'ordinary_device_token_minted_persisted'
            or raw.get('manifest_sha256') != manifest_digest()
            or raw.get('effects') != []
            or type(raw.get('setup_paid_model_calls')) is not int
            or not 0 <= raw['setup_paid_model_calls'] <= 2
            or raw.get('paid_model_calls') != len(expected) + raw['setup_paid_model_calls']):
        return False
    rows, calls, transports = raw.get('cases', []), raw.get('model_calls', []), raw.get('core_transports', [])
    if len(rows) != len(expected) or len(calls) != len(expected) + raw['setup_paid_model_calls']:
        return False
    for case, row in zip(expected, rows, strict=True):
        if (any(row.get(k) != v for k, v in case.items()) or row.get('status') != 'PASS'
                or row.get('findings') != [] or row.get('metrics', {}).get('agent_calls') != 1):
            return False
        attempts = [c for c in calls if c.get('case_id') == case['id']]
        http = [t for t in transports if t.get('case') == case['id']]
        if (len(attempts) != 1 or attempts[0].get('attempted') is not True
                or attempts[0].get('completed') is not True or len(http) != 1
                or http[0].get('status') != 200 or http[0].get('path') != 'ask_dj/message'
):
            return False
        try:
            generated = attempts[0].get('generated_text')
            if not isinstance(generated, str) or len(generated.encode('utf-8', errors='replace')) > 2048:
                return False
            plan = json.loads(generated, object_pairs_hook=unique_object)
        except (ValueError, TypeError, RecursionError):
            return False
        wanted = expected_plan(case)
        if (not isinstance(plan, dict) or set(plan) != set(wanted)
                or any(type(plan[key]) is not type(value) or plan[key] != value for key, value in wanted.items())):
            return False
        if case['read'] == 'artist_tracks':
            actions = http[0].get('body', {}).get('playback_actions', [])
            if ([a.get('uri') for a in actions] != ['spotify:track:' + c * 22 for c in ('e', 'f')]
                    or [a.get('title') for a in actions] != ['Synthetic named recording 2', 'Synthetic named recording 3']
                    or any(not a.get('action_id') for a in actions)):
                return False
    setup = [c for c in calls if c.get('case_id') == 'semantic-start']
    if len(setup) != raw['setup_paid_model_calls'] or any(c.get('completed') is not True for c in setup):
        return False
    return all(r.get('status') == r.get('expected_status') and r.get('cache_control') == 'no-store'
               for r in transports)


def validate_local_report(mode, raw):
    qualification={
        'release_context':'CORE_PAIRED_CURRENT_SELECTED_RELEASE_METADATA_ZERO_MODEL',
        'album_context':'CORE_PAIRED_ALBUM_TRACKS_AND_FROZEN_ALBUM_PLAY',
        'silence_signal':'CORE_PAIRED_SILENCE_LIVE_RECONNECT_ZERO_MODEL',
        'previous':'CORE_PAIRED_INFORMATIONAL_PREVIOUS_NO_EFFECT',
        'output':'REAL_PAIRED_OUTPUT_SELECTION_TRANSFER_EXACT_TARGET',
        'current_artist':'ISOLATED_REAL_HA_TEXT_STT_CURRENT_ARTIST_ZERO_EFFECTS',
        'choice_titles':'ISOLATED_REAL_HA_PAIRED_CATALOG_TITLES',
    }
    required={
        'album_context':{f'album-tracks-{i}' for i in range(5)}|{'album-offer','album-play','album-play-duplicate',
            'album-header-play','album-recording-play'}|{f'album-current-artist-{i}' for i in range(5)}|{'album-offer-'+locale for locale in ('en','de','fr','es')},
        'release_context':{f'release-{i}-{mode}' for i in range(7) for mode in ('current','selected')}|{'release-selected-other-current'},
        'previous':{'baseline-previous-question'},
        'silence_signal':{'silence-start','silence-snapshot','silence-end'},
        'output':{'output-offer','output-select','output-activate','output-track-offer',
                  'output-needs-choice','output-compound-play','output-offline'},
        'current_artist':{'artist-old-clarification-seed','artist-selected-earlier',
                          'artist-state-invariant','artist-pending-proposal',
                          'artist-not-confirmation','artist-provider-unavailable','artist-end-race'},
        'choice_titles':{'titles-'+phase+'-'+locale+'-'+step
                         for phase in ('standalone','session')
                         for locale in ('en','nl','de','fr','es') for step in ('lookup','list')}
    }
    if not isinstance(raw,dict) or raw.get('qualification')!=qualification.get(mode):
        return False
    if raw.get('source_hashes')!=expected_source_hashes() or raw.get('pairing')!='ordinary_device_token_minted_persisted':
        return False
    if mode=='silence_signal' and set(raw.get('live_cases',[]))!={'paired_auth','live_silence','dedup','reconnect_original_expiry','no_speech_budget','session_end'}:
        return False
    rows=raw.get('core_transports')
    if not isinstance(rows,list) or not all(isinstance(r,dict) for r in rows):
        return False
    ids=[r.get('case') for r in rows]
    if len(ids)!=len(set(ids)) or not required[mode].issubset(ids):
        return False
    for row in rows:
        if not isinstance(row.get('path'),str) or not isinstance(row.get('request'),dict) or not isinstance(row.get('body'),dict):
            return False
        expected=403 if row['case']=='artist-other-profile' else (409 if row['case'] in {'artist-end-race','output-offline','titles-ended-list','album-play-duplicate'} else (201 if row['path']=='session/start' else 200))
        if (type(row.get('status')) is not int or type(row.get('expected_status')) is not int
            or row['status']!=expected or row['expected_status']!=expected or row.get('cache_control')!='no-store'):
            return False
        if expected>=400:
            if not isinstance(row['body'].get('error'),str) or not row['body']['error']:
                return False
        elif row['body'].get('success') is not True:
            return False
    if not isinstance(raw.get('model_calls'),list) or raw['model_calls'] or type(raw.get('paid_model_calls')) is not int or raw['paid_model_calls']!=0:
        return False
    if mode == 'album_context':
        from scripts.verification.askdj_example_catalogue_golden import cases, check_response
        by_id = {r['case']:r for r in rows}
        for i,locale in enumerate(('nl','en','de','fr','es')):
            case = next(c for c in cases() if c['entry_id']=='listen.album_tracks' and c['language']==locale)
            if check_response(case, by_id[f'album-tracks-{i}']['body'], []):
                return False
        writes = [c for c in raw.get('provider_calls',[]) if c.get('method') in {'PUT','POST','DELETE'}]
        expected_bodies = [{'context_uri':'spotify:album:'+'b'*22},
            {'uris':['spotify:track:'+'2'*22]}, {'context_uri':'spotify:album:'+'c'*22}]
        if (len(writes)!=3 or [c.get('body') for c in writes]!=expected_bodies
                or any(c.get('method')!='PUT' or c.get('path')!='/me/player/play' for c in writes)):
            return False
    return True


def redacted_full_report(raw):
    calls = raw.get('model_calls', [])
    transports = raw.get('core_transports', [])
    # Every SDK attempt is attached to the actual Core client_message_id. No
    # output text, prompts, payloads, tokens, Profile IDs or routes are retained.
    usage = [{k: r.get(k) for k in ('case_id', 'model', 'attempted', 'completed', 'input_tokens', 'output_tokens')}
             for r in calls]
    by_case = Counter(r.get('case_id') for r in calls)
    rows = []
    invalid = []
    if raw.get('qualification')!='REAL_PAIRED_HA_COMMON_CORE_OPENAI_DIALOGUE_AND_EXACT_TARGET' or raw.get('source_hashes')!=expected_source_hashes():
        invalid.append('profile_or_source_binding')
    required={mode+'-'+step for mode in ('standalone','active','paused')
              for step in ('credit','pronoun','topic','volume','after-volume','search',
                           'refine','select','between-selection','play','after-play')}
    required.update(locale+'-'+persona+'-'+step
                    for locale in ('en','nl','de','fr','es')
                    for persona in ('home_dj','radio_dj','club_dj','festival_dj')
                    for step in ('identity','follow'))
    if not required.issubset({r.get('case') for r in transports}):
        invalid.append('missing_required_dialogue_steps')
    chains=raw.get('mixed_chains',[])
    if {r.get('mode') for r in chains if isinstance(r,dict)}!={'standalone','active','paused'}:
        invalid.append('mixed_contexts_missing')
    styles=raw.get('style_cases',[])
    if {(r.get('language'),r.get('persona')) for r in styles if isinstance(r,dict)}!={
        (locale,persona) for locale in ('en','nl','de','fr','es')
        for persona in ('home_dj','radio_dj','club_dj','festival_dj')}:
        invalid.append('language_persona_combinations_missing')
    if any(not isinstance(r,dict) or not r.get('identity') or not r.get('followup') for r in styles):
        invalid.append('missing_actual_style_answers')
    for item in transports:
        body = item.get('body') or {}
        question_id = (item.get('request') or {}).get('client_message_id') or item['case']
        declared = (body.get('conversation') or {}).get('metrics', {}).get('agent_calls')
        observed = by_case.get(question_id, 0)
        if question_id and declared is not None and declared != observed:
            # A joined duplicate reports the original semantic work, not an extra
            # paid attempt. Its shared message ID must still identify one attempt.
            invalid.append('declared_sdk_mismatch:'+item['case'])
        rows.append({'id': item['case'], 'semantic_case_id': question_id, 'status': item['status'],
                     'expected_status': item.get('expected_status'),
                     'paid_attempts': observed if question_id else 0})
    known_ids = {(item.get('request') or {}).get('client_message_id') or item['case'] for item in transports}
    # Voice uses its existing header/transport ID; include genuinely measured
    # utterance cases separately rather than attributing them to a prior question.
    unmatched = sorted(k for k in by_case if k not in known_ids and k)
    if unmatched:
        invalid.append('unbound_paid_attempt')
    denied_ids = {(item.get('request') or {}).get('client_message_id') or item['case']
                  for item in transports if item.get('status') == item.get('expected_status')
                  and item.get('expected_status') in (403,409)}
    incomplete = [r for r in calls if not r.get('completed')]
    if len(calls) == 0 or len(calls) > 128 or any(r.get('case_id') not in denied_ids for r in incomplete):
        invalid.append('paid_usage_incomplete_or_budget')
    if any(r.get('completed') and (type(r.get('input_tokens')) is not int or r['input_tokens']<=0
                                  or type(r.get('output_tokens')) is not int or r['output_tokens']<=0) for r in calls):
        invalid.append('missing_paid_token_usage')
    if any(r.get('model') != 'gpt-6-luna' or not r.get('case_id') for r in calls):
        invalid.append('paid_model_or_case_binding')
    if len(raw.get('mixed_chains', [])) != 3 or len(raw.get('style_cases', [])) != 20:
        invalid.append('conversation_or_persona_coverage_missing')
    if any(r['status'] != r['expected_status'] for r in rows):
        invalid.append('unexpected_http_outcome')
    return {'status': 'FAIL' if invalid else 'PASS', 'cases': rows, 'usage': usage,
            'paid_attempts': len(calls), 'unknown_usage_expected_denials': len(incomplete),
            'semantic_attempt_counts': dict(by_case), 'unbound_case_ids': unmatched, 'findings': invalid,
            'mixed_contexts': 3, 'language_persona_chains': 20,
            'external_provider_boundary': 'fixture', 'model_boundary': 'real_paid'}


def run(candidate, output):
    if not re.fullmatch('[0-9a-f]{40}', candidate):
        raise ValueError('invalid_candidate_sha')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() != candidate:
        raise ValueError('candidate_mismatch')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):
        raise ValueError('dirty_checkout')
    result = {'schema_version': 1, 'suite': 'askdj_release_matrix_v1',
              'candidate_sha': candidate, 'status': 'FAIL', 'profiles': [],
              'native_installed_hardware': 'NOT_RUN', 'inventory': validate_inventory()}
    # Failure evidence exists even when admission/credential/provider fails.
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(result, indent=2)+'\n')
    save()
    inventory=json.loads((ROOT/'docs/verification/fixtures/askdj_golden_release_matrix_v1.json').read_text())
    try:
        validate_owner_pattern_coverage(inventory)
    except ValueError as exc:
        result['findings']=[str(exc)]
        save()
        return 1
    with TemporaryDirectory(prefix='djc-release-matrix-') as tmp:
        temp = Path(tmp)
        for i, pattern in enumerate(TEST_PATTERNS):
            directory=temp/('unit'+str(i))
            directory.mkdir()
            renderer = pattern == 'test_vibecast_renderer.py'
            code = (host_renderer_run(directory) if renderer else owned_run(
                [IMAGE, '/candidate/tools/verification/run_askdj_owner_contracts.py', pattern, '/lab/owner-contracts.json'],
                payload={},directory=directory,seconds=240,network='none'))
            proof=directory/'owner-contracts.json'
            # No receipt means unknown execution, not an observed zero-test run.
            # Publish only the bounded exit code and a fixed diagnostic category.
            unit=json.loads(proof.read_text()) if proof.is_file() else {
                'status': 'FAIL', 'tests_run': None, 'runner_exit_code': code,
                'findings': ['owner_contract_receipt_missing'],
            }
            if renderer:
                unit['network']='host_available_not_used_by_renderer_fixtures'
                unit['execution_runtime']='host_python_node'
                unit['ha_runtime']='NOT_CLAIMED'
            else:
                unit['execution_runtime']='pinned_ha_container'
            result['profiles'].append({'id': pattern, 'kind': 'deterministic_owner_contract',
                                       **unit, 'status': 'PASS' if code == 0 and unit.get('status')=='PASS' else 'FAIL'})
            save()
            if code or unit.get("status")!="PASS":
                return 1
        # Named bindings must actually execute, not merely exist in source.
        bindings=required_bindings(inventory)
        executed=[name for p in result['profiles'] for name in p.get('executed',[])]
        if any(not any(name.startswith(Path(b['file']).stem+'.') and name.endswith('.'+b['method'])
                       for name in executed) for b in bindings):
            result['findings']=['named_owning_binding_not_executed']
            save()
            return 1
        qa=json.loads((ROOT/'examples/ask_dj_e2e_cases.json').read_text())
        outcomes={c['id']:c['status'] for p in result['profiles'] for c in p.get('case_outcomes',[])}
        if any(outcomes.get(case['id'])!='PASS' for case in qa):
            result['findings']=['missing_or_failed_single_turn_question_answer']
            save()
            return 1
        proactive=validate_moment_matrix()
        if any(outcomes.get(case)!='PASS' for case in proactive):
            result['findings']=['missing_or_failed_proactive_persona_mood_case']
            save()
            return 1
        result['executed_proactive_cases']=len(proactive)
        result['executed_single_turn_cases']=len(qa)
        result['executed_help_cases']=sum(c['id'].startswith('help_prompt_') for c in qa)
        result['reported_issues']=len(inventory['reported_issues'])
        if blockers := release_blockers(inventory):
            # Do not spend model credits rerunning a known rejected candidate.
            result['findings']=['open_core_qualification:'+item for item in blockers]
            save()
            return 1
        save()
        for mode, (filename, limit) in PROFILES.items():
            directory=temp/mode
            directory.mkdir()
            paid=mode in {'full_golden','contextual_golden','mood_prosody','semantic_reads','catalogue_golden','catalogue_variations'}
            key=os.environ.get('DJCONNECT_GOLDEN_OPENAI_API_KEY','') if paid else 'unused-networkless-probe'
            if not key or len(key)>8192:
                result['profiles'].append({'id':mode,'status':'FAIL','findings':['credential_missing']})
                save()
                return 1
            flags = ['-e','DJC_SAFETY_PROBE='+mode]
            payload = {'api_key':key,'model':'gpt-6-luna','max_tokens':700}
            if mode in {'catalogue_golden','catalogue_variations'}:
                from scripts.verification.askdj_example_catalogue_golden import MAX_OUTPUT_TOKENS
                payload['max_tokens'] = MAX_OUTPUT_TOKENS
            if mode == 'catalogue_variations':
                corpus_path=ROOT/'docs/verification/fixtures/askdj_catalogue_variations_v1.json'
                from tools.verification.askdj_catalogue_variations import cases as variation_cases
                try:
                    if not corpus_path.is_file() or corpus_path.stat().st_size > 256*1024:
                        raise ValueError('frozen_variation_corpus_missing_or_oversized')
                    corpus=json.loads(corpus_path.read_text())
                    variation_cases(corpus)
                except (ValueError, TypeError, KeyError):
                    result['profiles'].append({'id':mode,'status':'FAIL',
                        'findings':['qualified_frozen_variation_corpus_required_after_base_PASS']})
                    save()
                    return 1
                payload['variation_corpus']=corpus
                flags=['-e','DJC_SAFETY_PROBE=catalogue_golden']
            if mode == 'mood_prosody':
                tts_model = os.environ.get('DJCONNECT_GOLDEN_TTS_MODEL', 'gpt-4o-mini-tts')
                if tts_model != 'gpt-4o-mini-tts':
                    result['profiles'].append({'id':mode,'status':'FAIL','findings':['qualified_tts_model_configuration_missing']})
                    save()
                    return 1
                payload['tts_settings'] = {'chat_model': tts_model}
                flags = ['-e','DJC_SAFETY_PROBE=literal_tts','-e','DJC_MOOD_PROSODY=1',
                         '-e','DJC_PROSODY_FIVE_LANGUAGES=1']
            code=owned_run([*flags, IMAGE,
                            '/candidate/scripts/verification/verify_ask_dj_contextual_dialogue_http.py'],
                           payload=payload,
                           directory=directory,seconds=limit,network='bridge' if paid else 'none')
            path=directory/filename
            if not path.is_file() or path.stat().st_size>8*1024*1024:
                row={'id':mode,'status':'FAIL','findings':['receipt_missing_or_oversized']}
            else:
                raw=json.loads(path.read_text())
                if mode=='mood_prosody':
                    row={'id':mode,'status':'PASS' if validate_prosody_report(raw, directory) else 'FAIL',
                         'paid_tts_attempts':raw.get('paid_tts_attempts'),
                         'kind':'real_paired_ha_and_provider_prosody', 'audible_acceptance':'NOT_RUN',
                         'mood_prosody':raw.get('mood_prosody', [])}
                elif mode=='full_golden':
                    row={'id':mode,**redacted_full_report(raw)}
                elif mode=='contextual_golden':
                    raw['candidate_sha']=candidate
                    row={k:raw.get(k) for k in ('cases','manifest_sha256','paid_model_calls','usage')}
                    row.update(id=mode,status='PASS' if validate_report(raw,candidate) else 'FAIL')
                elif mode=='catalogue_golden':
                    from scripts.verification.askdj_example_catalogue_golden import validate_report as validate_catalogue
                    row={'id':mode,'status':'PASS' if validate_catalogue(raw, source_hashes=expected_source_hashes()) else 'FAIL',
                         'paid_attempts':raw.get('paid_model_calls'), 'kind':'real_paired_ha_exact_catalogue_questions',
                         'case_count':len(raw.get('cases',[])), 'manifest_sha256':raw.get('manifest_sha256'),
                         'failed_cases':[{'id':r.get('id'),'findings':r.get('findings',[])}
                                         for r in raw.get('cases',[]) if r.get('status')!='PASS'],
                         'native':'NOT_RUN','installed':'NOT_RUN'}
                elif mode=='catalogue_variations':
                    from scripts.verification.askdj_example_catalogue_golden import validate_variation_report
                    row={'id':mode,'status':'PASS' if validate_variation_report(raw,
                        corpus=corpus,source_hashes=expected_source_hashes()) else 'FAIL',
                        'paid_attempts':raw.get('paid_model_calls'),'kind':'real_paired_ha_frozen_question_variations',
                        'case_count':len(raw.get('cases',[])),'manifest_sha256':raw.get('manifest_sha256'),
                        'failed_cases':[{'id':r.get('id'),'findings':r.get('findings',[])}
                            for r in raw.get('cases',[]) if r.get('status')!='PASS'],
                        'native':'NOT_RUN','installed':'NOT_RUN'}
                elif mode=='semantic_reads':
                    row={'id':mode,'status':'PASS' if validate_semantic_report(raw) else 'FAIL',
                         'paid_attempts':raw.get('paid_model_calls'), 'kind':'real_paired_ha_semantic_interpretation',
                         'native':'NOT_RUN','installed':'NOT_RUN'}
                else:
                    calls=raw.get('model_calls',[])
                    paid_calls=raw.get('paid_model_calls',len(calls))
                    row={'id':mode,'status':'PASS' if validate_local_report(mode,raw) else 'FAIL',
                         'paid_attempts':paid_calls,
                         'external_agent_fixture_count':len(raw.get('agent_provider_fixtures',[])),
                         'actual_http_cases':len(raw.get('core_transports',[])),
                         'kind':'real_paired_ha_zero_paid_model'}
                if code:
                    row['status']='FAIL'
            result['profiles'].append(row)
            save()
            if row['status']!='PASS':
                return 1
        result['status']='PASS'
        save()
        return 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-sha',required=True)
    parser.add_argument('--report-path',type=Path,required=True)
    args=parser.parse_args()
    return run(args.candidate_sha,args.report_path)


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('ASKDJ_RELEASE_MATRIX=FAIL:'+type(exc).__name__,file=sys.stderr)
        raise SystemExit(1) from None
