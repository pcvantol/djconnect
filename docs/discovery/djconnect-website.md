# Repository Discovery Report: `pcvantol/djconnect-website`

## Overview

The website repo owns public product story, onboarding, docs presentation, release note presentation and Cloudflare Pages functions for downloads/stats/operator support.

## Purpose

Owns user-facing website pages, localization, release notes, public onboarding, support pages and limited server-side Pages Functions.

Does not own runtime contracts, canonical architecture decisions, client implementation or release artifacts.

## Strengths

- Broad static site and localization footprint.
- CI includes i18n validation, node tests, screenshots, smoke tests, build and Cloudflare Pages deploy.
- Product pages cover multiple clients and release flows.
- Operator functions are server-side and documented to avoid exposing secrets.

## Weaknesses

- No AGENTS.md found, so agent sessions lack repo-specific foundation-first instructions.
- Website docs contain product-language drift such as "Spotify profile" references in README/HANDOFF/CHANGELOG context.
- Public copy likely still emphasizes implementation and client specifics more than the new "AI DJ" foundation.
- Website owns operator/admin pages that touch central API trust boundaries; this is legitimate but needs strict ownership language.

## Architecture observations

Website should remain presentation/onboarding. Pages Functions for stats/releases/operator flows are acceptable operational helpers, but they should not grow into product API ownership.

## Product observations

Website is the main place where the Product Vision must become simple. It currently has strong technical docs but should be audited against Product Language: Community is complete, Personal is profile-centric, Cloud is optional/future, and Music Backends are adapters.

## Technical debt

- Missing AGENTS.md.
- Large static/localized page set increases drift risk.
- Release note mirrors can preserve old terminology indefinitely unless checked.

## Product debt

- Needs a dedicated website/product story epic.
- Needs fresh copy around "Play your music. DJConnect brings it to life."
- Need avoid implying Spotify is the identity model.

## Feature drift

Website may lag behind the foundation. It mentions current/future features across pages; those claims need source-of-truth verification.

## CI observations

Strong for a static/product site. Screenshot checks are unusually good.

## Security observations

Operator functions use server-side secrets; this should remain heavily tested and documented. Public static assets must never include relay/operator secrets.

## Privacy observations

Privacy page exists; content should be audited against Profile Architecture once implemented.

## Recommendations

1. Add AGENTS.md with foundation-first instructions and website-specific ownership.
2. Run product-language audit across all public pages and release-note templates.
3. Keep operator/admin functions minimal and server-side; document that website does not own central trust.
4. Add a "foundation language" content test for banned/avoid terms.

## Priority

P1 for AGENTS and language audit; P2 for content tests.

## Estimated effort

Medium due localization breadth.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 7 |
| Architecture | 7 |
| Documentation | 8 |
| Testing | 8 |
| CI/CD | 8 |
| Security | 7 |
| Privacy | 7 |
| Release | 8 |
| Developer Experience | 7 |
| Overall | 7.4 |
