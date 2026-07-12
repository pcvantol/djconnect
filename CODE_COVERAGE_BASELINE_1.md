# Code Coverage Baseline 1

Status: CROSS_PLATFORM_COVERAGE_BASELINE_ESTABLISHED
Date: 2026-07-12

## Summary

Coverage Baseline 1 records the first cross-platform native code coverage
measurement ingested by Verification Runtime `1.1.0`. Home Assistant, Apple
and Raspberry Pi coverage were produced reliably and accepted as runtime
qualification evidence.

Runtime image:

```text
pcvantol/djconnect-verification-platform:1.1.0
```

Immutable digest:

```text
sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619
```

Runtime validation confirmed version `1.1.0`, the capability registry, the
`coverage` capability and parser support for Cobertura XML, LCOV and Apple
`xccov` JSON.

## Baseline Results

| Platform | Repository | Commit SHA | Producer | Format | Line coverage | Branch coverage | Function coverage | Qualification |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| Home Assistant | `pcvantol/djconnect` | `9bedd037f87ac4c359da5dee5f63bddacf37cd74` | coverage.py | Cobertura XML | 16.43% | 10.19% | Not reported | COVERAGE_VALID |
| Apple | `pcvantol/djconnect-app` | `6062ddd8e1367bf52c1666b3e2c95514d189a9cf` | xccov | Apple xccov JSON | 9.39% | Not reported | Not reported | COVERAGE_VALID |
| Raspberry Pi | `pcvantol/djconnect-pi` | `ef9300e6b3a1d3c23311b52beaff0872d023a32b` | coverage.py | Cobertura XML | 75.09% | 61.99% | Not reported | COVERAGE_VALID |

## Evidence

Runtime evidence:

- `artifacts/verification/evidence/coverage-baseline-1-ha/coverage/coverage-summary.json`
- `artifacts/verification/evidence/coverage-baseline-1-apple/coverage/coverage-summary.json`
- `artifacts/verification/evidence/coverage-baseline-1-pi/coverage/coverage-summary.json`

Native reports:

- `artifacts/verification/reports/coverage-baseline-1/djconnect-ha-coverage.xml`
- `artifacts/verification/reports/coverage-baseline-1/apple/djconnect-apple-xccov.json`
- `artifacts/verification/reports/coverage-baseline-1/djconnect-pi-coverage.xml`

Apple XCTest result bundle:

- `artifacts/verification/reports/coverage-baseline-1/apple/DJConnectIOSCoverage.xcresult`

## Native Commands

Home Assistant:

```bash
/private/tmp/djconnect-phase9e-venv/bin/coverage run --branch --source=custom_components,tools -m pytest tests/verification
/private/tmp/djconnect-phase9e-venv/bin/coverage xml -o artifacts/verification/reports/coverage-baseline-1/djconnect-ha-coverage.xml
python -m tools.verification.cli coverage ingest artifacts/verification/reports/coverage-baseline-1/djconnect-ha-coverage.xml --format cobertura --repository pcvantol/djconnect --commit-sha 9bedd037f87ac4c359da5dee5f63bddacf37cd74 --expected-commit-sha 9bedd037f87ac4c359da5dee5f63bddacf37cd74 --scope home-assistant-verification --run-id coverage-baseline-1-ha --write-evidence --output markdown
```

Apple:

```bash
xcodebuild test -project DJConnectApp.xcodeproj -scheme DJConnectIOS -destination 'platform=iOS Simulator,id=D1DDCACC-2651-4EB9-A55E-2315C9314AA6' -derivedDataPath /Users/pcvantol/Documents/GitHub/djconnect/artifacts/verification/apple/CoverageBaseline1DerivedData -resultBundlePath /Users/pcvantol/Documents/GitHub/djconnect/artifacts/verification/reports/coverage-baseline-1/apple/DJConnectIOSCoverage.xcresult -enableCodeCoverage YES -only-testing:DJConnectIOSUITests/DJConnectIOSUITests/testPrimaryTabsAreAvailable
xcrun xccov view --report --json /Users/pcvantol/Documents/GitHub/djconnect/artifacts/verification/reports/coverage-baseline-1/apple/DJConnectIOSCoverage.xcresult
python -m tools.verification.cli coverage ingest artifacts/verification/reports/coverage-baseline-1/apple/djconnect-apple-xccov.json --format apple-xccov --repository pcvantol/djconnect-app --commit-sha 6062ddd8e1367bf52c1666b3e2c95514d189a9cf --expected-commit-sha 6062ddd8e1367bf52c1666b3e2c95514d189a9cf --scope apple-ios-ui-healthcheck --run-id coverage-baseline-1-apple --write-evidence --output markdown
```

Raspberry Pi:

```bash
/Users/pcvantol/Documents/GitHub/djconnect-pi/.venv/bin/python -m coverage run --branch --source=src -m pytest
/Users/pcvantol/Documents/GitHub/djconnect-pi/.venv/bin/python -m coverage xml -o /Users/pcvantol/Documents/GitHub/djconnect/artifacts/verification/reports/coverage-baseline-1/djconnect-pi-coverage.xml
python -m tools.verification.cli coverage ingest artifacts/verification/reports/coverage-baseline-1/djconnect-pi-coverage.xml --format cobertura --repository pcvantol/djconnect-pi --commit-sha ef9300e6b3a1d3c23311b52beaff0872d023a32b --expected-commit-sha ef9300e6b3a1d3c23311b52beaff0872d023a32b --scope raspberry-pi-client --run-id coverage-baseline-1-pi --write-evidence --output markdown
```

The Raspberry Pi root cause was fixed in commit
`ef9300e6b3a1d3c23311b52beaff0872d023a32b`: the Pi dev extra now includes
`coverage>=7`, and the stale legacy config test now validates the current
`dj_announcement_output` normalization contract. Coverage was then produced
from the Pi repository `.venv` without external `PYTHONPATH` or coverage
tooling.

## Limitations

- Coverage thresholds were not introduced.
- Runtime `1.0.0` was not used.
- Home Assistant coverage uses the repository's canonical verification test
  suite and includes `custom_components` plus `tools`.
- Apple coverage uses the already qualified stable iOS 26.5 simulator target
  and the existing XCTest primary-tab healthcheck. Branch and function metrics
  are not reported by the Runtime `1.1.0` Apple parser.
- Raspberry Pi coverage uses the repository `.venv` and includes `src` via
  coverage.py `--source=src`. The native Pi coverage run passed:
  `387 passed`.

## Final Decision

```text
CROSS_PLATFORM_COVERAGE_BASELINE_ESTABLISHED
```

Coverage provenance and Runtime `1.1.0` ingestion are valid for all three
repositories.
