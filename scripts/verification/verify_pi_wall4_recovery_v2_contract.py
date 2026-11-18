"""Pure synthetic schema qualification. Never writes an operational manifest.

Run with an existing JSON Schema2020-12 verifier environment; no dependency install,
network, subprocess, SSH or device operation is performed by this program.
"""
from __future__ import annotations

import copy
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / 'docs/release'
MANIFEST = 'PI_RC6_WALL4_RECOVERY_MANIFEST_V2.schema.json'
REQUEST = 'PI_RC6_WALL4_RECOVERY_REQUEST_V2.schema.json'


def synthetic(schema: dict):
    """Unqualified in-memory structural specimen, never release authority."""
    if 'const' in schema:
        return schema['const']
    if 'enum' in schema:
        return schema['enum'][0]
    kind = schema.get('type')
    if kind == 'object':
        return {key: synthetic(schema['properties'][key]) for key in schema['required']}
    if kind == 'array':
        return [synthetic(schema['items']) for _ in range(schema['minItems'])]
    if schema.get('format') == 'date-time':
        return '2026-10-21T22:15:00Z'
    if schema.get('minLength') == 40:
        return 'f' * 40
    if schema.get('minLength') == 64:
        return 'e' * 64
    if 'manifest_id' == schema.get('title') or 'release-' in schema.get('pattern', ''):
        return 'release-4.0.0-rc.6-pi-wall4-recovery-v2-SYNTHETIC-UNQUALIFIED'
    return 'SYNTHETIC-UNQUALIFIED-NOT-AUTHORITY'


def joined(request: dict, manifest: dict, *, consumer: str) -> bool:
    """Reference semantic joins, not a readiness/authority or Pi implementation."""
    target = manifest['required_targets'][0]
    artifact = manifest['artifact_bindings'][0]
    return (
        manifest['consumer']['source_sha'] == consumer
        and manifest['candidate_sha'] == manifest['repositories'][0]['source_sha']
        and all(request[key] == manifest[key] for key in (
            'candidate_sha', 'manifest_id', 'platform_version', 'release_profile',
            'inventory_sha256',
        ))
        and all(request[key] == target[key] == artifact[key] for key in (
            'target', 'deployment_instance', 'device_profile',
        ))
        and all(request[key] == artifact[key] for key in ('artifact_id', 'artifact_sha256'))
    )


