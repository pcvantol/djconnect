# Continue Current Playback Continuity

**Status:** Authorized architecture contract; implementation deferred
**Owner:** DJConnect Product Development
**Scope:** One provider-neutral current-playback observation for a future Continue Session Start. This document authorizes no production code, API, storage or renderer behaviour.

## Purpose

This contract defines the smallest safe way for a future `Continue` DJ Session to join playback that is already active. The Music Backend Playback Control Boundary remains authoritative for playback and its queue. DJConnect creates an ephemeral DJ Session around one observed current item; it does not take over the music service.

This is the canonical contract for Continue Current Playback Continuity. The Runtime and product documents link here rather than restating its detailed rules.

## Continue semantics

`Continue` is a Session Start Strategy: it explains why a new DJ Session starts. Under this contract it may join one item that is already actively playing. Mood and Persona remain independent Runtime inputs.

Continue does not:

- continue an ended DJ Session or restore its Performance Memory;
- reconstruct Session Flow or playback history before the new Session starts;
- adopt, copy, order or mutate a provider queue, playlist or album;
- restart the current item, replace playback or start playback when it is inactive; or
- create persistent playback or identity state.

| Term | Meaning |
| --- | --- |
| Continue Session Start Strategy | The listener's objective to join available playback. |
| Current Playback Continuity | One active item is observed and adopted at the start of a new DJ Session. |
| DJ Session continuity | Restoring a prior Runtime, Flow or Performance Memory; explicitly out of scope. |
| Queue continuity | Observing or continuing a provider queue; explicitly out of scope. |
| Persistent session restoration | Restoring durable state across a Session boundary; explicitly out of scope. |

## Current Playback Projection

The future use-case boundary exposes one immutable, ephemeral `CurrentPlaybackProjection`. It is an observation, not a playback command, provider payload or general-purpose Playback Context replacement. It exists for one Continue-start request and is discarded with that request or its Runtime.

An `ACTIVE` projection has these required fields:

- `observed_at`: an observation timestamp;
- `playback_state`: the bounded active state, initially `playing` only;
- `playback_item_identity`: the required opaque Playback Instance Identity owned by the Music Backend Observation Boundary for this concrete occurrence;
- `track_identity`: an opaque adapter-generated track identity when the provider can safely supply one; and
- `completeness`: an explicit bounded indication of which optional safe fields were observed.

Optional fields are bounded, safe track display metadata (title, artist names, album title and existing safe artwork reference), playback position and duration. Adapters may omit them and declare that omission in `completeness`; Runtime must not infer identity from display text. An adapter may expose a capability flag for each optional field, but the first implementation requires neither output, account nor context identity.

The projection never contains a queue, future item, playlist contents, context/queue URI, raw provider response, credentials, provider-specific metadata, Music DNA, Profile preferences, history or inferred identity. Its opaque identities are Runtime-internal: they never enter public DJ Moments, Broadcast payloads or persistent Profile state.

### Playback Instance Identity

Playback Instance Identity identifies exactly one concrete playback occurrence.
It is opaque, immutable, ephemeral and provider-neutral at the Runtime
boundary. The Music Backend Observation Boundary owns it. Its provider adapter
observes provider behaviour, determines when an occurrence begins and exposes
the same identity in both the Current Playback Projection and the corresponding
Track Started event. It is replaced only for a genuinely new occurrence.

Runtime only stores and compares this identity for bounded, runtime-scoped
deduplication. It never derives, interprets or persists it, and must never infer
it from URI, title, artist, album, artwork, timestamp, progress or other display
metadata. An Observation Boundary unable to satisfy this contract returns the
typed `UNSUPPORTED` or `UNAVAILABLE` result; no Runtime-generated or heuristic
identity is allowed.

Its lifetime is only the concrete playback occurrence: it is immutable,
ephemeral, Runtime-internal and discarded when that occurrence or its Runtime
ends. It is never written to Session Flow, Performance Memory, Music DNA,
Profile state, persistence, Broadcast, public APIs, immutable DJ Moments or
reconstruction logs.

### Observation capabilities

The Music Backend Observation Boundary determines support for each concrete
observation implementation. It exposes bounded capability information for
`supports_current_playback_projection`,
`supports_playback_instance_identity`,
`supports_live_track_started_events` and `supports_continue_stage2`.
Continue Stage 2 is enabled only when all required observation capabilities are
available. It is never assumed globally for a backend merely because another
observation implementation of that backend supports it.

### Track Started observation contract

A Track Started event is the canonical Runtime entry point for one normalized
playback observation. It carries the exact Playback Instance Identity supplied
by the Observation Boundary's Current Playback Projection and only safe canonical track
context needed by the established intelligence pipeline. Provider notifications
are normalized by adapters before they reach Runtime. They never expose raw
provider payloads, credentials, queue contents, future tracks or history.

The event path is:

```text
Music Backend Observation Boundary → normalized Track Started(identity) → Runtime
→ Planner → Knowledge Engine → DJ Moment Engine → Session Flow → Broadcast
```

Continue injects its adopted occurrence into this path once; it does not create
a second intelligence pipeline. Existing Track Insight enrichment may be reused
unchanged. Its normal safe failure behaviour remains sufficient: partial
metadata is acceptable and Continue adds no provider retrieval or retry path.

The tagged read result is exactly one of:

- `ACTIVE(projection)`: one eligible, currently playing item was observed;
- `NO_ACTIVE_PLAYBACK`: the read succeeded but no eligible playing item exists;
- `UNAVAILABLE`: the Observation Boundary, configuration or provider could not supply a trustworthy observation; or
- `UNSUPPORTED`: the Observation Boundary cannot reliably satisfy the required identity and live-observation capability contract.

