# Software Assurance — Trusted Delivery Single-Maintainer Governance Rollout

## Mission

Roll out the already-approved canonical Trusted Delivery Owner Authorization
capability to every active DJConnect repository. Do not redesign governance,
change risk classification, weaken technical gates, publish releases or deploy
software.

## Required sequence

For each repository discovered from `REPOSITORY_OWNERSHIP.md`:

1. Pin its Trusted Delivery caller to the merged canonical workflow revision.
2. Grant only the status permission required to publish `Owner Authorization`.
3. Prove LOW_RISK/NORMAL_RISK publishes `NOT_REQUIRED` success.
4. Prove HIGH_RISK publishes a blocking authorization status and can pass only
   after owner authorization for the exact head SHA.
5. Read back check-run names and status contexts.
6. Only then set branch protection to require the existing technical checks,
   `Trusted Delivery qualification / Qualify trusted delivery` and `Owner
   Authorization`, with fixed approving-review count zero.

Never change branch protection before the repository can publish its required
status. Record exact repository, workflow SHA, check context, branch-protection
read-back and evidence artifact for every migration.

## Decision

Produce exactly one result: `TRUSTED_DELIVERY_GOVERNANCE_ROLLOUT_COMPLETE` or
`TRUSTED_DELIVERY_GOVERNANCE_ROLLOUT_BLOCKED`.
