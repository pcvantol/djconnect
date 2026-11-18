"""One corrected mixed-public-source Help100 qualification; consumed earlier slots stay immutable."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

# Reuse immutable authority-independent file/JSON validators only. None of the
# consumed runner's admission, execute, finish, grant, deadlines or SHA is used.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.verification import run_help_catalogue_qualification_20261023 as safe

GRANT = 'DJC-CORE-HELP100-PUBLIC-SOURCE-WITNESS-20261025-ONCE'
WORKFLOW = 'pcvantol/djconnect/.github/workflows/help100-public-source-witness-20261025.yml@refs/heads/main'
CONTENT_SOURCE = 'e041b21435b9180aedfa573a44576ec2a0528800'
SOURCE_FINAL = 'e041b21435b9180aedfa573a44576ec2a0528800'
MANIFEST = 'f6fcebd0349768b83a6824d6dcfeb15e3b229e0c1a168dec4c5a044e1ac43b48'
IMAGE = 'ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4'
START = datetime(2026, 10, 25, 4, 30, tzinfo=timezone.utc)
LAST_START = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)
MAX_SECONDS = 1800
require = safe.require


def admit(env, now):
    fixed = {'GITHUB_REPOSITORY': 'pcvantol/djconnect', 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_WORKFLOW_REF': WORKFLOW, 'GITHUB_ACTOR': 'pcvantol',
        'GITHUB_TRIGGERING_ACTOR': 'pcvantol', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1', 'DJC_HELP100_GRANT': GRANT}
    require(all(env.get(k) == v for k, v in fixed.items()), 'CONTEXT_DENIED')
    require(START <= now < LAST_START, 'WINDOW_CLOSED')
    sha = env.get('GITHUB_SHA', '')
    require(re.fullmatch('[a-f0-9]{40}', sha) and env.get('DJC_EXPECTED_MAIN_SHA') == sha,
            'RESTRICTION_SHA_MISMATCH')
    require(re.fullmatch('[1-9][0-9]{0,19}', env.get('GITHUB_RUN_ID', '')), 'RUN_INVALID')
    return {'grant': GRANT, 'source': sha, 'run_id': env['GITHUB_RUN_ID'],
            'run_number': 1, 'run_attempt': 1}


def verify_original_base(root, baseline):
    """Read original Git blobs; paid admission requires a full-history checkout."""
    for name, digest in baseline.items():
        require(name.startswith('custom_components/djconnect/') and '..' not in Path(name).parts,
                'BASE_PATH_INVALID')
        actual = subprocess.check_output(['git', '-C', str(root), 'show', CONTENT_SOURCE + ':' + name])
        require(hashlib.sha256(actual).hexdigest() == digest, 'ORIGINAL_BASE_BLOB_CHANGED')


def profile_source_hashes(root):
    hashes = safe.profile_source_hashes(root)
    name = 'scripts/verification/artist_public_input_receipts.py'
    hashes[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    return hashes


def maps(root):
    pin = json.loads((Path(__file__).with_name('help100_public_source_witness_content_20261025.json')).read_text())
    require(pin['source_base'] == CONTENT_SOURCE
        and pin['basis'] == 'reviewed_public_source_witness_hashes_not_base_bytes', 'CONTENT_PIN_INVALID')
    baseline = pin['base_product_hashes']
    require(len(baseline) == 264 and set(baseline) == set(pin['product_hashes']), 'BASE_INVENTORY_INVALID')
    verify_original_base(root, baseline)
    changed = sorted(name for name in baseline if baseline[name] != pin['product_hashes'][name])
    require(changed == pin['reviewed_product_changes'] and len(changed) == 5,
            'REMEDIATION_DELTA_CHANGED')
    require(safe.product_hashes(root) == pin['product_hashes'], 'PRODUCT_CHANGED')
    require(profile_source_hashes(root) == pin['profile_hashes'], 'PROFILE_CHANGED')
    return pin


def qualification(sha):
    return safe.github_qualification(sha)


def source(root, sha):
    require(not root.is_symlink() and safe.git(root, 'rev-parse', 'HEAD') == sha,
            'SOURCE_MISMATCH')
    require(not safe.git(root, 'status', '--porcelain', '--untracked-files=normal'), 'SOURCE_DIRTY')
    return maps(root)


def profile(root):
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location('fresh_help100_profile',
        root / 'scripts/verification/askdj_example_catalogue_golden.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(len(module.cases()) == 70 and len(module.chain_cases()) == 30
            and module.manifest_digest() == MANIFEST and module.MAX_MODEL_CALLS == 392
            and module.MAX_OUTPUT_TOKENS == 3000, 'PROFILE_INVALID')
    return module


class Journal:
    def __init__(self, directory):
        self.directory, self.healthy, self.terminal = directory, True, False

    def write(self, stage, **closed):
        require(self.healthy and not self.terminal, 'DIAGNOSTIC_CLOSED')
        try:
            safe.write_json(self.directory / (stage + '.json'), {'schema': 1, 'stage': stage, **closed})
        except BaseException:
            self.healthy = False
            raise
        self.terminal = stage == 'terminal'


def docker(*args, timeout=30, **kwargs):
    return subprocess.run(['docker', *args], capture_output=True, text=True,
                          timeout=timeout, check=False, **kwargs)


def image_identity():
    image = docker('image', 'inspect', IMAGE)
    require(image.returncode == 0, 'IMAGE_UNAVAILABLE')
    metadata = json.loads(image.stdout)[0]
    identity = metadata['Id']
    require(IMAGE in metadata.get('RepoDigests', [])
        and re.fullmatch('sha256:[a-f0-9]{64}', identity)
        and metadata.get('Os') == 'linux' and metadata.get('Architecture') == 'amd64', 'IMAGE_MISMATCH')
    return identity


def setup_only(root, directory):
    """Same Actions host/image/UID/0700, no secret env/input and network-none."""
    image_id, identity = image_identity(), None
    work = directory / 'private-setup'
    work.mkdir(mode=0o700)
    name = 'djc-help100-setup-' + secrets.token_hex(10)
    label = 'setup-' + secrets.token_hex(10)
    try:
        created = docker('create', '--platform', 'linux/amd64', '--name', name, '--label', 'djc.help100=' + label,
            '--pull=never', '--network', 'none', '--user', f'{os.getuid()}:{os.getgid()}',
            '--memory', '2g', '--cpus', '2', '--pids-limit', '256', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--entrypoint', 'python', '--workdir', '/candidate',
            '-e', 'PYTHONPATH=/candidate', '-e', 'PYTHONDONTWRITEBYTECODE=1',
            '-e', 'DJC_SOURCE_ROOT=/candidate', '-e', 'DJC_SAFETY_PROBE=catalogue_golden',
            '-v', str(root) + ':/candidate:ro', '-v', str(work) + ':/lab', IMAGE,
            '/candidate/tools/verification/help100_preflight.py')
        require(created.returncode == 0 and re.fullmatch('[a-f0-9]{64}', created.stdout.strip()),
                'SETUP_CONTAINER_FAILED')
        identity = created.stdout.strip()
        state(identity, image_id, label)
        with (work / 'private.log').open('x') as log:
            result = subprocess.run(['docker', 'start', '-a', identity], stdout=log,
                stderr=subprocess.STDOUT, timeout=120, check=False)
        require(result.returncode == 0, 'SETUP_FAILED')
        value = safe.report_safe(safe.read_work_file(work / 'setup-preflight.json', maximum=2048),
            'SYNTHETIC-NEVER-AUTHORIZED-SETUP-ONLY')
        require(set(value) == {'schema', 'status', 'actual_HA_setup', 'uid', 'request_dispatches',
            'test_credential', 'openai_version', 'httpx_version'} and value['schema'] == 1
            and value['status'] == 'PASS_SETUP_ONLY_NOT_QUALIFIED'
            and value['actual_HA_setup'] == 'FIRST_MODEL_REQUEST_FENCED'
            and value['uid'] == os.getuid() and value['request_dispatches'] == 0
            and value['test_credential'] == 'SYNTHETIC_ONLY'
            and all(re.fullmatch('[0-9]{1,4}(?:\\.[0-9]{1,4}){1,3}', value[k])
                    for k in ('openai_version', 'httpx_version')), 'SETUP_RECEIPT_INVALID')
    finally:
        if identity is None:
            found = docker('inspect', name)
            if found.returncode == 0:
                row = json.loads(found.stdout)[0]
                validate_identity(row, row['Id'], image_id, label)
                identity = row['Id']
        absent = safe.container_absent(name) if identity is None else cleanup(identity, image_id, label)[2]
        safe.write_json(directory / 'setup-cleanup.json', {'state': 'VERIFIED_ABSENT' if absent else 'UNKNOWN'})
        require(absent, 'SETUP_CLEANUP_UNKNOWN')
    value['own_container'] = 'VERIFIED_ABSENT'
    safe.write_json(directory / 'setup-preflight.json', value)


def state(identity, image_id, label):
    result = docker('inspect', identity)
    require(result.returncode == 0, 'STATE_UNAVAILABLE')
    row = json.loads(result.stdout)[0]
    validate_identity(row, identity, image_id, label)
    value = row['State']
    require(type(value['Running']) is bool and type(value['ExitCode']) is int
            and type(value['OOMKilled']) is bool
            and value['Status'] in {'created', 'running', 'paused', 'restarting', 'removing', 'exited', 'dead'},
            'STATE_INVALID')
    return {'status': value['Status'], 'running': value['Running'],
            'exit_code': value['ExitCode'], 'oom_killed': value['OOMKilled']}


def validate_identity(row, identity, image_id, label):
    require(row['Id'] == identity and row['Config']['Image'] == IMAGE
        and row['Config']['Labels'].get('djc.help100') == label, 'CONTAINER_IDENTITY')
    if row['Image'] != image_id:
        # Docker's containerd store exposes the index as Image and the selected
        # platform manifest separately. Classic Docker exposes image config ID.
        descriptor = row.get('ImageManifestDescriptor', {})
        require(row['Image'] == IMAGE.split('@')[1]
            and descriptor.get('digest') == image_id
            and descriptor.get('platform', {}).get('architecture') == 'amd64'
            and descriptor.get('platform', {}).get('os') == 'linux', 'CONTAINER_IMAGE_JOIN')


def cleanup(identity, image_id, label):
    # identity was captured from our create RPC (or independently joined to our
    # random name/label/image). A failed diagnostic inspect must not leave its
    # already-started paid task running. Docker IDs cannot be reused.
    before = after = None
    try:
        before = state(identity, image_id, label)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        pass
    try:
        docker('stop', '--time', '5', identity, timeout=12)
    finally:
        try:
            after = state(identity, image_id, label)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        if after is None or after['running']:
            docker('kill', identity, timeout=10)
        require(docker('rm', '-f', identity).returncode == 0, 'REMOVE_FAILED')
    return before, after, safe.container_absent(identity)


def artist_wire_complete(report, cases):
    """One exact original-generation witness per frozen artist case and locale."""
    expected = {case['id']: case['language'] for case in cases if case.get('entry_id') == 'listen.artist'}
    if len(expected) != 5 or set(expected.values()) != {'en', 'nl', 'de', 'fr', 'es'}:
        return False
    seen = set()
    for call in report.get('model_calls', []):
        if not isinstance(call, dict) or 'artist_generation_wire' not in call:
            continue
        identifier, wire = call.get('case_id'), call['artist_generation_wire']
        if (not isinstance(identifier, str) or identifier not in expected or identifier in seen or not isinstance(wire, dict)
                or set(wire) != {'research_schema', 'language', 'drafts_requested',
                    'wire_contract_first', 'trusted_instructions_sha256'}
                or type(wire['research_schema']) is not int or wire['research_schema'] != 3
                or wire['language'] != expected[identifier] or wire['drafts_requested'] is not True
                or wire['wire_contract_first'] is not True
                or not isinstance(wire['trusted_instructions_sha256'], str)
                or not re.fullmatch('[a-f0-9]{64}', wire['trusted_instructions_sha256'])):
            return False
        seen.add(identifier)
    return seen == set(expected)


def finish(root, directory, work, coordinate, pin, key, code, absent, error):
    """Only validated receipts leave private-work; strict original acceptance stays."""
    result = {**coordinate, 'status': 'FAIL_OR_INCOMPLETE', 'error': error,
        'max_attempts': 392, 'max_output_tokens': 3000, 'max_seconds': MAX_SECONDS,
        'automatic_whole_test_reruns': 0, 'external_billing': 'UNKNOWN_NOT_A_BILLING_RECEIPT',
        'own_container_absent': absent, 'process_exit_code': code,
        'catalogue_publication': 'PENDING_INDEPENDENT_EDITORIAL_REVIEW',
        'sdk_attempts_reserved': None, 'sdk_completed_responses': None,
        'completed_cases': None, 'findings': []}
    current = profile(root)
    ids = [row['id'] for row in current.cases() + current.chain_cases()]
    progress = None
    try:
        from scripts.verification.catalogue_progress import validate_progress
        value = safe.report_safe(safe.read_work_file(work / 'catalogue-progress.json', maximum=16384), key)
        require(validate_progress(value, case_ids=ids, manifest=MANIFEST), 'PROGRESS_INVALID')
        safe.write_json(directory / 'catalogue-progress.json', value)
        progress = value
        result.update(sdk_attempts_reserved=value['sdk_attempts_reserved'],
            sdk_completed_responses=value['sdk_completed_responses'], completed_cases=len(value['completed_cases']))
    except (OSError, ValueError, TypeError, KeyError):
        result['findings'].append('PROGRESS_UNAVAILABLE_OR_INVALID')
    try:
        unchanged = source(root, coordinate['source']) == pin
    except (OSError, ValueError, subprocess.SubprocessError):
        unchanged = False
    result['all264_source_hashes_before_after_equal'] = unchanged
    try:
        raw = safe.read_work_file(work / 'catalogue-golden.json', maximum=8 * 1024 * 1024)
        report = safe.report_safe(raw, key)
        require(type(report) is dict and report.get('manifest_sha256') == MANIFEST
            and report.get('source_hashes') == pin['profile_hashes']
            and report.get('source_unchanged') is True, 'REPORT_BINDING_INVALID')
        # Keep a valid source-bound report even if its content/test outcome failed.
        safe.write_bytes(directory / 'catalogue-golden.json', raw)
        valid = current.validate_report(report, source_hashes=pin['profile_hashes'])
        wire_valid = artist_wire_complete(report, current.cases())
        result['artist_generation_wire_verified'] = bool(wire_valid)
        from scripts.verification.artist_public_input_receipts import artist_public_inputs_complete
        original_inputs_valid = artist_public_inputs_complete(report)
        result['artist_original_public_inputs_verified'] = bool(original_inputs_valid)
        valid = valid and wire_valid and original_inputs_valid
        complete = (progress is not None and progress['outcome'] == 'COMPLETE_NOT_QUALIFIED'
            and progress['completed_cases'] == ids and not progress['failed_cases']
            and progress['sdk_attempts_reserved'] == len(report.get('model_calls', []))
            and progress['sdk_completed_responses'] == sum(c.get('completed') is True
                for c in report.get('model_calls', [])))
        result.update(strict_validator=bool(valid), progress_report_counts_joined=bool(complete),
            report_sha256=hashlib.sha256(raw).hexdigest())
        if code == 0 and error == 'NONE' and absent and unchanged and valid and complete:
            result['status'] = 'PASS_EXECUTION_PENDING_EDITORIAL_REVIEW'
    except (OSError, ValueError, TypeError, KeyError, AssertionError):
        result['findings'].append('REPORT_UNAVAILABLE_OR_INVALID')
    for stage in ('IMPORT', 'MAIN', 'TERMINAL'):
        try:
            value = safe.report_safe(safe.read_work_file(work / ('child-' + stage + '.json'), maximum=1024), key)
            require(set(value) == {'schema', 'stage', 'error', 'qualification'}
                and value['schema'] == 1 and value['stage'] == stage
                and value['qualification'] == 'NOT_QUALIFIED'
                and value['error'] in {'NONE', 'UNKNOWN', 'IMPORT_FAILED', 'INPUT_OR_SETUP_INVALID',
                    'PERMISSION_DENIED', 'IO_FAILED', 'TIMEOUT_OR_CANCELLED', 'ACTUAL_TEST_FAILED',
                    'ASSERTION_FAILED', 'MODEL_AUTHENTICATION_FAILED', 'MODEL_PERMISSION_DENIED',
                    'MODEL_RATE_LIMIT', 'MODEL_TIMEOUT', 'MODEL_CONNECTION_FAILED', 'MODEL_HTTP_FAILED'},
                'CHILD_DIAGNOSTIC_INVALID')
            safe.write_json(directory / ('child-' + stage + '.json'), value)
        except (OSError, ValueError, TypeError, KeyError):
            result['findings'].append('CHILD_' + stage + '_UNAVAILABLE')
    safe.write_json(directory / 'summary.json', result)
    return 0 if result['status'].startswith('PASS_EXECUTION') else 1


def execute(root, directory, coordinate, pin, env, journal):
    identity, image_id, key, code, absent, primary = None, None, '', None, True, None
    name = None
    error, outcome = 'UNKNOWN', 1
    work = directory / 'private-work'
    wall_end, mono_end = time.time() + MAX_SECONDS, time.monotonic() + MAX_SECONDS
    def remaining(reserve=0):
        seconds = min(wall_end - time.time(), mono_end - time.monotonic()) - reserve
        require(seconds > 0, 'BUDGET_EXPIRED')
        return seconds
    try:
        admitted = json.loads((directory / 'admission.json').read_text())
        require(admitted['coordinates'] == coordinate and admitted['content'] == pin,
                'ADMISSION_CHANGED')
        # Registry index digest, platform manifest and image-config ID differ.
        # Keep the immutable RepoDigest fence and use actual config ID for our
        # container join; never equate index digest with image-config digest.
        image_id = image_identity()
        readiness = json.loads((directory / 'setup-preflight.json').read_text())
        require(readiness.get('status') == 'PASS_SETUP_ONLY_NOT_QUALIFIED'
            and readiness.get('own_container') == 'VERIFIED_ABSENT', 'SETUP_NOT_READY')
        require(journal.healthy and admit(env, datetime.now(timezone.utc)) == coordinate, 'CONTEXT_CHANGED')
        safe.reserve_once(directory / 'once-reservation.json', coordinate)
        journal.write('reserved', qualification='NOT_QUALIFIED')
        # Everything after reservation, including key/work setup, is in finally.
        key = env.get('DJCONNECT_GOLDEN_OPENAI_API_KEY', '')
        require(isinstance(key, str) and 20 <= len(key) <= 8192, 'CREDENTIAL_UNAVAILABLE')
        work.mkdir(mode=0o700)
        name = 'djc-help100-fresh-' + secrets.token_hex(10)
        command = ['create', '--platform', 'linux/amd64', '-i', '--name', name, '--label', 'djc.help100=' + coordinate['run_id'],
            '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}', '--network', 'bridge',
            '--memory', '2g', '--cpus', '2', '--pids-limit', '256', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--entrypoint', 'python', '--workdir', '/candidate',
            '-e', 'PYTHONPATH=/candidate', '-e', 'PYTHONDONTWRITEBYTECODE=1',
            '-e', 'DJC_SOURCE_ROOT=/candidate', '-e', 'DJC_SAFETY_PROBE=catalogue_golden',
            '-e', 'DJC_HELP100_WALL_END=' + str(wall_end - 30),
            '-e', 'DJC_HELP100_MONO_END=' + str(mono_end - 30),
            '-v', str(root) + ':/candidate:ro', '-v', str(work) + ':/lab', IMAGE,
            '/candidate/tools/verification/help100_child.py']
        # A CLI timeout may still have created a container; absence is unknown
        # until the exact unique name/label/image has been reconciled below.
        absent = False
        created = docker(*command, timeout=min(30, remaining(30)))
        require(created.returncode == 0 and re.fullmatch('[a-f0-9]{64}', created.stdout.strip()),
                'CONTAINER_CREATE_FAILED')
        identity, absent = created.stdout.strip(), False
        require(state(identity, image_id, coordinate['run_id'])['status'] == 'created', 'CONTAINER_STATE')
        journal.write('container-created', identity=identity, image=image_id)
        require(journal.healthy, 'DIAGNOSTIC_CLOSED')
        with (work / 'private.log').open('x') as log:
            child = subprocess.Popen(['docker', 'start', '-a', '-i', identity],
                stdin=subprocess.PIPE, text=True, stdout=log, stderr=subprocess.STDOUT)
            payload = json.dumps({'api_key': key, 'model': 'gpt-6-luna', 'max_tokens': 3000})
            try:
                while True:
                    try:
                        child.communicate(input=payload, timeout=min(0.5, remaining(20)))
                        break
                    except subprocess.TimeoutExpired:
                        # communicate retains its original buffered input; never
                        # start another process/container or send a second key.
                        payload = None
                code = child.returncode
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
        error = 'NONE' if code == 0 else 'CHILD_EXIT_NONZERO'
    except BaseException as exc:
        primary = exc
        error = ('TIMEOUT' if isinstance(exc, subprocess.TimeoutExpired) else
                 'CANCELLED' if isinstance(exc, (KeyboardInterrupt, SystemExit)) else 'SETUP_OR_EXECUTION_FAILED')
    finally:
        if name is not None and identity is None:
            try:
                found = docker('inspect', name)
                if found.returncode == 0:
                    row = json.loads(found.stdout)[0]
                    validate_identity(row, row['Id'], image_id, coordinate['run_id'])
                    identity = row['Id']
                else:
                    absent = safe.container_absent(name)
            except BaseException:
                absent = False
        if identity is not None:
            try:
                before, after, absent = cleanup(identity, image_id, coordinate['run_id'])
                safe.write_json(directory / 'container-state.json', {'before_cleanup': before, 'after_stop': after})
            except BaseException:
                absent = False
        try:
            safe.write_json(directory / 'cleanup.json', {'state': 'VERIFIED_ABSENT' if absent else 'UNKNOWN',
                'identity': identity, 'created': identity is not None})
        except BaseException:
            absent = False
        try:
            outcome = finish(root, directory, work, coordinate, pin, key, code, absent, error)
        except BaseException:
            outcome = 1
            try:
                safe.write_json(directory / 'summary.json', {**coordinate,
                    'status': 'FAIL_OR_INCOMPLETE', 'error': 'REPORT_VALIDATION_FAILED',
                    'own_container_absent': absent, 'process_exit_code': code,
                    'sdk_attempts_reserved': None, 'sdk_completed_responses': None,
                    'external_billing': 'UNKNOWN_NOT_A_BILLING_RECEIPT'})
            except BaseException:
                pass
        try:
            journal.write('terminal', error=error, cleanup='VERIFIED_ABSENT' if absent else 'UNKNOWN',
                outcome='EXECUTION_PASS_PENDING_EDITORIAL' if outcome == 0 else 'FAIL_OR_INCOMPLETE')
        except BaseException:
            outcome = 1
        key = ''
    if primary is not None:
        raise primary
    return outcome


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--report-dir', required=True, type=Path)
    parser.add_argument('--admit-only', action='store_true')
    parser.add_argument('--setup-only', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    directory = args.report_dir.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    journal = Journal(directory)
    if args.admit_only:
        journal.write('preflight', qualification='NOT_QUALIFIED')
    entered = False
    try:
        coordinate = admit(os.environ, datetime.now(timezone.utc))
        root = args.source_root.resolve()
        pin = source(root, coordinate['source'])
        runner = Path(__file__).resolve().parents[2]
        require(safe.git(runner, 'rev-parse', 'HEAD') == coordinate['source']
            and not safe.git(runner, 'status', '--porcelain', '--untracked-files=normal'), 'RUNNER_MISMATCH')
        if args.admit_only:
            links = {sha: qualification(sha) for sha in {CONTENT_SOURCE, SOURCE_FINAL, coordinate['source']}}
            profile(root)
            safe.write_json(directory / 'admission.json', {'coordinates': coordinate, 'content': pin,
                'original_qualification': links, 'scope': 'one100/392/3000/1800/no-whole-run-retry'})
            return 0
        if args.setup_only:
            setup_only(root, directory)
            return 0
        entered = True
        return execute(root, directory, coordinate, pin, os.environ, journal)
    except BaseException:
        if not entered:
            try:
                journal.write('terminal', error='PREADMISSION_FAILED', outcome='FAIL_OR_INCOMPLETE',
                    paid_dispatch='NOT_ENTERED_BY_THIS_PROCESS', billing='UNKNOWN_NOT_A_BILLING_RECEIPT')
            except BaseException:
                pass
        raise


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError):
        print('HELP100_FRESH=FAIL_CLOSED', file=sys.stderr)
        raise SystemExit(1) from None
