# HACS Pull Request Validation Reliability Assessment

**Status:** Assessment complete  
**Decision:** `GO_HACS_PR_RELIABILITY_CLASSIFIED`  
**Scope:** Existing Home Assistant/HACS validation route and retained GitHub
evidence only. No workflow, action, product or verification behavior change.

## Objective

Classify the reliability and governance position of HACS pull-request
validation in the existing DJConnect Verification Pipeline. This assessment
does not diagnose an unobservable root cause, change a failed result, or
authorize a release.

## Repository reconciliation

The current reusable validation route is
`.github/workflows/djconnect-ha-integration-ci.yml`, called by
`.github/workflows/validate.yaml` for both `pull_request` and `push` events.
The HACS job runs on `ubuntu-latest` after a pinned checkout and invokes the
pinned `hacs/action@1ebf01c408f29afcb6406bd431bc98fd8cbb15aa` with
`category: integration`. The caller retains the default `run-hacs: true`; the
job has no `continue-on-error` setting. The workflow has `contents: read` only.

The same validation route also provides repository tests, Ruff, Bandit,
dependency audit, hassfest and Software Assurance policy validation. The
separate Verification Framework unit-test job shares the caller workflow;
Advisory Golden Smoke runs on pull requests and Advisory Golden Regression on
non-pull-request invocations. CodeQL and Semgrep remain separate workflows.

## Reliability evidence

| Evidence | Observed result | Classification consequence |
| --- | --- | --- |
| PR [#459](https://github.com/pcvantol/djconnect/pull/459) | The retained HACS jobs completed for both the pull-request head and merge commits. | The configured pinned action can validate both PR ref forms. |
| PR [#461](https://github.com/pcvantol/djconnect/pull/461) | Retained head and merge jobs both failed before content validation with `Not Found` / repository loading; the `main` run completed. | A loading failure is not a repository-content verdict. It is an observed PR/lifecycle-associated external-loading limitation, not a proven race or deterministic ref defect. |
| PR [#500](https://github.com/pcvantol/djconnect/pull/500) | `validate / hacs` completed successfully in the current unchanged route. | The current route continues to produce completed PR content-validation evidence. |
| PR #280, #456 and #457 | Historical records report the same loading phase, but primary job logs are no longer retained. | They establish recurrence of the symptom, not a reproducible repository, action or infrastructure cause. |
| Action pinning record | The action source is immutable; its upstream container image remains a governed mutable-image exception. | Mutable-image risk is residual only and is not evidence of an action regression. |

## Reliability classification

HACS is **execution-required engineering evidence** in the current validation
workflow: it is enabled by default and a completed HACS content finding fails
its job. It is **not deterministic as an isolated pull-request reliability
oracle** because retained evidence contains both completed PR validations and
repository-loading failures that never reached content validation.

The historical failures classify as **external repository-loading failures with
an observed PR/lifecycle association**. They are not classified as a DJConnect
repository defect, metadata defect, proven merge-context defect, action
regression, infrastructure root cause or a temporary external cause: retained
evidence does not establish any one of those causes. A fresh recurrence needs
its own preserved log, checkout ref and action-image metadata before cause
classification.

## Evidence ownership and dependency boundary

HACS independently supports the narrow question whether the checked-out Home
Assistant custom-integration repository completes HACS validation. It may
support engineering review of integration packaging and repository content when
it completes. It does not own or decide:

- DJConnect product behavior, Runtime, Renderer, API, Broadcast, Planner,
  Knowledge Engine or Session Flow correctness;
- Golden Scenario behavior or qualification authority, which remain with the
  existing Golden Smoke/Regression profiles and the Verification Foundation;
- repository test, lint, static-security, dependency or Home Assistant
  conformance results, which remain with tests, Ruff, Bandit, dependency audit
  and hassfest respectively;
- software-assurance policy, code-analysis or security-scanning results, which
  remain with Software Assurance governance, CodeQL and Semgrep; or
- release authorization, which requires the wider Verification Pipeline and
  separately recorded release evidence.

A successful HACS pull-request job therefore cannot authorize a release. A
completed HACS content failure remains a failed job and is not suppressed, but
a repository-loading failure must be interpreted as a failed validation route,
not as a content finding.

## Governance position

Within the AI-Native Engineering Operating System, HACS is a bounded,
read-only Software Assurance input to the Verification Pipeline. Its
`contents: read` execution, immutable action-source pin and integration
category constrain the evidence it produces. It is advisory/non-blocking for
release authority: this assessment adds no branch protection, release gate,
retry, failure masking, alternative validator or action-pinning change.

The complete Verification Pipeline remains the decision context. Post-merge
qualification and release evidence remain separately owned; neither is replaced
by HACS pull-request success.

## Recommendation

**Exactly one next step:** after this assessment merges, run its dedicated
Finalization increment to reconcile rolling records. Do not implement a HACS
workflow change unless a future, preserved recurrence supplies new objective
evidence.
