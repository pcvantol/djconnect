# DJConnect Platform Foundation Index

This repository, `pcvantol/djconnect`, is the canonical source of truth for the DJConnect platform foundation.

The foundation defines the shared product direction, design principles, architecture rules, domain language, governance and cross-repository alignment for all DJConnect repositories. Sibling repositories extend this foundation with implementation-specific guidance, but they do not redefine it.

`PLATFORM_STRATEGY.md` sits above the foundation. It defines long-term
strategic intent and explains why the platform is currently evolving in its
present direction. The foundation owns architecture, governance and durable
platform rules.

## Recommended reading order

For clean Codex or AI-agent sessions, start with
`BOOTSTRAP_CODEX_SESSION.md`. That file defines the session startup procedure.
The files below define Platform Strategy, then the platform foundation itself.

1. `PLATFORM_STRATEGY.md`
2. `DJCONNECT_CONSTITUTION.md`
3. `PRODUCT_VISION.md`
4. `DESIGN_PRINCIPLES.md`
5. `ARCHITECTURE_PRINCIPLES.md`
6. `DOMAIN_MODEL.md`
7. `docs/product/README.md`
8. `docs/product/PRODUCT_STRATEGY.md`
9. `PLATFORM_BASELINE_v1.md`
10. `PLATFORM_BASELINE_1_0.md`
11. `PLATFORM_BASELINE_CERTIFICATION.md`
12. `PLATFORM_BASELINE_GAP_ANALYSIS.md`
13. `CLIENT_CAPABILITY_MATRIX.md`
14. `LOCALIZATION_STANDARD.md`
15. `PRODUCT_LANGUAGE.md`
16. `PLATFORM_GOVERNANCE.md`
17. `PLATFORM_QUALITY_STANDARD.md`
18. `PLATFORM_BACKLOG.md`
19. `INNOVATION_LAB.md`
20. `docs/research/R0_RUNTIME_INDEPENDENCE.md` where runtime evolution is relevant
21. `ADR_INDEX.md`
22. `CI_CD_RELEASE_GOVERNANCE.md`
23. `docs/verification/00_VERIFICATION_VISION.md`
24. `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
25. `SOFTWARE_ASSURANCE_PLATFORM.md`
26. `SOFTWARE_ASSURANCE_ARCHITECTURE.md`
27. `SOFTWARE_ASSURANCE_THEMES.md`
28. `SOFTWARE_ASSURANCE_CAPABILITY_MODEL.md`
29. `SOFTWARE_ASSURANCE_BACKLOG.md`
30. `SOFTWARE_ASSURANCE_DEPENDENCIES.md`
31. `SOFTWARE_ASSURANCE_IMPLEMENTATION_ORDER.md`
32. `SOFTWARE_ASSURANCE_INTEGRATION.md`
33. `SOFTWARE_ASSURANCE_EXECUTION_MODEL.md`
34. `SOFTWARE_ASSURANCE_PLATFORM_HEALTH.md`
35. `SOFTWARE_ASSURANCE_REPOSITORY_MODEL.md`
36. `SOFTWARE_ASSURANCE_GOVERNANCE.md`
37. `SOFTWARE_ASSURANCE_ROLLOUT.md`
38. `SOFTWARE_ASSURANCE_IMPLEMENTATION_STRATEGY.md`
39. `SOFTWARE_ASSURANCE_QUALITY_GATES.md`
40. `SOFTWARE_ASSURANCE_VERSIONING.md`
41. `SOFTWARE_ASSURANCE_IMPLEMENTATION.md`
42. `docs/meta/META_ENGINEERING_INDEX.md`

## Conflict-resolution order

When documents appear to conflict, resolve them in this order:

1. `PLATFORM_STRATEGY.md` for long-term strategic intent
2. `DJCONNECT_CONSTITUTION.md`
3. `PRODUCT_VISION.md`
4. `DESIGN_PRINCIPLES.md`
5. `ARCHITECTURE_PRINCIPLES.md`
6. `DOMAIN_MODEL.md`
7. `PLATFORM_GOVERNANCE.md`
8. Accepted ADRs in `ADR_INDEX.md` and `docs/adr/`
9. Roadmap and backlog documents
10. Repository-local implementation docs

Repository-specific AGENTS guidance, API contracts, operational procedures and release instructions remain authoritative for local implementation details. They must still conform to the platform foundation for product and platform direction.

## Document classes

### Foundation docs

Foundation docs define stable cross-repository intent and rules. They include the constitution, product vision, design principles, architecture principles, domain model, client capability model, localization standard, product language, governance, quality standard, backlog, innovation model, ADR index and release governance.

### Product strategy

`docs/product/PRODUCT_STRATEGY.md` defines validated product direction. It
begins where `INNOVATION_LAB.md` ends and intentionally does not define
features, epics, stories, roadmap sequencing or backlog work.

### Platform strategy

`PLATFORM_STRATEGY.md` defines stable long-term platform intent. Current
execution priorities are now platform qualification, adapter completion and
cross-platform evidence inside the frozen architecture.

Canonical lifecycle:

```text
Platform Architecture
  -> Platform Qualification
  -> Platform Baseline
  -> Business-first Engineering
