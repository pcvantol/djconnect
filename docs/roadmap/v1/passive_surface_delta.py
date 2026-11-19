"""Version13: admit only the existing selected passive Core node, preserve v12."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

NODE = 'SURFACE::CORE::PROJECTION'
PRIOR = 'history/20261016/provider-gender-finalization-maintenance-v12.json'


def validate(plan, previous_validator):
    d = plan['planning_maintenance']
    receipt = d.get('passive_surface_receipt', {})
    errors = []

    def check(ok, reason):
        if not ok:
            errors.append('maintenance: passive surface ' + reason)

    raw = (Path(__file__).parent / PRIOR).read_bytes()
    previous = json.loads(raw)
    check(receipt.get('previous_delta') == PRIOR
          and receipt.get('previous_delta_sha256') == hashlib.sha256(raw).hexdigest(), 'prior snapshot bytes')
    check(receipt.get('assignment_id') == 'DJC-CORE-PASSIVE-SESSION-PROJECTION-V1-20261015'
          and receipt.get('owner_selection') == 6199213014
          and receipt.get('base_sha') == '9faffe533d4a117eb8ad362e73809d126bdcc9d7'
          and receipt.get('branch') == 'codex/passive-session-projection-v1'
          and receipt.get('ack') == 6214264273 and receipt.get('material_start') == 6214391660,
          'selection/admission provenance')
    check(receipt.get('contract_commit') == '9bc26e0caab15a83acf50b79be7236f723ee0404'
          and bool(re.fullmatch(r'[a-f0-9]{40}', receipt.get('material_commit', ''))), 'contract/material pins')
    check(receipt.get('background_node') == 'SURFACE::APPLE::QUIET-TRANSPORT'
          and receipt.get('native') == 'OPEN_APPLE' and receipt.get('background') == 'PLANNED'
          and receipt.get('watch') == 'NOT_QUALIFIED' and receipt.get('joint') == 'OPEN'
          and receipt.get('consumer_writes') is False and receipt.get('automatic_dispatch') is False,
          'consumer/background/Watch authority overclaim')
    delivered = receipt.get('phase') == 'SOURCE_PROTECTED_MERGED'
    check(receipt.get('phase') in {'LOCAL_IMPLEMENTATION_AND_QUALIFICATION', 'SOURCE_PROTECTED_MERGED'}
          and receipt.get('source_delivery') == ('PROTECTED_MERGED' if delivered else 'UNPUBLISHED'),
          'source phase/delivery mismatch')
    if delivered:
        check(all(re.fullmatch(r'[a-f0-9]{40}', str(receipt.get(k, ''))) for k in ('source_main_sha', 'reviewed_head'))
              and receipt.get('source_review') == 'PASS' and receipt.get('required_checks') == 'PASS'
              and receipt.get('protected_merge') is True
              and all(re.fullmatch(r'[a-f0-9]{64}', str(receipt.get(k, '')))
                      for k in ('archive_sha256', 'formal_evidence_sha256')), 'protected source evidence missing')
    nodes = {n['id']: n for n in d.get('nodes', [])}
    prior_nodes = {n['id']: n for n in previous['nodes']}
    check(len(nodes) == len(d.get('nodes', [])) and nodes.keys() == prior_nodes.keys(), 'duplicate/new/missing node')
    core = nodes.get(NODE, {})
    check((core.get('status'), core.get('assignment_status')) ==
          (('Completed', 'CORE_DELIVERED') if delivered else ('In progress', 'IN_PROGRESS')),
          'existing Core node state')
    check(core.get('contract_binding') == 'docs/product/PASSIVE_SESSION_PROJECTION_V1.md', 'canonical contract binding')
    for name in prior_nodes.keys() - {NODE}:
        check(nodes.get(name) == prior_nodes[name], 'unrelated node changed: ' + name)
    stripped = deepcopy(d)
    stripped.pop('passive_surface_receipt', None)
    stripped['schema_version'] = previous['schema_version']
    stripped['nodes'] = deepcopy(previous['nodes'])
    for key in previous.keys() - {'document_references'}:
        check(stripped.get(key) == previous[key], 'prior receipt/edges changed: ' + key)
    old = deepcopy(plan)
    old['planning_maintenance'] = stripped
    errors.extend(previous_validator(old))
    return errors
