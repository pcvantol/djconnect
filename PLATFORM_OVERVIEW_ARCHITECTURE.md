# DJConnect Platform Overview Architecture

**Status:** Canonical architecture navigation
**Scope:** Existing platform architecture, described only
**Authority:** This overview introduces no implementation work or new
architecture. The linked canonical documents remain authoritative.

## Purpose

DJConnect is a collection of cooperating platforms. Each platform has one
architectural responsibility and explicit ownership boundaries. Platforms
cooperate through established contracts rather than by sharing responsibility.

This document is the recommended starting point for architectural orientation.
It summarizes existing architecture and directs readers to the canonical
documents that define each boundary in detail.

## Platform overview

| Platform | Architectural responsibility | Canonical detail |
| --- | --- | --- |
| Profile Platform | Persistent personal state and identity. | [Domain Model](DOMAIN_MODEL.md), [Persistent Session Architecture](PERSISTENT_SESSION_ARCHITECTURE.md) |
| Playback Platform | Playback ownership, backend abstraction and normalized observation. | [V4 Architecture](DJCONNECT_V4_ARCHITECTURE.md), [Live Playback Observation](docs/product/LIVE_PLAYBACK_OBSERVATION.md) |
| Session Intelligence Platform | Active Session decisions and their immutable semantic results. | [Runtime Contracts](DJ_SESSION_RUNTIME_CONTRACTS.md), [DJ Presentation Architecture](docs/product/DJ_PRESENTATION_ARCHITECTURE.md) |
| Presentation Platform | Renderer-safe distribution and local experience. | [Renderer Host Classification](docs/technical/RENDERER_HOST_CLASSIFICATION.md), [Universal Receiver Architecture](docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md) |
| Verification Platform | Deterministic proof that approved behaviour conforms. | [Verification Architecture](docs/verification/01_VERIFICATION_ARCHITECTURE.md), [Session Intelligence E2E Architecture](docs/verification/SESSION_INTELLIGENCE_E2E_ARCHITECTURE.md) |

## Profile Platform

The Profile Platform owns persistent user information: Profile identity, Music
DNA, Preferences, the Music Backend binding, long-term personal state and other
persistent personal capabilities. It does not own active Runtime, Planner or
Renderer state.

Presentation consumes only renderer-safe projections. It never becomes a
source of Profile truth. The [Domain Model](DOMAIN_MODEL.md) and
[Runtime Contracts](DJ_SESSION_RUNTIME_CONTRACTS.md) define the persistence and
Runtime boundary.

## Playback Platform

The Playback Platform owns playback: Music Backend abstraction, backend
integration, Output Targets, playback observation and normalization. Its
Playback Control and Playback Observation boundaries retain their respective
provider-specific responsibilities.

Playback ownership never migrates into Session Intelligence or Renderer Hosts.
Session Intelligence consumes bounded normalized context; Renderer Hosts render
only safe published projections. The [V4 Architecture](DJCONNECT_V4_ARCHITECTURE.md)
and [Live Playback Observation](docs/product/LIVE_PLAYBACK_OBSERVATION.md)
describe those boundaries.

## Session Intelligence Platform

The Session Intelligence Platform determines **what should happen** during an
active Session. It comprises the Session Runtime, Planner, Knowledge Engine, DJ
Moment Engine, Performance Memory, immutable DJMoments, Session Flow and
Session decision making.

The Runtime is server-owned and ephemeral. The Planner owns planning and
intent selection; the Knowledge Engine owns knowledge resolution; the DJ Moment
Engine owns realization into immutable DJMoments; and Session Flow retains
semantic ordering. This platform does not own backend playback, Renderer Host
presentation or persistent Profile state. The complete lifecycle and ownership
model is defined by the [DJ Session Runtime Contracts](DJ_SESSION_RUNTIME_CONTRACTS.md).

## Presentation Platform

The Presentation Platform determines **how Session Intelligence is
experienced**. The server-owned Presentation Composer transforms one approved
immutable DJMoment into one immutable renderer-safe Presentation before
Broadcast distributes its additive Presentation Projection beside the existing
DJMoment projection. Presentation Routing determines eligible independent
Renderer Hosts; each Renderer Host owns local presentation only.

