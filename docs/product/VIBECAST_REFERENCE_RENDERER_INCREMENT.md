# VibeCast Reference Renderer Increment

**Status:** Planned and selected for the next Reference Experience increment.

## Outcome

Deliver one ambient-first VibeCast web renderer that consumes only the existing
renderer-safe Broadcast projection. The 10-inch portrait Raspberry Pi is the
first real-hardware reference host. A future Google Cast Custom Web Receiver
uses the same renderer and data model in a landscape television composition.

The Apple client remains the paired Session owner and sender. It initiates a
bounded, ephemeral Receiver handoff; it never streams or mirrors pixels.

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
