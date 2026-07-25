# Playback Observation & Adaptive Planning Reconciliation

**Status:** Assessment complete; no implementation authorization.

| Definition | Owner/maturity | Planner, Flow and Broadcast relationship | Classification |
| --- | --- | --- | --- |
| Playback, queue and transport | Music Backend; external | DJConnect observes only; never mutates or orders playback | fully fitting |
| Manual, Continue and Discover | Session Runtime strategies | Start a Session around playback; do not own it | fully fitting |
| Live Playback Observation Stage 1 | Observation Boundary; Spotify Direct current | changed safe Media Identity reuses the one Runtime → Planner → Knowledge → Moment → Flow → Broadcast path | fully fitting |
| Planner Horizon | Planner; architecture/current bounded foundations | semantic, ephemeral and never provider queue; future slots may be superseded without rewriting realized Flow | fully fitting |
| Playback Reality and invalidation | Runtime/Planner architecture | material external playback change invalidates unrealized horizon, triggers safe observation and replanning | partially explicit |
| Continue Stage 2 | deferred external dependency | strict occurrence identity would correlate adoption and Track Started; no Flow/Broadcast identity exposure | externally blocked |

Listeners may freely skip, replace playlists/albums, choose tracks or switch
backends during an active DJ Session. The Music Backend remains authoritative;
DJConnect adapts to observed playback reality. Material change discards only
unrealized semantic Horizon slots, then re-observes and replans. The active
Runtime, realized Session Flow and applicable Runtime-scoped Performance Memory
remain intact. Uncertainty results in replanning or existing Silence, never a
pseudo occurrence identity or heuristic continuity claim.

Continue Stage 2 is not a practical next increment: Spotify and Music Assistant
do not currently provide the required backend-owned Playback Instance Identity.
ADR-0016 remains historical architectural authority. Future work may only adopt
current playback conservatively from safe Media Identity without occurrence
claims, or remain unavailable; it must not derive URI-plus-time, progress or
other pseudo-identifiers.

No Runtime, Planner, provider, Session Flow, Broadcast, API or playback-control
behavior changes in this assessment.
