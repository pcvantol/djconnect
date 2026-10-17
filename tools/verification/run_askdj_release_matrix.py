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
from tools.verification.run_askdj_contextual_release_gate import IMAGE, validate_report  # noqa: E402
from tools.verification.askdj_release_inventory import validate as validate_inventory  # noqa: E402

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
                    row={'id':mode,'status':'PASS' if not calls and paid_calls==0 else 'FAIL',
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
