# Code Coverage Baseline 1

Status: CROSS_PLATFORM_COVERAGE_BASELINE_PARTIAL
Date: 2026-07-12

## Summary

Coverage Baseline 1 records the first cross-platform native code coverage
measurement ingested by Verification Runtime `1.1.0`. Home Assistant and Apple
coverage were produced reliably. Raspberry Pi coverage is explicitly excluded
from the measured baseline because coverage could not be reliably produced in
the available Python environment.

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
| Raspberry Pi | `pcvantol/djconnect-pi` | `3d2853305041ea1d649faba00e9ccab1169816d7` | coverage.py attempt | Cobertura XML attempt | Not reliably produced | Not reliably produced | Not reliably produced | NOT_RELIABLY_PRODUCED |

## Evidence

Runtime evidence:

- `artifacts/verification/evidence/coverage-baseline-1-ha/coverage/coverage-summary.json`
- `artifacts/verification/evidence/coverage-baseline-1-apple/coverage/coverage-summary.json`

Native reports:

- `artifacts/verification/reports/coverage-baseline-1/djconnect-ha-coverage.xml`
- `artifacts/verification/reports/coverage-baseline-1/apple/djconnect-apple-xccov.json`

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

Raspberry Pi attempt:

```bash
PYTHONPATH=/private/tmp/djconnect-phase9e-venv/lib/python3.14/site-packages:src COVERAGE_FILE=/private/tmp/djconnect-pi-coverage-baseline-1.coverage /Users/pcvantol/Documents/GitHub/djconnect-pi/.venv/bin/python -m coverage run --branch --source=src -m pytest
```

The available environment had to mix the Raspberry Pi repository virtualenv
with coverage tooling from `/private/tmp/djconnect-phase9e-venv` and Python
3.14 site packages. That hybrid environment is not an authoritative Pi coverage
producer, so the resulting Pi coverage report and ingest are not used as
baseline evidence.

## Limitations

- Coverage thresholds were not introduced.
- Runtime `1.0.0` was not used.
- Home Assistant coverage uses the repository's canonical verification test
  suite and includes `custom_components` plus `tools`.
- Apple coverage uses the already qualified stable iOS 26.5 simulator target
  and the existing XCTest primary-tab healthcheck. Branch and function metrics
  are not reported by the Runtime `1.1.0` Apple parser.
- Raspberry Pi coverage could not be reliably produced in the available Python
  environment. The attempted run required a hybrid virtualenv/PYTHONPATH setup
  and reported `386 passed, 1 failed`, so Pi coverage metrics are excluded from
  Baseline 1.

## Final Decision

```text
CROSS_PLATFORM_COVERAGE_BASELINE_PARTIAL
```

Coverage provenance and Runtime `1.1.0` ingestion are valid for the Home
Assistant and Apple inputs. The baseline is partial because Raspberry Pi
coverage could not be reliably produced in the available Python environment.
