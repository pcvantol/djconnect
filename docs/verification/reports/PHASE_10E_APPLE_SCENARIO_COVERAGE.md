# Phase 10E Apple Scenario Coverage Expansion

Status: APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS
Date: 2026-07-12

## Executive Summary

Phase 10E retry executed the mandatory Apple Runtime Qualification gate before
any broad Apple scenario batch. Phase 10E-R3 then remediated the
planner/scenario mapping blocker by adding the first canonical Apple runtime
smoke scenario and making Apple-only execution gates scenario-aware.

The Apple runtime gate now passes. Release-equivalent simulator build, isolated
DerivedData cleanup, entitlement discovery, Xcode account/development signing,
simulator install, launch, screenshot, scoped log collection and XCTest UI
healthcheck all completed successfully.

The canonical smoke planner now selects `APPLE-001` as an Apple adapter case
alongside the existing Home Assistant smoke set. `APPLE-001` executed through
the Scenario Engine and thin Apple adapter using the prepared iOS 26.5
simulator target and passed with persisted evidence.

The July 12, 2026 Phase 10E retry reran after VPB-039 was resolved and found
no remaining blocking R3 issues. Runtime qualification passed again, the smoke
planner selected the Apple scenario, and `APPLE-001` passed again through the
Scenario Engine and Apple adapter.

Current decision:

```text
APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS
```

## Evidence

Latest successful runtime qualification evidence:

```text
artifacts/verification/evidence/apple10e-20260711T222229Z-657e8945b1/
```

Latest screenshot evidence:

```text
artifacts/verification/evidence/apple10e-20260711T222229Z-657e8945b1/apple/phase-10e-runtime-qualification.png
```

Toolchain maintenance evidence:

```text
artifacts/verification/evidence/appletoolchain-20260711T221128Z-914cdf77e6/
```

Apple scenario execution evidence:

```text
artifacts/verification/evidence/djv-20260711T222533Z-fe2a0bcda5/
```

## Gate Results

| Check | Result | Notes |
| --- | --- | --- |
| Toolchain maintenance | PASS | Xcode 26.6, no pending Software Update Xcode update, iOS 26.5 selected as latest eligible stable simulator runtime. |
| DerivedData isolation | PASS | `artifacts/verification/apple/DerivedData` cleaned before build. |
| APNs entitlements/signing metadata | PASS | iOS, macOS, widget and watch entitlement files found. |
| Xcode account/development signing | PASS | Xcode accepted automatic provisioning access for `DJConnectIOS`; team `ZEML4LPXH4`, bundle `dev.djconnect.ios`. |
| Distribution signing assets | SKIPPED | App Store/TestFlight signing remains deferred to release v1.0 readiness and is non-blocking for current platform verification. |
| Release-equivalent build | PASS | `xcodebuild ... -configuration Release ... CODE_SIGNING_ALLOWED=NO clean build` succeeded. |
| Simulator target | PASS | Prepared target `DJConnect Monkey iPhone 13 mini iOS 26.5` on `com.apple.CoreSimulator.SimRuntime.iOS-26-5`. |
| Cross-device simulator targets | SKIPPED | No cross-device target set configured for this retry. |
| Physical-device target | SKIPPED | Physical-device execution remains explicit opt-in. |
| Install app | PASS | `simctl install` succeeded. |
| Launch app | PASS | `simctl launch dev.djconnect.ios` succeeded. |
| Screenshot | PASS | Screenshot captured and persisted. |
| Scoped log collection | PASS | Simulator log excerpt collected. |
| UI automation healthcheck | PASS | `DJConnectIOSUITests.testPrimaryTabsAreAvailable` passed. |

## Fixes Applied

- Added canonical Apple runtime smoke scenario `APPLE-001`, scoped to Apple
  runtime primitives and evidence collection.
- Smoke planning now retains adapter diversity when reducing large scenario
  sets, so the first Apple adapter executable scenario is no longer dropped.
