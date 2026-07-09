# DJConnect Platform Governance

This document describes how DJConnect product ideas become architecture, implementation and releases.

It exists to prevent feature creep, duplicated client logic and fragmented product direction across repositories.

## Source of truth order

When documents conflict, use this order:

1. `DJCONNECT_CONSTITUTION.md`
2. `PRODUCT_VISION.md`
3. `DESIGN_PRINCIPLES.md`
4. `ARCHITECTURE_PRINCIPLES.md`
5. `DOMAIN_MODEL.md`
6. `CLIENT_CAPABILITY_MATRIX.md`
7. `PRODUCT_LANGUAGE.md`
8. `PRODUCT_ROADMAP.md`
9. `INNOVATION_LAB.md`
10. Repository-local implementation docs

## Feature lifecycle

```text
Idea
  -> Innovation Lab
  -> Product review
  -> Architecture review
  -> Roadmap
  -> Design / contract
  -> Codex prompt or implementation task
  -> Pull request
  -> Tests / review
  -> Release
  -> Roadmap and docs update
```

## Idea intake

New ideas should first be captured in `INNOVATION_LAB.md` unless they are already committed roadmap work.

Each idea should include:

- name;
- status;
- domain;
- user value;
- architecture fit;
- dependencies;
- open questions;
- anti-goals or constraints.

Innovation Lab is not a promise. It is a safe place to keep ideas without overcommitting.

## Product review

Before a feature is promoted to roadmap, ask:

1. Does it enrich listening?
2. Does it fit the Product Vision?
3. Is it Community, Personal or future Cloud?
4. Can it be explained simply on the website?
5. Does it make DJConnect feel more coherent rather than more complex?

## Architecture review

Before implementation, ask:

1. Which domain object owns this?
2. Is personal state attached to Profile?
3. Is hardware/runtime state attached to Device?
4. Is provider-specific behavior behind Music Backend?
5. Is durable intelligence backend-owned?
6. Does it publish through Insight Feed if it is insight-like?
7. Which clients can render it?
8. Does it need a feature flag?
9. What is the privacy model?
10. What is the graceful fallback?

## Roadmap promotion

Move an item from Innovation Lab to Roadmap only when:

- user value is clear;
- architecture fit is clear;
- owner repository is known;
- required contracts are identified;
- minimum acceptance criteria exist;
- privacy/security implications are understood.

## Implementation rules

- Prefer small PRs.
- Split large features by architecture layer.
- Update canonical docs before cross-repo changes.
- Do not implement client-local business logic that belongs in the backend.
- Do not create repo-local product roadmaps or sync prompts when canonical files exist.
- Do not ship experimental capabilities as stable by accident.

## Implementation Framework

Every implementation epic should follow the canonical framework in `docs/implementation/`.

Default lifecycle:

```text
Context
  -> Phases
  -> Review
  -> Completion
  -> Foundation update
```

The framework requires:

- an Epic Context before implementation starts;
- small, mergeable implementation phases;
- architecture review after each phase;
- completion reporting before the Epic is closed;
- foundation updates or ADRs when implementation changes platform truth.

Large architectural work should not be implemented as one broad PR. Each phase must compile independently, pass its expected tests and remain mergeable.

## Release governance

Every release should consider:

- changelog/release notes;
- website/docs updates;
- compatibility notes;
- privacy/security notes;
- migration notes;
- screenshots or demo assets where relevant;
- release artifact integrity;
- cross-repo contract impacts.

## Distribution governance

Distribution channels are part of the platform:

- HACS;
- GitHub releases;
- firmware release repo;
- app release repo;
- Pi release repo;
- TestFlight;
- future App Store;
- future Microsoft Store;
- future Play Store;
- website downloads/onboarding.

Release communication should describe user value, not just implementation change.

## Feature flags and experimental toggles

Experimental or risky features should have:

- maturity status;
- intended audience;
- default state;
- rollback/kill-switch behavior;
- capability detection;
- privacy review;
- expiry or promotion criteria.

Feature flags should usually be profile-aware when personal and device-aware when hardware-specific.

## AI-agent / Codex governance

AI-generated implementation prompts should start from the design foundation.

A good implementation prompt should include:

- relevant Constitution laws;
- domain ownership;
- affected repositories;
- contracts/endpoints/services;
- acceptance criteria;
- tests;
- privacy/security constraints;
- migration or breaking-change stance.

## Decision logging

Important architecture decisions should be captured as ADRs under `docs/adr/` and listed in `ADR_INDEX.md`.

Decisions that affect product language, tiers, clients or repository responsibilities should also update the relevant foundation docs.
