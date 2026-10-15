"""Version11 bounded Session-media delta over the preserved delivered v10 plan."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

PREFIX = 'MEDIA::'
CORE = {'MEDIA::CORE::SESSION-CONTRACT', 'MEDIA::CORE::SESSION-LIVE', 'MEDIA::CORE::SESSION-HISTORY'}
CONSUMERS = {'MEDIA::APPLE::SESSION-ARTWORK', 'MEDIA::JOINT::SESSION-ARTWORK'}
PAIRS = {('MEDIA::CORE::SESSION-CONTRACT', 'MEDIA::CORE::SESSION-LIVE'),
         ('MEDIA::CORE::SESSION-LIVE', 'MEDIA::CORE::SESSION-HISTORY'),
         ('MEDIA::CORE::SESSION-CONTRACT', 'MEDIA::APPLE::SESSION-ARTWORK'),
         ('MEDIA::CORE::SESSION-LIVE', 'MEDIA::JOINT::SESSION-ARTWORK'),
         ('MEDIA::CORE::SESSION-HISTORY', 'MEDIA::JOINT::SESSION-ARTWORK'),
         ('MEDIA::APPLE::SESSION-ARTWORK', 'MEDIA::JOINT::SESSION-ARTWORK')}


def validate(plan, previous_validator):
    d = plan['planning_maintenance']
    errors = []
    def check(value, message):
        if not value:
            errors.append('maintenance: Session artwork '+message)
    r = d.get('session_artwork_receipt', {})
    check(r.get('assignment_id') == 'DJC-CORE-SESSION-MOMENT-ARTWORK-V1-20261014'
          and r.get('selection') == 6175336907 and r.get('refinement') == 6176704119,
          'selection missing')
    check(r.get('base_sha') == 'f0a7ff4bb878247db9ab25c4a22320f17d806cd6'
          and r.get('branch') == 'codex/session-moment-artwork-v1'
          and r.get('ack') == 6189044515 and r.get('material_start') == 6189241629
          and r.get('contract_commit') == '1668d71d3d639a12d7c61d96fc9656a2c3ce2b81'
          and r.get('material_commit') == '23f58d2b5d8e0ba373d26d3058e9bdd687320a5a',
          'actual admission missing')
    check(r.get('previous_delta') == 'history/20261015/hybrid-finalization-maintenance-v10.json',
          'predecessor reference missing')
    prior_file = Path(__file__).parent/'history/20261015/hybrid-finalization-maintenance-v10.json'
    prior_bytes = prior_file.read_bytes()
    check(hashlib.sha256(prior_bytes).hexdigest() == r.get('previous_delta_sha256'), 'predecessor bytes changed')
    previous = json.loads(prior_bytes)
    stripped = deepcopy(d)
    stripped.pop('session_artwork_receipt', None)
    stripped['schema_version'] = previous['schema_version']
    stripped['nodes'] = [n for n in d.get('nodes', []) if not n.get('id', '').startswith(PREFIX)]
    stripped['edges'] = [e for e in d.get('edges', []) if not e.get('id', '').startswith('SESSION-MEDIA-')]
    for k in previous.keys()-{'document_references'}:
        check(stripped.get(k) == previous[k], 'previous delivered state changed: '+k)
    old = deepcopy(plan)
    old['planning_maintenance'] = stripped
    errors.extend(previous_validator(old))
    successor = r.get('selected_successor')
    if successor is not None:
        check(successor == {'assignment_id':'DJC-SESSION-SPEECH-PERSONA-VOICE-20261015',
              'owner_selection':6189231491,'autonomous_next':6189912293,
              'admission':'NOT_ADMITTED','start_boundary':'AFTER_VALID_ARTWORK_FINALIZATION_AND_FRESH_ADMISSION',
              'same_writer':True,'new_publication_gates_preserved':True,
              'implementation_in_this_slice':False}, 'queued successor overclaim or authority changed')
    delivered = r.get('phase') == 'SOURCE_PROTECTED_MERGED'
    check(r.get('phase') in {'LOCAL_IMPLEMENTATION_AND_QUALIFICATION', 'SOURCE_PROTECTED_MERGED'}
          and r.get('source_delivery') == ('PROTECTED_MERGED' if delivered else 'UNPUBLISHED'), 'delivery mismatch')
    check(r.get('native') == 'OPEN_APPLE' and r.get('installed') == 'NOT_RUN'
          and r.get('hardware') == 'NOT_RUN' and r.get('joint_acceptance') == 'OPEN'
          and r.get('family_acceptance') == 'PARTIAL' and r.get('consumer_writes') is False
          and r.get('automatic_dispatch') is False, 'consumer acceptance or dispatch overclaim')
    if delivered:
        check(all(re.fullmatch(r'[a-f0-9]{40}', str(r.get(k,''))) for k in ('source_main_sha',))
              and r.get('source_review') == 'PASS' and r.get('required_checks') == 'PASS'
              and r.get('protected_merge') is True
              and all(re.fullmatch(r'[a-f0-9]{64}', str(r.get(k,''))) for k in ('archive_sha256','formal_evidence_sha256')),
              'protected delivery evidence missing')
    nodes = {n.get('id'): n for n in d.get('nodes', [])}
    check(len(nodes) == len(d.get('nodes', [])), 'duplicate nodes')
    selected = {k for k in nodes if isinstance(k,str) and k.startswith(PREFIX)}
    check(selected == CORE|CONSUMERS, 'bounded unique subsets required')
    for nid in selected:
        n = nodes[nid]
        core = nid in CORE
        check(n.get('lane') == ('DJC-CORE' if core or 'JOINT' in nid else 'DJC-APPLE')
              and n.get('repository') == ('pcvantol/djconnect' if core or 'JOINT' in nid else 'pcvantol/djconnect-app'), 'owner mismatch')
        check((n.get('status'),n.get('assignment_status')) ==
              (('Completed','CORE_DELIVERED') if core and delivered else ('In progress','IN_PROGRESS') if core else ('Planned','NOT_ISSUED')), 'status overclaim')
        check(n.get('parent_reference') == 'PROJ::ROADMAP::P2-SESSION'
              and n.get('source_ids') == ['OWNER-SESSION-MOMENT-ARTWORK-20261014']
              and n.get('contract_binding') == 'docs/product/SESSION_ARTWORK_DELIVERY_CONTRACT_V1.md'
              and n.get('acceptance_boundary') and n.get('scope'), 'provenance missing')
    edges = [e for e in d.get('edges', []) if e.get('id','').startswith('SESSION-MEDIA-')]
    check(len(edges)==6 and {(e.get('producer'),e.get('consumer')) for e in edges} == PAIRS,
          'prerequisite scope changed')
    for nid in selected:
        incoming = {e['id'] for e in edges if e['consumer']==nid}
        grouped = [eid for g in nodes[nid].get('prerequisite_groups',[]) for eid in g.get('edge_ids',[])]
        check(set(grouped)==incoming and len(grouped)==len(incoming), 'prerequisite groups mismatch')
    for e in edges:
        check(e.get('hard_precedence') is True and e.get('logical_mode')=='AND'
              and e.get('source_ids')==['OWNER-SESSION-MOMENT-ARTWORK-20261014'], 'edge authority mismatch')
    # The full graph includes inherited and maintained nodes; never hide a cycle
    # inside a separately maintained subset.
    allnodes = {**{n['id']:n for n in plan['nodes']},**nodes}
    degree = dict.fromkeys(allnodes,0)
    graph = {n:[] for n in allnodes}
    for e in d.get('edges',[]):
        a,b=e.get('producer'),e.get('consumer')
        check(a in allnodes and b in allnodes,'dangling reference')
        if a in allnodes and b in allnodes and e.get('hard_precedence'):
            graph[a].append(b)
            degree[b]+=1
    ready=[n for n in degree if degree[n]==0]
    seen=0
    while ready:
        node=ready.pop()
        seen+=1
        for target in graph[node]:
            degree[target]-=1
            if degree[target]==0:
                ready.append(target)
    check(seen==len(graph),'cycle')
    return errors
