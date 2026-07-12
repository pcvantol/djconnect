# ESP Native Coverage Qualification

Status: `ESP_COVERAGE_QUALIFIED`

Date: 2026-07-12

## Management Summary

This follow-up increment removes the ESP firmware coverage capability gap
identified after Phase 17. It does not reopen or alter Phase 17, Coverage
Baseline 1, Windows Coverage Baseline 1, Platform Architecture, or Platform
Baseline certification.

The firmware repository now produces a native Cobertura report from its
host-testable production logic. Verification Runtime `1.1.0` ingested the
report and returned `COVERAGE_VALID`.

## Technology And Scope

- native producer: GCC/Clang `--coverage` instrumentation with `gcovr`;
- export format: Cobertura XML;
- test entrypoint: `test/native/test_logic.cpp`;
- production scope: host-testable firmware logic headers exercised by that
  suite: `LogicHelpers`, `DeviceCommandParser`, `NetworkActivityLogic`,
  `DJConnectMenuModel` and `PlaybackResponseParser`;
- excluded by design: Arduino/ESP-IDF hardware modules, which cannot be
  truthfully represented as host-native coverage and retain PlatformIO build
  and live ESP qualification evidence.

The workflow is implemented by
`pcvantol/djconnect-esp32/scripts/run_native_coverage.sh` and runs in Firmware
CI. It requires `gcovr`, writes a Cobertura artifact, and is suitable for local
and CI execution without a second coverage pipeline.

## Fresh Evidence

| Field | Value |
| --- | --- |
| Repository | `pcvantol/djconnect-esp32` |
| Measured commit SHA | `85f2aca71dbdbefb1344d890cccc4af493a8ca42` |
| Native producer | `c++ --coverage` + `gcovr` |
| Format | Cobertura XML |
| Line coverage | 90.28% (697 / 772) |
| Branch coverage | 72.71% (666 / 916) |
| Runtime | Verification Runtime `1.1.0` |
| Qualification | `COVERAGE_VALID` |

Evidence paths:

- native report: `../djconnect-esp32/release/native-coverage/djconnect-esp32-native-coverage.xml`;
- normalized evidence:
  `artifacts/verification/evidence/esp-coverage-followup/coverage/coverage-summary.json`.

## Validation

- native firmware logic suite passed with coverage instrumentation;
- firmware release/contract suite passed;
- Runtime ingestion enforced the measured SHA with `--expected-commit-sha`;
- normalized evidence and coverage summary were persisted;
- the ESP32 repository `git diff --check` passed.

## Coverage Matrix Amendment

The current coverage matrix classification is:

| Component | Classification | Evidence |
| --- | --- | --- |
| ESP32 firmware | `REQUIRES_NATIVE_COVERAGE` | This report and `esp-coverage-followup` Runtime evidence. |
| Voice Assistant | `COVERED_BY_PARENT_REPOSITORY` | Home Assistant integration coverage. |
| Firmware distribution | `NO_EXECUTABLE_PRODUCT_CODE` | Release-artifact repository only. |

## Decision

```text
ESP_COVERAGE_QUALIFIED
```

The remaining ESP platform coverage gap is eliminated. Platform Baseline v1.0
Certification remains a separate, explicit next phase and is not started here.
