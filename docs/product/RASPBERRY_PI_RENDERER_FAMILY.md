# Raspberry Pi Renderer Family

**Status:** Canonical reference

**Scope:** Compact reference for the separately assessed Raspberry Pi 4-inch
and Raspberry Pi 10-inch Renderer Hosts. This document summarizes existing
repository decisions only; it creates no capability, implementation,
qualification item, roadmap change or Execution Horizon change.

## Family purpose and architecture

The Raspberry Pi Renderer Family consists of two independent, household-first
shared appliances. Both are native QML Renderer Hosts that consume existing,
authorized renderer-safe projections from Home Assistant. Neither owns a DJ
Session, Runtime, Planner, Knowledge, Conversation, Music Backend,
authorization decision or canonical projection.

Both hosts are Registered + Interactive Shared Appliance Hosts. Registration
serves appliance identity, lifecycle and bounded device configuration; it is
not personal sign-in or profile ownership. The hosts are not Browser Receivers
or Universal Receivers. Native QML is their canonical normal-operation
technology, while the Universal Receiver remains an independent,
Home-Assistant-hosted browser Renderer Host.

The family shares Pi-local bootstrap, deployment, update, managed lifecycle,
watchdog and diagnostics foundations. Renderer behavior remains owned by each
Concrete Host. A projection being available to one host does not establish
capability inheritance for the other.

## Raspberry Pi 4-inch appliance

The Pi 4-inch is the compact shared-room playback companion. It presents
bounded playback and a compact current-state experience:

- current track, artwork, artist, status and compact progress;
- explicit bounded playback, volume/output, queue and playlist actions when
  authorized by the backend;
- compact renderer-safe Current DJMoment and Track Insight; and
- read-only, structured Ask DJ actions where authorized.

It intentionally does not expose a full Session Flow or Presentation timeline,
a personal renderer/dashboard, a Universal Receiver surface, free prompt input,
local PTT, local TTS or local DJ-response audio. It never infers personal
identity or owns Music DNA, personal history, Session state or Runtime logic.

## Raspberry Pi 10-inch wall appliance

The Pi 10-inch is the dedicated, always-on shared household wall experience.
It presents an authorized active Session and permits bounded, explicit nearby
playback interaction:

- renderer-safe current playback, including artwork, track, artist, status,
  progress and bounded output/control projection;
- Current DJMoment and resolved Presentation;
- full active renderer-safe Session Flow and Presentation timeline;
- compact Session Direction or active DJ context when supplied by an existing
  authorized projection; and
- explicit bounded playback, volume/output, queue and playlist actions when
  authorized by the backend.

It is not a personal dashboard, second music player, Universal Receiver,
browser substitute or expansion of the Pi 4-inch. Renderer-safe shared Ask DJ
projection or actions remain bounded and explicitly authorized; unrestricted
personal history, free-form shared chat authority, local PTT, TTS and local DJ
audio are outside the profile. Music DNA, profile details, personal Ask DJ
history, provider payloads, credentials, tokens, internal Runtime context and
private Session history never appear on the shared wall surface.

## Capability comparison

| Capability | Pi 4-inch | Pi 10-inch |
| --- | --- | --- |
| Appliance role | Compact shared-room playback companion | Always-on shared household wall experience |
| Technology | Native QML | Native QML |
| Classification | Registered + Interactive Shared Appliance Host | Registered + Interactive Shared Appliance Host |
| Current playback and bounded controls | Yes | Yes |
| Current DJMoment | Compact renderer-safe projection | Renderer-safe current immutable DJMoment and resolved Presentation |
| Track Insight | Renderer-safe | Renderer-safe where supplied by the existing projection |
| Session Flow / Presentation timeline | Intentionally absent | Full active renderer-safe projection |
| Session Direction / active context | Not a canonical profile surface | Compact projection where already authorized |
| Ask DJ | Read-only structured actions only | At most renderer-safe, explicitly authorized shared projection or actions |
| Personal renderer / dashboard | No | No |
| Universal Receiver | No | No |
| Relationship to the other Pi host | Independent profile; not a reduced Pi 10-inch | Independent profile; not an expanded Pi 4-inch |

## Canonical design principles

- Both appliances are independent native Renderer Hosts, not variants of a
  Browser or Universal Receiver.
- Both use native QML for normal operation and consume only existing
  renderer-safe, server-owned projections.
- Each has its own bounded profile; no automatic capability inheritance or
  feature-parity expectation exists between the two appliances.
- They are different products for different household situations: compact
  playback companionship on Pi 4-inch and shared active-Session presentation
  on Pi 10-inch.

## Relationship to registered future work

Interactive DJMoments, Session Continuation, Apple Watch Moment-First
Companion Experience and Native Surface Integration are separately registered,
assessment-first capability families. Their registration grants neither Pi
host a new surface nor a capability change. Any future Pi relevance requires a
separate repository-first capability assessment against the applicable
Concrete Host profile.

## Sources

- [Raspberry Pi Platform Foundation](../../RASPBERRY_PI_PLATFORM_FOUNDATION.md)
- [CMB-05 — Raspberry Pi 4-inch Capability Profile Assessment](PI_4_INCH_CAPABILITY_PROFILE_ASSESSMENT.md)
- [CMB-06 — Raspberry Pi 10-inch Capability Profile Assessment](PI_10_INCH_CAPABILITY_PROFILE_ASSESSMENT.md)
- [Renderer Host Classification](../technical/RENDERER_HOST_CLASSIFICATION.md)
- [Renderer Experience Roadmap](RENDERER_EXPERIENCE_ROADMAP.md)
