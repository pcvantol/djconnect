"""A combined PR cannot hide either existing stream or promote old proof."""
from copy import deepcopy
from pathlib import Path
import unittest
from validate_snapshot import load, validate

ROOT = Path(__file__).parent


class BranchConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.plan = load(ROOT / 'djconnect-platform-v1.json')

    def test_both_existing_streams_and_dependency_edges_survive(self):
        self.assertEqual(validate(self.plan), [])
        for dropped in ('display_admission_receipt', 'experience_reconciliation_receipt'):
            bad = deepcopy(self.plan)
            bad['planning_maintenance'].pop(dropped)
            self.assertTrue(validate(bad))
        for node in ('WEB::TRUST', 'WEB::DISPLAY', 'CORRECTION::CORE::PERSONAL-DJ-EXPERIENCE'):
            bad = deepcopy(self.plan)
            bad['planning_maintenance']['nodes'] = [n for n in bad['planning_maintenance']['nodes']
                                                   if n['id'] != node]
            self.assertTrue(validate(bad), node)

    def test_combining_branches_cannot_promote_review_or_acceptance(self):
        for field, value in (('overall_acceptance', 'PASS'), ('merge_readiness', 'GO'),
                             ('installed', 'PASS'), ('audible', 'PASS'),
                             ('source_delivery', 'PROTECTED_MERGED'), ('consumer_writes', True)):
            bad = deepcopy(self.plan)
            bad['planning_maintenance']['branch_consolidation_receipt'][field] = value
            self.assertTrue(validate(bad), field)

    def test_exact_original_heads_and_both_history_hashes_are_required(self):
        bad = deepcopy(self.plan)
        bad['planning_maintenance']['branch_consolidation_receipt']['original_heads']['waiting'] = '0'*40
        self.assertTrue(validate(bad))
        for i in (0, 1):
            bad = deepcopy(self.plan)
            bad['planning_maintenance']['branch_consolidation_receipt']['preserved_inputs'][i]['sha256'] = '0'*64
            self.assertTrue(validate(bad))

    def test_old_exact_source_and_cycle_diagnostics_still_execute(self):
        bad = deepcopy(self.plan)
        bad['planning_maintenance']['settings_consolidation_receipt']['core_source_pin'] = '0'*40
        self.assertTrue(any('source evidence' in e for e in validate(bad)))
        bad = deepcopy(self.plan)
        edges = bad['planning_maintenance']['edges']
        edge = deepcopy(next(e for e in edges if e['id'].startswith('SETTINGS-')))
        edge.update(id='SETTINGS-CYCLE', producer=edge['consumer'], consumer=edge['producer'])
        edges.append(edge)
        self.assertTrue(any('cyclic' in e for e in validate(bad)))
