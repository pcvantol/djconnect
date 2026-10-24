"""One NEW human-authorized Help100 slot; original failed slot stays consumed."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import stat
import math

CANDIDATE = '56ff7275ed31f74cc96af4a9e0744403ac3fbf1e'
GRANT = 'DJC-CORE-HELP-CATALOGUE-100-20261023-NEW-HUMAN-1721'
WORKFLOW = 'pcvantol/djconnect/.github/workflows/help-catalogue-qualified100-20261023.yml@refs/heads/main'
MANIFEST = 'f6fcebd0349768b83a6824d6dcfeb15e3b229e0c1a168dec4c5a044e1ac43b48'
CATALOGUE = 'dfaa98a1659ef5673037da26f98136314b314beea8afe8e31af4ffd5bd6ac4e7'
START = datetime(2026, 10, 23, 17, 21, tzinfo=timezone.utc)
LAST_START = datetime(2026, 10, 23, 18, 30, tzinfo=timezone.utc)
MAX_SECONDS = 1800
IMAGE = 'ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4'


def require(value, code):
    if not value:
        raise ValueError(code)


def admit_context(env, now):
    """Trusted Actions coordinates, not a caller-supplied budget boolean."""
    fixed = {'GITHUB_REPOSITORY': 'pcvantol/djconnect', 'GITHUB_REF': 'refs/heads/main',
             'GITHUB_WORKFLOW_REF': WORKFLOW, 'GITHUB_ACTOR': 'pcvantol',
             'GITHUB_TRIGGERING_ACTOR': 'pcvantol', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
             'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1', 'DJC_HELP100_GRANT': GRANT}
    require(all(env.get(k) == v for k, v in fixed.items()), 'help100_context_denied')
    require(START <= now < LAST_START, 'help100_window_closed')
    require(re.fullmatch('[1-9][0-9]{0,19}', env.get('GITHUB_RUN_ID', '')), 'help100_run_invalid')
    require(re.fullmatch('[a-f0-9]{40}', env.get('GITHUB_SHA', '')), 'help100_workflow_sha_invalid')
    return {'grant': GRANT, 'candidate': CANDIDATE, 'run_id': env['GITHUB_RUN_ID'],
            'workflow_sha': env['GITHUB_SHA'], 'run_number': 1, 'run_attempt': 1}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, timeout=30).strip()


def product_hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / 'custom_components/djconnect').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def source_facts(root):
    require(not root.is_symlink() and git(root, 'rev-parse', 'HEAD') == CANDIDATE,
            'help100_candidate_mismatch')
    require(not git(root, 'status', '--porcelain', '--untracked-files=normal'), 'help100_source_dirty')
    files = product_hashes(root)
    require(len(files) == 264, 'help100_product_count')
    require(files.get('custom_components/djconnect/ask_dj/examples_v1.json') == CATALOGUE,
            'help100_catalogue_mismatch')
    return files


def qualified_status(value, sha):
    require(isinstance(value, dict) and value.get('sha') == sha, 'help100_status_sha')
    rows = value.get('statuses', [])
    canonical = next((r for r in rows if isinstance(r, dict) and r.get('context') ==
                      'Post-Merge Release Evidence / Reconcile release evidence'), None)
    require(canonical is not None and canonical.get('state') == 'success' and
            canonical.get('description') == 'POST_MERGE_RELEASE_EVIDENCE_QUALIFIED',
            'help100_original_qualification_missing')
    return canonical['target_url']


def github_qualification(sha):
    # gh uses the step's read-only GitHub token. No model secret is available here.
    raw = subprocess.check_output(['gh', 'api', f'repos/pcvantol/djconnect/commits/{sha}/status'],
                                  text=True, timeout=40)
    return qualified_status(json.loads(raw), sha)


def write_bytes(path, raw):
    """Exclusive atomic publication; existing receipts are never replaced."""
    fd, temporary = tempfile.mkstemp(prefix='.help100-', dir=path.parent)
    primary = None
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        os.unlink(temporary)
        temporary = None
        parent = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except BaseException as exc:
        primary = exc
        raise
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                if primary is None:
                    raise


def write_json(path, value):
    write_bytes(path, (json.dumps(value, indent=2) + '\n').encode())


def load_profile(root):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    profile = importlib.import_module('scripts.verification.askdj_example_catalogue_golden')
    require(len(profile.cases()) == 70 and len(profile.chain_cases()) == 30 and
            profile.manifest_digest() == MANIFEST and profile.MAX_MODEL_CALLS == 392 and
            profile.MAX_OUTPUT_TOKENS == 3000, 'help100_profile_mismatch')
    return profile


def reserve_once(path, coordinates):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump({**coordinates, 'state': 'RESERVED_BEFORE_MODEL_SECRET_READ',
                   'max_attempts': 392, 'max_output_tokens': 3000, 'max_seconds': MAX_SECONDS}, output)
        output.flush()
        os.fsync(output.fileno())
    parent = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def report_safe(raw, key):
    require(len(raw) <= 8 * 1024 * 1024, 'help100_report_oversized')
    require(key.encode() not in raw, 'help100_credential_in_report')
    def unique(pairs):
        value = {}
        for name, item in pairs:
            require(name not in value, 'help100_duplicate_json_field')
            value[name] = item
        return value
    def nonfinite(_value):
        raise ValueError('help100_nonfinite_json')
    try:
        value = json.loads(raw.decode('utf-8', errors='strict'),
                           object_pairs_hook=unique, parse_constant=nonfinite)
        stack, seen = [(value, 0)], 0
        while stack:
            item, depth = stack.pop()
            seen += 1
            require(depth <= 48 and seen <= 200000, 'help100_json_bounds')
            if isinstance(item, dict):
                stack.extend((v, depth + 1) for v in item.values())
            elif isinstance(item, list):
                stack.extend((v, depth + 1) for v in item)
            elif isinstance(item, float):
                require(math.isfinite(item), 'help100_nonfinite_json')
        canonical = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        require(key.encode() not in canonical, 'help100_decoded_credential_in_report')
        return value
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('help100_json_invalid') from exc


def container_absent(name):
    result = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=20)
    return (result.returncode == 1 and result.stdout.strip() in ('', '[]') and
            re.fullmatch(r'Error(?: response from daemon)?: No such (?:object|container): ' +
                         re.escape(name) + r'\s*', result.stderr, re.IGNORECASE) is not None)


def read_work_file(path, *, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size <= maximum, 'help100_output_file_invalid')
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        require(len(raw) <= maximum and before.st_size == len(raw)
                and after.st_nlink == 1 and after.st_size == before.st_size
                and after.st_mtime_ns == before.st_mtime_ns,
                'help100_output_changed_during_read')
        return raw


def preserve_progress(root, work, directory, profile, key):
    """Only the exact already-qualified closed progress schema is publishable."""
    path = work / 'catalogue-progress.json'
    if not path.exists():
        return None
    raw = read_work_file(path, maximum=16384)
    value = report_safe(raw, key)
    from scripts.verification.catalogue_progress import validate_progress
    ids = [c['id'] for c in profile.cases() + profile.chain_cases()]
    require(validate_progress(value, case_ids=ids, manifest=MANIFEST),
            'help100_progress_invalid')
    # Publish ONLY the validated closed value; original raw bytes are never exported.
    write_json(directory / 'catalogue-progress.json', value)
    return value


def finish_execution(root, directory, coordinates, files, profile, key, *,
                     work, code, absent, interrupted):
    summary = {**coordinates, 'status': 'FAIL_OR_INCOMPLETE',
        'process_exit_code': code, 'interruption': interrupted,
        'manual_runs': 1, 'automatic_whole_test_reruns': 0,
        'max_attempts': 392, 'max_output_tokens': 3000, 'max_seconds': MAX_SECONDS,
        'external_billing': 'UNKNOWN_NOT_A_BILLING_RECEIPT',
        'original_failed_run': '39980138736_RETAINED_CONSUMED_NOT_RESET',
        'catalogue_publication': 'UNCHANGED_PENDING_INDEPENDENT_EDITORIAL_REVIEW',
        'native_installed_provider_acceptance': 'NOT_QUALIFIED',
        'own_container_absent': absent, 'findings': []}
    progress = None
    try:
        progress = preserve_progress(root, work, directory, profile, key)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        summary['findings'].append('PROGRESS_INVALID_OR_UNAVAILABLE')
    summary['progress'] = 'VALID_CLOSED_SNAPSHOT' if progress is not None else 'UNAVAILABLE'
    summary['progress_serialization'] = 'VALIDATED_CLOSED_VALUE_ONLY'
    summary['sdk_attempts_reserved'] = (progress['sdk_attempts_reserved'] if progress else None)
    summary['sdk_completed_responses'] = (progress['sdk_completed_responses'] if progress else None)
    try:
        unchanged = product_hashes(root) == files and git(root, 'rev-parse', 'HEAD') == CANDIDATE
    except (OSError, subprocess.SubprocessError):
        unchanged = False
    summary['all264_source_hashes_before_after_equal'] = unchanged
    strict = False
    path = work / 'catalogue-golden.json'
    if path.exists() and absent:
        try:
            raw = read_work_file(path, maximum=8 * 1024 * 1024)
            report = report_safe(raw, key)
            expected = profile_source_hashes(root)
            require(type(report) is dict and report.get('manifest_sha256') == MANIFEST
                    and report.get('qualification') == 'REAL_PAIRED_HA_EXACT_CATALOGUE_QUESTIONS_V1'
                    and report.get('source_hashes') == expected
                    and report.get('source_unchanged') is True,
                    'help100_report_binding_invalid')
            write_bytes(directory / 'catalogue-golden.json', raw)
            valid = profile.validate_report(report, source_hashes=expected)
            ids = [c['id'] for c in profile.cases() + profile.chain_cases()]
            complete = (progress is not None
                and progress['outcome'] == 'COMPLETE_NOT_QUALIFIED'
                and progress['completed_cases'] == ids and not progress['failed_cases']
                and progress['sdk_attempts_reserved'] == len(report.get('model_calls', []))
                and progress['sdk_completed_responses'] == sum(
                    c.get('completed') is True for c in report.get('model_calls', [])))
            strict = code == 0 and interrupted is None and absent and unchanged and valid and complete
            summary.update(case_count=len(report.get('cases', [])),
                paid_attempts_reported=report.get('paid_model_calls'),
                raw_sha256=hashlib.sha256(raw).hexdigest(), strict_validator=bool(valid),
                progress_report_counts_joined=bool(complete))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            summary['findings'].append('REPORT_INVALID_OR_UNAVAILABLE')
    else:
        summary['findings'].append('REPORT_MISSING')
    if not absent:
        summary['findings'].append('CLEANUP_UNKNOWN')
    if not unchanged:
        summary['findings'].append('SOURCE_CHANGED_OR_UNAVAILABLE')
    summary['status'] = 'PASS' if strict else 'FAIL_OR_INCOMPLETE'
    write_json(directory / 'summary.json', summary)
    return 0 if strict else 1


def execute(root, directory, coordinates, files, profile, env):
    admission = json.loads((directory / 'admission.json').read_text())
    require(admission['coordinates'] == coordinates and admission['product_hashes'] == files,
            'help100_admission_changed')
    reserve_once(directory / 'once-reservation.json', coordinates)
    key = env.get('DJCONNECT_GOLDEN_OPENAI_API_KEY', '')
    require(isinstance(key, str) and 20 <= len(key) <= 8192, 'help100_test_credential_missing')
    name = 'djc-help100-' + secrets.token_hex(8)
    work = directory / 'private-work'
    work.mkdir(mode=0o700)
    command = ['docker', 'run', '--rm', '-i', '--name', name,
               '--user', f'{os.getuid()}:{os.getgid()}', '--network', 'bridge',
               '--memory', '1g', '--cpus', '2', '--pids-limit', '256', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--entrypoint', 'python',
               '--workdir', '/candidate', '-e', 'PYTHONPATH=/candidate',
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'DJC_SOURCE_ROOT=/candidate',
               '-e', 'DJC_SAFETY_PROBE=catalogue_golden', '-v', str(root) + ':/candidate:ro',
               '-v', str(work) + ':/lab', IMAGE,
               '/candidate/scripts/verification/verify_ask_dj_contextual_dialogue_http.py']
    code, primary, interrupted = None, None, None
    try:
        with (work / 'private.log').open('w') as log:
            result = subprocess.run(command, input=json.dumps({'api_key': key, 'model': 'gpt-6-luna',
                                    'max_tokens': 3000}), text=True, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=MAX_SECONDS, check=False)
            code = result.returncode
    except BaseException as exc:
        primary = exc
        interrupted = ('TIMEOUT' if isinstance(exc, subprocess.TimeoutExpired)
                       else 'INTERRUPTED' if isinstance(exc, (KeyboardInterrupt, SystemExit))
                       else 'PROCESS_ERROR')
    finally:
        absent = False
        try:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30, check=False)
            absent = container_absent(name)
            write_json(directory / 'cleanup.json',
                       {'name': name, 'state': 'VERIFIED_ABSENT' if absent else 'UNKNOWN'})
        except (OSError, subprocess.SubprocessError):
            absent = False
        try:
            outcome = finish_execution(root, directory, coordinates, files, profile, key,
                work=work, code=code, absent=absent, interrupted=interrupted)
        except BaseException:
            if primary is None:
                raise
        finally:
            key = ''
    if primary is not None:
        raise primary
    return outcome


def profile_source_hashes(root):
    files = list((root / 'custom_components/djconnect').rglob('*.py'))
    names = ['scripts/verification/verify_ask_dj_contextual_dialogue_http.py',
             'scripts/verification/personal_dj_narration_probe.py', 'tools/verification/askdj_research_outcomes.py',
             'tools/verification/askdj_catalogue_variations.py', 'scripts/verification/askdj_semantic_read_golden.py',
             'scripts/verification/askdj_contextual_quality.py', 'scripts/verification/askdj_example_catalogue_golden.py',
             'scripts/verification/askdj_catalogue_provider_fixture.py', 'custom_components/djconnect/ask_dj/examples_v1.json',
             'scripts/verification/source_fixture_urls.py']
    files += [root / n for n in names]
    # Historical fixed1c has no checkpoint module. Never change its exact map;
    # a separately authorized future target must bind its diagnostic code too.
    progress = root / 'scripts/verification/catalogue_progress.py'
    if progress.is_file():
        files.append(progress)
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path, required=True)
    parser.add_argument('--admit-only', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    coordinates = admit_context(os.environ, datetime.now(timezone.utc))
    root, directory = args.source_root.resolve(), args.report_dir.resolve()
    files = source_facts(root)
    profile = load_profile(root)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if args.admit_only:
        runner = Path(__file__).resolve().parents[2]
        require(git(runner, 'rev-parse', 'HEAD') == coordinates['workflow_sha'], 'help100_runner_sha')
        require(not git(runner, 'status', '--porcelain', '--untracked-files=normal'), 'help100_runner_dirty')
        subprocess.run(['git', '-C', str(runner), 'merge-base', '--is-ancestor', CANDIDATE,
                        coordinates['workflow_sha']], check=True, timeout=30)
        links = {sha: github_qualification(sha) for sha in {CANDIDATE, coordinates['workflow_sha']}}
        write_json(directory / 'admission.json', {'coordinates': coordinates, 'product_hashes': files,
                   'manifest_sha256': MANIFEST, 'original_qualification': links,
                   'scope': 'One exact100 synthetic-provider/real-model HA test; no runtime deployment'})
        print('HELP100_ADMISSION=PASS_NO_MODEL_SECRET_READ')
        return 0
    return execute(root, directory, coordinates, files, profile, os.environ)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError):
        print('HELP100=FAIL_CLOSED', file=sys.stderr)
        raise SystemExit(1) from None
