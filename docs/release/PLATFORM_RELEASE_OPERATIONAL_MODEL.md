# Platform Release Operational Model

Status: `ARCHITECTURE_CORRECTED`

Codex orchestrates discovery, planning, version alignment, workflow dispatch,
evidence collection, Software Assurance, Trusted Delivery, qualification and
release decisions. GitHub Actions is the exclusive execution engine: it
performs source builds and owns tagging, releases, artifact publication,
deployment and supported rollback. Distribution repositories publish qualified
artifacts; deployment targets consume them. The Runtime has no direct mutation
path.

```text
Codex control plane
  -> GitHub Actions source builds
  -> qualified artifacts and evidence
  -> distribution repositories / release channels
  -> optional deployment targets
  -> evidence-based closure
```

The internal gate is candidate SHA qualified, Verification evidence valid,
Software Assurance and Trusted Delivery `PASS`, coverage valid, version
alignment `PASS` and artifacts generated. Target availability is only required
when that release profile performs deployment.

## Native runner alignment

Apple and Windows native source-build paths are qualified as of 2026-07-13.
Apple run `29246454969` built and uploaded an unsigned macOS artifact on
`djconnect-apple-macos`; Windows run `29246684022` built and uploaded an
unsigned Windows artifact on `djconnect-windows11-parallels`. The corresponding
runner evidence is recorded in `RUNNER_QUALIFICATION_REPORT.md`.

```text
NATIVE_RUNNER_ALIGNMENT_COMPLETE
PLATFORM_RELEASE_3_3_INTERNAL_READY
```
