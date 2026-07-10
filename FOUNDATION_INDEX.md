# DJConnect Platform Foundation Index

This repository, `pcvantol/djconnect`, is the canonical source of truth for the DJConnect platform foundation.

The foundation defines the shared product direction, design principles, architecture rules, domain language, governance and cross-repository alignment for all DJConnect repositories. Sibling repositories extend this foundation with implementation-specific guidance, but they do not redefine it.

## Recommended reading order

For clean Codex or AI-agent sessions, start with
`BOOTSTRAP_CODEX_SESSION.md`. That file defines the session startup procedure.
The files below define the platform foundation itself.

1. `DJCONNECT_CONSTITUTION.md`
2. `PRODUCT_VISION.md`
3. `DESIGN_PRINCIPLES.md`
4. `ARCHITECTURE_PRINCIPLES.md`
5. `DOMAIN_MODEL.md`
6. `PLATFORM_BASELINE_v1.md`
7. `CLIENT_CAPABILITY_MATRIX.md`
8. `LOCALIZATION_STANDARD.md`
9. `PRODUCT_LANGUAGE.md`
10. `PLATFORM_GOVERNANCE.md`
11. `PLATFORM_QUALITY_STANDARD.md`
12. `PLATFORM_BACKLOG.md`
13. `INNOVATION_LAB.md`
14. `docs/research/R0_RUNTIME_INDEPENDENCE.md` where runtime evolution is relevant
15. `ADR_INDEX.md`
16. `CI_CD_RELEASE_GOVERNANCE.md`
17. `docs/verification/00_VERIFICATION_VISION.md`
18. `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
19. `docs/meta/AI_COLLABORATION_MODEL.md`
20. `docs/meta/ENGINEERING_PLAYBOOK.md`
21. `docs/meta/ARCHITECTURAL_HEURISTICS.md`

## Conflict-resolution order

When documents appear to conflict, resolve them in this order:

1. `DJCONNECT_CONSTITUTION.md`
2. `PRODUCT_VISION.md`
3. `DESIGN_PRINCIPLES.md`
4. `ARCHITECTURE_PRINCIPLES.md`
5. `DOMAIN_MODEL.md`
6. `PLATFORM_GOVERNANCE.md`
7. Accepted ADRs in `ADR_INDEX.md` and `docs/adr/`
8. Roadmap and backlog documents
9. Repository-local implementation docs

Repository-specific AGENTS guidance, API contracts, operational procedures and release instructions remain authoritative for local implementation details. They must still conform to the platform foundation for product and platform direction.

## Document classes

### Foundation docs

Foundation docs define stable cross-repository intent and rules. They include the constitution, product vision, design principles, architecture principles, domain model, client capability model, localization standard, product language, governance, quality standard, backlog, innovation model, ADR index and release governance.

### Platform baseline

`PLATFORM_BASELINE_v1.md` captures accepted platform architecture after major
implementation epics.

Foundation describes principles. Baseline describes accepted implementation.

### AI-agent bootstrap

`BOOTSTRAP_CODEX_SESSION.md` defines how Codex and other AI agents start clean
DJConnect sessions. It does not replace the foundation. It tells agents which
foundation files, repository-local instructions and epic/phase context to read
before reporting readiness.

`AGENTS.md` files define repository-local implementation rules. They extend the
platform foundation and bootstrap procedure; they do not redefine platform
truth.

### Meta engineering docs

Meta engineering docs define how humans, AI agents, reviewers and maintainers
collaborate while evolving the platform.

- `docs/meta/AI_COLLABORATION_MODEL.md` defines the canonical AI collaboration
  model and repository-first engineering memory principle.
- `docs/meta/ENGINEERING_PLAYBOOK.md` defines the canonical engineering
  lifecycle from idea to production.
- `docs/meta/ARCHITECTURAL_HEURISTICS.md` defines practical architecture
  decision-making heuristics for the platform.

### Operational docs

Operational docs describe how work is performed, reviewed, released, secured or handed off. Examples include `CONTRIBUTING.md`, `SECURITY.md`, `DEVELOPMENT_ENVIRONMENT.md`, `HANDOFF.md`, release scripts and CI/CD guidance.

### Implementation docs

Implementation docs describe current repository behavior, API contracts, runtime details and tests. Examples include `API_CONTRACT.md`, `VOICE_INTENT_DATA.md`, `SYNC_PROMPTS.md`, module-level documentation and repository-specific AGENTS instructions.

### Research docs

Research docs explore long-term strategic questions without making
architecture decisions or roadmap commitments. They are inputs for future
epics, ADRs and backlog refinement.

- `docs/research/R0_RUNTIME_INDEPENDENCE.md` explores whether DJConnect could
  eventually support additional runtimes while preserving Home Assistant as the
  primary runtime today.

### Verification docs

Verification docs define how DJConnect proves that platform requirements,
accepted baselines, contracts, release artifacts and production readiness are
true in practice.

- `docs/verification/00_VERIFICATION_VISION.md` defines the long-term purpose,
  philosophy and principles of platform verification.
- `docs/verification/01_VERIFICATION_ARCHITECTURE.md` defines the permanent
  verification subsystem architecture: scenario catalog, orchestrator,
  adapters, evidence, reports and readiness.

## Sibling repositories

Sibling repositories own their client, firmware, website, central API or release-artifact responsibilities. They may add local docs that explain how the foundation applies in that repository, but cross-repository product, architecture, domain and governance decisions start here.

Do not create local copies of the canonical foundation in sibling repositories. Link back to this repository instead.
