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
            response = self.response(); change(response)
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
            changed = deepcopy(good); mutate(changed)
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
        unbound=deepcopy(seed);unbound.pop('fixture_bindings')
        with self.assertRaises(ValueError):
            materialize_case(unbound)

    def test_all_literal_core_routes_and_owner_bindings_are_accounted_for(self):
        from tools.verification.askdj_release_inventory import validate
        proof=validate()
        self.assertEqual(proof['literal_core_routes'],46)
        self.assertEqual(proof['executable_help_cases'],60)
        self.assertEqual(proof['conversation_families'],21)
