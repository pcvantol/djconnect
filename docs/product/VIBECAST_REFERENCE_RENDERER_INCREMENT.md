# VibeCast Reference Renderer Increment

**Status:** First slice complete under the owner's simulator acceptance override:
`SIMULATOR_QUAL=PASS`, `PHYSICAL_PI_QUAL=NOT_RERUN_BY_USER_OVERRIDE`.
The separately selected [same-track Moment timeline](VIBECAST_MULTIMOMENT_TIMELINE_CONTRACT.md)
is protected merged in Core [PR #1118](https://github.com/pcvantol/djconnect/pull/1118) with software/browser simulator acceptance. Its `PHYSICAL_PI_QUAL=NOT_RUN_FOR_THIS_SLICE`; the first slice's override and installed evidence do not transfer.

## Iteration 1 evidence

The first ambient renderer foundation is implemented as a separate, no-store
`/djconnect/vibecast` page. It reuses only the existing session-scoped Receiver
Broadcast WebSocket and keeps its projection in memory. The portrait 1200x1920
Pi is the live reference host; it renders a full-screen idle state and is
prepared for snapshot-first playback, artwork, mood and current-DJMoment
presentation. The same page includes a landscape composition for later Cast
feasibility work.

An earlier local candidate on the physical portrait Pi proved owner approval,
an active Broadcast snapshot, WebSocket reconnect, Runtime-end to Idle and no
durable browser token. That candidate was not bound to the final Apple/Core
merge SHAs. It did not show a non-terminal playback, DJMoment or Session Flow
update while the same Session stayed active. The Pi keeps no controls or
personal Profile projection.

The supported HA options-to-Profile backend binding was corrected by Core
[PR #1110](https://github.com/pcvantol/djconnect/pull/1110). Core
[PR #1114](https://github.com/pcvantol/djconnect/pull/1114) then preserved the
eligible Spotify observer across a config-entry reload. Core
[PR #1116](https://github.com/pcvantol/djconnect/pull/1116), protected merged as
`a187f7c6f7f91f4d5c25ff685323e528ba97449c`, now prevents slow or superseded
Track Insight work from publishing a stale title or narrative, correlates
renderer Moments with the current playback item, and resolves Session locale
from the explicit client request or selected Assist pipeline within the
canonical five-language contract.

The owner subsequently accepted the exact Core and Apple candidates through
the paired iPhone simulator, HA-dev, real Spotify Direct playback and the
portrait receiver. The same active Session showed a Dutch non-terminal track
update, reconnect and Runtime-end cleanup. The [closure receipt](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6010273964)
records `FIRST_SLICE=COMPLETE` and explicitly replaces the remaining physical
Pi run with simulator acceptance; it does not claim a new hardware result.
This increment starts no Cast follow-on.

## Outcome

Deliver one ambient-first VibeCast web renderer that consumes only the existing
renderer-safe Broadcast projection. The 10-inch portrait Raspberry Pi is the
first real-hardware reference host. A future Google Cast Custom Web Receiver
uses the same renderer and data model in a landscape television composition.

The Apple client remains the paired Session owner and sender. It initiates a
bounded, ephemeral Receiver handoff; it never streams or mirrors pixels.

## Portrait Pi owner handoff candidate

The first reference host can remain a browser Receiver even when its separate
native Pi client is not paired. Loading `/djconnect/vibecast` without Session
credentials creates a five-minute, memory-only claim. The Pi displays its
six-digit code; its browser alone keeps a distinct, high-entropy claim secret.
The paired Apple owner enters the displayed code from the active Session view.
Home Assistant authenticates that owner against the exact active Session and
binds the existing Runtime-scoped Broadcast Token to the claim. Only the same
browser secret can collect it, once. The browser then uses the existing
snapshot-first Broadcast WebSocket and keeps the Session ID and Token in memory.

Session start, active lookup and end, as well as the owner Broadcast Token and
handoff approval routes, require the authenticated device's server-side
Profile binding. An explicit Profile hint from a client cannot select another
owner's Session. A paired but not yet Profile-mapped client fails closed until
the existing Profile Platform maps it; installed Apple-owner mapping must be
confirmed during live acceptance. Apple's active-Session GET includes its
identified device and client type so reconnect can use this boundary.

The short code is a visual confirmation, not an authentication credential.
Claims are capacity-bounded, expire after five minutes, and never persist to
Home Assistant Store, browser storage, Pi configuration or Apple client state.
Approval returns no Broadcast Token to Apple. The receiver page and claim
responses use `no-store`; Runtime end invalidates the token. A refresh starts
a new claim. This control-plane handoff does not create a second Broadcast
data path or give the Pi owner controls.

The first-slice product acceptance is recorded in the closure receipt above.
The physical portrait Pi evidence remains the earlier subset, and later Cast
work remains separately gated.

```text
paired Apple sender
  -> ephemeral, session-scoped VibeCast handoff
  -> Universal Receiver Web Platform
  -> renderer-safe Broadcast snapshot + updates
  -> VibeCast web renderer
       -> portrait Pi reference host
       -> later landscape Google Cast Custom Web Receiver
```

## Scope

1. **Reference-host pre-flight**
   - prove the existing Receiver handoff, token lifetime, Runtime-end and
     reconnect boundaries on the Pi;
   - identify the smallest Apple-owner-to-reference-host handoff that never
     persists a Broadcast Token on the Pi; and
   - retain the existing paired-owner, session-scoped authorization model.
2. **Ambient renderer foundation**
   - reuse Universal Receiver connection, snapshot-first and incremental
     Broadcast handling;
   - keep only temporary renderer state; and
   - introduce no Runtime, Planner, Knowledge, DJMoment or parallel transport
     ownership.
3. **Adaptive ambient composition**
   - portrait layout for the 1200x1920 wall-panel reference host;
   - landscape layout for the future Cast television host;
   - renderer-safe artwork, track/artist identity, server-owned progress and
     one current eligible DJMoment; and
   - mood-led atmosphere, slow restrained motion and a graceful idle/Silence
     state.
4. **Reference validation**
   - Apple Simulator starts the owner-side handoff;
   - the Pi renders a live active Session and returns to idle after Runtime
     end; and
   - visual, reconnect and privacy checks confirm that no personal Profile
     data, controls or durable Broadcast Token reach the renderer.
5. **Cast feasibility follow-on**
   - validate the same web renderer on Google Cast Custom Web Receiver;
   - prove receiver launch/join, session handoff, idle and reconnect behavior;
     and
   - keep Cast work separate from native Google TV or pixel-streaming work.

## Explicit non-goals

- music playback, video streaming, AirPlay mirroring or sender pixel output;
- a second Broadcast, VibeCast feed, Session Runtime or planning pipeline;
- Profile, Music DNA, Ask DJ history, queue, settings, diagnostics or
  application navigation on the ambient renderer;
- beat detection, FFT/audio analysis, local intelligence or local generation;
- Google Cast production distribution before the Pi reference-host evidence is
  complete; and
- turning the interactive Universal Receiver shell into VibeCast by merely
  hiding controls.

## Exit criteria

The first increment is complete at the owner's simulator acceptance level.
Physical Pi qualification and Cast implementation planning require their own
future selection and evidence. The renderer contract remains reusable in
landscape without a different server contract.

## References

- [VibeCast Architecture](VIBECAST_ARCHITECTURE.md)
- [Universal Receiver Architecture](../technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Renderer Experience Roadmap](RENDERER_EXPERIENCE_ROADMAP.md)
