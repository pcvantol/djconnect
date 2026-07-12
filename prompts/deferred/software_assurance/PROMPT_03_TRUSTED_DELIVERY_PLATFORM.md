==============================================================================
SOFTWARE ASSURANCE IMPLEMENTATION PROMPT
==============================================================================

Status

BLOCKED_BY_PROMPT_2

Architecture

COMPLETE

Implementation

NOT STARTED

Current Platform State

Platform Evolution

Implementation Prerequisite

PLATFORM_BASELINE_V1_CERTIFIED

Prerequisite Status

SATISFIED

------------------------------------------------------------------------------

Activation metadata: Platform Baseline v1.0 Certification satisfied the
historical mandatory prerequisite `PLATFORM_BASELINE_V1_CERTIFIED` on
2026-07-12. This prompt remains blocked until Prompt 2 has completed
successfully; implementation has not started.

------------------------------------------------------------------------------

# DJConnect Platform
## Software Assurance Platform
### Implementation
### Prompt 3 of 4 — Trusted Delivery Platform

Repository:

pcvantol/djconnect

Prerequisite

PLATFORM_BASELINE_V1_CERTIFIED

Current Status

Prompt 1 completed.

Reusable CI Governance implementation exists.

Prompt 2 completed.

All repository workflows consume the canonical implementation.

This phase implements the Trusted Delivery Platform.

The objective is to create one canonical automated delivery model across every
DJConnect repository.

This phase modifies GitHub repository configuration.

It intentionally does not modify product functionality.

------------------------------------------------------------------------------

Mission

Implement the canonical Trusted Delivery Platform.

The platform must support:

AI implementation

↓

branch

↓

pull request

↓

automated verification

↓

automated qualification

↓

automatic merge

↓

post-merge verification

↓

release readiness

Routine implementation must not require manual review or merge approval.

Safety is provided through objective gates.

Not through manual clicks.

------------------------------------------------------------------------------

Read first

Read completely:

Platform Strategy

Platform Baseline

SOFTWARE_ASSURANCE_IMPLEMENTATION.md

CI Governance implementation

Workflow Harmonization Report

Repository Ownership

Execution Strategy

Verification Platform

Verification Runtime

Prompt Index

Phase Completion Protocol

------------------------------------------------------------------------------

Repository Discovery

Discover every active repository.

Inventory:

Branch protection

Rulesets

Merge methods

Required checks

Required reviews

Conversation resolution

CODEOWNERS

Dependabot

Workflow permissions

Environment protection

Secrets

Variables

Runner access

GitHub Apps

Auto Merge

Fork behaviour

Repository metadata

Generate the inventory.

------------------------------------------------------------------------------

Trusted Delivery Model

Implement one canonical delivery model.

The canonical path becomes:

Implementation

↓

Branch

↓

Pull Request

↓

Verification

↓

Qualification

↓

Trusted AI Merge

↓

Post Merge Verification

↓

Ready for Release

Direct push to main becomes exceptional.

------------------------------------------------------------------------------

Trusted AI Actor

Support a dedicated trusted AI delivery actor.

Preferred implementation:

GitHub App

Fallback:

approved GitHub Actions workflow

Last resort:

fine-grained PAT

The trusted AI actor may:

Create branches

Push to its branches

Create PRs

Update PRs

Enable Auto Merge

Merge qualifying PRs

Delete merged branches

It must not receive unrestricted administrator permissions.

------------------------------------------------------------------------------

Risk Classification

Implement canonical risk classes.

LOW_RISK

NORMAL_RISK

HIGH_RISK

Protected files should automatically become HIGH_RISK.

Examples:

Platform Strategy

Platform Foundation

Software Assurance

Verification

Repository Governance

Signing

Secrets

Release

Architecture

HIGH_RISK requires explicit human approval.

LOW_RISK and NORMAL_RISK may merge automatically.

------------------------------------------------------------------------------

Repository Rules

Normalize:

Protected main

Required checks

Conversation resolution

Current branch requirement

