# DJConnect Software Assurance Governance

Status: canonical governance  
Scope owner: `pcvantol/djconnect`  
Phase: architecture frozen; Software Assurance Generation 1 active; Prompt 1 ready for explicit execution

## Purpose

This document defines governance for future Software Assurance implementation.

It freezes architecture ownership and defines how Software Assurance backlog
items, findings, gates and future implementation work are governed.

No functionality is implemented by this document.

## Final Architecture Decision

```text
SOFTWARE_ASSURANCE_PLATFORM_ARCHITECTURE_COMPLETE
```

The Software Assurance Platform architecture is now frozen.

The following historical prerequisites had to be satisfied before
implementation:

- all primary adapters are complete;
- cross-platform qualification has completed.

## Implementation Prerequisites

Software Assurance implementation may begin only after all of these are true:

- Home Assistant qualified;
- Apple qualified;
- Raspberry Pi qualified;
- ESP32 qualified;
- Voice Endpoint qualified;
- Windows qualified;
- cross-platform qualification completed;
- Verification Runtime released as stable;
- Platform Baseline updated.

These prerequisites must not be weakened by repository-local prompts,
workflow changes or partial milestone pressure.

They are satisfied. Prompt 1 completed the reusable CI Governance Foundation;
Prompt 2 is active and remains subject to explicit authorization.

## Ownership

Software Assurance owns:

- engineering quality governance;
- capability model;
- quality policies;
- evidence taxonomy;
- execution profile governance;
- Platform Health governance;
- release-assurance input model;
- quality backlog governance.

Software Assurance does not own:

- product behaviour;
- Verification scenarios;
- platform adapters;
- runtime execution;
- source implementation;
- release publication;
- repository-local tool details.

Verification remains owner of behavioural correctness and qualification.

## Backlog Governance

Backlog flow:

```text
Finding
  -> Evidence
  -> Investigator
  -> Classification
  -> Risk Assessment
  -> Backlog Recommendation
  -> Platform Backlog
  -> Repository Work
```

Tools, scanners and dashboards may produce findings. They must not create
backlog items directly.

Backlog items are prioritized by:

- release impact;
- security/privacy risk;
- affected repositories;
- evidence confidence;
- recurrence;
- prerequisite status;
- implementation wave;
- cost of delay;
- available owner.

## Security Finding Governance

Security findings become backlog recommendations only after:

- evidence is captured and redacted;
- affected repository or platform owner is identified;
- severity and exploitability are classified;
- release impact is determined;
- false-positive review is complete when applicable;
- remediation scope is separated from policy or tooling scope.

Security findings that affect active releases may be routed to hotfix or
release governance. The finding still requires owner and evidence
classification.

## False Positive Governance

False positives must be handled as classified findings, not hidden.

A false-positive record should include:

- source evidence;
- reason for classification;
- owner of the classification;
- expiration or review trigger where appropriate;
- whether the false positive affects policy, tooling or repository code.

Suppressions must be scoped and reviewable.

## Duplicate Finding Governance

Duplicate findings are merged by canonical identity:

- same root cause;
- same owning repository or platform subsystem;
- same evidence class;
- same affected artifact, dependency, file family or release item;
- same remediation path.

Merged findings retain all evidence references and preserve the highest
applicable release impact until reclassified.

## Platform-wide Finding Decomposition

Platform-wide findings are decomposed into:

- canonical platform work;
- Verification Runtime work;
- repository-specific work;
- release repository work;
- documentation or governance work.

One platform-wide finding may produce multiple repository work items, but the
canonical root finding remains the parent.

## Architecture Freeze Rule

Future changes must extend existing Software Assurance themes, capabilities,
interfaces and governance documents.

Do not introduce new architectural subsystems without explicit architectural
review.

Allowed future changes:

- add capabilities under existing themes;
- refine policies;
- add evidence classes;
- add repository-specific extensions;
- update rollout milestones;
- add accepted ADRs when architecture genuinely changes.

Not allowed without architectural review:

- new assurance platform beside Software Assurance;
- duplicated evidence stores;
- workflow-owned quality policy;
- scanner-owned backlog;
- release gates not tied to canonical policy;
- new themes that bypass the frozen model.

## Definition Of Done

Future Software Assurance implementation work is done only when:

- prerequisite gates for the implementation wave are met;
- owner and repository scope are explicit;
- evidence contract is used;
- verification method is recorded;
- release impact is classified;
- Platform Health impact is known;
- documentation is updated;
- completion report exists;
- no ownership has moved silently;
- no implementation has created hidden quality gates.
