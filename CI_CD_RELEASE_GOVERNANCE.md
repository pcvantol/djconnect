# DJConnect CI/CD and Release Governance

This document defines the quality, security, privacy, and release-management expectations for the DJConnect platform.

It applies to source repositories and release repositories.

## Goals

CI/CD should protect:

- platform compatibility;
- user privacy;
- update safety;
- release artifact integrity;
- source/release consistency;
- security posture;
- cross-client contracts.

## Repository classes

### Source repositories

Source repositories own implementation and tests:

- `pcvantol/djconnect`;
- `pcvantol/djconnect-api`;
- `pcvantol/djconnect-app`;
- `pcvantol/djconnect-windows`;
- `pcvantol/djconnect-pi`;
- `pcvantol/djconnect-esp32`;
- `pcvantol/djconnect-website`.

### Release repositories

Release repositories publish community artifacts, unsigned/non-signed binaries, firmware images, app builds, manifests, and release notes.

They must not become product-logic owners. They mirror release outputs and public distribution state.

`pcvantol/djconnect-firmware` is the firmware distribution repository. It
publishes qualified native, ESPHome, RP2 and Raspberry Pi bootstrap artifacts
but never owns source or platform enablement. Every physical-device channel,
manifest, checksum and release note is authoritative there.

## Minimum CI expectations

Each source repo should have repo-appropriate checks for:

- formatting;
- linting;
- unit tests;
- build validation;
- dependency restore/build reproducibility;
- secret scanning;
- dependency/security scanning where practical;
- release notes validation when publishing;
- artifact naming/version consistency.

## Platform-level checks

Independent offline checks should overlap where their fixtures and outputs are
isolated. Core uses bounded module processes for its complete unittest suite and
coverage, with exact test-ID accounting and validated per-worker databases; see
`docs/verification/PARALLEL_OFFLINE_CI.md`. Other repository owners qualify their
own concurrency. Shared runtime state and resource limits must retain their
original semantics. No parallel optimization may omit checks, turn cancellation
or skipped prerequisites into success, multiply paid/provider/device effects, or
reorder protected Source, Final, qualification, publication and deployment gates.

Changes that affect cross-repo contracts should verify:

- HA integration compatibility;
- client protocol compatibility;
- API relay compatibility;
- release repo publication compatibility;
- `SYNC_PROMPTS.md` alignment;
- roadmap/design-doc updates if product behavior changes.

## Security regression guardrails

CI/CD and reviews should catch:

- OAuth tokens or secrets in logs, exports, diagnostics, release assets, or docs;
- unscoped local unauthenticated endpoints;
- guest pages that expose personal profile data;
- release artifacts without checksums where feasible;
- unsafe update flows without rollback or clear recovery notes;
- accidental direct pushes to protected release branches.

## Privacy regression guardrails

Review any change that touches:

- Ask DJ conversation history;
- Music DNA;
- recommendation history;
- likes/dislikes;
- profile export/import;
- shared device rendering;
- guest endpoints;
- diagnostics bundles;
- logs;
- release artifacts.

Default rule: personal profile data must not appear on shared or guest surfaces unless explicitly designed and documented.

## Ask DJ release qualification scope

The blocking actual Ask DJ qualification for the official Home Assistant
artifact covers English and Dutch (`en`, `nl`). Its exact contextual,
semantic, catalogue, variation, dialogue and prosody receipts must match
that scope. Findings shared across languages and findings in EN or NL still
block release while open. A finding explicitly limited to DE, FR or ES is
tracked outside this release scope.

All five product languages, deterministic regression coverage and historical
qualification receipts remain intact. A scoped pass makes no real-quality
claim for German, French or Spanish. It also makes no installed, native or
audible acceptance claim.

The [Core 4.0.0 external TestFlight roadmap decision](docs/roadmap/CORE_4_0_EXTERNAL_TESTFLIGHT.md)
records a separate, exact-candidate beta package and its deferred qualifications.

## Release hygiene checklist

Before release:

- confirm version bump strategy;
- run repo-specific CI;
- update changelog/release notes;
- update source-of-truth docs if product/architecture changed;
- update `SYNC_PROMPTS.md` for cross-repo contract changes;
- verify artifacts are published to the expected release repository;
- verify artifact names and versions match the changelog;
- verify secrets are not included;
- verify known compatibility constraints are stated;
- smoke-test the primary install/update path.

## Future audit

A dedicated CI/CD audit should inspect all source and release repos and produce:

- current workflow inventory;
- missing checks;
- duplicated release logic;
- artifact integrity gaps;
- branch protection recommendations;
- privacy/security regression checklist;
- release notes consistency recommendations;
- suggested GitHub Actions hardening.
