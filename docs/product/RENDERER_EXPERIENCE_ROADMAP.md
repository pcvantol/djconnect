# Renderer Experience Roadmap

**Status:** CMB-04 repository-first assessment

## Decision

`GO_RENDERER_ROADMAP_REEXPRESSION`

Renderer Experience is a projection roadmap, not a second capability model or
an implementation programme. Home Assistant remains owner of Runtime, Planner,
Knowledge, immutable DJMoments, Session Flow, Presentation and Broadcast.
Every Renderer Host consumes only authorized renderer-safe projections.

## Atomic capability inventory

| Atomic renderer capability | Owner | Maturity | Consumers and boundary |
| --- | --- | --- | --- |
| Renderer-safe playback / Now Playing | HA Broadcast and Music Backend boundary | Implemented | Apple, Windows, Pi and Universal Receiver; local display only. |
| Current immutable DJMoment and Presentation | HA DJMoment Engine / Presentation | Implemented | eligible Renderer Hosts; no local Moment generation. |
| Session Flow projection | HA Session Runtime / Broadcast | Implemented | Apple/Windows rich clients, Pi 10-inch and Universal Receiver; intentionally absent on constrained voice/Pi 4-inch surfaces. |
| Track Insight | HA Insight service | Implemented | Apple, Windows and Pi; server-authoritative insight. |
| Ask DJ and Discover | HA Conversation / Discovery | Implemented personal projections | Apple and Windows rich; Pi read-heavy where authorized; not guest/ambient defaults. |
| Native Track Insight sharing | Apple Renderer Host | Implemented reference realization | explicit user action through Apple Share Sheet; no Broadcast, Runtime or API scope. |
| Universal Receiver interactive web presentation | Web Renderer Host | Implemented | browser Session Flow and Now Playing through existing Broadcast only. |
| VibeCast ambient experience | VibeCast Renderer Host | Planned | separate Guest + Ambient experience; Custom Web Receiver feasibility precedes implementation. |
| Pi 4-inch compact appliance profile | Pi Concrete Host | Planned assessment | bounded playback and Current DJMoment; intentional rich-surface absences. |
| Pi 10-inch wall appliance profile | Pi Concrete Host | Planned assessment | adds Session Flow / Presentation projection; independent from Pi 4-inch. |
| Voice / notification presentation | Voice Interaction and constrained-device hosts | Implemented bounded | HA owns response intelligence; hosts provide short spoken/control projection only. |
| Future Renderer Hosts | selected Host Role / Concrete Host | Assessment-only | capability profile and privacy evidence required before any implementation. |

## Surface model

| Surface | Canonical owner | Renderer scope |
| --- | --- | --- |
| Playback | HA Music Backend / Broadcast | local presentation and authorized bounded controls. |
| Track Insight | HA Insight service | renderer-safe display; Apple may locally share the approved result. |
| DJ Moments and Session Flow | HA Runtime, DJMoment Engine and Broadcast | immutable presentation only. |
| Sharing | existing producer plus native Renderer Host | explicit user action; platform-native sending remains local. |
| Voice and notifications | HA Conversation / Presentation | local voice or notification realization, never intelligence. |
| Controls | HA command and authorization boundaries | bounded input; no Session or Planner ownership. |
| Discover and Ask DJ | HA Discovery / Conversation | personal or explicitly authorized projection only. |

## Cross-renderer consistency

Shared capabilities are renderer-safe Broadcast, immutable DJMoments, Session
Flow where the host profile permits it, and server-owned Track Insight.
Platform-specific capabilities are intentional: Apple native sharing is native
only; rich Ask DJ/Discover are personal-host projections; Universal Receiver is
interactive web; VibeCast is ambient; Pi 4-inch and Pi 10-inch have independent
appliance profiles; ESP32/Voice hosts remain voice/control constrained. No
feature-parity obligation follows from shared terminology.

## Dependency map

| Roadmap item | Objective dependency |
| --- | --- |
| CMB-05 / CMB-06 | this atomic baseline plus each Pi host's source, privacy and hardware evidence. |
| CMB-07 | this supported/absent surface matrix and platform capability profiles. |
| CMB-08 | this separation: Universal Receiver is a Web Renderer Host; VibeCast is a distinct Ambient Renderer experience. |
| CMB-02 / CMB-03 | concrete host profiles and registered platform divergences. |
| Future Renderer Hosts | Host Role selection, local privacy evidence and an explicit bounded capability assessment. |

Platform Profiles validate the inherited capability set; Platform Divergences
record deliberate platform-specific absences or realizations. Neither changes
canonical ownership or requires convergence.

## Recommendation

Use this atomic inventory as the Renderer Experience planning projection. The
next dependent renderer assessment is CMB-08; no renderer implementation,
Runtime change, API change or new capability family is authorized by CMB-04.
