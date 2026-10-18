"""Maintenance16 composes both preserved15 streams without promoting delivery."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
INPUTS = (
    'history/20261017/personal-dj-before-consolidation-maintenance-v15.json',
    'history/20261017/display-before-consolidation-maintenance-v15.json',
)
INPUT_HASHES = {'history/20261017/personal-dj-before-consolidation-maintenance-v15.json': '0c4a190d700b7de36b10986f3c00a2269f4646130e14c43d7c82f16cfbca2efc', 'history/20261017/display-before-consolidation-maintenance-v15.json': 'f3a77f4dd736fd8433d6f0c3b7374d1d118d094fe0fcc76d20aae7c95cee26c8'}
PREMERGE_HEADS = {'ask_dj': 'e3d7b55f5c67019a306cc4a4b3a31b2028304c9c', 'display': '6e560061cbee3bed86c50fc0deee7d74b9bfee9b'}
DISPLAY_NODES = {'WEB::TRUST', 'WEB::DISPLAY'}


def validate(plan, previous_validator):
    delta = plan['planning_maintenance']
    receipt = delta.get('branch_consolidation_receipt', {})
    errors = []

    def check(ok, reason):
        if not ok:
            errors.append('maintenance: branch consolidation ' + reason)

    preserved = []
    originals = []
    for name in INPUTS:
        raw = (ROOT / name).read_bytes()
        check(hashlib.sha256(raw).hexdigest() == INPUT_HASHES[name], 'pinned premerge historical bytes')
        preserved.append({'path': name, 'sha256': INPUT_HASHES[name]})
        originals.append(json.loads(raw))
    experience, display = originals
    check(receipt.get('preserved_inputs') == preserved, 'both exact historical inputs')
    expected_receipt = {
        'schema_version': 'djconnect-core-branch-consolidation/1',
        'source_delivery': 'LOCAL_COMBINED_DRAFT_PREPARATION',
        'overall_acceptance': 'OPEN',
        'original_main': '6a3adbc8e66ab380dfea1726ca34728097d0c684',
        'original_heads': {
            'ask_dj': 'dae30074947b1cc3b105016ae14c99e0008c3870',
            'waiting': '4b3a805975fbd6876c037b273ecbcced2f9af5b2',
            'display': '6e560061cbee3bed86c50fc0deee7d74b9bfee9b',
        },
        'premerge_heads': PREMERGE_HEADS,
        'preserved_inputs': preserved, 'existing_pr': 1197, 'sole_writer': True,
        'consumer_writes': False, 'automatic_dispatch': False,
        'merge_readiness': 'NOT_QUALIFIED', 'native': 'OPEN',
        'installed': 'NOT_RUN', 'audible': 'NOT_RUN',
    }
    check(receipt == expected_receipt, 'no unqualified merge, installation or consumer promotion')
    references = delta.get('document_references', [])
    paths = [r.get('path') for r in references]
    required = {r['path'] for old in originals for r in old['document_references']}
    check(len(paths) == len(set(paths)) and required <= set(paths), 'union of document references')

    # Only the two existing display nodes and the additive display receipt join
    # the current correction. Every other node, edge and delivery receipt stays.
    expected = deepcopy(experience)
    expected['schema_version'] = 'djconnect-federated-planning-delta/16'
    expected['branch_consolidation_receipt'] = receipt
    expected['display_admission_receipt'] = delta.get('display_admission_receipt')
    expected['document_references'] = references
    by_id = {n['id']: n for n in display['nodes']}
    expected['nodes'] = [deepcopy(by_id[n['id']]) if n['id'] in DISPLAY_NODES else n
                         for n in expected['nodes']]
    check(delta == expected, 'exact bounded composition of nodes, edges and prior receipts')

    # Execute both unchanged component validators. Current reference hashes are
    # checked by the experience validator; display still validates its own exact
    # original settings predecessor and all trust/consumer negative boundaries.
    for original in originals:
        view = deepcopy(delta)
        view.pop('branch_consolidation_receipt', None)
        view['schema_version'] = 'djconnect-federated-planning-delta/15'
        if 'display_admission_receipt' in original:
            view.pop('experience_reconciliation_receipt', None)
            view['nodes'] = [n for n in view['nodes']
                             if n['id'] != 'CORRECTION::CORE::PERSONAL-DJ-EXPERIENCE']
            view['edges'] = [e for e in view['edges']
                             if not e['id'].startswith('EXPERIENCE-CORRECTION-')]
        else:
            view.pop('display_admission_receipt', None)
            prior_nodes = {n['id']: n for n in original['nodes']}
            view['nodes'] = [deepcopy(prior_nodes[n['id']])
                             if n['id'] in DISPLAY_NODES else n for n in view['nodes']]
        child = deepcopy(plan)
        child['planning_maintenance'] = view
        errors.extend(previous_validator(child))
    return errors
