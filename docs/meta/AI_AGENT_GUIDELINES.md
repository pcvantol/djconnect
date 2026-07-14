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

Every clean AI session begins by synchronizing `main` with `git switch main`
and `git pull --ff-only`, then verifying branch, `HEAD`, upstream,
fast-forward status and cleanliness. Stop if either synchronization or
verification fails. Only then read:

1. `BOOTSTRAP.md`
2. `ENGINEERING_STATUS.md`, repository status, management summary and roadmap
3. current active roadmap and backlog
4. `PROMPT_INDEX.md` and Prompt History only when needed
5. repository-local instructions, foundation and Meta Engineering guidance

Do not plan before this read and the implementation-reality check. Never start
implementation without repository context.

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
Prompt

↓

Dedicated Branch

↓

Focused Implementation

↓

Validation

↓

Documentation, Repository Status, Management Summary and Prompt Index Updates

↓

Commit(s)

↓

Exactly One Reviewable Pull Request

↓

Stop
```

Treat one canonical prompt as one engineering increment and deliver it through
one independently reviewable pull request. Work on a dedicated branch; merge
is a separate explicit decision. Do not begin a subsequent canonical prompt
until the preceding increment has its reviewable pull request.

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

Every engineering increment must produce exactly one small, focused and
reviewable pull request with one coherent objective. Do not combine unrelated
work or create competing prompt scopes.

One architectural concern per pull request whenever practical.

---

# Prompt Usage

Prompts are execution instructions.

They are not architecture.

They should become smaller over time.

Repository knowledge should become larger.

The long-term goal is minimal prompts.

Prompt lifecycle and ownership are canonical in `PROMPT_INDEX.md`: `Draft`,
`Active`, `Completed`, `Deprecated` and `Archived`. Only one prompt may be
`Active` during execution. Changing this Engineering Method requires a
dedicated Engineering Governance prompt, never an implementation prompt.

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

Update Repository Status, Management Summary and Prompt Index; commit the
increment and open exactly one reviewable pull request. Then stop.

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
