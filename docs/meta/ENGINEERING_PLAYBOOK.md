# Engineering Playbook

**Status:** Canonical Engineering Guidance

**Audience:** Engineers, architects, reviewers and AI agents

**Scope:** Entire DJConnect platform

---

# Purpose

This playbook describes how engineering work is performed within the DJConnect platform.

It defines the preferred engineering workflow from idea to production.

The objective is consistency.

Every feature, refactor, architectural change and verification activity should follow the same engineering lifecycle.

---

# Core Principle

> Engineering is a sequence of small, verifiable improvements.

Large, risky, difficult-to-review changes are intentionally avoided.

Every completed phase should leave the platform in a better state than before.

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
- platform maturity;
- business value that fits within the frozen architecture;

over:

- new platform architecture;
- new foundational abstractions;
- new governance layers.

New architectural work requires Architecture Review with objective evidence.
Routine implementation work must not reopen architecture.

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
