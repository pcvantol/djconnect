"""Maintenance14: one shared settings scope with owner output addendum, never a consumer dispatch."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

PREFIX = 'SETTINGS::'
PRIOR = 'history/20261016/passive-finalization-maintenance-v13.json'
SUFFIXES = {'CORE::DOCS', 'CORE::PRODUCER', 'CORE::MIGRATION', 'APPLE::EDITOR',
            'PI::ADOPTION', 'ESP32::ADOPTION', 'VIBECAST::COMPAT', 'WEBSITE::COPY', 'JOINT::ACCEPTANCE'}
NODES = {PREFIX + x for x in SUFFIXES}
CONTRACT = 'docs/product/PROFILE_SESSION_SETTINGS_CONSOLIDATION_V1.md'
CONSUMERS = ('APPLE::EDITOR', 'PI::ADOPTION', 'ESP32::ADOPTION',
             'VIBECAST::COMPAT', 'WEBSITE::COPY')
EXPECTED_PAIRS = {
    ('SETTINGS::CORE::DOCS', 'SETTINGS::CORE::PRODUCER'),
    ('SPEECH::CORE::DELIVERY', 'SETTINGS::CORE::PRODUCER'),
    ('SETTINGS::CORE::PRODUCER', 'SETTINGS::CORE::MIGRATION'),
    ('SETTINGS::CORE::MIGRATION', 'SETTINGS::JOINT::ACCEPTANCE'),
} | {(PREFIX + 'CORE::PRODUCER', PREFIX + c) for c in CONSUMERS} | {
    (PREFIX + c, PREFIX + 'CORE::MIGRATION') for c in CONSUMERS}


def validate(plan, previous_validator):
    delta = plan['planning_maintenance']
    receipt = delta.get('settings_consolidation_receipt', {})
    errors = []

    def check(ok, reason):
        if not ok:
            errors.append('maintenance: settings consolidation ' + reason)

    raw = (Path(__file__).parent / PRIOR).read_bytes()
    prior = json.loads(raw)
    check(receipt.get('previous_delta') == PRIOR
          and receipt.get('previous_delta_sha256') == hashlib.sha256(raw).hexdigest(), 'prior bytes')
    inventory = 'docs/product/PROFILE_SESSION_SETTINGS_INVENTORY_V1.json'
    check(receipt.get('inventory_path') == inventory and receipt.get('inventory_sha256')
          == hashlib.sha256((Path(__file__).parents[3] / inventory).read_bytes()).hexdigest(),
          'canonical inventory bytes')
    check(receipt.get('assignment_id') == 'DJC-PROFILE-SESSION-SETTINGS-CONSOLIDATION-V1-20261016'
          and receipt.get('owner_selection') == 6214905647
          and receipt.get('ack') == 6218545503
          and receipt.get('base_sha') == '148bd5aee3110c1a1ab13e7c463a164c99d79b70'
          and receipt.get('branch') == 'codex/profile-session-settings-consolidation-v1', 'selection and admission')
    check(receipt.get('parameters') == ['persona', 'voice', 'gender', 'mood', 'presence', 'announcement_output']
          and receipt.get('last_explicit_choice_is_default') is True
          and receipt.get('atomic_active_and_default') is True
          and receipt.get('voice_scope') == 'profile_and_session'
          and receipt.get('contract_version') == 3
          and receipt.get('runtime_checkpoint_contract_version') == 3
          and receipt.get('owner_addenda') == [6220504359, 6220590330, 6220625247, 6220695648,
                                               6220756856, 6220784635, 6220817753]
          and receipt.get('portability') == 'PARKED_NO_PICKUP'
          and receipt.get('ha_only') == ['assist_pipeline', 'physical_ha_speaker', 'esp_administration']
          and receipt.get('client_local') == ['autoplay_default_off', 'os_permissions', 'physical_device_preferences'],
          'six shared semantics and owner scope boundaries')
    check(receipt.get('native') == 'OPEN_APPLE' and receipt.get('other_consumers') == 'OPEN_OWNING_LANES'
          and receipt.get('joint') == 'OPEN' and receipt.get('family_acceptance') == 'PARTIAL'
          and receipt.get('automatic_dispatch') is False and receipt.get('consumer_writes') is False,
          'consumer and family claim boundary')
    delivered = receipt.get('phase') == 'SOURCE_PROTECTED_MERGED'
    check(receipt.get('phase') in {'LOCAL_IMPLEMENTATION_AND_QUALIFICATION', 'SOURCE_PROTECTED_MERGED'}
          and receipt.get('source_delivery') == ('PROTECTED_MERGED' if delivered else 'UNPUBLISHED'),
          'source phase')
    if delivered:
        check(all(re.fullmatch('[a-f0-9]{40}', str(receipt.get(k, ''))) for k in ('source_main_sha', 'reviewed_head'))
              and receipt.get('source_review') == 'PASS' and receipt.get('required_checks') == 'PASS'
              and receipt.get('core_source_pin') == receipt.get('source_main_sha')
              and receipt.get('protected_merge') is True
              and all(re.fullmatch('[a-f0-9]{64}', str(receipt.get(k, '')))
                      for k in ('archive_sha256', 'formal_evidence_sha256')), 'source evidence')
    nodes = delta.get('nodes', [])
    settings = {n['id']: n for n in nodes if n['id'].startswith(PREFIX)}
    check(set(settings) == NODES and len(nodes) == len({n['id'] for n in nodes}), 'unique bounded family')
    for name, node in settings.items():
        check(node.get('contract_binding') == CONTRACT, 'canonical contract')
        core = name in {'SETTINGS::CORE::DOCS', 'SETTINGS::CORE::PRODUCER'}
        expected = ('Completed', 'CORE_DELIVERED') if delivered and core else (
            ('In progress', 'IN_PROGRESS') if name.startswith('SETTINGS::CORE::') else ('Planned', 'NOT_ISSUED'))
        check((node.get('status'), node.get('assignment_status')) == expected, 'node acceptance ' + name)
    prior_nodes = {n['id']: n for n in prior['nodes']}
    check({n['id']: n for n in nodes if not n['id'].startswith(PREFIX)} == prior_nodes, 'unrelated delivered nodes')
    edges = delta.get('edges', [])
    check(len(edges) == len({e['id'] for e in edges}), 'duplicate edge')
    check([e for e in edges if not e['id'].startswith('SETTINGS-')] == prior['edges'], 'prior graph')
    added = [e for e in edges if e['id'].startswith('SETTINGS-')]
    check(len(added) == len(EXPECTED_PAIRS)
          and {(e.get('producer'), e.get('consumer')) for e in added} == EXPECTED_PAIRS,
          'exact producer consumer dependencies')
    known = {n['id'] for n in nodes} | {n['id'] for n in plan.get('nodes', [])}
    graph = {name: set() for name in known}
    for edge in edges:
        source, target = edge.get('producer'), edge.get('consumer')
        check(source in known and target in known, 'unknown graph endpoint')
        if source in known and target in known:
            graph[source].add(target)
    # Iterative topological removal checks the actual complete maintained graph.
    incoming = {name: 0 for name in graph}
    for targets in graph.values():
        for target in targets:
            incoming[target] += 1
    ready = [name for name, count in incoming.items() if count == 0]
    visited = 0
    while ready:
        source = ready.pop()
        visited += 1
        for target in graph[source]:
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
    check(visited == len(graph), 'cyclic dependencies')
    for edge in added:
        check(edge.get('hard_precedence') is True and edge.get('logical_mode') == 'AND',
              'hard AND completion dependency')
    stripped = deepcopy(delta)
    stripped.pop('settings_consolidation_receipt', None)
    stripped['schema_version'] = prior['schema_version']
    stripped['nodes'] = deepcopy(prior['nodes'])
    stripped['edges'] = deepcopy(prior['edges'])
    for key in prior.keys() - {'document_references'}:
        check(stripped.get(key) == prior[key], 'prior receipt ' + key)
    previous = deepcopy(plan)
    previous['planning_maintenance'] = stripped
    errors.extend(previous_validator(previous))
    return errors
