# AI Collaboration Model

**Status:** Canonical Engineering Guidance
**Audience:** Humans, AI agents, reviewers and maintainers
**Scope:** Entire DJConnect platform

---

# Purpose

This document defines how humans and AI collaborate while engineering the DJConnect platform.

It is **not** a product document.

It is **not** an architecture document.

It defines the engineering model used to build, evolve and verify the platform.

This document exists because conversations are temporary.

The repository is permanent.

---

# Core Principle

> **The repository is the memory.**

Chats are used to discover ideas.

Repositories preserve decisions.

Every architectural decision that is expected to survive a conversation must become repository knowledge.

No implementation should depend on remembering previous conversations.

---

# Engineering Roles

## Human

The human remains accountable.

Responsibilities include:

- Product Vision
- Business priorities
- User value
- Architecture approval
- Risk acceptance
- Security acceptance
- Release approval
- Trade-off decisions
- Final ownership

These responsibilities are never delegated.

---

## ChatGPT

Role:

**Chief Architect**

Primary responsibilities:

- Architecture
- Product design
- Design reviews
- Trade-off analysis
- Roadmaps
- System thinking
- Meta-engineering
- Quality reviews
- Technical strategy

ChatGPT should optimise the platform.

Not individual pull requests.

---

## Codex

Role:

**Engineering Lead**

Primary responsibilities:

- Implementation
- Refactoring
- Documentation
- Testing
- Verification
- Pull Requests
- Completion Reports
- Prompt generation
- Repository maintenance

Codex executes.

It does not own product strategy.

---

## Repository

The repository is the permanent memory of the engineering system.

Everything important eventually belongs inside the repository.

Examples:

- Architecture
- Decisions
- Verification
- Standards
- Technical Design
- Lessons Learned
- Engineering workflow

Never rely on chat history as the canonical source.

---

# Repository First

When new knowledge appears:

Discovery

↓

Discussion

↓

Decision

↓

Repository

↓

Implementation

Not:

Discussion

↓

Implementation

↓

Hope somebody remembers later.

---

# Decision Flow

The engineering workflow is intentionally simple.

```
Discovery

↓

Architecture Discussion

↓

Decision

↓

Repository Update

↓

Implementation

↓

Verification

↓

Review

↓

Merge
```

Every important decision should become durable repository knowledge before broad implementation begins.

---

# Knowledge Flow

Knowledge progresses through the following stages.

## Temporary

Ideas

Questions

Brainstorming

Trade-offs

Chats

Temporary notes

---

## Accepted

Architectural decisions

Platform principles

Verification rules

Standards

Playbooks

Engineering guidance

These belong in Git.

---

# Engineering Principles

The following principles guide every engineering activity.

## Repository > Prompt

Large prompts are temporary.

Repository documentation is durable.

The long-term goal is to reduce prompts over time.

---

## Evidence > Opinion

Claims should be supported by:

- implementation;
- tests;
- runtime evidence;
- logs;
- measurements;
- documentation.

Architectural preference alone is insufficient.

---

## Architecture Before Implementation

Broad implementation begins only after:

- architectural direction;
- ownership;
- contracts;
- quality expectations

are sufficiently understood.

---

## Small, Reviewable Changes

Prefer:

- small pull requests;
- small phases;
- clear completion reports;
- deterministic reviews.

Avoid long-lived mega branches.

---

## Verification Before Trust

Passing compilation is not sufficient.

Behaviour should be demonstrated.

Evidence should be collected.

Verification should be repeatable.

---

## Scenario Driven Development

Behaviour originates from scenarios.

Implementation grows to satisfy scenarios.

Not the other way around.

---

## Thin Adapters

Adapters execute platform operations.

They do not interpret behaviour.

Business logic belongs elsewhere.

---

## Execution Environment Owns Tooling

Tooling belongs to the Verification Execution Environment.

Examples:

- Docker
- Xcode
- GitHub
- SSH
- Serial
- Build qualification
- Cleanup
- Environment preparation

Adapters must not duplicate this responsibility.

---

# AI Working Agreement

Every Codex session should begin by reading:

- AGENTS.md
- BOOTSTRAP_CODEX_SESSION.md
- BOOTSTRAP_CODEX_VERIFICATION.md (when applicable)
- the active phase from PROMPT_INDEX.md

The repository should provide enough context that large prompts become unnecessary.

---

# Completion Workflow

Every completed phase should leave the repository in a better state.

Expected outputs include:

- implementation;
- documentation;
- verification;
- completion report;
- lessons learned;
- updated roadmap;
- next phase prompt.

Knowledge accumulation is intentional.

---

# Anti-patterns

Avoid:

## Chat Memory

Do not assume future engineers or AI agents know previous conversations.

---

## Giant Prompts

Large prompts are useful temporarily.

Long-term knowledge belongs in the repository.

---

## Hidden Decisions

Important architectural decisions should never exist only inside someone's head.

---

## Verification by Hope

A feature is not considered correct because it appears to work.

Verification requires evidence.

---

## Architecture Drift

Implementation should not silently redefine architecture.

Architectural change requires explicit review.

---

## AI Without Accountability

AI may implement.

Humans remain accountable.

---

# Continuous Improvement

This document is intentionally living guidance.

It should change only when engineering practice genuinely improves.

Routine implementation work should not require modifications.

Major architectural or workflow lessons should.

---

# Closing Principle

The objective is not merely to build software.

The objective is to build a software platform that becomes progressively easier to understand, verify, maintain and evolve.

Every engineering phase should leave the repository:

- more explicit;
- more reproducible;
- more verifiable;
- more understandable;

than it was before.

The repository is the engineering memory.

AI accelerates engineering.

Humans remain responsible for direction and acceptance.
