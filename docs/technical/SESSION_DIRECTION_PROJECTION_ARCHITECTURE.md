# Session Direction Projection Architecture

**Status:** Selected bounded implementation under DJC-CORE-SESSION-FORECAST-V1-20261012;
local qualification in progress, protected delivery pending.

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

## Session Forecast v1 refinement

[Canonical Forecast contract](../product/SESSION_FORECAST_V1.md) implements the
small mutable projection with ordinary paired owner-read and additive Broadcast
state/update, not a new Horizon or Moment. Planner semantics are allowlisted and
realized by existing authored presentation ownership for four Personas/five locales.
Nominal external900s is conditional intent coverage; current Runtime15-minute
foundation and future internal20-minute target are unchanged. Artist imagery has
separate exact subject/role/source/usage/expiry/audience qualification; private
Discovery grants and unknown future media never leave Core. Reads are pure and
expiry/authority/end remove content. Current Core, native view, shared compatibility,
visible ambient adoption and joint acceptance retain separate qualification.
Earlier future-design wording above is the preserved pre-implementation baseline.


### Observed queue as bounded narrative context

The 22 October 2026 DJ-bulletin increment enriches existing Forecast prose with
an admitted observed contiguous queue prefix (max five, original thirty-second
expiry), owned by the music backend. It does not export a provider queue,
advance Planner slots, promise order or qualify upcoming imagery/actions. The
original design's prohibition on represented predicted tracks remains; the
explicit extension is factual, conditional narrative context only. See
`docs/product/SESSION_FORECAST_V1.md` for admission, expiry and privacy bounds.
