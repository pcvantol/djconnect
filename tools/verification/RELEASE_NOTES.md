# DJConnect Verification Platform Release Notes

This file tracks releases of the Verification Runtime. It is separate from the
DJConnect Home Assistant integration `CHANGELOG.md`.

The Verification Runtime release notes cover only reusable engine components:
runtime identity, capabilities, compatibility, execution engine behavior,
planning, evidence/reporting, Docker runtime packaging, GitHub runner readiness
and adapter-framework capabilities. Product scenarios, DJConnect feature
changes, Home Assistant integration changes and client/firmware changes belong
in their owning release notes.

Canonical runtime product documents:

- `tools/verification/RUNTIME_CAPABILITIES.md`
- `tools/verification/RUNTIME_COMPATIBILITY.md`
- `tools/verification/RUNTIME_COVERAGE.md`
- `tools/verification/RUNTIME_METADATA.md`
- `tools/verification/RUNTIME_ROADMAP.md`
- `tools/verification/RUNTIME_RELEASES.md`

## 1.1.0 - 2026-07-12

Runtime name: `djconnect-verification-platform`
Product name: `Verification Runtime`
Runtime schema version: `1`

### Added

- Stable `coverage` runtime capability.
- Parser plugin framework for native coverage ingestion.
- Initial parser plugins for Cobertura XML, LCOV and Apple `xccov` JSON
  coverage exports.
- Canonical normalized coverage model with repository, commit SHA, runtime
  version, producer, format, scope, timestamp, parser version, line coverage,
  branch coverage, function coverage, method coverage, covered files, excluded
  files, metadata, evidence and qualification.
- Coverage validator that fails closed for missing reports, empty reports,
  malformed reports, unsupported formats, invalid totals, duplicate reports,
  broken provenance, parser failures and commit SHA mismatches.
- Coverage qualification states: `COVERAGE_VALID`, `COVERAGE_INVALID`,
  `COVERAGE_NOT_AVAILABLE`, `COVERAGE_STALE`, `COVERAGE_SHA_MISMATCH`,
  `COVERAGE_UNSUPPORTED_FORMAT` and `COVERAGE_EMPTY`.
- Coverage evidence writer that persists `coverage/coverage-summary.json` and
  indexes it as verification evidence.
- Coverage investigator classifications for missing reports, SHA mismatches,
  anomalies, unexpected exclusions, unsupported formats and corruption.
- Coverage JSON and Markdown reports.
- CLI command `coverage ingest` for runtime coverage ingestion.
- Runtime metadata now advertises `coverage` automatically.
- Docker release tags now include `1.1.0`, `1.1` and `latest` for stable
  releases, in addition to SHA-specific tags.

### Compatibility Notes

- Runtime `1.1.0` is backward-compatible with Runtime `1.0.0` consumers that
  require only planner, execution, evidence, investigator, qualification and
  reporting.
- Consumers that require coverage must declare minimum runtime version `1.1.0`
  and required capability `coverage`.
- Missing coverage metrics normalize to `NOT_REPORTED`, never zero.
- The runtime consumes native coverage reports but does not generate coverage.
- Phase 13 adds the first Windows adapter surface as an additive
  `execution`-capability consumer. This does not change the Runtime `1.1.0`
  capability contract or Docker image version.

### Migration Notes

- Repositories should continue producing coverage with their native toolchains.
- Repositories can opt into runtime coverage by passing native reports to
  `python -m tools.verification.cli coverage ingest`.
- Bootstrap must validate the `coverage` capability before selecting Runtime
  `1.1.0` for coverage workflows.

### Docker Publication

- Published to Docker Hub repository
  `pcvantol/djconnect-verification-platform`.
- Published stable tags: `1.1.0`, `1.1`, `latest`.
- Published immutable tags: `1.1.0-f05773616a1a`,
  `sha-f05773616a1a`.
- Published digest:
  `sha256:3f0b8d3ba5f07afa5c8f05cd305dd92c43806e0fed24395be96d832e7ef72619`.
- Pull-back qualification from Docker Hub passed for `1.1.0`.
- Clean-container config smoke confirmed Runtime `1.1.0` metadata and the
  `coverage` capability.
