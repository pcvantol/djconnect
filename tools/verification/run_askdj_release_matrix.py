"""Full reactive release matrix: deterministic contracts + isolated HA + paid dialogue."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_askdj_contextual_release_gate import IMAGE, validate_report  # noqa: E402
from askdj_release_inventory import validate as validate_inventory  # noqa: E402

# Existing owning interpretation/authorization/transport suites. These use explicit
# agent/provider fixtures; their PASS is not paid-model or physical acceptance.
TEST_PATTERNS = (
    'test_ask_dj*.py', 'test_askdj_contextual_release_gate.py', 'test_voice_intents.py', 'test_http_voice_helpers.py',
    'test_music_dna*.py', 'test_session_conversation*.py',
)
PROFILES = {
    'current_artist': ('current-artist.json', 240),
    'previous': ('previous-safety-fixed.json', 240),
    'output': ('output-safety-fixed.json', 240),
    'choice_titles': ('choice-titles.json', 240),
    'release_context': ('release-context.json', 240),
    'full_golden': ('dialogue.json', 1500),
    'contextual_golden': ('golden-contextual.json', 600),
}


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
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def validate_local_report(mode, raw):
    qualification={
        'release_context':'CORE_PAIRED_CURRENT_SELECTED_RELEASE_METADATA_ZERO_MODEL',
        'previous':'CORE_PAIRED_INFORMATIONAL_PREVIOUS_NO_EFFECT',
        'output':'REAL_PAIRED_OUTPUT_SELECTION_TRANSFER_EXACT_TARGET',
        'current_artist':'ISOLATED_REAL_HA_TEXT_STT_CURRENT_ARTIST_ZERO_EFFECTS',
        'choice_titles':'ISOLATED_REAL_HA_PAIRED_CATALOG_TITLES',
    }
    required={
        'release_context':{f'release-{i}-{mode}' for i in range(7) for mode in ('current','selected')}|{'release-selected-other-current'},
        'previous':{'baseline-previous-question'},
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
    rows=raw.get('core_transports')
    if not isinstance(rows,list) or not all(isinstance(r,dict) for r in rows):
        return False
    ids=[r.get('case') for r in rows]
    if len(ids)!=len(set(ids)) or not required[mode].issubset(ids):
        return False
    if any(r.get('status')!=r.get('expected_status') or r.get('cache_control')!='no-store' for r in rows):
        return False
    if raw.get('model_calls',[]) or raw.get('paid_model_calls',0)!=0:
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
    with TemporaryDirectory(prefix='djc-release-matrix-') as tmp:
        temp = Path(tmp)
        for i, pattern in enumerate(TEST_PATTERNS):
            directory=temp/('unit'+str(i));directory.mkdir()
            code = owned_run([IMAGE, '/candidate/tools/verification/run_askdj_owner_contracts.py', pattern, '/lab/owner-contracts.json'],
                             payload={},directory=directory,seconds=240,network='none')
            proof=directory/'owner-contracts.json'
            unit=json.loads(proof.read_text()) if proof.is_file() else {'status':'FAIL','tests_run':0}
            result['profiles'].append({'id': pattern, 'kind': 'deterministic_owner_contract',
                                       **unit, 'status': 'PASS' if code == 0 and unit.get('status')=='PASS' else 'FAIL'})
            save()
            if code or unit.get("status")!="PASS":
                return 1
        # Named bindings must actually execute, not merely exist in source.
        inventory=json.loads((ROOT/'docs/verification/fixtures/askdj_golden_release_matrix_v1.json').read_text())
        bindings=list(inventory['additional_route_contracts'].values())
        for family in inventory['families']:
            bindings.extend(family['owning_tests'])
        executed=[name for p in result['profiles'] for name in p.get('executed',[])]
        if any(not any(name.startswith(Path(b['file']).stem+'.') and name.endswith('.'+b['method'])
                       for name in executed) for b in bindings):
            result['findings']=['named_owning_binding_not_executed'];save();return 1
        qa=json.loads((ROOT/'examples/ask_dj_e2e_cases.json').read_text())
        outcomes={c['id']:c['status'] for p in result['profiles'] for c in p.get('case_outcomes',[])}
        if any(outcomes.get(case['id'])!='PASS' for case in qa):
            result['findings']=['missing_or_failed_single_turn_question_answer'];save();return 1
        result['executed_single_turn_cases']=len(qa)
        result['executed_help_cases']=sum(c['id'].startswith('help_prompt_') for c in qa)
        save()
        for mode, (filename, limit) in PROFILES.items():
            directory=temp/mode;directory.mkdir()
            paid=mode in {'full_golden','contextual_golden'}
            key=os.environ.get('DJCONNECT_GOLDEN_OPENAI_API_KEY','') if paid else 'unused-networkless-probe'
            if not key or len(key)>8192:
                result['profiles'].append({'id':mode,'status':'FAIL','findings':['credential_missing']});save();return 1
            code=owned_run(['-e','DJC_SAFETY_PROBE='+mode, IMAGE,
                            '/candidate/scripts/verification/verify_ask_dj_contextual_dialogue_http.py'],
                           payload={'api_key':key,'model':'gpt-6-luna','max_tokens':700},
                           directory=directory,seconds=limit,network='bridge' if paid else 'none')
            path=directory/filename
            if not path.is_file() or path.stat().st_size>8*1024*1024:
                row={'id':mode,'status':'FAIL','findings':['receipt_missing_or_oversized']}
            else:
                raw=json.loads(path.read_text())
                if mode=='full_golden':
                    row={'id':mode,**redacted_full_report(raw)}
                elif mode=='contextual_golden':
                    raw['candidate_sha']=candidate
                    row={k:raw.get(k) for k in ('cases','manifest_sha256','paid_model_calls','usage')}
                    row.update(id=mode,status='PASS' if validate_report(raw,candidate) else 'FAIL')
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
            result['profiles'].append(row);save()
            if row['status']!='PASS':
                return 1
        result['status']='PASS';save();return 0


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
