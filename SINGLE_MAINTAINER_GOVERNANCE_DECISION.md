# Single-Maintainer Governance Decision

Status: proposed canonical Trusted Delivery decision
Date: 2026-07-13
Decision: `SINGLE_MAINTAINER_GOVERNANCE_READY`

## Decision

DJConnect adopts `SINGLE_MAINTAINER_RISK_BASED_REVIEW_GOVERNANCE` for the
active Trusted Delivery implementation. It replaces a universal required
approving-review count with risk-based qualification.

Routine LOW_RISK and NORMAL_RISK changes require a pull request, current
branch, required objective checks, risk classification, qualification,
resolved conversations and a clean merge state. They do not require an
independent human approval and may be auto-merged by the Trusted Delivery App
only after those requirements pass.

HIGH_RISK changes require an explicit, auditable approval by the repository
owner. The Trusted Delivery App cannot approve HIGH_RISK work and cannot merge
it until the qualification gate confirms that approval. Direct routine pushes
to `main` remain prohibited. The owner retains an audited emergency override;
it is not a routine delivery route.

## Objective Deadlock

Live GitHub read-back on 2026-07-13 found only `pcvantol` as a direct human
collaborator in each affected source repository. GitHub cannot treat the PR
author as an independent approving reviewer. A universal required-review count
therefore makes routine single-maintainer delivery unsatisfiable. This is a
governance-operability defect, not a CI, action-pinning or code-quality
failure. Retaining that rule would prevent Prompt 3 completion.

## Options Evaluated

| Option | Assessment | Decision |
| --- | --- | --- |
| A — add an independent human | Gives strong separation but no qualified reviewer is available today. It requires durable trust, availability and CODEOWNERS maintenance, so it is not a viable prerequisite for routine delivery. | Not selected for routine work; may be added later. |
| B — independent review app | The existing App is controlled by the same maintainer and delivery system. A separate GitHub identity does not create ownership/control separation or meaningful independent assurance. | Rejected as an independent reviewer. |
| C — single-maintainer risk-based governance | Preserves objective verification and qualification for routine work while reserving explicit human approval for high-risk work. | Selected. |

## Native GitHub Boundary

GitHub branch protection can require pull requests, checks, conversation
resolution and a fixed approving-review count, but it does not natively make
that count conditional on a PR risk class or changed path. The policy is
therefore enforced by a required `Trusted Delivery qualification` check. That
check must calculate the risk class from the PR diff and fail HIGH_RISK work
until it observes an explicit owner approval. GitHub's fixed review-count is
set to zero for routine delivery; the custom check is the conditional gate.

This is a design target only. Applying repository settings, adding the required
check or granting merge automation remains a separate, explicitly authorized
GitHub configuration change.
