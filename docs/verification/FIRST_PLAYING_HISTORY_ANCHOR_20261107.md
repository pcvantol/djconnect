# First playing history observation — 7 November 2026

Decision: local source qualification only.

## 2026-11-07 — First playing observation after a paused projection

#### Repository Status

Bounded Core source correction from fully reconciled main
`8ab09da8ce0c8c29d335cd5caefefc790d54011e` (#1509 / #1510). HA-dev debug
`8fc90590e843241128109230db55cb936e4d4757` remains installed with the
original #1439 overlay. Existing authorized protected delivery applies.

#### Management Summary

An ordinary Dutch current-artist answer appeared in a fresh Mac Session,
but neither the Session nor paired Profile history retained that turn. The
original request/response correlation is unavailable. The original Session
had history enabled, no retained playback observation for its first item,
and later observations for other items. No old request was replayed.

On exact predecessor product, isolated paired real HA reproduces HTTP 200
with correct literal metadata and private_ephemeral, history_persisted false
and no entry IDs after observing a paused item and then the same item playing.
The Runtime previously checked only item-ID inequality to record playing,
although paused playback already exposes that same ID.

The first transition into playing now reaches the existing history transaction.
The same item on resume reuses the repository's deduplicated observation; a
paused-only projection does not record playback. History disabled, owner,
withdrawal, clear, source binding and literal-text archive rules remain.
No API field, authority, provider call, playback dispatch or model path added.

The revised real HA harness uses the genuine paired request and existing
SQLite/Store paths with synthetic Spotify/STT fixtures. The original Session
contains both conversation entries; the same two exchanges are visible to
paired Mac, iPhone and Watch fixtures and survive Store/SQLite reload. Resume
preserves the same observation ID, another owner is denied, clear withdraws
the exchanges, and the history-disabled paused-to-playing case remains
private_ephemeral without a playback anchor or history message. Ten cases pass.
No live provider, native, audible or installed acceptance is claimed.

All 4,735 canonical tests are accounted for (11 existing skips); 172 framework
and 18 lifecycle/roadmap/Postman checks, Ruff and Bandit pass. All 42 isolated
HA groups use frozen product source. Current receipts come from actual reruns;
historical proof stays frozen. All five UI languages and Help 28/42 stay intact.

#### Roadmap Position

Generation 2 Product Development / Phase 1 Platform Qualification unchanged.
This corrects existing playback observation and current metadata retention.

#### Rolling Horizon (Execution Horizon — Next 5 Planned)

Derived afresh from docs/roadmap/v1/djconnect-platform-v1.json and CATALOGUE.md;
producer edges SETTINGS-4/6/8/10/12 retain the same prerequisites. These entries
do not issue prompts or grant execution/native dispatch authority.

1. **SETTINGS::APPLE::EDITOR — One Jouw DJ editor and shared Session quick controls**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

2. **SETTINGS::PI::ADOPTION — Pi allowed shared Session settings and legacy disposition**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

3. **SETTINGS::ESP32::ADOPTION — ESP32 Assist/voice/settings compatibility and legacy disposition**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

4. **SETTINGS::VIBECAST::COMPAT — Shared renderer allowed Session fields without Profile preferences**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

5. **SETTINGS::WEBSITE::COPY — Six-parameter scope/help and obsolete settings copy audit**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

#### Blocked Items

Exact-head Source gates and Owner Authorization, merge, independent main CI,
debug composition with the original #1439, install/readback, separate Final
and scoped cleanup remain. Any native acceptance requires a fresh ordinary
question and current qualified source, with no replay of the old request.

#### Deferred Items

Golden remains source protocol only and execute:false; no newly qualified
fixture owner, provider coverage or native admission is asserted. Physical
Watch, signing/restore, retained latest #1486 and APNs remain independent.
The Dutch opening terminology discrepancy remains separate. Keep the timer
stopped and retain original WIP, private evidence and rollback.

#### Repository State

Repository State: `MERGED_RECONCILED` for predecessor only. This Source must
merge and then receive its own separate Final.

#### Workspace State

Workspace State: `NOT_READY` until protected delivery and own Final cleanup.
See [qualification](docs/verification/FIRST_PLAYING_HISTORY_ANCHOR_20261107.md).

<!-- first-playing-history-anchor-source-20261107-end -->

Portable proof: `examples/client_contracts/current_metadata_history_v1/actual-ha-wire.json`.
Private evidence root: `/Volumes/Shared Data/tmp/pcvantol/core-paused-first-observation-20261107`.
Original native evidence stays private; no credentials, original request payload or live history is included.
