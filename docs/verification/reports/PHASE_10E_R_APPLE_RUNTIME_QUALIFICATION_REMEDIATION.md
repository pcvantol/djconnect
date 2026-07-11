# Phase 10E-R Apple Runtime Qualification Remediation

Status: APPLE_RUNTIME_QUALIFIED_ON_SELECTED_RUNTIME; SUPERSEDED_BY_LATEST_RUNTIME_GATE
Date: 2026-07-11

## Executive Summary

Phase 10E-R remediated the Apple Runtime Qualification blocker from Phase 10E.

The mandatory Apple runtime gate now passes with a release-equivalent simulator
build, isolated DerivedData, prepared iPhone simulator target JSON, app install,
app launch, screenshot evidence, scoped log evidence and XCTest UI automation
healthcheck.

Decision:

```text
APPLE_RUNTIME_QUALIFIED
```

Later in the same branch, the operator tightened the Apple prerequisite:
verification must always check the current Xcode/iOS simulator platform and use
the latest locally available iOS simulator runtime. That stricter requirement
supersedes this report as the active Apple runtime gate. See:

```text
docs/verification/reports/PHASE_10E_R2_APPLE_LATEST_RUNTIME_QUALIFICATION.md
```

Broad Apple scenario execution may now be selected by the Planning Engine in a
Phase 10E retry only after Phase 10E-R2 returns
`APPLE_LATEST_RUNTIME_QUALIFIED`. Phase 11 must not start until Apple scenario
coverage itself has run and reported.

## Evidence

Runtime qualification evidence:

```text
artifacts/verification/evidence/apple10e-20260711T115656Z-4cea94c38f/
```

Primary machine-readable evidence:

```text
artifacts/verification/evidence/apple10e-20260711T115656Z-4cea94c38f/apple/runtime-qualification.json
```

Screenshot evidence:

```text
artifacts/verification/evidence/apple10e-20260711T115656Z-4cea94c38f/apple/phase-10e-runtime-qualification.png
```

## Runtime Configuration

Apple source repository:

```text
/Users/pcvantol/Documents/GitHub/djconnect-app
```

Selected simulator:

```text
iPhone 17 Pro
iOS 26.4
D2980B6D-3BA5-4C1D-84E8-3F9819ACE10E
```

Isolated DerivedData:

```text
/private/tmp/djconnect-phase10er-derived
```

Qualified app artifact:

```text
/private/tmp/djconnect-phase10er-derived/Build/Products/Release-iphonesimulator/DJConnect.app
```

Bundle id:

```text
dev.djconnect.ios
```

UI healthcheck:

```text
XCTest
DJConnectIOSUITests/DJConnectIOSUITests/testMonkeyModeSafeNavigationSmoke
```

Physical-device execution remained explicitly skipped because no physical
device opt-in was configured.

## Gate Results

| Check | Result | Notes |
| --- | --- | --- |
| Release-equivalent build | PASS | `xcodebuild` Release simulator build completed with isolated DerivedData. |
| APNs entitlements/signing metadata | PASS | Entitlement files were discovered for iOS, macOS, widgets and watchOS. |
| Simulator target | PASS | Prepared target JSON selected the iPhone 17 Pro simulator. |
| Physical-device target | SKIPPED | Physical-device execution remains explicit opt-in. |
| DerivedData isolation | PASS | Phase 10E-R used `/private/tmp/djconnect-phase10er-derived`. |
| Install app | PASS | `xcrun simctl install` installed the qualified artifact. |
| Launch app | PASS | `xcrun simctl launch dev.djconnect.ios` returned pid `21091`. |
| Screenshot | PASS | Simulator screenshot was captured and persisted. |
| Scoped log collection | PASS | Adapter operation logs and simulator log excerpt were persisted and redacted. |
| UI automation healthcheck | PASS | Existing iOS XCTest monkey navigation smoke test completed with return code `0`. |

## Remediation Work

The first Release simulator build failed in the Apple client repository because
Swift 6 required exhaustive handling for `DJConnectError.profile`.

Local Apple source fix applied:

```text
Sources/DJConnectUI/DJConnectAppModel.swift
```

The watch proxy error-code mapper now maps profile errors to:

```text
profile_error
```

That cross-repository source change must be committed in `pcvantol/djconnect-app`
before Phase 10E retry evidence is considered reproducible from a clean clone.

## Tests And Commands Run

Apple Release simulator build:

```bash
xcodebuild -quiet -project DJConnectApp.xcodeproj -scheme DJConnectIOS -configuration Release -destination 'id=D2980B6D-3BA5-4C1D-84E8-3F9819ACE10E' -derivedDataPath /private/tmp/djconnect-phase10er-derived CODE_SIGNING_ALLOWED=NO build
```

iOS XCTest UI healthcheck:

```bash
xcodebuild -quiet -project DJConnectApp.xcodeproj -scheme DJConnectIOS -configuration Debug -destination 'id=D2980B6D-3BA5-4C1D-84E8-3F9819ACE10E' -derivedDataPath /private/tmp/djconnect-phase10er-ui-derived -only-testing:DJConnectIOSUITests/DJConnectIOSUITests/testMonkeyModeSafeNavigationSmoke test
```

Phase 10E-R runtime gate:

```bash
python3 -m tools.verification.cli apple qualify-runtime
```

Result:

```text
PASS
```

## Classification

Primary class: product implementation defect in Apple client source, plus
operator/runtime configuration gap remediated by this phase.

Confidence: high.

Owner: Apple Client / Verification Execution Environment.

Blocking: no for Apple runtime qualification after the Apple client source fix
is preserved; yes for clean reproducibility until the `djconnect-app` fix is
committed.

## Completion Decision

Phase 10E-R is complete for the originally selected runtime:

```text
APPLE_RUNTIME_QUALIFIED
```

The active prerequisite is now Phase 10E-R2 latest-runtime qualification.
Continue there before Phase 10E retry. Do not begin Phase 11 yet.
