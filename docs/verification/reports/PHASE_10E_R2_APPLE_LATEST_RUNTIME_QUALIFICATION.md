# Phase 10E-R2 Apple Latest Runtime Qualification

Status: APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED
Date: 2026-07-11

## Executive Summary

Phase 10E-R2 implements the stricter Apple runtime prerequisite requested by
the operator: before Apple verification runs, the local Xcode/iOS simulator
toolchain must be checked and the Phase 10E runtime gate must use the latest
eligible stable iOS simulator runtime by default.

The new toolchain maintenance gate passed. Local Xcode reported:

```text
Xcode 26.6
Build version 17F113
```

`softwareupdate --list` reported no available Xcode update, and
`xcodebuild -downloadPlatform iOS` completed. The initial evidence also had an
iOS 27.0 simulator runtime installed, but iOS 27.0 is beta on 2026-07-11 and is
not the default stable qualification target.

The full Apple Runtime Qualification was then rerun against an iPhone 17 Pro
iOS 27.0 simulator as future/beta evidence. Release-equivalent build, install,
launch, screenshot and scoped log evidence passed, but the integrated XCTest UI
healthcheck timed out.
After follow-up review, the gate was tightened further so
`DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA` is cleaned before every
release-equivalent build and only approved verification scratch roots may be
used for that cleanup. A second follow-up added explicit signing gates:
`xcode_account` must prove Xcode automatic provisioning access before live
runtime work, while App Store/TestFlight distribution signing is tracked as a
release-v1.0 readiness concern rather than a blocker for current platform
verification. A third follow-up added an explicit
cross-device target-set gate for multi-device or multi-iOS scenario batches.
A fourth follow-up added explicit future/beta runtime channels for Xcode beta
and Home Assistant beta, separated from stable qualification evidence.

Decision:

```text
APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED
```

This is historical evidence from before the VPB-037 rescope. Broad Apple
scenario coverage can continue with the Xcode account/development-signing gate,
latest eligible simulator target and prepared XCTest healthcheck. iOS 27.0
remains available only for the `future_beta` route until it is the official
stable iOS runtime.

The latest rerun on 2026-07-11 refreshed the stable toolchain gate. Xcode 26.6
remained selected, `softwareupdate --list` reported no Xcode update, and
`xcodebuild -downloadPlatform iOS` resolved iOS 26.5 as the latest eligible
stable simulator runtime. Runtime qualification then failed closed before live
mutation because this shell did not provide the required operator configuration:
isolated DerivedData, prepared Apple target JSON, distribution signing
expectations and UI healthcheck command/driver. Later follow-up work prepared
the Xcode account/development-signing path and rescoped App Store/TestFlight
distribution signing to release-v1.0 readiness.

## Evidence

Toolchain maintenance evidence:

```text
artifacts/verification/evidence/appletoolchain-20260711T120519Z-d8c912c54e/
```

Latest stable toolchain maintenance rerun:

```text
artifacts/verification/evidence/appletoolchain-20260711T152806Z-b88e218cd8/
```

Primary machine-readable toolchain evidence:

```text
artifacts/verification/evidence/appletoolchain-20260711T120519Z-d8c912c54e/apple/toolchain-ensure-ios-runtime.json
```

Blocked latest-runtime qualification evidence:

```text
artifacts/verification/evidence/apple10e-20260711T121537Z-9c692b98a7/
```

Latest stable-runtime qualification rerun:

