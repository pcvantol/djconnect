"""Offline native Golden inventory/plan/evidence grammar; never execution authority."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
CONTRACT = 'native_client_golden_v1'
CLIENTS = ('iphone', 'ipad', 'mac', 'watch')
LOCALES = ('en', 'nl')
MATRIX = 'docs/verification/fixtures/askdj_golden_release_matrix_v1.json'
HELP = 'custom_components/djconnect/ask_dj/examples_v1.json'
MOMENTS = 'docs/verification/fixtures/dj_moment_persona_mood_golden_v1.json'
PROOFS = (
    'examples/client_contracts/session_for_you_v1/actual-ha-mood-refresh-20261106.json',
    'examples/client_contracts/session_for_you_v1/actual-ha-output-readback-20261106.json',
    'examples/client_contracts/music_announcement_v1/actual-ha-wire.json',
)
BINDINGS = ('core_install', 'fixture_owner', 'provider_coverage', 'owner_authorization', 'cumulative_budget')
POLICIES = {'zero': (0, 0), 'one_or_two': (1, 2), 'zero_or_one': (0, 1),
            'zero_or_one_or_two': (0, 2), 'two': (2, 2)}


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def closed(value, keys, reason):
    require(type(value) is dict and set(value) == set(keys), reason)


def sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def positive(value, limit, *, zero=False):
    return type(value) is int and (0 if zero else 1) <= value <= limit


def inventory(root=ROOT):
    matrix = json.loads((root / MATRIX).read_text())
    help_data = json.loads((root / HELP).read_text())
    moments = json.loads((root / MOMENTS).read_text())
    inputs = [MATRIX, matrix['existing_single_turn_cases'], HELP, MOMENTS,
              'docs/verification/NATIVE_CLIENT_GOLDEN_CONTRACT_V1.md',
              'tools/verification/native_client_golden_contract.py',
              'scripts/verification/askdj_example_catalogue_golden.py', *PROOFS]
    require(all(not Path(p).is_absolute() and '..' not in Path(p).parts
                and (root / p).resolve().is_relative_to(root.resolve()) for p in inputs), 'unsafe_source_path')
    from scripts.verification.askdj_example_catalogue_golden import cases as questions, chain_cases
    catalogue_cases = {c['id']: c for c in questions(root) + chain_cases(root)}
    cases = []
    for family in matrix['families']:
        for step in family['steps']:
            language = step.get('language')
            original = catalogue_cases.get(step['id'])
            if original:
                require(step['question'] == original['question']
                        and language == original['language']
                        and step['expected_answer'] == original['expected']['answer']
                        and step['model_policy'] == original['model_policy'], 'canonical_catalogue_matrix_drift')
            cases.append({'source': MATRIX, 'id': step['id'], 'family': family['id'],
                'language': language, 'question': step['question'],
                'expected': step['expected_answer'], 'model_policy': step['model_policy'],
                'kind': 'canonical_step', 'requires': [], 'entry_id': step.get('entry_id'),
                'driver': 'ordinary_ask_dj_flow' if step['id'] in catalogue_cases else None,
                'expected_route_effect': catalogue_cases.get(step['id'], {}).get('expected'),
                'native_mapping': 'PENDING_EXPLICIT_LOCALE' if language is None else
                    'SOURCE_BOUND_ORDINARY_ASK_DJ' if language in LOCALES and step.get('execution_profile') == 'catalogue_golden'
                    else 'PENDING_NATIVE_OWNER_MAPPING' if language in LOCALES else 'OUTSIDE_SELECTED_LOCALES'})
    for entry in help_data['entries']:
        for language in LOCALES:
            cases.append({'source': HELP, 'id': entry['id'], 'family': entry['group'],
                'language': language, 'question': entry['templates'][language],
                'expected': {'advertised_route': entry['route'], 'advertised_intent': entry['intent'],
                             'on_explicit_send_effect': entry['effect'], 'observation_effect': 'none',
                             'safety': entry['safety']},
                'model_policy': None, 'kind': 'help_observation', 'requires': entry['requires'],
                'entry_id': entry['id'], 'driver': 'ordinary_paired_help_get', 'expected_route_effect': None,
                'native_mapping': 'SOURCE_BOUND_PURE_HELP_GET'})
    for cell in moments['cells']:
        for family in (*moments['families'], 'music-only'):
            cases.append({'source': MOMENTS, 'id': cell['id'] + '-' + family,
                'family': family, 'language': cell['language'], 'question': None,
                'expected': {'cell': cell, 'family': moments['families'].get(family)},
                'model_policy': None, 'kind': 'session_contribution', 'requires': ['admitted_original_session'],
                'entry_id': None, 'driver': None, 'expected_route_effect': None,
                'native_mapping': 'PENDING_NATIVE_OWNER_MAPPING' if cell['language'] in LOCALES
                    else 'OUTSIDE_SELECTED_LOCALES'})
    for path in PROOFS:
        record = json.loads((root / path).read_text())
        outcomes = record.get('cases') or record['receipt']['extension']['cases']
        for name in outcomes:
            cases.append({'source': path, 'id': name, 'family': 'existing_producer_contract',
                'language': None, 'question': None, 'expected': {'original_assertion': name},
                'model_policy': None, 'kind': 'producer_fixture',
                'entry_id': None, 'driver': None, 'expected_route_effect': None,
                'requires': ['real_disposable_fixture_not_offline_receipt'],
                'native_mapping': 'PENDING_EXPLICIT_NATIVE_DRIVER'})
    keys = [(c['source'], c['id'], c['language']) for c in cases]
    require(len(set(keys)) == len(keys), 'duplicate_source_case')
    return {'schema_version': 1, 'contract_id': CONTRACT, 'qualification': 'SOURCE_PROTOCOL_ONLY',
        'execute': False, 'clients': list(CLIENTS), 'selected_languages': list(LOCALES),
        'source_pins': {p: digest((root / p).read_bytes()) for p in inputs}, 'cases': cases,
        'coverage': {'canonical_families': len(matrix['families']),
            'canonical_steps': sum(len(f['steps']) for f in matrix['families']),
            'help_entry_locale_rows': len(help_data['entries']) * len(LOCALES),
            'moment_cases': len(moments['cells']) * (len(moments['families']) + 1),
            'mapping_states': dict(Counter(c['native_mapping'] for c in cases))}}


def case_key(case):
    require(type(case.get('source')) is str and 0 < len(case['source']) <= 512
            and type(case.get('id')) is str and 0 < len(case['id']) <= 256
            and (case.get('language') is None or type(case['language']) is str), 'invalid_case_reference')
    return (case['source'], case['id'], case['language'])


def plan_check(plan, catalogue, *, expected_receipts, expected_app_receipts, root=ROOT):
    """Independent expected pins are mandatory; even valid input is not a grant."""
    require(catalogue == inventory(root), 'unverified_or_mutated_inventory')
    closed(plan, ('schema_version', 'contract_id', 'inventory_sha256', 'run_id', 'clients',
                  'receipts', 'app_receipts', 'starts_at', 'expires_at', 'budget', 'retry_automatically', 'cases'),
           'open_plan_schema')
    require(type(plan['schema_version']) is int and plan['schema_version'] == 1
            and plan['contract_id'] == CONTRACT and plan['inventory_sha256'] == digest(canonical(catalogue)),
            'changed_inventory_or_contract')
    require(type(plan['run_id']) is str and str(uuid.UUID(plan['run_id'])) == plan['run_id'], 'invalid_run_id')
    require(type(plan['clients']) is list and plan['clients'] == list(CLIENTS), 'incomplete_client_set')
    require(plan['retry_automatically'] is False, 'retry_not_admitted')
    closed(plan['receipts'], BINDINGS, 'receipt_schema')
    closed(expected_receipts, BINDINGS, 'independent_receipts_required')
    require(all(sha(plan['receipts'][k]) and plan['receipts'][k] == expected_receipts[k] for k in BINDINGS),
            'receipt_origin_mismatch')
    closed(plan['app_receipts'], CLIENTS, 'app_receipt_schema')
    closed(expected_app_receipts, CLIENTS, 'independent_app_receipts_required')
    require(all(sha(v) for v in plan['app_receipts'].values())
            and plan['app_receipts'] == expected_app_receipts, 'missing_or_wrong_client_binary_receipt')
    starts, expires = (datetime.fromisoformat(plan[k]) for k in ('starts_at', 'expires_at'))
    require(starts.utcoffset() is not None and expires.utcoffset() is not None
            and 0 < (expires - starts).total_seconds() <= 600, 'invalid_lifetime')
    budget = plan['budget']
    closed(budget, ('provider_attempts', 'attempts_per_turn', 'output_tokens_per_attempt', 'audio_actions',
                    'grant_id_sha256', 'cumulative_attempt_limit', 'previously_reserved_attempts'),
           'open_budget_schema')
    require(positive(budget['provider_attempts'], 40, zero=True)
            and positive(budget['attempts_per_turn'], 2)
            and positive(budget['output_tokens_per_attempt'], 3000)
            and positive(budget['audio_actions'], 40, zero=True)
            and sha(budget['grant_id_sha256'])
            and positive(budget['cumulative_attempt_limit'], 10**6, zero=True)
            and positive(budget['previously_reserved_attempts'], budget['cumulative_attempt_limit'], zero=True)
            and budget['previously_reserved_attempts'] + budget['provider_attempts'] <= budget['cumulative_attempt_limit'],
            'budget_outside_existing_observer_contract')
    require(digest(canonical(budget)) == expected_receipts['cumulative_budget'], 'changed_cumulative_budget_snapshot')
    known = {case_key(c): c for c in catalogue['cases']}
    require(type(plan['cases']) is list and 0 < len(plan['cases']) <= 40, 'empty_or_unbounded_case_selection')
    selected, blockers = set(), []
    for case in plan['cases']:
        closed(case, ('source', 'id', 'language', 'client', 'question_sha256', 'model_policy_sha256'),
               'open_case_schema')
        key = case_key(case)
        require(key in known and case['language'] in LOCALES and case['client'] in CLIENTS, 'unknown_case_or_locale')
        identity = (*key, case['client'])
        require(identity not in selected, 'duplicate_case_client')
        selected.add(identity)
        original = known[key]
        require(case['question_sha256'] == digest(canonical(original['question']))
                and case['model_policy_sha256'] == digest(canonical(original['model_policy'])), 'changed_question_or_policy')
        if not original['native_mapping'].startswith('SOURCE_BOUND_'):
            blockers.append({'source': case['source'], 'id': case['id'], 'language': case['language'],
                             'client': case['client'], 'reason': original['native_mapping']})
        if original['kind'] != 'help_observation' and original['model_policy'] not in POLICIES:
            blockers.append({'source': case['source'], 'id': case['id'], 'language': case['language'],
                             'client': case['client'], 'reason': 'UNQUALIFIED_TYPED_MODEL_POLICY'})
    require({c['client'] for c in plan['cases']} == set(CLIENTS), 'missing_client_case_coverage')
    return {'schema_version': 1, 'contract_id': CONTRACT, 'execute': False,
        'qualification': 'DRAFT_NOT_ADMITTED', 'plan_sha256': digest(canonical(plan)),
        'selected_case_clients': len(selected), 'blockers': blockers,
        'runtime_fixture_provider_native_qualification': 'NOT_GRANTED',
        'coverage_scope': 'SELECTED_CASE_CLIENTS_ONLY',
        'missing_live_gates': ['INSTALLED_ADAPTER_ORIGIN', 'REAL_DISPOSABLE_FIXTURE',
            'CUMULATIVE_OPERATOR_GRANT', 'ALL_PROVIDER_TRANSPORT_COVERAGE', 'NATIVE_EXECUTION_AND_REVIEW']}


def reconcile(plan, evidence, catalogue, *, expected_receipts, expected_app_receipts, root=ROOT):
    """Closed privacy-safe projection, never a native PASS or release authority."""
    checked = plan_check(plan, catalogue, expected_receipts=expected_receipts,
                         expected_app_receipts=expected_app_receipts, root=root)
    closed(evidence, ('schema_version', 'run_id', 'plan_sha256', 'receipts', 'unattributed_attempts', 'cases'),
           'open_evidence_schema')
    require(type(evidence['schema_version']) is int and evidence['schema_version'] == 1
            and evidence['run_id'] == plan['run_id'] and evidence['plan_sha256'] == checked['plan_sha256'],
            'evidence_run_mismatch')
    require(evidence['receipts'] == expected_receipts and evidence['unattributed_attempts'] == 0
            and type(evidence['unattributed_attempts']) is int, 'unattributed_or_wrong_origin')
    expected = {(*case_key(c), c['client']): c for c in plan['cases']}
    seen, provider_receipts, attempts, public = set(), set(), 0, []
    require(type(evidence['cases']) is list, 'invalid_case_evidence')
    for row in evidence['cases']:
        closed(row, ('source', 'id', 'language', 'client', 'client_message_sha256', 'server_object_sha256',
                     'answer_projection_sha256', 'history_sha256', 'session_entry_sha256',
                     'provider_attempts', 'provider_terminal', 'provider_receipt_sha256', 'model_sha256',
                     'input_tokens', 'output_tokens', 'semantic', 'effect', 'native'), 'unsafe_case_export')
        key = (*case_key(row), row['client'])
        require(key in expected and key not in seen, 'unknown_duplicate_or_wrong_client_evidence')
        seen.add(key)
        original = next(c for c in catalogue['cases'] if case_key(c) == case_key(row))
        require(all(sha(row[k]) for k in ('client_message_sha256', 'server_object_sha256',
                                         'answer_projection_sha256')), 'missing_original_request_projection_binding')
        if original['kind'] == 'help_observation':
            require(row['history_sha256'] is None and row['session_entry_sha256'] is None, 'help_read_cannot_claim_history_write')
        else:
            require(sha(row['history_sha256']) and sha(row['session_entry_sha256']),
                    'missing_original_turn_history_projection_binding')
        count = row['provider_attempts']
        require(positive(count, plan['budget']['attempts_per_turn'], zero=True), 'attempt_limit')
        policy = 'zero' if original['kind'] == 'help_observation' else original['model_policy']
        if policy in POLICIES:
            low, high = POLICIES[policy]
            require(low <= count <= high, 'canonical_model_attempt_policy')
        require(row['provider_terminal'] in {'complete', 'failed', 'unknown', 'not_used'}, 'invalid_terminal')
        require((count == 0) == (row['provider_terminal'] == 'not_used'), 'terminal_count_mismatch')
        if count == 0:
            require(row['provider_receipt_sha256'] is None and row['model_sha256'] is None
                    and type(row['input_tokens']) is int and row['input_tokens'] == 0
                    and type(row['output_tokens']) is int and row['output_tokens'] == 0, 'zero_model_cannot_claim_provider_usage')
        else:
            require(sha(row['provider_receipt_sha256']), 'missing_provider_attempt_origin')
            require(row['provider_receipt_sha256'] not in provider_receipts, 'reused_provider_receipt')
            provider_receipts.add(row['provider_receipt_sha256'])
            if row['provider_terminal'] == 'complete':
                require(sha(row['model_sha256']) and positive(row['input_tokens'], 10**9, zero=True)
                        and positive(row['output_tokens'], count * plan['budget']['output_tokens_per_attempt'], zero=True),
                        'missing_terminal_model_or_usage')
            else:
                require((row['model_sha256'] is None or sha(row['model_sha256']))
                        and all(v is None or positive(v, 10**9, zero=True)
                                for v in (row['input_tokens'], row['output_tokens'])), 'invalid_partial_usage')
        require(all(row[k] in {'PASS', 'FAIL', 'NOT_REVIEWED'} for k in ('semantic', 'effect', 'native')),
                'invalid_independent_verdict')
        attempts += count
        public.append(row.copy())
    require(attempts <= plan['budget']['provider_attempts'], 'cumulative_batch_limit')
    return {'schema_version': 1, 'contract_id': CONTRACT, 'execute': False,
        'qualification': 'EVIDENCE_PENDING_INDEPENDENT_REVIEW', 'run_id': plan['run_id'],
        'plan_sha256': checked['plan_sha256'], 'complete_selected_set': seen == set(expected),
        'observed_provider_attempts': attempts, 'cases': public,
        'all_supplied_verdicts_pass': bool(public) and all(
            r['provider_terminal'] in {'complete', 'not_used'}
            and all(r[k] == 'PASS' for k in ('semantic', 'effect', 'native')) for r in public),
        'blockers': checked['blockers'], 'native_release_authority': 'NOT_GRANTED'}


def read_json(path):
    """Bound external records before decoding; duplicate keys/nonfinite values fail."""
    require(path.stat().st_size <= 4 * 1024 * 1024, 'record_too_large')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError('nonfinite_json')
    return json.loads(path.read_text(), object_pairs_hook=unique, parse_constant=nonfinite)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--expected-receipts', type=Path)
    parser.add_argument('--expected-app-receipts', type=Path)
    args = parser.parse_args()
    if args.evidence and not args.plan:
        parser.error('--evidence requires --plan')
    if args.plan and not (args.expected_receipts and args.expected_app_receipts):
        parser.error('plan checks require independent expected receipt pin maps')
    catalogue = inventory()
    if args.plan:
        plan = read_json(args.plan)
        pins = read_json(args.expected_receipts)
        apps = read_json(args.expected_app_receipts)
        result = (reconcile(plan, read_json(args.evidence), catalogue, expected_receipts=pins,
                            expected_app_receipts=apps) if args.evidence else
                  plan_check(plan, catalogue, expected_receipts=pins, expected_app_receipts=apps))
    else:
        result = catalogue
    data = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(data)
    print(json.dumps({'inventory_sha256': digest(canonical(catalogue)),
                      'coverage': catalogue['coverage'], 'execute': False,
                      'qualification': result['qualification']}, sort_keys=True))


if __name__ == '__main__':
    main()
