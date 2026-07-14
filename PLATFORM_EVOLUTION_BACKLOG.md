# DJConnect Platform Evolution Backlog

**Owner:** Platform Evolution
**Status:** Canonical active backlog

Platform Evolution is supporting work, not the primary roadmap. Items enter
this backlog only after objective evidence shows that product delivery, safety
or governed operations are constrained.

| Initiative | Priority | Status | Dependencies | Promotion path |
| --- | --- | --- | --- | --- |
| Component Release Mode | P2 | Backlog | release evidence and current manifest model | bounded architecture review if contracts change |
| GitHub Actions retention policy | P1 | Backlog | Repository Ownership integration, explicit protected-evidence metadata and governance review | governed workflow change after approved design |
| Public distribution: Apple | P1 | Backlog | qualified Internal Release consumers and explicit authorization | release-operational work |
| Public distribution: Windows | P1 | Backlog | qualified Internal Release consumers and explicit authorization | release-operational work |
| Public HACS distribution | P1 | Backlog | fresh candidate and release authorization | release-operational work |
| Firmware OTA publication and staged rollback | P1 | Backlog | manifest-bound consumer qualification | release-operational work |
| Website production deployment and announcements | P1 | Backlog | approved manifest and consumer qualification | release-operational work |
| Technical Debt Engine integration | P1 | Backlog | released standalone TDE CLI, stable evidence schema, trusted distribution and Software Assurance compatibility | Platform Evolution integration after external product initialization |
| SBOM generation | P2 | Backlog | Trusted Delivery compatibility assessment | scoped Platform Evolution proposal |
| Release Health and observability | P2 | Backlog | operational release evidence | scoped Platform Evolution proposal |
| Platform diagnostics | P3 | Backlog | privacy and redaction review | scoped Platform Evolution proposal |
| Future governance improvements | P3 | Backlog | governance evidence | governance review |

## Current operational work

Platform Release 3.3 Internal is **Operational** but remains blocked. It needs
a fresh exact-SHA candidate manifest, qualified manifest-bound deployment and
smoke consumers for every required target, and explicit dispatch authorization.
It is documented in `docs/release/PLATFORM_RELEASE_MANAGEMENT_SUMMARY.md`; it
does not become a fourth program.

## Backlog detail: GitHub Actions retention policy

Design one centrally governed, fail-closed retention capability for workflow
runs, artifacts, safe orphan caches and historical branch reconciliation. It
must use configurable `FEATURE_BRANCH` (2), `RELEASE_BRANCH` (5), `MAIN` (20)
and non-deleting `PROTECTED_EVIDENCE` profiles; discover participating
repositories through `REPOSITORY_OWNERSHIP.md`; and preserve release, dry-run,
qualification, certification, Software Assurance, Trusted Delivery, incident,
rollback and explicitly protected audit evidence through machine-readable
metadata rather than names.

Future design and implementation must cover push, closed pull request, branch
deletion, scheduled and manual reconciliation, idempotence, fork-safe
least-privilege execution, objective cleanup evidence and a fail-closed retain
state whenever protection cannot be determined. This is a Platform Evolution
backlog item only; it authorizes neither workflow changes nor deletion.

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
