==============================================================================
SOFTWARE ASSURANCE IMPLEMENTATION PROMPT
==============================================================================

Status

COMPLETE

Architecture

COMPLETE

Implementation

COMPLETE

Current Platform State

Platform Evolution

Implementation Prerequisite

PLATFORM_BASELINE_V1_CERTIFIED

Prerequisite Status

SATISFIED

------------------------------------------------------------------------------

Activation metadata: Platform Baseline v1.0 Certification satisfied the
historical mandatory prerequisite `PLATFORM_BASELINE_V1_CERTIFIED` on
2026-07-12. Prompt 1 completed successfully on 2026-07-12. This prompt is now
complete. The cross-repository rollout consumed the canonical policy without
changing GitHub repository settings, rulesets, branch protection or CODEOWNERS.

------------------------------------------------------------------------------

# DJConnect Platform
## Software Assurance Platform
### Implementation
### Prompt 2 of 4 — Cross-Repository CI Governance Rollout

Repository:

pcvantol/djconnect

Prerequisite

PLATFORM_BASELINE_V1_CERTIFIED

Current Status

Software Assurance implementation is active.

Prompt 1 has completed successfully.

The reusable Software Assurance CI Governance implementation now exists.

This phase rolls that implementation out across the complete DJConnect platform.

------------------------------------------------------------------------------

Mission

Deploy the canonical CI Governance implementation to every active DJConnect
repository.

Do not redesign governance.

Do not redesign policies.

Consume the reusable implementation produced by Prompt 1.

The objective is one consistent CI platform.

------------------------------------------------------------------------------

Read first

Read completely:

Platform Strategy

Platform Baseline

SOFTWARE_ASSURANCE_IMPLEMENTATION.md

CI Governance implementation

Execution Profiles

Runner Policy

Retention Model

Validation Model

Repository Ownership

Repository Bootstrap

Prompt Index

Phase Completion Protocol

Current repository inventory

Current GitHub Actions workflows

------------------------------------------------------------------------------

Repository Discovery

Determine every active repository using Repository Ownership.

Do not use hardcoded repository names.

Inventory for every repository:

Workflow files

Reusable workflows

Workflow permissions

Concurrency

Timeouts

Caches

Artifacts

Runner usage

Triggers

Workflow documentation

Current deviations

Generate rollout inventory.

------------------------------------------------------------------------------

Rollout Strategy

The rollout must consume the reusable implementation.

Do not duplicate policy.

Repositories should inherit the canonical implementation.

Repository-specific overrides remain explicit.

------------------------------------------------------------------------------

Workflow Harmonization

Update every workflow.

Normalize:

Naming

Permissions

Concurrency

Timeouts

Runner labels

Execution profile

Caching

Artifacts

Retention

Logging

Summaries

Action pinning

Workflow metadata

Workflow documentation

The implementation should become consistent across all repositories.

------------------------------------------------------------------------------

Execution Profiles

Apply the reusable execution profiles.

Economy

Balanced

Release

Every workflow should reference one execution profile.

Avoid repository-specific copies.

------------------------------------------------------------------------------

Permissions

Apply least privilege.

Canonical default:

permissions:

contents: read

Only elevate permissions when required.

Document every exception.

------------------------------------------------------------------------------

Runner Selection

Normalize runner selection.

GitHub-hosted Linux

Default.

GitHub-hosted macOS

Only where technically required.

Self-hosted

Only for:

Apple

Pi

ESP32

Voice

HA Lab

Parallels

Hardware-bound execution only.

------------------------------------------------------------------------------

Workflow Retention

Deploy the reusable retention implementation.

Routine workflows:

Retain maximum two completed workflow runs.

Support:

Dry run

Scheduled cleanup

Manual cleanup

Preservation exceptions

Repository rollout should consume Prompt 1 implementation.

------------------------------------------------------------------------------

Artifacts

Normalize:

Artifact naming

Retention

Compression

Evidence uploads

Failure uploads

Release evidence

Reduce duplicate storage.

------------------------------------------------------------------------------

Caching

Normalize caches.

NuGet

SwiftPM

PlatformIO

pip

npm

Docker

Use deterministic keys.

Remove obsolete caches.

------------------------------------------------------------------------------

Workflow Documentation

Every workflow should contain:

Purpose

Execution profile

Owner

Required runner

Expected outputs

Evidence

Failure behaviour

Generated from the reusable governance implementation where practical.

------------------------------------------------------------------------------

Cross-Repository Compliance

Generate:

Repository

Workflow Count

Compliant

Warnings

Overrides

Outstanding Work

Every repository should be comparable.

------------------------------------------------------------------------------

Repository Overrides

Repository-specific behaviour must be recorded.

Example:

Apple

requires

macOS

Pi

requires

SSH

ESP

requires

USB

Voice

requires

Audio

Document every override.

------------------------------------------------------------------------------

Validation

Validate:

Workflow syntax

Permissions

Concurrency

Timeouts

Execution profiles

Runner labels

Retention

Artifacts

Caches

Action versions

Cross references

Run:

git diff --check

Validate GitHub Actions.

Run dry-run rollout verification.

------------------------------------------------------------------------------

Deliverables

Update:

Every GitHub Actions workflow

Workflow documentation

Retention

Artifacts

Execution profiles

Runner configuration

Workflow metadata

Create:

CROSS_REPOSITORY_ROLLOUT_REPORT.md

Workflow Inventory

Override Register

Compliance Matrix

------------------------------------------------------------------------------

Acceptance Criteria

Every active repository now consumes the canonical CI Governance
implementation.

Workflow behaviour is consistent.

Execution profiles are in use.

Runner selection is standardized.

Retention policy is active.

Artifact policy is active.

Repository overrides are documented.

GitHub repository settings remain unchanged.

Prompt 3 owns GitHub configuration.

------------------------------------------------------------------------------

Completion

Complete according to:

docs/meta/PHASE_COMPLETION_PROTOCOL.md

Generate Prompt 3 only after successful completion.

Stop.

Do not modify GitHub repository settings.

Do not modify branch protection.

Do not modify repository rulesets.

Do not modify CODEOWNERS.

Prompt 3 owns GitHub governance.
