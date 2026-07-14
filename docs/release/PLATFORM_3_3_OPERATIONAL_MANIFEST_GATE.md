# Platform Release 3.3 — Operational Manifest Gate

Date: 2026-07-14  
Decision: `PLATFORM_RELEASE_3_3_CANDIDATE_BLOCKED`

## Scope and method

This is a read-only gate check for the requested `3.3.0` release across the
ten repositories in `REPOSITORY_OWNERSHIP.md`. The operator has subsequently
authorized preparation of a proposal with a private target scope. The fresh
source snapshot and proposed targets are recorded in
[`PLATFORM_3_3_OPERATIONAL_MANIFEST_PREPARATION.md`](PLATFORM_3_3_OPERATIONAL_MANIFEST_PREPARATION.md).

No workflow was dispatched, no artifact was created, and no external target
was changed.

## Result

All ten current `main` SHAs have a non-expired artifact named
`post-merge-release-evidence`. These records support post-merge governance;
they are not deployable release artifacts and contain no approved
manifest-bound artifact ID/checksum pair.

The static-consumer branches have subsequently been merged. Their current-main
CI and artifact evidence must still be reconciled before a candidate can bind
them. For Apple, the internal unsigned build artifact is consumed by the Apple
Secure Distribution Relay; `djconnect-app-releases` is not a signed public
publication target for this `INTERNAL_RELEASE`.

| Gate | Result |
| --- | --- |
| Exact current-main SHA inventory | Present; refreshed in preparation record |
| Required target set | Proposed, pending final approval |
| Deployable artifact IDs and SHA-256 bindings | Missing |
| Verification, coverage, Software Assurance and Trusted Delivery evidence bound to a candidate | Missing |
| Explicit operational-manifest approval | Missing |
| Authorized deployment or smoke dispatch | Not performed |

## Consequence

The proposal in `PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json` remains
`NOT_APPROVED`. It is not valid to convert the proposal into an operational
manifest, dispatch a deployment/smoke workflow, tag a release or publish any
of the ten components.

## Required operator decisions

1. Review, merge and publish the static consumer branches where they are
   intended to be part of current `main`.
2. Produce qualified deployable artifacts and exact SHA-256 bindings for each
   required target, then bind current-main verification and delivery evidence.
3. Explicitly approve the resulting complete manifest. It must use the Apple
   Secure Distribution Relay for private devices and must not treat
   `djconnect-app-releases` as a public publication target.
4. Explicitly authorize only the resulting manifest-bound deployment and
   smoke dispatches.
