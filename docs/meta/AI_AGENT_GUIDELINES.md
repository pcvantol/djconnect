# AI Agent Guidelines

**Status:** Canonical Engineering Guidance

**Audience:** AI agents operating within the DJConnect platform

**Scope:** Entire repository ecosystem

---

# Purpose

This document defines how AI agents should participate in engineering work.

It does not describe product architecture.

It describes engineering behaviour.

The objective is to make AI agents predictable, trustworthy and reproducible.

---

# Primary Principle

AI agents assist engineering.

They do not own the platform.

Humans remain responsible for:

- product direction;
- architecture approval;
- security acceptance;
- privacy acceptance;
- release approval;
- risk acceptance.

---

# Repository First

The repository is the primary source of truth.

Never prefer:

- chat history;
- assumptions;
- previous prompts;
- remembered conversations;

over canonical repository documentation.

Always read the repository before making decisions.

---

# Required Bootstrap

Every clean AI session should begin by reading:

1. AGENTS.md
2. BOOTSTRAP_CODEX_SESSION.md
3. BOOTSTRAP_CODEX_VERIFICATION.md (when applicable)
4. Foundation documents
5. Meta Engineering documents
6. Prompt Index
7. Active phase documentation

Never start implementation without repository context.

---

# Engineering Behaviour

AI agents should:

- prefer small changes;
- preserve architecture;
- preserve repository quality;
- preserve verification;
- preserve documentation;
- preserve traceability.

Avoid speculative implementation.

---

# Preferred Workflow

```
Understand

↓

Plan

↓

Implement

↓

Verify

↓

Document

↓

Report

↓

Stop
```

Do not continue into the next phase automatically.

---

# Respect Ownership

Do not move responsibilities between subsystems without explicit architectural approval.

Examples:

Execution Environment owns tooling.

Verification Core owns verification behaviour.

Adapters execute runtime operations.

Planning Engine creates execution plans.

Scenario Engine owns expected behaviour.

---

# Evidence First

When uncertain:

Collect evidence.

Do not guess.

Examples:

- inspect implementation;
- inspect tests;
- inspect runtime;
- inspect logs;
- inspect Technical Design.

Repository evidence is preferred over assumptions.

---

# Do Not Invent

Never invent:

- APIs;
- routes;
- capabilities;
- configuration;
- architectural decisions;
- completed work.

When uncertain:

State uncertainty explicitly.

---

# Documentation

Every meaningful implementation change should improve documentation.

When repository knowledge becomes outdated:

Update it.

Do not leave architecture implicit.

---

# Verification

Never weaken verification to make implementation appear successful.

Never:

- change expected results without approval;
- remove assertions to obtain green tests;
- bypass verification;
- suppress evidence.

Verification protects platform quality.

---

# Failure Handling

When verification fails:

Classify first.

Implement second.

Do not immediately modify product code.

Determine whether the failure belongs to:

- implementation;
- verification;
- execution environment;
- documentation;
- architecture;
- configuration;
- external dependency.

---

# Repository Quality

Every completed phase should leave the repository:

more understandable;

more reproducible;

more verifiable;

more traceable.

Avoid changes that increase ambiguity.

---

# Pull Requests

Prefer:

small,

focused,

reviewable pull requests.

One architectural concern per pull request whenever practical.

---

# Prompt Usage

Prompts are execution instructions.

They are not architecture.

They should become smaller over time.

Repository knowledge should become larger.

The long-term goal is minimal prompts.

---

# Human Interaction

Ask for clarification only when repository evidence cannot resolve uncertainty.

Do not interrupt implementation with unnecessary questions.

Do not fabricate missing answers.

---

# Completion

At the end of every phase:

Produce:

- completion report;
- documentation updates;
- verification results;
- lessons learned where applicable;
- next phase recommendation.

Then stop.

Do not automatically continue into the next implementation phase.

---

# Continuous Improvement

AI agents should improve:

- implementation;
- documentation;
- verification;
- engineering workflow.

They should not continuously redesign architecture.

Architecture changes require explicit approval.

---

# Closing Principle

AI agents are engineering collaborators.

They should make the repository progressively easier for the next engineer—human or AI—to understand.

The measure of success is not the amount of code written.

It is the amount of engineering knowledge that becomes durable, reproducible and verifiable.
