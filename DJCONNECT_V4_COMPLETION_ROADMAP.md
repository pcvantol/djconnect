# DJConnect V4 Completion Roadmap

**Status:** Canonical high-level completion projection
**Owner:** DJConnect Product Development
**Scope:** Sequencing from current Home Assistant server capabilities to the
complete V4 iOS experience. This document is orchestration only: it does not
change architecture, maturity, production behaviour or ownership.

## Executive summary

DJConnect V4 completes when the Home Assistant server can host a durable,
intelligent, privacy-safe DJ Session and the iOS Renderer Host can consume that
stable experience without owning business logic. V4 is not complete merely when
transport or SQLite exist. It requires a durable Session lifecycle and history,
a safe live Runtime, a sufficiently mature DJ performance pipeline, bounded
voice paths and stable renderer-safe contracts.

The server completes before iOS completion. The Persistent Session Platform and
Rolling Session Horizon are foundational tracks; neither displaces the AI DJ
product goal. Renderer adoption consumes stable server contracts and does not
redefine them.

## Status legend

- **CURRENT** — implemented and validated on current main.
- **NEXT** — first separately authorized cell after a fresh Pre-Flight.
- **PLANNED** — sequenced V4 work, not authorization.
- **BLOCKED** — requires a documented external capability or prior contract.
- **POST-V4** — deliberately outside this completion projection.

## Current baseline

| Area | Status | Repository evidence |
| --- | --- | --- |
| V4 Runtime, Session Flow and immutable DJMoments | CURRENT | `DJCONNECT_V4_ARCHITECTURE.md`, `DJ_SESSION_RUNTIME_CONTRACTS.md` |
| Planner | Stage 3 current | `docs/product/DJ_INTELLIGENCE_MATURITY.md` |
| Knowledge Engine | Stage 2 current | `docs/product/DJ_INTELLIGENCE_MATURITY.md` |
| DJ Moment Engine | Stage 2 current; Stage 3 partial | `docs/product/DJ_INTELLIGENCE_MATURITY.md` |
| Performance Memory | CURRENT, Runtime-scoped only | `DJ_SESSION_RUNTIME_CONTRACTS.md` |
| Broadcast transport | CURRENT: HTTP snapshot, snapshot-first WebSocket, capability discovery | `docs/technical/BROADCAST_TRANSPORT.md` |
| Recovery | CURRENT: bounded owner cursor replay; fresh snapshot fallback | `SESSION_FLOW_RECOVERY_ARCHITECTURE.md` |
| Persistent Session / Rolling Horizon | Accepted architecture, implementation deferred | `PERSISTENT_SESSION_ARCHITECTURE.md`, `ROLLING_SESSION_HORIZON_ARCHITECTURE.md` |
| Renderer model | CURRENT architecture: clients are Renderer Hosts | `docs/product/DJ_PRESENTATION_ARCHITECTURE.md` |
| Apple baseline | CURRENT pairing, Session lifecycle routes, HTTP/WebSocket and APNs foundations | `docs/technical/CLIENT_SERVER_TRANSPORT.md`, `docs/technical/WEBSOCKET_API.md` |

## V4 product completion definition

A completed V4 experience is one where a Profile can start a Session, the server
hosts a coherent live performance around playback, authorized users can recover
live presentation, inspect durable Session history, replay eligible Moments,
and receive a rich but bounded DJ performance across stable Renderer Host
contracts. Playback and queue execution always remain Music Backend-owned.

## Track overview

| Track | Goal | Depends on | V4 role |
| --- | --- | --- | --- |
| A. Persistent Session Platform | Durable Session lifecycle and history without durable Runtime. | Persistent Session Architecture | Required |
| B. Rolling Session Horizon | Approximately 20-minute, ephemeral experience planning. | Rolling Horizon Architecture; safe observations | Required |
| C. DJ Session Intelligence | Mature planning, knowledge and Moment performance. | Maturity cells, Horizon where needed | Required |
| D. Lyrics Capability | Copyright-safe, Planner-approved Lyrics knowledge. | Knowledge/Horizon contracts | Required for V4 Lyrics experience |
| E. Voice Platform | Room voice and per-user Moment replay as separate paths. | Stable current/historical Moment contracts | Required |
| F. Renderer Hosts | Consume stable projections without business logic. | Server contracts | Required only for V4-critical hosts |
| G. Apple/iOS V4 | Native iOS completion on stable server contracts. | A–E server gates | Required |

## Track A — Persistent Session Platform

The accepted `LOCALIZATION_NARRATIVE_ARCHITECTURE.md` applies to every
user-facing Track A capability. Its delivery remains a separately sequenced
cross-cutting roadmap; this does not authorize translations or renderer work.

