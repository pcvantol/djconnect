# HACS CI Failure Classification Assessment

**Status:** Superseded for current planning by
[`HACS_CI_VALIDATOR_EVIDENCE_RECONCILIATION_ASSESSMENT.md`](HACS_CI_VALIDATOR_EVIDENCE_RECONCILIATION_ASSESSMENT.md)

**Decision:** `HACS_CI_WORKFLOW_CORRECTION_REQUIRED`

**Scope:** Existing Home Assistant/HACS CI route only.

> **Current-planning note:** This assessment's historical observations remain
> intact, but its `HACS_CI_WORKFLOW_CORRECTION_REQUIRED` decision is superseded
> by PR #459 evidence that the same configured route successfully validated
> both a pull-request head commit and merge commit. The reconciliation
> assessment records the current `NO_GO_INSUFFICIENT_EVIDENCE` decision.

## Objective

Classify the repeated HACS repository-loading failure without changing the
DJConnect Runtime, product behavior, Golden Qualification, CI gates or action
pinning. Determine whether the existing HACS check produces a reliable,
actionable signal for pull requests and whether a minimal workflow correction
is needed before Product Development continues.

## Objective evidence

| Evidence | Observation | Conclusion |
| --- | --- | --- |
| PR [#456](https://github.com/pcvantol/djconnect/pull/456) HACS job | The reusable CI workflow checked out `refs/pull/456/merge`; the pinned HACS action then attempted `pcvantol/djconnect@codex/finalize-ai-collaboration-bootstrap` and returned `Not Found` before validation. | The failure occurred during external repository/ref loading, not a repository-content validation rule. |
| PR [#457](https://github.com/pcvantol/djconnect/pull/457) HACS jobs | Both the head-ref and merge-ref invocations used the same pinned action and failed with the same repository-loading result. | The result is reproducible across both pull-request ref forms, not a one-off merge-ref race. |
| Post-merge `main` run | The same pinned action validated `pcvantol/djconnect@refs/heads/main` successfully in [run 30151280296](https://github.com/pcvantol/djconnect/actions/runs/30151280296). | Current canonical repository content is accepted by HACS. |
| Earlier repository evidence | PR #280 records the same failure before repository validation could start. | The failure pattern predates PR #456 and is not introduced by its documentation changes. |
| Workflow and action configuration | `validate.yaml` invokes the shared workflow for both `pull_request` and `push`; the HACS job uses `hacs/action@1ebf01c408f29afcb6406bd431bc98fd8cbb15aa` with `category: integration`. The action source pin is governed, while its upstream Docker image remains the documented mutable-image exception. | No unpinned workflow reference, changed category or missing HACS job explains the failure. The mutable upstream image remains a residual risk, not proof of an action regression here. |

The HACS publisher documentation says its action is intended to validate a
pull-request fork or branch when configured for pull requests and the pushed
branch for push events. The observed PR-ref-only failure therefore conflicts
with the expected action mode, while the successful `main` run proves that
repository content reaches a valid HACS state after merge.

## Classification

This is not a DJConnect repository-content defect: HACS completed all
validation on current `main` using the same action pin and category. It is not
classified as transient: the identical failure appears for PR #280, PR #456
and both PR #457 ref forms. It is also not an evidenced action-pin regression:
the assessment found no pin change and the repository's governed exception
already records the action's mutable container-image residual risk.

The existing PR HACS check is therefore **not a reliable actionable
repository-content signal**. Its current failure text does distinguish loading
failure from an actual HACS validation finding, but CI presents both as the
same failed job. The canonical-main HACS run remains a reliable repository
health signal.

## Required boundaries

- Do not disable HACS validation or convert a failed HACS content validation
  into success.
- Do not alter action pinning, Software Assurance governance, advisory versus
  blocking semantics, branch protection or release gates in this assessment.
- Do not change Golden Scenarios, Qualification Foundation, Smoke, Regression,
  Session Intelligence or any DJConnect product behavior.
- Do not add retry infrastructure, a second CI/verification framework or a
  second HACS validator.

## Recommended next step

One separately authorized implementation prompt: **HACS PR-ref validation
reliability correction**. It must make the current PR-ref limitation explicit
and retain one real HACS validation on canonical `main`; it must preserve the
existing source pin, category, permissions and advisory/non-blocking
semantics. The prompt must add focused workflow-level evidence that an actual
HACS content validation failure remains visible and fails, while a documented
PR-ref loading limitation is classified distinctly rather than masquerading as
a repository-content failure. It must not introduce retries, gates, framework
layers or product changes.

No workflow correction is implemented by this assessment.
