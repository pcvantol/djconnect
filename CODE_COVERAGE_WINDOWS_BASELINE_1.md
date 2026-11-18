# Windows Coverage Baseline 1

Status: WINDOWS_COVERAGE_BASELINE_ESTABLISHED
Date: 2026-07-12

## Summary

Windows Coverage Baseline 1 records the first validated native coverage
measurement for `pcvantol/djconnect-windows` after Phase 13E-R2 qualified the
live Windows path.

This is a post-Baseline-1 coverage record. It does not modify, replace or
retroactively extend Coverage Baseline 1, which remains immutable historical
evidence for Home Assistant, Apple and Raspberry Pi.

Runtime image:

```text
pcvantol/djconnect-verification-platform:1.1.0
```

Immutable digest:

```text
sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619
```

## Result

| Platform | Repository | Commit SHA | Producer | Format | Line coverage | Branch coverage | Function coverage | Method coverage | Qualification |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Windows | `pcvantol/djconnect-windows` | `b205f087214eb5fe90c4129c2afa9dee7f836a82` | Coverlet console `10.0.1` | Cobertura XML | 72.45% | 50.85% | Not reported | Not reported by Runtime; native producer reported 73.05% | COVERAGE_VALID |

Native test result: `125 test(s) passed`, plus localization validation for
620 keys across `en`, `nl`, `de`, `fr` and `es`.

## Scope Validation

The coverage scope is `windows-client-linked-production-sources`. The native
test project links selected production C# sources from `src/DJConnect.Windows`
into the `DJConnect.Tests` executable harness. The coverage report includes 17
unique production source files from `Models`, `Resources` and `Services`.

The executable test harness file `tests/DJConnect.Tests/Program.cs` is excluded
with `--exclude-by-file "**/tests/**/*.cs"` because it is test code, not
Windows product code. No `bin`, `obj`, generated XAML, MAUI generated,
platform bootstrap, vendor or fixture source files are present in the accepted
report.

The report intentionally does not claim full MAUI UI coverage. Product files
that are not compiled into the native test harness, such as `MainPage.xaml.cs`,
`MauiProgram.cs`, platform entrypoints, view models and storage-backed services,
remain future Windows coverage work.

## Evidence

Runtime evidence:

- `artifacts/verification/evidence/windows-coverage-baseline-1/coverage/coverage-summary.json`

Native reports:

- `artifacts/verification/reports/windows-coverage-baseline-1/djconnect-windows-coverage.xml`

An earlier fail-closed native attempt is retained for audit only:

- `artifacts/verification/reports/windows-coverage-baseline-1/djconnect-windows-coverlet-coverage.xml`

## Commands

```bash
./run_tests.sh
dotnet build tests/DJConnect.Tests/DJConnect.Tests.csproj --no-incremental
/tmp/djconnect-dotnet-tools/coverlet tests/DJConnect.Tests/bin/Debug/net10.0/DJConnect.Tests.dll --target "dotnet" --targetargs "tests/DJConnect.Tests/bin/Debug/net10.0/DJConnect.Tests.dll" --include-test-assembly --exclude-by-file "**/tests/**/*.cs" --format cobertura --output /Users/pcvantol/Documents/GitHub/djconnect/artifacts/verification/reports/windows-coverage-baseline-1/djconnect-windows-coverage.xml
python -m tools.verification.cli coverage ingest artifacts/verification/reports/windows-coverage-baseline-1/djconnect-windows-coverage.xml --format cobertura --repository pcvantol/djconnect-windows --commit-sha b205f087214eb5fe90c4129c2afa9dee7f836a82 --expected-commit-sha b205f087214eb5fe90c4129c2afa9dee7f836a82 --scope windows-client-linked-production-sources --run-id windows-coverage-baseline-1 --write-evidence --output markdown
```

## Regression Validation

- Windows native tests: `125 test(s) passed`.
- Windows test project build: succeeded.
- Windows MAUI build: preserved from Phase 13E-R2 Parallels VM evidence
  `djv-20260712T135722Z-d09b6ec5ba`; the local macOS build cannot execute the
  Windows WinUI `XamlCompiler.exe` and fails closed with exit code 126.
- Coverage parser and Windows adapter regression: `23 passed`.
- Scenario catalog validation: `validated 234 scenarios`.
- Smoke plan generation: `46` cases in `3` batches.
- SHA mismatch probe: returned `COVERAGE_SHA_MISMATCH`.

## Decision

```text
WINDOWS_COVERAGE_BASELINE_ESTABLISHED
```

Windows may now be included in a future coordinated four-platform coverage
snapshot or baseline. Coverage Baseline 1 remains unchanged.
