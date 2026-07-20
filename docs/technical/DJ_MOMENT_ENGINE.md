# DJ Moment Engine

## Status

`CONFIRMED_CODE` — first bounded production slice.

## Production pipeline

```text
Active Session Runtime
  → Planner Event (track_available)
  → Knowledge Intent (track_context)
  → DJ Moment Engine
  → frozen DJ Moment
  → Session Flow
  → Broadcast State and dj_moment_published event
  → authenticated owner and constrained Broadcast Token consumers
```

The Runtime is the only entry point. There is no client endpoint or generic
AI endpoint for the Moment Engine.

## Implemented slice

At session start, the Runtime submits one deterministic `track_available`
Planner Event. The Planner requests `track_context`; the Engine either creates
one Track Moment for the resolved current track or records an explicit Silence
Moment. A Track Moment cannot be generated twice for the same title/artist/
album identity within one Runtime.

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
