# Prompt History: macOS Runner-Host Bootstrap Pre-Merge Preparation

**Prompt ID:** `G2-EVOL-MACOS-BOOTSTRAP-PREMERGE-001`  
**Prompt Title:** Platform Evolution: Prepare macOS runner-host bootstrap for merge  
**Generation:** 2  
**Engineering Program:** Platform Evolution  
**Branch:** `codex/prepare-macos-runner-bootstrap-merge`  
**Implementation Commit:** `be0310415210b9c58d86313bd11762731b94c094`  
**Pull Request:** [#146](https://github.com/pcvantol/djconnect/pull/146)  
**Decision:** `MACOS_RUNNER_BOOTSTRAP_MERGE_READY`  
**Execution Date:** 2026-07-16

## Objective

Prepare PR #144 for merge without changing its engineering scope. Correct its
description, identify every temporary workflow reference that targets a commit
outside `main`, and record the post-merge repin sequence.

## Repository evidence

- Current `main` was synchronized at
  `308d2bc57a4e0185c4b4fbf66d2f63fa285e905d`, tracked `origin/main` and had a
  clean working tree before this increment.
- PR #144 was open and `CLEAN` at candidate
  `aee1687876c279d758f1404f9ca9e1563e310276`; all required checks and Owner
  Authorization were successful.
- Eight caller workflows pin the candidate reusable governance workflow to
  `beb68dc935ce8422e7c6c1a1e7eadd61760f289c`. That commit is reachable from
  PR #144 and is not contained in `main`.
- The reusable workflow checks out canonical policy source
  `631f0b893a537807dfc59a6e69e413703a2eebdd`, also reachable from PR #144 and
  not contained in `main`.

## Validation summary

- Verified the PR state, candidate SHA, required checks and Owner
  Authorization through GitHub.
- Compared every reusable-workflow SHA in the PR branch with `main` ancestry.
- Updated PR #144's GitHub description to reflect its complete implemented
  scope and post-merge dependency.
- Ran `git diff --check` successfully.

## Created artifacts

- `docs/release/MACOS_RUNNER_BOOTSTRAP_MERGE_READINESS.md`
- this immutable Prompt History record

## Updated artifacts

- `ENGINEERING_STATUS.md`
- `REPOSITORY_STATUS.md`
- `MANAGEMENT_SUMMARY.md`
- `PROMPT_INDEX.md`
- PR #144 description

## Known limitations

This increment intentionally does not repin workflows. The exact replacement
SHA cannot be selected until PR #144's implementation exists on merged
`main`.

## Deferred work

After PR #144 is merged, repin the eight reusable-workflow callers and the
reusable workflow's canonical policy checkout to an immutable SHA on `main`.
Validate that increment before deleting the PR #144 feature branch.

## Recommended next prompt

Draft only — Platform Evolution: repin PR #144 bootstrap workflow references
to the immutable merged `main` SHA after the merge commit exists; validate the
callers and reusable workflow, then remove the feature branch.
