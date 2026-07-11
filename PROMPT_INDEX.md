# DJConnect Verification Prompt Index

Status: canonical prompt navigation

This index tells clean Codex and AI-agent sessions which verification prompt is
active, what came before it and which evidence proves status. Chat history is
not required.

## Active Next Phase

The Software Assurance Platform architecture sprint has completed with decision
`SOFTWARE_ASSURANCE_PLATFORM_ARCHITECTURE_COMPLETE`. Software Assurance
implementation is intentionally deferred until an explicit post-baseline
implementation prompt starts that work.

The Architecture Closure Review completed on 2026-07-11 with decision
`ARCHITECTURE_FROZEN`.

Platform Baseline v1.0 has not yet been certified. The current platform
decision is `PLATFORM_BASELINE_V1_NOT_CERTIFIED`. The active engineering
objective is Platform Qualification, and the active next verification work
remains the Phase 10E-R2 follow-up backlog.

Phase 9V rerun has qualified the Verification Platform using the dedicated
local Home Assistant verification lab. The canonical planner selected the
approved first Profile scenario set, exact-SHA CI passed, the `ha-profile` lab
was qualified, and `PROFILE-001` through `PROFILE-005` executed successfully
through the Home Assistant adapter with persisted evidence.

Phase 9V qualifies the Verification Platform. It does not qualify broad
DJConnect Home Assistant backend scenario coverage.

The Verification Platform runtime is versioned as `1.0.0` and can be released
as a generic Docker image containing only reusable engine components. Runtime
identity and total execution time are recorded in run metadata and summaries;
scenario catalogs, product source, lab state, secrets and evidence remain
external to the image.

Phase 10 implemented and qualified the thin Apple Verification Adapter with
mock/unit evidence. Live Apple simulator/device execution was explicitly
skipped because no prepared Apple target JSON and app artifact were configured.

Phase 10E executed the mandatory Apple Runtime Qualification gate first and
returned `APPLE_RUNTIME_QUALIFICATION_BLOCKED`. Broad Apple scenario execution
did not start. Phase 10E-R remediated the local Apple runtime path and returned
`APPLE_RUNTIME_QUALIFIED` for the selected iOS 26.4 simulator.

The Apple runtime prerequisite was later tightened: verification now has to run
the Apple toolchain maintenance gate, keep the iOS simulator platform current
through Xcode, and qualify only the latest eligible stable iOS simulator
runtime by default. The latest Phase 10E-R2 follow-up rerun passed toolchain
maintenance with Xcode 26.6 and stable iOS 26.5 available. It also resolved
the committed `djconnect-app` clean-clone fix, latest-stable
DerivedData/target JSON configuration and XCTest healthcheck configuration.
Runtime qualification historically returned
`APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED` before live mutation because App
Store/TestFlight release signing expectations were not available in the local
keychain/provisioning profile inventory. That distribution-signing path is now
explicitly deferred until release v1.0 readiness and is non-blocking for current
platform verification.

Phase 10E-R2 is closed in this branch with the Xcode account/development-signing
path available for current platform verification. Continue Phase 10E retry with
the latest eligible simulator target and prepared XCTest healthcheck; App
Store/TestFlight distribution signing remains a release-v1.0 readiness
follow-up.

## Deferred Implementation Epics

### Software Assurance Platform

Status:

```text
ARCHITECTURE_COMPLETE
```

Implementation:

```text
DEFERRED
```

Prerequisite:

```text
PLATFORM_BASELINE_V1_CERTIFIED
```

Implementation sequence:

1. [Prompt 1: CI Governance Foundation](prompts/deferred/software_assurance/PROMPT_01_CI_GOVERNANCE_FOUNDATION.md)
2. [Prompt 2: Cross-Repository Workflow Harmonization](prompts/deferred/software_assurance/PROMPT_02_CROSS_REPOSITORY_WORKFLOW_HARMONIZATION.md)
3. [Prompt 3: Trusted Delivery Platform](prompts/deferred/software_assurance/PROMPT_03_TRUSTED_DELIVERY_PLATFORM.md)
4. [Prompt 4: Trusted Delivery Certification](prompts/deferred/software_assurance/PROMPT_04_TRUSTED_DELIVERY_CERTIFICATION.md)

