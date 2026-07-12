# Verification Runtime Coverage Capability

Status: Canonical  
Runtime version: `1.1.0`  
Capability: `coverage`

## Purpose

Runtime `1.1.0` introduces platform-independent code coverage as a first-class
Verification Runtime capability.

Repositories produce native coverage reports. The runtime consumes those
reports, validates them, normalizes them, records coverage evidence, qualifies
coverage state, investigates coverage anomalies and renders coverage reports.

The runtime does not generate coverage.

## Pipeline

```text
Native Coverage Report
  -> Coverage Parser
  -> Coverage Validator
  -> Coverage Normalizer
  -> Coverage Evidence
  -> Coverage Investigator
  -> Coverage Qualification
  -> Coverage Reports
```

Every stage is independently testable.

## Parser Framework

Coverage parsers are plugin-style classes registered with the coverage parser
registry. Runtime `1.1.0` supports:

- Cobertura XML;
- LCOV;
- Apple `xccov` / `xcresult` JSON exports.

Future formats should require only a new parser plugin. Reserved future
formats include Coverlet, JaCoCo, Istanbul, `llvm-cov` and `gcov`.

## Normalized Model

The canonical coverage model records:

- repository;
- commit SHA;
- runtime version;
- coverage producer;
- coverage format;
- coverage scope;
- coverage timestamp;
- coverage version;
- parser version;
- line coverage;
- branch coverage;
- function coverage;
- method coverage;
- covered files;
- excluded files;
- coverage status;
- coverage metadata;
- native report reference;
- coverage evidence;
- coverage qualification.

Not every producer supplies every metric. Missing metrics are represented as
`NOT_REPORTED`, never as zero.

## Validation

Coverage validation fails closed for:

- missing report;
- empty report;
- malformed report;
- unsupported format;
- invalid totals;
- coverage SHA mismatch;
- duplicate reports;
- broken provenance;
- coverage generated for another commit;
- parser failure.

## Qualification

Coverage qualification results are:

- `COVERAGE_VALID`;
- `COVERAGE_INVALID`;
- `COVERAGE_NOT_AVAILABLE`;
- `COVERAGE_STALE`;
- `COVERAGE_SHA_MISMATCH`;
- `COVERAGE_UNSUPPORTED_FORMAT`;
- `COVERAGE_EMPTY`.

## Evidence

Coverage evidence is written under:

```text
coverage/coverage-summary.json
```

The evidence includes:

- coverage summary;
- coverage details;
- coverage metadata;
- validation;
- qualification;
- statistics;
- provenance;
- native report reference;
- parser version;
- runtime version.

## Investigator

Runtime `1.1.0` prepares coverage investigator classifications for:

- coverage regression;
- coverage anomalies;
- unexpected exclusions;
- unexpected increases;
- missing reports;
- broken provenance;
- coverage corruption.

Trend analysis, diff coverage and historical coverage remain future
capabilities.

## CLI

```bash
python -m tools.verification.cli coverage ingest coverage.xml --format cobertura
python -m tools.verification.cli coverage ingest lcov.info --format lcov
python -m tools.verification.cli coverage ingest xccov.json --format apple-xccov
```

Use `--expected-commit-sha` to fail closed when a report was generated for a
different commit. Use `--write-evidence --run-id <id>` to persist runtime
coverage evidence.

## Future Preparation

The coverage model is prepared for future capabilities:

- diff coverage;
- historical coverage;
- coverage trends;
- mutation coverage;
- coverage quality gates;
- repository coverage;
- platform coverage;
- quality budgets.

## Coverage Baseline 1

Coverage Baseline 1 was produced on 2026-07-12 using Runtime `1.1.0` and
Docker image digest:

```text
sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619
```

Baseline reports:

- `CODE_COVERAGE_BASELINE_1.md`
- `CODE_COVERAGE_BASELINE_1.json`
- `COVERAGE_BASELINE_REPORT.md`

The baseline is recorded as `CROSS_PLATFORM_COVERAGE_BASELINE_PARTIAL` because
Raspberry Pi coverage could not be reliably produced in the available Python
environment. Home Assistant and Apple coverage provenance and Runtime ingestion
remained valid.
