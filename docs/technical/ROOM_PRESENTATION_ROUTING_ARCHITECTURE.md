# Room Presentation Routing Architecture

## Status

Canonical deferred architecture. This document defines the ownership and
routing boundary for future room-scoped presentation only. It authorizes no
Runtime, playback, Broadcast, Renderer Host, Home Assistant registry,
configuration, transport or user-interface implementation.

## Purpose

Room Presentation Routing determines which independent Renderer Hosts may
present the same immutable Presentation for one DJMoment in the Home Assistant
Area of the active playback output. It is Presentation distribution, not
DJMoment creation, Presentation composition, playback control or
Renderer-to-Renderer coordination.

```text
Session Runtime owns DJMoment and Presentation Composer composes Presentation
        ↓
Room Presentation Routing selects eligible hosts for the active Area
        ↓
Renderer Hosts consume supported capabilities from that same Presentation
```

The Runtime remains the owner of Session lifecycle and immutable DJMoments.
Broadcast remains the owner of renderer-safe distribution. A Renderer Host
remains the owner of only its local presentation.

## Architectural principle

The active playback output is the sole future starting point for room
presentation routing:

```text
Active playback output
        ↓
Home Assistant entity
        ↓
Device Registry
        ↓
Area Registry
        ↓
Active Home Assistant Area
        ↓
eligible Renderer Hosts
```

The current output determines the active Area; the Area determines eligibility.
The Runtime does not select a Renderer Host directly, and Renderer Hosts do not
discover, select or communicate with each other.

## Room Presentation Context

The future Runtime-scoped **Room Presentation Context** is the minimal
architectural context for this routing decision. It is ephemeral, belongs to
the active Session and is destroyed with that Session. It conceptually contains
only:

- the current playback output target;
- the resolved Home Assistant Area, when reliable;
- eligible Visual Renderer Hosts;
- eligible Audio Renderer Hosts; and
- a routing status.

It is not persistent configuration, Profile state, Session history, a
DJMoment field, a provider payload or a new Broadcast contract. This document
does not define its implementation model or lifecycle API.

## Output target resolution

Where Home Assistant already has a safe normalized playback target, future
routing may resolve it through the entity, Device Registry and Area Registry.
The Area is an installation-owned Home Assistant concept; it is neither an
inferred client room nor a provider-owned zone.

Some playback backends may expose an output that is not itself a Home Assistant
entity. That absence must not be guessed from track metadata, a device name or
a Renderer Host location. It is the reason for the separate deferred Output
Target Binding concept.

## Deferred Output Target Binding

**Output Target Binding** is future installation configuration that maps a
provider-specific playback output onto a canonical Home Assistant Area. For
example:

```text
Spotify Connect device
        ↓
Home Assistant media_player
        ↓
Home Assistant Area
```

It is not Session Runtime state, Playback Observation state or a Renderer Host
responsibility. It must not expose provider credentials, make provider-specific
payloads part of Broadcast, or create a second playback path. A dedicated
capability must define authorization, configuration, validation and lifecycle
before any binding is implemented.

## Independent Renderer Hosts

Routing makes eligible hosts recipients of the same immutable DJMoment; it
does not create a master Renderer Host. Each host consumes only the independent
Presentation Capabilities it supports; routing never selects a capability for a
host. See [Presentation Capability Architecture](../product/PRESENTATION_CAPABILITY_ARCHITECTURE.md).

### Visual Renderer Hosts

Eligible visual hosts in the active Area may present existing renderer-safe
projections such as Now Playing, Session Flow, DJMoments and an Ambient
presentation. Examples include the Raspberry Pi Wall Panel, Universal Receiver
and future Ambient displays.

### Audio Renderer Hosts

Eligible audio hosts in the active Area may render server-approved speech.
A Home Assistant Voice Satellite is one possible Audio Renderer Host. Voice
Satellite remains the correct Home Assistant product, entity, configuration and
UI terminology; Audio Renderer Host is DJConnect's internal architectural term.
They consume the same DJMoment as visual hosts and never synchronize through
peer communication.

The Raspberry Pi Wall Panel is a Visual Renderer Host. It does not need local
TTS generation. Where speech is available, an independent Audio Renderer Host
in the same resolved Area is expected to render it. Platform Adapter work stays
independent from Room Presentation Routing.

### Ambient Light Renderer Hosts

Eligible Ambient Light Renderer Hosts are a deferred third presentation role.
They receive the same immutable DJMoment and Presentation Intent, and may
express that approved meaning through local lighting capabilities. They do not
read raw audio, communicate with Visual or Audio Renderer Hosts, or alter
routing ownership; see
[Ambient Light Renderer Host Architecture](AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md).

## Shared presentation and soft synchronization

```text
one immutable DJMoment
        ↓
Room Presentation Routing
        ├── Visual Renderer Host(s)
        └── Audio Renderer Host(s)
        └── Ambient Light Renderer Host(s)
```

Each host interprets the same Presentation Intent according to its approved
capabilities. Shared immutable identity supports **soft synchronization**:
visual and audio presentation should be approximately aligned without a
Renderer-to-Renderer protocol. Sample-accurate playback, clock authority,
acknowledgements, retries and a master renderer are explicitly out of scope.

## Deferred Area Presentation Policy

An **Area Presentation Policy** is a future installation-owned configuration
concept. It may eventually express choices such as a preferred Audio Renderer,
speech enabled or visual enabled. It is not part of the current Session, a
DJMoment, Broadcast state or Renderer Host local state. No policy fields,
defaults or selection algorithm are defined here.

## Safety fallback

When the active Home Assistant Area cannot be resolved reliably, DJConnect
must not autonomously present speech in an arbitrary room. Speech routing stays
disabled until a reliable Area is available.

Visual Guest Renderers may continue presenting the authorized Session through
their existing renderer-safe Broadcast subscription. That is ordinary
renderer-local presentation, not a fallback Area decision and not permission
to infer a room.

## Ownership and non-goals

| Concern | Owner |
| --- | --- |
| Session lifecycle and immutable DJMoment | Session Runtime / DJ Moment Engine |
| Semantic order | Session Flow |
| Safe distribution | Broadcast |
| Active playback output normalization | Session Runtime / existing playback boundary |
| Future Area eligibility decision | Room Presentation Routing |
| Local visual or audio rendering | each independent Renderer Host |
| Local ambient-light rendering | each independent Ambient Light Renderer Host |
| Provider-output-to-Area installation mapping | future Output Target Binding |

This architecture does not authorize implementation of Room Presentation
Context, Output Target Binding, Area Presentation Policy, Voice Satellite
routing, room configuration, TTS generation, renderer discovery, peer
communication, a new HTTP endpoint, a new WebSocket channel, persistence,
transport changes or Runtime behavior changes.

## References

- [DJ Presentation Architecture](../product/DJ_PRESENTATION_ARCHITECTURE.md)
- [Audio Renderer Host Architecture](AUDIO_RENDERER_HOST_ARCHITECTURE.md)
- [Ambient Light Renderer Host Architecture](AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md)
- [Renderer Host Classification](RENDERER_HOST_CLASSIFICATION.md)
- [Platform Ambient Experience](PLATFORM_AMBIENT_EXPERIENCE.md)
- [Universal Receiver V1 — Server Architecture](UNIVERSAL_RECEIVER_ARCHITECTURE.md)
- [Broadcast Transport](BROADCAST_TRANSPORT.md)