- Clean-container LCOV ingestion smoke returned `COVERAGE_VALID`.

## 1.0.0 - 2026-07-11

Runtime name: `djconnect-verification-platform`
Product name: `Verification Runtime`
Runtime schema version: `1`

### Added

- Versioned runtime identity surfaced through `verification_runtime` metadata.
- Default parallel scenario execution with dynamic worker detection and
  dependency/resource-aware batching.
- Host preflight checks before local lab runner startup for conflicting
  processes, occupied ports and available disk space.
- Execution summaries with total scenario count, executed scenario count,
  status buckets and `total_execution_seconds`.
- Generic Docker release command for the engine-only runtime image.
- OCI-labeled Docker image build with runtime version, release SHA, build date,
  base image and license metadata.
- GitHub Actions runner positioning for hosted non-mutating verification jobs
  and capability-gated self-hosted runner jobs.
- GitHub Actions workflow for publishing the generic runtime image to Docker
  Hub using repository Docker Hub secrets, with pre-publication image label
  inspection and container smoke testing.
- Verification runs now fail closed unless the configured published runtime
  image can be pulled from Docker Hub at run start.
- Regular repository CI now runs the Verification Platform unit test suite
  `tests/verification` as its own check.
- Default Docker Hub publish target documented as
  `pcvantol/djconnect-verification-platform` with runtime tags `1.0.0`,
  `1.0.0-<short-sha>` and `sha-<short-sha>`.
- Runtime capability model introduced with initial capabilities `planner`,
  `execution`, `evidence`, `investigator`, `qualification` and `reporting`.
- Capability-driven compatibility, runtime metadata and independent runtime
  release model documented as the public runtime contract.
- Stable versus `future_beta` runtime channel separation for Apple/Xcode and
  Home Assistant beta verification evidence.
- Installation documentation for local checkout, Docker runtime and GitHub
  runner usage.
- Functional help documentation for common operator workflows, result
  interpretation and failure handling.
- Release governance requiring changed Verification Runtime behavior
  to be published through the CI Docker release workflow before Docker-based
  consumers use it.

### Changed

- Parallel execution is now the default for workstation runs; operators can
  override worker count or force sequential execution.
- Verification reports and summaries now treat runtime version and total
  execution time as required metadata for new runs.
- Docker runtime packaging is explicitly engine-only: product scenarios, source
  checkouts, lab state, secrets and evidence remain external inputs.
- Docker Hub published stable images are authoritative for Docker-based
  verification; local builds are development artifacts and must not be used as
  silent fallback runtime releases.
- Apple stable qualification excludes beta iOS runtimes by default; beta
  evidence is advisory and isolated in `future_beta` mode.

### Verified

- `python3 -m pytest tests/verification` passed with 116 tests.
- Docker release dry-runs produced the expected runtime tags:
  `1.0.0`, `1.0.0-<short-sha>` and `sha-<short-sha>`.
- Runtime config reports `parallel_execution: true`, stable test mode and
  `verification_runtime.version: "1.0.0"`.
- GitHub workflow structure is covered by `tests/verification` to keep image
  label inspection and `docker run ... config` smoke testing before publication.
- The repository validation workflow includes a dedicated Verification
  framework test job.

### Deferred Follow-Ups

- Docker Hub publication requires GitHub repository secrets
  `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` with push scope for
  `pcvantol/djconnect-verification-platform`.
- Docker repository naming is now dedicated to the generic verification runtime:
  `pcvantol/djconnect-verification-platform`.
- Live Home Assistant labs, Apple simulator runs, hardware, SSH/serial, signing
  material and destructive cleanup require capability-gated self-hosted runners
  or approved local labs; self-hosted runner support is deferred to a separate
  epic.

### Known Limitations

- Phase 10E-R2 remains blocked until latest eligible stable Apple runtime
  qualification passes.

## Release Note Maintenance

- Add a new section for every Verification Runtime release.
- Keep entries scoped to the generic verification engine.
- Record the runtime version, schema version, validation commands and known
  limitations.
- Do not duplicate DJConnect product or Home Assistant integration changelog
  content here.
