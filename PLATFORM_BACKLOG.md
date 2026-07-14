# DJConnect Platform Backlog — Generation 1 archive

This document preserves Generation 1 platform-program history and completion
evidence. It is not an active roadmap or backlog.

The canonical active Platform Evolution backlog is
`PLATFORM_EVOLUTION_BACKLOG.md`. Active product work is in
`PRODUCT_ROADMAP.md`; Innovation Lab work is in `INNOVATION_BACKLOG.md`.

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

**Status:** ✅ Complete  
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

## Epic 3B — Client and Voice Endpoint Profile Adoption

**Status:** ✅ Complete  
**Goal:** Extend Profile adoption across clients and Home Assistant voice
request sources without reopening Epic 3 server-side foundation work.

Scope:

- ✅ verify the request-context resolver contract across source types;
- ✅ define reusable Profile Adoption Contract fixtures;
- ✅ expose profile context capability/version discovery;
- add explicit HA Voice satellite mapping support;
- add room/area mapping management;
- add playback player/zone mapping where configured;
- align Apple profile/device context;
- align Windows profile/device context;
- align Raspberry Pi profile/device context;
- verify ESP32 continues resolving through registered `device_id`;
- add cross-client resolver contract tests for DJConnect Device, HA Voice
  satellite, Home Assistant user hint, room/area, playback zone/player, fallback
  and ambiguous contexts.

Privacy requirements:

- shared voice satellites must not expose personal Ask DJ history by default;
- room mapping should normally target shared, household, room, kids or guest
  profiles;
- linking a shared satellite to a personal profile requires explicit
  configuration;
- ambiguous speaker identity must fall back safely rather than guessing a
  personal profile;
- private-session rules still apply after Profile resolution.

Suggested subphases:

1. contract verification;
2. Apple;
3. Windows;
4. Pi;
5. ESP32;
6. HA Voice satellites;
7. cross-client resolver contract tests.

## Verification Program V1

**Status:** ✅ Complete
**Goal:** Build durable platform verification before expanding adapter
coverage.

Completed:

- ✅ Verification Vision;
- ✅ Verification Architecture;
- ✅ Scenario Schema;
- ✅ Scenario Catalog;
- ✅ Verification Matrix;
- ✅ Verification Harness Architecture;
- ✅ Verification Core;
- ✅ Verification Core Refinement;
- ✅ Technical Design Reconstruction;
- ✅ Implementation Gap Analysis;
- ✅ Phase 8 Verification Execution Environment.
- ✅ Phase 8A Verification Data Framework.
- ✅ Phase 8B Verification Modes and Verification Policies.
- ✅ Phase 8C Verification Planning Engine.
- ✅ Phase 9 Home Assistant Verification Adapter.
- ✅ Phase 9L Local Home Assistant Verification Lab Qualification.
- ✅ Phase 9V Verification Platform Qualification Rerun.
- ✅ Home Assistant Qualification.
- ✅ Apple Qualification.
- ✅ Verification Framework Completion.
- ✅ Raspberry Pi Qualification.
- ✅ Windows Qualification.

Next:

- ✅ Phase 9E-R Home Assistant Scenario Coverage Remediation qualified with
  non-blocking warnings.
- ✅ Phase 10 Apple Verification Adapter qualified with live runtime skipped.
- ✅ Phase 10E-R3 Apple Scenario Coverage qualified with non-blocking warnings.
- ✅ Verification Framework Completion stabilized the runtime
  primitives, planner, execution, evidence, investigator, qualification,
  reporting and coverage capabilities.
- ✅ Phase 12E-R Raspberry Pi product scenario mapping qualified.
- ✅ Phase 13 Windows Verification Adapter qualified with live runtime pending.
- ✅ Phase 13E-R2 Windows Client Build Remediation and Live Qualification
  returned `WINDOWS_LIVE_QUALIFIED`.
- ✅ Phase 14E ESP Live Qualification returned `ESP_LIVE_QUALIFIED`.
- ✅ Phase 15E-R DJConnect Voice Assistant Live Qualification Remediation
  returned `VOICE_ASSISTANT_LIVE_QUALIFIED`.
- ✅ Phase 16-R returned `CROSS_PLATFORM_QUALIFIED`.
- ✅ Phase 17 Platform Test Coverage Improvement completed with fresh
  exact-SHA evidence for Home Assistant, Apple, Raspberry Pi and Windows.
- ✅ ESP Native Coverage Follow-up returned `ESP_COVERAGE_QUALIFIED`.

Remaining:

- ✅ Platform Baseline v1.0 certified; Generation 1 complete.
- ✅ Generation 1 Platform Engineering closed and frozen; Software Assurance
  Generation 1 is the next active program.

## Coverage Baseline 1

**Status:** ✅ Established
**Decision:** `CROSS_PLATFORM_COVERAGE_BASELINE_ESTABLISHED`
**Runtime:** Verification Runtime `1.1.0`

Baseline repositories:

- Home Assistant: 16.43% line, 10.19% branch.
- Apple: 9.39% line.
- Raspberry Pi: 75.09% line, 61.99% branch.

