"""Cost-free container setup evidence; never a model or catalogue grant.

No provider credentials, SDK client or model invocation enters this probe.
The consumed manual workflows remain consumed irrespective of its result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.verification.run_help_catalogue_qualification_20261023 import (  # noqa: E402
    IMAGE, container_absent, product_hashes, profile_source_hashes as historical_profile_source_hashes, write_json,
)


def profile_source_hashes(source):
    # Current cost-free probe must bind the new observer actually imported by
    # the container. Keep consumed runner/profile maps byte-identical.
    hashes = historical_profile_source_hashes(source)
    for helper in ('scripts/verification/artist_public_input_receipts.py',
                   'scripts/verification/artist_answer_review_receipts.py',
                 'scripts/verification/artist_typed_receipts.py'):
        hashes[helper] = hashlib.sha256((source / helper).read_bytes()).hexdigest()
    return hashes


PROBE = r'''
import contextlib, io, json, os
from pathlib import Path
value = {'schema_version': 1, 'status': 'FAIL_SETUP_ONLY', 'phase': 'ownership',
    'owner_matches': False, 'lab_write': False, 'source_hashes': {},
    'checkpoint_initialized': False, 'model_calls': 0, 'qualification': 'NOT_QUALIFIED'}
code = 1
try:
    assert not any(k in os.environ for k in ('OPENAI_API_KEY', 'DJCONNECT_GOLDEN_OPENAI_API_KEY'))
    value['owner_matches'] = os.getuid() == Path('/lab').stat().st_uid
    assert value['owner_matches']
    with Path('/lab/synthetic-permission-probe').open('x') as f:
        f.write('synthetic-only')
    value['lab_write'] = True
    value['phase'] = 'source_import'
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from scripts.verification.verify_ask_dj_contextual_dialogue_http import hashes
        from scripts.verification.catalogue_progress import CatalogueProgress, validate_progress
        from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases, manifest_digest
    value['phase'] = 'checkpoint'
    ids = [x['id'] for x in cases() + chain_cases()]
    manifest = manifest_digest()
    CatalogueProgress(Path('/lab/costfree-progress.json'), case_ids=ids, manifest=manifest)
    progress = json.loads(Path('/lab/costfree-progress.json').read_text())
    assert validate_progress(progress, case_ids=ids, manifest=manifest)
    assert progress['sdk_attempts_reserved'] == progress['sdk_completed_responses'] == 0
    value['checkpoint_initialized'] = True
    value['source_hashes'] = hashes()
    value.update(status='PASS_SETUP_ONLY', phase='complete')
    code = 0
except BaseException:
    # No arbitrary exception text, imports' output, prompts or environment values.
    pass
print(json.dumps(value, allow_nan=False))
raise SystemExit(code)
'''


def command(source: Path, lab: Path, name: str) -> list[str]:
    return ['docker', 'run', '--rm', '-i', '--name', name,
        '--user', f'{os.getuid()}:{os.getgid()}', '--network', 'none',
        '--memory', '1g', '--cpus', '2', '--pids-limit', '256',
        '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--entrypoint', 'python', '--workdir', '/candidate',
        '-e', 'PYTHONPATH=/candidate', '-e', 'PYTHONDONTWRITEBYTECODE=1',
        '-e', 'DJC_SOURCE_ROOT=/candidate', '-v', str(source) + ':/candidate:ro',
        '-v', str(lab) + ':/lab', IMAGE, '-c', PROBE]


def valid_probe(value, expected):
    return (type(value) is dict and set(value) == {
        'schema_version', 'status', 'phase', 'owner_matches', 'lab_write',
        'source_hashes', 'checkpoint_initialized', 'model_calls', 'qualification'}
        and type(value['schema_version']) is int and value['schema_version'] == 1
        and value['status'] == 'PASS_SETUP_ONLY' and value['phase'] == 'complete'
        and all(value[k] is True for k in ('owner_matches', 'lab_write', 'checkpoint_initialized'))
        and type(value['model_calls']) is int and value['model_calls'] == 0
        and value['qualification'] == 'NOT_QUALIFIED' and value['source_hashes'] == expected)


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate_preflight_field')
        value[key] = item
    return value


def run(source: Path, directory: Path):
    source = source.resolve(strict=True)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    lab = directory / 'private-synthetic-lab'
    lab.mkdir(mode=0o700)
    before = product_hashes(source)
    if len(before) != 272 or lab.stat().st_uid != os.getuid():
        raise ValueError('preflight_source_or_owner_invalid')
    expected = profile_source_hashes(source)
    name = 'djc-help-preflight-' + secrets.token_hex(8)
    result, value, failure = None, None, None
    try:
        result = subprocess.run(command(source, lab, name), input=b'',
            capture_output=True, timeout=180, check=False)
        if len(result.stdout) > 128 * 1024:
            raise ValueError('preflight_output_oversized')
        value = json.loads(result.stdout.decode('utf-8', errors='strict'), object_pairs_hook=unique)
    except subprocess.TimeoutExpired:
        failure = 'BOUNDED_CONTAINER_TIMEOUT'
    except (OSError, ValueError):
        failure = 'CONTAINER_OR_CLOSED_RECEIPT_UNAVAILABLE'
    finally:
        absent = False
        try:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30, check=False)
            absent = container_absent(name)
        except (OSError, subprocess.SubprocessError):
            pass
    after = product_hashes(source)
    passed = (failure is None and result is not None and result.returncode == 0
              and valid_probe(value, expected) and absent and before == after)
    receipt = {'schema_version': 1, 'status': 'PASS_SETUP_ONLY' if passed else 'FAIL_SETUP_ONLY',
        'qualification': 'NOT_QUALIFIED', 'failure': failure,
        'phase': value.get('phase') if isinstance(value, dict) and value.get('phase') in {
            'ownership', 'source_import', 'checkpoint', 'complete'} else 'UNKNOWN',
        'network': 'none', 'credentials': 'NONE', 'model_calls': 0,
        'own_container': 'VERIFIED_ABSENT' if absent else 'UNKNOWN',
        'product_hashes_before': before, 'product_hashes_after': after,
        'expected_source_hashes': expected,
        'scope': 'IMPORT_OWNERSHIP_AND_ZERO_CALL_CHECKPOINT_ONLY_NOT_PAID_ANSWERS_OR_EXECUTION_AUTHORITY'}
    write_json(directory / 'preflight.json', receipt)
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.source_root, args.report_dir))
