# DJConnect Platform Backlog

This is the canonical high-level platform backlog for DJConnect.

It is not a sprint board and not a replacement for GitHub issues. It defines the main epics and their intended order.

## Status legend

- ✅ Done
- 🟡 In progress
- ⏳ Not started
- 🔵 Research
- ⛔ Blocked

## Epic 1 — Platform Foundation

**Status:** 🟡 In progress  
**Goal:** Establish the canonical product, design, architecture, language and governance foundation.

Deliverables:

- ✅ `DJCONNECT_CONSTITUTION.md`
- ✅ `PRODUCT_VISION.md`
- ✅ `DESIGN_PRINCIPLES.md`
- ✅ `ARCHITECTURE_PRINCIPLES.md`
- ✅ `INNOVATION_LAB.md`
- ✅ `DOMAIN_MODEL.md`
- ✅ `PRODUCT_LANGUAGE.md`
- ✅ `CLIENT_CAPABILITY_MATRIX.md`
- ✅ `PLATFORM_GOVERNANCE.md`
- ✅ `PLATFORM_BACKLOG.md`
- ⏳ `PLATFORM_QUALITY_STANDARD.md`
- ⏳ `ADR_INDEX.md`
- ⏳ Cross-repo AGENTS / sync alignment

Exit criteria:

- all foundation documents exist;
- sibling repos point to canonical foundation;
- no duplicate product roadmap/sync prompt truth exists outside the HA repo;
- Epic 2 can start with a clear review standard.

## Epic 2 — Platform Discovery

**Status:** ⏳ Not started  
**Goal:** Audit every repository for product, architecture, CI/CD, security, privacy, release and documentation quality.

Repositories:

- `pcvantol/djconnect`
- `pcvantol/djconnect-api`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-esp32`
- `pcvantol/djconnect-firmware`
- `pcvantol/djconnect-website`
- `pcvantol/djconnect-app-releases`
- `pcvantol/djconnect-pi-releases`

Deliverables:

- Platform Discovery Report;
- Repository Scorecards;
- Technical Debt Register;
- Product Debt Register;
- CI/CD Review;
- Security/Privacy Review;
- Release Process Review.

## Epic 3 — Profile Architecture

**Status:** ⏳ Not started  
**Goal:** Implement Profile as the primary identity between devices and music backends.

Scope:

- profile storage;
- device -> profile mapping;
- profile resolver;
- backend/account resolver;
- Ask DJ history per profile;
- privacy controls;
- profile export/import;
- config/options flow;
- tests.

## Epic 4 — Intelligence Engine / Insight Feed

**Status:** ⏳ Not started  
**Goal:** Consolidate Track Insight, Lyrics Explain, Artist/Album Insight, Discover and VibeCast around a shared backend-owned intelligence/feed model.

Scope:

- Insight Provider model;
- Insight Feed contract;
- VibeCast hybrid mode;
- Lyrics Explain research;
- Discover contract alignment;
- client renderer updates.

## Epic 5 — Feature Flags and Experimental Framework

**Status:** ⏳ Not started  
**Goal:** Add platform-wide maturity, rollout and experimental toggles.

Scope:

- feature maturity model;
- profile-level experimental settings;
- client capability advertisement;
- developer/preview toggles;
- kill switches;
- release promotion path.

## Epic 6 — Distribution and Release Strategy

**Status:** ⏳ Not started  
**Goal:** Define and harden distribution channels.

Scope:

- HACS release strategy;
- firmware release repository;
- app release repository;
- Pi release repository;
- TestFlight route;
- App Store route;
- Microsoft Store route;
- release notes and communication;
- privacy/store metadata;
- beta community.

## Epic 7 — Platform Quality Standard

**Status:** ⏳ Not started  
**Goal:** Establish consistent quality expectations for every repository.

Scope:

- linting;
- formatting;
- unit tests;
- contract tests;
- CI;
- CodeQL/dependency scanning;
- secret scanning;
- release artifact validation;
- localization checks;
- accessibility where applicable;
- privacy regression checks.

## Epic 8 — Website and Product Story

**Status:** ⏳ Not started  
**Goal:** Make the public website explain the product vision clearly.

Scope:

- AI DJ positioning;
- Community vs Personal;
- onboarding;
- compatibility;
- privacy;
- screenshots/videos;
- download/release flows;
- future cloud kept appropriately future-facing.

## Epic 9 — Future Clients

**Status:** 🔵 Research  
**Goal:** Prepare for Android, web, VR/MR and other clients without fragmenting the platform.

Scope:

- Android client planning;
- Web client planning;
- VR/MR Innovation Lab research;
- client capability contracts;
- distribution implications.

## Epic 10 — Future Cloud and Personal

**Status:** 🔵 Research  
**Goal:** Define how optional cloud capabilities support Personal without replacing local-first Community.

Scope:

- entitlement layer;
- premium DJ voices;
- DJ personas;
- cloud sync;
- profile portability;
- hosted AI;
- privacy/compliance model.
