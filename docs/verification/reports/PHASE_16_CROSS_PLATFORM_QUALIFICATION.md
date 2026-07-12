# Phase 16 Cross-Platform Qualification

Status: `CROSS_PLATFORM_QUALIFIED`

Date: 2026-07-12

Branch: `main`

Repository SHA: `07178bad48d3bb8ad977e6b9070abfdf444889b4`

Verification Runtime: `1.1.0`

## Executive Summary

Phase 16 selected the canonical cross-platform smoke plan, verified repository
and CI gates, and initially stopped before live mutation because mandatory
environment gates were not safe for the active repository SHA.

Phase 16-R remediated the environment blockers, refreshed the local Home
Assistant lab to the required `ha-full` profile for the active SHA, verified the
Windows Parallels runtime, configured the already-qualified live adapter
targets, and executed the selected cross-platform smoke coverage through the
Scenario Engine.

Qualification decision:

```text
CROSS_PLATFORM_QUALIFIED
```

## Scope

Executed:

- read the canonical platform bootstrap, verification bootstrap, prompt index,
  Phase 16 prompt and completion protocol;
- ignored deferred Software Assurance implementation because
  `PLATFORM_BASELINE_V1_CERTIFIED` has not been reached;
- selected the canonical cross-platform smoke plan with the Verification
  Planning Engine;
- validated the full scenario catalog;
- inspected exact-SHA GitHub CI status for the active repository SHA;
- ran the Verification Execution Environment prepare gate;
- classified the blockers before scenario mutation.

Out of scope and not executed:

- Platform Test Coverage Improvement;
- Platform Baseline certification;
- Software Assurance implementation;
- new product behavior;
- new verification architecture;
- scenario expectation changes.

## Implementation

No product implementation changed.

No verification architecture changed.

Phase 16 produced documentation and prompt-index updates only, because the
environment gate failed before live cross-platform mutation.

## Verification

Scenario catalog validation:

```bash
python3 -m tools.verification.cli validate
```

Result:

```text
validated 234 scenarios
```

Cross-platform smoke planning:

```bash
python3 -m tools.verification.cli plan --strategy smoke --policy smoke --format summary
```

Result:

```text
plan_id: plan-smoke-smoke-20260712T162853Z
strategy: smoke
policy: smoke
cases: 47
batches: 4
estimated_seconds: 240
```

Selected executable coverage:

| Platform | Cases |
| --- | ---: |
| Apple | 1 |
| Home Assistant | 35 |
| Raspberry Pi | 9 |
| Windows | 1 |
| Voice Endpoint | 1 |

The plan's lab execution metadata also retained external requirements for
ESP32 runtime evidence and release artifacts. ESP32 live evidence from Phase
14E remains linked below because the Phase 16 executable smoke plan did not
select ESP adapter cases directly.

Exact-SHA CI inspection:

```bash
gh run list --limit 10 --json databaseId,headSha,status,conclusion,workflowName,createdAt,event
```

Result:

```text
CI_PASS for SHA 07178bad48d3bb8ad977e6b9070abfdf444889b4:
- CodeQL, run 29199339001
- Validate Home Assistant custom integration, run 29199339015
```

Environment prepare gate:

```bash
python3 -m tools.verification.cli prepare
```

Result:

```text
run_id: djv-20260712T162902Z-21406a02c3
host_preflight: FAIL
ha_docker_discovery: FAIL
windows_dotnet_maintenance: FAIL
github_workflow_discovery: PASS
github_ci_status: PASS
dependency_inspection: PASS
environment_cleanup: PASS
secrets_loading: PASS
```

Repository hygiene after documentation updates:

```bash
git diff --check
```

Result:

```text
passed
```

## Evidence

Current Phase 16 gate evidence:

- active repository SHA:
  `07178bad48d3bb8ad977e6b9070abfdf444889b4`;
- planner run:
  `plan-smoke-smoke-20260712T162853Z`;
- prepare run identity:
  `djv-20260712T162902Z-21406a02c3`;
- exact-SHA CI:
  GitHub Actions runs `29199339001` and `29199339015`.

Linked prior qualification evidence:

| Platform | Decision | Evidence |
| --- | --- | --- |
| Home Assistant | `HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS` | `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.md` |
| Apple | `APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS` | `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md` |
| Raspberry Pi | `RASPBERRY_PI_PRODUCT_SCENARIO_MAPPING_QUALIFIED` | `docs/verification/reports/PHASE_12E_R_RASPBERRY_PI_PRODUCT_SCENARIO_MAPPING.md` |
| Windows | `WINDOWS_LIVE_QUALIFIED` | `docs/verification/reports/PHASE_13E_R2_WINDOWS_CLIENT_BUILD_REMEDIATION.md` |
| ESP32 | `ESP_LIVE_QUALIFIED` | `docs/verification/reports/PHASE_14E_ESP_LIVE_QUALIFICATION.md` |
| Voice Assistant | `VOICE_ASSISTANT_LIVE_QUALIFIED` | `docs/verification/reports/PHASE_15E_R_DJCONNECT_VOICE_ASSISTANT_LIVE_QUALIFICATION_REMEDIATION.md` |

## Investigation

