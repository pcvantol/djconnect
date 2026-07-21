# Prompt History: Rolling Session Horizon Architecture

**Prompt ID:** `G2-PRODUCT-PR288-001`
**Prompt Title:** Rolling Session Horizon Architecture
**Generation:** 2
**Engineering Program:** DJConnect Product Development
**Branch:** `codex/rolling-session-horizon-architecture`
**Commit:** `8dacd7e674484e396dff6113554c27b9952c318a`
**Pull Request:** [#288](https://github.com/pcvantol/djconnect/pull/288)
**Merge Commit:** `ec9fbb3eff183cf380e9dc1ca8d630f465f1ad3f`
**Decision:** `ROLLING_SESSION_HORIZON_ARCHITECTURE_ACCEPTED`
**Execution Date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Objective

Define a provider-neutral, approximately twenty-minute Rolling Session Horizon
for future Planner experience planning without changing the current Planner,
queue, providers, transport, persistence or renderers.

## Repository evidence

- The Horizon is a Planner-owned, Runtime-scoped ephemeral object.
- The Observation Boundary may supply only an optional safe Upcoming Playback
  Projection; no future context degrades to current-track-safe planning.
- Horizon slots are speculative intent candidates, never generated DJMoments.
  Existing Flow records only consumed outcomes and Broadcast exposes no Horizon.
- Mood, Direction, Performance Memory, bounded Session feedback and normalized
  Audience Signals can affect only future planning through Planner policy.

## Validation

- Development-host desired-state verification: `MATCH`.
- Full local unit suite: 1240 passed, 7 skipped.
- Ruff and `git diff --check` passed.

## Known limitations

No Horizon domain implementation, provider projection, queue control, Lyrics,
audience adapter, feedback persistence, transport endpoint or renderer work is
included. The existing Planner remains at its current 15-minute implementation
horizon.

## Deferred work

Horizon domain model; Upcoming Playback Projection; basic planning window;
invalidation; Mood/Direction and feedback adaptation; Universal Receiver
audience drift reconciliation; Knowledge prefetch; Lyrics; narrative sequencing;
Discover/recommendation expansion; and audience-adaptive renderer adoption are
separate increments.

## Recommended next prompt

After this Finalization merge, select one fresh Pre-Flight-backed capability.
The Horizon roadmap's first cell is the runtime-local domain model; Persistent
Session Foundation is separately planned. Do not combine them.

