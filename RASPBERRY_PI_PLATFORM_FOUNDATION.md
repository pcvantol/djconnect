# Raspberry Pi Platform Foundation v2

**Status:** Canonical Platform Evolution architecture

**Owner:** DJConnect Platform Foundation

**Scope:** Raspberry Pi Concrete Host participation in the canonical Capability Architecture. This document changes no Runtime, ownership, API contract, Session Intelligence or renderer behaviour.

## Purpose and authority

The Raspberry Pi Platform Family consumes the [Capability Model](DJCONNECT_CAPABILITY_MODEL.md) and [Host Role Architecture](HOST_ROLE_ARCHITECTURE.md). It does not redefine capabilities, Host Roles, ownership or platform-wide contracts.

```text
Canonical Capability
        ↓
Host Role
        ↓
Pi Concrete Host
        ↓
Raspberry Pi Platform Family
```

The Platform Family is an organizational product, release and technology
grouping. Its Concrete Hosts inherit only the bounded, authorized projections
permitted by their Host Roles. Neither the family nor a Concrete Host owns the
Session Runtime, Planner, Knowledge, Conversation Agent or Music Backend.

## Concrete Hosts

| Concrete Host | Native implementation | Host Roles | Purpose | Assessment rule |
| --- | --- | --- | --- | --- |
| Pi 4-inch Appliance | Native QML application | Interaction Host; Renderer Host; Shared Appliance Host | Compact shared-room controller. | Its capability profile is independent. |
| Pi 10-inch Wall Appliance | Native QML application | Interaction Host; Renderer Host; Shared Appliance Host | Dedicated always-on household wall experience. It does not replace the Pi 4-inch appliance. | Its capability profile is independent. |

Capability parity between these appliances must never be assumed. Every
capability expansion begins with a Repository Capability Assessment against the
Capability Model, the inherited Host Roles and the specific Concrete Host.

## Native Pi architecture

Native QML is the canonical normal-operation implementation for both Concrete
Hosts. The Universal Receiver is hosted by Home Assistant, Session-authorized
and browser-based; it remains independent of the Raspberry Pi Platform Family
and is never a replacement implementation for Pi. A Pi may execute a browser
temporarily for qualification or engineering validation only.

A browser-based renderer may exist as an additional Renderer Host, but does not
change the native Pi architecture, Pi lifecycle or Pi product role.

## Capability projections

The following are projections of existing canonical capabilities, not new Pi
capabilities or Pi-owned contracts.

### Pi 4-inch Appliance

The compact shared-room controller projects bounded Playback, current playback
and compact DJMoment information through `CAP-PB-02`–`CAP-PB-05`,
`CAP-BP-01`/`CAP-BP-03`, and `CAP-SI-05`. Its primary user-facing projections
are playback controls, output selection, queue and playlist interactions where
the selected Music Backend permits them, current playback and a compact Current
DJMoment.

Intentional absences are rich Session Flow, Music DNA management, conversation
history and Discovery dashboards. Those are not parity defects.

### Pi 10-inch Wall Appliance

The wall appliance projects the same bounded Playback and current-DJMoment
capabilities, plus the renderer-safe Session Flow and Presentation projections
already owned by Home Assistant: `CAP-SI-06` and `CAP-BP-06`.

Its independent renderer layout is:

| Surface region | Canonical projection |
| --- | --- |
| Top | playback, artwork, progress, outputs and compact controls |
| Middle | Current DJMoment |
| Lower | Session Flow and Presentation timeline |

Gesture navigation and the absence of permanent navigation chrome are
renderer-local implementation choices. They do not create a Session navigation
contract or a new capability.

## Shared Raspberry Pi Platform layer

The two Concrete Hosts inherit one shared native Raspberry Pi platform layer.
It owns only Pi-local operational concerns:

- bootstrap and deployment;
- updater and atomic updates;
- platform adapter and managed lifecycle;
- watchdog and diagnostics.

This shared layer is not a Runtime, Music Backend, Conversation Agent or
renderer authority. Renderer-specific behavior stays within the respective
Concrete Host.

## Independent renderer surfaces

Pi renderer surfaces update independently from canonical projections. There is
no renderer-wide refresh mechanism. The surface set is:

- Playback;
- Current DJMoment;
- Session Flow;
- Ambient Presentation;
- Status;
- platform overlays.

Each surface may be absent when its Concrete Host intentionally does not expose
the corresponding capability projection.

## Appliance lifecycle

The following local appliance states are canonical Pi presentation/lifecycle
states. They are renderer-local and never alter Session ownership.

| State | Local responsibility |
| --- | --- |
| Bootstrapping | establish native platform services and obtain authorized runtime state |
| No Session | render bounded idle/shared-room state without creating a Session |
| Active Session | render authorized active-Session projections |
| Ambient Session | render low-attention local presentation where the host supports it |
| Screen Off | preserve local appliance power/display policy only |
| Temporary Wake | temporarily expose the permitted local surfaces |
| Updating | perform the shared platform layer's controlled update lifecycle |

## Session-coordinated multimodal participation

Pi participates in an active Session but never coordinates directly with other
hosts. The canonical Session remains the sole coordinator of context,
decisions, events and authorized actions. Examples include a Voice Interaction
Host speaking while Pi presents the same DJMoment, Universal Receiver rendering
the same Presentation, and Apple rendering additional authorized personal
projections.

ESPHome Voice Hosts are independent Concrete Hosts. They provide Ask DJ,
Session Start Requests, Session-aware/outside-Session conversation and spoken
responses. Pi provides complementary visual presentation. Neither host
coordinates directly with the other; both consume the same Session.

## Deferred Platform Evolution work

The following work remains assessment-first and is not implementation
authorization:

- CMB-05: Pi 4-inch capability-profile assessment;
- CMB-06: Pi 10-inch capability-profile assessment;
- bounded renderer-surface and ambient capability assessments only after the
  applicable Concrete Host assessment;
- any future host expansion only after a Repository Capability Assessment.

## Preserved boundaries

- Home Assistant remains the only Runtime Host and owner of Session
  Intelligence, authorization, Conversation and Music Backend orchestration.
- Pi consumes canonical Runtime contracts only.
- Universal Receiver is independent of the Pi Platform Family.
- Native QML remains the canonical Pi implementation.
- Pi 4-inch and Pi 10-inch remain independently assessable Concrete Hosts.

The CMB-05 assessment is recorded in
`docs/product/PI_4_INCH_CAPABILITY_PROFILE_ASSESSMENT.md`. Its partial
qualification preserves this foundation: the Pi 4-inch remains a compact,
shared native appliance with intentional rich-surface absences, while only
target-hardware compact-projection and shared-profile visibility evidence
remain for future assessment.