```

The current platform state is Platform Qualification.

### Architecture closure

`ARCHITECTURE_CLOSURE_REVIEW.md` and `ARCHITECTURE_DECISION.md` record the
2026-07-11 closure decision `ARCHITECTURE_FROZEN`. Future work should proceed
inside the frozen architecture unless a later evidence-backed Architecture
Review demonstrates a genuine foundational gap.

### Platform baseline

`PLATFORM_BASELINE_v1.md` captures accepted platform architecture after major
implementation epics.

Foundation describes principles. Baseline describes accepted implementation.

`PLATFORM_BASELINE_CERTIFICATION.md` captures the Platform Baseline v1.0
certification status. The current certification result is
`PLATFORM_BASELINE_V1_NOT_CERTIFIED`.

`PLATFORM_BASELINE_1_0.md` and `PLATFORM_BASELINE_GAP_ANALYSIS.md` remain as
baseline assessment and qualification follow-up evidence.

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

- `docs/meta/META_ENGINEERING_INDEX.md` is the canonical navigation page for
  Meta Engineering.
- `docs/meta/AI_COLLABORATION_MODEL.md` defines the canonical AI collaboration
  model and repository-first engineering memory principle.
- `docs/meta/ENGINEERING_PLAYBOOK.md` defines the canonical engineering
  lifecycle from idea to production.
- `docs/meta/ARCHITECTURAL_HEURISTICS.md` defines practical architecture
  decision-making heuristics for the platform.
- `docs/meta/DECISION_PATTERNS.md` defines where newly discovered engineering
  knowledge belongs in the repository.
- `docs/meta/REPOSITORY_AS_MEMORY.md` explains why the repository is the
  durable engineering memory instead of prompts or chat history.
- `docs/meta/AI_AGENT_GUIDELINES.md` defines how AI agents are expected to
  operate within the DJConnect engineering process.

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

### Software Assurance docs

Software Assurance docs define the platform-wide engineering quality
governance layer that extends Verification without replacing it.

- `SOFTWARE_ASSURANCE_PLATFORM.md` defines scope, ownership, boundaries,
  execution model, governance principles, Platform Health and roadmap position.
- `SOFTWARE_ASSURANCE_ARCHITECTURE.md` defines the assurance layer,
  responsibility boundaries, evidence flow, reporting model and integration
  with Verification, Release Qualification and Meta Engineering.
- `SOFTWARE_ASSURANCE_THEMES.md` defines the six canonical assurance themes:
  Static Quality, Supply Chain Assurance, Dynamic Runtime Assurance, Execution
  Strategy and Cost Governance, Release Assurance and Platform Health.
- `SOFTWARE_ASSURANCE_CAPABILITY_MODEL.md` defines reusable capability IDs,
  ownership, execution targets, evidence, verification method, dependencies,
  completion criteria and priority.
- `SOFTWARE_ASSURANCE_BACKLOG.md` decomposes themes into epics, features,
  stories, acceptance criteria and definitions of done.
- `SOFTWARE_ASSURANCE_DEPENDENCIES.md` defines the acyclic capability
  dependency graph and critical paths.
- `SOFTWARE_ASSURANCE_IMPLEMENTATION_ORDER.md` groups capabilities into future
  implementation milestones without enabling tooling.
- `SOFTWARE_ASSURANCE_INTEGRATION.md` defines interfaces between Foundation,
  Verification, Software Assurance, Verification Runtime, Execution
  Environment, Evidence, Platform Health and Release Qualification.
- `SOFTWARE_ASSURANCE_EXECUTION_MODEL.md` defines execution targets,
  cost-aware profiles, self-hosted runner architecture, hybrid execution and
  the GitHub Actions boundary.
- `SOFTWARE_ASSURANCE_PLATFORM_HEALTH.md` defines Platform Health data flow,
  health categories and non-gating trend semantics.
- `SOFTWARE_ASSURANCE_REPOSITORY_MODEL.md` defines how sibling repositories
  consume Software Assurance without redefining it.
- `SOFTWARE_ASSURANCE_GOVERNANCE.md` defines the architecture freeze,
  implementation prerequisites, ownership, backlog governance and final
  architecture decision.
- `SOFTWARE_ASSURANCE_ROLLOUT.md` defines the canonical wave rollout and
  repository rollout governance.
- `SOFTWARE_ASSURANCE_IMPLEMENTATION_STRATEGY.md` defines deferred
  implementation strategy, CI/CD placement and roadmap transition.
- `SOFTWARE_ASSURANCE_QUALITY_GATES.md` defines future gate architecture
  without enabling gates.
- `SOFTWARE_ASSURANCE_VERSIONING.md` defines lifecycle, semantic versioning
  and compatibility expectations.
- `SOFTWARE_ASSURANCE_IMPLEMENTATION.md` registers the future implementation
  epic, records its deferred state and requires
  `PLATFORM_BASELINE_V1_CERTIFIED` before Prompt 1 may begin.

## Sibling repositories

Sibling repositories own their client, firmware, website, central API or release-artifact responsibilities. They may add local docs that explain how the foundation applies in that repository, but cross-repository product, architecture, domain and governance decisions start here.

Do not create local copies of the canonical foundation in sibling repositories. Link back to this repository instead.
