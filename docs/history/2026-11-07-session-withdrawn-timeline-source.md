## 2026-11-07 — Keep withdrawn conversation entries valid in Session history

#### Repository Status

Bounded Core correction from reconciled main `f1c3b21599692dde180f8df3420f4ca14f641063`.
The current HA-dev build contains #1515 and the original #1439 overlay.

#### Management Summary

A completed individual deletion left four dependent conversation entries
unavailable. The ordinary paired version 2 timeline included the four
entries without required conversation identity and context. Apple rejected
the entire page. Profile history remained readable.

The projection now supplies the existing conversation identity, role,
input type and owning Session on each unavailable entry. Dependent text,
selection context, sources, media, actions and speech remain withdrawn.
The original deletion scope, stored rows, ordering, and unrelated content
are preserved. No new deletion or replay was run against HA-dev.

The synthetic timeline regression failed before the correction and passes
after it, including both roles and independent neighboring content. All
42 isolated HA groups, the standalone catalogue check, 4,735 canonical
tests with 11 existing skips, 172 framework checks, Ruff and Bandit passed.

#### Roadmap Position

Generation 2 Product Development / Phase 1 Platform Qualification unchanged.
The correction uses the existing paired Session history contract and
owner deletion boundary.

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

Source checks and exact Owner Authorization, protected merge, independent
main CI, HA-dev debug installation/readback, native timeline read and
separate Final remain.

#### Deferred Items

Golden remains execute:false. Physical Watch, signing, restore authority
and APNs remain separate. Keep the timer stopped and retain unrelated WIP.

#### Repository State

Repository State: `MERGED_RECONCILED` for the predecessor only.

#### Workspace State

Workspace State: `NOT_READY` until protected delivery and own Final cleanup.
See [qualification](docs/verification/SESSION_WITHDRAWN_TIMELINE_20261107.md).

<!-- session-withdrawn-timeline-source-20261107-end -->
