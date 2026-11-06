"""Run the EN/NL functional addendum in isolated HA; spends zero model/provider calls."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.verification.golden_en_nl_features import HTTP_CASES, LOCALES, REGRESSIONS, findings  # noqa: E402

IMAGE = 'ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4'


def source_pins():
    names = subprocess.check_output(['git', 'ls-files', '-z', 'custom_components/djconnect',
        'scripts/verification', 'tools/verification/run_golden_en_nl_features.py', 'tests'], cwd=ROOT).split(b'\0')
    # Include this addendum when running before its first commit too.
    paths = {ROOT / n.decode() for n in names if n}
    paths.update((ROOT / 'scripts/verification/golden_en_nl_features.py', Path(__file__).resolve()))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New external evidence directory')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        parser.error('Evidence must be outside the source checkout')
    output.mkdir(parents=True, exist_ok=False)
    before = source_pins()

    def run(job):
        harness, locale = job
        folder = output / (harness + '--' + locale)
        folder.mkdir()
        name = 'djc-en-nl-' + os.urandom(8).hex()
        cmd = ['docker', 'run', '--rm', '--name', name, '--network', 'none', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'DJC_SOURCE_ROOT=/candidate',
            '-e', 'DJC_LAB_ROOT=/lab', '-e', 'PYTHONPATH=/candidate:/candidate/scripts/verification',
            '-e', 'DJC_GOLDEN_LOCALE=' + locale, '-v', str(ROOT) + ':/candidate:ro',
            '-v', str(folder) + ':/lab:rw', '-w', '/candidate', '--entrypoint', 'python', IMAGE]
        args = (['-m', 'unittest', *REGRESSIONS] if harness == 'recent_regressions'
                else ['/candidate/scripts/verification/' + harness + '.py'])
        errors = []
        try:
            with (folder / 'run.log').open('w') as log:
                result = subprocess.run(cmd + args, stdout=log, stderr=subprocess.STDOUT, timeout=360)
            if result.returncode:
                errors.append('process_failed:' + str(result.returncode))
            if harness != 'recent_regressions':
                receipt_path = folder / 'http-producer-receipt.json'
                if receipt_path.is_file():
                    errors.extend(findings(harness, locale, json.loads(receipt_path.read_text())))
                else:
                    errors.append('receipt_missing')
        except (subprocess.TimeoutExpired, ValueError) as exc:
            errors.append(type(exc).__name__)
        finally:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30, check=False)
        return {'harness': harness, 'language': locale, 'findings': errors,
                'status': 'FAIL' if errors else 'PASS'}

    jobs = [(h, locale) for h in HTTP_CASES for locale in LOCALES]
    jobs.append(('recent_regressions', 'en,nl'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, jobs))
    stable = before == source_pins()
    report = {'suite': 'golden_en_nl_functional_addendum_v1', 'languages': list(LOCALES),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_pins': before, 'source_unchanged': stable, 'results': results,
        'status': 'PASS' if stable and all(r['status'] == 'PASS' for r in results) else 'FAIL',
        'real_model_provider_calls': 0, 'installed_native_audible_apns': 'NOT_RUN',
        'real_answer_quality': 'NOT_QUALIFIED_BY_SYNTHETIC_TRANSPORTS',
        'original_full_manifest_qualified': False}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('suite', 'status', 'languages', 'results')}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
