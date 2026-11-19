# Phase Completion Protocol

**Status:** Canonical Engineering Guidance

**Audience:** Engineers, reviewers and AI agents

**Scope:** Entire DJConnect platform

---

# Purpose

Every implementation phase must finish in a consistent, reproducible and reviewable way.

The objective of this protocol is to ensure that every completed phase leaves:

- the implementation;
- the documentation;
- the verification;
- the repository;
- and the engineering knowledge

in a better state than before.

Completion is not defined by "the code compiles".

Completion is defined by a qualified engineering outcome.

---

# Core Principle

> Every completed phase must increase repository knowledge.

Implementation without durable knowledge is considered incomplete.

---

# Capability Completion Lifecycle

Every implementation capability follows the canonical lifecycle in
`ENGINEERING_METHOD.md`:

```text
PRE-FLIGHT -> IMPLEMENTATION -> VALIDATION -> MERGE -> FINALIZATION
-> WORKSPACE CLEANUP -> MERGED_RECONCILED + WORKSPACE_READY -> NEXT CAPABILITY
```

At the conclusion of every implementation phase, execute the following
completion protocol. Its implementation pull request is not capability
completion: after merge, the separate Finalization increment reconciles the
repository, then mandatory local-only Workspace Cleanup establishes
`WORKSPACE_READY`. The next capability requires both states.

```
Implementation

↓

Review

↓

Verification

↓

Evidence

↓

Investigation

↓

Repository Updates

↓

Completion Report

↓

Qualification Decision

↓

Next Phase Generation

↓

Stop
```

Never continue directly into the next phase.

---

# Step 1 — Implementation Review

Review the completed implementation.

Verify:

- implementation scope;
- architecture compliance;
- coding standards;
- documentation;
- ownership boundaries;
- verification readiness;
- repository hygiene.

Determine whether the phase objective has actually been achieved.

---

# Step 2 — Verification

Execute every verification activity required by the current phase.

Examples include:

- unit tests;
- integration tests;
- verification scenarios;
- smoke tests;
- live validation;
- repository validation;
- environment qualification.

Verification must produce evidence.

Never assume success.

---

# Step 3 — Evidence Collection

Collect all evidence produced by verification.

Examples:

- logs;
- reports;
- runtime metadata;
- screenshots;
- environment snapshots;
- CI metadata;
- storage snapshots;
- timing information;
- generated artifacts.

Evidence should be reproducible.

---

# Step 4 — Investigation

If verification identifies failures:

Classify them before changing implementation.

Possible classifications include:

- implementation defect;
- verification defect;
- execution environment defect;
- documentation mismatch;
- technical design mismatch;
- architecture mismatch;
- external dependency;
- environment issue;
- unknown.

Do not immediately modify implementation.

Understand the failure first.

---

# Step 5 — Repository Intelligence Review

Ask the following question:

"What knowledge discovered during this phase should never have to be rediscovered?"

If the answer is:

"Something"

then update the repository.

Possible destinations include:

Foundation

Technical Design

Verification

Meta Engineering

Platform Backlog

Completion Report

Prompt Library

Never leave important knowledge only in memory.

---

# Step 6 — Architecture Impact Assessment

Determine whether this phase changes:

Platform Foundation

Platform Baseline

Architecture

Ownership

Responsibilities

Contracts

If architecture changed:

Update the appropriate canonical document.

Do not silently change architecture through implementation.

---

# Step 7 — Technical Design Assessment

Determine whether implementation reality changed.

Examples:

HTTP

WebSocket

Pairing

Storage

Logging

Runtime

Deployment

If implementation differs from Technical Design:

Update Technical Design.

---

# Step 8 — Verification Assessment

Determine whether the Verification Platform requires updates.

Examples:

Scenario Catalog

Verification Matrix

Verification Data

Verification Modes

Verification Policies

Planning Engine

Execution Environment

Prompt Library

Update only the affected subsystem.

---

# Step 9 — Meta Engineering Assessment

Determine whether engineering practice improved.

Examples:

New workflow

New heuristic

New collaboration model

New AI guidance

New lesson

If yes:

