# DJConnect Verification Platform Release Notes

This file tracks releases of the generic DJConnect Verification Platform
runtime. It is separate from the DJConnect Home Assistant integration
`CHANGELOG.md`.

The Verification Platform release notes cover only reusable engine components:
runtime identity, execution engine behavior, planning, evidence/reporting,
Docker runtime packaging, GitHub runner readiness and adapter-framework
capabilities. Product scenarios, DJConnect feature changes, Home Assistant
integration changes and client/firmware changes belong in their owning release
notes.

## 0.2.0 - 2026-07-11

Runtime name: `djconnect-verification-platform`  
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
- Stable versus `future_beta` runtime channel separation for Apple/Xcode and
  Home Assistant beta verification evidence.
- Installation documentation for local checkout, Docker runtime and GitHub
  runner usage.

### Changed

- Parallel execution is now the default for workstation runs; operators can
  override worker count or force sequential execution.
- Verification reports and summaries now treat runtime version and total
  execution time as required metadata for new runs.
- Docker runtime packaging is explicitly engine-only: product scenarios, source
  checkouts, lab state, secrets and evidence remain external inputs.
- Apple stable qualification excludes beta iOS runtimes by default; beta
  evidence is advisory and isolated in `future_beta` mode.

### Verified

- `python3 -m pytest tests/verification` passed with 115 tests.
- Docker release dry-runs produced the expected runtime tags:
  `0.2.0`, `0.2.0-<short-sha>` and `sha-<short-sha>`.
- Runtime config reports `parallel_execution: true`, stable test mode and
  `verification_runtime.version: "0.2.0"`.

### Known Limitations

- Hosted GitHub runners are intended for non-mutating verification work until
  workflow jobs and artifact upload are implemented.
- Live Home Assistant labs, Apple simulator runs, hardware, SSH/serial, signing
  material and destructive cleanup require capability-gated self-hosted runners
  or approved local labs.
- Phase 10E-R2 remains blocked until latest eligible stable Apple runtime
  qualification passes.

## Release Note Maintenance

- Add a new section for every Verification Platform runtime release.
- Keep entries scoped to the generic verification engine.
- Record the runtime version, schema version, validation commands and known
  limitations.
- Do not duplicate DJConnect product or Home Assistant integration changelog
  content here.
