# macOS Runner-Host Bootstrap Merge Readiness

**Status:** Post-merge repin reviewable
**Candidate branch:** `codex/macos-runner-recovery-bootstrap`  
**Candidate SHA:** `aee1687876c279d758f1404f9ca9e1563e310276`  
**Decision:** `MACOS_RUNNER_BOOTSTRAP_MERGE_READY`

## Subsequent merge outcome

PR #144 was squash-merged into `main` as
`452bed7655e579d3fb12b7b379f8fc0b70a8c342` on 2026-07-16. The documented
post-merge repin now targets immutable current-`main` SHA
`3d7d24a84b3aaacb8f2fb229e09c33da85e0545d`, which contains the merge and the
governance fallback. The original candidate branch remains retained until this
separately reviewed increment is merged and its checks are green.

## Scope and evidence

This record prepares PR #144 for review and merge. It does not change the
bootstrap, runner, CI, governance, deployment or release implementation.

At the time of this record, GitHub evidence shows that PR #144 is open,
mergeable (`CLEAN`) and that its required checks, including Owner
Authorization, completed successfully for candidate
`aee1687876c279d758f1404f9ca9e1563e310276`. No newer candidate commit was
reported after that validation.

PR #144 implements the following complete scope:

- Apple-Silicon macOS development-host and runner-host bootstrap;
- desired-state host verification, delta reporting, repair and dry-run modes;
- recovery logging, redaction, Markdown reporting and restart continuation;
- CI runner qualification and current-tooling maintenance;
- Apple tooling, Homebrew, Docker and the Home Assistant lab;
- ngrok and Tailscale discovery/configuration checks without secret capture;
- explicit machine-independent encrypted asset export/import;
- Windows ARM64 runner bootstrap;
- onboarding package build, tracked distribution artifacts and unit tests.

Signing material, private keys, credentials, release manifests, deployment
authorization and deployment behaviour remain outside this scope.

## Temporary bootstrap references

The following references are immutable SHA pins, but are temporary because
their target commits are reachable from PR #144 and are not yet contained in
`main`. They were introduced solely to let the candidate validate the
governance runtime-validation fallback before the implementation exists on
`main`.

| Workflow file | Repinned immutable `main` SHA | Reason | Review obligation |
| --- | --- | --- | --- |
| `.github/workflows/codeql.yml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Calls the reusable governance workflow on merged `main`. | Repinned; validate this caller. |
| `.github/workflows/djconnect-codeql-ci.yml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Calls the reusable governance workflow on merged `main`. | Repinned; validate this caller. |
| `.github/workflows/djconnect-ha-integration-ci.yml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Calls the reusable governance workflow on merged `main`. | Repinned; validate this caller. |
| `.github/workflows/djconnect-python-ci.yml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Calls the reusable governance workflow on merged `main`. | Repinned; validate this caller. |
| `.github/workflows/djconnect-semgrep-ci.yml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Calls the reusable governance workflow on merged `main`. | Repinned; validate this caller. |
| `.github/workflows/semgrep.yml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Calls the reusable governance workflow on merged `main`. | Repinned; validate this caller. |
| `.github/workflows/validate.yaml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Calls the reusable governance workflow on merged `main`. | Repinned; validate this caller. |
| `.github/workflows/verification-platform-docker-release.yml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Calls the reusable governance workflow on merged `main`. | Repinned; validate this caller. |
| `.github/workflows/software-assurance-governance.yml` | `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` | Checks out the canonical policy source from merged `main`. | Repinned; validate reusable workflow. |

The existing reference in
`.github/workflows/post-merge-release-evidence-dispatch.yml` to
`2c65089aa2654e749852ab82728119e8c106c1ad` is not in this checklist: that
commit is already contained in `main` and was not introduced by PR #144.

## Required post-merge sequence

1. PR #144 is merged and `main` is synchronized.
2. `3d7d24a84b3aaacb8f2fb229e09c33da85e0545d` is verified to contain the
   merge and the reusable governance workflow.
3. This separately reviewed post-merge increment replaces all nine temporary
   references with that SHA.
4. Validate the changed callers and reusable workflow from the new immutable
   reference.
5. Delete the PR #144 feature branch only after this repin pull request is
   merged and its validation is green.

This sequence prevents a reusable workflow from depending on a feature-branch
commit after that branch is removed.

## Deferred work

- Resume separately authorized Platform Release 3.3 target qualification only
  through its own prompt and authorization.

## Recommended next prompt

After this reviewable repin merges and its checks are green, delete the
retained PR #144 feature branch. Do not start another release operation here.
