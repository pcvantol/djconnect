"""Bounded current corrective work, preserving historical delivery receipts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

PRIOR = 'history/20261017/settings-finalization-maintenance-v14.json'
NODE = 'CORRECTION::CORE::PERSONAL-DJ-EXPERIENCE'


def validate(plan, previous_validator):
    delta = plan['planning_maintenance']
    receipt = delta.get('experience_reconciliation_receipt', {})
    errors = []

    def check(ok, reason):
        if not ok:
            errors.append('maintenance: experience reconciliation ' + reason)

    raw = (Path(__file__).parent / PRIOR).read_bytes()
    prior = json.loads(raw)
    check(receipt.get('previous_delta') == PRIOR
          and receipt.get('previous_delta_sha256') == hashlib.sha256(raw).hexdigest(), 'prior bytes')
    check(receipt.get('schema_version') == 'djconnect-experience-reconciliation/1'
          and receipt.get('source_delivery') == 'UNPUBLISHED'
          and receipt.get('overall_acceptance') == 'OPEN', 'local evidence boundary')
    check(receipt.get('native') == 'OPEN_APPLE' and receipt.get('installed') == 'NOT_RUN'
          and receipt.get('audible') == 'NOT_RUN' and receipt.get('consumer_writes') is False
          and receipt.get('automatic_dispatch') is False, 'no consumer or installation overclaim')
    components = receipt.get('components', [])
    expected = {'legacy-announcement', 'durable-flow-retention', 'public-music-research',
                'tts-mood-prosody', 'all-family-narration', 'published-narration-golden', 'track-insight', 'voice-preview'}
    check(len(components) == len(expected) and {r.get('id') for r in components} == expected,
          'complete unique requirement inventory')
    check(all(r.get('status') not in {'Completed', 'PASS', 'CLOSED'} for r in components),
          'no unqualified component closure')
    nodes = [n for n in delta.get('nodes', []) if n.get('id') == NODE]
    check(len(nodes) == 1 and nodes[0].get('status') == 'In progress'
          and nodes[0].get('parent_reference') == 'SPEECH::CORE::REALIZATION'
          and nodes[0].get('lane') == 'DJC-CORE', 'existing family corrective child')
    edges = [e for e in delta.get('edges', []) if e.get('id', '').startswith('EXPERIENCE-CORRECTION-')]
    check(len(edges) == 2 and {(e.get('producer'), e.get('consumer')) for e in edges} == {
        ('SPEECH::CORE::REALIZATION', NODE), (NODE, 'SPEECH::JOINT::ACCEPTANCE')}
        and all(e.get('hard_precedence') is True and e.get('logical_mode') == 'AND' for e in edges),
          'hard AND corrective acceptance dependency')
    stripped = deepcopy(delta)
    stripped.pop('experience_reconciliation_receipt', None)
    stripped['schema_version'] = prior['schema_version']
    stripped['nodes'] = [n for n in stripped['nodes'] if n.get('id') != NODE]
    stripped['edges'] = [e for e in stripped['edges'] if not e.get('id', '').startswith('EXPERIENCE-CORRECTION-')]
    references = stripped.get('document_references', [])
    check({r['path'] for r in prior['document_references']} <= {r['path'] for r in references},
          'prior document references retained')
    check(all((Path(__file__).parents[3] / r['path']).is_file()
              and hashlib.sha256((Path(__file__).parents[3] / r['path']).read_bytes()).hexdigest() == r['sha256']
              for r in references), 'current canonical document bytes')
    current_references = stripped['document_references']
    stripped['document_references'] = prior['document_references']
    check(stripped == prior, 'historical receipts and unrelated lanes unchanged')
    stripped['document_references'] = current_references
    previous = deepcopy(plan)
    previous['planning_maintenance'] = stripped
    errors.extend(previous_validator(previous))
    return errors