Coverage Baseline 1 is immutable historical evidence. Future coverage
improvement must compare against it, not replace it.

Windows is intentionally excluded from Coverage Baseline 1. Its first
validated measurement is recorded separately as Windows Coverage Baseline 1
with decision `WINDOWS_COVERAGE_BASELINE_ESTABLISHED`: 72.45% line coverage and
50.85% branch coverage for `pcvantol/djconnect-windows` commit
`b205f087214eb5fe90c4129c2afa9dee7f836a82`.

## Phase 14 — ESP Verification Adapter

**Status:** ✅ Complete
**Decision:** `ESP_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING`
**Goal:** Implement and qualify the thin ESP verification adapter without
changing the frozen platform architecture.

Objectives:

- implement thin ESP verification adapter;
- adapter registration;
- runtime primitives;
- planner integration;
- Scenario Engine routing;
- capability mapping;
- CLI execution where applicable;
- mock qualification.

## Phase 14E — ESP Live Qualification

**Status:** ✅ Complete
**Decision:** `ESP_LIVE_QUALIFIED`
**Goal:** Qualify the ESP adapter against real ESP hardware.

Objectives:

- qualify against real ESP hardware;
- execute canonical ESP smoke scenarios;
- collect qualification evidence;
- validate planner integration;
- validate adapter behaviour.

## Phase 15 — DJConnect Voice Assistant Verification Adapter

**Status:** ✅ Complete
**Decision:** `VOICE_ASSISTANT_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING`
**Goal:** Treat the DJConnect Voice Assistant Conversation Agent as its own
verification platform, distinct from the ESP adapter.

Objectives:

- verification adapter;
- planner integration;
- conversation routing;
- Scenario Engine integration;
- capability mapping;
- mock qualification.

## Phase 15E — DJConnect Voice Assistant Live Qualification

**Status:** ✅ Complete
**Decision:** `VOICE_ASSISTANT_LIVE_QUALIFIED`
**Goal:** Qualify the Voice Assistant adapter against the real Conversation
Agent.

Objectives:

- qualify against the real Conversation Agent;
- execute canonical voice scenarios;
- validate conversation flow;
- validate evidence;
- validate reporting.

## Phase 16 — Cross-Platform Qualification

**Status:** ✅ Complete
**Decision:** `CROSS_PLATFORM_QUALIFIED`
**Goal:** Prove the frozen verification platform across all primary
qualification platforms.

Platforms:

- Home Assistant;
- Apple;
- Raspberry Pi;
- Windows;
- ESP;
- DJConnect Voice Assistant.

Objectives:

- verify planner independence;
- verify Scenario Engine portability;
- verify adapter symmetry;
- verify capability abstraction;
- verify evidence consistency;
- verify qualification consistency;
- verify reporting consistency;
- verify platform-independent behaviour.

## Platform Test Coverage Improvement

**Status:** ✅ Complete
**Decision:** `PLATFORM_TEST_COVERAGE_IMPROVEMENT_COMPLETE`
**Position:** Completed after Coverage Baseline 1 and Phase 16 Cross-Platform
Qualification; before Platform Baseline v1.0 Certification.
**Goal:** Increase meaningful automated test coverage across all platform
repositories without changing coverage scope to inflate percentages.

Purpose:

- improve native test suites;
- deepen verification evidence;
- improve testability where justified by risk;
- preserve Coverage Baseline 1 as immutable comparison evidence.

Allowed coverage improvement sources:

- better tests;
- deeper verification;
- improved testability.

Forbidden coverage improvement sources:

- excluding valid production code;
- manipulating coverage scope;
- removing difficult code from measurement.

Objectives:

- Home Assistant: validate coverage scope and improve unit, integration and
  runtime verification coverage.
- Apple: expand simulator tests, runtime tests and domain/service coverage.
- Raspberry Pi: preserve existing quality and improve only where justified by
  risk analysis.
- Windows: use Windows Coverage Baseline 1 as the starting point, expand
  adapter/runtime tests and include Windows in future coordinated coverage
  baselines.

Deliverables:

- improved native test suites;
- updated normalized coverage evidence;
- updated coverage qualification reports;
- trend analysis versus Coverage Baseline 1;
- documented platform-specific coverage improvements.

Acceptance criteria:

- coverage scope validated;
- production source roots verified;
- critical uncovered paths identified;
- meaningful automated tests added;
- `COVERAGE_VALID` maintained;
- measurable improvement versus Coverage Baseline 1;
- Raspberry Pi coverage does not regress;
- Windows is added only after live Windows qualification;
- no qualification regressions introduced.

Dependencies:

- Phase 13E-R2 Windows Live Qualification;
- Phase 16 Cross-Platform Qualification;
- Coverage Baseline 1 remains immutable;
- Verification Runtime `1.1.0` coverage capability remains stable.

## ESP Native Coverage Follow-up

**Status:** ✅ Complete
**Decision:** `ESP_COVERAGE_QUALIFIED`