Current state:

```text
Waiting for Platform Baseline certification.
```

Canonical registration:

- `SOFTWARE_ASSURANCE_IMPLEMENTATION.md`
- `prompts/deferred/software_assurance/`

The existence of these prompts does not authorize implementation. Future AI
agents must verify that Platform Baseline v1.0 is certified before beginning
Prompt 1.

Use this clean-session prompt:

```text
Read BOOTSTRAP_CODEX_VERIFICATION.md and resolve the Phase 10E-R2 follow-up backlog items from PROMPT_INDEX.md.
```

## Prompt Table

| Phase | Title | Status | Canonical prompt path | Required predecessor | Output/report path | Merge requirement | Next phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Verification Vision | Complete | Historical chat prompt; reconstructed in docs | Platform Foundation | `docs/verification/00_VERIFICATION_VISION.md` | Merged to `main` | Phase 1 |
| 1 | Verification Architecture | Complete | Historical chat prompt; reconstructed in docs | Phase 0 | `docs/verification/01_VERIFICATION_ARCHITECTURE.md` | Merged to `main` | Phase 2 |
| 2 | Scenario Schema | Complete | Historical chat prompt; reconstructed in docs | Phase 1 | `docs/verification/02_SCENARIO_SCHEMA.md` | Merged to `main` | Phase 3 |
| 3 | Scenario Catalog | Complete | Historical chat prompt; reconstructed in docs | Phase 2 | `docs/verification/03_SCENARIO_CATALOG.md` | Merged to `main` | Phase 3A |
| 3A | Verification Matrix | Complete | Historical chat prompt; reconstructed in docs | Phase 3 | `docs/verification/03A_VERIFICATION_MATRIX.md` | Merged to `main` | Phase 4 |
| 4 | Verification Harness | Complete | Historical chat prompt; reconstructed in docs | Phase 3A | `docs/verification/04_VERIFICATION_HARNESS.md` | Merged to `main` | Verification Core |
| 6 | Technical Design Reconstruction | Complete | Historical chat prompt; reconstructed in docs | Platform Baseline | Technical design docs and `docs/verification/07_IMPLEMENTATION_GAP_ANALYSIS.md` references | Merged to `main` | Phase 7 |
| 7 | Platform Implementation Gap Analysis | Complete | Historical chat prompt; reconstructed in docs | Phase 6 | `docs/verification/07_IMPLEMENTATION_GAP_ANALYSIS.md` | Merged to `main` | Phase 8 |
| 8 | Verification Execution Environment | Complete | Historical chat prompt; reconstructed in docs | Phase 7 | `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md` | Merged to `main` | Phase 8A |
| 8A | Verification Data Framework | Complete | Historical chat prompt; reconstructed in docs | Phase 8 | `docs/verification/08A_VERIFICATION_DATA_FRAMEWORK.md` | Merged to `main` | Phase 8B |
| 8B | Verification Modes And Policies | Complete | Historical chat prompt; reconstructed in docs | Phase 8A | `docs/verification/08B_VERIFICATION_MODES.md`; `docs/verification/08B_VERIFICATION_POLICIES.md` | Merged to `main` | Phase 8C |
| 8C | Verification Planning Engine | Complete | Historical chat prompt; reconstructed in docs | Phase 8B | `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md` | Merged to `main` | Phase 9 |
| 9 | Home Assistant Verification Adapter | Complete | Historical chat prompt; reconstructed in docs | Phase 8C | `docs/verification/09_HOME_ASSISTANT_VERIFICATION_ADAPTER.md`; `docs/verification/reports/PHASE_09_HOME_ASSISTANT_ADAPTER_COMPLETION.md` | Merged to `main` | Phase 9V |
| 9V | Verification Platform Qualification | Not qualified | Historical chat prompt; reconstructed in report | Phase 9 | `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION.md`; `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`; `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md` | Reports committed to `main` | Phase 9R |
| 9R | Verification Platform Qualification Remediation | Remediated with external prerequisites | `prompts/verification/PHASE_09R_QUALIFICATION_REMEDIATION.md` | Phase 9V not qualified | `docs/verification/reports/PHASE_09R_QUALIFICATION_REMEDIATION.md` | PR #63 branch `docs/phase-09r-remediation-prompt-v2` | Phase 9L |
| 9L | Local HA Verification Lab | Not qualified | `prompts/verification/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md` | Phase 9R | `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`; evidence `artifacts/verification/evidence/phase-09l-local-ha-lab-20260710T1450Z/` | Merge Phase 9L implementation before remediation or continue same PR if still open | Phase 9L-R |
| 9L-R | Local HA Lab Remediation | Not qualified - external Docker prerequisite | `prompts/verification/PHASE_09L_R_LOCAL_HA_LAB_REMEDIATION.md` | Phase 9L not qualified | Updated `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`; evidence `artifacts/verification/evidence/phase-09l-r-local-ha-lab-20260710T153557Z/`; `docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.md` | PR #67 branch `codex/phase-09l-r-local-ha-lab-remediation` | Phase 9L-R2 |
| 9L-R2 | Docker Runtime Remediation And Local HA Lab Qualification | Not qualified - Docker Desktop container-start blocker | `prompts/verification/PHASE_09L_R2_DOCKER_RUNTIME_REMEDIATION.md` | Phase 9L-R not qualified, modular lab validation complete | Updated `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md` | New remediation branch | Phase 9L-R3 |
| 9L-R3 | Docker Desktop Repair And Local HA Lab Qualification | Not qualified - unstable Docker Desktop container-start behavior | Historical chat prompt; superseded by `prompts/verification/PHASE_09L_R4_DOCKER_DESKTOP_CLEAN_RUNTIME_REPAIR.md` | Phase 9L-R2 not qualified; no-mount Docker probe cannot start | Updated `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md` | PR #68 branch `phase-09l-r2-docker-runtime-remediation` | Phase 9L-R4 |
| 9L-R4 | Docker Desktop Clean Runtime Repair And Local HA Lab Qualification | Not qualified - stable Docker gate failed on probe 1 | `prompts/verification/PHASE_09L_R4_DOCKER_DESKTOP_CLEAN_RUNTIME_REPAIR.md` | Phase 9L-R3 not qualified; repeated container starts are unstable | Updated `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md` | New remediation branch | Phase 9L-R5 |
| 9L-R5 | Docker Desktop Operator Reset And Local HA Lab Qualification | Not qualified - bind-mount probe remains in Created | `prompts/verification/PHASE_09L_R5_DOCKER_DESKTOP_OPERATOR_RESET.md` | Phase 9L-R4 not qualified; no-mount probe remains in Created | Updated `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md` | PR #69 branch `phase-09l-r4-docker-desktop-clean-runtime-repair` | Phase 9L-R6 |
| 9L-R6 | Docker Desktop Documents Permission And Local HA Lab Qualification | Qualified | `prompts/verification/PHASE_09L_R6_DOCKER_DESKTOP_DOCUMENTS_PERMISSION.md` | Phase 9L-R5 not qualified; Docker Desktop bind mounts blocked by macOS Documents permission | `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`; evidence `artifacts/verification/evidence/djv-20260711T080007Z-69941deb88/` | PR #69 branch `phase-09l-r4-docker-desktop-clean-runtime-repair` | Phase 9V rerun |
| 9V rerun | Verification Platform Qualification Rerun | Qualified | `prompts/verification/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION_RERUN.md` | Phase 9L-R6 qualified the local HA lab | `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION_RERUN.md`; evidence `artifacts/verification/evidence/djv-20260711T091949Z-a0c9568562/` | Must merge before Phase 9E | Phase 9E |
| 9E | Home Assistant Scenario Coverage Expansion | Not qualified | `prompts/verification/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE_EXPANSION.md` | Phase 9V rerun qualified the Verification Platform | `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.md`; `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.json` | New PR; merge only after Phase 9E completion protocol | Phase 9E-R |
| 9E-R | Home Assistant Scenario Coverage Remediation | Qualified with non-blocking warnings | `prompts/verification/PHASE_09E_R_HOME_ASSISTANT_SCENARIO_COVERAGE_REMEDIATION.md` | Phase 9E returned `HOME_ASSISTANT_BACKEND_NOT_QUALIFIED` | Updated `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.md`; updated JSON report | New PR or continue Phase 9E PR if still open | Phase 10 |
| 10 | Apple Verification Adapter | Qualified with live runtime skipped | `prompts/verification/PHASE_10_APPLE_VERIFICATION_ADAPTER.md` | Phase 9E-R returned `HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS` with warnings explicitly non-blocking for Apple work | `docs/verification/reports/PHASE_10_APPLE_ADAPTER_COMPLETION.md` | New PR; merge only after Phase 10 completion protocol | Phase 10E |
| 10E | Apple Scenario Coverage Expansion | Blocked - runtime qualification missing local configuration | `prompts/verification/PHASE_10E_APPLE_SCENARIO_COVERAGE_EXPANSION.md` | Phase 10 returned `APPLE_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED` | `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md`; evidence `artifacts/verification/evidence/apple10e-20260711T114536Z-417af0454b/` | New PR; do not merge as Apple coverage qualified | Phase 10E-R |
| 10E-R | Apple Runtime Qualification Remediation | Qualified on older selected runtime | `prompts/verification/PHASE_10E_R_APPLE_RUNTIME_QUALIFICATION_REMEDIATION.md` | Phase 10E returned `APPLE_RUNTIME_QUALIFICATION_BLOCKED` | `docs/verification/reports/PHASE_10E_R_APPLE_RUNTIME_QUALIFICATION_REMEDIATION.md`; evidence `artifacts/verification/evidence/apple10e-20260711T115656Z-4cea94c38f/` | Continue Phase 10E PR if still open | Phase 10E-R2 |
| 10E-R2 | Apple Latest Runtime Qualification Remediation | Closed - App Store distribution deferred | `prompts/verification/PHASE_10E_R2_APPLE_LATEST_RUNTIME_QUALIFICATION_REMEDIATION.md` | Latest-runtime rule requires Xcode/iOS simulator maintenance and stable iOS 26.5 qualification | `docs/verification/reports/PHASE_10E_R2_APPLE_LATEST_RUNTIME_QUALIFICATION.md`; evidence `artifacts/verification/evidence/appletoolchain-20260711T183955Z-d4d3276dc7/`; blocked historical evidence `artifacts/verification/evidence/apple10e-20260711T184303Z-61c57ca54d/`; VPB-037 resolved for current platform verification | Continue Phase 10E PR if still open; App Store/TestFlight signing deferred to release v1.0 readiness | Phase 10E retry |
| 10E retry | Apple Scenario Coverage Expansion After Runtime Qualification | Ready for development-signed platform verification retry | `prompts/verification/PHASE_10E_APPLE_SCENARIO_COVERAGE_EXPANSION.md` | Phase 10E-R2 provides Xcode account/development signing, latest simulator target and XCTest healthcheck configuration | Future updated Phase 10E coverage report | Continue Phase 10E PR if still open | Phase 11 |
| 11+ | Additional Platform Adapters | Future | To be generated after Apple coverage work | Phase 10E and roadmap review | Future adapter reports | Future PRs | Future adapter qualification |

