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
`xcodebuild -downloadPlatform iOS` completed. The machine also had an iOS 27.0
simulator runtime installed, but iOS 27.0 is beta on 2026-07-11 and is not the
default stable qualification target.

The full Apple Runtime Qualification was then rerun against an iPhone 17 Pro
iOS 27.0 simulator as future/beta evidence. Release-equivalent build, install,
launch, screenshot and scoped log evidence passed, but the integrated XCTest UI
healthcheck timed out.
After follow-up review, the gate was tightened further so
`DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA` is cleaned before every
release-equivalent build and only approved verification scratch roots may be
used for that cleanup. A second follow-up tightened release signing: the gate
now requires the configured Apple Distribution identity to be present in the
keychain and a matching provisioning profile to be available before the
release-equivalent build command can run. A third follow-up added an explicit
cross-device target-set gate for multi-device or multi-iOS scenario batches.
A fourth follow-up added explicit future/beta runtime channels for Xcode beta
and Home Assistant beta, separated from stable qualification evidence.

Decision:

```text
APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED
```

Broad Apple scenario coverage remains blocked until the stable latest-eligible
runtime qualification passes. iOS 27.0 remains available only for the
`future_beta` route until it is the official stable iOS runtime.

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

Future/beta selected simulator from the blocked evidence:

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
| Future/beta channel isolation | Tightened after run | Xcode beta and Home Assistant beta now require `DJCONNECT_VERIFICATION_TEST_MODE=future_beta` and produce separate advisory evidence. |
| Latest iOS runtime discovery | Updated after run | Stable mode now selects the latest eligible stable iOS runtime and excludes iOS 27.0 beta by default. `future_beta` mode may select `com.apple.CoreSimulator.SimRuntime.iOS-27-0`. |
| APNs entitlements/signing metadata | PASS | Entitlement files were discovered. |
| Distribution signing assets | Tightened after run | Future runs require matching Apple Distribution identity, team id, bundle id and provisioning profile metadata before release build. |
| Release-equivalent build | PASS | Release simulator build completed for the future/beta iOS 27.0 target in the blocked evidence run. |
| Simulator target | Updated after run | Prepared target JSON must use the latest eligible iOS runtime for the active verification mode. Stable mode excludes beta runtimes by default. |
| Cross-device simulator targets | Tightened after run | Future cross-device or multi-iOS batches require every configured simulator UDID and declared runtime version to be available before execution. |
| Physical-device target | SKIPPED | Physical-device execution remains explicit opt-in. |
| DerivedData isolation | PASS | Latest-runtime rerun used isolated DerivedData paths; the gate now cleans the configured DerivedData path before each release-equivalent build. |
| Install app | PASS | The app artifact installed on the iOS 27.0 simulator. |
| Launch app | PASS | `xcrun simctl launch dev.djconnect.ios` returned pid `38568`. |
| Screenshot | PASS | Simulator screenshot was captured and persisted. |
| Scoped log collection | PASS | Adapter operation logs and simulator log excerpt were persisted and redacted. |
| UI automation healthcheck | FAIL | Integrated XCTest healthcheck timed out after 600 seconds in the original blocked run; the active default timeout is now 180 seconds and remains overrideable with `DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_TIMEOUT`. |

## Implementation Changes

Added a maintenance CLI:

```bash
python3 -m tools.verification.cli apple ensure-ios-runtime
```

This command records Xcode version, checks macOS Software Update, runs:

```bash
xcodebuild -downloadPlatform iOS
```

and persists the latest eligible iOS simulator runtime in evidence.

The Phase 10E Apple Runtime Qualification gate now fails closed when
`DJCONNECT_VERIFICATION_APPLE_TARGET_JSON` points at a simulator that is not on
the latest eligible iOS runtime for the active verification mode. In default
stable mode, iOS 27.0 is excluded while it is beta; `future_beta` mode can verify
against it explicitly.

The default stable iOS major ceiling is `26` for this evidence date. It can be
advanced explicitly with `DJCONNECT_VERIFICATION_STABLE_IOS_MAJOR_VERSION` once
Apple releases a newer iOS major as stable.

The gate also fails closed unless `DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA`
is an absolute path under `/private/tmp`, `/tmp` or this repository's
`artifacts/verification` scratch tree. Approved DerivedData paths are removed
and recreated before the release-equivalent build command runs.

The gate now requires these release signing expectations before the build can
run:

```text
DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY
DJCONNECT_VERIFICATION_APPLE_TEAM_ID
DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID
DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE
```

It verifies the signing identity with:

```bash
security find-identity -v -p codesigning
```

and scans provisioning profiles from
`~/Library/MobileDevice/Provisioning Profiles` unless
`DJCONNECT_VERIFICATION_APPLE_PROFILES_DIR` is set. Evidence records only
metadata needed to prove the match; it does not persist private keys,
certificate material or full profile payloads.

For cross-device or multi-iOS scenario batches, the gate accepts:

```text
DJCONNECT_VERIFICATION_APPLE_TARGETS_JSON
```

This is a JSON list of required simulator targets. Each target must include a
UDID, and may include `ios_version` or `runtime_version`. When configured, the
gate verifies every listed simulator is present in
`xcrun simctl list devices available --json` and that declared runtime versions
match the discovered CoreSimulator runtime.

Future/beta runtime verification is available only with explicit opt-in:

```text
DJCONNECT_VERIFICATION_TEST_MODE=future_beta
```

Xcode beta additionally requires:

```text
DJCONNECT_VERIFICATION_XCODE_CHANNEL=beta
DJCONNECT_VERIFICATION_XCODE_BETA_DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
```

Home Assistant beta additionally requires:

```text
DJCONNECT_VERIFICATION_HA_CHANNEL=beta
```

The HA beta lab uses a separate default container, port and lab root from the
stable lab. Beta/future evidence is advisory early-warning evidence and must
not replace stable release qualification.

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

Continue Phase 10E-R2 by remediating or rerunning the integrated XCTest
healthcheck on the latest eligible stable iOS runtime. Do not begin Phase 10E
retry or Phase 11 yet.
