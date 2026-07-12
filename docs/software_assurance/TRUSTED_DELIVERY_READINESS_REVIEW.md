# Trusted Delivery Readiness Review

Status: complete
Date: 2026-07-12
Scope: Software Assurance Generation 1 pre-Prompt 3 governance gate
Decision: `TRUSTED_DELIVERY_NOT_READY`

## Management Summary

Prompt 1 remains valid and Prompt 2 completed its rollout: the canonical
policy validates and every active repository consumes the pinned governance
workflow. The platform is not ready for Trusted Delivery because GitHub
governance protections and mandatory workflow controls are inconsistent across
the active repositories. No Trusted Delivery implementation or GitHub settings
change was performed by this review.

## Prompt 1 Foundation

The canonical policy, executable validation implementation, Economy/Balanced/
Release profiles and shared workflow metadata template are present. The policy
self-check passes. Workflow rollout remains a Prompt 2 capability; the policy
source itself keeps `workflow_rollout_enabled: false`.

## Prompt 2 Rollout and Repository Compliance Matrix

| Repository | Workflows | Governance consumer | Profile use | Classification |
| --- | ---: | ---: | --- | --- |
| `djconnect` | 9 | 8 | Balanced, Release | Blocking governance gaps |
| `djconnect-api` | 3 | 3 | Balanced | Blocking governance gaps |
| `djconnect-app` | 6 | 6 | Balanced, Release | Blocking governance gaps |
| `djconnect-app-releases` | 1 | 1 | Balanced | Blocking governance gaps |
| `djconnect-esp32` | 4 | 4 | Balanced, Release | Blocking governance gaps |
| `djconnect-firmware` | 1 | 1 | Balanced | Blocking governance gaps |
| `djconnect-pi` | 4 | 4 | Balanced, Release | Blocking governance gaps |
| `djconnect-pi-releases` | 1 | 1 | Balanced | Blocking governance gaps |
| `djconnect-website` | 4 | 4 | Balanced, Release | Blocking governance gaps |
| `djconnect-windows` | 4 | 4 | Balanced, Release | Blocking governance gaps |

The `djconnect` reusable governance workflow is the producer and is not a
consumer of itself; all other active workflows consume the pinned producer.

## Runner Readiness Summary

GitHub-hosted Linux is the predominant runner. macOS is justified for Apple
build/TestFlight work; Windows is justified for Windows qualification; ESP32,
Pi and release workflows retain their existing hardware or platform-specific
execution paths. No self-hosted runner inventory, capability-label
qualification, health record or cleanup evidence is registered. This is a
warning for future hardware Trusted Delivery, but not the primary current
blocker because Prompt 3 must establish the trusted delivery model first.

## Execution Profile Summary

The rollout assigns Balanced to CI/security/validation work and Release to
release, TestFlight and production deployment workflows. Economy is defined by
the canonical policy but is not used by a deployed workflow; this is
informational, not a blocker.

## Supply Chain Review

The newly introduced governance consumer is pinned by immutable SHA. Existing
third-party actions remain mixed: 115 references use version tags or floating
repository aliases across the active source repositories. GitHub Actions
settings report `sha_pinning_required: false` in every reviewed repository.
Compatibility review is required before any automatic rewrite. This is a
blocking Trusted Delivery prerequisite because policy requires immutable action
pinning and the platform cannot currently enforce it.

## Repository Overrides

Apple uses macOS and Release profiles for unsigned-release/TestFlight work;
ESP32 retains firmware and hardware release behavior; Pi retains SSH/runtime
requirements; website deployment uses Release; Windows retains Windows/macOS
release behavior; distribution repositories use standalone governance
workflows. These remain justified and documented. Voice and HA Lab are not
separate GitHub workflow repositories in this rollout.

## Outstanding Blockers

1. `BLOCKING` — `main` is unprotected in `djconnect-app-releases`,
   `djconnect-firmware`, `djconnect-pi-releases` and `djconnect-windows`.
2. `BLOCKING` — existing protection in the remaining repositories is
   inconsistent: several lack required status checks, administrator
   enforcement, review-conversation resolution, linear history or equivalent
   ruleset coverage.
3. `BLOCKING` — no reviewed repository has a ruleset; branch governance is
   therefore not consistently policy-driven.
4. `BLOCKING` — immutable third-party action pinning is neither complete nor
   enforced (`sha_pinning_required: false` everywhere).
5. `BLOCKING` — workflow quality remains inconsistent: active workflows are
   missing one or more canonical permissions, concurrency or timeout controls.
6. `BLOCKING` — no verified Trusted AI actor, auto-merge policy, CODEOWNERS
   enforcement, emergency-owner override model or repository-permission model
   is present as an enforced platform-wide governance contract.

## Outstanding Warnings

- Dependabot security updates are disabled in the app-release, ESP32 and
  firmware-distribution repositories.
- No self-hosted runner capability/health register exists.
- Existing third-party action aliases require repository-specific compatibility
  verification before SHA migration.
- Economy profile has no deployed workflow consumer.

## Validation Evidence

- canonical policy self-validation passed;
- all active workflow YAML files parsed successfully;
- all repositories and workflow consumers were inventoried;
- live GitHub API review covered branch protection, rulesets, Actions policy
  and workflow-token permissions for all ten repositories;
- `git diff --check` passed before this report was created;
- repository working trees were clean at review time.

## Final Decision

```text
TRUSTED_DELIVERY_NOT_READY
```

Prompt 3 must not begin until every blocking governance prerequisite has
objective, durable evidence. This review created no GitHub governance change
and does not authorize Trusted Delivery implementation.
