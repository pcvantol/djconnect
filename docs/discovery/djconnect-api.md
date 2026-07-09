# Repository Discovery Report: `pcvantol/djconnect-api`

## Overview

The central API repo owns the Cloudflare Worker trust/relay boundary: APNs relay, bootstrap proofs, per-install `djci_` tokens, diagnostics and future entitlement/profile-cloud surfaces.

## Purpose

Owns central relay authentication, install-token issuing/rotation/revocation, APNs registration/event delivery, D1 storage, audit/diagnostics and operator surfaces.

Does not own Home Assistant local runtime, durable local intelligence, client UX or canonical foundation docs.

## Strengths

- Very clear trust boundary in code and tests.
- Strong token model: per-install tokens, bootstrap proofs, hashing and D1 migrations.
- Tests cover privacy-safe APNs payloads, proof issuing, install-token flows and diagnostics.
- CI includes typecheck, Wrangler dry-run, migrations, Vitest, Postman smoke, secret pattern scan, deploy and staging-safe smoke.
- Good Cloudflare operational documentation.

## Weaknesses

- AGENTS does not yet visibly reference the full canonical foundation set.
- Central API is near future Cloud/Personal boundary; without ADR-0007 accepted, it can accidentally expand from relay to product brain.
- `wrangler.jsonc` includes public APNs team/key ids and topics. These are not private secrets, but the privacy/security docs should explicitly classify them as non-secret configuration.

## Architecture observations

Currently aligned: central API is relay/trust, not local intelligence. This repo is the highest-risk future boundary because entitlement/profile-cloud work naturally wants to live here. ADR-0007 should be accepted before broadening responsibility.

## Product observations

Product-facing role is invisible to most users, which is correct. It should not become a required dependency for Community local-first value.

## Technical debt

- ADR-0007 remains planned, not accepted.
- Operator/admin surfaces need continued privacy review.
- API and website operator surfaces are coupled through relay-secret mediated functions.

## Product debt

- Future Cloud and Personal are not yet productized; central API should avoid speculative product claims.

## Feature drift

Ahead on APNs/bootstrap trust relative to other repos. Not expected to implement music features.

## CI observations

Strong. Deploy path is integrated and migration-aware.

## Security observations

Strong but high sensitivity. APNs token encryption at rest and token revocation are positive signs.

## Privacy observations

Strong if payload restrictions remain enforced. Must never carry raw prompts, raw assistant responses, full history or Music DNA.

## Recommendations

1. Promote ADR-0007 before any entitlement/profile-cloud expansion.
2. Refresh AGENTS with full canonical foundation reference.
3. Add an explicit "central API must not own durable intelligence" test/doc assertion.
4. Keep operator surfaces server-side and token-minimized.

## Priority

P0 before cloud/profile expansion; P1 for AGENTS/foundation sync.

## Estimated effort

Small for docs/ADR; medium for future entitlement architecture.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 7 |
| Architecture | 8 |
| Documentation | 8 |
| Testing | 8 |
| CI/CD | 9 |
| Security | 9 |
| Privacy | 8 |
| Release | 8 |
| Developer Experience | 8 |
| Overall | 8.1 |
