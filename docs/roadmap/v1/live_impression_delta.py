"""Additive Live-impressie delta; all prior source and delivery records remain intact."""
from copy import deepcopy
import hashlib
from pathlib import Path

PREFIX = 'LIVE-IMPRESSION::'
PATH = 'history/20261119/live-impression-predecessor-maintenance-v16.json'

def validate(plan, previous_validator):
    d = plan['planning_maintenance']
    errors = []
    def check(ok, message):
        if not ok:
            errors.append('maintenance: live impression '+message)
    receipt = d.get('live_impression_receipt',{})
    raw = (Path(__file__).parent / PATH).read_bytes()
    check(receipt.get('predecessor_path')==PATH and receipt.get('predecessor_sha256')==hashlib.sha256(raw).hexdigest(), 'predecessor preservation')
    check(receipt.get('assignment_id')=='DJC-LIVE-IMPRESSION-V1-20261108' and receipt.get('automatic_dispatch') is False, 'owner/effect scope')
    check(receipt.get('source_delivery')=='LOCAL_IMPLEMENTATION_NOT_MERGED' and receipt.get('installed')=='NOT_RUN'
          and receipt.get('live_model')=='NOT_RUN' and receipt.get('native')=='OPEN_APPLE'
          and receipt.get('shared_tv')=='NOT_RUN', 'source and acceptance boundaries')
    nodes=[n for n in d['nodes'] if n['id'].startswith(PREFIX)]
    check({n['id'] for n in nodes}=={PREFIX+x for x in ('CONTRACT','PRODUCER','APPLE','ACCEPTANCE')}, 'bounded family nodes')
    check(all(n['status']==('Planned' if n['id'].endswith('ACCEPTANCE') else 'In progress') for n in nodes), 'no delivery promotion')
    check(all(n['lane']==('DJC-APPLE' if n['id'].endswith('::APPLE') else 'DJC-CORE') for n in nodes), 'owning lanes')
    edges=[e for e in d['edges'] if e['id'].startswith('LIVE-IMPRESSION-')]
    check({(e['producer'],e['consumer']) for e in edges}=={(PREFIX+a,PREFIX+b) for a,b in
        [('CONTRACT','PRODUCER'),('CONTRACT','APPLE'),('PRODUCER','ACCEPTANCE'),('APPLE','ACCEPTANCE')]}
        and len(edges)==4 and all(e['hard_precedence'] is True for e in edges), 'functional dependencies')
    refs=[r for r in d['document_references'] if r['path'] in {'docs/product/LIVE_IMPRESSION_EXPERIENCE_V1.md','docs/technical/LIVE_IMPRESSION_RESEARCH_MEDIA_CONTRACT_V1.md'}]
    check(len(refs)==2 and all(hashlib.sha256((Path(__file__).parents[3]/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in refs), 'versioned design documents')
    prior=deepcopy(plan)
    stripped=deepcopy(d)
    stripped['schema_version']='djconnect-federated-planning-delta/16'
    stripped.pop('live_impression_receipt',None)
    stripped['nodes']=[n for n in stripped['nodes'] if not n['id'].startswith(PREFIX)]
    stripped['edges']=[e for e in stripped['edges'] if not e['id'].startswith('LIVE-IMPRESSION-')]
    stripped['document_references']=[r for r in stripped['document_references'] if r not in refs]
    prior['planning_maintenance']=stripped
    errors.extend(previous_validator(prior))
    return errors
