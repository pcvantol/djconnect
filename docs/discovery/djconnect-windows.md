# Repository Discovery Report: `pcvantol/djconnect-windows`

## Overview

The Windows repo owns a .NET MAUI desktop Intelligence Client, with Windows as the canonical current target and Mac Catalyst also present for shared desktop validation.

## Purpose

Owns Windows-native DJConnect UX, desktop Ask DJ, Track Insight, Music DNA, Discover, queue/playlists rendering, pairing and diagnostics.

Does not own backend intelligence, provider playback logic, canonical Ask DJ history, Music DNA storage or platform foundation docs.

## Strengths

- Strong README and tests state that Home Assistant is the trusted backend and Windows stores no Spotify credentials, Music DNA or Ask DJ server history.
- Tests are unusually comprehensive for a young client: protocol, pairing, websocket fallback, Music DNA, Music Discovery, Track Insight, backend-aware actions and localization.
- CI includes secret-like string scanning, contract fixtures, .NET tests, formatting, builds, CodeQL and Semgrep.
- Functional parity with Apple is intentional and documented.

## Weaknesses

- Branch was not `main` during audit (`codex/sync-djconnect-v1-contracts`), so the audit may include in-flight contract-sync work.
- Repo-local `SYNC_PROMPTS.md` exists; canonical cross-repo sync prompt should live only in HA.
- Windows follows Apple closely; without a platform parity matrix this can become copy-by-feature rather than capability-by-client.
- App is desktop-rich; the Product Vision should decide which Apple features are required vs optional for Windows.

## Architecture observations

Windows largely respects backend-owned intelligence and Music Backend boundaries. The websocket fast path is correctly capability-gated and local-only. The most important architecture risk is duplication of client-side parsing/presentation logic with Apple and Pi; that is expected today, but long-term contract fixtures should be the guardrail.

## Product observations

Strong match to Product Vision as an Intelligence Client. It is ahead of Pi and ESP by design. It should not become the place where desktop-specific product concepts are invented without foundation review.

## Technical debt

- Foundation references are partial.
- Local `SYNC_PROMPTS.md` should be replaced with a pointer.
- Signed packaging and store strategy remain incomplete.

## Product debt

- Desktop parity with Apple is not yet formally defined.
- Mac Catalyst in this repo overlaps conceptually with Apple macOS app and should remain a validation/build target, not a second Mac product strategy unless explicitly decided.

## Feature drift

Near parity with Apple for Ask DJ, Music DNA, Discover and Track Insight. Behind Apple on APNs/watchOS/VibeCast-specific surfaces.

## CI observations

Strong and appropriate for MAUI. Secret scanning in workflow is a useful repo-specific guard.

## Security observations

Good local credential and diagnostic redaction posture. WebSocket HA auth token handling is intentionally opt-in/local.

## Privacy observations

Good: no automatic diagnostic upload and no local source of truth for Music DNA/history.

## Recommendations

1. Add foundation-first AGENTS refresh.
2. Remove or pointerize local `SYNC_PROMPTS.md`.
3. Add a Windows-vs-Apple parity matrix with required, optional and intentionally absent capabilities.
4. Decide whether Mac Catalyst remains internal validation or becomes product surface.

## Priority

P1 for canonical-doc hygiene and parity matrix; P2 for Mac Catalyst decision.

## Estimated effort

Small to medium.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 8 |
| Architecture | 8 |
| Documentation | 8 |
| Testing | 8 |
| CI/CD | 8 |
| Security | 8 |
| Privacy | 8 |
| Release | 7 |
| Developer Experience | 7 |
| Overall | 7.8 |