- Verification CLI now supports `--apple-adapter` for scenario execution.
- CLI env files are loaded for all commands, so `execute --env-file ...` makes
  prepared Apple target JSON available to the adapter.
- Execution Environment gates are scenario-aware: Apple-only runs skip HA lab
  and Docker runtime gates while preserving GitHub, dependency, cleanup and
  secret gates.
- Apple adapter now boots the configured simulator and waits for
  `simctl bootstatus -b` before simulator install, launch, screenshot and log
  collection primitives.
- Runtime qualification now terminates the primitive app launch before XCTest,
  so UI tests launch with their configured arguments.
- Gate status now treats policy-deferred distribution signing, cross-device
  simulator targets and physical-device targets as non-blocking `SKIPPED`
  checks for current platform verification.
- The Apple app test path clears stale crash-prompt state during `--uitesting`
  launches while preserving production crash detection.
- The primary-tabs UI healthcheck is scoped to primary tabbar availability;
  deeper More navigation remains separate UI coverage.

## Crash Log Analysis

The earlier screenshot showed the Dutch crash-recovery prompt:

```text
De app is mogelijk gecrasht
```

Per the operator note, previous-run crash evidence was inspected before
classifying the failure. No DJConnect simulator CrashReporter file was found.
The app persistent log showed normal launch/demo-mode messages rather than a
fresh crash stack. The blocker was stale crash-prompt UserDefaults state from a
prior unclean launch, not a confirmed new runtime crash.

## Scenario Selection

After the runtime gate passed, planning was executed with the verification venv:

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli plan --strategy smoke --policy smoke --format json
```

Planner result:

| Metric | Value |
| --- | --- |
| Total selected cases | 45 |
| HA cases | 44 |
| Apple adapter cases | 1 |
| Executes adapters | false |

The selected Apple adapter case is `APPLE-001`. The scenario is Apple-only and
therefore does not invent HA/backend product assertions inside the adapter.
Broader cross-runtime scenarios remain future coverage work.

## Phase 10E Retry Scenario Execution

Selected scenario:

```text
APPLE-001
```

Execution command:

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli --env-file artifacts/verification/apple/phase10e.env --apple-adapter execute --scenario-id APPLE-001
```

Result:

```text
execute: 1 of 1 tests executed, status PASS (1 PASS), total 2.02s
```

Scenario run id:

```text
djv-20260711T222533Z-fe2a0bcda5
```

The run executed through the Scenario Engine and Apple adapter. Environment
gates skipped HA lab and Docker runtime checks because `APPLE-001` does not
require Home Assistant or Docker. GitHub exact-SHA CI, workflow discovery,
dependency inspection, cleanup planning and secret-name loading gates passed.

## Tests Run

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m unittest tests.verification.test_planning_engine tests.verification.test_apple_adapter tests.verification.test_execution_environment
```

Result:

```text
Ran 54 tests in 18.664s
OK
```

Runtime qualification:

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli --env-file artifacts/verification/apple/phase10e.env apple qualify-runtime
```

Result:

```text
state: PASS
broad_scenario_execution_allowed: true
run_id: apple10e-20260711T222229Z-657e8945b1
```

Scenario catalog validation:

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli validate
```

Result:

```text
validated 232 scenarios
```

## Classification

Primary class: Qualified with warnings.

Confidence: high.

Owner: Verification Platform.

Blocking: no for the next adapter phase.

Warnings:

- Apple coverage is limited to the first runtime-smoke scenario set.
- Broader Apple product/UI scenarios remain future coverage work.
- watchOS paired simulator orchestration remains deferred.
- Physical-device execution remains explicit opt-in and was skipped.
- App Store/TestFlight distribution signing remains deferred to release v1.0
  readiness.

## Completion Decision

Phase 10E-R3 qualifies the first Apple scenario coverage set with non-blocking
warnings:

```text
APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS
```

Do not start Phase 11 automatically. Continue only from the generated Phase 11
prompt in a clean session.
