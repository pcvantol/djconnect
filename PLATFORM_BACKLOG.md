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

**Status:** ✅ Done  
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
- ✅ `PLATFORM_QUALITY_STANDARD.md`
- ✅ `ADR_INDEX.md`
- ✅ Cross-repo AGENTS / sync alignment
- ✅ `FOUNDATION_INDEX.md`
- ✅ `DESIGN_FOUNDATION_VERSION.md`
- ✅ `PLATFORM_PRINCIPLES.md`
- ✅ `REPOSITORY_OWNERSHIP.md`
- ✅ `EPIC_1_COMPLETION_REPORT.md`

Exit criteria:

- all foundation documents exist;
- sibling repos point to canonical foundation;
- no duplicate product roadmap/sync prompt truth exists outside the HA repo;
- Epic 2 can start with a clear review standard.

## Epic 2 — Platform Discovery & Repository Audit

**Status:** ✅ Done  
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

- ✅ `PLATFORM_DISCOVERY_REPORT.md`
- ✅ Repository Discovery Reports under `docs/discovery/`
- ✅ Repository Scorecards
- ✅ Technical Debt Register
- ✅ Product Debt Register
- ✅ CI/CD Review
- ✅ Security/Privacy Review
- ✅ Release Process Review
- ✅ `docs/discovery/BACKLOG_RECOMMENDATIONS.md`
- ✅ `docs/discovery/INNOVATION_RECOMMENDATIONS.md`

Discovery policy:

- do not implement runtime features during Epic 2;
- do not perform large refactors during Epic 2;
- only make documentation, report, backlog, issue and ADR-proposal changes;
- runtime changes are allowed only for a discovered critical bug and should be reviewed explicitly before implementation.

## Epic 2A — Foundation Sync Across Repositories

**Status:** ⏳ Not started  
**Goal:** Ensure every DJConnect repository points to the canonical foundation without copying or redefining it.

Scope:

- add or refresh `AGENTS.md` in every repository;
- remove or replace repo-local cross-repo `SYNC_PROMPTS.md` files with canonical pointers;
- align release repositories with `REPOSITORY_OWNERSHIP.md`;
- keep repo-specific implementation guidance intact;
- avoid local copies of canonical foundation documents.

## Epic 2B — Contract Fixture Compatibility Suite

**Status:** ⏳ Not started  
**Goal:** Turn existing HA client contract fixtures into an explicit cross-client compatibility suite.

Scope:

- versioned fixture manifest;
- Apple, Windows and Pi conformance status;
- HTTP and websocket fixture families;
- privacy/redaction fixture checks;
- release-note and CI visibility for fixture compatibility.

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
**Goal:** Add platform-wide maturity, rollout, experimental toggles and client capability governance.

Scope:

- feature maturity model;
- profile-level experimental settings;
- client capability advertisement;
- required/optional/forbidden capability matrix by client class;
- Apple/Windows/Pi/ESP parity tracking;
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
- beta community;
- public release repository README/license hygiene;
- artifact checksum/manifest validation for release-only repositories.

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
- future cloud kept appropriately future-facing;
- product-language linting for public docs and release-note templates.

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
