# macOS Runner-Host Bootstrap Merge Readiness

**Status:** Pre-merge preparation for PR [#144](https://github.com/pcvantol/djconnect/pull/144)  
**Candidate branch:** `codex/macos-runner-recovery-bootstrap`  
**Candidate SHA:** `aee1687876c279d758f1404f9ca9e1563e310276`  
**Decision:** `MACOS_RUNNER_BOOTSTRAP_MERGE_READY`

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

| Workflow file | Current temporary SHA | Reason | Required post-merge replacement |
| --- | --- | --- | --- |
| `.github/workflows/codeql.yml` | `beb68dc935ce8422e7c6c1a1e7eadd61760f289c` | Calls the candidate reusable governance workflow containing the fallback. | Repin to the immutable `main` SHA that contains the merged reusable workflow. |
| `.github/workflows/djconnect-codeql-ci.yml` | `beb68dc935ce8422e7c6c1a1e7eadd61760f289c` | Calls the candidate reusable governance workflow containing the fallback. | Repin to the immutable `main` SHA that contains the merged reusable workflow. |
| `.github/workflows/djconnect-ha-integration-ci.yml` | `beb68dc935ce8422e7c6c1a1e7eadd61760f289c` | Calls the candidate reusable governance workflow containing the fallback. | Repin to the immutable `main` SHA that contains the merged reusable workflow. |
| `.github/workflows/djconnect-python-ci.yml` | `beb68dc935ce8422e7c6c1a1e7eadd61760f289c` | Calls the candidate reusable governance workflow containing the fallback. | Repin to the immutable `main` SHA that contains the merged reusable workflow. |
| `.github/workflows/djconnect-semgrep-ci.yml` | `beb68dc935ce8422e7c6c1a1e7eadd61760f289c` | Calls the candidate reusable governance workflow containing the fallback. | Repin to the immutable `main` SHA that contains the merged reusable workflow. |
| `.github/workflows/semgrep.yml` | `beb68dc935ce8422e7c6c1a1e7eadd61760f289c` | Calls the candidate reusable governance workflow containing the fallback. | Repin to the immutable `main` SHA that contains the merged reusable workflow. |
| `.github/workflows/validate.yaml` | `beb68dc935ce8422e7c6c1a1e7eadd61760f289c` | Calls the candidate reusable governance workflow containing the fallback. | Repin to the immutable `main` SHA that contains the merged reusable workflow. |
| `.github/workflows/verification-platform-docker-release.yml` | `beb68dc935ce8422e7c6c1a1e7eadd61760f289c` | Calls the candidate reusable governance workflow containing the fallback. | Repin to the immutable `main` SHA that contains the merged reusable workflow. |
| `.github/workflows/software-assurance-governance.yml` | `631f0b893a537807dfc59a6e69e413703a2eebdd` | Checks out the candidate canonical policy source containing the raw GitHub API fallback. | Repin the checkout `ref` to the immutable `main` SHA that contains the merged fallback. |

The existing reference in
`.github/workflows/post-merge-release-evidence-dispatch.yml` to
`2c65089aa2654e749852ab82728119e8c106c1ad` is not in this checklist: that
commit is already contained in `main` and was not introduced by PR #144.

## Required post-merge sequence

1. Merge the approved PR #144 and synchronize `main`.
2. Resolve the immutable `main` SHA that contains the merged fallback and
   verify that it contains both the reusable governance workflow and its
   canonical policy checkout source.
3. In one separately reviewed post-merge increment, replace all nine
   temporary references in the table with that SHA.
4. Validate the changed callers and reusable workflow from the new `main`
   reference.
5. Delete the PR #144 feature branch only after the repin pull request is
   merged and its validation is green.

This sequence prevents a reusable workflow from depending on a feature-branch
commit after that branch is removed.

## Deferred work

- Execute the post-merge repin only after PR #144 has a merge commit on
  `main`.
- Resume separately authorized Platform Release 3.3 target qualification only
  through its own prompt and authorization.

## Recommended next prompt

Draft only — after PR #144 is merged, repin the documented temporary bootstrap
workflow references to the immutable merged `main` SHA, validate them, then
remove the feature branch.