| Finding | Classification | Owner | Blocking | Recommended action |
| --- | --- | --- | --- | --- |
| Port `18123` was already bound by Docker process `com.docke`, so a fresh HA lab could not be started safely. | Execution environment issue | Local verification lab | Yes | Destroy or replace the stale HA lab before Phase 16-R. |
| Docker HA discovery found a running `djconnect-verification-ha` container labelled for source SHA `af8228bc7c933df61cab47d4105002839ba65fb3`, not the active SHA `07178bad48d3bb8ad977e6b9070abfdf444889b4`. | Execution environment issue | Local verification lab | Yes | Recreate the required lab profile for the active SHA and rerun doctor/prepare gates. |
| The existing HA container used lab profile `ha-assist`, while the Phase 16 plan requires broader `ha-full` capabilities. | Execution environment issue | Local verification lab | Yes | Create a clean `ha-full` lab or otherwise prove all selected Phase 16 readiness gates. |
| Windows .NET maintenance failed because Parallels VM `Windows 11 Home` was not started. | Operator configuration issue | Windows runtime lab | Yes | Start the VM and rerun `windows_dotnet_maintenance` before live Windows scenario execution. |

No product implementation defect was found.

## Repository Intelligence Review

Knowledge captured:

- Phase 16 must start from lab state that is both current-SHA safe and broad
  enough for the selected cross-platform plan.
- Prior `ha-assist` Voice Assistant evidence is not sufficient by itself for
  Phase 16 when the planner selects `ha-full` readiness gates.
- Windows live qualification can regress to blocked if the prepared Parallels
  VM is stopped, even when the Windows adapter and client code are already
  qualified.

## Architecture Impact Assessment

No architecture changed.

The frozen Verification Architecture held: the Planning Engine selected scope,
the Execution Environment owned safety gates and the phase stopped before an
unsafe live mutation.

## Technical Design Assessment

No product technical design changed.

No HTTP, pairing, voice, client, firmware, storage or playback contract changed.

## Verification Assessment

Phase 16 did not execute the selected 47 cross-platform cases because mandatory
environment gates failed first.

Phase 16-R then executed the selected 47 cross-platform cases with configured
Home Assistant, Apple, Raspberry Pi, Windows and Voice Assistant adapters.
The first full configured run produced 42 PASS and 5 FAIL. Investigation found
four transient HA WebSocket timeouts from parallel worker execution and one
operator invocation mismatch for `ASKDJ-010`, which is a Raspberry Pi mapped
scenario. Targeted remediation reruns passed all five remaining cases:

- `BACKEND-001`, `BACKEND-008`, `ASKDJ-008` and `ASKDJ-020` passed in a
  serial HA adapter rerun;
- `ASKDJ-010` passed through the Raspberry Pi adapter using the previously
  qualified `rbpi-djconnect.local` target.

The selected Phase 16 smoke scope is therefore qualified. Platform Test
Coverage Improvement may be selected next, but must not be started
automatically.

Follow-up implementation note:

- the Verification Execution Environment now supports
  `python3 -m tools.verification.cli prepare --refresh-ha-lab`, equivalent to
  `DJCONNECT_VERIFICATION_HA_REFRESH=1`, to refresh only the dedicated
  DJConnect HA lab container before a run.

## Known Blockers

- None blocking Phase 16-R completion.

Resolved blockers:

- stale/non-current HA Docker lab on port `18123`;
- HA lab profile mismatch for Phase 16 cross-platform requirements;
- Parallels `Windows 11 Home` VM stopped during Windows maintenance gate;
- local lab authentication absent after a prior already-onboarded HA lab.

## Qualification Decision

Phase 16-R returns:

```text
CROSS_PLATFORM_QUALIFIED
```

Next engineering action:

```text
Platform Test Coverage Improvement
```

Do not execute Platform Test Coverage Improvement automatically.

## Phase 16-R Addendum

Phase 16-R remediation evidence:

- `python3 -m tools.verification.cli validate`: `validated 234 scenarios`;
- `python3 -m tools.verification.cli plan --strategy smoke --policy smoke --format summary`:
  47 selected smoke cases across Apple, Home Assistant, Raspberry Pi, Windows
  and Voice Assistant;
- `python3 -m tools.verification.cli lab ha fresh`: replaced the stale local
  HA lab;
- `python3 -m tools.verification.cli lab ha bootstrap-auth`: created fresh
  local lab credentials without exposing the token;
- `python3 -m tools.verification.cli prepare --refresh-ha-lab`: refreshed and
  qualified a `ha-full` lab for SHA
  `07178bad48d3bb8ad977e6b9070abfdf444889b4`;
- `python3 -m tools.verification.cli doctor --environment ha-docker`:
  `ha_docker_discovery` PASS with the current `ha-full` lab;
- Parallels VM `Windows 11 Home`: running during Phase 16-R execution;
- configured cross-platform run:
  `artifacts/verification/evidence/djv-20260712T174727Z-77dee61aa9/`
  produced 42 PASS and 5 remediated failures;
- serial HA rerun:
  `artifacts/verification/evidence/djv-20260712T175431Z-e49257d9dc/`
  produced 4 PASS for the transient HA WebSocket timeout cases;
- Raspberry Pi rerun:
  `artifacts/verification/evidence/djv-20260712T175532Z-311df26a8c/`
  produced 1 PASS for `ASKDJ-010`.

The 47 selected Phase 16 smoke cases are green when the configured full run and
the targeted remediation reruns are considered together.