## Status Rules

- `Complete` means repository evidence exists and the work has been merged or
  committed as a completed artifact.
- `Not qualified` means the phase ran and produced a negative decision.
- `Remediated with external prerequisites` means blockers were converted into
  checks or explicit prerequisites, but the platform is not yet qualified.
- `Closed - stable runtime config follow-ups` means the phase executed and
  produced a repository decision, but the next qualification attempt is
  intentionally deferred to explicit follow-up backlog items.
- `Active next phase` means a clean session should execute that prompt.
- `Qualified` means repository evidence exists and the phase decision permits
  the next phase to start after merge.
- `Not qualified - external Docker prerequisite` means remediation code
  improved framework behavior, including lab-only HA auth bootstrap and modular
  lab composition, but live lab qualification is blocked by local Docker runtime
  prerequisites outside repository code.
- `Blocked` means do not start the phase until the predecessor result changes.
- `Not qualified` means the phase produced required artifacts but still has
  blocking prerequisites.

Do not mark Phase 9L complete until repository evidence includes its local lab
qualification report and the final result line.

Exact clean-session command for the current follow-up gate:

```text
Read BOOTSTRAP_CODEX_VERIFICATION.md and resolve the Phase 10E-R2 follow-up backlog items from PROMPT_INDEX.md.
```
