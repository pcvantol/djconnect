# Platform Release Engineering

Status: canonical navigation  
Scope owner: `pcvantol/djconnect`

Platform Release Engineering is the reusable, platform-wide release control
model. It coordinates participating repositories without making a repository
release process the source of truth.

## Canonical documents

- `PLATFORM_RELEASE_ARCHITECTURE.md` is the frozen Generation 1 release
  architecture: versioning, lifecycle, qualification, certification, dry-run,
  rollback, evidence and orchestration.
- `PLATFORM_RELEASE_ROADMAP.md` sequences the later implementation prompts.
- `PROMPT_01_RELEASE_ARCHITECTURE_COMPLETION.md` records the architecture-phase
  outcome.
- `RUNTIME.md` documents the planner, fail-closed workflow-orchestration gate
  and non-production rehearsal path.
- `PLATFORM_RELEASE_RUNTIME_ARCHITECTURE.md` freezes the separation between the
  Platform Release Runtime (orchestration) and GitHub Actions (execution).
- `APPLE_RELEASE_ARCHITECTURE.md` defines the canonical two-artifact Apple
  model for iPhone, iPad, Apple Watch and macOS.
- `PROMPT_02_RELEASE_ORCHESTRATOR_COMPLETION.md` records the implementation
  outcome and qualification evidence.
- `PLATFORM_RELEASE_QUALIFICATION.md` records the completed Generation 1
  capability qualification and its objective decision.
- `PLATFORM_RELEASE_MANAGEMENT_SUMMARY.md` records the current Platform 3.3
  release position, including the distinction between historical dry-run
  evidence and the exact-SHA evidence required for the current `main` commits.
- `PLATFORM_RELEASE_COMPLIANCE_REPORT.md`,
  `PLATFORM_RELEASE_OPERATIONAL_READINESS.md` and
  `PLATFORM_RELEASE_GAP_ANALYSIS.md` record the supporting compliance,
  operational and future-work evidence.
- `PROMPT_04_PLATFORM_RELEASE_QUALIFICATION_COMPLETION.md` records the
  formal Generation 1 qualification decision.
- `RUNNER_ARCHITECTURE.md` and `RUNNER_POLICY.md` define the corrected
  GitHub Actions build locations and the narrow self-hosted runner boundary.
  `RUNNER_TOOLING_CURRENCY_STANDARD.md` defines how hosted and self-hosted
  execution tooling remains current. `MACOS_DEVELOPMENT_HOST_BOOTSTRAP.md`
  defines repeatable bootstrap of a replacement macOS development host.
- `DEPLOYMENT_ARCHITECTURE.md` defines artifact-only deployment targets.
- `POST_DEPLOYMENT_SMOKE_TEST_POLICY.md` and
  `POST_DEPLOYMENT_SMOKE_EVIDENCE_SCHEMA.md` define the bounded,
  non-destructive post-deployment operational smoke decision and its redacted
  evidence contract.
- `VERIFICATION_VS_RELEASE.md` defines the boundary between runtime/hardware
  proof and release production.
- `PLATFORM_RELEASE_OPERATIONAL_MODEL.md` defines Codex orchestration and
  GitHub Actions build execution.
- `RELEASE_ARCHITECTURE_CORRECTIONS_COMPLETION.md` records the 2026-07-13
  correction decision and its evidence.
- `RUNNER_QUALIFICATION_REPORT.md`, `RUNNER_DEPLOYMENT_MATRIX.md` and
  `NATIVE_RUNNER_ALIGNMENT_COMPLETION.md` record the final Apple/Windows
  native runner alignment evidence.
- `PLATFORM_RELEASE_RUNTIME_EXECUTION.md`,
  `PLATFORM_RELEASE_OPERATIONAL_RUNTIME.md`,
  `PLATFORM_RELEASE_EXECUTION_REPORT.md` and
  `PLATFORM_RELEASE_DEPLOYMENT_EVIDENCE.md` record the controlled operational
  runtime and its representative non-production qualification.

The architecture consumes repository membership from
[`REPOSITORY_OWNERSHIP.md`](../../REPOSITORY_OWNERSHIP.md). It consumes
behavioural evidence from the Verification Platform and assurance evidence
from the Software Assurance Platform. It does not replace either system.

## Boundaries

This directory defines release architecture and controlled runtime contracts.
It does not contain repository version files, credentials or product artifacts.

The Verification Runtime has its own independent product lifecycle. Its
compatibility evidence may be consumed by a platform release, but a runtime
release is not automatically a DJConnect platform release.
