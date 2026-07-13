# Trusted Delivery Single-Maintainer Governance

Status: operational implementation policy
Owner: `pcvantol`
Scope: every active repository that consumes the canonical Trusted Delivery
workflow

## Purpose

DJConnect has one repository owner. A fixed GitHub approving-review count is
therefore neither an independent control nor an executable requirement for an
owner-authored pull request. This policy keeps the technical gates intact while
making the owner decision explicit, attributable and tied to one immutable
candidate SHA.

Trusted Delivery remains the single governance engine. Owner Authorization is
one capability within that engine; it is not a second review process and it
does not replace a technical gate.

## Canonical decision model

| Risk class | Technical qualification | Owner Authorization | Merge state |
| --- | --- | --- | --- |
| `LOW_RISK` | Verification, Software Assurance and Trusted Delivery must pass. | `NOT_REQUIRED`; the status succeeds automatically. | Eligible after all required technical statuses pass. |
| `NORMAL_RISK` | Verification, Software Assurance and Trusted Delivery must pass. | `NOT_REQUIRED`; the status succeeds automatically. | Eligible after all required technical statuses pass. |
| `HIGH_RISK` | Verification, Software Assurance and Trusted Delivery must pass. | Required from `pcvantol` for the exact current candidate SHA. | Blocked until the owner status succeeds. |

The required technical checks are never bypassed by authorization. A changed
pull-request head receives a new SHA and is unauthorized until it is evaluated
again. A stale authorization is therefore not merge evidence.

## Technical operation

`Trusted Delivery qualification` classifies the pull request and publishes a
commit status named `Owner Authorization` on its head SHA:

- LOW/NORMAL: successful with `NOT_REQUIRED` semantics;
- HIGH: failing with `HIGH_RISK authorization required for this exact SHA`.

The technical Trusted Delivery check can pass for a qualified HIGH_RISK
candidate while the separate required Owner Authorization status remains
blocking. The repository owner dispatches `Owner Authorization` only after the
technical check passes. The workflow validates the supplied repository,
target branch, PR number and full head SHA against GitHub's current PR state,
the HIGH_RISK status and the technical Trusted Delivery check. It accepts only
the configured owner actor and then publishes success for that exact SHA.

The workflow artifact is immutable evidence, containing repository, branch,
PR number, candidate SHA, risk classification, owner, GitHub actor, workflow
run id, timestamp and result.

## Branch-protection target

Each active repository's `main` protection must require:

1. its normal technical checks;
2. `Trusted Delivery qualification / Qualify trusted delivery`; and
3. `Owner Authorization`.

Fixed approving-review counts must be zero. GitHub protection cannot express
a risk-conditional review count; the SHA-bound status does. The target matrix
records rollout state and branch-protection gaps. Protection must not be
changed to require this status in a repository until that repository consumes
the canonical workflow that publishes it.

## Boundary and rollout

The root repository uses its local reusable workflow so the pull request that
introduces this policy qualifies the implementation it contains. Consumer
repositories must pin the shared workflow after the root merge and add the
same status permission to their callers before their protection is migrated.
This is a sequenced rollout, not a parallel governance model.

No authorization creates an artifact, publishes a release, deploys software,
or changes a repository branch. It only records a governance decision after
the candidate's technical qualification is already PASS.