Merge methods

Delete merged branches

Force push disabled

Emergency owner override

Single-maintainer compatible

------------------------------------------------------------------------------

Single Maintainer Governance

The governance model must remain operational for one maintainer.

Requirements:

Routine AI delivery requires no manual merge click.

Required verification remains mandatory.

Conversation resolution remains mandatory.

Repository owner retains explicit emergency override.

No configuration may permanently lock out the owner.

Document the operating model.

------------------------------------------------------------------------------

Auto Merge

Implement canonical Auto Merge.

Conditions:

Required checks passed

Verification qualified

Security gates passed

Completion report exists

No unresolved blocking Investigator findings

No protected-path restriction

Current Platform Phase permits implementation

Auto Merge should become the normal path.

------------------------------------------------------------------------------

Protected Paths

Protect:

Platform Strategy

Platform Foundation

Software Assurance

Verification Platform

Repository Bootstrap

Cross Repository Governance

GitHub Governance

Secrets

Signing

Release

Architecture

Changes require:

HIGH_RISK

Human approval

------------------------------------------------------------------------------

Fork Security

Untrusted forks:

Hosted runners only

No secrets

No self-hosted

No signing

No release

No publishing

No hardware

Trusted AI path only applies to trusted repositories.

------------------------------------------------------------------------------

Repository Permissions

Normalize:

Workflow permissions

Rulesets

Branch protection

Environment protection

GitHub App permissions

Runner trust

Repository roles

Use least privilege.

------------------------------------------------------------------------------

CODEOWNERS

Harmonize ownership.

Protect:

Platform

Verification

Software Assurance

Release

Security

GitHub Actions

Bootstrap

Architecture

Ownership should remain compatible with the single-maintainer model.

------------------------------------------------------------------------------

Dependabot

Normalize:

Schedule

Grouping

Labels

Target branches

Security updates

Auto Merge policy

Maximum open PRs

------------------------------------------------------------------------------

Audit Trail

Every unattended AI merge should produce evidence.

Capture:

AI actor

Branch

PR

Commit SHA

Merge SHA

Risk Class

Verification

Qualification

Security

Completion Report

Merge Method

Post Merge Verification

Store no secrets.

------------------------------------------------------------------------------

Compliance

Generate one platform-wide compliance matrix.

Repository

Trusted AI Ready

Branch Protection

Rulesets

Permissions

Auto Merge

Runner Trust

Fork Security

CODEOWNERS

Dependabot

Compliance

Manual Actions Remaining

------------------------------------------------------------------------------

Manual Configuration

Generate:

MANUAL_GITHUB_CONFIGURATION.md

Only include settings that cannot be changed automatically.

Provide:

Current

Target

Verification

------------------------------------------------------------------------------

Validation

Validate:

Repository settings

Rulesets

Permissions

Auto Merge

Trusted AI actor

Fork security

Runner access

Protected paths

CODEOWNERS

Dependabot

Compliance

Read-back verification

Run:

git diff --check

------------------------------------------------------------------------------

Deliverables

Update:

Repository governance

Repository settings

CODEOWNERS

Dependabot

Repository metadata

Create:

TRUSTED_DELIVERY_REPORT.md

REPOSITORY_COMPLIANCE_MATRIX.md

MANUAL_GITHUB_CONFIGURATION.md

Exception Register

------------------------------------------------------------------------------

Acceptance Criteria

Every active repository supports:

Trusted AI delivery

Protected main

Required verification

Automatic merge after successful qualification

Single-maintainer operation

Emergency owner override

Fork isolation

Runner isolation

Repository compliance

Audit trail

No repository requires routine manual merge approval.

------------------------------------------------------------------------------

Completion

Complete according to:

docs/meta/PHASE_COMPLETION_PROTOCOL.md

Generate Prompt 4 only after successful completion.

Stop.

Do not modify Software Assurance Architecture.

Do not modify Platform Strategy.

Do not reopen platform architecture.

This phase establishes the Trusted Delivery Platform.
