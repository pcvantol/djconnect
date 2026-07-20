# ADR-0016: Playback Instance Identity belongs to the Music Backend Observation Boundary

## Status

Accepted

## Date

2026-07-20

## Context

Continue Current Playback Continuity may create a new DJ Session around one
item that is already playing. To prevent duplicate adoption while allowing a
real replay of the same track, Runtime needs one stable identity for that
specific playback occurrence. The identity must be supplied both with the
current-playback observation and its corresponding normalized Track Started
observation.

The Runtime cannot safely derive that identity from a URI, metadata, position,
timestamp or provider payload. Those values do not distinguish every genuine
replay from duplicate delivery and would leak provider behaviour into the
Session Runtime.

## Decision

Playback Instance Identity is owned by the **Music Backend Observation
Boundary**. It is an opaque, canonical, provider-neutral value at the Runtime
boundary.

Provider adapters implement the Music Backend Observation Boundary. They
normalize provider observations, determine whether a concrete playback
occurrence can be identified reliably, and expose the same identity in both a
`CurrentPlaybackProjection` and its normalized Track Started observation.

The Music Backend has two distinct responsibilities:

| Boundary | Owns |
| --- | --- |
| Playback Control Boundary | Playback, queue, transport and playback commands. |
| Playback Observation Boundary | Playback observation, `CurrentPlaybackProjection`, Track Started observation, Playback Instance Identity and provider normalization. |

Runtime communicates only with the Playback Observation Boundary for Continue
bootstrap. It consumes the identity only as an opaque Runtime input; it never
derives, interprets, generates or persists one. Runtime does not depend
directly on Playback Control.

### Lifetime and privacy

Playback Instance Identity exists only while its concrete playback occurrence
exists. It is immutable, ephemeral, Runtime-internal and discarded when that
occurrence ends or the Runtime ends. It is never persisted.

It must never be written to Session Flow, Performance Memory, Music DNA,
Profile state, persistence, Broadcast, public APIs, immutable DJ Moments or
reconstruction logs. It crosses an ownership boundary only as the opaque input
from the Observation Boundary to Runtime.

### Capability model

The Observation Boundary determines its own support; it is not a global
backend-wide assumption. A concrete observation implementation exposes these
capabilities:

- `supports_current_playback_projection`;
- `supports_playback_instance_identity`;
- `supports_live_track_started_events`; and
- `supports_continue_stage2`.

Continue Stage 2 is enabled only when all required observation capabilities
are available. `supports_continue_stage2` represents that complete capability
set for the selected observation implementation; it does not grant control,
queue or persistence capabilities.

### Unsupported observations

When the Observation Boundary cannot reliably satisfy the Playback Instance
Identity contract, Continue Stage 2 is `UNSUPPORTED`. Runtime is not created;
it generates no heuristic or fallback identity and introduces no queue
ownership. Runtime must never compensate for a missing observation capability.

## Consequences

- Spotify, Music Assistant and future providers can implement their own
  observation mechanics without exposing provider-specific values to Runtime.
- A duplicate Track Started delivery can be suppressed by occurrence identity,
  while a legitimate replay is eligible only with a distinct identity.
- A provider that cannot make this distinction reliably remains unsupported for
  Continue Stage 2 rather than weakening the contract for every provider.
- Continue Stage 2 requires a narrow observation contract, not a new playback
  control API or a second Runtime orchestration path.

## Alternatives considered

### Runtime-owned identity

Rejected. Runtime cannot observe enough provider lifecycle information to
distinguish all duplicates from legitimate replays without heuristics.

### Playback Control Boundary-owned identity

Rejected. Control commands and queue ownership are unrelated to observing a
current occurrence and would make Continue depend on playback mutation.

### URI, metadata, timestamp or progress-derived identity

Rejected. None identifies a concrete occurrence reliably; each fails for
replays, reconnects or duplicate delivery.

### Persistent or cross-device identity

Deferred. Continue Stage 2 needs only an ephemeral occurrence identity.

## Deferred

- Runtime-generated, heuristic, URI-based, metadata-derived and timestamp-based identity;
- queue ownership and queue snapshots;
- future-track awareness and playback history;
- persistent Playback Instance Identity and persistent Performance Memory; and
- cross-device continuity.

## Related documents

- `docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`
- `docs/adr/0002-music-backends-are-adapters.md`
- `DJ_SESSION_RUNTIME_CONTRACTS.md`
- `docs/product/DJ_SESSION_DOMAIN_MODEL.md`
- `DJCONNECT_V4_ARCHITECTURE.md`
