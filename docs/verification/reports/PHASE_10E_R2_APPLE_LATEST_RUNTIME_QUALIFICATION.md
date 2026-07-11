# Phase 10E-R2 Apple Latest Runtime Qualification

Status: APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED
Date: 2026-07-11

## Executive Summary

Phase 10E-R2 implements the stricter Apple runtime prerequisite requested by
the operator: before Apple verification runs, the local Xcode/iOS simulator
toolchain must be checked and the Phase 10E runtime gate must use the latest
locally available iOS simulator runtime.

The new toolchain maintenance gate passed. Local Xcode reported:

```text
Xcode 26.6
Build version 17F113
```

`softwareupdate --list` reported no available Xcode update, and
`xcodebuild -downloadPlatform iOS` completed. The latest locally available iOS
simulator runtime is iOS 27.0.

The full Apple Runtime Qualification was then rerun against an iPhone 17 Pro
iOS 27.0 simulator. Release-equivalent build, install, launch, screenshot and
scoped log evidence passed, but the integrated XCTest UI healthcheck timed out.
After follow-up review, the gate was tightened further so
`DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA` is cleaned before every
release-equivalent build and only approved verification scratch roots may be
used for that cleanup.

Decision:

```text
APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED
```

Broad Apple scenario coverage remains blocked until the iOS 27.0/latest-runtime
qualification run passes or the integrated XCTest timeout is remediated and
classified with evidence.

## Evidence

Toolchain maintenance evidence:

```text
artifacts/verification/evidence/appletoolchain-20260711T120519Z-d8c912c54e/
```

Primary machine-readable toolchain evidence:

```text
artifacts/verification/evidence/appletoolchain-20260711T120519Z-d8c912c54e/apple/toolchain-ensure-ios-runtime.json
```

Blocked latest-runtime qualification evidence:

```text
artifacts/verification/evidence/apple10e-20260711T121537Z-9c692b98a7/
```

Primary machine-readable runtime evidence:

```text
artifacts/verification/evidence/apple10e-20260711T121537Z-9c692b98a7/apple/runtime-qualification.json
```

## Runtime Configuration

Apple source repository:

```text
/Users/pcvantol/Documents/GitHub/djconnect-app
```

Latest selected simulator:

```text
iPhone 17 Pro
iOS 27.0
90318F40-1066-4B89-B4D0-CD0EA9A5C435
```

Bundle id:

```text
dev.djconnect.ios
```

## Gate Results

| Check | Result | Notes |
| --- | --- | --- |
| Toolchain maintenance | PASS | Xcode 26.6 was present, Software Update advertised no Xcode update, and `xcodebuild -downloadPlatform iOS` completed. |
| Latest iOS runtime discovery | PASS | Latest local runtime resolved to `com.apple.CoreSimulator.SimRuntime.iOS-27-0`. |
| Release-equivalent build | PASS | Release simulator build completed for the iOS 27.0 target. |
| APNs entitlements/signing metadata | PASS | Entitlement files were discovered. |
| Simulator target | PASS | Prepared target JSON used the latest locally available iOS runtime. |
| Physical-device target | SKIPPED | Physical-device execution remains explicit opt-in. |
| DerivedData isolation | PASS | Latest-runtime rerun used isolated DerivedData paths; the gate now cleans the configured DerivedData path before each release-equivalent build. |
| Install app | PASS | The app artifact installed on the iOS 27.0 simulator. |
| Launch app | PASS | `xcrun simctl launch dev.djconnect.ios` returned pid `38568`. |
| Screenshot | PASS | Simulator screenshot was captured and persisted. |
| Scoped log collection | PASS | Adapter operation logs and simulator log excerpt were persisted and redacted. |
| UI automation healthcheck | FAIL | Integrated XCTest healthcheck timed out after 600 seconds. |

## Implementation Changes

Added a maintenance CLI:

```bash
python3 -m tools.verification.cli apple ensure-ios-runtime
```

This command records Xcode version, checks macOS Software Update, runs:

```bash
xcodebuild -downloadPlatform iOS
```

and persists the latest locally available iOS simulator runtime in evidence.

The Phase 10E Apple Runtime Qualification gate now fails closed when
`DJCONNECT_VERIFICATION_APPLE_TARGET_JSON` points at a simulator that is not on
the latest locally available iOS runtime.

The gate also fails closed unless `DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA`
is an absolute path under `/private/tmp`, `/tmp` or this repository's
`artifacts/verification` scratch tree. Approved DerivedData paths are removed
and recreated before the release-equivalent build command runs.

## Tests And Commands Run

Verification unit tests:

```bash
python3 -m unittest tests.verification.test_apple_adapter
```

Result:

```text
13 tests passed
```

Toolchain maintenance gate:

```bash
python3 -m tools.verification.cli apple ensure-ios-runtime
```

Result:

```text
PASS
```

Latest-runtime qualification gate:

```bash
python3 -m tools.verification.cli apple qualify-runtime
```

Result:

```text
BLOCKED
```

## Classification

Primary class: Apple verification execution environment / XCTest sequencing
blocker.

Confidence: medium.

Owner: Verification Execution Environment / Apple Adapter.

Blocking: yes for broad Apple scenario execution and Phase 10E retry.

## Completion Decision

Phase 10E-R2 is not complete:

```text
APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED
```

Continue Phase 10E-R2 by remediating the integrated XCTest healthcheck timeout
on the latest locally available iOS runtime. Do not begin Phase 10E retry or
Phase 11 yet.
