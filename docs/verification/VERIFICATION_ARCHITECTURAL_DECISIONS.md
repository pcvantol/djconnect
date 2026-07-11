# Verification Architectural Decisions

Status: canonical reconstruction

This document records accepted Verification Program decisions as they stand in
the repository. It preserves final outcomes without pretending the path was
cleaner than it was.

## VAD-001 - Verification Is A Platform Capability

Context: DJConnect spans HA, clients, firmware, hardware and release surfaces.

Decision: Verification is a platform capability, not a collection of local test
scripts.

Rationale: Repository tests cannot prove platform behavior, cross-client
contracts, privacy boundaries or release readiness alone.

Rejected alternatives: per-repository checklist ownership; one-off release QA;
CI-only proof.

Consequences: Verification has durable architecture, scenarios, evidence,
reports and readiness decisions.

Status: accepted.

Related documents: `docs/verification/00_VERIFICATION_VISION.md`,
`docs/verification/01_VERIFICATION_ARCHITECTURE.md`.

## VAD-002 - Scenario x Matrix x Data x Mode x Policy

Context: A scenario describes behavior, but not every environment, dataset or
quality attribute.

Decision: Concrete test cases are generated from Scenario x Matrix x Data x
Mode x Policy.

Rationale: This avoids duplicating scenarios while still covering platforms,
locales, accessibility, security, privacy, performance and release gates.

Rejected alternatives: hand-writing separate tests for every platform; adding
environment conditions directly into scenarios.

Consequences: The Planning Engine owns expansion and reduction.

Status: accepted.

Related documents: `docs/verification/03A_VERIFICATION_MATRIX.md`,
`docs/verification/08A_VERIFICATION_DATA_FRAMEWORK.md`,
`docs/verification/08B_VERIFICATION_MODES.md`,
`docs/verification/08B_VERIFICATION_POLICIES.md`.

## VAD-003 - Scenario Engine And Core Own Verification Behavior

Context: Adapters need to execute actions without redefining expected behavior.

Decision: Scenario interpretation, assertions, aggregation and pass/fail
ownership remain in the Scenario Engine and Verification Core.

Rationale: Expected behavior must stay traceable to Foundation, baseline,
technical design and scenarios.

Rejected alternatives: adapter-local assertions; product-specific logic inside
environment tooling.

Consequences: Adapter results are raw observations until the Core evaluates
them.

Status: accepted.

Related documents: `docs/verification/04_VERIFICATION_HARNESS.md`,
`docs/verification/09_HOME_ASSISTANT_VERIFICATION_ADAPTER.md`.

## VAD-004 - Platform Adapters Stay Thin

Context: The first adapter is Home Assistant, but more adapters will follow.

Decision: Platform adapters answer only how to perform runtime operations.

Rationale: Thin adapters keep behavior portable and prevent platform-specific
test logic from fragmenting expected results.

Rejected alternatives: rich adapter frameworks with embedded product
knowledge; HA-specific CLI and planner paths.

Consequences: Adapters expose primitives such as REST, WebSocket, service,
state, storage snapshot and log collection.

Status: accepted.

Related documents: `docs/verification/09_HOME_ASSISTANT_VERIFICATION_ADAPTER.md`.

## VAD-005 - Execution Environment Is Separate

Context: Build tools, Docker, CI, SSH, serial, VMs and artifacts surround
execution but are not adapter behavior.

Decision: The Verification Execution Environment owns repository hygiene,
build qualification, toolchains, Docker, CI, SSH, serial, simulators, VMs,
artifacts, secrets loading by name and cleanup.

Rationale: Platform adapters should not duplicate environment preparation or
cleanup.

Rejected alternatives: each adapter managing its own builds, logs and runtime
lifecycle.

Consequences: Live verification must pass environment gates before mutation.

Status: accepted.

Related documents: `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`.

## VAD-006 - Adapter Growth Is Scenario-Driven