`NO_ACTIVE_PLAYBACK` is not an error disguised as an empty payload, and neither
`UNAVAILABLE` nor `UNSUPPORTED` is silently converted to no playback. Runtime
is not created for `UNSUPPORTED` and never generates a fallback identity or
introduces queue ownership to compensate.

## Ownership and privacy

| Owner | Responsibility |
| --- | --- |
| Music Backend Playback Control Boundary | Is authoritative for playback, queue, transport and playback commands. |
| Music Backend Observation Boundary | Owns playback observation, Current Playback Projection, Track Started observation, Playback Instance Identity and provider normalization. |
| Provider adapter | Implements the Observation Boundary, translates provider state and contains all provider-specific logic and raw payloads. |
| Session Start orchestration | Resolves Profile and backend authority, requests at most one projection, validates the Continue result and starts no playback. |
| Session Runtime | Receives only a validated projection and opaque identity as startup inputs; owns the ephemeral Session and no queue snapshot, playback authority or identity derivation. |
| Planner | Receives Continue independently from Mood and Persona, then decides future performance after startup; it never approves playback adoption or controls playback. |
| Session Flow | Records the new Session Start and only the explicitly adopted current item; it never reconstructs earlier playback or queue content. |
| Performance Memory | Starts fresh and may contain only contributions canonically published after the new Session begins. |

Only the resolved Profile authorized for the selected Music Backend binding may request adoption. Shared and guest contexts may use safe shared track metadata only; they never receive personal account detail, Music DNA, history, preferences or opaque playback identities. Music DNA remains Profile-owned, opt-in and outside the projection. Projection data is never persisted and no raw identifier is included in a DJ Moment or Broadcast event. Runtime communicates only with the Observation Boundary and never depends directly on the Playback Control Boundary.

## Future startup flow

```text
Continue request
  → resolve Profile, backend, Mood and Persona independently
  → read one CurrentPlaybackProjection
  → ACTIVE validation
  → create the ephemeral Runtime
  → record Session Start and adopt the current item once
  → initialize fresh runtime-scoped Performance Memory from those contributions
  → invoke the existing Track Started intelligence path once
  → observe later real Track Started events normally
```

The Runtime becomes `ACTIVE` only after the projection has been validated and the startup contribution has been adopted. A Session Start records no pre-session history. The adopted item uses the existing Track Started path; no parallel enrichment or DJ Moment pipeline is permitted. The Music Backend is not paused, resumed, seeked, restarted or otherwise mutated.

For `NO_ACTIVE_PLAYBACK`, orchestration returns the typed `continue_playback_unavailable` result, creates no Runtime and does not fall back to Manual or Discover. For `UNAVAILABLE` or `UNSUPPORTED`, it returns a distinct typed backend-observation failure, likewise without a Runtime or playback mutation. Client presentation of these results is future renderer work.

## Identity, deduplication and races

Deduplication is Runtime-scoped and non-persistent. The bootstrap key is the
Observation Boundary-owned `playback_item_identity` only; `track_identity`, title, artist,
album, URI, artwork, timestamps and progress are never identity fallbacks. It
suppresses only a duplicate Track Started delivery for the adopted active
playback instance.

- A later replay is eligible after the Observation Boundary reports a distinct Playback Instance Identity.
- A real Track Started event for the same bootstrap identity is consumed by the established path without adding a second Flow contribution or Moment.
- A changed identity during resolution invalidates the snapshot; orchestration does not reread, guess or adopt a replacement item in the same start attempt.
- Duplicate start requests remain subject to the existing one-active-Runtime rule; only one request can adopt an item.
- The bootstrap key is discarded when the Runtime ends, or when the Backend reports a distinct real Track Started item. No durable event sourcing is introduced.

If playback stops, becomes stale or loses required active identity before Runtime activation, the result is `continue_playback_unavailable` and no Runtime is created. If Runtime creation succeeds but startup adoption cannot complete, orchestration rolls the new Runtime back before reporting failure. If adoption succeeds and later intelligence generation fails, existing safe Track Started failure behaviour applies; no fabricated Silence hides a bootstrap failure, and no adopted item is duplicated.

Incomplete optional metadata does not invalidate an otherwise active, identified projection. It may lead the existing intelligence path to its existing safe result. Provider retries, reconnects and output transfers do not produce an additional adoption unless they carry a distinct Playback Instance Identity.

## Authorized future implementation slice

The next production PR may implement exactly:

1. the tagged `CurrentPlaybackProjection` and Observation Boundary-owned Playback Instance Identity at the existing Music Backend use-case boundary;
2. normalized Track Started events carrying the same identity;
3. adapter mappings for one safe active item, without exposing raw payloads;
4. one Continue startup read and validation;
5. one adopted startup item using the existing Track Started path;
6. Runtime-scoped bootstrap deduplication; and
7. typed active, no-active-playback, unavailable and unsupported outcomes with focused unit, integration and end-to-end tests.

It must update the authorized maturity step to current. It must not add queue access, future-track inspection, playback mutation, Session restoration, persistent state, a new DJMoment type, renderer behaviour or a second public playback abstraction.

## Deferred work

Runtime-generated, heuristic, URI-based, metadata-derived and timestamp-based
identity; queue snapshots, ordering and mutation; playlist or album ownership;
future-track awareness; playback history; multi-track planning; continuous or
autonomous replanning; persistent Playback Instance Identity or Performance
Memory; multi-device and cross-device continuity; audience adaptation; external
knowledge; Concert, History and Discovery Moments; and renderer-specific
continuity behaviour remain deferred.
