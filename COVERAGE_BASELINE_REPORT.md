# Coverage Baseline Report

Status: CROSS_PLATFORM_COVERAGE_BASELINE_PARTIAL
Date: 2026-07-12

Coverage Baseline 1 used only Verification Runtime `1.1.0` and Docker image
`pcvantol/djconnect-verification-platform:1.1.0`.

Immutable image digest:

```text
sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619
```

## Qualification

All three native coverage reports were ingested by Runtime `1.1.0` and
qualified as `COVERAGE_VALID`.

The cross-platform baseline decision is `PARTIAL`, not because of coverage
integrity, but because Raspberry Pi native tests did not pass completely while
producing coverage.

## Validation Results

- Runtime Docker Hub pull passed for `1.1.0`.
- Runtime config reported version `1.1.0` and capability `coverage`.
- Runtime image inspection recorded the immutable digest.
- Home Assistant native coverage run passed: `143 passed`.
- Apple XCTest coverage run passed: `1 passed`.
- Raspberry Pi native coverage run completed with `386 passed, 1 failed`.
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

Raspberry Pi included `src` via coverage.py `--source=src`. No Runtime-level
excluded files were reported.

## Follow-up

Resolve the Raspberry Pi native test failure before promoting Coverage Baseline
1 from partial to fully established.