Context: The adapter surface can grow without limit if implemented
speculatively.

Decision: Add adapter primitives only when required by approved scenarios.

Rationale: Scenario-driven growth keeps the adapter reviewable and aligned
with platform needs.

Rejected alternatives: complete HA API wrapper; speculative multi-platform
orchestration.

Consequences: Phase 9 started with `PROFILE-001` through `PROFILE-005`.

Status: accepted.

Related documents: `docs/verification/03_SCENARIO_CATALOG.md`,
`docs/verification/reports/PHASE_09_HOME_ASSISTANT_ADAPTER_COMPLETION.md`.

## VAD-007 - Deterministic Data And Seed Ownership

Context: Verification cannot depend on ad hoc strings or developer-specific
fixtures.

Decision: The Verification Data Framework owns canonical data, generators,
profiles, boundaries, localization payloads, security payloads and seeds.

Rationale: Runs must be reproducible and varied without hiding data choices in
adapters or scenarios.

Rejected alternatives: hardcoded examples in scenarios; random values without
seed tracking.

Consequences: Evidence must record seed, data profile and generator versions.

Status: accepted; evidence emission remains a Phase 9V/9L gap.

Related documents: `docs/verification/08A_VERIFICATION_DATA_FRAMEWORK.md`,
`docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`.

## VAD-008 - Durable Immutable Evidence

Context: Phase 9V showed that reports without durable run artifacts are not
enough.

Decision: Verification evidence must be persisted as immutable per-run
artifacts with redaction and checksums.

Rationale: Review, investigation and rerun support require reproducible
artifacts, not only terminal output.

Rejected alternatives: manual report-only evidence; overwriting latest-run
files.

Consequences: Run artifacts are stored under the configured evidence directory
and can be listed, shown, verified and investigated.

Status: accepted; implemented by Phase 9R.

Related documents: `docs/verification/reports/PHASE_09R_QUALIFICATION_REMEDIATION.md`,
`tools/verification/evidence/run_store.py`.

## VAD-009 - Exact-SHA CI Qualification

Context: Phase 9V could not accept CI because the checked SHA had no usable
status evidence.

Decision: GitHub CI qualification must be exact-SHA based.

Rationale: A green workflow for another commit is not qualification evidence
for the current run.

Rejected alternatives: accepting branch-level status; accepting absent
connector status as pass.

Consequences: Missing auth, no data, running checks, failed checks and SHA
mismatch are explicit gate states.

Status: accepted; implemented by Phase 9R, still requires operator auth.

Related documents: `docs/verification/reports/PHASE_09R_QUALIFICATION_REMEDIATION.md`.

## VAD-010 - Docker-Based Local HA Verification Lab

Context: Phase 9V lacked a proven Home Assistant runtime; Phase 9R detected an
existing HA container but could not prove it safe.

Decision: Local HA verification must use a dedicated Docker-based verification
lab with labels, isolated config/storage/logs and source/SHA fingerprinting.

Rationale: A production-like HA container must not be mutated by verification.

Rejected alternatives: using any running `homeassistant` container; relying on
manual assurance.

Consequences: Phase 9L must build and qualify the local lab before Phase 9V
can rerun.

Status: accepted; implementation pending Phase 9L.

Related documents: `prompts/verification/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`.

## VAD-011 - Failure Ownership Is Explicit

Context: Phase 9V failures mixed framework gaps, environment gaps and adapter
gaps.

Decision: Failures must be classified into one owning category before fixes.

Rationale: Product defects, adapter defects, scenario defects, environment
defects and documentation mismatches need different owners and rerun scopes.

Rejected alternatives: one generic failed status; assuming all failed scenario
runs are product bugs.

Consequences: The Investigator emits classification, confidence, owner,
blocking status and action.

Status: accepted; implemented as an existing Verification Core workflow in
Phase 9R.

Related documents: `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION.md`,
`tools/verification/core/investigator.py`.

