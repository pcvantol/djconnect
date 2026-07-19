# Innovation Engineering

**Status:** Canonical Engineering Guidance

**Scope:** Entire DJConnect platform

## Purpose

Innovation Engineering is the learning-oriented lane of the DJConnect
Engineering Method. It makes rapid experiments, technical spikes,
proofs-of-concept and prototypes first-class engineering work without turning
them into ungoverned production delivery.

It is not an exception to the Engineering Method. It is a lighter mode within
it: learning speed is the optimization target while repository integrity,
architectural ownership and safe operation remain mandatory.

Innovation Engineering works in the canonical repositories. It must not create
shadow repositories or separate prototype repositories.

## Engineering modes

The Engineering Method has three official modes. Modes describe how work is
performed; Generation 2 programs describe which portfolio owns the initiative.
They are complementary, not interchangeable.

| Mode | Purpose | Governance level | Expected output |
| --- | --- | --- | --- |
| Platform Engineering | Establish or evolve platform capabilities and shared engineering foundations. | Full; architecture, ownership and frozen-baseline controls apply. | A governed platform capability with durable documentation and verification evidence. |
| Product Engineering | Deliver validated user-facing product value. | Full normal product lifecycle. | A production-ready, verified product increment. |
| Innovation Engineering | Learn quickly through bounded experiments, spikes and prototypes not yet promoted to product delivery. | Lightweight, with non-negotiable repository and safety controls. | An experiment plus an Innovation Review decision. |

Platform Engineering remains subject to the frozen Generation 1 baseline and
requires Architecture Review where that baseline would change. Product
Engineering begins only after normal product ownership and planning are in
place. Innovation Engineering does not create a fourth Generation 2 program:
it is the execution mode used by Innovation Lab work.

## Required boundaries

Innovation Engineering must:

- maximize iteration and learning speed;
- retain experiments inside their canonical owning repositories;
- use an isolated innovation branch;
- preserve architectural ownership and existing repository protections;
- leave a clear path to Product Engineering; and
- conclude with an evidence-based Innovation Review.

It must never:

- bypass ownership, security, privacy or secret-handling rules;
- make destructive migrations;
- expose secrets;
- silently change production manifests or represent an experiment as a
  platform release;
- use a shadow repository; or
- treat prototype code as a promoted product capability without a promotion
  decision.

## Branch and deployment model

Innovation work uses a dedicated branch named with one of these prefixes:

```text
innovation/*
prototype/*
experiment/*
```

The default prefix is `innovation/`. Feature branch naming remains reserved for
Product Engineering after promotion. An innovation branch may contain several
rapid iterations, but its scope must remain one bounded learning objective.

Deployment is target-scoped and requires an explicit request for each target.
For example, an experiment may be deployed to one Raspberry Pi, Home
Assistant instance, API environment, Apple client or Windows client. Such a
deployment is experimental evidence only: it must not update production
manifests, create release artifacts or imply release approval.

## Lightweight governance profile

Innovation Engineering allows rapid implementation, exploratory architecture,
temporary code, local experimentation and repeated implementation/deployment
cycles on explicitly selected targets.

It does not require backlog registration, roadmap changes, release planning,
release orchestration, qualification evidence or version increments solely for
the experiment.

Every iteration still requires a successful build, basic smoke validation,
repository integrity, no secret exposure and no destructive migration. The
normal development-machine, synchronization and branch-hygiene requirements
continue to apply to tracked repository changes.

## Lifecycle

```text
Idea
  -> Innovation branch
  -> Rapid iteration
  -> Innovation Review
  -> Abandon | Archive | Continue | Promote
```

The Innovation Review records the objective, what was tested, the evidence,
known risks, the requested deployment targets (if any) and one outcome:

- **Abandon:** stop the experiment and remove or revert temporary work when
  appropriate; retain a concise decision record when it avoids rediscovery.
- **Archive:** preserve a useful experiment and its learning record without
  further active work.
- **Continue:** retain the innovation branch for another explicitly bounded
  learning cycle.
- **Promote:** hand the proven experiment to the Product Engineering lifecycle.

Only **Promote** changes the execution mode. Promotion does not require a
rewrite: successful innovation code may be reused after it receives normal
planning, ownership, verification and governance.

```text
innovation/music-dna-v2
  -> feature/music-dna-engine
  -> Product Engineering lifecycle
  -> verification and qualification
  -> merge
```

## AI operating model

When an explicit prompt selects Innovation Engineering, AI agents must:

1. create or use an `innovation/` branch by default;
2. state the bounded learning objective and repository ownership;
3. avoid unnecessary roadmap, backlog, release, qualification and versioning
   work;
4. deploy only the explicitly requested targets;
5. iterate quickly while retaining build and smoke evidence; and
6. finish with an Innovation Review that selects Abandon, Archive, Continue or
   Promote.

AI agents must return to the normal Product Engineering operating model when
the Innovation Review outcome is Promote. They may not infer promotion from a
successful prototype.
