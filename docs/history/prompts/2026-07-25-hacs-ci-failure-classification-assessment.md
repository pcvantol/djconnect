# Prompt History: HACS CI Failure Classification Assessment

**Prompt ID:** HACS CI Failure Classification Assessment

**Generation:** Generation 2

**Engineering program:** Platform Evolution

**Branch:** `codex/hacs-ci-failure-classification-assessment`

**Decision:** `HACS_CI_WORKFLOW_CORRECTION_REQUIRED`

**Execution date:** 2026-07-25

**Created:** 2026-07-25

## Objective

Assess only the repeated `validate / hacs` repository-loading failure from PR
#456. Determine whether it is a repository-content defect, branch/ref issue,
external HACS failure, action regression or unreliable validator signal, and
whether a minimal workflow correction is required. Do not implement a workflow
correction.

## Outcome

The pinned HACS action fails consistently only for pull-request head and merge
refs, before HACS content validation begins. The same action, category and
repository pass on post-merge `main`; PR #280 records the same prior pattern.
The failure is therefore ref-dependent and reproducible, not a repository
content defect or a transient external event.

The assessment records `HACS_CI_WORKFLOW_CORRECTION_REQUIRED`: the existing
PR check is not an actionable repository-content signal, while canonical-main
HACS validation remains valid. It proposes exactly one bounded follow-up
workflow-correction prompt and does not change CI, action pinning, governance,
blocking semantics, Runtime, Verification or product behavior.

## Evidence

- PR #456 failed HACS loading for its pull-request merge ref.
- PR #457 reproduced the failure for both its head and merge refs.
- Post-merge `main` run 30151280296 passed HACS validation.
- PR #280 already recorded the same pre-validation HACS loading failure.
- The shared workflow and `hacs/action` source pin were inspected; the existing
  mutable Docker-image exception is recorded as residual risk only.

## Validation

- focused documentation/governance validation
- `git diff --check`
- objective GitHub run and job-log evidence for PR #456, PR #457 and `main`

## Recommended next prompt

Implement only the separately authorized HACS PR-ref validation reliability
correction defined by the assessment. Preserve HACS content failures,
permissions, source pinning and advisory/non-blocking semantics; add no retry,
gate or second validator.
