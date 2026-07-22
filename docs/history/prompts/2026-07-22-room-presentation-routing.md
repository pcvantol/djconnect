# Prompt History: Room Presentation Routing

**Prompt ID:** Room Presentation Routing
**Generation:** V4
**Engineering program:** DJConnect Product Development
**Branch:** `codex/define-room-presentation-routing`
**Pull Request:** [#392](https://github.com/pcvantol/djconnect/pull/392)
**Merge Commit:** `d5ff9c9cb887a3e9f9b255d7315673c719c4ac48`
**Decision:** `MERGED_RECONCILED` after dedicated Finalization
**Execution date:** 2026-07-22

## Outcome

PR #392 establishes the canonical deferred Room Presentation Routing
architecture. The active playback output is the only future routing source: a
safe normalized target may resolve through the Home Assistant entity, Device
Registry and Area Registry to a Home Assistant Area. That Area may determine
eligible independent Visual and Audio Renderer Hosts for the same immutable
DJMoment.

Room Presentation Context is Runtime-scoped, ephemeral and destroyed with the
Session. It is not persistent Session or Profile state, a DJMoment field, a
provider payload or a Broadcast contract. Visual and Audio Renderer Hosts do
not communicate directly or become master renderers; their shared DJMoment
identity supports soft, rather than sample-accurate, synchronization.

If the Area cannot be reliably resolved, autonomous speech routing remains
disabled. Existing Visual Guest Renderers may continue their authorized
renderer-safe Broadcast presentation without inferring an Area. Output Target
Binding and Area Presentation Policy remain separately deferred,
installation-owned configuration concepts.

No production code, Runtime behavior, Playback Observation, Broadcast
projection, transport, Renderer Host implementation, TTS generation or
configuration UI was introduced.

## Validation

- `python3 -m unittest discover -s tests` — 1,360 passed, 7 skipped
- `ruff check custom_components/djconnect tests` — passed
- `git diff --check` — passed
- development-host verification — MATCH
- PR #392 merge and current-main containment — verified

## Deferred work

Room Presentation Context implementation, Output Target Binding, Area
Presentation Policy, Home Assistant Voice Satellite routing, Renderer
discovery, peer synchronization, TTS generation and configuration UI remain
separate bounded capabilities.
