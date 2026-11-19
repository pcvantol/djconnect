# Repository Discovery Report: `pcvantol/djconnect-app-releases`

## Overview

The app releases repo is a public distribution surface for Apple and desktop app release artifacts and metadata.

## Purpose

Owns public app release artifacts only.

Does not own Apple source, Windows source, backend contracts, entitlement model, product logic or foundation docs.

## Strengths

- Intentionally small.
- README states source code lives elsewhere and that Spotify/Home Assistant long-lived tokens are not stored in the app.
- Support guidance asks for redacted diagnostics and no tokens.

## Weaknesses

- No AGENTS.md.
- Dirty local README observed during audit.
- README contains stale Keychain install notes that conflict with current Apple app README stating app-private storage and "no Keychain permission/fallback popup".
- README uses old `Client API url` wording; foundation/current HA language prefers `Client adres`.
- README says Spotify Premium is required, which is not Music Backend-neutral.
- No CI/release metadata validation visible.
- Legal section says "All rights reserved" while source repos are MIT; release artifact license posture needs clearer wording.

## Architecture observations

Correctly small release surface, but stale docs can mislead users and reviewers. Release repos must not redefine pairing/storage behavior.

## Product observations

Product language lags behind canonical foundation and source repos.

## Technical debt

- No validation workflow.
- README stale relative to Apple source.
- No AGENTS/foundation pointer.

## Product debt

- Backend-neutral requirements and current pairing language needed.
- App distribution strategy is not settled; TestFlight/App Store remains separate workstream.

## Feature drift

Release README is behind source repo behavior.

## CI observations

None observed.

## Security observations

Stale Keychain docs are not a direct vulnerability, but can cause incorrect support expectations.

## Privacy observations

Good no-token statements, but "does not collect or process personal data outside the app" should be revisited once APNs/central bootstrap and future Personal are described.

## Recommendations

1. Refresh README from source repos; remove stale Keychain wording.
2. Add AGENTS.md pointing to canonical foundation.
3. Add minimal release artifact validation or document upstream-only validation.
4. Clarify licensing for artifacts and source repos.

## Priority

P1 because release docs are public/user-facing.

## Estimated effort

Small.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 5 |
| Architecture | 7 |
| Documentation | 5 |
| Testing | 1 |
| CI/CD | 1 |
| Security | 5 |
| Privacy | 5 |
| Release | 6 |
| Developer Experience | 4 |
| Overall | 4.3 |