The ESP32 firmware now uses its host-native C++ logic suite with compiler
coverage instrumentation and `gcovr` to emit Cobertura XML. Runtime `1.1.0`
ingested fresh firmware commit `85f2aca71dbdbefb1344d890cccc4af493a8ca42` as
`COVERAGE_VALID` (90.28% line, 72.71% branch). This strengthens the evidence
available before Platform Baseline certification without changing Phase 17 or
either historical coverage baseline.

## Software Assurance Platform

**Status:** ✅ Architecture complete
**Goal:** Establish the canonical platform-wide software quality governance
layer that extends Verification without replacing behavioural verification.

Completed:

- ✅ Prompt 1: Foundation and Architecture.
- ✅ Canonical ownership and boundary model.
- ✅ Canonical Software Assurance themes.
- ✅ Cost-aware execution profile architecture.
- ✅ Platform Health trend model.
- ✅ Prompt 2: Capability Model, Epic Decomposition and Backlog.
- ✅ Complete capability model with IDs, owners, dependencies and priorities.
- ✅ Theme-to-epic-to-feature-to-story decomposition.
- ✅ Dependency graph and implementation milestones.
- ✅ Prompt 3: Platform Integration and Execution Architecture.
- ✅ Verification Runtime, Execution Environment, execution target, Platform
  Health, release and repository integration model.
- ✅ Prompt 4: Governance, Rollout and Implementation Strategy.
- ✅ Architecture freeze, prerequisites, rollout waves, quality gates,
  versioning and final architecture decision.

Next:

- ⏳ Software Assurance implementation is ready only through its explicit
  registered prompt sequence.

Guardrails:

- no scanners are introduced during architecture prompts;
- no GitHub Actions workflows are modified;
- no release gates are enabled;

## Platform Baseline v1.0 Qualification

**Status:** ✅ Certified
**Decision:** `PLATFORM_BASELINE_V1_CERTIFIED`
**Evidence:** `PLATFORM_BASELINE_CERTIFICATION.md`,
`PLATFORM_BASELINE_1_0.md`,
`PLATFORM_BASELINE_GAP_ANALYSIS.md`

Remaining qualification follow-up:

- ✅ Windows live runtime qualification returned `WINDOWS_LIVE_QUALIFIED`.
- ✅ ESP live qualification returned `ESP_LIVE_QUALIFIED`.
- ✅ Voice Assistant live qualification returned
  `VOICE_ASSISTANT_LIVE_QUALIFIED`.
- ✅ Cross-platform qualification returned `CROSS_PLATFORM_QUALIFIED`.
- ✅ Coverage improvement returned
  `PLATFORM_TEST_COVERAGE_IMPROVEMENT_COMPLETE`; ESP native coverage returned
  `ESP_COVERAGE_QUALIFIED`.

Next:

- preserve the architecture freeze unless a future Architecture Review with
  objective evidence supersedes it;
- begin Software Assurance only through its explicit registered Prompt 1;
- keep Verification as owner of behavioural correctness.

## Architecture Closure Review

**Status:** ✅ Frozen
**Decision:** `ARCHITECTURE_FROZEN`
**Evidence:** `ARCHITECTURE_CLOSURE_REVIEW.md`, `ARCHITECTURE_DECISION.md`

Result:

- ✅ No additional foundational architecture required.
- ✅ Platform Strategy, Platform Foundation, Verification Platform, Software
  Assurance Architecture, Meta Engineering, Repository Bootstrap,
  Cross-Repository Governance, Repository Metadata and Product Strategy
  Foundation may be treated as frozen.
- ✅ Business-first engineering remains blocked until Platform Baseline v1.0 is
  certified.

Next:

- preserve the completed adapter, cross-platform and coverage qualification
  evidence inside the frozen architecture;
- do not create new foundational architecture unless future evidence proves a
  genuine gap.

## Epic 4 — Intelligence Platform

**Status:** 🟡 Current  
**Goal:** Consolidate Insight Providers, Music Intelligence, AI orchestration,
insight generation, recommendation reasoning, mood reasoning,
profile-aware intelligence and future orchestration around a shared
backend-owned intelligence platform.

Scope:

- Insight Provider model;
- Music Intelligence model;
- Insight Feed contract;
- AI orchestration;
- insight generation;
- recommendation reasoning;
- mood reasoning;
- profile-aware intelligence;
- VibeCast hybrid mode;
- Lyrics Explain research;
- Discover contract alignment;
- future orchestration;
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

## Research Program

Research items are strategic investigations. They are not implementation epics,
not roadmap commitments and not architectural decisions.

### R0 — Runtime Independence

**Status:** 🔵 Research
**Priority:** Strategic
**Schedule:** Not scheduled
**Goal:** Explore whether DJConnect could eventually support additional
runtimes while preserving one platform architecture and keeping Home Assistant
first-class.

Deliverable:

- `docs/research/R0_RUNTIME_INDEPENDENCE.md`

Scope:

- current Home Assistant runtime strengths and limitations;
- possible runtime evolution scenarios;
- Home Assistant dependency matrix;
- possible DJConnect Core and runtime adapter model;
- plugin architecture considerations;
- migration, business and risk analysis.
