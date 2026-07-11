# Phase 10E Apple Scenario Coverage Expansion

Status: APPLE_RUNTIME_QUALIFIED_SCENARIO_SELECTION_BLOCKED
Date: 2026-07-11

## Executive Summary

Phase 10E retry executed the mandatory Apple Runtime Qualification gate before
any broad Apple scenario batch. The latest eligible stable runtime is iOS 26.5
on simulator target `DJConnect Monkey iPhone 13 mini iOS 26.5`.

The Apple runtime gate now passes. Release-equivalent simulator build, isolated
DerivedData cleanup, entitlement discovery, Xcode account/development signing,
simulator install, launch, screenshot, scoped log collection and XCTest UI
healthcheck all completed successfully.

Broad Apple scenario execution was not started. After the runtime gate passed,
the canonical smoke planner still selected only HA cases and produced no Apple
adapter executable scenario set. Phase 10E is therefore blocked on
verification planning/adapter mapping, not on Xcode, CoreSimulator or iOS app
startup.

Current decision:

```text
APPLE_RUNTIME_QUALIFIED_SCENARIO_SELECTION_BLOCKED
```

## Evidence

Latest successful runtime qualification evidence:

```text
artifacts/verification/evidence/apple10e-20260711T215124Z-d64d7aa157/
```

Latest screenshot evidence:

```text
artifacts/verification/evidence/apple10e-20260711T215124Z-d64d7aa157/apple/phase-10e-runtime-qualification.png
```

Toolchain maintenance evidence:

```text
artifacts/verification/evidence/appletoolchain-20260711T210854Z-a1d2f84c66/
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
| Total selected cases | 44 |
| HA cases | 44 |
| Apple adapter cases | 0 |
| Executes adapters | false |

The planner records `apple.runtime` in lab requirements, but the selected smoke
execution plan still contains only Home Assistant cases. No Apple executable
scenario set was available to run without inventing expected behavior outside
the canonical scenario/planner mapping.

## Tests Run

```bash
python3 -m unittest tests.verification.test_apple_adapter
```

Result:

```text
Ran 26 tests in 4.068s
OK
```

Runtime qualification:

```bash
python3 -m tools.verification.cli --env-file artifacts/verification/apple/phase10e.env apple qualify-runtime
```

Result:

```text
state: PASS
broad_scenario_execution_allowed: true
run_id: apple10e-20260711T215124Z-d64d7aa157
```

## Classification

Primary class: Verification planning/adapter mapping blocker.

Confidence: high.

Owner: Verification Platform.

Blocking: yes, for broad Apple scenario coverage.

Recommended action: add or map canonical Apple adapter executable scenario
cases so the planner can select an Apple scenario set after runtime
qualification. Do not begin Phase 11 automatically.

## Completion Decision

Phase 10E retry completed the runtime qualification portion successfully but
did not complete broad Apple scenario coverage:

```text
APPLE_RUNTIME_QUALIFIED_SCENARIO_SELECTION_BLOCKED
```

Do not start Phase 11. Continue only with a Phase 10E follow-up that maps
canonical scenarios to Apple adapter executable cases.
