# Rolling Session Horizon Architecture

**Status:** Accepted architecture amendment
**Owner:** DJConnect Product Development
**Scope:** Runtime-scoped experience planning and future sequencing. No Planner,
provider, queue, persistence, transport or renderer implementation is added.

## Decision

A **Rolling Session Horizon** is the Session Planner's one ephemeral planning
object for the upcoming DJ experience. It is Profile-scoped through its active
Session Runtime, is created and destroyed with the Planner, and is never a
provider queue, persisted Session state, serialized Session Flow or renderer
projection.

```text
Profile + persistent Session context + ephemeral Runtime
  + Current Playback + Upcoming Playback Projection
  + Strategy + Mood + Direction + approved feedback
  + Performance Memory + Knowledge confidence
  -> Session Planner -> Rolling Session Horizon
  -> approved Knowledge Intents -> Knowledge Engine -> DJ Moment Engine
  -> immutable DJMoments
```

The default product target is approximately **twenty minutes** of observable
experience context. It is a policy target, not a queue reservation, provider
command or promise that twenty minutes of tracks are available. Only a future
Planner policy may configure it; clients, providers and renderers never do.

## Ownership and lifetime

| Owner | Owns | Never owns |
| --- | --- | --- |
| Observation Boundary | Current Playback and safe Upcoming Playback Projection. | Queue mutation, Planner policy or Session identity. |
| Session Runtime | Bounded projection adoption and routing permitted changes to Planner. | Future playback, queue execution or persistent horizon state. |
| Session Planner | Horizon construction, deterministic replanning, intent approval and invalidation. | Queue control, generated wording or persistence. |
| Knowledge Engine | Cancellable safe preparation for an approved knowledge-dependent candidate. | Scheduling or timing decisions. |
| DJ Moment Engine | One immutable Moment after a current intent is realized. | Horizon contents or future approval. |
| Session Flow | Realized contributions and their ordering. | Speculative slots or provider state. |
| Broadcast / Renderers | Published safe Moments and projections. | Horizon inspection or mutation. |

Runtime end, integration unload and Home Assistant restart discard the horizon.
A future safely re-bootstrapped Session builds a new horizon from fresh
projections; it never deserializes Planner state, Performance Memory, prefetch
work or an earlier object graph.

## Upcoming Playback Projection

The provider-neutral **Upcoming Playback Projection** is optional and
immutable. It may contain only a bounded ordered list of safely observable
upcoming playable references, safe estimated relative durations and a
freshness/confidence marker. It never contains raw provider data, credentials,
queue-control tokens, Playback Instance Identity, listener identity or a
fabricated item.

When it exposes less than twenty minutes, the Planner plans only that window.
When it is unavailable, stale, invalid or low confidence, the Planner does not
query or control a queue: it uses a current-track-safe, Silence-capable plan.
Stage 1 observation stays current-track-only; this amendment requires neither
Playback Observation Stage 2 nor Music Assistant work.

## Minimal representation and realization

The Horizon holds bounded ordered **experience slots**, not DJMoments. A slot
has a runtime-local identifier, relative window, optional safe expected playback
reference, candidate or approved semantic intent (or reserved Silence), bounded
narrative purpose/priority, required knowledge category/confidence and one
status: `candidate`, `approved`, `superseded` or `consumed`. A superseded
slot may retain only a bounded invalidation reason.

Slots contain no generated content, Presentation Intent, raw metadata or
pre-created Moment. `approved` is Planner approval only. `consumed` occurs
only when the existing realization path records a Moment or intentional Silence
in Session Flow.

## Replanning, confidence and stability

The Planner rebuilds or partially invalidates only from normalized Runtime
inputs: accepted playback projection change, rolling-window advance,
Strategy/Mood/Direction change, approved Session feedback, safe Knowledge
confidence change or Planner tick. Audience Events and Audience Projections are
not Planner inputs; a future coarse Audience Observation requires its own
explicit decision. It is
debounced and deterministic for an identical input snapshot.

