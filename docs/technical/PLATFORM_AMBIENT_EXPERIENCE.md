# Platform Ambient Experience

## Status

**Deferred architecture.** This document preserves a future direction only. It
does not authorize a Platform Adapter, Raspberry Pi implementation, Receiver
feature, Runtime contract, transport change or hardware integration.

The reference hardware for future evaluation is a Raspberry Pi-based wall
panel. It is not a new DJConnect platform owner and does not alter Universal
Receiver V1's platform-neutral Renderer Host boundary.

## Purpose

Platform Ambient Experience describes how an installation-owned wall display
may eventually use hardware-specific presentation capabilities without moving
business meaning away from Home Assistant.

```text
Home Assistant Runtime → Broadcast → Renderer Host → Platform Adapter → hardware
       owns meaning       owns delivery      owns UI       owns device detail
```

The Platform Adapter is deliberately outside the Runtime and outside the HTML
Renderer. It is a future local integration boundary for hardware capabilities
that cannot reasonably be provided by a browser page.

## Platform-neutral Renderer principle

The Universal Receiver remains a platform-neutral, passive Web Renderer Host.
It consumes only renderer-safe Broadcast projections, reconstructs temporary
presentation from server snapshots and has no Runtime, Planner, Knowledge,
Session Flow or Broadcast authority.

Platform-specific capabilities must not become Renderer business logic. A
browser page must not acquire GPIO, display-power, watchdog, audio-device or
kiosk-process ownership merely because it is displayed on a wall panel.

## Deferred Platform Adapter

A future Platform Adapter may own only local, hardware-specific concerns such
as:

- display brightness and power state;
- kiosk lifecycle and browser watchdog behaviour;
- hardware audio-output selection; and
- other installation-local device integration.

It does not own playback, Session lifecycle, Planner timing or selection,
Knowledge, DJMoment realization, Session Flow, Broadcast state, Profile data or
provider credentials. It does not create a second transport, a second Runtime
or a hardware-specific intelligence pipeline.

The Adapter is an optional local companion to a Renderer Host, not a
replacement Renderer. It remains disposable with the local device and never
becomes an authoritative Session participant.

## Deferred Display Policy

A future Display Policy may map high-level presentation state to local
hardware. Its possible local intents are:

| Local intent | Illustrative local mapping |
| --- | --- |
| `ACTIVE` | Full brightness while the wall panel actively presents the Session. |
| `AMBIENT` | Dimmed, passive room display. |
| `SLEEP` | Display power off or an equivalent low-power local state. |

These are architecture vocabulary, not a current Runtime field, Broadcast
projection, API, automation or brightness algorithm. The Runtime must not
directly set hardware brightness or display power. A future Renderer Host and
its Platform Adapter may map existing server-owned Presentation Intent onto a
local Display Policy only after a dedicated capability defines the needed safe
contract and evaluates the reference hardware.

## Deferred Ambient Audio

Ambient Audio is subtle, renderer-specific feedback: for example an arrival
chime, transition cue or soft acknowledgement sound. It is distinct from TTS
and from a DJMoment's server-owned meaning.

The Runtime may publish Presentation Intent through its established semantic
path. A future Renderer Host or Platform Adapter may decide whether its local
hardware can render an appropriate ambient cue. It must not generate narrative,
change a Moment, infer a new event, fetch audio from a provider or make itself
an audio authority.

## Optional rendering of server-generated speech

Future Renderer Hosts may optionally render speech that the server has already
approved and generated. The Runtime remains owner of what may be spoken; the
Renderer Host and its Platform Adapter remain owner of how approved speech is
rendered on local hardware.

This preserves the distinction between server-owned speech content and
platform-owned output. It does not authorize local speech generation, a local
voice model, a new TTS provider, speech persistence or a new voice transport.

## Raspberry Pi wall-panel boundary

The future Raspberry Pi wall panel remains:

- local-first and installation-owned;
- stateless beyond temporary local presentation and device operation;
- Renderer-only; and
- subordinate to the Home Assistant-owned Runtime and Broadcast lifecycle.

Disconnecting, restarting or replacing the panel must never affect an active
Session, Planner, Knowledge Engine, playback backend, Session Flow or Broadcast
state. It must reconstruct presentation from the established renderer-safe
projection when it reconnects.

## Deferred gate

Platform Ambient Experience remains deferred until all of the following are
true:

1. the reference wall-panel hardware is available;
2. Universal Receiver platform maturity makes real integration evaluation
   meaningful; and
3. a dedicated Pre-Flight identifies the smallest needed local contract without
   changing the platform-neutral Renderer boundary.

It does not outrank current Universal Receiver work or the active Automated
Session Intelligence E2E Verification Epic.

## Explicit non-goals

This document does not implement or authorize:

- a Platform Adapter or Raspberry Pi-specific code;
- display dimming, display power management, kiosk control or watchdogs;
- Ambient Audio, local audio playback or TTS;
- a new Runtime, Broadcast, HTTP or WebSocket contract;
- browser persistence, local Session state or browser authority; or
- a change to Universal Receiver V1 behaviour.

## References

- [Universal Receiver V1 — Server Architecture](UNIVERSAL_RECEIVER_ARCHITECTURE.md)
- [DJ Presentation Architecture](../product/DJ_PRESENTATION_ARCHITECTURE.md)
- [Developer Experience Roadmap](../product/DEVELOPER_EXPERIENCE_ROADMAP.md)
