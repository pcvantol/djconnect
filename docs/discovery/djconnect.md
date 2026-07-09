# Repository Discovery Report: `pcvantol/djconnect`

## Overview

The Home Assistant repository is the platform core and canonical source of truth. It contains the HACS integration, local-first backend runtime, foundation docs, API contracts, contract fixtures, release governance and shared CI workflows.

## Purpose

Owns Home Assistant integration behavior, local backend orchestration, Music Backend adapters, Ask DJ, Music DNA, Track Insight, VibeCast, Music Discovery, diagnostics, OTA/status flows and canonical platform documentation.

Does not own native client UX, ESP firmware implementation, website implementation, central APNs provider credentials or release artifact repositories.

## Strengths

- Strong foundation alignment after Epic 1.
- Broad unit test coverage across config flow, HTTP, websocket, Ask DJ, Music DNA, Music Discovery, VibeCast, Spotify backend, diagnostics and release scripts.
- Good privacy posture: redaction rules are explicit and tested.
- Music Backend adapter layer exists through `use_cases.py`.
- Client contract fixtures are exported and consumed by Apple/Pi/Windows.
- CI is platform-reference quality for a HACS integration: tests, ruff, bandit, hassfest, HACS, Semgrep and CodeQL.

## Weaknesses

- Profile Architecture is still conceptual. Runtime still uses HA user/device-derived Music DNA keys in several places.
- Core intelligence features are implemented as separate modules rather than a unified Insight Feed.
- The codebase carries a long history of Spotify Direct assumptions, even though Music Backend boundaries are improving.
- Documentation volume is high; contributors may struggle to identify the one current implementation contract without `FOUNDATION_INDEX.md`.

## Architecture observations

The repo is directionally correct: backend-owned intelligence and adapter-backed playback are real, not only documented. The largest architecture gap is the absence of a first-class DJConnect Profile resolver and storage model. Until Epic 3 lands, several "Profile" guarantees are simulated by HA user ids, device ids or Music DNA keys.

The use-case layer is the correct seam for future backend routing, but it should become the only route into provider-specific playback and library behavior.

## Product observations

The product story is mostly aligned with the foundation. User-facing README language still opens with "Muziekbediening met karakter" and "Home Assistant custom integration", which is accurate but less aligned with "Your AI DJ" than the foundation now wants.

## Technical debt

- First-class Profile resolver missing.
- Insight Feed abstraction missing.
- Backlog/docs mention many active surfaces; contract ownership should be centralized further.
- Some older docs still use implementation-first framing.

## Product debt

- Community/Personal boundary is documented but not implemented as a platform mechanism.
- Music DNA is opt-in, but "DJConnect Profile" is not yet the user-visible identity owner.
- VibeCast and Discover are feature-specific rather than feed-driven.

## Feature drift

HA is ahead of most clients on backend contracts and discovery surfaces. It exposes capabilities that clients consume unevenly.

## CI observations

Excellent. This is the platform reference for validation and reusable workflows.

## Security observations

Strong redaction coverage and central API bootstrap design. Local `.env.apns.local` exists in the working tree; it should stay untracked and never enter reports/prompts.

## Privacy observations

Strong compared with the rest of the platform. Profile-level privacy is still blocked by missing Profile Architecture.

## Recommendations

1. Make Epic 3 the next implementation epic: Profile Architecture.
2. Promote ADR-0005 Insight Feed before consolidating Track Insight, VibeCast, Discover and Lyrics work.
3. Keep `use_cases.py` as the only provider boundary and reduce direct Spotify helper calls over time.
4. Add a compact "current contracts" entrypoint that points to API contract, fixtures and websocket capabilities.

## Priority

P0 for Profile Architecture; P1 for Insight Feed; P2 for doc simplification.

## Estimated effort

Large for Profile Architecture; medium for Insight Feed ADR/design; small for doc entrypoint cleanup.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 8 |
| Architecture | 8 |
| Documentation | 9 |
| Testing | 9 |
| CI/CD | 9 |
| Security | 9 |
| Privacy | 8 |
| Release | 9 |
| Developer Experience | 8 |
| Overall | 8.6 |
