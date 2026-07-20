# DJ Moment Engine

## Status

`CONFIRMED_CODE` — first bounded production slice.

## Production pipeline

```text
Active Session Runtime
  → Planner Event (track_available)
  → Knowledge Intent (track_context)
  → runtime-scoped Knowledge Engine
  → validated Knowledge Context
  → DJ Moment Engine
  → frozen DJ Moment
  → Session Flow
  → Broadcast State and dj_moment_published event
  → authenticated owner and constrained Broadcast Token consumers
```

The Runtime is the only entry point and owns its Planner, Knowledge Engine and
Moment Engine for its lifetime. There is no client endpoint or generic AI
endpoint for either intelligence service.

A future normalized Track Started observation carries the opaque Playback
Instance Identity owned by the Music Backend Observation Boundary. Runtime may
compare that identity only for runtime-scoped deduplication; it never derives it
from track metadata or exposes it in Moments or Broadcast. The Continue
continuity contract defines this future production boundary in
[`../product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](../product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).

## Implemented slice

At session start, the Runtime submits one deterministic `track_available`
Planner Event. The Planner requests `track_context`; the Runtime asks its
Knowledge Engine to assemble validated track and analysis context, then asks
its Moment Engine to create one Track Moment or record explicit Silence. A
Track Moment cannot be generated twice for the same title/artist/album identity
within one Runtime.

That current metadata-based Moment guard is not Playback Instance Identity and
must not be used for Continue occurrence correlation. A future Continue Stage
2 slice uses only the opaque identity supplied in a canonical live observation;
it must preserve legitimate replay semantics even when media metadata matches.

Every published Moment is a frozen dataclass containing its Knowledge Intent,
Presentation Intent, semantic actions and safe source references. Mood and
Persona are copied into Presentation Intent at creation. Later Runtime Mood or
Persona changes affect only future Moments.

The first Personas are `home_dj`, `radio_dj`, `club_dj` and `festival_dj`.
They are behavioural prompt guidance, never voice-provider settings.

## Reuse assessment

| Classification | Existing building block | Use in this slice |
| --- | --- | --- |
| KEEP | `TrackInsightService` | Current-track resolution, artist/genre enrichment, HA Conversation execution, response parsing and fallback. |
| REFACTOR | Runtime orchestration | The Runtime now owns the Planner → Knowledge Engine → Moment Engine transition; API handlers only begin the active Session trigger. |
| KEEP | Knowledge privacy filtering | Knowledge Context contains only validated music context and excludes raw Music DNA, Profile preferences and conversation data. |
| KEEP | Track Insight cache and validation | The provider returns the existing normalized track/analysis contract. |
| REFACTOR | `TrackInsightPromptBuilder` | Accepts optional semantic presentation guidance for Persona and Mood; no renderer instruction is added. |
| KEEP | Broadcast authorization | Owner device/Profile authorization and Broadcast Token runtime isolation remain unchanged. |
| KEEP | Music DNA privacy boundary | Music DNA is not passed to shared Moment generation or Broadcast projections. |
| DEFER | Ask DJ chat ownership | No interactive chat turn, history or generic Ask DJ endpoint is used by the Engine. |
| DEFER | Discover, recommendations, lyrics, concert and audience generation | Represented by the architecture only; no production generation is included. |

## Privacy and projection

Track Context is `session_shared` only because it uses safe music metadata and
Track Insight output. The engine does not include raw prompts, Music DNA,
Profile preferences, conversation history or secrets in a Moment's generation
metadata. `owner_only` Moments are filtered from Broadcast Token snapshots and
incremental events. Silence remains in the internal Session Flow and is not
published as a visual Moment event.

## Failure behaviour

Track Insight failures, timeouts or malformed output cannot fail a Runtime or
interrupt playback. The Engine records a bounded Silence Moment instead. It
does not retry indefinitely and never publishes a partial Moment.

## Intentionally not implemented

- continuous or fifteen-minute autonomous planning;
- periodic generation or concurrent generation loops;
- playback selection, mood mutation or audience-driven replanning;
- Voice, VibeCast or renderer presentation work;
- Follow-up action execution;
- personal Music DNA wording in shared or Broadcast-token output.
