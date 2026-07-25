# Session Direction Projection Architecture

**Status:** Future technical design; no implementation authorization.

## Reconciliation

The Session Planner already owns current musical direction, semantic intent and
future Horizon. DJMoments and Session Flow are immutable realized decisions.
Broadcast owns mutable snapshots for Renderer Hosts; the current renderer-safe
playback projection intentionally excludes Planner state. No existing projection
therefore exposes the desired live direction without either leaking the Horizon
or creating an unnecessary DJMoment.

| Concept | Owner/lifetime | Renderer-facing | Classification |
| --- | --- | --- | --- |
| Planner direction and Horizon | Planner; active Runtime; mutable | no | partially fitting |
| DJMoment / Session Update | Moment Engine / Flow; immutable | yes | orthogonal |
| Broadcast snapshot | Broadcast; active Runtime; mutable | yes | partially fitting |
| Session Direction Projection | Planner-produced, Runtime-owned; active Runtime only | future renderer-safe field | required extension |

## Contract

A future Session Direction Projection is a small mutable renderer-facing
projection for an active Session only. It expresses the Planner's current
semantic musical direction; it is neither a provider queue, future-track list,
Horizon inspection, playback control, DJMoment nor Session Flow item. It is
released when the Runtime ends, has no history and changes only when Planner
direction materially changes.

Planner remains the source. Runtime owns projection lifecycle and Broadcast may
distribute it only through the existing authoritative snapshot/update semantics.
Renderers display it without inference or persistence. A narrative-worthy
direction change remains a separately Planner-approved immutable Session Update
DJMoment in Session Flow; ordinary live projection changes create none.

Music Backends remain owners of playback, queue and transport. This projection
must never represent provider queue order or predicted tracks.

## Deferred implementation

Any implementation requires a dedicated Pre-Flight, schema/privacy contract,
Broadcast compatibility evidence, renderer assessment and focused validation.
This design changes no Runtime, Planner, DJMoment, Session Flow, Broadcast,
HTTP or WebSocket behavior.
