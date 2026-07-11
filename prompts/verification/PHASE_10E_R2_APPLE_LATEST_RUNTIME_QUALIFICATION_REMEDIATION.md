# Phase 10E-R2 Apple Latest Runtime Qualification Remediation

## Objective

Remediate and rerun Apple Runtime Qualification using the latest locally
available iOS simulator runtime.

## Required Context

Read:

1. `BOOTSTRAP_CODEX_VERIFICATION.md`
2. `PROMPT_INDEX.md`
3. `docs/verification/reports/PHASE_10E_R2_APPLE_LATEST_RUNTIME_QUALIFICATION.md`
4. `docs/verification/reports/PHASE_10E_R_APPLE_RUNTIME_QUALIFICATION_REMEDIATION.md`
5. `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`
6. `docs/verification/10_APPLE_VERIFICATION_ADAPTER.md` if present, otherwise the Phase 10 Apple adapter report

## Mandatory Gates

Run the Apple toolchain maintenance gate before runtime qualification:

```bash
python3 -m tools.verification.cli apple ensure-ios-runtime
```

Stable runtime qualification is the default. Future/beta runtime verification
must run in a separate mode:

```bash
DJCONNECT_VERIFICATION_TEST_MODE=future_beta \
DJCONNECT_VERIFICATION_XCODE_CHANNEL=beta \
DJCONNECT_VERIFICATION_XCODE_BETA_DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
python3 -m tools.verification.cli apple ensure-ios-runtime
```

Home Assistant beta verification must also be explicitly isolated:

```bash
DJCONNECT_VERIFICATION_TEST_MODE=future_beta \
DJCONNECT_VERIFICATION_HA_CHANNEL=beta \
python3 -m tools.verification.cli lab ha fresh
```

Beta/future results are advisory early-warning evidence and must not replace
stable release qualification evidence.

Then rerun Apple Runtime Qualification against a simulator from the latest
locally available iOS runtime:

```bash
python3 -m tools.verification.cli apple qualify-runtime
```

The runtime gate must fail closed if the configured target JSON does not use
the latest locally available iOS runtime.

For cross-device or multi-iOS scenario batches, configure
`DJCONNECT_VERIFICATION_APPLE_TARGETS_JSON` with all required simulator
targets. The gate must verify each configured simulator UDID is available and
that any declared `ios_version` or `runtime_version` matches the discovered
CoreSimulator runtime before the batch can run.

The runtime gate must also clean `DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA`
before every release-equivalent build. Use only an absolute DerivedData path
under `/private/tmp`, `/tmp` or `artifacts/verification`; any other cleanup
target must fail closed.

The runtime gate must verify release signing assets before the
release-equivalent build command runs. Configure the expected Apple
Distribution identity, team id, bundle id and provisioning profile with:

```text
DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY
DJCONNECT_VERIFICATION_APPLE_TEAM_ID
DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID
DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE
```

Profiles are discovered in `~/Library/MobileDevice/Provisioning Profiles` by
default, or in `DJCONNECT_VERIFICATION_APPLE_PROFILES_DIR` when set. Persist
only metadata proving the match; do not persist private keys, certificate
material or full profile payloads.

## Stop Conditions

Stop and report blocked if:

- Xcode is unavailable.
- macOS Software Update or Xcode reports an operator-required Xcode update that
  cannot be applied from the session.
- `xcodebuild -downloadPlatform iOS` fails.
- No available iOS simulator runtime exists.
- A cross-device or multi-iOS target set is configured but any required
  simulator UDID or declared iOS runtime version is unavailable.
- The DerivedData path is missing, relative or outside the approved verification
  scratch roots.
- The expected Apple Distribution identity is missing from the keychain.
- No provisioning profile matches the configured profile name/UUID, team id and
  bundle id.
- The latest-runtime XCTest healthcheck still times out after remediation.

## Completion Criteria

Phase 10E-R2 may report:

```text
APPLE_LATEST_RUNTIME_QUALIFIED
```

only when the latest-runtime qualification passes release-equivalent build,
entitlements metadata, distribution signing assets, simulator target freshness,
configured cross-device simulator availability, isolated DerivedData, install,
launch, screenshot, scoped log collection and UI automation healthcheck.

Do not begin Phase 10E retry or Phase 11 until this phase returns
`APPLE_LATEST_RUNTIME_QUALIFIED`.
