# DJConnect Verification Prompt Index

Status: canonical prompt navigation

## Generation 2 navigation

`ROADMAP_INDEX.md` is the canonical navigation for the three Generation 2
engineering programs. This Prompt Index remains the source only for approved
execution prompts; it does not own product or Platform Evolution prioritization.
Historical Software Assurance and release prompts remain evidence records; they
do not become active without a new explicitly approved prompt.
`ENGINEERING_PLATFORM_GENERATION_1_COMPLETION_REPORT.md` records the completed
Generation 1 program and the transition to Generation 2.

This index tells clean Codex and AI-agent sessions which verification prompt is
active, what came before it and which evidence proves status. Chat history is
not required.

## Canonical Prompt Governance

Every canonical prompt is exactly one engineering increment and every
increment terminates with exactly one reviewable pull request. Merge is a
separate explicit decision. Prompts progress through `Draft`, `Active`,
`Completed`, `Deprecated` and `Archived` states. During execution, exactly one
prompt may be `Active`; no prompt may overlap or compete with it. A following
prompt stays `Draft` until the preceding increment has its reviewable pull
request.

The Engineering Method is defined in `docs/meta/ENGINEERING_PLAYBOOK.md` and
may be changed only by a dedicated Engineering Governance prompt.

The operational repository-driven method is `ENGINEERING_METHOD.md`.
`BOOTSTRAP.md` defines the current-state reading order and
`docs/history/prompts/` retains immutable historical records only.

Every prompt begins with repository synchronization, current-main verification,
previous-pull-request verification, post-merge state classification and rolling
state reconciliation when required before this index, repository state or
planning is read.

## Prompt Registry

