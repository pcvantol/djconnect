# Live Playback Observation

**Status:** Authorized architecture amendment; Stage 1 implementation planned
**Owner:** DJConnect Product Development
**Scope:** Provider-neutral observation of ordinary media changes while an active DJ Session exists. This document authorizes no production code, API, storage, renderer or Continue Stage 2 implementation.

## Purpose

An active DJ Session must remain responsive when playback changes outside DJConnect. A listener can skip in Spotify, allow a playlist to advance, select another item from another Spotify Connect client, or change current media through Music Assistant or Home Assistant. Playback remains owned by the Music Backend; DJConnect observes a safe bounded result only to host the active Session around what is playing.

This contract defines a deliberately limited Stage 1 before the strict occurrence-correct contract required by Continue Stage 2. It does not weaken [`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md) or ADR-0016.

## Maturity progression

| Stage | Contract | Status |
| --- | --- | --- |
| 0 | No generic production path observes external playback changes during an active Session. | current |
| 1 | An active Session observes a change from one safe Media Identity to another, then reuses the established Track Started intelligence pipeline. It is useful for ordinary skips, external selection and playlist/album progression, but has deliberately limited replay guarantees. | planned |
| 2 | The Observation Boundary supplies Playback Instance Identity and correlated live `TrackStartedObservation` events. Runtime distinguishes duplicate delivery from a legitimate replay and supports Continue Stage 2 bootstrap correlation. | authorized, deferred |

Stage 1 is **not** occurrence-correct. Stage 2 remains separate and requires every strict prerequisite in the Continue contract.

## Terms and boundaries

| Term | Meaning |
| --- | --- |
| Media Identity | A safe, adapter-normalized reference for one playable media entity. It identifies media, not one playback occurrence. It is Runtime-internal and is never raw provider payload or public renderer data. |
| Playback Instance Identity | The opaque identifier for one concrete playback occurrence defined by ADR-0016. It is not Media Identity and is required only by Stage 2. |
| Media-change observation | A bounded Observation Boundary result containing playback state, a safe Media Identity when available and safe existing metadata. It is not a provider callback exposed to Runtime. |
| Stage 1 Track Started input | The eligible, normalized media-change result accepted by Runtime after a Media Identity comparison. It invokes the existing Track Started processing path; it is not the occurrence-correct `TrackStartedObservation` reserved for Stage 2. |

Media Identity may use an existing canonical provider media reference only after adapter normalization. It must not be derived from title, artist, album, artwork or other display metadata. Raw provider payloads, credentials, queue contents, future tracks, Music DNA and playback history never cross into Runtime, Session Flow, DJ Moments or Broadcast.

## Stage 1 semantics

While an eligible DJ Session is active, the Playback Observation Boundary may accept a new Track Started input only when one of these conditions holds:

- the observed playable Media Identity differs from the last accepted active Media Identity;
- playback becomes active with a valid Media Identity that the Runtime has not accepted for that active Session; or
- an adapter-normalized backend event supplies an equally safe media-change signal.

The initial observation when an observer attaches is a baseline, not a second Track Started input. This prevents the Session Start path from duplicating its initial contribution. A change observed before that baseline is established may be missed; Stage 1 makes no lossless-delivery claim.

```text
Active DJ Session
  → Playback Observation Boundary samples or receives current playback state
  → adapter normalizes playback state and safe Media Identity
  → Runtime compares it with its runtime-scoped last accepted Media Identity
  → eligible changed identity invokes existing Track Started processing
  → existing Track Insight → Planner → Knowledge Engine → DJ Moment Engine
  → Session Flow → Broadcast
```

There is no second enrichment, intelligence, Session Flow or Broadcast pipeline. Track Insight remains optional post-acceptance enrichment; missing or partial enrichment does not change observation correctness and follows the existing safe downstream behaviour.

## Strategy independence and ownership

Stage 1 runs for every active Session Start Strategy: Manual, Discover and the existing Continue Stage 1 empty-runtime fallback. Observation is not a Start Strategy. An external skip neither changes the active Strategy nor gives Runtime playback, queue or provider ownership.

| Owner | Responsibility | Never owns |
| --- | --- | --- |
| Music Backend Playback Control Boundary | Playback, queue, transport and all playback mutation. | Observation lifecycle, Runtime or identity comparison. |
| Music Backend Observation Boundary | Samples or receives provider state, normalizes safe Media Identity and playback state, reports observation capability, and emits bounded media-change observations. | Playback mutation, Session ownership, queue ownership or identity persistence. |
| Provider adapter | Contains provider-specific polling/event mechanics and raw payloads. | Runtime policy or public exposure of provider payloads. |
| Session Runtime | Starts/stops active-session observation, retains only the last accepted Media Identity and invokes the existing Track Started processing path. | Provider semantics, playback control, queue state or Playback Instance Identity derivation. |
| Planner | Responds to the canonical Track Started input. | Provider observation. |
| Session Flow and Broadcast | Record and distribute resulting immutable Moments through their existing path. | Raw observation state or provider payloads. |

The existing public playback-control capability map is unchanged. Observation capabilities are internal to the Observation Boundary and scoped to the selected backend implementation, authorized account and, where necessary, player/output.

## State, lifecycle and deduplication

Stage 1 retains only one last accepted active Media Identity per active Runtime. It is ephemeral, cleared when the Session ends and never persisted. It may suppress repeated polling or event delivery for that same identity.

| Observed condition | Stage 1 behaviour |
| --- | --- |
| No active playback | Do not emit Track Started; retain the last accepted identity. |
| Playback paused | Do not emit Track Started. |
| Resume with unchanged identity | Do not emit Track Started. |
| Media changes while paused | Do not emit until a different eligible Media Identity becomes active. |
| Playback stops | Do not synthesize Silence; retain the last accepted identity. |
| A different eligible identity becomes active | Emit one Stage 1 Track Started input and replace the last accepted identity only after acceptance. |
| Temporary backend unavailability | Do not clear the accepted identity, mutate playback or end the Runtime. Resume observation when the Boundary is available. |
| Output change | Do not emit solely for an output change. |
| Backend/account scope changes | Stop the affected observer and re-establish a baseline only after the Boundary can validate the newly selected scope; do not infer continuity. |
| Session ending | Cancel polling, unsubscribe events and discard pending observations without publishing a new Moment. |
| Observation during Session start | Serialize through Runtime; establish one baseline after activation and never duplicate the initial Session Start contribution. |

Stage 1 deliberately cannot distinguish duplicate delivery from an immediate replay of the same media, pause/resume from replay with unchanged identity, seek from replay, same-track restart, every reconnect or output-transfer case, or tracks that begin and end between observations. It must not use timestamps, progress, URI-plus-time or other occurrence heuristics to conceal these limits.

Media Identity deduplication is never used for Continue Stage 2 bootstrap or live-event correlation. Stage 2 remains identity-only according to the Playback Instance Identity contract.

## Sources, cadence and capability model

An adapter may use existing provider events when they are available or bounded polling when they are not. Runtime owns only the active-session lifecycle; each adapter owns its source, cadence, non-overlap guard, error handling and normalization. Observation starts only after Runtime activation and stops at Session end. It is not persistent monitoring and never mutates playback.

| Backend observation implementation | Stage 1 readiness | Source and cadence owned by adapter | Safe Media Identity |
| --- | --- | --- | --- |
| Spotify Direct | eligible | Poll the existing normalized current-playback status at a bounded active-session cadence of no more than once every 15 seconds, with no overlapping requests. | Existing non-empty normalized Spotify playable URI. |
| Music Assistant | conditionally eligible | Subscribe to the configured Home Assistant `media_player` state changes for the active Session; no Runtime polling loop. The adapter may use an adapter-owned bounded reconciliation only if a later contract defines it. | Existing non-empty `media_content_id`, normalized with its media type and selected player scope. |

Music Assistant does not claim Stage 1 support when its configured player omits a safe media reference. In that state it reports observation unavailable rather than deriving an identity from display metadata. Neither backend qualifies for Stage 2 from these Stage 1 paths.

The Observation Boundary exposes only the following internal capability fields:

| Capability | Meaning |
| --- | --- |
| `supports_current_playback_status` | Can safely obtain bounded current playback state for the selected scope. |
| `supports_media_change_observation` | Can produce a safe Stage 1 media-change observation. |
| `observation_mode_event` | Uses a normalized provider/HA event source. |
| `observation_mode_polling` | Uses bounded adapter-owned polling. |
| `supports_occurrence_identity` | Can satisfy the strict Playback Instance Identity contract. |
| `supports_continue_stage2` | Can satisfy every Continue Stage 2 projection, identity and correlation rule. |

A backend may support Stage 1 while reporting both Stage 2 fields as false. No field grants backend-wide support beyond its selected observation scope.

## Smallest future production slice

One production increment may advance **Playback Observation Stage 1** from planned to current. It may implement Spotify Direct polling and the Music Assistant state-change adapter only where their readiness conditions above are met. It must contain:

1. an active-session Observation Boundary lifecycle for Manual, Discover and Continue Stage 1;
2. adapter-owned safe Media Identity normalization and capability reporting;
3. bounded, non-overlapping Spotify polling and Music Assistant event subscription with cancellation at Session end;
4. one runtime-scoped last-accepted Media Identity and serialized baseline/change handling;
5. one eligible-change invocation of the existing Track Insight and Track Started intelligence path;
6. safe temporary-unavailability handling without playback mutation; and
7. maturity evidence and focused tests.

It must not add Continue Stage 2 adoption, Playback Instance Identity, queue or future-track awareness, a new Start Strategy, persistent observation history, cross-device continuity, autonomous replanning or a second pipeline.

Required tests cover external skip, natural progression, external selection, repeated delivery, pause/resume, stop then a different track, temporary unavailability, Session-end cancellation, all three active Strategies, reuse of Track Insight/Planner/Knowledge/Moment/Flow/Broadcast, absence of playback mutation and the documented unsupported same-track replay case.

## Deferred

- occurrence-correct same-track replay and duplicate-delivery distinction;
- Playback Instance Identity and Continue Stage 2 bootstrap correlation;
- complete queue observation, future-track awareness and queue mutation;
- persistent observation history and cross-device continuity; and
- autonomous replanning.

## Related documents

- [`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md)
- [`DJ_INTELLIGENCE_ARCHITECTURE.md`](DJ_INTELLIGENCE_ARCHITECTURE.md)
- [`DJ_INTELLIGENCE_MATURITY.md`](DJ_INTELLIGENCE_MATURITY.md)
- [`../adr/0016-playback-instance-identity-observation-boundary.md`](../adr/0016-playback-instance-identity-observation-boundary.md)
- [`../../DJ_SESSION_RUNTIME_CONTRACTS.md`](../../DJ_SESSION_RUNTIME_CONTRACTS.md)
