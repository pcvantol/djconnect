# Repository Discovery Report: `pcvantol/djconnect-pi-releases`

## Overview

The Pi releases repo is a public distribution surface for Raspberry Pi client tarballs, checksums and update metadata.

## Purpose

Owns public Pi release artifacts only.

Does not own Pi source code, backend contracts, canonical docs, client architecture or product logic.

## Strengths

- README clearly states no application source code lives here.
- Release asset naming, install root and updater flow are documented.
- Privacy/security notes cover tokens and credentials.
- Source repo publishing flow is described.

## Weaknesses

- No AGENTS.md.
- Dirty README and `.DS_Store` observed during audit.
- README says Spotify Premium is required, which is no longer backend-neutral.
- Uses `Client API URL` wording; current product language prefers `Client adres`.
- No CI workflow for artifact/checksum validation.

## Architecture observations

Correct release-surface role. The repo should remain artifact-only and not grow product or update logic beyond metadata.

## Product observations

Good Pi-specific release explanation, but product language lags canonical foundation.

## Technical debt

- Missing AGENTS/foundation pointer.
- Missing repo-local validation.
- Dirty local worktree should be cleaned separately.

## Product debt

- Backend-neutral requirements needed.
- Pairing wording should align with current HA/client language.

## Feature drift

Release README is slightly behind Pi source repo behavior and product language.

## CI observations

None observed.

## Security observations

Checksum flow is documented. Lack of validation workflow means release integrity depends on source repo workflow and manual review.

## Privacy observations

Good no-token statements; shared-device privacy will depend on future Profile Architecture.

## Recommendations

1. Refresh README wording from Pi source repo.
2. Add AGENTS.md pointing to canonical foundation.
3. Remove accidental `.DS_Store` from working tree/repo if tracked.
4. Add or document artifact checksum validation.

## Priority

P1 for public README and AGENTS; P2 for validation workflow.

## Estimated effort

Small.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 6 |
| Architecture | 8 |
| Documentation | 6 |
| Testing | 1 |
| CI/CD | 1 |
| Security | 6 |
| Privacy | 6 |
| Release | 7 |
| Developer Experience | 5 |
| Overall | 5.1 |