def qualify() -> dict:
    from jsonschema import Draft202012Validator, FormatChecker

    formats = FormatChecker()

    @formats.checks('date-time', raises=(ValueError, TypeError))
    def valid_timestamp(value):
        if not isinstance(value, str) or 'T' not in value:
            return False
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.tzinfo is not None

    schemas = {name: json.loads((RELEASE / name).read_text()) for name in (REQUEST, MANIFEST)}
    specimens = {}
    validators = {}
    positive = negative = 0
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=formats)
        specimen = synthetic(schema)
        validator.validate(specimen)
        positive += 1
        specimens[name], validators[name] = specimen, validator

        def reject(candidate):
            nonlocal negative
            assert not validator.is_valid(candidate), (name, candidate)
            negative += 1

        def traverse(node, rule, path=()):
            if rule.get('type') == 'object':
                modified = copy.deepcopy(specimen)
                parent = modified
                for part in path:
                    parent = parent[part]
                parent['unexpected_scope_override'] = 'wall-10inch'
                reject(modified)
                for key in rule['required']:
                    modified = copy.deepcopy(specimen)
                    parent = modified
                    for part in path:
                        parent = parent[part]
                    del parent[key]
                    reject(modified)
                    traverse(node[key], rule['properties'][key], path + (key,))
            elif rule.get('type') == 'array':
                for replacement in ([], [copy.deepcopy(node[0]) for _ in range(rule['maxItems'] + 1)]):
                    modified = copy.deepcopy(specimen)
                    parent = modified
                    for part in path[:-1]:
                        parent = parent[part]
                    parent[path[-1]] = replacement
                    reject(modified)
                traverse(node[0], rule['items'], path + (0,))
            elif 'const' in rule:
                modified = copy.deepcopy(specimen)
                parent = modified
                for part in path[:-1]:
                    parent = parent[part]
                parent[path[-1]] = 'WRONG-CONSTANT'
                reject(modified)

        traverse(specimen, schema)

    manifest, request = specimens[MANIFEST], specimens[REQUEST]
    consumer = manifest['consumer']['source_sha']
    assert joined(request, manifest, consumer=consumer)
    positive += 1
    for key, wrong in (
        ('manifest_id', 'release-4.0.0-rc.6-pi-wall4-recovery-v2-OTHER'),
        ('deployment_instance', 'wall-10inch'), ('device_profile', 'pi5-arm64'),
        ('candidate_sha', 'a' * 40), ('artifact_sha256', 'b' * 64),
    ):
        changed = copy.deepcopy(request)
        changed[key] = wrong
        assert not joined(changed, manifest, consumer=consumer)
        negative += 1
    assert not joined(request, manifest, consumer='a' * 40)
    negative += 1
    old = json.loads((RELEASE / 'PLATFORM_4_0_RC6_PI_OPERATIONAL_MANIFEST.json').read_text())
    assert not validators[MANIFEST].is_valid(old)
    assert not Draft202012Validator(json.loads(
        (RELEASE / 'PI_TWO_HOST_OPERATIONAL_MANIFEST_V3.schema.json').read_text()
    )).is_valid(manifest)
    negative += 2
    for path, wrong in (
        (('schema_version',), 3),
        (('kind',), 'platform_release_operational_manifest'),
        (('required_targets', 0, 'deployment_instance'), 'wall-10inch'),
        (('artifact_bindings', 0, 'device_profile'), 'pi5-arm64'),
        (('recovery', 'operation'), 'deployment'),
        (('recovery', 'workflow_path'), '.github/workflows/deploy.yml'),
        (('recovery', 'manifest_path'), 'docs/release/PLATFORM_4_0_RC6_PI_OPERATIONAL_MANIFEST.json'),
        (('recovery', 'smoke_workflow_path'), '.github/workflows/smoke-rc6.yml'),
        (('recovery', 'aggregate_disposition'), 'DEPLOYMENT_OPERATIONAL'),
        (('consumer', 'smoke_contract_id'), 'pi-rc6-instance-readback-v1'),
        (('generated_at',), 'not-a-date'),
        (('approval', 'approved_at'), 'not-a-date'),
        (('manifest_id',), 'release-4.0.0-rc.6-pi-wall4-recovery-v2-bad\n'),
    ):
        changed = copy.deepcopy(manifest)
        parent = changed
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = wrong
        assert not validators[MANIFEST].is_valid(changed), path
        negative += 1
    # Actual V1 manifest remains historical and cannot be consumed as V2.
    v1 = json.loads((RELEASE / 'PLATFORM_4_0_RC6_PI_WALL4_RECOVERY_MANIFEST.json').read_text())
    assert not validators[MANIFEST].is_valid(v1)
    assert not Draft202012Validator(json.loads(
        (RELEASE / 'PI_RC6_WALL4_RECOVERY_MANIFEST_V1.schema.json').read_text()
    )).is_valid(manifest)
    negative += 2
    for path, wrong in (
        (('schema_version',), 4),
        (('consumer', 'recovery_contract_id'), 'pi-rc6-wall4-recovery-v1'),
        (('consumer', 'smoke_contract_id'), 'pi-rc6-wall4-recovery-readback-v1'),
        (('recovery', 'root_helper_sha256'), '11ce41115c7aa5ac34e568f3ea9008915f342bc3272850b56c61eed19a760ab9'),
        (('recovery', 'readonly_observer_sha256'), 'f' * 64),
        (('recovery', 'claim_policy'), 'RESET_OLD_CLAIM_AND_RETRY'),
        (('recovery', 'previous_recovery_attempt', 'workflow_run_id'), '39669504016'),
        (('recovery', 'previous_recovery_attempt', 'root_helper_sha256'), 'c395af61f47c42633c65013d61853c66c442781832ed4225d035d9209e9f0be2'),
        (('recovery', 'previous_recovery_attempt', 'intent_dispatched'), False),
        (('recovery', 'previous_recovery_attempt', 'remote_may_still_be_running'), False),
        (('recovery', 'previous_recovery_attempt', 'result'), 'SMOKE_PASS'),
        (('recovery', 'previous_recovery_attempt', 'evidence_sha256'), 'f' * 64),
        (('recovery', 'previous_recovery_attempt', 'disposition'), 'CANCELLED_NO_EFFECTS'),
    ):
        changed = copy.deepcopy(manifest)
        parent = changed
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = wrong
        assert not validators[MANIFEST].is_valid(changed), path
        negative += 1
    return {'decision': 'SYNTHETIC_V2_SCHEMA_AND_REFERENCE_JOIN_PASS',
            'positive': positive, 'negative': negative, 'device_effects': 0,
            'approval_or_readiness': False}


if __name__ == '__main__':
    print(json.dumps(qualify(), sort_keys=True))