## VAD-012 - Investigator Is A Workflow, Not A Subsystem

Context: The framework needed executable investigation without expanding the
architecture again.

Decision: Verification Investigator belongs inside the existing Verification
system and does not introduce a new top-level architecture layer.

Rationale: Investigation is part of evidence and readiness, not a separate
platform subsystem.

Rejected alternatives: adding a new architectural layer after the foundation
was declared complete.

Consequences: Future investigation improvements extend Verification Core,
Evidence or Reporting.

Status: accepted.

Related documents: `BOOTSTRAP_CODEX_VERIFICATION.md`,
`docs/verification/reports/PHASE_09R_QUALIFICATION_REMEDIATION.md`.

## VAD-013 - Evidence-First Acceptance

Context: The Verification Program must support review and future automation.

Decision: A phase is accepted only when evidence, reports, tests and blocking
limitations are recorded.

Rationale: Passing commands without preserved evidence does not prove platform
readiness.

Rejected alternatives: verbal acceptance; chat-only completion state.

Consequences: Each qualification phase must produce report artifacts and a
readiness decision.

Status: accepted.

Related documents: `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION.md`.

## VAD-014 - Qualify Each Adapter Before The Next Platform

Context: Future Apple, Pi, ESP32 and Windows adapters will depend on the
framework.

Decision: The Verification Platform and each adapter must be qualified before
starting the next platform adapter.

Rationale: Later adapters should not inherit unproven framework assumptions.

Rejected alternatives: parallel adapter implementation before Phase 9V is
qualified.

Consequences: Phase 10 Apple remains blocked until Phase 9V succeeds.

Status: accepted.

Related documents: `PROMPT_INDEX.md`,
`docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`.

## VAD-015 - Repository Is Durable AI Context

Context: Large chat prompts carried essential context but were not durable.

Decision: Verification context, prompt status and architectural decisions must
live in the repository.

Rationale: Clean agents must be able to continue work without unavailable chat
history.

Rejected alternatives: chat-only prompts; handoff notes outside source
control.

Consequences: `BOOTSTRAP_CODEX_VERIFICATION.md`, `PROMPT_INDEX.md` and
canonical prompts under `prompts/verification/` become the entrypoints.

Status: accepted.

Related documents: `BOOTSTRAP_CODEX_VERIFICATION.md`, `PROMPT_INDEX.md`.

## VAD-016 - No Direct Coupling To Chat History

Context: Earlier phases depended on large pasted prompts.

Decision: Clean sessions must read repository documents and prompts, not chat
history.

Rationale: The repository must be the portable source of truth for humans and
agents.

Rejected alternatives: instructing future agents to find external
non-repository notes or infer context from external PR discussion.

Consequences: Prompt files and indices must be kept current with phase status.

Status: accepted.

Related documents: `BOOTSTRAP_CODEX_VERIFICATION.md`, `PROMPT_INDEX.md`.

## VAD-017 - Runtime Docker Images Are Engine-Only

Context: The Verification Platform runtime can now be released as a Docker
image, while DJConnect scenario catalogs and product repositories continue to
evolve independently.

Decision: Docker releases of the Verification Platform contain only generic
engine components. Product scenarios, repository checkouts, Home Assistant lab
state, client artifacts, secrets and evidence are supplied externally at run
time.

Rationale: Runtime reproducibility should not bake in a specific DJConnect
product state or leak environment-specific artifacts into a reusable engine
image.

Rejected alternatives: publishing a monolithic image that includes the current
scenario catalog, local lab config or product repository source.

Consequences: Release tags identify the verification runtime version and
release SHA. Scenario and product coverage remain versioned by the repository
checkout, mounted artifacts and recorded run metadata.

Status: accepted.

Related documents: `docs/verification/04_VERIFICATION_HARNESS.md`,
`docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`,
`tools/verification/README.md`.
