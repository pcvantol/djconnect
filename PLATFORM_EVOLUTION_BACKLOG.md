# DJConnect Platform Evolution Backlog

**Owner:** Platform Evolution
**Status:** Canonical future-evolution backlog

Platform Evolution is supporting work, not the primary roadmap. Completed
Generation 2 foundations are recorded in
`GENERATION_2_PROGRAM_RECONCILIATION.md`, not in this backlog. Every item
below uses exactly one program status: Completed, Current execution, Planned,
Deferred, Historical or Retired.

Platform Evolution remains assessment-first foundation evolution, governance,
qualification, privacy and release maturity. It is not the primary source of
user-facing roadmap progress; the current Product Initiative is recorded in
`PRODUCT_ROADMAP.md`.

| Initiative | Priority | Status | Dependencies | Promotion path |
| --- | --- | --- | --- | --- |
| Capability-profile assessment follow-up | P2 | Planned | `DJCONNECT_CAPABILITY_MODEL.md`, current contract/host evidence | assessment-first increments in `CAPABILITY_MODEL_BACKLOG.md`; no product implementation authorization |
| Canonical governance Version 2.2 alignment | P0 | Historical | merged governance evidence | retained governance evidence only |
| Component Release Mode | P2 | Planned | release evidence and current manifest model | bounded architecture review if contracts change |
| GitHub Actions retention and evidence preservation (`TD-GITHUB-001`) | P1 | Planned | governance approval, Repository Ownership integration and a future approved retention design | governed implementation only after design and qualification |
| Public distribution: Apple | P1 | Planned | qualified Internal Release consumers and explicit authorization | release-operational work |
| Public distribution: Windows | P1 | Planned | qualified Internal Release consumers and explicit authorization | release-operational work |
| Public HACS distribution | P1 | Planned | fresh candidate and release authorization | release-operational work |
| Client Connectivity & Resilience qualification | P1 | Assessed | `docs/technical/CLIENT_CONNECTIVITY_RESILIENCE_ARCHITECTURE.md`, Public Release Readiness Assessment | `GO_CLIENT_CONNECTIVITY_PARTIALLY_QUALIFIED`; bounded external HTTP and resilience evidence remains required before Public Release Readiness, with no Runtime, transport or client implementation authorization |
| HACS 3.3.0 release visibility (`HACS-3.3.0-001`) | P1 | Planned | verify release/tag metadata, HACS cache/index discovery and update presentation | bounded distribution investigation |
| HACS pull-request validation reliability (`HACS-CI-PR-REF-001`) | P1 | Assessed | `docs/software_assurance/HACS_PR_VALIDATION_RELIABILITY_ASSESSMENT.md`; retained PR #461 head/merge loading failures, PR #459/#500 success and `main` success | HACS is execution-required engineering evidence but not release-authoritative; no workflow, Runtime, qualification, gate or action-pinning change |
| Home Assistant DJConnect HTTP-route registration (`HA-HTTP-ROUTE-3.3.0-001`) | P0 | Historical | reconciled incident evidence | retained incident evidence only |
| Firmware OTA publication and staged rollback | P1 | Planned | manifest-bound consumer qualification | release-operational work |
| Website production deployment and announcements | P1 | Planned | approved manifest and consumer qualification | release-operational work |
| Technical Debt Engine integration | P1 | Deferred | released standalone TDE CLI, stable evidence schema, trusted distribution and Software Assurance compatibility | Platform Evolution integration after external product initialization |
| Privacy Assessment | P2 | Planned | privacy inventory, profile/shared-device review and Software Assurance compatibility | Platform Evolution assessment; possible future standalone engine |
| SBOM generation | P2 | Planned | Trusted Delivery compatibility assessment | scoped Platform Evolution proposal |
| Release Health and observability | P2 | Planned | operational release evidence and [`PLATFORM_RELEASE_OBSERVATORY_DESIGN.md`](docs/platform_evolution/PLATFORM_RELEASE_OBSERVATORY_DESIGN.md) | three bounded delivery increments; no implementation authorization |
| Platform diagnostics | P3 | Planned | privacy and redaction review | scoped Platform Evolution proposal |
| Future governance improvements | P3 | Planned | governance evidence | governance review |

## Historical operational context

Platform Release 3.3 Internal is **Historical** operational evidence. Its
completed release and any retained operational evidence are documented in
`docs/release/PLATFORM_RELEASE_MANAGEMENT_SUMMARY.md`; they do not become a
fourth program or an active Platform Evolution item.

## Backlog detail: GitHub Actions retention and evidence preservation

**Risk ID:** `TD-GITHUB-001`

**Owner:** Platform Evolution

**Priority:** P1
**Status:** Open / Backlog

Generation 1 accepted the narrow GitHub native SHA-enforcement compatibility
exception. The active compensating controls are recursive workflow-closure
validation, terminal immutable-action validation and registry consistency
checks. They preserve the accepted Generation 1 exception but do not resolve
the broader risk that governed release and assurance evidence may not be
retained or protected consistently across repositories.

