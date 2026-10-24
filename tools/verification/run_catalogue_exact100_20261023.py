"""One specifically authorized catalogue run; never a generic release matrix."""
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

CANDIDATE = '1c5516d51c01c688b595ed2f0cccf28606e1ba13'
GRANT = 'DJC-CORE-CATALOGUE-100-20261023'
WORKFLOW = 'pcvantol/djconnect/.github/workflows/catalogue-exact100-20261023.yml@refs/heads/main'
MANIFEST = 'f6fcebd0349768b83a6824d6dcfeb15e3b229e0c1a168dec4c5a044e1ac43b48'
CATALOGUE = 'dfaa98a1659ef5673037da26f98136314b314beea8afe8e31af4ffd5bd6ac4e7'
START = datetime(2026, 10, 23, 14, 27, tzinfo=timezone.utc)
LAST_START = datetime(2026, 10, 23, 19, 10, tzinfo=timezone.utc)
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
             'GITHUB_RUN_NUMBER': '1', 'GITHUB_RUN_ATTEMPT': '1', 'DJC_EXACT100_GRANT': GRANT}
    require(all(env.get(k) == v for k, v in fixed.items()), 'exact100_context_denied')
    require(START <= now < LAST_START, 'exact100_window_closed')
    require(re.fullmatch('[1-9][0-9]{0,19}', env.get('GITHUB_RUN_ID', '')), 'exact100_run_invalid')
    require(re.fullmatch('[a-f0-9]{40}', env.get('GITHUB_SHA', '')), 'exact100_workflow_sha_invalid')
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
            'exact100_candidate_mismatch')
    require(not git(root, 'status', '--porcelain', '--untracked-files=normal'), 'exact100_source_dirty')
    files = product_hashes(root)
    require(len(files) == 264, 'exact100_product_count')
    require(files.get('custom_components/djconnect/ask_dj/examples_v1.json') == CATALOGUE,
            'exact100_catalogue_mismatch')
    return files


def qualified_status(value, sha):
    require(isinstance(value, dict) and value.get('sha') == sha, 'exact100_status_sha')
    rows = value.get('statuses', [])
    canonical = next((r for r in rows if isinstance(r, dict) and r.get('context') ==
                      'Post-Merge Release Evidence / Reconcile release evidence'), None)
    require(canonical is not None and canonical.get('state') == 'success' and
            canonical.get('description') == 'POST_MERGE_RELEASE_EVIDENCE_QUALIFIED',
            'exact100_original_qualification_missing')
    return canonical['target_url']


def github_qualification(sha):
    # gh uses the step's read-only GitHub token. No model secret is available here.
    raw = subprocess.check_output(['gh', 'api', f'repos/pcvantol/djconnect/commits/{sha}/status'],
                                  text=True, timeout=40)
    return qualified_status(json.loads(raw), sha)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def load_profile(root):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    profile = importlib.import_module('scripts.verification.askdj_example_catalogue_golden')
    require(len(profile.cases()) == 70 and len(profile.chain_cases()) == 30 and
            profile.manifest_digest() == MANIFEST and profile.MAX_MODEL_CALLS == 392 and
            profile.MAX_OUTPUT_TOKENS == 3000, 'exact100_profile_mismatch')
    return profile


def reserve_once(path, coordinates):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump({**coordinates, 'state': 'RESERVED_BEFORE_MODEL_SECRET_READ',
                   'max_attempts': 392, 'max_output_tokens': 3000, 'max_seconds': MAX_SECONDS}, output)
        output.flush()
        os.fsync(output.fileno())


def report_safe(raw, key):
    require(len(raw) <= 8 * 1024 * 1024, 'exact100_report_oversized')
    require(key.encode() not in raw, 'exact100_credential_in_report')
    return json.loads(raw)


def container_absent(name):
    result = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=20)
    return (result.returncode == 1 and result.stdout.strip() in ('', '[]') and
            re.fullmatch(r'Error(?: response from daemon)?: No such (?:object|container): ' +
                         re.escape(name) + r'\s*', result.stderr, re.IGNORECASE) is not None)


