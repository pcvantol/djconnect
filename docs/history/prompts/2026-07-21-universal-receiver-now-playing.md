# Prompt History: Universal Receiver V1 — Now Playing

**Prompt ID:** Universal Receiver V1 — Capability 3
**Generation:** V4
**Engineering program:** DJConnect Product Development
**Branch:** `codex/universal-receiver-now-playing`
**Pull Request:** [#362](https://github.com/pcvantol/djconnect/pull/362)
**Merge Commit:** `dfbc5826ae73762818e4bd002b97773852014394`
**Decision:** `MERGED_UNRECONCILED` pending dedicated Finalization
**Execution date:** 2026-07-21
**Created:** 2026-07-21
**Updated:** 2026-07-21

## Outcome

PR #362 completes Universal Receiver V1 Capability 3 with one minimal Now
Playing card. It renders only the existing renderer-safe Broadcast playback
projection: optional HA-proxied artwork, title, artist, album, playback status,
target, elapsed position and total duration.

The Receiver replaces its temporary presentation state from snapshots and
existing playback events. It displays the server-owned `position_ms` exactly as
published and does not create a browser timer, prediction, smoothing loop,
provider request or additional transport. Missing artwork and metadata degrade
to a hidden image and neutral placeholders; reconnect reconstructs the card
from the existing snapshot.

No Runtime, Planner, Knowledge Engine, DJ Moment Engine, Session Flow or
Broadcast ownership changed. No controls, queue, persistence, diagnostics,
configuration, endpoint or WebSocket channel was added.

## Validation

- `python -m unittest discover -s tests` — 1320 passed, 7 skipped
- `ruff check custom_components tests` — passed
- `git diff --check` — passed
- `./scripts/runner/bootstrap_djconnect_macos_host.sh --verify` — MATCH
- `python -m unittest tests.test_capability_completion_lifecycle` — passed

Focused Receiver coverage verifies Now Playing snapshot rendering, artwork and
metadata updates, server-published progress, state updates, missing-artwork
degradation, reconnect reconstruction, and the absence of browser polling or
a playback clock.

## Known limitations

The Receiver remains deliberately minimal. It has no controls, queue,
playlist, Ask DJ, diagnostics, Session selection, persistence, animations or
browser-owned playback logic.

## Deferred work

Future Universal Receiver capabilities remain separately authorized and must
consume the same renderer-safe Broadcast projections. Client-side progress
estimators may be removed only through separately authorized client migrations.

## Recommended next prompt

After this Finalization merges and Workspace Cleanup restores
`MERGED_RECONCILED` and `WORKSPACE_READY`, select the next bounded Universal
Receiver capability from current repository evidence. Do not add controls,
queue data or browser Runtime authority implicitly.
