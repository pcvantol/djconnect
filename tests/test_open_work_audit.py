"""Permanent negative evidence checks for the actual cross-lane open-work readback."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('open_work_audit', ROOT / 'tools/verification/open_work_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class OpenWorkAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(audit.REGISTER.read_text())
        cls.plan = json.loads((ROOT / 'docs/roadmap/v1/djconnect-platform-v1.json').read_text())

    def changed(self):
        return copy.deepcopy(self.data)

    def assertRejected(self, data, message):
        self.assertTrue(any(message in e for e in audit.validate(data, self.plan)))

    def test_current_register_and_generated_document_are_consistent(self):
        self.assertEqual(audit.validate(self.data, self.plan), [])
        self.assertEqual(audit.REPORT.read_text(), audit.render(self.data))
        self.assertEqual(len(self.data['repositories']), 13)

    def test_each_requested_topic_cannot_be_omitted(self):
        for topic in audit.TOPICS:
            with self.subTest(topic=topic):
                d = self.changed()
                d['items'] = [r for r in d['items'] if r['topic'] != topic]
                self.assertRejected(d, 'topic omitted')

    def test_each_unfinished_maintenance_gate_is_retained(self):
        for row in self.data['dag_open']:
            with self.subTest(node=row['id']):
                d = self.changed()
                d['dag_open'] = [r for r in d['dag_open'] if r['id'] != row['id']]
                self.assertRejected(d, 'unfinished DAG gates')

    def test_null_status_inventory_projection_is_not_an_open_assignment(self):
        plan = copy.deepcopy(self.plan)
        plan['nodes'].append({'id': 'TEST::HISTORICAL-INVENTORY', 'type': 'inventory_record',
                              'status': None, 'source_status_summary': 'Unassessed'})
        self.assertEqual(audit.validate(self.data, plan), [])
        d = self.changed()
        d['dag_open'].append({'id': 'TEST::HISTORICAL-INVENTORY', 'status': None})
        self.assertTrue(audit.validate(d, plan))

    def test_duplicate_work_issue_and_proof_are_rejected(self):
        for key, expected in [('items', 'duplicate work'), ('github_open', 'duplicate GitHub'), ('proofs', 'duplicate proof')]:
            with self.subTest(key=key):
                d = self.changed()
                d[key].append(copy.deepcopy(d[key][0]))
                self.assertRejected(d, expected)

    def test_unknown_owner_dependencies_evidence_and_canonical_refs(self):
        for key, value, expected in [('owners', [], 'owner, next action'),
                                     ('required_tests', [], 'owner, next action'),
                                     ('depends_on', ['imaginary'], 'unknown dependency'),
                                     ('proof_ids', ['imaginary'], 'unknown evidence'),
                                     ('dag_refs', ['NEW::UNSELECTED-FAMILY'], 'canonical DAG')]:
            with self.subTest(key=key):
                d = self.changed()
                d['items'][0][key] = value
                self.assertRejected(d, expected)

    def test_cyclic_dependencies_are_not_a_valid_execution_queue(self):
        d = self.changed()
        d['items'][0]['depends_on'] = ['delivery']
        self.assertRejected(d, 'cyclic')

    def test_wrong_source_even_with_same_version_is_not_installed_pass(self):
        d = self.changed()
        p = next(r for r in d['proofs'] if r['id'] == 'installed-dev')
        p['commit'] = d['core_local_correction']['commit']
        self.assertRejected(d, 'observed exact source')

    def test_partial_changed_or_extra_installed_files_fail(self):
        for field, value, expected in [('actual_files', 176, 'file set'), ('expected_files', True, 'file set'),
                                       ('changed_or_missing', 1, 'files differ'), ('extra_files', 1, 'files differ')]:
            with self.subTest(field=field):
                d = self.changed()
                next(r for r in d['proofs'] if r['id'] == 'installed-dev')[field] = value
                self.assertRejected(d, expected)

    def test_equal_but_truncated_counts_and_maps_cannot_qualify_installed(self):
        d = self.changed()
        for p in d['proofs']:
            if p['kind'] == 'installed_manifest':
                p['expected_files'] = p['actual_files'] = 1
                key = next(iter(p['files']))
                p['files'] = {key: p['files'][key]}
        self.assertRejected(d, 'file set is incomplete')

    def test_missing_extra_or_changed_actual_file_hash_fails(self):
        for mutation in ('missing', 'extra', 'changed'):
            with self.subTest(mutation=mutation):
                d = self.changed()
                p = next(r for r in d['proofs'] if r['id'] == 'installed-dev')
                key = next(iter(p['files']))
                if mutation == 'missing':
                    del p['files'][key]
                elif mutation == 'extra':
                    p['files']['untracked.py'] = '0' * 64
                else:
                    p['files'][key] = '0' * 64
                self.assertRejected(d, 'files differ')

    def test_manifest_cannot_be_silently_replaced(self):
        original = audit.SOURCE_MANIFEST.read_bytes()
        with patch.object(Path, 'read_bytes', return_value=original + b' '):
            self.assertRejected(self.data, 'manifest digest differs')
        d = self.changed()
        d['source_manifest']['sha256'] = '0' * 64
        self.assertRejected(d, 'invalid pinned source manifest')

    def test_deleting_local_proofs_and_all_references_cannot_leave_false_claims(self):
        for pid in ('local-corrective-regressions', 'local-real-model-quality'):
            d = self.changed()
            d['proofs'] = [r for r in d['proofs'] if r['id'] != pid]
            for item in d['items']:
                item['proof_ids'] = [r for r in item['proof_ids'] if r != pid]
            self.assertRejected(d, 'missing or inconsistent')

    def test_rendered_counts_derive_from_bound_proofs(self):
        d = self.changed()
        p = next(r for r in d['proofs'] if r['id'] == 'local-corrective-regressions')
        p['count'] = d['core_local_correction']['host_tests'] = 2273
        self.assertEqual(audit.validate(d, self.plan), [])
        self.assertIn('2,273 host tests', audit.render(d))

    def test_installed_and_external_contract_versions_are_exact(self):
        for pid, field in [('installed-dev', 'contract_versions'), ('installed-prod', 'surface_versions')]:
            for value in (None, True, '1', 2):
                d = self.changed()
                next(r for r in d['proofs'] if r['id'] == pid)[field]['active_session_mood'] = value
                self.assertRejected(d, 'contract must be v1')
        for field in ('mood_version', 'presence_version'):
            d = self.changed()
            next(r for r in d['proofs'] if r['id'] == 'external-dev-advertisement')[field] = 2
            self.assertRejected(d, 'external advertisement v1')

    def test_missing_or_nonboolean_capability_is_not_success(self):
        for value in [None, False, 'true', 1]:
            with self.subTest(value=value):
                d = self.changed()
                next(r for r in d['proofs'] if r['id'] == 'installed-dev')['capabilities']['active_session_mood'] = value
                self.assertRejected(d, 'advertisement is missing')

    def test_fixture_tests_and_lane_report_do_not_prove_installed_bytes(self):
        for kind in ['local_tests', 'owner_lane_report']:
            with self.subTest(kind=kind):
                d = self.changed()
                next(r for r in d['proofs'] if r['id'] == 'installed-dev')['kind'] = kind
                self.assertRejected(d, 'installed-manifest')

    def test_scoped_issue_closure_does_not_close_native_or_whole_product(self):
        d = self.changed()
        next(r for r in d['items'] if r['id'] == 'advertisement')['product_acceptance'] = 'PASS'
        self.assertRejected(d, 'whole product completion')
        for field, value in [('kind', 'local_tests'), ('tls_verified', False), ('http_status', 426)]:
            with self.subTest(field=field):
                d = self.changed()
                next(r for r in d['proofs'] if r['id'] == 'external-dev-advertisement')[field] = value
                self.assertRejected(d, 'verified external advertisement')

    def test_unimplemented_preview_cannot_borrow_mood_advertisement_proof(self):
        d = self.changed()
        preview = next(r for r in d['items'] if r['id'] == 'preview')
        advert = next(r for r in d['items'] if r['id'] == 'advertisement')
        for key in ['status', 'closure_scope', 'product_acceptance', 'proof_ids']:
            preview[key] = copy.deepcopy(advert[key])
        self.assertRejected(d, 'whole product completion')

    def test_unpublished_source_and_real_quality_failure_cannot_be_promoted(self):
        for key, value in [('published', True), ('installed', True), ('overall_quality', 'PASS')]:
            with self.subTest(key=key):
                d = self.changed()
                d['core_local_correction'][key] = value
                self.assertRejected(d, 'unpublished correction')
        d = self.changed()
        d['core_local_correction']['open_quality_steps'] = 0
        self.assertRejected(d, 'findings must not disappear')

    def test_open_findings_cannot_be_marked_product_pass(self):
        d = self.changed()
        d['items'][0]['product_acceptance'] = 'PASS'
        self.assertRejected(d, 'open finding')

    def test_retired_windows_is_not_new_work(self):
        d = self.changed()
        next(r for r in d['repositories'] if r['name'] == 'djconnect-windows')['product_active'] = True
        self.assertRejected(d, 'retired Windows')

    def test_audit_cannot_dispatch_or_write_consumers(self):
        for field in ['automatic_dispatch', 'consumer_writes']:
            with self.subTest(field=field):
                d = self.changed()
                d[field] = True
                self.assertRejected(d, 'dispatch')

    def test_active_or_unpublished_refs_cannot_be_reported_deleted(self):
        d = self.changed()
        d['cleanup']['deleted_branches'] = ['codex/askdj-contextual-golden-release-v1']
        self.assertRejected(d, 'fabricate cleanup')
        d = self.changed()
        d['cleanup']['preserved'][0]['reason'] = 'DELETE_OLD'
        self.assertRejected(d, 'preserve ambiguous')


if __name__ == '__main__':
    unittest.main()
