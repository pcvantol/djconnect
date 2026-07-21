# Engineering Playbook

**Status:** Canonical Engineering Guidance

**Audience:** Engineers, architects, reviewers and AI agents

**Scope:** Entire DJConnect platform

---

# Purpose

This playbook describes how engineering work is performed within the DJConnect platform.

It defines the mandatory engineering workflow from prompt to reviewable pull
request, and the preferred lifecycle from idea to production.

The objective is consistency.

Every feature, refactor, architectural change and verification activity should follow the same engineering lifecycle.

---

# Core Principle

> Engineering is a sequence of small, verifiable improvements.

Large, risky, difficult-to-review changes are intentionally avoided.

Every completed phase should leave the platform in a better state than before.

---

# Canonical Engineering Workflow

Every canonical prompt represents exactly one engineering increment. Every
engineering increment terminates with exactly one reviewable pull request.
Merge is a separate, explicit governance decision. The canonical Capability
Completion Lifecycle, its `GO`/`NO-GO` Pre-Flight and post-merge Finalization
are defined in `ENGINEERING_METHOD.md`; this playbook does not duplicate that
operational contract.

Before this workflow begins, synchronize and verify current main, read the
canonical repository state and perform the implementation-reality check. The
mandatory sequence is defined in `PROMPT_INITIALIZATION.md`; planning must not
start earlier.

```text
Prompt

↓

Dedicated Branch

↓

Focused Implementation

↓

Validation

↓

Exactly One Reviewable Implementation Pull Request

↓

Merge

↓

Dedicated Finalization

↓

`MERGED_RECONCILED`

↓

Workspace Cleanup

↓

`WORKSPACE_READY`

↓

Next Capability
```

## Mandatory Rules

1. One prompt equals one engineering increment.
2. One engineering increment equals one reviewable pull request.
3. Every pull request has exactly one coherent objective and is independently
   reviewable.
4. Every increment leaves the repository in a valid state.
5. Merge remains an explicit governance decision; opening a pull request does
   not authorize its merge.
6. The next production capability must not begin until its predecessor's
   Finalization has merged, restored `MERGED_RECONCILED` and completed the
   canonical Workspace Cleanup to establish `WORKSPACE_READY`.
7. Canonical prompts must not compete for, or overlap on, implementation
   scope.

## Prompt Lifecycle And Governance

Canonical prompts use this lifecycle:

```text
Draft → Active → Completed → Deprecated → Archived
```

`Draft` is approved planning that is not yet executable. `Active` is the one
authorized engineering increment currently being executed. `Completed` means
the increment has a reviewable pull request and its completion contract is
recorded. `Deprecated` retains a superseded prompt for traceability.
`Archived` retains historical prompts outside active navigation.

The Prompt Index records the lifecycle state, owning branch, coherent
objective and resulting pull request. It permits exactly one `Active` prompt
while work is being executed. A completed prompt is never reactivated; later
work requires a new draft and a new explicit activation after the previous
reviewable pull request exists.

## Engineering Method Protection

The Canonical Engineering Workflow and its templates are the Engineering
Method. Only a dedicated Engineering Governance prompt may change this method.
Implementation prompts must follow it and must not modify it incidentally.

The operational V2 method is canonical in `ENGINEERING_METHOD.md`. It requires
current-main and implementation-reality verification before planning, a
repository-state bootstrap, immutable Prompt History and fail-closed branch
hygiene. `PROMPT_GOVERNANCE.md`, `PROMPT_FINALIZATION.md` and
`AI_SESSION_INITIALIZATION.md` define the non-duplicated execution contracts.

Innovation Engineering is the explicit learning-oriented mode of this method.
Its intentionally lighter governance, branch and deployment rules, and
Innovation Review outcomes are defined in `INNOVATION_ENGINEERING.md`.
Innovation work remains subject to the non-negotiable repository-integrity and
safety controls in the canonical workflow.

---

# Engineering Lifecycle

All significant work follows the same lifecycle.