A policy-defined stability window protects near-term approved commitments.
Invalid playback context, explicit privacy/safety invalidation or a high-priority
approved Direction change may supersede them; later slots are otherwise rebuilt
partially. Strategy or incompatible Direction change may rebuild completely.
Realized Session Flow and published DJMoments are never rewritten. Removing,
reordering or invalidating an expected reference affects only matching future
slots and emits no Moment by itself.

Knowledge confidence constrains a slot; it never fabricates a story. The
Knowledge Engine may prepare safe context shortly before an approved target,
but cancels it on supersession, Session end or confidence loss. Caches and
prepared context are Runtime-scoped. Full lyrics, raw provider responses and
copyright-restricted content are never persisted as Session state.

## Dynamic influences and Audience Experience

Strategy, current Mood, Persona and Direction influence only future priority
and pacing. Performance Memory is Runtime-scoped realized history used to avoid
repetition. Persistent history supplies only authorized durable outcomes.
Durable Profile likes/dislikes and bounded Session feedback are distinct: a
like, dislike or approved skip may trigger future partial replanning and later
separate Music DNA learning, but cannot change playback, historic Flow or a
published Moment.

Audience Experience is a separate, privacy-bounded participant presentation
concern. Its Audience Events and Audience Projections are never raw Home
Assistant entities, provider commands, renderer mutations or Planner inputs.
A future coarse Audience Observation would need a separate privacy,
aggregation, confidence and Planner-influence decision; it is not authorized by
this Horizon architecture. Household visibility must not expose personal Music
DNA, preference, conversation, raw sensor data or participant identity.

The current Universal Receiver audience-signal capability is declarative only;
its documentation and implementation must reconcile before interaction expands.

## Persistence, transport and privacy

Horizon slots, status, invalidation, confidence and prefetch work are ephemeral.
Persistent Session history retains only lifecycle outcomes and authorized,
immutable historical DJMoment projections that actually occurred. HTTP,
WebSocket, Broadcast and Renderer Hosts never receive the complete Horizon. A
diagnostic projection would require a separate privacy and transport decision.

## Bounded implementation roadmap

1. Rolling Horizon domain model and invalidation vocabulary; no provider input.
2. Provider-neutral Upcoming Playback Projection with safe degradation.
3. Deterministic approximately twenty-minute planning window; no queue control.
4. Debounced invalidation, stability window and partial rebuild.
5. Mood and Direction future-slot adaptation.
6. Session feedback adaptation for likes, dislikes and approved skips.
7. Reconcile Universal Receiver drift, then separately assess coarse Audience
   Observation only after Audience Experience and privacy prerequisites.
8. Cancellable Runtime-scoped Knowledge prefetch.
9. Separate copyright-safe Lyrics Knowledge capability.
10. Narrative sequencing, callbacks, opening, pacing and closing.
11. Discover/recommendation expansion, then audience-adaptive intelligence and
    stable native renderer adoption.

No Audience Experience capability is a Horizon or Planner cell. A future coarse
Audience Observation may be assessed only after separate privacy, aggregation
and artistic-autonomy evidence; it is not implied by this architecture.

## Explicit non-goals

No horizon implementation, Planner change, queue control, playback action,
Lyrics retrieval, sensor adapter, feedback persistence, DJMoment type, schema,
endpoint, renderer work, Music Assistant, Playback Observation Stage 2 or
Continue Stage 2 is added.

## Related records

- [DJ Session Runtime Contracts](DJ_SESSION_RUNTIME_CONTRACTS.md)
- [DJConnect v4 Architecture](DJCONNECT_V4_ARCHITECTURE.md)
- [DJ Intelligence Architecture](docs/product/DJ_INTELLIGENCE_ARCHITECTURE.md)
- [DJ Intelligence Maturity](docs/product/DJ_INTELLIGENCE_MATURITY.md)
- [Live Playback Observation](docs/product/LIVE_PLAYBACK_OBSERVATION.md)
