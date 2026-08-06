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
| VibeCast ambient experience | VibeCast Renderer Host | Planned / selected reference increment | separate Guest + Ambient experience; portrait Pi reference validation precedes landscape Custom Web Receiver feasibility. |
| Pi 4-inch compact appliance profile | Pi Concrete Host | Planned assessment | bounded playback and Current DJMoment; intentional rich-surface absences. |
| Pi 10-inch wall appliance profile | Pi Concrete Host | Planned assessment | adds Session Flow / Presentation projection; independent from Pi 4-inch. |
| Apple Watch Moment-First Conversational Companion | Apple Renderer Host / Product Development | Planned assessment | Phase 3 Apple Premium Experience; Current DJMoment, bounded active Session Flow, compact Session projection and Ask DJ PTT are future renderer-safe experience candidates, not Watch parity or implementation authorization. |
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

## Registered future capability family: Native Surface Integration

**Status:** roadmap registered; no assessment or implementation is authorized.

Native Surface Integration is the future Renderer Host family for
platform-native surfaces that either present existing renderer-safe projections
or submit an explicit, existing Session lifecycle request. It has no DJ
Intelligence, Playback Runtime, Music Backend, Planner, Knowledge, Broadcast
or projection-creation ownership.

| Surface category | Existing-boundary purpose | Examples | Explicit boundary |
| --- | --- | --- | --- |
| Session Control Surfaces | An explicit user request to start, continue, open or end a Session, or open Ask DJ | App Shortcuts, App Icon Context Menu, Jump Lists, Spotlight and Siri App Intents | A surface submits only existing authorized Session lifecycle requests or opens a local renderer view. It does not control playback, execute DJ Intelligence or create automatic Session mutations. |
| Session Surfaces | Active-Session presentation | Live Activity, Dynamic Island and Lock Screen Live Activity | The Apple Renderer Host presents only existing renderer-safe projections while a DJ Session is active and removes the surface when that Session ends. |
| Information Surfaces | Persistent, non-player presentation | iOS Widget, macOS Widget and future watchOS complications | Widgets present only renderer-safe Session Direction or current DJMoment information. They are not a second music player or a source of Runtime state. |

The canonical boundaries remain:

```text
Session Control Surfaces -> existing authorized Session Runtime request -> Renderer
Session Surfaces         -> renderer-safe projections -> Apple Renderer Host
Information Surfaces     -> renderer-safe projections -> Widgets
```

No arrow introduces a Runtime, Planner, Broadcast, Knowledge Engine or DJ
Intelligence capability. The Renderer Host owns local platform presentation and
user interaction; Home Assistant remains the owner of authorization, Session
lifecycle and every canonical projection.

### Apple-first assessment candidate

**CMB-12 — Apple Native Surface Capability Assessment** is the first future
assessment for this family. It will inventory only repository evidence for
Widgets, Live Activity, Dynamic Island, Lock Screen Activity, App Shortcuts,
App Icon Context Menu, Spotlight, Siri App Intents, Notifications, Handoff and
Universal Links. It must not design an architecture or implement Apple code.

The assessment is deliberately sequenced after CMB-05, CMB-06 and CMB-07. It
is not part of the current Execution Horizon and introduces no priority
override.

### Candidate follow-on slices

Small, Medium and Large Widgets, Live Activity, Dynamic Island, Lock Screen
Activity, App Shortcuts and Siri App Intents are possible separately bounded
implementation candidates only after the Apple-first assessment and a future
explicit authorization. This registration neither selects nor authorizes any
candidate.

## Recommendation

Use this atomic inventory as the Renderer Experience planning projection. The
next dependent renderer assessment is CMB-08; no renderer implementation,
Runtime change, API change or new capability family is authorized by CMB-04.

## CMB-08: Universal Receiver and VibeCast decomposition

**Decision:** `GO_UNIVERSAL_RECEIVER_DECOMPOSITION`

The existing repository decomposition is complete and overlap-free. The
Universal Receiver is the implemented **Interactive Web Renderer Host**. It
owns only temporary browser presentation and lifecycle, and consumes existing
Broadcast snapshots, updates, renderer-safe Now Playing, current DJMoment and
Session Flow. It owns no Runtime, authorization decision, Planner, Knowledge,
DJMoment, canonical history or provider access.

VibeCast is a separate, planned **Ambient Renderer experience**. Its selected
reference increment uses the portrait Pi as real-hardware evidence before
Google Cast feasibility. It may reuse
the Universal Receiver Web Platform's connection lifecycle, safe projection
subscription, handoff foundations and design primitives, but owns its ambient
composition, attention model and television-oriented lifecycle. Google TV is a
future Custom Web Receiver host, not a second Runtime, native TV app or sender
pixel stream.

| Capability | Owner | Maturity | Classification |
| --- | --- | --- | --- |
| Broadcast subscription, snapshot-first delivery, reconnect and Runtime-end cleanup | Broadcast / Web platform | Implemented | shared infrastructure |
| Interactive Now Playing, current DJMoment and Session Flow rendering | Universal Receiver | Implemented | Receiver-specific |
| Ambient composition, minimal interaction and adaptive portrait/landscape pacing | VibeCast Renderer Host | Planned / selected reference increment | VibeCast-specific |
| Session authorization, Planning, Knowledge, Moments and Flow | Runtime / Broadcast | Implemented | neither renderer owns it |
| Guest participation | Broadcast authorization and Renderer Host classification | existing boundary; detailed lifecycle planned | shared boundary |

Guest renderers receive only session-scoped, renderer-safe projections. The
existing Receiver token grants no owner controls, Ask DJ, likes or Profile
access. A future VibeCast interaction adapter may submit only existing
server-validated Session Commands after receiver-input feasibility is proven;
rich Ask DJ, Discover, profiles, queue management and persistent controls stay
personal or interactive-host concerns.

No new Broadcast projection is necessary: current and future receiver work must
reuse existing safe playback, DJMoment, Session Flow and Presentation
projections. CMB-02 and CMB-03 depend on this distinction for profile and
divergence validation; CMB-05/CMB-06 remain independent Pi profile assessments.
The bounded planning and exit criteria for the selected work are recorded in
[`VibeCast Reference Renderer Increment`](VIBECAST_REFERENCE_RENDERER_INCREMENT.md).