| Prompt | Lifecycle | Coherent objective | Branch | Completion evidence |
| --- | --- | --- | --- | --- |
| Engineering Workflow Alignment | Completed | Establish the mandatory canonical AI-native engineering workflow without implementation changes. | `codex/engineering-workflow-alignment` | `docs/meta/ENGINEERING_WORKFLOW_ALIGNMENT_COMPLETION.md`; PR [#107](https://github.com/pcvantol/djconnect/pull/107) |
| Engineering Method V2 Governance Alignment | Completed | Establish repository-driven V2 onboarding, reality verification, prompt archival and hygiene without implementation or architecture changes. | `codex/engineering-method-v2` | `docs/history/prompts/2026-07-14-engineering-method-v2.md`; PR [#114](https://github.com/pcvantol/djconnect/pull/114) |
| Engineering Method V2.3 Repository Synchronization | Completed | Make synchronized current main and current-main verification mandatory before repository reading and planning; no implementation or architecture changes. | `codex/engineering-method-v2-3` | `docs/history/prompts/2026-07-14-engineering-method-v2-3.md`; PR [#118](https://github.com/pcvantol/djconnect/pull/118) |
| Post-Merge Engineering State Reconciliation | Completed / merged reconciled | Establish explicit post-merge lifecycle and reconcile the merged V2.3 rolling-state transition; no implementation or architecture changes. | `codex/post-merge-engineering-state-reconciliation` | `docs/history/prompts/2026-07-15-post-merge-engineering-state-reconciliation.md`; PR [#125](https://github.com/pcvantol/djconnect/pull/125) |
| Repository Governance Rollout Planning | Completed / merged reconciled | Verify canonical governance and repository maturity; align the maintainer-selected Version 2.2 decision value. | `codex/repository-governance-rollout` | `docs/governance/REPOSITORY_GOVERNANCE_ROLLOUT.md`; PR [#126](https://github.com/pcvantol/djconnect/pull/126) |
| Repository Governance Rollout Planning Completion | Completed / merged reconciled / archived | Establish the Version 2.2 adoption queue. | `codex/repository-governance-rollout-completion` | `docs/history/prompts/2026-07-15-repository-governance-rollout-completion.md`; PR [#127](https://github.com/pcvantol/djconnect/pull/127) |
| Repository Governance Audit | Completed / merged reconciled / archived | Audit all nine merged Version 2.2 repository adoptions. | `codex/repository-governance-audit` | `docs/governance/REPOSITORY_GOVERNANCE_AUDIT_V2_2.md`; PR [#128](https://github.com/pcvantol/djconnect/pull/128) |
| Rolling Records Reconciliation | Completed / merged reconciled / archived | Reconciled central rolling records after the completed governance rollout. | `codex/reconcile-governance-rolling-records` | `docs/history/prompts/2026-07-15-platform-governance-rolling-records-reconciliation.md`; PR [#129](https://github.com/pcvantol/djconnect/pull/129) |
| macOS Runner-Host Bootstrap Pre-Merge Preparation | Completed / merged reconciled / archived | Corrected PR #144 scope description, identified its temporary candidate workflow references and recorded the post-merge repin sequence without changing behaviour. | `codex/prepare-macos-runner-bootstrap-merge` | `docs/release/MACOS_RUNNER_BOOTSTRAP_MERGE_READINESS.md`; PR [#146](https://github.com/pcvantol/djconnect/pull/146) |
| macOS Runner-Host Bootstrap Post-Merge Repin | Completed / merged reconciled / archived | Repinned the eight governance callers and reusable-workflow policy checkout to immutable merged-main evidence. | `codex/repin-macos-bootstrap-main` | `docs/history/prompts/2026-07-16-macos-runner-bootstrap-postmerge-repin.md`; PR [#147](https://github.com/pcvantol/djconnect/pull/147) |
| Platform Release Observatory Design | Completed / merged reconciled / archived | Define the canonical local-only, read-only Observatory and register its bounded Platform Evolution delivery backlog. | `codex/platform-release-observatory-design` | `docs/history/prompts/2026-07-17-platform-release-observatory-design.md`; PR [#148](https://github.com/pcvantol/djconnect/pull/148) |
| Observatory Post-Merge Rolling-Records Reconciliation | Completed / merged reconciled / archived | Reconcile current rolling records after PR #148; record that the PR #144 branch is already removed and preserve the unrelated non-main Windows-runner branch for separate review. | `codex/reconcile-observatory-rolling-records` | `docs/history/prompts/2026-07-17-observatory-rolling-records-reconciliation.md`; PR [#154](https://github.com/pcvantol/djconnect/pull/154) |
| Observatory Hygiene Merge Reconciliation | Completed / merged reconciled / archived | Reconcile rolling records after merged PR #154 and record deletion of the reviewed obsolete Windows-runner branch. | `codex/reconcile-observatory-hygiene-merge` | `docs/history/prompts/2026-07-17-observatory-hygiene-merge-reconciliation.md`; PR [#155](https://github.com/pcvantol/djconnect/pull/155) |
| Observatory Hygiene Post-Merge Reconciliation | Completed / merged reconciled / archived | Reconcile rolling records after merged PR #155. | `codex/reconcile-observatory-hygiene-merge-postmerge` | `docs/history/prompts/2026-07-17-observatory-hygiene-postmerge-reconciliation.md`; PR [#156](https://github.com/pcvantol/djconnect/pull/156) |
| Platform Release 3.3 Windows ARM64 Evidence Reconciliation | Completed / merged reconciled / archived | Reconcile the completed manifest-bound Windows ARM64 deployment and post-deployment smoke evidence into the canonical release records. | `codex/reconcile-windows-release-evidence` | `docs/release/PLATFORM_3_3_WINDOWS_DEPLOYMENT_COMPLETION.md`; PR [#157](https://github.com/pcvantol/djconnect/pull/157) |
| Windows Evidence Post-Merge Reconciliation | Completed / merged reconciled / archived | Reconciled rolling records after merged PR #157; no release operation or implementation change. | `codex/reconcile-windows-evidence-postmerge` | `docs/history/prompts/2026-07-17-windows-evidence-postmerge-reconciliation.md`; PR [#158](https://github.com/pcvantol/djconnect/pull/158) |
| Safe Codex Subagent Parallelization | Completed / merged reconciled | Establish bounded parallel read-only subagent delegation without changing the one-prompt/one-PR contract. | `codex/govern-subagent-parallelization` | `ENGINEERING_METHOD.md`; PR [#161](https://github.com/pcvantol/djconnect/pull/161) |
| Innovation Engineering Method Evolution | Completed / merged reconciled | Establish Innovation Engineering as the official lightweight learning mode with an explicit promotion path. | `innovation/engineering-method-evolution` | `docs/history/prompts/2026-07-19-innovation-engineering-method-evolution.md`; PR [#162](https://github.com/pcvantol/djconnect/pull/162) |
| Innovation Engineering Post-Merge Reconciliation | Completed / merged reconciled / archived | Reconcile rolling records after merged PR #162; no implementation or release change. | `codex/reconcile-innovation-engineering-merge` | `docs/history/prompts/2026-07-19-innovation-engineering-postmerge-reconciliation.md`; PR [#163](https://github.com/pcvantol/djconnect/pull/163) |
| Home Assistant Deployment Consumer Qualification | Completed / merged reconciled / archived | Qualified the final required Internal Release 3.3 target with an exact artifact deployment and separate post-deployment smoke. | `codex/record-ha-deployment-qualification` | `docs/release/PLATFORM_3_3_HOME_ASSISTANT_DEPLOYMENT_COMPLETION.md`; PR [#183](https://github.com/pcvantol/djconnect/pull/183) |
| Platform Release 3.3 Target Qualification Post-Merge Reconciliation | Completed / merged reconciled / archived | Reconciled rolling records after merged PR #183; no release operation or implementation change. | `codex/reconcile-release-3-3-target-qualification` | `docs/history/prompts/2026-07-19-platform-release-3-3-target-qualification-postmerge-reconciliation.md`; PR [#184](https://github.com/pcvantol/djconnect/pull/184) |
| Home Assistant HTTP Route Incident Remediation | Completed / merged reconciled | Restore config-entry route registration and add route probes to the future HA smoke contract. | `codex/restore-ha-route-registration` | PR [#185](https://github.com/pcvantol/djconnect/pull/185) |
| Home Assistant HTTP Route Incident Post-Merge Reconciliation | Completed / merged reconciled | Reconciled rolling records after merged PR #185; no deployment or release binding change. | `codex/reconcile-ha-route-incident-merge` | PR [#186](https://github.com/pcvantol/djconnect/pull/186) |
| Platform Release 3.3 Operational Burn-in Procedure | Completed / merged reconciled | Establish the reusable seven-day operational burn-in evidence procedure without execution changes. | `agent/platform-3-3-operational-burn-in` | PR [#200](https://github.com/pcvantol/djconnect/pull/200) |
| Platform Release 3.3 Release Certification Process | Completed / merged reconciled | Establish the mandatory evidence-based Release Certification process without execution changes. | `agent/platform-3-3-release-certification-process` | PR [#201](https://github.com/pcvantol/djconnect/pull/201) |
| Platform Release 3.3 Release Completion | Completed / merged reconciled / archived | Formally close the completed 3.3 release and transition it to Maintenance. | `agent/platform-3-3-release-completion` | `docs/history/prompts/2026-07-19-platform-release-3-3-release-completion.md`; PR [#202](https://github.com/pcvantol/djconnect/pull/202), merged as `be5504ad39a2eb251cda066c4fced865477291a6` |
| Platform Release 3.3 Release Completion Post-Merge Reconciliation | Reviewable | Reconcile the merged Release Completion prompt archive and stale rolling-record navigation; no product, runtime, deployment, release or governance behaviour changes. | `codex/reconcile-platform-3-3-release-completion` | This reviewable reconciliation pull request |

All governance rollout work is completed, merged, reconciled and archived.
No `RG-*` adoption prompt remains active.

## Current post-merge reconciliation

PR #202 is merged as `be5504ad39a2eb251cda066c4fced865477291a6`; its Release
Completion record is archived and Platform Release 3.3 is in Maintenance. The
current reviewable reconciliation corrects the predecessor's stale reviewable
navigation state. No Product Definition increment has started.

## Next Engineering Increment

No Platform Release 3.3 execution is active. After this reconciliation is
merged, select the next active work from Product Engineering or Innovation
Engineering; 3.3 remains in Maintenance unless its completion record is
formally reopened.

## Active Next Phase

### Platform Release Engineering Generation 1

The reusable Release Architecture is frozen and the Release Orchestrator is
complete for its planning, simulation and evidence-binding contract. The
historical Platform Release 3.3 dry run returned
`PLATFORM_RELEASE_DRY_RUN_PASSED`; formal Generation 1 capability
qualification returned `PLATFORM_RELEASE_QUALIFIED`.

The corrected execution model is now recorded on `main`: Codex is the release
control plane, GitHub Actions is the exclusive execution engine, Apple and
Windows native builds use their qualified self-hosted runners, and Home
Assistant, API, Website, ESP32 and Pi source builds use GitHub-hosted Linux.
Pi and ESP32 remain artifact-consuming deployment and Verification targets.
The qualified macOS runner has the three separately bounded capabilities
defined in `docs/release/`: Apple Native Build, Private-Network Deployment
Relay and Apple Secure Distribution Relay.

The approved manifest `release-3.3.0-internal-20260714` has completed exact
manifest-bound deployment and separate smoke for all required targets:
Home Assistant, API, Website, Raspberry Pi, ESP32, Apple MacBook, Apple
iPhone with required paired-Watch validation, iPad and Windows ARM64. The
final Home Assistant operation is deployment run `29683604435` with smoke run
`29683901389`. This target qualification does not authorize Release
Certification or burn-in.

Platform Release 3.3 is complete and transitions to Maintenance through its
formal completion record. Future release engineering uses the reusable
burn-in, certification and completion procedures under `docs/release/`.

The Software Assurance Platform architecture sprint has completed with decision
`SOFTWARE_ASSURANCE_PLATFORM_ARCHITECTURE_COMPLETE`. Software Assurance
implementation is ready only through its explicit registered prompt sequence.

The Architecture Closure Review completed on 2026-07-11 with decision
`ARCHITECTURE_FROZEN`.

Platform Baseline v1.0 is certified. The current platform decision is
`PLATFORM_BASELINE_V1_CERTIFIED`. Platform Qualification is
complete. Home Assistant, Apple, Raspberry Pi, Windows, ESP and DJConnect
Voice Assistant qualification are complete for the current verification
roadmap. Phase 13E-R2 returned `WINDOWS_LIVE_QUALIFIED`. Phase 14 returned
`ESP_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING`. Phase 14E returned
`ESP_LIVE_QUALIFIED`. Phase 15 returned
`VOICE_ASSISTANT_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING`. Phase 15E
returned `VOICE_ASSISTANT_LIVE_QUALIFICATION_BLOCKED` because the local Home
Assistant Assist lab was stale for the active repository SHA and live Voice
Assistant target/opt-in configuration was absent. Phase 15E-R remediated those
blockers and returned `VOICE_ASSISTANT_LIVE_QUALIFIED`. Phase 16 selected the
canonical cross-platform smoke plan but returned
`CROSS_PLATFORM_QUALIFICATION_BLOCKED` before mutation because the local HA lab
was stale for the active repository SHA and the prepared Windows VM was not
running. Phase 16-R remediated the environment blockers and returned
`CROSS_PLATFORM_QUALIFIED`. Phase 17 Platform Test Coverage Improvement
returned `PLATFORM_TEST_COVERAGE_IMPROVEMENT_COMPLETE`: its immutable
historical matrix added Home Assistant, ESP32 firmware and Voice Assistant
coverage responsibility. The subsequent ESP native coverage follow-up returned
`ESP_COVERAGE_QUALIFIED`. Platform Baseline v1.0 Certification accepted the
completed evidence. Software Assurance Prompts 1 through 4 subsequently
completed; their resulting capabilities are operationally frozen and no
Software Assurance prompt is currently active.

Generation 1 Platform Engineering is formally closed and frozen. Platform
Evolution is the current lifecycle; Software Assurance Generation 1 is complete
and operationally frozen. Do not reopen Platform Engineering.

Phase 9V rerun has qualified the Verification Platform using the dedicated
local Home Assistant verification lab. The canonical planner selected the
approved first Profile scenario set, exact-SHA CI passed, the `ha-profile` lab
was qualified, and `PROFILE-001` through `PROFILE-005` executed successfully
through the Home Assistant adapter with persisted evidence.

Phase 9V qualifies the Verification Platform. It does not qualify broad
DJConnect Home Assistant backend scenario coverage.

The Verification Platform runtime is versioned as `1.1.0` and can be released
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
path available for current platform verification. The Phase 10E retry then
qualified the latest eligible iOS 26.5 simulator runtime and XCTest primary-tab
healthcheck, returning
`APPLE_RUNTIME_QUALIFIED_SCENARIO_SELECTION_BLOCKED`. Broad Apple scenario
execution did not start because the canonical smoke planner still selected only
HA cases and exposed no Apple adapter executable scenario set. App
Store/TestFlight distribution signing remains a release-v1.0 readiness
follow-up.

Phase 10E-R3 remediated the planner/scenario mapping blocker and returned
`APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS`. The Phase 10E retry after
R3 found no remaining blocking R3 issues: the smoke planner selects
`APPLE-001`, Apple runtime qualification passed again on iOS 26.5, and
`APPLE-001` executed through the Scenario Engine and Apple adapter with PASS
evidence. Remaining Apple warnings are non-blocking for selecting the next
platform adapter.

Phase 11 selected the Raspberry Pi Verification Adapter as the next platform
adapter phase and returned `RASPBERRY_PI_ADAPTER_SELECTED`. The selection
favored Raspberry Pi because it adds the first non-Apple rich client runtime
path and directly targets ambient/shared-room evidence needed for Platform
Baseline v1.0. Phase 11 generated the Phase 12 implementation prompt and did
not begin adapter implementation.

Phase 12 implemented the thin Raspberry Pi Verification Adapter and returned
`RASPBERRY_PI_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED`. The adapter is
qualified for mock/unit primitive coverage, Scenario Engine integration and
planning integration. Live Raspberry Pi runtime proof remains deferred until
prepared target configuration and exact-SHA environment gates are available.

Phase 12E qualified the live Raspberry Pi runtime smoke path against
`rbpi-djconnect.local` and returned
`RASPBERRY_PI_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS`. `PI-001` executed
through the Scenario Engine and Raspberry Pi adapter with PASS evidence.
Phase 12E-R then remediated and qualified the warning by adding canonical Pi
execution-surface mapping for shared Pi product scenarios. Smoke planning now
exposes 9 Raspberry Pi adapter cases instead of only `PI-001`, and
`PROFILE-010`, `CAPABILITIES-005`, `ASKDJ-010` and `TRACKINSIGHT-005` passed in
run `djv-20260712T093801Z-b5be5b3197`. A follow-up full Pi smoke execution
passed all 9 Pi adapter cases in run `djv-20260712T094155Z-cf11275694`.

Phase 13 implemented the first thin Windows Verification Adapter and returned
`WINDOWS_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING`. Smoke planning selects
`WIN-001` as adapter `windows_native_arm64`, the adapter records canonical
Windows client ownership as `pcvantol/djconnect-windows`, and `WIN-001` passed
through the Scenario Engine and Windows adapter in mock/local mode in run
`djv-20260712T115323Z-0e7b518464`. The operator confirmed Windows is available
in Parallels.

Phase 13E executed the Windows live qualification gate and returned
`WINDOWS_LIVE_QUALIFICATION_BLOCKED`. The adapter and planner remain healthy:
`WIN-001` validates and the focused Windows adapter/planner regression tests
pass. Live execution run `djv-20260712T121332Z-a50bf9b10e` failed closed before
mutation because `DJCONNECT_VERIFICATION_WINDOWS_TARGET_JSON` was not
configured and no real `pcvantol/djconnect-windows` artifact/runtime commands
were provided. Mac Catalyst build and runtime qualification remain outside
Phase 13E and Phase 13E-R scope.

Phase 13E-R remediated the missing Windows target configuration and returned
`WINDOWS_LIVE_TARGET_CONFIGURED_CLIENT_BUILD_BLOCKED`. The prepared Parallels
`Windows 11 Home` target, `windows_dotnet_maintenance` gate and Windows
adapter path are healthy. Live execution run
`djv-20260712T123021Z-ccda65836f` reached the real
`pcvantol/djconnect-windows` checkout but failed at launch because the Windows
client does not compile for `net10.0-windows10.0.19041.0`: `StatusResponse`
does not define Profile / Music DNA members referenced by `MainViewModel.cs`.
The active next phase is Phase 13E-R2 Windows Client Build Remediation And Live
Qualification.

Phase 13E-R2 remediated the Windows client build blocker and returned
`WINDOWS_LIVE_QUALIFIED`. The Windows client now deserializes backend-owned
Profile / Music DNA metadata in `StatusResponse`, the Windows repository core
tests passed, the Parallels Windows build for `net10.0-windows10.0.19041.0`
succeeded and `WIN-001` passed live through the Scenario Engine and
`windows_native_arm64` adapter in run `djv-20260712T135722Z-d09b6ec5ba`.
The active next phase is Phase 14 ESP Verification Adapter.

Coverage Baseline 1 is established as immutable historical evidence with
decision `CROSS_PLATFORM_COVERAGE_BASELINE_ESTABLISHED`. It includes Home
Assistant, Apple and Raspberry Pi. Windows remains excluded from that immutable
historical baseline.

Windows Coverage Baseline 1 is established as a later explicit post-Baseline-1
record with decision `WINDOWS_COVERAGE_BASELINE_ESTABLISHED`. It measured
`pcvantol/djconnect-windows` commit
`b205f087214eb5fe90c4129c2afa9dee7f836a82` through native Coverlet Cobertura
and Runtime `1.1.0`, returning `COVERAGE_VALID` with 72.45% line coverage and
50.85% branch coverage. Future coordinated coverage reporting may include all
four platforms without redefining Coverage Baseline 1.

Phase 14 implemented and mock-qualified the thin ESP Verification Adapter and
returned `ESP_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING`. Phase 14E
qualified the adapter against real LilyGO ESP32-S3 hardware and returned
`ESP_LIVE_QUALIFIED`. `HARDWARE-001` through `HARDWARE-010` passed through the
Scenario Engine and ESP32 adapter after the Home Assistant lab was recreated
for the current repository SHA and firmware `3.2.11` was flashed to the
device.

Phase 15 treated the DJConnect Voice Assistant Conversation Agent as its own
verification platform, distinct from the ESP adapter, and returned
`VOICE_ASSISTANT_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING`. The
`voice_endpoint` adapter, CLI registration, Scenario Engine routing and
planning metadata are mock/local qualified. Phase 15E attempted live
qualification and returned `VOICE_ASSISTANT_LIVE_QUALIFICATION_BLOCKED`.
Phase 15E-R remediated the stale HA Assist lab, Piper sidecar configuration,
Voice Assistant target configuration and live opt-in blockers, then passed
`VOICE-001` through the live `voice_endpoint` adapter path with decision
`VOICE_ASSISTANT_LIVE_QUALIFIED`.

Phase 16 was Cross-Platform Qualification across Home Assistant, Apple,
Raspberry Pi, Windows, ESP and DJConnect Voice Assistant. It selected the
canonical cross-platform smoke plan and verified exact-SHA CI, but returned
`CROSS_PLATFORM_QUALIFICATION_BLOCKED` before live mutation because the local
Home Assistant verification lab was stale for the active SHA and the Parallels
Windows VM was stopped during the Windows maintenance gate. Phase 16-R
remediated the local lab and Windows runtime blockers, refreshed the HA lab to
the required `ha-full` profile for SHA
`07178bad48d3bb8ad977e6b9070abfdf444889b4`, and returned
`CROSS_PLATFORM_QUALIFIED`.

After Phase 16 Cross-Platform Qualification, Phase 17 completed Platform Test
Coverage Improvement. The subsequent ESP native coverage follow-up qualified
the remaining ESP coverage capability. The next platform activity is the
Platform Baseline Readiness Review rerun; certification remains a separate,
explicit activity.

## Active Implementation Program

### Software Assurance Platform

Status:

```text
ARCHITECTURE_COMPLETE
```

Implementation program:

```text
SOFTWARE_ASSURANCE_GENERATION_1_ACTIVE
```

Prerequisite:

```text
PLATFORM_BASELINE_V1_CERTIFIED
```

Prerequisite status:

```text
SATISFIED
```

Implementation sequence:

1. [Prompt 1: CI Governance Foundation](prompts/deferred/software_assurance/PROMPT_01_CI_GOVERNANCE_FOUNDATION.md) — `COMPLETE`
2. [Prompt 2: Cross-Repository Workflow Harmonization](prompts/deferred/software_assurance/PROMPT_02_CROSS_REPOSITORY_WORKFLOW_HARMONIZATION.md) — `COMPLETE`
3. [Prompt 3: Trusted Delivery Platform](prompts/deferred/software_assurance/PROMPT_03_TRUSTED_DELIVERY_PLATFORM.md) — `PASS`
4. [Prompt 4: Trusted Delivery Certification](prompts/deferred/software_assurance/PROMPT_04_TRUSTED_DELIVERY_CERTIFICATION.md) — `COMPLETE`

Historical implementation state:

```text
Platform Baseline v1.0 certified; all four Software Assurance Generation 1 prompts complete; Trusted Delivery certified.
```

Canonical registration:

- `SOFTWARE_ASSURANCE_IMPLEMENTATION.md`
- `prompts/deferred/software_assurance/`

No Software Assurance Generation 1 prompt is active. Future work proceeds
through Product Development, Platform Evolution or Platform Release Engineering.

### Trusted Delivery Single-Maintainer Governance

Status: `TRUSTED_DELIVERY_GOVERNANCE_OPERATIONAL`

The canonical Trusted Delivery implementation now separates technical
qualification from SHA-bound Owner Authorization. Fixed approving-review counts
are not a valid single-maintainer control. LOW/NORMAL candidates receive
automatic `NOT_REQUIRED` status; HIGH_RISK candidates remain blocked until the
configured owner authorizes the exact current SHA after technical qualification
passes. The implementation is recorded in
`TRUSTED_DELIVERY_SINGLE_MAINTAINER_GOVERNANCE.md` and its completion report.

The next explicit phase is [Prompt 5: Single-Maintainer Governance
Rollout](prompts/deferred/software_assurance/PROMPT_05_SINGLE_MAINTAINER_GOVERNANCE_ROLLOUT.md).
It must first roll out the merged shared workflow to consumers and then migrate
branch protection; it must not execute automatically.

### Platform Release Engineering

Status:

```text
PLATFORM_RELEASE_3_3_CANDIDATE_BLOCKED
```

Prompt 1 froze the reusable Platform Release Architecture with decision
`PLATFORM_RELEASE_ARCHITECTURE_COMPLETE`. Prompt 2 implemented and qualified
the simulation-only Platform Release Orchestrator with decision
`PLATFORM_RELEASE_ORCHESTRATOR_QUALIFIED`. Prompt 3 returned
`PLATFORM_RELEASE_DRY_RUN_PASSED` and Prompt 4 returned
`PLATFORM_RELEASE_QUALIFIED`. No operational platform release has been
executed. The canonical architecture, runtime and completion reports are:

- `docs/release/PLATFORM_RELEASE_ARCHITECTURE.md`
- `docs/release/RUNTIME.md`
- `docs/release/PLATFORM_RELEASE_ROADMAP.md`
- `docs/release/PROMPT_01_RELEASE_ARCHITECTURE_COMPLETION.md`
- `docs/release/PROMPT_02_RELEASE_ORCHESTRATOR_COMPLETION.md`

The `main` branch also contains the corrected runner/deployment architecture,
the private-network and Apple distribution relay contracts, and the bounded
post-deployment smoke policy. Pi has a merged manifest-bound deployment and
smoke workflow; it has not been dispatched. No fresh candidate manifest or
exact-SHA evidence bundle exists for the current set of `main` commits, and
the remaining required deployment consumers have not yet been completed and
qualified. Consequently no deployment, tag, GitHub Release or publication is
authorized.

The next explicit release-engineering sequence is:

1. Complete and qualify the manifest-bound deployment and bounded smoke
   consumers required by the approved Internal Release target set.
2. Reconstruct a Platform 3.3 candidate manifest from the then-current
   `main` SHAs and bind new verification, coverage and Trusted Delivery
   evidence to those SHAs.
3. Obtain explicit authorization for the Internal Release and execute only
   the approved manifest-bound workflow dispatches.
4. Collect operational and burn-in evidence before considering
   [Prompt 5: Platform Release Certification](prompts/release/PROMPT_05_PLATFORM_RELEASE_CERTIFICATION.md).

Prompt 5 is generated but inactive. It must not start automatically and must
not be used to waive missing candidate, deployment or operational evidence.

Release-engineering clean-session command:

```text
Read docs/release/PLATFORM_RELEASE_ARCHITECTURE.md,
docs/release/PLATFORM_RELEASE_RUNTIME_ARCHITECTURE.md,
docs/release/DEPLOYMENT_WORKFLOW_POLICY.md and
docs/release/PLATFORM_RELEASE_MANAGEMENT_SUMMARY.md. Do not dispatch a
release until the current-main candidate and required deployment consumers are
qualified and explicit authorization is supplied.
```

Use this clean-session prompt for future operator-directed work:

```text
Read `docs/release/PLATFORM_RELEASE_MANAGEMENT_SUMMARY.md` and the canonical
deployment contracts. Reconstruct evidence for current `main` only after the
required deployment consumers are qualified; do not execute an Internal
Release or Prompt 5 implicitly.
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
| 10E retry | Apple Scenario Coverage Expansion After Runtime Qualification | Qualified with non-blocking warnings after R3 retry | `prompts/verification/PHASE_10E_APPLE_SCENARIO_COVERAGE_EXPANSION.md` | Phase 10E-R3 resolved the planner/scenario mapping blocker and no remaining R3 blockers were found | `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md`; runtime evidence `artifacts/verification/evidence/apple10e-20260711T222229Z-657e8945b1/`; scenario evidence `artifacts/verification/evidence/djv-20260711T222533Z-fe2a0bcda5/` | Continue Phase 10E PR if still open; Apple warnings are non-blocking | Phase 11 |
| 10E-R3 | Apple Scenario Planner Mapping Remediation | Qualified with non-blocking warnings | `prompts/verification/PHASE_10E_R3_APPLE_SCENARIO_PLANNER_MAPPING_REMEDIATION.md` | Phase 10E retry returned `APPLE_RUNTIME_QUALIFIED_SCENARIO_SELECTION_BLOCKED` | `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md`; JSON report; evidence `artifacts/verification/evidence/djv-20260711T221707Z-9af6ed501d/`; confirmed by retry evidence `artifacts/verification/evidence/djv-20260711T222533Z-fe2a0bcda5/` | New remediation branch or continue Phase 10E PR if still open | Phase 11 |
| 11 | Additional Platform Adapter Selection | Complete - Raspberry Pi selected | `prompts/verification/PHASE_11_ADDITIONAL_PLATFORM_ADAPTER_SELECTION.md` | Phase 10E-R3 returned `APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS` with warnings explicitly non-blocking for adapter selection | `docs/verification/reports/PHASE_11_ADDITIONAL_PLATFORM_ADAPTER_SELECTION.md` | New phase branch; no adapter implementation in Phase 11 | Phase 12 |
| 12 | Raspberry Pi Verification Adapter | Qualified with live runtime skipped | `prompts/verification/PHASE_12_RASPBERRY_PI_VERIFICATION_ADAPTER.md` | Phase 11 returned `RASPBERRY_PI_ADAPTER_SELECTED` | `docs/verification/reports/PHASE_12_RASPBERRY_PI_ADAPTER_COMPLETION.md` | New phase branch; complete Phase 12 protocol before broad Pi coverage | Phase 12E |
| 12E | Raspberry Pi Scenario Coverage Expansion | Qualified with non-blocking warnings | `prompts/verification/PHASE_12E_RASPBERRY_PI_SCENARIO_COVERAGE_EXPANSION.md` | Phase 12 returned `RASPBERRY_PI_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED` | `docs/verification/reports/PHASE_12E_RASPBERRY_PI_SCENARIO_COVERAGE.md`; evidence `artifacts/verification/evidence/djv-20260712T065051Z-7468abf4dd/` | New phase branch; complete Phase 12E protocol before next adapter work | Phase 12E-R |
| 12E-R | Raspberry Pi Product Scenario Mapping Remediation | Qualified | Generated from Phase 12E warning | Phase 12E returned `RASPBERRY_PI_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS` because broader Pi product mapping was missing | `docs/verification/reports/PHASE_12E_R_RASPBERRY_PI_PRODUCT_SCENARIO_MAPPING.md`; focused evidence `artifacts/verification/evidence/djv-20260712T093801Z-b5be5b3197/`; full Pi smoke evidence `artifacts/verification/evidence/djv-20260712T094155Z-cf11275694/` | Complete remediation protocol before next adapter work | Next adapter selection |
| 13 | Windows Verification Adapter | Qualified with live runtime pending | Generated from Phase 13 operator prompt | Phase 12E-R remediation | `docs/verification/reports/PHASE_13_WINDOWS_ADAPTER_COMPLETION.md`; mock/local evidence `artifacts/verification/evidence/djv-20260712T115323Z-0e7b518464/` | Complete Phase 13 protocol before live Windows coverage | Phase 13E Windows runtime qualification |
| 13E | Windows Live Qualification | Blocked - Windows target configuration missing | To be generated by future operator prompt | Phase 13 returned `WINDOWS_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING` | `docs/verification/reports/PHASE_13E_WINDOWS_LIVE_QUALIFICATION.md`; evidence `artifacts/verification/evidence/djv-20260712T121332Z-a50bf9b10e/` | Future PR or follow-up branch | Phase 13E-R Windows live target configuration remediation |
| 13E-R | Windows Live Target Configuration Remediation | Blocked - Windows client build failure | `prompts/verification/PHASE_13E_R_WINDOWS_LIVE_TARGET_CONFIGURATION_REMEDIATION.md` | Phase 13E returned `WINDOWS_LIVE_QUALIFICATION_BLOCKED` because `DJCONNECT_VERIFICATION_WINDOWS_TARGET_JSON` and real Windows artifact/runtime commands were not configured | `docs/verification/reports/PHASE_13E_R_WINDOWS_LIVE_TARGET_CONFIGURATION_REMEDIATION.md`; evidence `artifacts/verification/evidence/djv-20260712T123021Z-ccda65836f/` | Future PR or follow-up branch | Phase 13E-R2 Windows client build remediation |
| 13E-R2 | Windows Client Build Remediation And Live Qualification | Qualified | `prompts/verification/PHASE_13E_R2_WINDOWS_CLIENT_BUILD_REMEDIATION.md` | Phase 13E-R returned `WINDOWS_LIVE_TARGET_CONFIGURED_CLIENT_BUILD_BLOCKED` because the real Windows client checkout did not compile for `net10.0-windows10.0.19041.0` | `docs/verification/reports/PHASE_13E_R2_WINDOWS_CLIENT_BUILD_REMEDIATION.md`; evidence `artifacts/verification/evidence/djv-20260712T135722Z-d09b6ec5ba/` | Future PR or follow-up branch | Phase 14 ESP Verification Adapter |
| 14 | ESP Verification Adapter | Qualified with live runtime pending | `prompts/verification/PHASE_14_ESP_VERIFICATION_ADAPTER.md` | Phase 13E-R2 returned `WINDOWS_LIVE_QUALIFIED` | `docs/verification/reports/PHASE_14_ESP_ADAPTER_COMPLETION.md` | Future PR | Phase 14E ESP Live Qualification |
| 14E | ESP Live Qualification | Qualified | Generated from Phase 14E operator prompt | Phase 14 returned `ESP_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING` | `docs/verification/reports/PHASE_14E_ESP_LIVE_QUALIFICATION.md`; evidence `artifacts/verification/evidence/djv-20260712T151318Z-f838e458f3/` and full hardware set `djv-20260712T151519Z-81422a10e9` through `djv-20260712T151756Z-d4dc9fc4f8` | Future PR | Phase 15 DJConnect Voice Assistant Verification Adapter |
| 15 | DJConnect Voice Assistant Verification Adapter | Qualified with live runtime pending | `prompts/verification/PHASE_15_DJCONNECT_VOICE_ASSISTANT_VERIFICATION_ADAPTER.md` | Phase 14E returned `ESP_LIVE_QUALIFIED` | `docs/verification/reports/PHASE_15_DJCONNECT_VOICE_ASSISTANT_ADAPTER_COMPLETION.md` | Future PR | Phase 15E DJConnect Voice Assistant Live Qualification |
| 15E | DJConnect Voice Assistant Live Qualification | Blocked - HA Assist lab stale and live target configuration absent | `prompts/verification/PHASE_15E_DJCONNECT_VOICE_ASSISTANT_LIVE_QUALIFICATION.md` | Phase 15 returned `VOICE_ASSISTANT_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING` | `docs/verification/reports/PHASE_15E_DJCONNECT_VOICE_ASSISTANT_LIVE_QUALIFICATION.md`; evidence `artifacts/verification/evidence/djv-20260712T154526Z-1d6103fdd3/` | Future PR | Phase 15E-R Voice Assistant live qualification remediation |
| 15E-R | DJConnect Voice Assistant Live Qualification Remediation | Qualified | `prompts/verification/PHASE_15E_R_DJCONNECT_VOICE_ASSISTANT_LIVE_QUALIFICATION_REMEDIATION.md` | Phase 15E returned `VOICE_ASSISTANT_LIVE_QUALIFICATION_BLOCKED` because the local HA Assist lab was stale for the current repository SHA and live Voice Assistant target/opt-in configuration was absent | `docs/verification/reports/PHASE_15E_R_DJCONNECT_VOICE_ASSISTANT_LIVE_QUALIFICATION_REMEDIATION.md`; evidence `artifacts/verification/evidence/djv-20260712T155553Z-fbdeaf590f/` | Future PR | Phase 16 Cross-Platform Qualification |
| 16 | Cross-Platform Qualification | Blocked - stale HA lab and stopped Windows VM | `prompts/verification/PHASE_16_CROSS_PLATFORM_QUALIFICATION.md` | Phase 15E-R returned `VOICE_ASSISTANT_LIVE_QUALIFIED` | `docs/verification/reports/PHASE_16_CROSS_PLATFORM_QUALIFICATION.md` | Future PR | Phase 16-R Cross-Platform Qualification Environment Remediation |
| 16-R | Cross-Platform Qualification Environment Remediation | Qualified | `prompts/verification/PHASE_16_R_CROSS_PLATFORM_QUALIFICATION_ENVIRONMENT_REMEDIATION.md` | Phase 16 returned `CROSS_PLATFORM_QUALIFICATION_BLOCKED` because the HA lab was stale for the active SHA and the Windows VM was stopped | `docs/verification/reports/PHASE_16_CROSS_PLATFORM_QUALIFICATION.md`; evidence `artifacts/verification/evidence/djv-20260712T174727Z-77dee61aa9/`, `artifacts/verification/evidence/djv-20260712T175431Z-e49257d9dc/`, `artifacts/verification/evidence/djv-20260712T175532Z-311df26a8c/` | Future PR | Platform Test Coverage Improvement |
| 17 | Platform Test Coverage Improvement | Complete | `prompts/verification/PHASE_17_PLATFORM_TEST_COVERAGE_IMPROVEMENT.md` | Coverage Baseline 1 established; Windows Coverage Baseline 1 established; Phase 16-R returned `CROSS_PLATFORM_QUALIFIED` | `docs/verification/reports/PHASE_17_PLATFORM_TEST_COVERAGE_IMPROVEMENT.md`; fresh HA, Apple, Pi and Windows evidence under `artifacts/verification/evidence/phase-17-{ha,apple,pi,windows}/` | Preserve historical baselines; ESP-native coverage export remains `NOT_YET_SUPPORTED`; do not start certification automatically | Platform Baseline v1.0 Certification |

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

Exact clean-session command for the next operator-directed gate:

```text
Read SOFTWARE_ASSURANCE_IMPLEMENTATION.md and execute only the explicitly
authorized next Software Assurance implementation prompt.
```
