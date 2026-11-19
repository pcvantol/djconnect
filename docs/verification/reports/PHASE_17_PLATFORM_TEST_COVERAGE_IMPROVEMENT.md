# Phase 17 Platform Test Coverage Improvement

Status: `PLATFORM_TEST_COVERAGE_IMPROVEMENT_COMPLETE`

Date: 2026-07-12

## Summary

Phase 17 registered the missing canonical execution prompt, verified that the
Verification Runtime can ingest current coverage evidence, and fixed a
fail-closed defect in its LCOV parser. The full platform coverage matrix now
includes the Home Assistant integration, Apple, Raspberry Pi, Windows, ESP32
firmware and the DJConnect Voice Assistant request surface. Fresh native
coverage validates for the Home Assistant integration, Apple, Raspberry Pi and
Windows. The ESP32 native test suite passes, but its repository has no
configured, product-representative native coverage producer or export flow.

The ESP32 coverage capability is documented as `NOT_YET_SUPPORTED`; it is a
follow-up capability gap, not an unclassified platform or a Phase 17 blocker.

Coverage Baseline 1 and Windows Coverage Baseline 1 remain unchanged.

## Implementation

- Added the canonical Phase 17 prompt.
- Hardened `LCOVParser`: malformed and negative `DA`, `FNDA` and `BRDA`
  counts now return a failed parse result instead of being silently treated as
  uncovered-but-valid data.
- Added regression coverage proving that a negative LCOV count is classified
  as `coverage_corruption` by the Coverage Investigator.

## Verification

Focused runtime regression:

```text
tests/verification/test_coverage_runtime.py: 9 passed
```

Fresh scoped runtime coverage was generated from the focused regression and
ingested by Verification Runtime `1.1.0` as `COVERAGE_VALID`:

| Scope | Line | Branch | Qualification |
| --- | ---: | ---: | --- |
| `tools/verification/coverage` | 85.54% | 72.73% | `COVERAGE_VALID` |

Evidence:

- native report: `artifacts/verification/reports/phase-17-verification-coverage.xml`
- normalized evidence: `artifacts/verification/evidence/phase-17-verification-runtime/coverage/coverage-summary.json`

`git diff --check` passed.

## Native Platform Evidence

| Platform | Commit SHA | Native producer / format | Result | Runtime qualification | Evidence |
| --- | --- | --- | ---: | --- | --- |
| Apple | `6062ddd8e1367bf52c1666b3e2c95514d189a9cf` | XCTest / `xccov` JSON | 9.39% line | `COVERAGE_VALID` | `artifacts/verification/reports/phase-17-apple/DJConnectIOSCoverage.xcresult`; `artifacts/verification/evidence/phase-17-apple/coverage/coverage-summary.json` |
| Raspberry Pi | `374ce78f0cb0b36688dbad9c2ebb7d2adc9a9e3f` | coverage.py / Cobertura XML | 75.10% line, 62.04% branch | `COVERAGE_VALID` | `artifacts/verification/reports/phase-17-pi/djconnect-pi-coverage.xml`; `artifacts/verification/evidence/phase-17-pi/coverage/coverage-summary.json` |
| Windows | `b205f087214eb5fe90c4129c2afa9dee7f836a82` | Coverlet console 10.0.1 / Cobertura XML | 72.45% line, 50.85% branch | `COVERAGE_VALID` | `artifacts/verification/reports/phase-17-windows/djconnect-windows-coverage.xml`; `artifacts/verification/evidence/phase-17-windows/coverage/coverage-summary.json` |
| Home Assistant | `3ef4ec1ad37256485befa5170a9842b022bbfb8d` | coverage.py / Cobertura XML | 81.11% line, 68.33% branch | `COVERAGE_VALID` | `artifacts/verification/reports/phase-17-ha/djconnect-ha-coverage.xml`; `artifacts/verification/evidence/phase-17-ha/coverage/coverage-summary.json` |

Apple's iOS 26.5 simulator XCTest result contains one passing test and no
failures. Raspberry Pi's native pytest suite produced the Cobertura artifact
from its approved repository `.venv`. Windows ran its 125-test native harness
before Coverlet generated the report. Each runtime ingest supplied the same SHA
as the measured repository checkout and enforced it with
`--expected-commit-sha`.

## Canonical Platform Coverage Matrix