```text
artifacts/verification/evidence/apple10e-20260711T152822Z-a6328549f9/
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

Latest stable runtime from the rerun:

```text
iOS 26.5
com.apple.CoreSimulator.SimRuntime.iOS-26-5
```

Available iOS 26.5 simulator targets included:

```text
iPhone 17 Pro - 7B10306E-5AC5-46F6-96AC-5F4C592BA85B
DJConnect Monkey iPhone 13 mini iOS 26.5 - D1DDCACC-2651-4EB9-A55E-2315C9314AA6
```

Bundle id:

```text
dev.djconnect.ios
```

## Gate Results

| Check | Result | Notes |
| --- | --- | --- |
| Toolchain maintenance | PASS | Xcode 26.6 was present, Software Update advertised no Xcode update, and `xcodebuild -downloadPlatform iOS` completed. Latest rerun resolved iOS 26.5 as stable. |
| Future/beta channel isolation | Tightened after run | Xcode beta and Home Assistant beta now require `DJCONNECT_VERIFICATION_TEST_MODE=future_beta` and produce separate advisory evidence. |
| Latest iOS runtime discovery | PASS | Stable mode selected iOS 26.5 in the latest rerun and excludes iOS 27.0 beta by default. `future_beta` mode may select `com.apple.CoreSimulator.SimRuntime.iOS-27-0`. |
| APNs entitlements/signing metadata | PASS | Entitlement files were discovered. |
| Distribution signing assets | BLOCKED | Latest rerun did not provide `DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY`, `DJCONNECT_VERIFICATION_APPLE_TEAM_ID`, `DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID` or `DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE`. |
| Release-equivalent build | BLOCKED | Latest rerun skipped the build because isolated DerivedData and distribution signing assets were not configured. |
| Simulator target | BLOCKED | Latest rerun did not provide `DJCONNECT_VERIFICATION_APPLE_TARGET_JSON`; no live install/launch target was available. |
| Cross-device simulator targets | Tightened after run | Future cross-device or multi-iOS batches require every configured simulator UDID and declared runtime version to be available before execution. |
| Physical-device target | SKIPPED | Physical-device execution remains explicit opt-in. |
| DerivedData isolation | BLOCKED | Latest rerun did not provide `DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA`; the gate stopped before cleanup/build. |
| Install app | BLOCKED | No prepared target/app artifact was available after the simulator target gate blocked. |
| Launch app | BLOCKED | No prepared target/app artifact was available after the simulator target gate blocked. |
| Screenshot | BLOCKED | No prepared simulator target was available. |
| Scoped log collection | BLOCKED | No runtime log evidence was produced because runtime execution did not start. |
| UI automation healthcheck | BLOCKED | Latest rerun did not provide `DJCONNECT_VERIFICATION_APPLE_UI_DRIVER` and `DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND`. |

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

Latest stable rerun:

```bash
python3 -m tools.verification.cli apple ensure-ios-runtime
python3 -m tools.verification.cli apple qualify-runtime
```

Result:

```text
Toolchain maintenance: PASS
Latest stable runtime: iOS 26.5
Runtime qualification: BLOCKED
```

## Classification

Primary class: Apple verification execution environment / operator
configuration blocker.

Confidence: medium.

Owner: Verification Execution Environment / operator Apple signing and runtime
configuration.

Blocking: yes for broad Apple scenario execution and Phase 10E retry.

## Completion Decision

Phase 10E-R2 execution is complete for this branch and closed with the
following decision:

```text
APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED
```

This historical run is not an Apple coverage qualification. Later follow-up work
resolved the current platform-verification blocker by proving the Xcode
account/development-signing path and preparing the simulator/XCTest
configuration. Continue with Phase 10E retry; App Store/TestFlight distribution
signing remains deferred to release-v1.0 readiness.

## Follow-Up Backlog

The close-out follow-ups are tracked in
`docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`:

- `VPB-031`: resolved by `djconnect-app` commit `9d305764` on `main` and
  `origin/main`.
- `VPB-036`: resolved for the local stable runtime path by
  `apple prepare-qualification-config`, which selected iOS 26.5 simulator
  `D1DDCACC-2651-4EB9-A55E-2315C9314AA6` and the approved DerivedData path
  under `artifacts/verification/apple/DerivedData`.
- `VPB-037`: resolved for current platform verification. Follow-up evidence on
  July 11, 2026 proved the Xcode account/development-signing path with Xcode 27
  beta, team `ZEML4LPXH4`, bundle `dev.djconnect.ios`, signing identity
  `Apple Development: Peter van Tol (4R93ZR43D5)` and provisioning profile
  `iOS Team Provisioning Profile: dev.djconnect.ios`
  (`00d91f4f-5a9e-4f13-8790-2393253068e7`). App Store/TestFlight distribution
  signing is deferred until release v1.0 readiness and is non-blocking for this
  platform verification phase.
- `VPB-038`: resolved by `apple prepare-qualification-config`, which emits an
  XCTest UI healthcheck command for the latest-stable simulator. The runtime
  gate now skips live UI healthcheck when prerequisite signing/build/target
  gates are blocked.

## Follow-Up Rerun

The follow-up rerun on July 11, 2026 produced:

```text
APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED
```

Evidence:

- toolchain gate passed with Xcode 26.6, no Software Update Xcode update, and
  iOS 26.5 resolved by `xcodebuild -downloadPlatform iOS`;
- config preparation resolved `VPB-036` and `VPB-038`;
- runtime qualification evidence
  `artifacts/verification/evidence/apple10e-20260711T184303Z-61c57ca54d/`
  passed DerivedData isolation, APNs entitlement discovery and latest-stable
  simulator target freshness;
- the historical runtime qualification blocked on missing distribution signing
  expectations, but that App Store/TestFlight path has since been rescoped to
  release-v1.0 readiness. Continue current platform verification with the
  Xcode account/development-signing gate and prepared simulator/XCTest
  configuration.
