# VibeCast Reference Renderer Increment

**Status:** Selected first slice; Core and Apple owner-handoff source merged;
physical reference acceptance open.

## Iteration 1 evidence

The first ambient renderer foundation is implemented as a separate, no-store
`/djconnect/vibecast` page. It reuses only the existing session-scoped Receiver
Broadcast WebSocket and keeps its projection in memory. The portrait 1200x1920
Pi is the live reference host; it renders a full-screen idle state and is
prepared for snapshot-first playback, artwork, mood and current-DJMoment
presentation. The same page includes a landscape composition for later Cast
feasibility work.

This is not yet end-to-end reference validation: the newly merged Apple-owner
handoff has not been installed and observed with a paired Apple owner on the
physical Pi. Active-Session capture, reconnect evidence and Runtime-end
observation remain the acceptance work. The Pi does not persist a Broadcast
Token and the renderer contains no controls or personal projection.

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

The product candidate is not accepted merely because these routes and UI build.
Acceptance still requires the physical portrait Pi, a paired Apple owner and
an exact live receipt for approval, snapshot and updates, reconnect, Runtime
end, readability and absence of durable/private data. The later Cast sender
remains outside this increment until that receipt exists.

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

The increment is ready to advance to Cast implementation planning only when a
real owner-initiated Pi session has demonstrated snapshot-first rendering,
incremental updates, reconnect, Runtime-end cleanup, portrait readability and
token non-persistence. The resulting VibeCast composition must be reusable in
landscape without a different server contract.

## References

- [VibeCast Architecture](VIBECAST_ARCHITECTURE.md)
- [Universal Receiver Architecture](../technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Renderer Experience Roadmap](RENDERER_EXPERIENCE_ROADMAP.md)