| Component | Repository / ownership | Current qualification role | Native test and coverage capability | Coverage responsibility | Evidence disposition |
| --- | --- | --- | --- | --- | --- |
| Verification Runtime | `pcvantol/djconnect`, `tools/verification` | Versioned Verification Runtime `1.1.0` | pytest; coverage.py/Cobertura | `REQUIRES_NATIVE_COVERAGE` | `COVERAGE_VALID`, scoped runtime evidence under `phase-17-verification-runtime/`. |
| Home Assistant integration | `pcvantol/djconnect`, `custom_components/djconnect` | Primary backend/platform runtime | pytest; coverage.py/Cobertura | `REQUIRES_NATIVE_COVERAGE` | `COVERAGE_VALID`, fresh full test run (1,260 passed, 6 skipped). |
| Apple Client | `pcvantol/djconnect-app` | Primary Intelligence Client | XCTest; `xccov` JSON | `REQUIRES_NATIVE_COVERAGE` | `COVERAGE_VALID`. |
| Raspberry Pi Client | `pcvantol/djconnect-pi` | Primary Ambient Client | pytest; coverage.py/Cobertura | `REQUIRES_NATIVE_COVERAGE` | `COVERAGE_VALID`. |
| Windows Client | `pcvantol/djconnect-windows` | Primary Intelligence Client | native .NET harness; Coverlet/Cobertura | `REQUIRES_NATIVE_COVERAGE` | `COVERAGE_VALID`. |
| ESP32 firmware | `pcvantol/djconnect-esp32` | Primary Voice / Control Client | host-native C++ and release/contract tests; no product-representative coverage export configured | `NOT_YET_SUPPORTED` | Native and release/contract suites pass at `85f2aca71dbdbefb1344d890cccc4af493a8ca42`, but no supported Cobertura/LCOV provenance is available for Runtime ingestion. Follow-up capability gap. |
| DJConnect Voice Assistant / Conversation Agent | Home Assistant integration modules `conversation.py`, `pipeline.py`, `assist_stt.py` | Primary Voice Endpoint | exercised by HA pytest suite and Voice Assistant adapter qualification | `COVERED_BY_PARENT_REPOSITORY` | Included in fresh HA Cobertura report; the modules are represented at 95.24%, 87.97% and 80.54% line coverage respectively. |
| Central API / APNs relay | `pcvantol/djconnect-api` | Optional central trust/relay boundary, outside current local-first primary-runtime qualification | Vitest repository exists, but no Phase 17 coverage contract or runtime ingestion is registered | `NOT_YET_SUPPORTED` | Explicitly outside the current primary-runtime baseline; no historical evidence reused. |
| Firmware distribution | `pcvantol/djconnect-firmware` | Release-artifact distribution only | Release manifest/assets, no source product runtime | `NO_EXECUTABLE_PRODUCT_CODE` | No separate native coverage applies. |
| VibeCast presentation surface | Home Assistant integration `vibecast.py` | Backend-owned presentation capability | HA pytest; coverage.py/Cobertura | `COVERED_BY_PARENT_REPOSITORY` | Covered by the fresh Home Assistant integration report. |

This matrix does not change platform ownership or architecture. It documents
which existing code owners need native coverage and prevents unsupported ESP32
coverage from being silently omitted.

## Investigation

| Finding | Classification | Blocking | Disposition |
| --- | --- | --- | --- |
| Negative LCOV counters were accepted as valid zero-hit entries. | Verification Runtime defect | Resolved | Parser now rejects negative metric values; regression added. |
| Fresh exact-SHA Apple coverage report required. | Execution environment / external runtime prerequisite | Resolved | iOS 26.5 XCTest completed and its `xccov` export qualified. |
| Fresh exact-SHA Raspberry Pi coverage report required. | Execution environment / sibling repository prerequisite | Resolved | The approved Pi `.venv` produced Cobertura coverage and qualified. |
| Fresh exact-SHA Windows coverage report required. | Execution environment / sibling repository prerequisite | Resolved | The running Parallels target produced a new Coverlet Cobertura report and qualified. |
| ESP32 coverage was not classified before prior completion. | Coverage capability gap | No | Native test and release/contract tests pass; add a product-representative export as a future coverage capability increment. |

## Architecture And Repository Intelligence

No platform architecture, product contract, scenario expectation or production
coverage scope changed. The fail-closed LCOV handling is recorded as durable
Verification Runtime behavior. Historical baselines remain immutable and must
only be compared against, never rewritten.

## Qualification Decision

```text
PLATFORM_TEST_COVERAGE_IMPROVEMENT_COMPLETE
```

The Phase 17 evidence gate is complete. Platform Baseline v1.0 Certification
is unblocked, but must begin only from its own explicit prompt. Do not start it
automatically.
