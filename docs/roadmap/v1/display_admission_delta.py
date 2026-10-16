"""Maintenance15: selected Core trust/display review only, never fake runtime delivery."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

PRIOR = 'history/20261016/settings-capability-finalization-maintenance-v14.json'
NODES = {'WEB::TRUST', 'WEB::DISPLAY'}
CONTRACT = 'docs/product/VIBECAST_DISPLAY_ADMISSION_V1.md'


def validate(plan, previous_validator):
    d = plan['planning_maintenance']
    r = d.get('display_admission_receipt', {})
    errors = []

    def check(ok, reason):
        if not ok:
            errors.append('maintenance: display admission ' + reason)

    raw = (Path(__file__).parent / PRIOR).read_bytes()
    prior = json.loads(raw)
    check(r.get('previous_delta') == PRIOR and r.get('previous_delta_sha256') == hashlib.sha256(raw).hexdigest(),
          'predecessor preservation')
    check(r.get('assignment_id') == 'DJC-CORE-VIBECAST-DISPLAY-ADMISSION-V1-20261016'
          and r.get('owner_selection') == 6222775045 and r.get('ack') == 6224062979
          and r.get('base_sha') == '1329ad1ce8bd066d65a08b3988261a44e2cac730'
          and r.get('branch') == 'codex/vibecast-display-admission-v1'
          and r.get('first_contract_commit') == '275679322111fbda110bce2dad1f16da2932017e', 'selected admission')
    check(r.get('phase') == 'CONTRACT_REVIEW' and r.get('source_delivery') == 'UNPUBLISHED'
          and r.get('trust_anchor') == 'OPEN_JOINT_REVIEW' and r.get('wire') == 'NOT_FROZEN'
          and r.get('runtime') == 'NOT_IMPLEMENTED' and r.get('native') == 'OPEN_APPLE'
          and r.get('TV') == 'NOT_RUN' and r.get('joint') == 'OPEN'
          and r.get('consumer_writes') is False and r.get('automatic_dispatch') is False,
          'trust/runtime/consumer claim boundary')
    nodes = d.get('nodes', [])
    by_id = {n['id']: n for n in nodes}
    previous_nodes = {n['id']: n for n in prior['nodes']}
    check(len(nodes) == len(by_id) and by_id.keys() == previous_nodes.keys(), 'unique existing nodes only')
    for name, old in previous_nodes.items():
        expected = deepcopy(old)
        if name in NODES:
            expected.update(status='In progress', assignment_status='IN_PROGRESS', contract_binding=CONTRACT)
        check(by_id.get(name) == expected, 'exact node scope ' + name)
    check(d.get('edges') == prior['edges'], 'unchanged dependency graph')
    # The complete preserved predecessor validator checks all references and its acyclic graph.
    stripped = deepcopy(d)
    stripped.pop('display_admission_receipt', None)
    stripped['schema_version'] = prior['schema_version']
    stripped['nodes'] = deepcopy(prior['nodes'])
    for key in prior.keys() - {'document_references'}:
        check(stripped.get(key) == prior[key], 'prior receipt ' + key)
    previous = deepcopy(plan)
    previous['planning_maintenance'] = stripped
    errors.extend(previous_validator(previous))
    return errors
