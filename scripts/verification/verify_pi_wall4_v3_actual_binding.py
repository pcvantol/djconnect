"""Offline qualification of the actual V3 consumer binding, never effect authority.

Requires an existing JSON Schema environment. No network, credentials, workflow,
SSH, ledger, deployment or manifest write is performed. Requests stay in memory.
"""
from __future__ import annotations

import copy
import datetime
import json
from pathlib import Path

from verify_pi_wall4_recovery_v3_contract import joined

RELEASE = Path(__file__).resolve().parents[2] / 'docs/release'
CONSUMER = 'bea606ae8b0f74ca9cf2256007efd7dfd400af63'
PATH = 'PLATFORM_4_0_RC6_PI_WALL4_RECOVERY_V3_MANIFEST.json'


def qualify_binding() -> dict:
    from jsonschema import Draft202012Validator, FormatChecker

    manifest = json.loads((RELEASE / PATH).read_text())
    schema = json.loads((RELEASE / 'PI_RC6_WALL4_RECOVERY_MANIFEST_V3.schema.json').read_text())
    request_schema = json.loads((RELEASE / 'PI_RC6_WALL4_RECOVERY_REQUEST_V3.schema.json').read_text())
    formats = FormatChecker()

    @formats.checks('date-time', raises=(ValueError, TypeError))
    def valid_timestamp(value):
        if not isinstance(value, str) or 'T' not in value:
            return False
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.tzinfo is not None

    for rule in (schema, request_schema):
        Draft202012Validator.check_schema(rule)
    validator = Draft202012Validator(schema, format_checker=formats)
    request_validator = Draft202012Validator(request_schema, format_checker=formats)
    request = {
        key: manifest[key] if key == 'manifest_id' else rule['const']
        for key, rule in request_schema['properties'].items()
    }

    def valid(candidate, selection, consumer=CONSUMER):
        return (
            validator.is_valid(candidate) and request_validator.is_valid(selection)
            and candidate['consumer']['source_sha'] == CONSUMER
            and joined(selection, candidate, consumer=consumer)
        )

    assert validator.is_valid(manifest)
    assert request_validator.is_valid(request)
    assert valid(manifest, request)
    negative = 0
    for key in request:
        changed = copy.deepcopy(request)
        changed[key] = 'WRONG'
        assert not valid(manifest, changed), key
        negative += 1
    for consumer in (
        '0dde0abe22a0859f170a7c1d3eab41f1ade44d37',
        '2e7479d0d15aa11ad3bff4c8103c18dbb1f2c32a', 'a' * 40,
    ):
        assert not valid(manifest, request, consumer)
        negative += 1
    for path in (
        ('consumer', 'source_sha'), ('approval', 'state'),
        ('generated_at',), ('recovery', 'claim_policy'),
        ('recovery', 'root_helper_sha256'), ('recovery', 'readonly_observer_sha256'),
        ('recovery', 'previous_recovery_attempt', 'evidence_sha256'),
        ('required_targets', 0, 'deployment_instance'),
    ):
        changed = copy.deepcopy(manifest)
        parent = changed
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = 'WRONG'
        assert not valid(changed, request), path
        negative += 1
    # A structurally valid replacement consumer is still outside this exact binding.
    changed = copy.deepcopy(manifest)
    changed['consumer']['source_sha'] = 'a' * 40
    assert validator.is_valid(changed)
    assert not valid(changed, request, 'a' * 40)
    negative += 1
    return {
        'status': 'SOURCE_BINDING_ONLY_NOT_OPERATIONAL_AUTHORITY',
        'consumer_Final': CONSUMER, 'positive': 3, 'negative': negative,
        'physical_recovery': 'NOT_ESTABLISHED',
    }


if __name__ == '__main__':
    print(json.dumps(qualify_binding(), sort_keys=True))
