# DJConnect Implementation Framework

This directory defines the standard implementation structure for future DJConnect epics.

The framework is part of the DJConnect Platform Foundation. It exists so Epic 3 and later work can start from a repeatable architecture-first process instead of inventing a new workflow every time.

## Overview

Implementation epics turn foundation, discovery and ADR decisions into working software. They must keep DJConnect coherent across repositories, preserve the Profile / Device / Music Backend / Renderer ownership model and avoid letting code become the product specification.

Large architectural work should always be split into phases. Each phase must compile independently, pass its expected tests and remain mergeable on its own.

## Implementation lifecycle

```text
Epic
  -> Context
  -> Phase 1
  -> Review
  -> Phase 2
  -> Review
  -> ...
  -> Completion
  -> Merge
  -> Update Foundation
```

## Epic

An Epic is a coherent platform change with clear product and architecture intent. It may affect one repository or several repositories, but it must start from the canonical foundation in `pcvantol/djconnect`.

Each Epic should define:

- mission;
- owner repository or repositories;
- relevant foundation documents;
- relevant discovery reports;
- expected phases;
- breaking-change stance;
- out-of-scope work;
- definition of success.

## Context

The Context prompt establishes the architecture boundary before implementation begins. It should be created from `epic-template/00-context.md`.

The Context must describe what the Epic is trying to change, what it must not change and which foundation rules are authoritative.

## Phases

Each phase is a small implementation unit. A phase may include runtime code, docs, tests, migrations and contract changes, but it must be independently reviewable and mergeable.

Use `epic-template/01-phase-template.md` for every phase.

## Review

After each phase, run an architecture review using `epic-template/02-review-template.md`.

The review decides whether:

- the phase followed the Constitution and Domain Model;
- responsibilities moved to the correct owner;
- duplicate contracts or business logic were introduced;
- docs and tests are sufficient;
- an ADR is needed;
- the next phase can begin.

## Completion

Close the Epic with `epic-template/03-completion-template.md`.

The completion report should summarize architecture changes, documents changed, repositories changed, runtime impact, breaking changes, migrations, tests, known follow-up work, backlog updates, Innovation Lab updates and foundation updates.

## Merge rules

- Prefer many small PRs over one large PR.
- Every PR must compile independently.
- Every PR must remain mergeable.
- Runtime changes must stay within the phase scope.
- Documentation must move with implementation.
- Cross-repository changes must be sequenced so each repo remains understandable at every step.

## Update Foundation

If implementation reveals that a foundation principle is wrong, incomplete or ambiguous, update the relevant foundation document or propose an ADR. Do not let runtime code silently redefine platform truth.
