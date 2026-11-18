# Repository Discovery Report: `pcvantol/djconnect-pi`

## Overview

The Pi repo owns the Raspberry Pi Ambient Client: a touch-display, kiosk-style household client with local pairing, status, now playing, controls, readonly/light Ask DJ, Track Insight, Music DNA and Music Discovery rendering.

## Purpose

Owns Pi runtime, kiosk UX, local Client API daemon, mDNS while unpaired, updater, systemd integration and ambient/shared display behavior.

Does not own durable intelligence, Music DNA storage, Spotify credentials, backend playback logic or foundation docs.

## Strengths

- Excellent README clarity on what Pi intentionally does not implement: no PTT, no local DJ response audio, no local Music DNA authority.
- Correct Ambient Client framing: shared wall/device behavior, local-only pairing, household context.
- WebSocket fast path is capability-gated with HTTP fallback.
- Strong pytest coverage and shared HA contract fixture consumption.
- Release/update process is explicit and artifact-oriented.

## Weaknesses

- AGENTS is foundation-aware but should be refreshed to the full Epic 1 foundation set.
- The Pi has grown beyond "light" ambient display into Music DNA, Discovery and action surfaces. This may be justified, but should be reviewed against the capability matrix.
- The README lists many HA endpoints including some that seem broader than Pi's intended ambient role. This can create accidental scope creep.

## Architecture observations

Pi mostly follows the foundation. It renders backend-owned data and does not calculate intelligence. The risk is capability creep: if Pi becomes a full Intelligence Client, the Ambient Client class loses meaning.

## Product observations

Strong room/shared-device alignment. It should default to shared/household profiles after Epic 3. Personal Music DNA visibility on a shared wall display must be explicitly guarded by profile resolution and privacy mode.

## Technical debt

- Profile resolution is pending HA Epic 3.
- Shared-profile privacy rules cannot be fully enforced until backend profile contracts exist.
- Endpoint surface should be reviewed and minimized to Ambient needs.

## Product debt

- The Pi currently exposes richer features than the matrix's "readonly or light" wording in places.
- Needs a clear "Ambient Client capability budget" so it does not chase Apple/Windows parity.

## Feature drift

Ahead for an Ambient Client: Music DNA and Music Discovery display/actions. Behind Intelligence Clients on Ask DJ input/voice by design.

## CI observations

Strong: pytest, ruff/bandit via shared workflow, contract fixtures, Postman, release publishing.

## Security observations

Good local token and websocket-token posture. Local diagnostic routes require continued review because shared devices are physically accessible.

## Privacy observations

Good stated boundaries, but shared-screen leakage depends on future Profile Architecture.

## Recommendations

1. Define Ambient Client capability budget in Epic 2 backlog.
2. Refresh AGENTS to full foundation set.
3. Add explicit shared-profile/privacy tests once Profile Architecture exists.
4. Keep Pi Music DNA/Discovery read-heavy and backend-owned; avoid making it a personal management console.

## Priority

P1 for capability budget; P2 for foundation sync; P0 after Epic 3 for shared-profile privacy tests.

## Estimated effort

Small for docs; medium for future profile/privacy tests.

## Scores

| Dimension | Score |
| --- | ---: |
| Product | 7 |
| Architecture | 8 |
| Documentation | 8 |
| Testing | 8 |
| CI/CD | 8 |
| Security | 8 |
| Privacy | 7 |
| Release | 8 |
| Developer Experience | 8 |
| Overall | 7.8 |