```
Idea

↓

Discovery

↓

Assessment

↓

Architecture

↓

Foundation

↓

Implementation Planning

↓

Implementation

↓

Verification

↓

Review

↓

Merge

↓

Baseline Update

↓

Lessons Learned
```

Not every task requires every step.

The larger the impact, the more of the lifecycle should be completed.

---

# Phase 1 — Discovery

Understand the problem.

Questions include:

- What problem is being solved?
- Who benefits?
- What repositories are involved?
- What assumptions exist?
- What constraints exist?
- Is there already a solution?

Discovery should produce understanding.

Not code.

---

# Phase 2 — Assessment

Assess the current situation.

Examples:

- technical debt
- product debt
- operational debt
- architecture
- security
- privacy
- repository structure
- verification
- CI/CD

Assessment should be evidence-based.

---

# Phase 3 — Architecture

Architecture comes before implementation.

Typical outputs:

- architectural decisions
- ownership
- responsibilities
- contracts
- quality attributes
- implementation strategy

Implementation should not begin until architectural direction is sufficiently understood.

---

# Phase 4 — Foundation

Long-lived knowledge belongs in the Foundation.

Examples:

- principles
- terminology
- governance
- platform baselines
- contracts

Foundation changes should be relatively rare.

---

# Phase 5 — Planning

Implementation should be divided into small phases.

Every phase should define:

- objective
- scope
- out-of-scope
- acceptance criteria
- expected outputs

Large implementations should never be attempted in one step.

---

# Phase 6 — Implementation

Implementation follows the approved architecture.

Implementation should:

- remain incremental;
- be reviewable;
- minimise unnecessary change;
- preserve repository quality;
- update documentation where required.

---

# Phase 7 — Verification

Implementation is not complete until it is verified.

Verification should demonstrate behaviour through evidence.

Examples:

- unit tests
- integration tests
- verification scenarios
- evidence collection
- reports

Passing tests alone do not replace engineering judgement.

---

# Phase 8 — Review

Every meaningful change should be reviewed.

Review considers:

- correctness
- architecture
- maintainability
- security
- privacy
- verification
- documentation

The objective is platform quality.

Not approval speed.

---

# Phase 9 — Merge

Merge only after:

- verification;
- review;
- documentation;
- completion report.

Main should remain deployable.

---

# Phase 10 — Baseline

After important milestones:

Create or update:

- Platform Baseline
- Completion Report
- Lessons Learned
- Prompt Index
- Architecture Decisions

The repository should become more complete after every milestone.

---

# Working Agreements

Prefer:

- small pull requests;
- deterministic verification;
- evidence-backed decisions;
- repository-native documentation;
- reusable abstractions.

Avoid:

- speculative abstractions;
- large refactors without architectural justification;
- undocumented decisions;
- hidden assumptions;
- architecture drift.

## Architecture Freeze Operating Rule

The DJConnect platform architecture is intentionally frozen with decision
`ARCHITECTURE_FROZEN`.

Until Platform Baseline v1.0 is certified, future engineering should prefer:

- implementation;
- verification;
- qualification;
- documentation;
- evidence;
- coverage;
- operator readiness;
- platform maturity;

over:

- new platform architecture;
- new foundational abstractions;
- new governance layers.

New architectural work requires Architecture Review with objective evidence.
Routine implementation work must not reopen architecture.
Routine findings should be classified as implementation, verification,
documentation, operator configuration or backlog unless objective evidence
shows a genuine architecture gap.

---

# AI-assisted Engineering

Humans determine direction.

AI accelerates execution.

AI should:

- implement;
- document;
- verify;
- report;
- refactor.

Humans remain responsible for:

- product vision;
- architecture;
- acceptance;
- risk;
- release.

---

# Repository Quality

Every engineering phase should improve at least one of:

- implementation;
- documentation;
- verification;
- maintainability;
- reproducibility;
- readability;
- developer experience.

Engineering work should never leave the repository in a less understandable state.

---

# Completion Principle

Every completed engineering phase should answer:

- What changed?
- Why?
- How was it verified?
- What remains?
- What is the next logical step?

The answer to those questions belongs in the repository.

Not in chat history.
