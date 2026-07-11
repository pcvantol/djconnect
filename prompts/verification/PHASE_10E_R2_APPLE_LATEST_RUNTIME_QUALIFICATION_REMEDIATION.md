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

Then rerun Apple Runtime Qualification against a simulator from the latest
locally available iOS runtime:

```bash
python3 -m tools.verification.cli apple qualify-runtime
```

The runtime gate must fail closed if the configured target JSON does not use
the latest locally available iOS runtime.

## Stop Conditions

Stop and report blocked if:

- Xcode is unavailable.
- macOS Software Update or Xcode reports an operator-required Xcode update that
  cannot be applied from the session.
- `xcodebuild -downloadPlatform iOS` fails.
- No available iOS simulator runtime exists.
- The latest-runtime XCTest healthcheck still times out after remediation.

## Completion Criteria

Phase 10E-R2 may report:

```text
APPLE_LATEST_RUNTIME_QUALIFIED
```

only when the latest-runtime qualification passes release-equivalent build,
entitlements metadata, simulator target freshness, isolated DerivedData,
install, launch, screenshot, scoped log collection and UI automation
healthcheck.

Do not begin Phase 10E retry or Phase 11 until this phase returns
`APPLE_LATEST_RUNTIME_QUALIFIED`.