Update the appropriate Meta Engineering document.

Do not duplicate knowledge.

---

# Step 10 — Platform Backlog

Move all remaining work into the canonical backlog.

Do not leave:

TODO comments

Temporary notes

Untracked work

Document:

priority

owner

blocking status

recommended phase

---

# Step 11 — Completion Report

Create or update the canonical Completion Report.

Every report must include:

Decision

Branch

Commit SHA

Pull Request

Validation performed

Created documents

Updated documents

Outstanding blockers

Recommended next prompt

The report may add implementation, evidence, scope and readiness detail, but
must not omit the completion contract above.

Completion Reports document what actually happened.

---

# Step 12 — Qualification Decision

Every phase ends with one explicit decision.

Examples:

PASS

PASS WITH WARNINGS

NOT QUALIFIED

BLOCKED

The decision should be evidence-based.

Not opinion-based.

---

# Step 13 — Next Phase Generation

Determine the next engineering action.

If the phase is qualified and a next increment is authorized:

Generate it as `Draft`.

If the phase is not qualified:

Generate a remediation prompt.

Store the prompt in the Prompt Library.

Update:

PROMPT_INDEX.md

Do not activate or execute the next phase until this increment has exactly one
reviewable pull request.

---

# Step 14 — Bootstrap Assessment

Determine whether repository bootstrap documentation requires updates.

Possible documents include:

AGENTS.md

BOOTSTRAP_CODEX_SESSION.md

BOOTSTRAP_CODEX_VERIFICATION.md

Prompt Index

Meta Engineering

Update only when genuinely required.

Avoid unnecessary churn.

---

# Step 15 — Pull Request Creation

Before merging, create exactly one reviewable pull request for the completed
engineering increment. Confirm that it has one coherent objective and can be
reviewed independently. Merge remains a separate explicit governance decision.

Verify:

documentation

reports

verification

repository navigation

prompt library

completion report

No phase should merge incomplete documentation.

---

# Step 16 — Pull Request Review

Before merging:

Verify:

documentation

reports

verification

repository navigation

prompt library

completion report

No phase should merge incomplete documentation.

---

# Step 17 — AI Memory Check

Ask one final question.

"If this conversation disappeared forever, would any important engineering knowledge disappear with it?"

If the answer is yes:

Move that knowledge into the repository.

The repository should become progressively more complete.

---

# Step 18 — Final Output

Every completed capability should produce:

Completion Report

Qualification Decision

Updated Documentation

Merged Finalization with updated rolling records, Prompt History and applicable
roadmap/governance records

Workspace Cleanup report with `WORKSPACE_READY` decision and explicit stale
local branch result (`none` or named branches with disposition)

User-facing two-PR management feedback summary for the Product & Platform
Architect: outcomes, preserved boundaries, validation, remaining decisions and
combined planning feedback from repository/GitHub evidence only

User-facing Product and Platform position: current program/cycle, roadmap phase
and active increment, plus a tentative three-to-five-item canonical
roadmap/backlog projection with source, status, gates and explicit
reprioritization caveat

Repository Improvements

Commit SHA

Pull Request

`MERGED_RECONCILED` and `WORKSPACE_READY` decisions and recommended next
capability

Clean-session bootstrap command

---

# Stop Condition

After all required outputs have been produced:

Stop.

Do not automatically execute the next implementation phase.

Every new phase begins from a clean engineering session.

---

# Definition of Done

A phase is complete only when:

✓ Implementation is complete

✓ Verification has executed

✓ Evidence exists

✓ Pre-Flight ended in `GO`

✓ Implementation and Validation are complete for the stated scope

✓ Production implementation merged

✓ Finalization merged

✓ Rolling records and applicable roadmap/governance records are synchronized

✓ Immutable Prompt History is recorded

✓ Governance and repository-bootstrap validation passed

✓ Repository state is `MERGED_RECONCILED`

✓ No important engineering knowledge exists only in conversations

---

# Closing Principle

Code is temporary.

Engineering knowledge is cumulative.

Every completed phase should leave the repository more valuable than the implementation alone.

The implementation solves today's problem.

The repository should help solve tomorrow's.