1. **CURRENT — Persistence foundation:** DJConnect-owned SQLite service,
   schema/version metadata, migration runner, integrity checks and test harness.
2. **CURRENT — Lifecycle store:** Profile-owned Session identity and
   `OPENING`/`ACTIVE`/`INTERRUPTED`/`ENDED` transitions.
3. **CURRENT — Startup reconciliation:** deterministic technical closure of open
   Sessions; re-bootstrap remains separately gated.
4. **CURRENT — Historical projections and query service:** immutable,
   renderer-safe historical Session and DJMoment projections plus one
   owner-authorized, transport-independent query boundary; no pagination or
   client/transport feature.
5. **PLANNED — Retention:** expiry, cleanup, favorites/preservation only when
   approved, visibility and audit-safe policy.
6. **PLANNED — Backup and export:** HA backup/restore validation plus versioned
   Profile and Session-history export/import independent of SQLite.

Runtime, Planner graphs, Performance Memory, Broadcast delivery/recovery state,
Playback Instance Identity, temporary audio and TTS URLs remain ephemeral.

## Track B — Rolling Session Horizon

1. **PLANNED — Horizon domain model:** runtime-local experience slots,
   invalidation vocabulary and policy target.
2. **PLANNED — Upcoming Playback Projection:** provider-neutral bounded future
   context with shorter-window and current-track degradation.
3. **PLANNED — Basic window:** deterministic approximately 20-minute planning
   around playback, including Silence-capable slots; no queue action.
4. **PLANNED — Replanning:** invalidation, debouncing, stability window,
   cancellation of obsolete intents and confidence handling.
5. **PLANNED — Adaptation:** Mood, Direction, approved likes/dislikes/skips and
   normalized Audience Signals affect only future slots.
6. **PLANNED — Prefetch:** cancellable Runtime-scoped Knowledge preparation.

Only realized outcomes become Session Flow and, when approved by Track A,
historical Session projections.

## Track C — DJ Session Intelligence

The maturity model remains authoritative; this roadmap does not advance it.

- **Planner:** complete the bounded `PL-3.2` audience-direction cell, then
  pacing, cadence, horizon-aware scheduling, deterministic Silence, openings,
  middle/closing structure, callbacks and longer narrative arcs through small
  cells.
- **Knowledge:** enrich existing artist/album/genre context only through safe
  source-qualified cells; add confidence/provenance and later prefetch.
- **Moment Engine:** complete the approved Stage 3 baseline, then persona-aware
  variation, richer transitions/updates, openings, closings and continuity
  without new alternate pipelines.
- **Discover:** retain Profile alignment while adding controlled multi-path
  discovery, adjacent genres, deep cuts and context-aware recommendations only
  after corresponding Planner/Knowledge evidence.

## Track D — Lyrics Capability

Lyrics is a dedicated intelligence capability, not a provider field.

1. Lyrics Architecture: provider, copyright, quotation and retention boundary.
2. Safe Lyrics Knowledge Projection: theme/meaning and short compliant
   quotation rules; never unrestricted song text.
3. Planner-approved Lyrics intent and Horizon-aware prefetch/cancellation.
4. Lyrics-aware immutable Moment realization, with voice-safe short output.
5. Rich iOS Lyrics Insight and eligible replay presentation.

Knowledge selects safe context, Planner decides relevance, Moment Engine
performs, and clients render the immutable result.

## Track E — Voice Platform

Two paths remain separate.

**Autonomous room voice** consumes a current voice-eligible DJMoment. HA resolves
the active playback output, its room/area and an eligible DJConnect Voice
Satellite in that room. No eligible satellite is a deterministic no-speech
fallback; automatic voice never selects an unrelated room.

**User-initiated replay** is available for eligible current or historical
Moments. A shared server-side voice-render service performs request-scoped
authorization, optional coalescing, short-lived bounded audio delivery and
independent local playback for each requester. It has no global
`last_audio_url`, singleton current-TTS state or canonical audio persistence.

Sequence: voice-render architecture → shared application service → visibility
and concurrency → ephemeral delivery → room resolver/Satellite delivery →
client replay contract → Renderer adoption.

## Track F — Renderer Hosts

HA remains canonical Runtime and business-logic owner. Apple, Windows, Pi, Web
and Voice are Renderer Hosts; Universal Receiver is a projection/transport
capability, not a browser mandate. The Wall Pi native QML host remains
canonical. A browser receiver can be additive but never replaces QML.

V4-critical renderer work is limited to stable live Moments, recovery,
historical Session/Moment views, replay and Lyrics presentation. Broader
renderer expansion is not a server-completion dependency.

## Track G — Apple/iOS V4 completion

After the server contracts are stable, iOS adopts them in this order:

1. Profile/device binding; Manual, Discover and eligible Continue start.
2. Current Session, current Moment and live Broadcast subscription.
3. HTTP snapshot fallback, owner recovery, foreground/background reconnect.
4. Current Session timeline and renderer-safe Moment detail.
5. Historical Session browser, paginated Moment timeline and interrupted/ended
   states.
6. Replay TTS on every eligible Moment with concurrent independent requests.
7. Lyrics Insight, transitions, Session Updates and Discover rendering.
8. Approved Mood/Direction controls, feedback, favorites/retention controls.
9. Accessibility, lifecycle resilience and remaining required demo-mode support.

**iOS V4 complete** means iOS can start/observe/recover a Session; render live
and historical authorized Moments; replay eligible Moments; present Lyrics and
intelligence contributions; send only approved feedback; preserve Profile and
visibility boundaries; coexist with autonomous room voice; and rely on server
contracts rather than client-owned business logic. WatchOS/macOS parity is
separate unless a later V4 gate explicitly adds it.

## Dependency graph

```text
Persistent Session Architecture
  -> persistence foundation -> lifecycle/reconciliation -> historical projections
  -> stable history APIs -> replay voice -> iOS history/replay

Rolling Horizon Architecture
  -> horizon model -> future projection -> replanning/adaptation
  -> prefetch -> Lyrics/narrative intelligence -> iOS intelligence adoption

Shared voice render service -> autonomous room voice
Stable live Broadcast/recovery (CURRENT) -> all live Renderer adoption
```

Tracks A and B can proceed in parallel after individually authorized first
cells. Track C may progress through existing independent maturity cells in
parallel with A/B when those cells do not need history or future context. Track
D follows its own source/copyright architecture and benefits from B prefetch.
Track E replay follows historical Moment contracts; room voice follows stable
current Moment plus shared voice service. Track G waits for the relevant server
contracts rather than every optional Renderer Host.

## Ordered implementation waves

1. Persistence foundation and one bounded existing Planner maturity cell.
2. Session lifecycle store; Horizon domain model; Lyrics architecture.
3. Startup reconciliation; Upcoming Playback Projection; source-qualified
   Knowledge cells.
4. Historical projections/history APIs; horizon replanning; shared voice service.
5. Retention/backup/export; feedback/audience adaptation; Lyrics realization.
6. Historical replay and autonomous room voice; stable iOS live/history/replay.
7. Narrative intelligence, Discover expansion and iOS rich Moment adoption.

Every item remains one capability, one vertical slice and one Finalization
cycle; waves are coordination, not authorization to bundle work.

## Server completion gate

The HA server is V4-complete only when all of the following are stable:

- Persistent Session lifecycle, restart safety, history, retention and approved
  backup/export boundaries;
- renderer-safe historical Session/Moment pagination contracts;
- current Broadcast, snapshot-first delivery, owner recovery and fresh snapshot
  fallback;
- stable on-demand replay voice and autonomous room-aware voice;
- implemented Rolling Horizon with safe degradation;
- agreed Planner/Knowledge/Moment maturity, including Lyrics and Discover
  baselines explicitly selected from the maturity model;
- stable renderer-safe contracts without client-owned business logic.

## Deferred outside V4

**BLOCKED:** Music Assistant qualification, Playback Observation Stage 2 and
Continue Stage 2 remain dependent on their existing external capability gates.

**POST-V4:** cross-install continuation, cloud Profile roaming, cross-household
sharing, persistent/cross-Session Broadcast replay, public recovery tokens,
native Pi replacement by Chromium, broad Web Receiver replacement, voice
cloning/training, speculative analytics, long-term autonomous learning and
provider expansion not required by approved V4 cells.

## Guardrails and canonical links

- Runtime, Performance Memory and Broadcast recovery always remain ephemeral.
- Music Backend owns playback and queue execution.
- Planner decides; Knowledge Engine selects; Moment Engine performs; Broadcast
  distributes; Renderer Hosts present.
- No renderer or persistence increment may redefine those boundaries.
- Use `DJ_INTELLIGENCE_MATURITY.md` for actual maturity and executable cells.

Canonical decisions: [V4 Architecture](DJCONNECT_V4_ARCHITECTURE.md),
[Runtime Contracts](DJ_SESSION_RUNTIME_CONTRACTS.md),
[Persistent Session](PERSISTENT_SESSION_ARCHITECTURE.md),
[Rolling Horizon](ROLLING_SESSION_HORIZON_ARCHITECTURE.md),
[Intelligence Maturity](docs/product/DJ_INTELLIGENCE_MATURITY.md),
[Presentation Architecture](docs/product/DJ_PRESENTATION_ARCHITECTURE.md) and
[Broadcast Transport](docs/technical/BROADCAST_TRANSPORT.md).
