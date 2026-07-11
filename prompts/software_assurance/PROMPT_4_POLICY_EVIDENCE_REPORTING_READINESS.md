# Software Assurance Platform
## Prompt 4 of 4 - Policy, Evidence, Reporting and Implementation Readiness

Repository:

`pcvantol/djconnect`

## Context

Prompt 1 created the canonical Software Assurance Platform architecture.

Prompt 2 created the canonical Software Assurance capability model, backlog,
dependency graph and implementation order.

Prompt 3 integrated Software Assurance with the existing DJConnect Platform,
Verification Runtime, Execution Environment, execution targets, Platform
Health, Release Qualification and repository model.

This final architecture prompt defines the policy, evidence, reporting and
implementation-readiness model for future implementation waves.

This phase is architecture only.

No implementation should begin.

No CI workflows should be changed.

No scanners should be introduced.

No quality gates should be enabled.

## Mission

Create the canonical Software Assurance policy, evidence, reporting and
implementation-readiness architecture.

The objective is to define:

- quality policy ownership;
- policy classes;
- evidence classes;
- evidence retention posture;
- report schemas and report layers;
- repository health reporting;
- platform health reporting;
- release-assurance reporting inputs;
- implementation readiness criteria;
- adoption governance;
- relationship to Verification evidence;
- governance and non-duplication rules.

## Read First

Read completely:

- `AGENTS.md`
- `BOOTSTRAP_CODEX_SESSION.md`
- `docs/meta/README.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`
- all `SOFTWARE_ASSURANCE_*.md` documents;
- `PLATFORM_QUALITY_STANDARD.md`;
- `CI_CD_RELEASE_GOVERNANCE.md`;
- `docs/verification/08B_VERIFICATION_POLICIES.md`;
- `docs/verification/08B_VERIFICATION_MODES.md`;
- `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`;
- `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`;
- `tools/verification/README.md`;
- current GitHub Actions workflow inventory.

Inspect current implementation before proposing architecture.

## Required Deliverables

Create:

- `SOFTWARE_ASSURANCE_POLICIES.md`
- `SOFTWARE_ASSURANCE_EVIDENCE.md`
- `SOFTWARE_ASSURANCE_REPORTING.md`
- `SOFTWARE_ASSURANCE_IMPLEMENTATION_READINESS.md`

Update where appropriate:

- Software Assurance architecture and navigation;
- Platform Backlog;
- Repository Status;
- README/Foundation navigation;
- Prompt completion report.

## Requirements

Define canonical Software Assurance policy classes:

- local advisory;
- pull request advisory;
- pull request blocking;
- nightly;
- release candidate;
- production qualification;
- emergency/hotfix;
- research/non-blocking.

Define evidence classes for all Software Assurance themes and cross-cutting
capabilities.

Define reporting layers:

```text
Raw Evidence Reference
  -> Theme Report
  -> Repository Health Report
  -> Platform Health Report
  -> Release Assurance Input
```

Reports must distinguish:

- advisory findings;
- warning findings;
- blocking findings;
- release-blocking findings;
- stale evidence;
- missing evidence;
- waived findings;
- externally blocked findings.

Define implementation-readiness criteria for each future milestone, including:

- required canonical contracts;
- required verification method;
- required owner;
- required execution target model;
- required evidence retention posture;
- required rollback or waiver posture;
- required completion report.

Platform Health must remain trend reporting and must not override failed
release gates.

## Do Not

Do not:

- implement scanners;
- add SBOM generation;
- add report generators;
- modify GitHub Actions;
- modify CI workflows;
- modify Verification code;
- create release gates;
- mark any current workflow as newly required.

Architecture only.

## Acceptance Criteria

Prompt 4 is complete when the repository has canonical policy, evidence,
reporting and implementation-readiness architecture for Software Assurance,
and implementation has not started.

Complete this phase according to:

`docs/meta/PHASE_COMPLETION_PROTOCOL.md`

After completion, stop and report that the four-prompt Software Assurance
architecture sprint is complete.
