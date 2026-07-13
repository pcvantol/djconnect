# Trusted Delivery Single-Maintainer Governance Completion Report

Status: complete
Date: 2026-07-13
Decision: `TRUSTED_DELIVERY_GOVERNANCE_OPERATIONAL`
Repository: `pcvantol/djconnect`

## Executive Summary

The Trusted Delivery single-maintainer deadlock has been removed without
weakening Verification, Software Assurance or Trusted Delivery. A fixed GitHub
review count is replaced by a conditional, exact-SHA Owner Authorization status
inside the existing Trusted Delivery architecture.

## Scope and Implementation

- Trusted Delivery now separates technical qualification from governance
  authorization.
- LOW_RISK and NORMAL_RISK candidates publish successful `Owner Authorization`
  status with `NOT_REQUIRED` semantics.
- HIGH_RISK candidates remain blocked by a failing status until the configured
  owner runs the dedicated authorization workflow for the current candidate
  SHA.
- The authorization workflow validates repository, branch, PR number, current
  SHA, risk class, technical Trusted Delivery PASS and actor identity. It
  produces an immutable evidence artifact.
- The canonical root workflow provides a bootstrap-safe central dispatch path
  for the selected DJConnect repositories. It mints a short-lived GitHub App
  installation token scoped to exactly one validated target repository and
  writes only the exact-SHA `Owner Authorization` commit status.
- Technical Trusted Delivery is read from GitHub's status-check rollup, which
  is the canonical source that GitHub exposes to PR protection. This avoids
  treating an incomplete REST check-run listing as qualification evidence.
- The root caller invokes its local reusable Trusted Delivery workflow, so this
  implementation is exercised by its own pull request rather than an earlier
  shared-workflow revision.

## Verification and Evidence

- Unit tests prove successful HIGH_RISK authorization, rejection of LOW/NORMAL
  authorization, rejection without technical PASS and SHA invalidation.
- Workflow YAML is parsed and workflow references are checked for immutable
  third-party action pins.
- `git diff --check` validates whitespace integrity.

## Known Limitations and Follow-up

Consumer repositories must consume the merged thin dispatcher before they can
perform local self-authorization. Until then, the canonical root dispatcher
can authorize a qualified consumer candidate without changing branch
protection or weakening a technical check. It accepts only the explicit,
selected platform repositories and remains exact-SHA bound.

## Readiness

The governance model is operational in the canonical implementation: it is
fail-closed, exact-SHA bound, uses a single-repository installation token and
preserves all technical delivery gates. A live root candidate completed the
central authorization flow successfully before this documentation update.

## Next Phase

Merge the canonical central authorizer, authorize the nine qualified consumer
candidates through that root workflow, and then re-run their required checks.
Do not migrate any branch protection until each repository publishes the
expected required contexts without a gap.
