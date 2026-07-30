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
| Capability-profile assessment follow-up | P2 | Completed | PR #539 / `QUALIFICATION_REGISTER.md`; current CMB-05/CMB-06/CMB-07/CMB-09/CMB-12 evidence | `GO_CAPABILITY_PROFILE_FOLLOW_UP_RECONCILED`; seven original items reconciled to six unique active items; no product implementation authorization |
| Canonical governance Version 2.2 alignment | P0 | Historical | merged governance evidence | retained governance evidence only |
| Component Release Mode | P2 | Implemented — Finalization pending | `docs/release/COMPONENT_RELEASE_MODE_ASSESSMENT.md`, `docs/release/COMPONENT_RELEASE_QUALIFICATION_ASSESSMENT.md`, `docs/release/COMPONENT_RELEASE_SCOPE_REFINEMENT.md` and `docs/release/COMPONENT_RELEASE_SELECTION_EVIDENCE_CLOSURE_IMPLEMENTATION.md` | `GO_COMPONENT_RELEASE_SELECTION_EVIDENCE_CLOSURE_IMPLEMENTED`; canonical profiles are now deterministically selected and fail-closed against exact closure evidence. Component execution and release remain unauthorized pending profile-specific execute qualification. |
| GitHub Actions retention and evidence preservation (`TD-GITHUB-001`) | P1 | Completed | PRs #547–#554; `docs/software_assurance/EVIDENCE_PRESERVATION_IMPLEMENTATION_REPORT.md`; durable record for `f6e346018dadaccc8457dac7b5cadd19a03b80e7` | `GO_TD_GITHUB_001_QUALIFIED`; redacted, immutable release-asset evidence is published and read back fail-closed |
| Platform Dependency Governance conformance | P1 | Completed | `docs/software_assurance/PLATFORM_DEPENDENCY_GOVERNANCE_POLICY.md`; merged Dependabot rollout and successor finalization evidence | GitHub-native version-update conformance is complete; TDE 1.1.1 supplies separate canonical non-blocking observe evidence and does not replace native security controls |
| Public distribution: Apple | P1 | Planned | qualified Internal Release consumers and explicit authorization | release-operational work |
| Public distribution: Windows | P1 | Planned | qualified Internal Release consumers and explicit authorization | release-operational work |
| Public HACS distribution | P1 | Planned | fresh candidate and release authorization | release-operational work |
| Client Connectivity & Resilience qualification | P1 | Assessed | `docs/technical/CLIENT_CONNECTIVITY_RESILIENCE_ARCHITECTURE.md`, Public Release Readiness Assessment | `GO_CLIENT_CONNECTIVITY_PARTIALLY_QUALIFIED`; bounded external HTTP and resilience evidence remains required before Public Release Readiness, with no Runtime, transport or client implementation authorization |
| HACS 3.3.0 release visibility (`HACS-3.3.0-001`) | P1 | Planned | verify release/tag metadata, HACS cache/index discovery and update presentation | bounded distribution investigation |
| HACS pull-request validation reliability (`HACS-CI-PR-REF-001`) | P1 | Assessed | `docs/software_assurance/HACS_PR_VALIDATION_RELIABILITY_ASSESSMENT.md`; retained PR #461 head/merge loading failures, PR #459/#500 success and `main` success | HACS is execution-required engineering evidence but not release-authoritative; no workflow, Runtime, qualification, gate or action-pinning change |
| Home Assistant DJConnect HTTP-route registration (`HA-HTTP-ROUTE-3.3.0-001`) | P0 | Historical | reconciled incident evidence | retained incident evidence only |
| Firmware OTA publication and staged rollback | P1 | Planned | manifest-bound consumer qualification | release-operational work |
| ESPHome firmware platform adoption | P2 | Planned | ADR-0017; pinned community baseline, board-specific qualification and existing firmware distribution evidence | board-by-board Platform Adoption; no Runtime, pairing, renderer or HA-integration change |
| Website production deployment and announcements | P1 | Planned | approved manifest and consumer qualification | release-operational work |
| Technical Debt Engine 1.1.1 consumer rollout | P1 | Completed | PR #583 and current `tde-observe.yml` evidence across the selected source consumers | Canonical public runtime and CLI provide observe-only `code_size`, `complexity`, `coverage` and `dependency_health` evidence; no release or merge gate |
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