The platform includes Visual, Audio and Ambient Light Renderer Hosts, the
Universal Receiver Web Platform, VibeCast and Audience Experience. These are
presentation concerns: none owns the Runtime, Planner, Knowledge Engine, DJ
Moment Engine, Session Flow or playback. VibeCast remains a distinct ambient
experience built on the Universal Receiver Web Platform, while Audience
Experience remains a separate participant-originated concern.

Continue through [Renderer Host Classification](docs/technical/RENDERER_HOST_CLASSIFICATION.md),
[Room Presentation Routing](docs/technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md),
[Universal Receiver Architecture](docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md),
[Presentation Composer Architecture](docs/product/PRESENTATION_COMPOSER_ARCHITECTURE.md),
[Presentation Capability Architecture](docs/product/PRESENTATION_CAPABILITY_ARCHITECTURE.md),
[Speech Rendering Contract](docs/technical/SPEECH_RENDERING_CONTRACT.md),
[VibeCast Architecture](docs/product/VIBECAST_ARCHITECTURE.md) and
[Audience Experience Architecture](docs/product/AUDIENCE_EXPERIENCE_ARCHITECTURE.md).

## Verification Platform

The Verification Platform determines **whether implementation conforms to
approved behaviour**. It owns the Verification Runtime, Verification Clock,
Golden Scenarios, Golden Smoke, Golden Regression, qualification and
deterministic verification evidence.

Verification is orthogonal to product execution. It observes and proves
behaviour through its own infrastructure; it never becomes the Session Runtime,
does not own product decisions and does not participate in Runtime execution.
The [Verification Architecture](docs/verification/01_VERIFICATION_ARCHITECTURE.md),
[Verification Clock Architecture](docs/verification/VERIFICATION_CLOCK_ARCHITECTURE.md)
and [Session Intelligence Qualification Policy](docs/verification/SESSION_INTELLIGENCE_QUALIFICATION_POLICY.md)
define its detailed boundaries.

## Platform relationships

The following is a conceptual relationship, not a replacement execution
pipeline:

```text
Profile Platform
        ↓
Playback Platform
        ↓
Session Intelligence Platform
        ↓
Broadcast
        ↓
Presentation Platform

Verification Platform — orthogonal behavioural proof
```

Profile supplies persistent context. Playback owns the actual listening state.
Session Intelligence uses the permitted context to decide what should happen.
Broadcast carries renderer-safe projections to the Presentation Platform, which
renders them locally. The Verification Platform validates approved behaviour
without joining this Runtime path.

## Ownership boundaries

| Owner | Owns | Does not own |
| --- | --- | --- |
| Profile Platform | Persistent user state. | Active Runtime state or presentation. |
| Playback Platform | Playback and backend-specific execution or observation. | Session decisions or Renderer presentation. |
| Session Intelligence Platform | Session decisions and immutable semantic output. | Playback execution, Profile persistence or renderer behaviour. |
| Presentation Platform | Renderer-safe presentation. | Runtime meaning, planning or playback. |
| Verification Platform | Behavioural proof. | Product Runtime execution or product ownership. |

No platform duplicates another platform's responsibility. Existing canonical
contracts resolve detailed ownership questions.

## Architectural characteristics

The existing architecture is capability-oriented, projection-driven, explicit
about ownership and platform-neutral. It uses immutability where the existing
model requires it, keeps renderer projections safe, separates Presentation from
Intelligence, and separates Verification from execution. These are summaries of
the established architecture principles, not additional principles.

## Historical evolution

| Generation | Historical focus |
| --- | --- |
| Generation 1 | Foundational playback and product capabilities. |
| Generation 2 | Session Intelligence and the Verification Platform. |
| Generation 3 | Presentation Platform architecture. |

This history provides orientation only; it does not redefine repository
lifecycle terminology, status or delivery priorities.

## Continue reading

Start with the detailed document for the platform boundary in question. For
cross-cutting principles, use [Architecture Principles](ARCHITECTURE_PRINCIPLES.md)
and [DJConnect V4 Architecture](DJCONNECT_V4_ARCHITECTURE.md). For canonical
reference precedence and wider repository navigation, return to
[Foundation Index](FOUNDATION_INDEX.md) and [Canonical References](CANONICAL_REFERENCES.md).
