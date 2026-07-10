# Repository as Memory

**Status:** Canonical Engineering Guidance

**Audience:** Architects, engineers and AI agents

**Scope:** Entire DJConnect platform

---

# Purpose

This document explains one of the most important engineering principles adopted by the DJConnect platform:

> The repository is the permanent engineering memory.

This principle fundamentally changes how humans and AI collaborate.

Instead of relying on conversations, prompts or personal memory, the repository itself becomes the primary source of engineering knowledge.

---

# Problem Statement

Large engineering projects accumulate knowledge continuously.

Historically that knowledge often exists in:

- conversations;
- chat history;
- email;
- issue discussions;
- individual engineers;
- undocumented assumptions.

This creates several problems.

Knowledge disappears.

New engineers require lengthy onboarding.

AI agents require increasingly large prompts.

Important architectural decisions become difficult to reconstruct.

---

# Repository as Memory

DJConnect adopts a different approach.

Important knowledge should migrate through the following stages.

```
Discovery

↓

Discussion

↓

Accepted Decision

↓

Repository

↓

Implementation

↓

Verification

↓

Maintenance
```

Only temporary exploration should remain outside the repository.

Everything else should become durable repository knowledge.

---

# Repository Before Prompt

Large prompts are useful during exploration.

They should not become permanent engineering assets.

Instead:

Prompt

↓

Repository Documentation

↓

Small Prompt

↓

Implementation

The repository should gradually replace prompt context.

---

# AI Context

Every new AI session should begin by reading repository documentation.

Not previous conversations.

The repository should contain enough context that AI agents can become productive with minimal additional prompting.

Examples:

- AGENTS.md
- BOOTSTRAP documents
- Foundation
- Technical Design
- Verification
- Meta Engineering

---

# Living Knowledge

The repository should continuously become more complete.

Every completed engineering phase should ask:

What knowledge should future engineers not have to rediscover?

The answer belongs in the repository.

---

# Durable Knowledge

Examples of durable knowledge include:

Architecture

Verification

Technical Design

Engineering workflow

Lessons learned

Coding conventions

Ownership

Platform principles

AI collaboration

These should never exist only in chat history.

---

# Temporary Knowledge

Not everything belongs in Git.

Examples:

Brainstorming

Experiments

Rejected ideas

Early design sketches

These may remain temporary until accepted.

---

# Repository Evolution

Repository quality should improve continuously.

Each phase should ideally contribute at least one of:

- implementation;
- documentation;
- verification;
- navigation;
- traceability;
- engineering guidance.

The repository should become easier to understand over time.

---

# AI-Native Engineering

The long-term objective is an AI-native repository.

Characteristics include:

Minimal onboarding prompts.

Self-describing architecture.

Traceable decisions.

Canonical ownership.

Verification-first engineering.

Repository-driven implementation.

Small reproducible prompts.

---

# Engineering Workflow

The preferred workflow is:

```
Discussion

↓

Decision

↓

Repository

↓

Implementation

↓

Verification

↓

Review

↓

Merge
```

Not:

```
Discussion

↓

Implementation

↓

Hope someone remembers later
```

---

# Anti-patterns

Avoid:

Repository knowledge hidden in chats.

Prompt-only architecture.

Undocumented architectural decisions.

Repeated explanations.

Large prompts replacing documentation.

Multiple competing sources of truth.

---

# Success Criteria

The repository should eventually contain sufficient engineering knowledge that:

- new engineers require minimal onboarding;
- AI agents require only small bootstrap prompts;
- architectural intent is explicit;
- verification is reproducible;
- important decisions are traceable.

At that point the repository itself becomes the primary engineering memory.

---

# Closing Principle

People remember.

Chats expire.

Repositories persist.

The objective is therefore simple:

Every important engineering insight should eventually become repository knowledge.
