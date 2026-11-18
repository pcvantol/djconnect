"""Validate bounded lane evidence without mistaking source, fixtures or CI for product acceptance."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / 'docs/governance/djconnect-open-work-20261017.json'
REPORT = REGISTER.with_name('DJC_PLATFORM_OPEN_WORK_20261017.md')
# Immutable dated source snapshot, independently compared with Git cc9b49fe.
SOURCE_MANIFEST = REGISTER.with_name('core-source-manifest-cc9b49fe.json')
SOURCE_MANIFEST_SHA256 = '780022ac088d59f5ac46fde6846e151de40c0e1c5fd3cdfda5dbb23550080eb4'
TOPICS = {
    'ask_dj', 'source_delivery', 'flow_history', 'album_artist_art', 'tts',
    'voice_preview', 'profile_settings', 'mood_presence_advertisement',
    'lan_websocket', 'vibecast_api', 'vibecast', 'ui_ux', 'performance',
    'crash_memory', 'surface_transport', 'widgets_activity_island',
    'production_push', 'watch_flow', 'maintenance', 'track_insight',
}
PROOF_KINDS = {'local_tests', 'model_run', 'installed_manifest', 'public_http', 'owner_lane_report'}


def validate_installed(proof: dict, expected_commit: str) -> list[str]:
    """A matching version label or fixture cannot qualify an installed artifact."""
    errors = []
    manifest_bytes = SOURCE_MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    if hashlib.sha256(manifest_bytes).hexdigest() != SOURCE_MANIFEST_SHA256:
        errors.append('pinned source manifest digest differs')
    if manifest['commit'] != expected_commit:
        errors.append('pinned source manifest commit differs')
    if proof.get('kind') != 'installed_manifest' or proof.get('commit') != expected_commit:
        errors.append('installed proof needs the observed exact source and installed-manifest kind')
    expected, actual = proof.get('expected_files'), proof.get('actual_files')
    files = proof.get('files')
    if (type(expected) is not int or type(actual) is not int
            or expected != len(manifest['files']) or actual != expected
            or not isinstance(files, dict) or len(files) != actual):
        errors.append('installed file set is incomplete')
    if (files != manifest['files'] or proof.get('changed_or_missing') != 0
            or proof.get('extra_files') != 0):
        errors.append('installed files differ from the candidate')
    caps = proof.get('capabilities')
    if not isinstance(caps, dict) or any(caps.get(k) is not True for k in ('active_session_mood', 'active_session_presence')):
        errors.append('installed Mood/Presence advertisement is missing')
    if proof.get('settings_version') != 3:
        errors.append('installed shared settings contract is not version3')
    for key in ('contract_versions', 'surface_versions'):
        versions = proof.get(key, {})
        if any(type(versions.get(k)) is not int or versions.get(k) != 1
               for k in ('active_session_mood', 'active_session_presence')):
            errors.append('installed Mood/Presence contract must be v1')
    return errors


def validate(data: dict, plan: dict) -> list[str]:
    errors: list[str] = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(data.get('schema_version') == 'djconnect-open-work-audit/1', 'unknown audit schema')
    check(data.get('automatic_dispatch') is False and data.get('consumer_writes') is False,
          'audit must not dispatch or take over consumer writes')
    main = data.get('core_main_observed', '')
    check(data.get('source_manifest') == {'path': SOURCE_MANIFEST.name,
                                       'sha256': SOURCE_MANIFEST_SHA256}, 'invalid pinned source manifest')
    check(isinstance(main, str) and bool(re.fullmatch('[a-f0-9]{40}', main)), 'invalid source pin')
    local = data.get('core_local_correction', {})
    check(local.get('published') is False and local.get('installed') is False
          and local.get('overall_quality') == 'NO_GO', 'unpublished correction must remain uninstalled and NO_GO')
    check(local.get('open_quality_steps', 0) > 0 and local.get('open_core_findings', 0) > 0,
          'known real-quality findings must not disappear')
    findings = local.get('open_findings', [])
    check(len(findings) == local.get('open_core_findings')
          and len({r.get('id') for r in findings}) == len(findings)
          and all(r.get('finding') for r in findings), 'named Core findings must remain accounted for')
    repos = data.get('repositories', [])
    names = [r.get('name') for r in repos]
    check(len(names) == len(set(names)), 'duplicate repository')
    check({'djconnect', 'djconnect-app', 'djconnect-api', 'djconnect-vibecast-receiver',
           'djconnect-pi', 'djconnect-esp32', 'djconnect-website', 'djconnect-firmware',
           'djconnect-pico', 'djconnect-app-releases', 'djconnect-pi-releases',
           'djconnect-windows', 'djconnect-sha-enforcement-reproducer'} <= set(names),
          'repository coverage is incomplete')
    check(all(r.get('product_active') is False for r in repos
              if r.get('name') in {'djconnect-windows', 'djconnect-sha-enforcement-reproducer'}),
          'retired Windows or engineering reproducer cannot become an active product')
    github = data.get('github_open', [])
    keys = [(r.get('repo'), r.get('number')) for r in github]
    check(len(keys) == len(set(keys)), 'duplicate GitHub item')
    check(all(r.get('repo') in names and r.get('state') == 'open' and r.get('kind') in {'issue', 'pull_request'}
              and r.get('url') == f"https://github.com/pcvantol/{r.get('repo')}/{'pull' if r.get('kind') == 'pull_request' else 'issues'}/{r.get('number')}"
              for r in github), 'invalid issue or PR identity')
    nodes = plan['nodes'] + plan['planning_maintenance']['nodes']
    known = {n['id'] for n in nodes}
    expected_dag = {n['id']: n['status'] for n in plan['planning_maintenance']['nodes']
                    if n.get('status') in {'Planned', 'In progress'}}
    retained = data.get('dag_open', [])
    check(len(retained) == len(expected_dag)
          and {r.get('id'): r.get('status') for r in retained} == expected_dag,
          'canonical unfinished DAG gates must be retained, not counted from null status projections')
    proofs = data.get('proofs', [])
    proof_ids = [r.get('id') for r in proofs]
    check(len(proof_ids) == len(set(proof_ids)), 'duplicate proof')
    proof_map = {r['id']: r for r in proofs if isinstance(r.get('id'), str)}
    regression = proof_map.get('local-corrective-regressions', {})
    check(regression.get('kind') == 'local_tests' and regression.get('status') == 'PASS'
          and regression.get('commit') == local.get('commit')
          and type(regression.get('count')) is int and regression['count'] > 0
          and regression.get('count') == local.get('host_tests')
          and type(regression.get('skips')) is int and regression['skips'] >= 0
          and regression.get('skips') == local.get('existing_skips'), 'missing or inconsistent local regression evidence')
    quality = proof_map.get('local-real-model-quality', {})
    check(quality.get('kind') == 'model_run' and quality.get('status') == 'FAIL'
          and quality.get('open_quality_steps') == local.get('open_quality_steps')
          and quality.get('open_core_findings') == local.get('open_core_findings'),
          'missing or inconsistent real model quality evidence')
    for proof in proofs:
        check(proof.get('kind') in PROOF_KINDS, 'unknown evidence kind')
        if proof.get('kind') == 'installed_manifest' and proof.get('status') == 'PASS':
            errors.extend(validate_installed(proof, main))
    items = data.get('items', [])
    ids = [r.get('id') for r in items]
    check(len(ids) == len(set(ids)), 'duplicate work item')
    check(TOPICS <= {r.get('topic') for r in items}, 'requested topic omitted')
    edges = {r['id']: r.get('depends_on', []) for r in items if isinstance(r.get('id'), str)}
    for row in items:
        check(row.get('status') in {'OPEN', 'RESOLVED_SCOPED'}, 'unknown completion status')
        check(bool(row.get('owners')) and bool(row.get('next_action')) and bool(row.get('required_tests')),
              'work item needs owner, next action and real acceptance tests')
        check(all(ref in known for ref in row.get('dag_refs', [])), 'unknown canonical DAG reference')
        check(all(dep in edges for dep in row.get('depends_on', [])), 'unknown dependency')
        check(all(p in proof_map for p in row.get('proof_ids', [])), 'unknown evidence reference')
        if row.get('status') == 'RESOLVED_SCOPED':
            check(row.get('id') == 'advertisement' and row.get('topic') == 'mood_presence_advertisement'
                  and row.get('closure_scope') == 'producer_advertisement_only'
                  and row.get('product_acceptance') == 'NOT_CLAIMED', 'scoped closure must not imply whole product completion')
            check({'installed-dev', 'installed-prod', 'external-dev-advertisement'} <= set(row.get('proof_ids', [])),
                  'advertisement closure requires both installed manifests and external-dev HTTP evidence')
            for pid in ('installed-dev', 'installed-prod'):
                proof = proof_map.get(pid, {})
                check(proof.get('status') == 'PASS', 'closure needs successful installed evidence')
                errors.extend(validate_installed(proof, main))
            http = proof_map.get('external-dev-advertisement', {})
            check(http.get('kind') == 'public_http' and http.get('status') == 'PASS'
                  and http.get('commit') == main and http.get('http_status') == 200
                  and http.get('tls_verified') is True and http.get('mood_available') is True
                  and http.get('presence_available') is True
                  and type(http.get('mood_version')) is int and http.get('mood_version') == 1
                  and type(http.get('presence_version')) is int and http.get('presence_version') == 1,
                  'closure needs real verified external advertisement v1')
        else:
            check(row.get('product_acceptance') == 'OPEN', 'open finding cannot have product PASS')
    remaining = dict(edges)
    while remaining:
        ready = [key for key, deps in remaining.items() if not any(dep in remaining for dep in deps)]
        if not ready:
            errors.append('cyclic open-work dependencies')
            break
        for key in ready:
            del remaining[key]
    cleanup = data.get('cleanup', {})
    check(cleanup.get('deleted_branches') == [] and cleanup.get('deleted_worktrees') == [],
          'this readback found no proven stale ref; cannot fabricate cleanup')
    check(all(r.get('unpublished_or_active') is True and str(r.get('reason', '')).startswith('PRESERVE_')
              for r in cleanup.get('preserved', [])), 'preserve ambiguous and unpublished work')
    return errors


def render(data: dict) -> str:
    """One readable view from the evidence register, without duplicating roadmap authority."""
    github = data['github_open']
    combined = data.get('combined_branch_status_reconciliation', {})
    count = Counter(r['kind'] for r in github)
    proofs = {r['id']: r for r in data['proofs']}
    dev_count = len(proofs['installed-dev']['files'])
    prod_count = len(proofs['installed-prod']['files'])
    regression = proofs['local-corrective-regressions']
    quality = proofs['local-real-model-quality']
    out = [
        '# DJConnect integral open-work reconciliation — 17 October 2026\n\n',
        ("Current combined local checkpoint: "
         f"{combined['reported_issues']} reported issues, {combined['conversation_families']} families, "
         f"{combined['conversation_steps']} steps; {combined['open_core_findings']} Core findings and "
         f"{combined['open_quality_steps']} real-quality steps OPEN; merge {combined['merge_readiness']}. "
         "No installation or audible claim. The dated observations below remain historical.\n\n"
         if combined.get('current_local_state') else ''),
        'Direct owner request; existing Core writer, [register #1101](https://github.com/pcvantol/djconnect/issues/1101). '
        'This dated evidence overlay does not start a product slice, dispatch another writer or replace the living DAG.\n\n',
        f"Observed {data['observed_at']}; Core main `{data['core_main_observed']}`. "
        f"{len(data['repositories'])} repositories, {count['issue']} open issues/registers and {count['pull_request']} open PRs. "
        f"All {len(data['dag_open'])} explicitly Planned/In-progress maintenance gates are retained below; "
        'null-status historical inventory/projection rows are not counted as unfinished product assignments. '
        'Windows remains retired; its register is historical.\n\n',
        '## What can close and what stays open\n\n',
        f"HA-dev has {dev_count} and HA-prod has {prod_count} integration files byte-equal to the pinned source manifest of the observed main. "
        'Mood/Presence v1 and settings3 are advertised. Configured external-dev HTTPS also advertises them. '
        'Only the original missing-advertisement defect in Core#1165 closed on this evidence; '
        'native Mood controls and joint settings acceptance remain open. No Session setting or playback was changed for this audit. '
        'A production external URL was not configured in the HA config readback, so no external-prod HTTP acceptance is claimed.\n\n',
        f"The personal-DJ corrective source `{data['core_local_correction']['commit']}` is local, unpublished and uninstalled. "
        f"{regression['count']:,} host tests ({regression['skips']} existing skips) and scoped reviews are software evidence. "
        f"{quality['open_core_findings']} Core findings and {quality['open_quality_steps']} real-quality Golden steps remain open: no factual/Persona/Mood/all-family narration GO, "
        'no protected delivery or install of those bytes. No paid model run was started by this audit.\n\n',
        'Named release-blocking Core findings:\n\n',
        *[f"- `{r['id']}`: {r['finding']}\n" for r in data['core_local_correction']['open_findings']],
        '\n',
        '## Requirement, evidence and next acceptance\n\n',
    ]
    for row in data['items']:
        out += [f"### {row['topic']} — {row['status']}\n\n",
                f"Owner: {', '.join(row['owners'])}.\n\n", row['summary'] + '\n\n',
                '**Next:** ' + row['next_action'] + '\n\n', '**Required acceptance:**\n\n']
        out += [f'- {test}\n' for test in row['required_tests']]
        out += ['\n']
        if row['dag_refs']:
            out += ['Existing DAG: ' + ', '.join(f'`{ref}`' for ref in row['dag_refs']) + '.\n\n']
    out += ['## Lane feedback and scoped resolution\n\n']
    for row in data.get('closed_in_audit', []):
        out += [f"- [{row['repo']}#{row['number']}]({row['evidence']}): {row['state']}, `{row['scope']}` only.\n"]
    for row in data.get('lane_updates', []):
        out += [f"- [{row['repo']}#{row['issue']} lane feedback]({row['url']}).\n"]
    out += ['\n## Open GitHub work at the captured readback\n\n',
            'This is the initial readback; subsequent scoped closures are listed above.\n\n',
            '| Repository | Item | Kind |\n|---|---|---|\n']
    for row in github:
        title = row['title'].replace('|', '/')
        out += [f"| {row['repo']} | [#{row['number']} {title}]({row['url']}) | {row['kind']} |\n"]
    out += ['\n## Canonical remaining maintenance gates\n\n', '| Existing node | Lane | Captured status |\n|---|---|---|\n']
    out += [f"| `{r['id']}` | {r['lane']} | {r['status']} |\n" for r in data['dag_open']]
    out += ['\n## Cleanup and resource result\n\n',
            'No stale registered product branch/worktree was proven safe to remove in the eight checked-out lane repositories. '
            'Current branches are active, dirty or contain unpublished work. They are preserved; the receiver writer also retains its own isolated checkout. '
            'The browser-validation resource lock is not an index/ref lock and was preserved. '
            'Compiler caches were checksum/mode/mtime-preserved externally with original paths retained. '
            'Only one redundant local Time Machine snapshot was removed after a verified all-Core-refs bundle and confirmation of a newer completed external backup; '
            'the external backup and current WIP/evidence remain intact. No external restore-mount test is claimed. '
            'Fresh hostverify then returned MATCH/exit0; resource values are private operational evidence, not a product readiness guarantee.\n\n',
            '## Verification and closure boundary\n\n',
            '`python3 tools/verification/open_work_audit.py --check-rendered` validates this register and generated report. '
            'The regular unittest suite includes negative tests for missing topics/DAG gates, fabricated installed/native completion, '
            'missing capability fields, wrong source/partial file sets, dependency cycles and unsafe cleanup. '
            'These are reconciliation/readback checks; they do not execute open native, audible, background, production-push or model-quality scenarios. '
            'Existing owning product suites and real Golden gates stay mandatory.\n\n',
            'Detailed private raw readbacks are kept separately. Public lane updates contain only bounded contract/pin/test/blocker facts. '
            'No secrets, private URLs, Profile/device identifiers or raw model/Apple proof material belong in this report.\n',
    ]
    return ''.join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-rendered', action='store_true')
    parser.add_argument('--write-report', action='store_true')
    parser.add_argument('--product-complete', action='store_true')
    args = parser.parse_args()
    data = json.loads(REGISTER.read_text())
    plan = json.loads((ROOT / 'docs/roadmap/v1/djconnect-platform-v1.json').read_text())
    errors = validate(data, plan)
    if args.product_complete:
        errors.append('product acceptance remains open; audit/software evidence cannot close the lane')
    if not errors and args.write_report:
        REPORT.write_text(render(data))
    if args.check_rendered and REPORT.read_text() != render(data):
        errors.append('generated open-work report drift')
    print(json.dumps({'status': 'FAIL' if errors else 'PASS_AUDIT_ONLY', 'product_acceptance': 'OPEN',
                      'errors': errors}, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
