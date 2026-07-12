# Coverage Baseline Report

Status: CROSS_PLATFORM_COVERAGE_BASELINE_ESTABLISHED
Date: 2026-07-12

Coverage Baseline 1 used only Verification Runtime `1.1.0` and Docker image
`pcvantol/djconnect-verification-platform:1.1.0`.

Immutable image digest:

```text
sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619
```

## Qualification

Home Assistant, Apple and Raspberry Pi native coverage reports were ingested by
Runtime `1.1.0` and qualified as `COVERAGE_VALID`.

The cross-platform baseline decision is `ESTABLISHED`. The Raspberry Pi
coverage root cause was fixed before finalizing the baseline: the Pi dev extra
now includes `coverage>=7`, the stale config test follows the current
`dj_announcement_output` contract, and coverage is produced from the Pi
repository `.venv` without external coverage tooling.

## Validation Results

- Runtime Docker Hub pull passed for `1.1.0`.
- Runtime config reported version `1.1.0` and capability `coverage`.
- Runtime image inspection recorded the immutable digest.
- Home Assistant native coverage run passed: `143 passed`.
- Apple XCTest coverage run passed: `1 passed`.
- Raspberry Pi native coverage run passed: `387 passed`.
- Scenario catalog validation passed: `validated 233 scenarios`.
- Verification regression suite passed: `143 passed`.

## Parser Versions

Runtime `1.1.0` parser version reported `1` for:

- Cobertura XML;
- Apple `xccov` JSON.

## Included And Excluded Files

Home Assistant included `custom_components` and `tools` via coverage.py
`--source=custom_components,tools`. No Runtime-level excluded files were
reported.

Apple included the Xcode coverage targets emitted by the `DJConnectIOS`
XCTest run. Apple frameworks are not repository source and are not represented
as repository coverage entries in the normalized report.

Raspberry Pi included `src` via coverage.py `--source=src` from the repository
`.venv`. No Runtime-level excluded files were reported.

## Follow-up

Use the established baseline as the starting point for future trend, diff
coverage and threshold work.
