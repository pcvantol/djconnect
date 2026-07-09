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
- `pcvantol/djconnect-firmware`;
- `pcvantol/djconnect-website`.

### Release repositories

Release repositories publish community artifacts, unsigned/non-signed binaries, firmware images, app builds, manifests, and release notes.

They must not become product-logic owners. They mirror release outputs and public distribution state.

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
