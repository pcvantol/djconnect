"""Fast provider/native-free regressions; synthetic pins never admit a live run."""
from copy import deepcopy
import json
import unittest

from tools.verification import native_client_golden_contract as contract


class NativeClientGoldenContractTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = contract.inventory()
        self.receipts = {key: contract.digest('synthetic-independent-' + key) for key in contract.BINDINGS}
        self.app_receipts = {client: contract.digest('synthetic-binary-' + client) for client in contract.CLIENTS}
        self.plan = self.make_plan(next(c for c in self.catalogue['cases']
                                       if c['kind'] == 'help_observation' and c['language'] == 'en'))

    def make_plan(self, source):
        result = {'schema_version': 1, 'contract_id': contract.CONTRACT,
            'inventory_sha256': contract.digest(contract.canonical(self.catalogue)),
            'run_id': '00000000-0000-4000-8000-000000000001', 'clients': list(contract.CLIENTS),
            'receipts': self.receipts.copy(),
            'app_receipts': self.app_receipts.copy(),
            'starts_at': '2026-11-06T12:00:00+00:00', 'expires_at': '2026-11-06T12:10:00+00:00',
            'budget': {'provider_attempts': 0, 'attempts_per_turn': 2,
                       'output_tokens_per_attempt': 3000, 'audio_actions': 0,
                       'grant_id_sha256': contract.digest('synthetic-stable-grant'),
                       'cumulative_attempt_limit': 40, 'previously_reserved_attempts': 0},
            'retry_automatically': False, 'cases': [
                {k: source[k] for k in ('source', 'id', 'language')} | {
                    'client': client, 'question_sha256': contract.digest(contract.canonical(source['question'])),
                    'model_policy_sha256': contract.digest(contract.canonical(source['model_policy']))}
                for client in contract.CLIENTS]}
        self.bind_budget(result)
        return result

    def bind_budget(self, plan):
        # Synthetic independent expected snapshot; never a live spending grant.
        self.receipts['cumulative_budget'] = contract.digest(contract.canonical(plan['budget']))
        plan['receipts'] = self.receipts.copy()

    def check(self, plan=None, catalogue=None, expected=None):
        return contract.plan_check(plan or self.plan, catalogue or self.catalogue,
                                   expected_receipts=self.receipts if expected is None else expected,
                                   expected_app_receipts=self.app_receipts)

    def evidence(self, plan=None):
        plan = plan or self.plan
        return {'schema_version': 1, 'run_id': plan['run_id'],
            'plan_sha256': contract.digest(contract.canonical(plan)), 'receipts': self.receipts.copy(),
            'unattributed_attempts': 0, 'cases': [
                {k: c[k] for k in ('source', 'id', 'language', 'client')} | {
                    'client_message_sha256': contract.digest('synthetic-request-' + c['client']),
                    'server_object_sha256': contract.digest('synthetic-server-' + c['client']),
                    'answer_projection_sha256': contract.digest('synthetic-projection-' + c['client']),
                    'history_sha256': None, 'session_entry_sha256': None,
                    'provider_attempts': 0, 'provider_terminal': 'not_used',
                    'provider_receipt_sha256': None, 'model_sha256': None,
                    'input_tokens': 0, 'output_tokens': 0,
                    'semantic': 'NOT_REVIEWED', 'effect': 'NOT_REVIEWED', 'native': 'NOT_REVIEWED'}
                for c in plan['cases']]}

    def reconcile(self, evidence, plan=None):
        return contract.reconcile(plan or self.plan, evidence, self.catalogue,
                                  expected_receipts=self.receipts, expected_app_receipts=self.app_receipts)

    def test_complete_current_matrix_not_the_old_167_step_catalogue(self):
        matrix = json.loads((contract.ROOT / contract.MATRIX).read_text())
        rows = [c for c in self.catalogue['cases'] if c['source'] == contract.MATRIX]
        source = {s['id']: s for f in matrix['families'] for s in f['steps']}
        self.assertEqual(len(rows), 385)
        self.assertEqual({c['id'] for c in rows}, set(source))
        for row in rows:
            self.assertEqual(row['question'], source[row['id']]['question'])
            self.assertEqual(row['model_policy'], source[row['id']]['model_policy'])
            self.assertEqual(row['language'], source[row['id']].get('language'))
        self.assertEqual(self.catalogue['coverage']['canonical_families'], 44)
        self.assertEqual(self.catalogue['coverage']['help_entry_locale_rows'], 28)
        self.assertEqual(self.catalogue['coverage']['moment_cases'], 560)
        self.assertEqual(sum(c['native_mapping'] == 'SOURCE_BOUND_ORDINARY_ASK_DJ' for c in rows), 40)
        self.assertFalse(self.catalogue['execute'])

    def test_a_valid_draft_cannot_become_runtime_admission(self):
        result = self.check()
        self.assertFalse(result['execute'])
        self.assertEqual(result['qualification'], 'DRAFT_NOT_ADMITTED')
        self.assertEqual(result['selected_case_clients'], 4)
        self.assertIn('REAL_DISPOSABLE_FIXTURE', result['missing_live_gates'])
        self.assertEqual(result['runtime_fixture_provider_native_qualification'], 'NOT_GRANTED')

    def test_mutated_inventory_policy_cannot_authorize_its_own_new_hash(self):
        forged = deepcopy(self.catalogue)
        forged['cases'][0]['model_policy'] = 'zero'
        plan = deepcopy(self.plan)
        plan['inventory_sha256'] = contract.digest(contract.canonical(forged))
        with self.assertRaisesRegex(ValueError, 'unverified_or_mutated_inventory'):
            self.check(plan, forged)

    def test_original_question_policy_and_locale_are_not_reconstructed(self):
        for field, value in [('question_sha256', '0' * 64), ('model_policy_sha256', '1' * 64),
                             ('language', 'en-US'), ('id', 'invented-golden-id')]:
            plan = deepcopy(self.plan)
            plan['cases'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(plan)

    def test_independent_receipt_pins_and_all_client_binaries_are_required(self):
        for key in contract.BINDINGS:
            plan = deepcopy(self.plan)
            plan['receipts'][key] = '0' * 64
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'receipt_origin_mismatch'):
                self.check(plan)
        with self.assertRaisesRegex(ValueError, 'independent_receipts_required'):
            self.check(expected={})
        for client in contract.CLIENTS:
            plan = deepcopy(self.plan)
            del plan['app_receipts'][client]
            with self.subTest(client=client), self.assertRaises(ValueError):
                self.check(plan)

    def test_the_client_list_does_not_hide_missing_watch_execution(self):
        plan = deepcopy(self.plan)
        plan['cases'] = [c for c in plan['cases'] if c['client'] != 'watch']
        with self.assertRaisesRegex(ValueError, 'missing_client_case_coverage'):
            self.check(plan)

    def test_duplicate_case_unknown_keys_and_retry_fail_closed(self):
        mutations = [lambda p: p.update(execute=True), lambda p: p.update(qualified=True),
                     lambda p: p.update(retry_automatically=True),
                     lambda p: p['cases'].append(deepcopy(p['cases'][0])),
                     lambda p: p['cases'][0].update(raw_prompt='private text')]
        for mutate in mutations:
            plan = deepcopy(self.plan)
            mutate(plan)
            with self.assertRaises(ValueError):
                self.check(plan)

    def test_budget_boolean_overspend_policy_expansion_and_lifetime_fail(self):
        for key, value in [('provider_attempts', True), ('provider_attempts', 41),
                           ('attempts_per_turn', 3), ('output_tokens_per_attempt', 3001),
                           ('audio_actions', -1)]:
            plan = deepcopy(self.plan)
            plan['budget'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.check(plan)
        for expiry in ('2026-11-06T12:10:01+00:00', '2026-11-06T11:59:59+00:00', '2026-11-06T12:01:00'):
            plan = deepcopy(self.plan)
            plan['expires_at'] = expiry
            with self.assertRaises(ValueError):
                self.check(plan)

    def test_complete_synthetic_evidence_is_still_not_native_qualification(self):
        evidence = self.evidence()
        for row in evidence['cases']:
            row.update(semantic='PASS', effect='PASS', native='PASS')
        report = self.reconcile(evidence)
        self.assertTrue(report['complete_selected_set'])
        self.assertTrue(report['all_supplied_verdicts_pass'])
        self.assertFalse(report['execute'])
        self.assertEqual(report['qualification'], 'EVIDENCE_PENDING_INDEPENDENT_REVIEW')
        self.assertEqual(report['native_release_authority'], 'NOT_GRANTED')

    def test_missing_client_receipt_is_incomplete_not_skipped_pass(self):
        evidence = self.evidence()
        evidence['cases'].pop()
        report = self.reconcile(evidence)
        self.assertFalse(report['complete_selected_set'])
        self.assertFalse(report['all_supplied_verdicts_pass'])

    def test_wrong_original_run_or_receipt_or_duplicate_export_is_rejected(self):
        mutations = [lambda e: e.update(run_id='00000000-0000-4000-8000-000000000002'),
                     lambda e: e.update(plan_sha256='0' * 64),
                     lambda e: e['receipts'].update(fixture_owner='0' * 64),
                     lambda e: e['cases'].append(deepcopy(e['cases'][0])),
                     lambda e: e['cases'][0].update(client='windows'),
                     lambda e: e.update(unattributed_attempts=1),
                     lambda e: e.update(unattributed_attempts=False)]
        for mutate in mutations:
            evidence = self.evidence()
            mutate(evidence)
            with self.assertRaises(ValueError):
                self.reconcile(evidence)

    def test_safe_export_rejects_raw_answer_credentials_and_help_history_write(self):
        for mutate in [lambda e: e.update(token='synthetic-secret'),
                       lambda e: e['cases'][0].update(answer='private answer'),
                       lambda e: e['cases'][0].update(history_sha256='0' * 64),
                       lambda e: e['cases'][0].update(provider_attempts=1, provider_terminal='complete')]:
            evidence = self.evidence()
            mutate(evidence)
            with self.assertRaises(ValueError):
                self.reconcile(evidence)

    def test_failed_attempts_are_counted_and_never_become_reviewed_success(self):
        source = next(c for c in self.catalogue['cases'] if c['kind'] == 'canonical_step'
                      and c['language'] == 'en')
        plan = self.make_plan(source)
        plan['budget']['provider_attempts'] = 4
        self.bind_budget(plan)
        evidence = self.evidence(plan)
        for row in evidence['cases']:
            row.update(history_sha256=contract.digest('synthetic-history'),
                       session_entry_sha256=contract.digest('synthetic-session-entry'),
                       provider_attempts=1, provider_terminal='failed',
                       provider_receipt_sha256=contract.digest('synthetic-failed-attempt-' + row['client']),
                       model_sha256=None, input_tokens=None, output_tokens=None)
        report = self.reconcile(evidence, plan)
        self.assertEqual(report['observed_provider_attempts'], 4)
        self.assertFalse(report['all_supplied_verdicts_pass'])
        self.assertTrue(any(b['reason'] == 'UNQUALIFIED_TYPED_MODEL_POLICY' for b in report['blockers']))
        plan['budget']['provider_attempts'] = 3
        self.bind_budget(plan)
        evidence['receipts'] = self.receipts.copy()
        evidence['plan_sha256'] = contract.digest(contract.canonical(plan))
        with self.assertRaisesRegex(ValueError, 'cumulative_batch_limit'):
            self.reconcile(evidence, plan)

    def test_new_run_id_cannot_reset_the_independently_pinned_cumulative_snapshot(self):
        plan = deepcopy(self.plan)
        plan['budget']['previously_reserved_attempts'] = 10
        self.bind_budget(plan)
        self.check(plan)
        plan['run_id'] = '00000000-0000-4000-8000-000000000003'
        plan['budget']['previously_reserved_attempts'] = 0
        with self.assertRaisesRegex(ValueError, 'changed_cumulative_budget_snapshot'):
            self.check(plan)

    def test_changed_actual_app_binary_pin_cannot_reuse_the_same_operator_receipt(self):
        plan = deepcopy(self.plan)
        plan['app_receipts']['watch'] = contract.digest('another-synthetic-binary')
        with self.assertRaisesRegex(ValueError, 'missing_or_wrong_client_binary_receipt'):
            self.check(plan)

    def test_reused_provider_receipt_cannot_count_as_independent_attempts(self):
        source = next(c for c in self.catalogue['cases'] if c['kind'] == 'canonical_step'
                      and c['language'] == 'en')
        plan = self.make_plan(source)
        plan['budget']['provider_attempts'] = 4
        self.bind_budget(plan)
        evidence = self.evidence(plan)
        for row in evidence['cases']:
            row.update(history_sha256=contract.digest('synthetic-history'),
                       session_entry_sha256=contract.digest('synthetic-session-entry'),
                       provider_attempts=1, provider_terminal='failed',
                       provider_receipt_sha256=contract.digest('same-synthetic-receipt'),
                       model_sha256=None, input_tokens=None, output_tokens=None)
        with self.assertRaisesRegex(ValueError, 'reused_provider_receipt'):
            self.reconcile(evidence, plan)

    def test_duplicate_json_nonfinite_and_oversized_records_are_not_coerced(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'record.json'
            for raw in ('{"execute":false,"execute":true}', '{"budget":NaN}', ' ' * (4*1024*1024+1)):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    contract.read_json(path)

    def test_complete_provider_terminal_needs_model_and_exact_usage(self):
        source = next(c for c in self.catalogue['cases'] if c['kind'] == 'canonical_step'
                      and c['language'] == 'en')
        plan = self.make_plan(source)
        plan['budget']['provider_attempts'] = 4
        self.bind_budget(plan)
        evidence = self.evidence(plan)
        for row in evidence['cases']:
            row.update(history_sha256=contract.digest('synthetic-history'),
                       session_entry_sha256=contract.digest('synthetic-session-entry'),
                       provider_attempts=1, provider_terminal='complete',
                       provider_receipt_sha256=contract.digest('synthetic-attempt-' + row['client']),
                       model_sha256=contract.digest('synthetic-model'), input_tokens=17, output_tokens=23)
        self.assertEqual(self.reconcile(evidence, plan)['observed_provider_attempts'], 4)
        for key, value in [('model_sha256', None), ('input_tokens', True), ('output_tokens', None), ('output_tokens', 3001)]:
            bad = deepcopy(evidence)
            bad['cases'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.reconcile(bad, plan)

    def test_committed_consumer_inventory_cannot_silently_drift_from_source(self):
        path = contract.ROOT/'examples/client_contracts/native_golden_v1/catalogue.json'
        self.assertEqual(contract.read_json(path), self.catalogue)

    def test_help_observation_never_inherits_the_underlying_play_command_effect(self):
        rows = [c for c in self.catalogue['cases'] if c['kind'] == 'help_observation']
        self.assertTrue(any(c['expected']['on_explicit_send_effect'] == 'explicit_play' for c in rows))
        self.assertTrue(all(c['expected']['observation_effect'] == 'none' for c in rows))
