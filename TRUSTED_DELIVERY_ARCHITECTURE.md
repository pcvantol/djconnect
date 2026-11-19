# Trusted Delivery Architecture

Trusted Delivery is the sole DJConnect governance engine. It separates
technical qualification from governance authorization without creating a
parallel review system.

For every pull request, Trusted Delivery publishes its technical qualification
and the SHA-bound `Owner Authorization` status. `LOW_RISK` and `NORMAL_RISK`
receive `NOT_REQUIRED` authorization success. `HIGH_RISK` receives a failing
authorization status until the repository owner runs the internal Owner
Authorization workflow for the exact current candidate SHA. The failing status
is deliberately separate from the passing technical qualification so branch
protection can require both without weakening either decision.

The authorization workflow validates repository, target branch, PR number,
current head SHA, HIGH_RISK status, Trusted Delivery technical PASS and the
GitHub actor. It then writes immutable workflow-artifact evidence and changes
only the `Owner Authorization` status for that SHA. A new SHA has no matching
status and is therefore automatically unauthorized.

Technical checks remain independent required checks. Owner Authorization cannot
change Verification, Software Assurance or Trusted Delivery results.

After merge, `Post-Merge Release Evidence` reconciles the qualified PR head
with the distinct exact `main` SHA. It validates GitHub merge provenance and
fresh main-SHA CI/coverage before publishing a separate immutable status. This
does not claim squash-merge SHA equality and does not weaken pre-merge gates.

Canonical policy: `TRUSTED_DELIVERY_SINGLE_MAINTAINER_GOVERNANCE.md`.