## Backlog detail: ESPHome firmware platform adoption

**Owner:** `pcvantol/djconnect-esp32` source; `pcvantol/djconnect-firmware`
distribution.

**Priority:** P2
**Status:** Planned

Implement the accepted ESPHome Firmware Platform Architecture board by board:
record an attributed pinned community baseline; compose DJConnect packages and
components; qualify boot/display, input, audio where applicable, memory,
networking/provisioning, pairing, Runtime connection, device UI, OTA and reboot
recovery; then publish through the existing beta/stable manifest path. The
Device Installer consumes manifests and remains firmware-agnostic.

This backlog item authorizes no change to the Runtime, pairing, renderer
contracts, transport protocols, capabilities or Home Assistant integration.

## Backlog detail: GitHub Actions retention and evidence preservation

**Risk ID:** `TD-GITHUB-001`

**Owner:** Platform Evolution

**Priority:** P1
**Status:** Assessed / qualification pending

The canonical evidence inventory and preservation classes are recorded in
`docs/software_assurance/TD_GITHUB_001_RETENTION_EVIDENCE_ASSESSMENT.md`.
Existing Actions cleanup and Golden-report retention remain unchanged. The
remaining question is whether every decision-bound record is independently,
redactedly and immutably durable; no archive, export, cleanup-policy or
workflow change is authorized.

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

**Assessment status:** `GO_COMPONENT_RELEASE_MODE_PARTIALLY_QUALIFIED`

The canonical component inventory, ownership, release boundaries, version
posture and minimum verification evidence are recorded in
`docs/release/COMPONENT_RELEASE_MODE_ASSESSMENT.md`. Existing repository-local
patch releases remain bounded by the platform `major.minor` train. The
completed Component Release Qualification found that a generic selected-source
and dependency/evidence closure is not yet represented by the current Runtime;
only a future Scope Refinement remains.

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

Any future refinement and implementation must prove single-component selection,
patch version handling, affected-component-only Verification/Software
Assurance/Trusted Delivery, release/deployment/rollback evidence and qualified
runner routing. This is a Platform Evolution backlog item only; it authorizes
neither a Component Release nor changes to Platform Release execution.

## Historical delivery: Technical Debt Engine 1.1.1 consumer rollout

DJConnect consumes the standalone **Technical Debt Engine** (TDE) as an
independent public product. The selected source repositories use the exact
published `technical-debt-engine-runtime==1.1.1` and the public `tde` CLI;
DJConnect does not contain, copy or own TDE runtime, analyzers, schemas,
qualification logic, packaging or release lifecycle.

The completed rollout produces repository-scoped, artifact-backed standard
assessments for `code_size`, `complexity`, `coverage` and `dependency_health`.
It is observe-only and non-blocking: it neither replaces Dependabot,
dependency audit, Software Assurance, Trusted Delivery or Verification nor
becomes a merge, release or product gate. Future changes to TDE itself remain
owned by its repository. Any future change from observation to enforcement
would require a separate DJConnect governance and qualification decision.

## Backlog detail: Privacy Assessment

Establish a Generation 2 Platform Evolution privacy assessment capability for
DJConnect’s profile, Music DNA, Ask DJ history, shared-device, diagnostics,
release and evidence surfaces. The initial capability remains DJConnect-owned:
it inventories data flows, checks documented privacy boundaries, records
findings as informational evidence and feeds Software Assurance without
creating release gates. A future standalone assessment engine is a separate
product decision and is not authorized by this backlog item.