def execute(root, directory, coordinates, files, profile, env):
    admission = json.loads((directory / 'admission.json').read_text())
    require(admission['coordinates'] == coordinates and admission['product_hashes'] == files,
            'exact100_admission_changed')
    reserve_once(directory / 'once-reservation.json', coordinates)
    key = env.get('DJCONNECT_GOLDEN_OPENAI_API_KEY', '')
    require(isinstance(key, str) and 20 <= len(key) <= 8192, 'exact100_test_credential_missing')
    name = 'djc-exact100-' + secrets.token_hex(8)
    work = directory / 'private-work'
    work.mkdir(mode=0o700)
    command = ['docker', 'run', '--rm', '-i', '--name', name, '--network', 'bridge',
               '--memory', '1g', '--cpus', '2', '--pids-limit', '256', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--entrypoint', 'python',
               '--workdir', '/candidate', '-e', 'PYTHONPATH=/candidate',
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'DJC_SOURCE_ROOT=/candidate',
               '-e', 'DJC_SAFETY_PROBE=catalogue_golden', '-v', str(root) + ':/candidate:ro',
               '-v', str(work) + ':/lab', IMAGE,
               '/candidate/scripts/verification/verify_ask_dj_contextual_dialogue_http.py']
    code = 124
    try:
        with (work / 'private.log').open('w') as log:
            result = subprocess.run(command, input=json.dumps({'api_key': key, 'model': 'gpt-6-luna',
                                    'max_tokens': 3000}), text=True, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=MAX_SECONDS, check=False)
            code = result.returncode
    except subprocess.TimeoutExpired:
        pass
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30, check=False)
        absent = container_absent(name)
        write_json(directory / 'cleanup.json', {'name': name, 'state': 'VERIFIED_ABSENT' if absent else 'UNKNOWN'})
    require(absent, 'exact100_container_cleanup_unknown')
    require(product_hashes(root) == files and git(root, 'rev-parse', 'HEAD') == CANDIDATE,
            'exact100_source_changed')
    path = work / 'catalogue-golden.json'
    summary = {**coordinates, 'exit_code': code, 'status': 'FAIL_OR_INCOMPLETE',
               'manual_runs': 1, 'automatic_reruns': 0, 'max_attempts': 392,
               'max_output_tokens': 3000, 'max_seconds': MAX_SECONDS,
               'all264_source_hashes_before_after_equal': True, 'own_container_absent': True,
               'catalogue_publication': 'UNCHANGED_PENDING_INDEPENDENT_EDITORIAL_REVIEW',
               'native_installed_provider_acceptance': 'NOT_QUALIFIED'}
    if path.is_file():
        raw = path.read_bytes()
        report = report_safe(raw, key)
        expected = profile_source_hashes(root)
        strict = code == 0 and profile.validate_report(report, source_hashes=expected)
        summary.update(status='PASS' if strict else 'FAIL',
                       paid_attempts=report.get('paid_model_calls'), case_count=len(report.get('cases', [])),
                       raw_sha256=hashlib.sha256(raw).hexdigest(), strict_validator=bool(strict))
        (directory / 'catalogue-golden.json').write_bytes(raw)
    else:
        summary['paid_attempts'] = 'UNKNOWN_POSSIBLY_SPENT_NO_RETRY'
    key = ''
    write_json(directory / 'summary.json', summary)
    return 0 if summary['status'] == 'PASS' else 1


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
        require(git(runner, 'rev-parse', 'HEAD') == coordinates['workflow_sha'], 'exact100_runner_sha')
        require(not git(runner, 'status', '--porcelain', '--untracked-files=normal'), 'exact100_runner_dirty')
        subprocess.run(['git', '-C', str(runner), 'merge-base', '--is-ancestor', CANDIDATE,
                        coordinates['workflow_sha']], check=True, timeout=30)
        links = {sha: github_qualification(sha) for sha in {CANDIDATE, coordinates['workflow_sha']}}
        write_json(directory / 'admission.json', {'coordinates': coordinates, 'product_hashes': files,
                   'manifest_sha256': MANIFEST, 'original_qualification': links,
                   'scope': 'One exact100 synthetic-provider/real-model HA test; no runtime deployment'})
        print('EXACT100_ADMISSION=PASS_NO_MODEL_SECRET_READ')
        return 0
    return execute(root, directory, coordinates, files, profile, os.environ)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError):
        print('EXACT100=FAIL_CLOSED', file=sys.stderr)
        raise SystemExit(1) from None