This risk remains open because a retention and evidence-preservation design has
not been approved or qualified. The future work must answer, without assuming
a solution, how protected release, qualification, certification, assurance,
incident, rollback and audit evidence is classified, preserved and governed;
how uncertain classification fails closed; and how the policy remains
compatible with repository ownership and governance boundaries.

Required acceptance evidence and closure criteria are:

- an approved retention and evidence-preservation design;
- evidence that protected release, qualification, certification, assurance,
  incident, rollback and audit evidence is retained;
- demonstrated fail-closed behaviour when classification or protection cannot
  be reliably established;
- qualified implementation evidence; and
- governance approval before any cleanup or deletion becomes operational.

This backlog record authorizes no retention design, workflow change,
deletion-policy decision or implementation. It records an open Platform
Evolution risk only.

## Backlog detail: Release Health and observability

**Detailed capability:** [Platform Release Observatory](docs/platform_evolution/PLATFORM_RELEASE_OBSERVATORY_DESIGN.md)
**Owner:** Platform Evolution
**Priority:** P2
**Status:** Design Complete / Implementation Backlog

The Observatory is a local-only, read-only capability for factual current and
historical release inventory and rollout investigation. It consumes existing
approved manifests, repository/GitHub evidence, deployment and smoke evidence,
artifact/distribution evidence, and supported factual publication state. It
does not execute, approve or gate releases; it does not replace Platform
Release Runtime, GitHub Actions, or the current Platform Release 3.3
operational sequence. Product Development does not depend on this initiative.

Future delivery remains three separately reviewable increments:

1. Evidence and timing contract in the owning CI, deployment, smoke and
   publication flows.
2. Collector and local SQLite persistence.
3. Local dashboard and evidence investigation UI.

This backlog registration authorizes no implementation. Its P2 priority is
supported by the existing operational evidence records, which remain the
authoritative release source until a future delivery increment is authorized.

## Backlog detail: Component Release Mode

Design a first-class Component Release mode within the existing Platform
Release Runtime. The runtime remains the one canonical release orchestrator;
the new mode must select exactly one Repository Ownership participant and reuse
the existing release graph, Verification Runtime, Software Assurance, Trusted
Delivery, SHA-based candidate qualification, evidence, deployment and rollback
paths. It must not create a second release engine or alter coordinated Platform
Release mode.

The selected component may increment only its patch version within the current
platform `major.minor` train. Repository discovery must determine the affected
source repository, dependent release repository where applicable, deployment
target and verification target without bringing unrelated repositories into
the qualification or release scope. Component release notes must contain only
the component, patch version, fixes, candidate SHA and applicable verification
and qualification evidence.

Future design and implementation must prove single-component selection, patch
version handling, affected-component-only Verification/Software Assurance/
Trusted Delivery, release/deployment/rollback evidence and qualified runner
routing. This is a Platform Evolution backlog item only; it authorizes neither
a Component Release nor changes to Platform Release execution.

## Backlog detail: Technical Debt Engine integration

Integrate DJConnect as a reference consumer of the standalone **Technical Debt
Engine** (TDE), whose canonical CLI is `tde`. TDE is an independent,
platform- and project-agnostic product and must live in its own repository
(suggested: `pcvantol/technical-debt-engine`; final name remains a product
initialization decision). DJConnect must not contain, copy or reimplement TDE
runtime, analyzers, schemas, qualification logic, packaging or release process.

DJConnect's future integration layer may discover repositories through
`REPOSITORY_OWNERSHIP.md`, invoke only an immutably pinned released TDE CLI,
validate TDE schema/version/repository identity/candidate SHA, apply
DJConnect-specific configuration and exclusions, retain per-repository evidence
and aggregate platform baselines and trends. Generation 1 integration is
informational: observe, baseline, report, compare and trend only. It must keep
release gating disabled and preserve Software Assurance and Trusted Delivery.

The standalone product must first establish its own vision, architecture,
roadmap, backlog, governance, CLI and versioned evidence contracts, adapter and
test strategy, packaging/release strategy and prompt index. Its first released
CLI needs supported language adapters, reproducible trusted distribution and
documented exit codes. DJConnect integration may begin only after that release;
it must never depend on unreleased local TDE source.

Future work must reject stale, candidate-SHA-mismatched, incomplete,
unsupported-schema or untrusted-version evidence. Optional regression-aware
release gates require a separate future governance and qualification decision.
This is a Platform Evolution backlog item only; it authorizes neither creation
of the TDE repository nor any TDE/DJConnect implementation.

## Backlog detail: Privacy Assessment

Establish a Generation 2 Platform Evolution privacy assessment capability for
DJConnect’s profile, Music DNA, Ask DJ history, shared-device, diagnostics,
release and evidence surfaces. The initial capability remains DJConnect-owned:
it inventories data flows, checks documented privacy boundaries, records
findings as informational evidence and feeds Software Assurance without
creating release gates. A future standalone assessment engine is a separate
product decision and is not authorized by this backlog item.
