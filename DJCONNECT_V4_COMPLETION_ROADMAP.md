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

## V4 milestone — Session Intelligence Runtime Complete

**Status:** Completed on current main.

The **Session Intelligence Runtime Integration Epic** is complete. The Runtime
is the canonical execution engine for every currently supported Track Started
decision. Planner, Knowledge Engine, DJ Moment Engine, Session Flow and
Broadcast now execute through one integrated, server-owned Runtime lifecycle.
The legacy Track Started path remains only bounded runtime protection when that
lifecycle cannot safely execute.

Subsystem ownership is complete and stable. This is the transition from
runtime-architecture construction to experience expansion: future intelligence
work must extend the existing Planner, Knowledge and DJ Moment Engine
abstractions and their existing Runtime lifecycle. It must not introduce a
second Runtime pipeline.

## Current baseline

| Area | Status | Repository evidence |
| --- | --- | --- |
| V4 Runtime and Session Intelligence lifecycle | CURRENT and integrated | `DJ_SESSION_RUNTIME_CONTRACTS.md`, this milestone |
| Planner, rolling horizon, candidate slots and planned intents | CURRENT, Runtime-scoped | `ROLLING_SESSION_HORIZON_ARCHITECTURE.md`, `docs/product/DJ_INTELLIGENCE_MATURITY.md` |
| Knowledge Engine and prepared-knowledge path | CURRENT through supported intent resolution | `docs/product/DJ_INTELLIGENCE_MATURITY.md` |
| DJ Moment Engine, Session Flow and immutable DJMoments | CURRENT through supported Track Started realization | `DJ_SESSION_RUNTIME_CONTRACTS.md`, `docs/product/DJ_INTELLIGENCE_MATURITY.md` |
| Performance Memory | CURRENT, Runtime-scoped only | `DJ_SESSION_RUNTIME_CONTRACTS.md` |
| Broadcast transport | CURRENT: HTTP snapshot, snapshot-first WebSocket, capability discovery | `docs/technical/BROADCAST_TRANSPORT.md` |
| Recovery | CURRENT: bounded owner cursor replay; fresh snapshot fallback | `SESSION_FLOW_RECOVERY_ARCHITECTURE.md` |
| Persistent Session | CURRENT foundation, lifecycle, reconciliation, history and retention; backup/export remains planned | `PERSISTENT_SESSION_ARCHITECTURE.md` |
| Experience Renderer model | CURRENT architecture; renderer delivery is the next focus | `docs/product/DJ_PRESENTATION_ARCHITECTURE.md`, `docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md` |
| Apple baseline | CURRENT pairing, Session lifecycle routes, HTTP/WebSocket and APNs foundations | `docs/technical/CLIENT_SERVER_TRANSPORT.md`, `docs/technical/WEBSOCKET_API.md` |

## V4 product completion definition

A completed V4 experience is one where a Profile can start a Session, the server
hosts a coherent live performance around playback, authorized users can recover
live presentation, inspect durable Session history, replay eligible Moments,
and receive a rich but bounded DJ performance across stable Renderer Host
contracts. Playback and queue execution always remain Music Backend-owned.

## Roadmap transition

The roadmap is now organized into three deliberately separate tracks. Completion
of the Runtime Integration Epic does not make deferred experience or
intelligence work implicit authorization.

### Platform — completed foundation

- Session Runtime
- Planner
- Knowledge Engine
- DJ Moment Engine
- Session Flow
- Broadcast
- Session Intelligence Runtime

These are stable, server-owned foundations. Maintenance may correct defects,
but new product work reuses their established ownership boundaries.

### Experience — primary next focus

**Universal Receiver V1 is the primary active architectural Epic.** Its
server-side Renderer Host contract is complete. Capability 1 — Broadcast
Connection and Session Rendering — and Capability 2 — Session Flow Timeline
Rendering — are complete. Subsequent browser delivery, like Apple, Windows,
Raspberry Pi and Voice delivery, must consume existing Broadcast projections
and server APIs without acquiring Runtime ownership.

Universal Receiver V1 Capability 3 — Now Playing Experience — is complete in
PR #362, merged as `dfbc5826ae73762818e4bd002b97773852014394`. It consumes the
renderer-safe Playback Projection from PR #360 and introduces no browser-owned
playback API, transport or timing authority.

