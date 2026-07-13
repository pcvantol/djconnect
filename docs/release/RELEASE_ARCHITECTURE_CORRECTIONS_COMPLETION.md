# Release Architecture Corrections — Completion Report

Date: 2026-07-13  
Decision: `RELEASE_ARCHITECTURE_CORRECTED`

## Executive summary

The first Internal Release preparation exposed an incorrect assumption that
every platform build required a self-hosted or physical-target runner. The
canonical architecture now limits self-hosted source builds to Apple and
Windows native toolchains. All other platform source builds execute on
GitHub-hosted Linux. Pi and ESP32 are deployment targets that consume
published artifacts; they are not source-build runners.

## Scope

Architecture and navigation documents only. No product source, workflow,
version, candidate SHA, release, tag, publication or deployment was changed.

## Evidence and validation

- Workflow inventory read across HA, API, Apple, Windows, Pi, ESP32 and
  Website repositories.
- Existing Platform Release Architecture, Software Assurance execution model
  and Trusted Delivery boundaries were reviewed for consistency.
- `git diff --check` passed.
- The release graph, artifact manifest and canonical release navigation now
  name GitHub Actions as the source-build surface and separate deployment
  targets from build locations.

## Canonical corrections

- Codex is the release control plane only.
- Apple uses a qualified self-hosted macOS runner; Windows uses a qualified
  self-hosted Windows runner.
- HA, API, Website, ESP32 and Pi source builds use GitHub-hosted Linux.
- Firmware distribution is `pcvantol/djconnect-firmware`; Pi distribution is
  `pcvantol/djconnect-pi-releases`.
- Verification owns physical/runtime/hardware evidence; Release Engineering
  consumes valid evidence for the candidate SHA.
- Hardware availability is required only when the chosen release profile
  actually performs deployment or explicitly requires post-release validation.

## Known limitations and next phase

This is an architecture alignment, not a Platform Release 3.3 execution.
Operational workflow changes and release execution remain outside this scope.
The next explicit phase may perform the operational Internal Release using the
corrected architecture.
