# Prompt History: Renderer-Safe Playback Projection

**Prompt ID:** Universal Receiver V1 — Renderer-Safe Playback Projection
**Generation:** V4
**Engineering program:** DJConnect Product Development
**Branch:** `codex/renderer-safe-playback-projection`
**Pull Request:** [#360](https://github.com/pcvantol/djconnect/pull/360)
**Merge Commit:** `637ab709174b1c49409259f66c902d23b32619fa`
**Decision:** `MERGED_UNRECONCILED` pending dedicated Finalization
**Execution date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Outcome

PR #360 establishes one Session Runtime-owned, backend-neutral playback
presentation projection for Renderer Hosts. Existing Playback Observation
normalizes safely observed track metadata and sends it through the existing
Broadcast snapshot and event stream. The projection contains only renderer-safe
fields: opaque replacement identity, state, title, artist, album, target,
duration, optional Home Assistant-proxied artwork and optional position.

When a reliable backend observation contains both duration and position, the
Runtime owns a bounded server-side progress clock. It publishes safe progress
updates at most once a second, corrects them from the existing backend snapshot
stream and stops on pause, stop, replacement, duration end, observer stop or
Runtime disposal. Renderer Hosts do not estimate playback time, access a
provider or receive a raw artwork URL or backend payload.

No Planner, Knowledge Engine, DJ Moment Engine or Session Flow ownership
changed. No persistence, provider queue read, endpoint, WebSocket channel or
provider polling was introduced. This unblocks, but does not implement,
Universal Receiver V1 Capability 3 — Now Playing Experience.

## Validation

- `python -m unittest discover -s tests` — 1320 passed, 7 skipped
- `ruff check custom_components tests` — passed
- `git diff --check` — passed
- `./scripts/runner/bootstrap_djconnect_macos_host.sh --verify` — MATCH
- `python -m unittest tests.test_capability_completion_lifecycle` — passed

Focused coverage verifies renderer-safe metadata normalization, HA-proxied
artwork, duplicate suppression, server-owned progress publication, snapshot
correction, pause, bounded duration, missing progress evidence, observer stop
and Runtime disposal.

## Known limitations

Only backends that safely expose both a duration and position can supply live
progress. No Playback Instance Identity, seek control, queue data, browser
progress estimation or artwork fetch/cache is introduced.

## Deferred work

Universal Receiver Capability 3 remains a separate presentation-only
implementation. Client-side progress estimators may be removed only by
separately authorized client migrations after the server contract is reconciled.

## Recommended next prompt

After this Finalization merges and Workspace Cleanup restores
`MERGED_RECONCILED` and `WORKSPACE_READY`, implement Universal Receiver V1
Capability 3 — Now Playing Experience as a passive renderer of the existing
Broadcast projection.
