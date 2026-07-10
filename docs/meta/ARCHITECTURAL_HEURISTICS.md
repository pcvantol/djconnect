# Architectural Heuristics

**Status:** Canonical Engineering Guidance

**Audience:** Architects, engineers and AI agents

**Scope:** Entire DJConnect platform

---

# Purpose

Architecture is rarely about finding a single objectively correct answer.

Instead, architecture is a continuous process of making good decisions with incomplete information.

This document captures the engineering heuristics that guide architectural decisions within the DJConnect platform.

These are not hard rules.

They are decision-making principles.

---

# What is a Heuristic?

A heuristic is a practical rule that improves decision quality.

Unlike requirements or architecture principles:

- heuristics are not mandatory;
- heuristics may have exceptions;
- heuristics help resolve uncertainty.

Every heuristic should improve long-term platform quality.

---

# Repository Before Conversation

If knowledge is expected to survive this engineering session, it belongs in the repository.

Chats are for exploration.

Repositories are for preservation.

---

# Explicit Before Implicit

Architecture should become progressively more explicit.

Avoid:

- hidden assumptions;
- undocumented ownership;
- implicit contracts;
- tribal knowledge.

Prefer:

- documented ownership;
- documented responsibilities;
- documented contracts;
- documented boundaries.

---

# Understand Before Improving

Never redesign a system before understanding it.

For legacy systems:

Current State

↓

Technical Design Reconstruction

↓

Gap Analysis

↓

Target Architecture

Not:

Current State

↓

Rewrite

---

# Architecture Before Scale

Small experiments may begin quickly.

Platform-wide implementation should begin only after architectural direction has become sufficiently stable.

Large implementation without architectural alignment usually creates technical debt.

---

# One Responsibility

Every subsystem should have a single primary responsibility.

Examples:

Verification Core

↓

Verification behaviour

Execution Environment

↓

Tooling

Platform Adapter

↓

Platform execution

Scenario Engine

↓

Expected behaviour

Planning Engine

↓

Execution planning

When a subsystem starts accumulating unrelated responsibilities, reconsider the design.

---

# Prefer Composition

Avoid creating large components that own many responsibilities.

Instead:

Compose smaller responsibilities.

This generally improves:

- maintainability;
- verification;
- reuse;
- understanding.

---

# Grow From Real Use

Avoid speculative architecture.

Prefer:

Scenario

↓

Implementation

↓

Generalisation

Not:

Generalisation

↓

Hope somebody needs it.

Reusable abstractions should emerge from repeated use.

---

# Thin Boundaries

Adapters should remain thin.

Execution should remain separate from decision making.

Presentation should remain separate from domain behaviour.

Infrastructure should remain separate from product behaviour.

---

# Evidence Before Change

When implementation appears incorrect:

Collect evidence first.

Examples:

Tests

Logs

Runtime behaviour

Technical Design

Verification reports

Avoid modifying implementation based only on intuition.

---

# Small Changes

Prefer many small changes over one large change.

Smaller changes:

- review more easily;
- verify more easily;
- revert more easily;
- understand more easily.

---

# Durable Knowledge

If a decision is important enough to explain repeatedly, it deserves documentation.

Do not repeatedly rely on conversation history.

---

# Prefer Stable Interfaces

Internal implementation may evolve.

Interfaces should evolve more carefully.

Stable interfaces reduce coupling.

---

# Avoid Duplicate Truth

Every important concept should have one canonical source.

Examples:

Platform terminology

↓

Foundation

Verification Scenarios

↓

Scenario Catalog

Technical implementation

↓

Technical Design

Do not maintain competing definitions.

---

# Prefer Repository Context

The repository should provide enough context that AI agents require only minimal prompts.

Large prompts indicate missing repository knowledge.

Improve the repository instead of growing prompts indefinitely.

---

# Human Decisions

Certain decisions remain human responsibilities.

Examples:

Product direction

Architecture approval

Security acceptance

Privacy acceptance

Release approval

AI may recommend.

Humans decide.

---

# Refactor Towards Simplicity

Complexity should decrease over time.

When two solutions are functionally equivalent:

Prefer the simpler one.

Provided that:

- readability;
- maintainability;
- verification;
- extensibility

do not suffer.

---

# Architecture Evolves

Architecture is never finished.

However:

Core architectural concepts should change rarely.

Implementation should evolve more frequently.

This creates stability.

---

# Heuristic Review

Every major architectural discussion should ask:

Does this improve:

- understanding?
- ownership?
- verification?
- maintainability?
- reproducibility?
- repository quality?

If not, reconsider the change.

---

# Closing Principle

Architecture exists to make future engineering easier.

Good architecture reduces the number of difficult decisions future engineers need to make.

The best architectural decision is often the one that future engineers no longer have to think about.
