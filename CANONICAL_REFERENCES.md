# DJConnect Canonical References

Status: repository-local canonical reference map

This repository, `pcvantol/djconnect`, is the canonical platform repository for
DJConnect. It owns the platform foundation, platform prompt index, verification
foundation, Meta Engineering foundation, repository ownership and Home
Assistant integration implementation.

Sibling repositories must reference these canonical documents instead of
copying or redefining them.

## Platform Strategy

- Canonical repository: `pcvantol/djconnect`
- Canonical document: `PLATFORM_STRATEGY.md`
- Local responsibility: maintain the long-term strategic intent that explains
  why the platform is evolving toward a production-ready, fully verified
  cross-platform baseline before business-first feature velocity.
- May this repository modify it: yes, through Architecture Review.

Sibling repositories may reference Platform Strategy, but they must not copy,
reinterpret or redefine it in repository-local prompt indexes or roadmaps.

## Platform Overview Architecture

- Canonical repository: `pcvantol/djconnect`
- Canonical document: `PLATFORM_OVERVIEW_ARCHITECTURE.md`
- Local responsibility: provide the descriptive architectural entry point for
  the existing Profile, Playback, Session Intelligence, Presentation and
  Verification platforms, while directing readers to their detailed canonical
  documents.
- May this repository modify it: yes, only when established architecture or its
  canonical navigation changes.

The overview does not define a new platform, ownership model, implementation
plan or Runtime behaviour.

## Platform Foundation

- Canonical repository: `pcvantol/djconnect`
- Canonical document: `FOUNDATION_INDEX.md`
- Local responsibility: maintain the platform foundation and update it when
  product direction, architecture, governance, domain language, localization,
  ownership, release rules or cross-repository contracts change.
- May this repository modify it: yes.

Authoritative foundation documents include:

