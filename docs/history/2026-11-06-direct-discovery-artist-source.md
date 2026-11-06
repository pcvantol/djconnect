## 2026-11-06 — Direct artist playback from Discovery

#### Repository Status

Explicit owner choice: play the selected artist directly through Spotify,
without a This Is promise. Dedicated branch codex/discovery-direct-artist-20261106
starts at qualified main48434a60ccef649725a4bc8898f4aa3210570e6a. Predecessor
source1491 and separate Finalization1492 are merged and reconciled; the verified
Finalization worktree was bundled and removed. Current machine verification
exited0/MATCH. Source review and exact-head protected authorization are separate.

#### Management Summary

Artist Play Now resolves the exact original server-cached artist identity and
starts that same artist context. Editorial search and playlist-items access are
not prerequisites. The existing paired Profile/account/consent/cache/output and
single-transport fences remain. No client URI, guessed playlist, fan playlist,
top-tracks substitute, transfer, queue append or automatic retry is introduced.
Track, album, playlist and read-only explicit candidate diagnosis remain separate.
The three actual artist read probes succeeded but found no qualified official
This Is search candidate; this establishes the unusable dependency, not the
Spotify app's quota mode. No new OAuth or broader scope is needed by this change.

The original isolated HA failure is preserved before the product fix. Current
synthetic provider/real paired HA checks validate artist identity, one direct
context PUT, no editorial lookup, ignored extra client URI, wrong identity,
denial, duplicate/concurrent selection, stale cache, changed pairing during artist
and token waits, active output and actual aiohttp disconnect without replay.
See the separate qualification record for final test counts and source pins.
No source proof claims installed, live provider, native or audible acceptance.

#### Roadmap Position

Generation2 Product Development / Phase1 Platform Qualification is unchanged.
This repairs an existing Discover action; no new platform capability is issued.
Golden998 scenario definitions, EN/NL selection, all five UI languages and
execute:false are preserved. Current evidence is rebound only from actual reruns.

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

Exact-head Owner Authorization, protected source merge, independent main CI,
separate Finalization and HA-dev debug install with original #1439 remain gates.
After install, real artist-context readback and native/audible acceptance must
be recorded separately. #1439 live signing/restore/physical Apple/APNs gates
remain open. Retained-latest #1486 remains outside this build.

#### Deferred Items

Existing HAEVN artist-collections WIP is preserved in its own branch. ForYou
receipt correlation, Bulletin speech/retention/image contracts and Apple UI
follow-ups retain their own owners and evidence. Help28 EN/NL /42 DE-FR-ES
textual qualification boundary and all five-language UI data remain unchanged.
The timer remains stopped.

#### Repository State

Source increment is locally reviewable after its checks; no merge or install is
claimed. Repository State: `MERGED_RECONCILED` describes predecessor source1491
only; this source requires its own protected merge and separate Finalization.

#### Workspace State

Only the new repair worktree is modified. Original detached/canonical worktrees,
HAEVN WIP, original #1439 overlay, evidence and private installation rollback are
preserved. No cleanup or user-data deletion is included.

<!-- direct-discovery-artist-source-end -->