- Universal Receiver V1
- Apple
- Windows
- Raspberry Pi
- Voice
- Verification Platform
- Session Simulation

Each remains a separately authorized capability. This ordering identifies
experience-platform focus; it does not authorize a browser implementation,
client change or renderer-specific transport.

### Intelligence Expansion — deferred future evolution

- Preferences
- Music DNA expansion
- Narrative Sequencing
- Lyrics
- Discover Evolution
- Audience Intelligence
- Playback Observation Stage 2
- Continue Stage 2

Audience Intelligence remains intentionally deferred. Its future use must be a
bounded influence on the existing Planner rather than a new execution path.

## Platform detail — Persistent Session

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
5. **CURRENT — Retention:** bounded expiry and transactional cleanup of
   immutable historical projections; favorites/preservation remains deferred.
6. **PLANNED — Backup and export:** HA backup/restore validation plus versioned
   Profile and Session-history export/import independent of SQLite.

Runtime, Planner graphs, Performance Memory, Broadcast delivery/recovery state,
Playback Instance Identity, temporary audio and TTS URLs remain ephemeral.

## Completed Runtime Integration scope

The completed lifecycle includes the Rolling Session Horizon, Upcoming Playback
Projection, Planning Window, candidate slots, Planned Intents, deterministic
selection and replanning, planning readiness, Knowledge Prefetch, Prepared
Knowledge consumption and the canonical Track Started activation path. It is
bounded to observable playback and remains Runtime-scoped and ephemeral.

Only realized outcomes enter Session Flow and Broadcast. Future changes to
preferences, narrative, Lyrics, Discover or Audience Intelligence must reuse
this lifecycle; provider queues, persistence and renderer state remain outside
Planner ownership.

## Intelligence Expansion detail — Lyrics Capability

Lyrics is a dedicated intelligence capability, not a provider field.

1. Lyrics Architecture: provider, copyright, quotation and retention boundary.
2. Safe Lyrics Knowledge Projection: theme/meaning and short compliant
   quotation rules; never unrestricted song text.
3. Planner-approved Lyrics intent and Horizon-aware prefetch/cancellation.
4. Lyrics-aware immutable Moment realization, with voice-safe short output.
5. Rich iOS Lyrics Insight and eligible replay presentation.

Knowledge selects safe context, Planner decides relevance, Moment Engine
performs, and clients render the immutable result.

## Experience detail — Voice Platform

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

## Experience detail — Renderer Hosts

HA remains canonical Runtime and business-logic owner. Apple, Windows, Pi, Web
and Voice are Renderer Hosts; Universal Receiver is a projection/transport
capability, not a browser mandate. The Wall Pi native QML host remains
canonical. A browser receiver can be additive but never replaces QML.
Its canonical server boundary is
[`docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md`](docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md).

V4-critical renderer work is limited to stable live Moments, recovery,
historical Session/Moment views, replay and Lyrics presentation. Broader
renderer expansion is not a server-completion dependency.

## Experience detail — Apple/iOS V4 completion

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

## Post-milestone dependency graph

```text
Persistent Session Architecture
  -> persistence foundation -> lifecycle/reconciliation -> historical projections
  -> stable history APIs -> replay voice -> iOS history/replay

Completed Session Intelligence Runtime
  -> existing Planner / Knowledge / DJ Moment Engine abstractions
  -> bounded experience and intelligence extensions

Universal Receiver V1 server architecture
  -> Capabilities 1 and 2 complete -> future renderer experience evidence

Shared voice render service -> autonomous room voice
Stable live Broadcast/recovery (CURRENT) -> all live Renderer adoption
```

The completed Runtime foundation lets Experience work proceed without a new
server pipeline. Universal Receiver delivery is the primary next architectural
Epic. Apple, Windows, Raspberry Pi and Voice work consume the same stable
Renderer Host boundary. Intelligence Expansion remains independently deferred
and may proceed only through the maturity model and a fresh Pre-Flight.

Every item remains one capability, one vertical slice and one Finalization
cycle; this roadmap is sequencing, not authorization to bundle work.

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