- `DJCONNECT_CONSTITUTION.md`
- `PRODUCT_VISION.md`
- `DESIGN_FOUNDATION_VERSION.md`
- `DESIGN_PRINCIPLES.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `DOMAIN_MODEL.md`
- `PLATFORM_PRINCIPLES.md`
- `CLIENT_CAPABILITY_MATRIX.md`
- `DJCONNECT_CAPABILITY_MODEL.md`
- `HOST_ROLE_ARCHITECTURE.md`
- `RASPBERRY_PI_PLATFORM_FOUNDATION.md`
- `EXPERIENCE_FOUNDATION.md`
- `LOCALIZATION_STANDARD.md`
- `PRODUCT_LANGUAGE.md`
- `PLATFORM_GOVERNANCE.md`
- `PLATFORM_QUALITY_STANDARD.md`
- `PLATFORM_BACKLOG.md`
- `REPOSITORY_OWNERSHIP.md`
- `PLATFORM_DISCOVERY_REPORT.md`
- `ADR_INDEX.md`

## Product Strategy Foundation

- Canonical repository: `pcvantol/djconnect`
- Canonical documents: `docs/product/README.md` and
  `docs/product/PRODUCT_STRATEGY.md`
- Local responsibility: maintain validated product direction after concepts
  graduate from `INNOVATION_LAB.md`, without duplicating Platform Strategy,
  the Innovation Lab, roadmap sequencing or engineering backlog work.
- May this repository modify it: yes, through explicit product strategy
  foundation updates.

Innovation Labs remain the canonical source for product ideas. Product
Strategy accepts only validated product direction. A formal post-baseline
Product Roadmap and Product Backlog do not yet exist under this product
strategy lifecycle.
- `CI_CD_RELEASE_GOVERNANCE.md`

## Verification Foundation

- Canonical repository: `pcvantol/djconnect`
- Canonical documents: `BOOTSTRAP_CODEX_VERIFICATION.md`,
  `docs/verification/00_VERIFICATION_VISION.md`,
  `docs/verification/01_VERIFICATION_ARCHITECTURE.md` and
  `PROMPT_INDEX.md`
- Local responsibility: maintain the canonical Verification Program,
  prompt navigation, reports, scenario framework, adapters and evidence rules.
- May this repository modify it: yes, through explicit verification phases.

Sibling repositories may own local verification targets or artifacts, but they
must not redefine the canonical Verification Foundation.

## Software Assurance Foundation

- Canonical repository: `pcvantol/djconnect`
- Canonical documents: `SOFTWARE_ASSURANCE_PLATFORM.md`,
  `SOFTWARE_ASSURANCE_ARCHITECTURE.md`,
  `SOFTWARE_ASSURANCE_THEMES.md`,
  `SOFTWARE_ASSURANCE_CAPABILITY_MODEL.md`,
  `SOFTWARE_ASSURANCE_BACKLOG.md`,
  `SOFTWARE_ASSURANCE_DEPENDENCIES.md`,
  `SOFTWARE_ASSURANCE_IMPLEMENTATION_ORDER.md`,
  `SOFTWARE_ASSURANCE_INTEGRATION.md`,
  `SOFTWARE_ASSURANCE_EXECUTION_MODEL.md`,
  `SOFTWARE_ASSURANCE_PLATFORM_HEALTH.md` and
  `SOFTWARE_ASSURANCE_REPOSITORY_MODEL.md`,
  `SOFTWARE_ASSURANCE_GOVERNANCE.md`,
  `SOFTWARE_ASSURANCE_ROLLOUT.md`,
  `SOFTWARE_ASSURANCE_IMPLEMENTATION_STRATEGY.md`,
  `SOFTWARE_ASSURANCE_QUALITY_GATES.md`,
  `SOFTWARE_ASSURANCE_VERSIONING.md` and
  `SOFTWARE_ASSURANCE_IMPLEMENTATION.md`
- Local responsibility: maintain platform-wide engineering quality governance,
  software assurance themes, capability IDs, implementation backlog, execution
  profile architecture, dependency graph, integration boundaries, rollout
  governance, quality gate architecture, versioning, implementation
  registration, evidence taxonomy, reporting boundaries and Platform Health
  definitions.
- May this repository modify it: yes, through explicit Software Assurance
  architecture or implementation phases.

Software Assurance extends the Verification Platform. It must not redefine
verification scenarios, behavioural expected results, adapter ownership or
release gates.

## Meta Engineering Foundation

- Canonical repository: `pcvantol/djconnect`
- Canonical document: `docs/meta/README.md`
- Local responsibility: maintain the shared engineering process, AI
  collaboration model, repository-as-memory model, completion protocol and
  decision-placement guidance.
- May this repository modify it: yes, when engineering practice changes.

Meta Engineering documents are process guidance. They do not redefine product
behavior, runtime architecture or verification expectations.

## Platform Prompt Index

- Canonical repository: `pcvantol/djconnect`
- Canonical document: `PROMPT_INDEX.md`
- Local responsibility: maintain the complete platform verification roadmap,
  current active phase, predecessor relationships, reports and next phase
  navigation.
- May this repository modify it: yes.

Client repositories may keep repository-local prompt indexes for their own
current phase and completion status only. They must not copy the platform
roadmap.

## Repository Ownership

- Canonical repository: `pcvantol/djconnect`
- Canonical document: `REPOSITORY_OWNERSHIP.md`
- Local responsibility: maintain cross-repository ownership boundaries and
  clarify what each repository owns and must not own.
- May this repository modify it: yes.

## Technical Design Ownership

- Canonical repository: `pcvantol/djconnect` for Home Assistant integration
  technical design and shared backend contracts.
- Canonical documents: `docs/technical/`, `API_CONTRACT.md`,
  `DOMAIN_MODEL.md`, accepted ADRs and implementation-specific module docs.
- Local responsibility: keep Home Assistant integration implementation reality,
  API contracts, verification adapters and technical design aligned.
- May this repository modify it: yes for this repository's implementation and
  canonical shared contracts.

Sibling repositories own their local technical design for Apple, Windows,
Raspberry Pi, ESP32, website, API and release artifacts.

## Local Implementation Ownership

- Canonical repository: `pcvantol/djconnect`
- Canonical documents: `AGENTS.md`, `custom_components/djconnect/AGENTS.md`,
  `README.md`, `CONTRIBUTING.md`, implementation files and local tests.
- Local responsibility: implement and maintain the Home Assistant/HACS
  integration, local-first backend runtime, pairing, OAuth/backend playback,
  Ask DJ, Music DNA, OTA/status/diagnostics, HA-facing API contracts and
  verification tooling owned by this repository.
- May this repository modify it: yes.

This repository must not modify sibling repository source code unless a task
explicitly checks out and scopes that repository.

## Clean-Session Entrypoints

- General work: read `BOOTSTRAP_CODEX_SESSION.md`.
- Verification work: read `BOOTSTRAP_CODEX_SESSION.md`, then
  `BOOTSTRAP_CODEX_VERIFICATION.md`.
- Software Assurance work: read `BOOTSTRAP_CODEX_SESSION.md`, the Software
  Assurance foundation documents and the relevant Verification and Meta
  Engineering documents.
- Repository state: read `REPOSITORY_STATUS.md`.
- Platform roadmap: read `PROMPT_INDEX.md`.

`CHAT_BOOTSTRAP.md` is deprecated and is not a canonical entrypoint.
