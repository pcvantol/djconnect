# DJConnect Host Role Architecture

**Status:** Canonical architecture

**Owner:** DJConnect Platform Foundation

**Scope:** Architectural participation roles between canonical capabilities and concrete platforms. This document changes no Runtime, renderer, API, capability ownership or platform behaviour.

## Purpose

DJConnect capabilities exist canonically once. A concrete platform does not define those capabilities; it implements one or more **Host Roles** through which it participates in them.

```text
Canonical Capability
        ↓
Host Role
        ↓
Platform
```

The [DJConnect Capability Model](DJCONNECT_CAPABILITY_MODEL.md) remains the authority for capability identity, ownership, maturity, privacy and projection state. This document is the authority for Host Role meaning and inheritance.

## Principles

- Host Roles are orthogonal. A platform may implement more than one at once.
- Host Roles define participation only: they never own a capability, Runtime state, Session state, provider credential, canonical event or authorization decision.
- Home Assistant is the only Runtime Host. A Runtime Host may never be duplicated.
- Platform capability profiles are inherited through Host Roles. A projection is still subject to the Capability Model's authorization, privacy and intentional-absence rules.
- Multiple Interaction and Renderer Hosts may participate concurrently in one DJ Session. The Session remains the sole coordinator of context, decisions, canonical events and authorized actions. Hosts complement each other through bounded input and presentation projections; they do not coordinate directly or duplicate Session intelligence.

## Canonical Host Roles

| Role | Purpose and responsibilities | Prohibited responsibilities | Required capability types | Optional capability types | Intentional absences |
| --- | --- | --- | --- | --- | --- |
| Runtime Host | Runs the canonical Session Runtime, Planner, Knowledge, DJMoment Engine, Presentation, Broadcast, Conversation, authorization and playback orchestration. | A second Runtime, delegated Session ownership, client-owned canonical events. | CAP-SI-01–07, CAP-BP-01–06, CAP-CV-01–06, CAP-PB-01–05. | CAP-ID-01–05, CAP-PS-01–04, CAP-IN-01–04, CAP-VR-01–05, CAP-DL-01–06. | none; Home Assistant is the sole implementation. |
| Interaction Host | Initiates bounded interaction: Ask DJ, Session Start Request, playback/Session commands, follow-ups, clarification and confirmation. | Runtime, Planner, Knowledge, Session or Conversation intelligence ownership. | CAP-CV-01, CAP-CV-03–05, CAP-SI-07. | CAP-PB-03/05, CAP-CV-02/06, CAP-VR-01–03, CAP-IN-03/04. | direct Session creation and host-to-host coordination. |
| Renderer Host | Presents renderer-safe Runtime state, immutable DJMoments, Session Flow and Presentation. | Runtime meaning, Planner access, personal-state inference or presentation authority. | CAP-BP-01/03/05/06, CAP-SI-05/06. | CAP-PB-04, CAP-IN-01/02, CAP-VR-03/04. | private Profile state without explicit policy. |
| Rich Personal Host | Provides an authorized personal Profile experience. | Canonical Profile, Music DNA, recommendation or conversation-history storage. | CAP-ID-01–03, CAP-PS-01/02/04. | CAP-ID-05, CAP-CV-02/06, CAP-IN-01–04. | shared-device default and provider credentials. |
| Shared Appliance Host | Provides an always-on, managed household appliance and room presentation experience. | Personal Profile authority, unrestricted personal history or local intelligence. | CAP-DL-06, CAP-BP-01/03/06. | CAP-ID-02/03, CAP-CV-01, CAP-IN-01/02. | private personal projection unless policy authorizes it. |
| Ambient Host | Provides low-attention, peripheral presentation. | Session control authority, rich personal management or direct Runtime access. | CAP-BP-01/05/06. | CAP-PB-04, CAP-SI-05/06. | rich history, queue browsing and personal state. |
| Voice Interaction Host | Provides voice-first Ask DJ, Session Start Request, Session-aware and outside-Session conversation, bounded actions and spoken responses. | Conversation intelligence, Session ownership, rich history or host-to-host coordination. | CAP-CV-01/03–05, CAP-SI-07, CAP-VR-01/03. | CAP-PB-03/05, CAP-VR-02/04, CAP-BP-06. | Session Flow UI, queue browsing, artwork and rich history. |
| Constrained Device Host | Provides minimal physical control, BLE provisioning, OTA and a deliberately reduced capability surface. | Personal intelligence UI, conversation history, provider credentials or Runtime ownership. | CAP-DL-01–06. | CAP-PB-03, CAP-VR-01/02/04/05. | rich Ask DJ chat, Music DNA and Discovery UI. |

### Voice operating contexts

A Voice Interaction Host is an Interaction Host with a voice-first projection. Outside an active Session, Ask DJ remains available and may submit an authorized `CAP-SI-07` Session Start Request. Inside an active Session, Ask DJ and bounded voice actions use the active Session context. In both contexts, Home Assistant owns Conversation intelligence and the Session remains the sole coordinator.

## Canonical Host Role Matrix

`Yes` denotes an implemented role, `Planned` a documented future role, and `—` an intentional non-role. The matrix documents only implemented Host Roles; capabilities are inherited through the mapping below.

| Platform | Runtime | Interaction | Renderer | Rich Personal | Shared Appliance | Ambient | Voice Interaction | Constrained Device |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Home Assistant | Yes | — | — | — | — | — | — | — |
| Apple | — | Yes | Yes | Yes | — | — | — | — |
| Windows | — | Yes | Yes | Yes | — | — | — | — |
| Pi 4-inch | — | Yes | Yes | — | Yes | — | — | — |
| Pi 10-inch | — | Planned | Planned | — | Planned | Planned | — | — |
| ESPHome Voice Hosts | — | Yes | — | — | — | — | Yes | — |
| constrained ESP32 | — | Yes | — | — | — | — | — | Yes |
| Universal Receiver | — | Yes (bounded) | Yes | — | — | — | — | — |
| VibeCast | — | Yes (lightweight) | Yes | — | — | Yes | — | — |
| Central API | — | — | — | — | — | — | — | — |
| Website | — | — | — | — | — | — | — | — |

Central API and Website are supporting/product surfaces, respectively; neither is a Runtime or Host Role implementation. Release/artifact repositories are also not Host Role implementations.

## Capability → Host Role inheritance

The following maps every canonical capability from the Capability Model to required and optional Host Roles. It intentionally does not map capability IDs directly to platforms.

| Capability IDs | Required Host Roles | Optional Host Roles |
| --- | --- | --- |
| CAP-ID-01–05 | Runtime Host | Rich Personal Host; Shared Appliance Host; Interaction Host |
| CAP-PB-01–05 | Runtime Host | Interaction Host; Renderer Host; Voice Interaction Host; Constrained Device Host |
| CAP-SI-01–07 | Runtime Host | Interaction Host; Renderer Host; Voice Interaction Host |
| CAP-BP-01–06 | Runtime Host | Renderer Host; Ambient Host; Shared Appliance Host; Voice Interaction Host |
| CAP-CV-01–06 | Runtime Host | Interaction Host; Rich Personal Host; Voice Interaction Host; Shared Appliance Host |
| CAP-PS-01–04 | Runtime Host | Rich Personal Host; Shared Appliance Host |
| CAP-IN-01–04 | Runtime Host | Rich Personal Host; Renderer Host; Shared Appliance Host; Interaction Host |
| CAP-VR-01–05 | Runtime Host | Voice Interaction Host; Interaction Host; Constrained Device Host; Renderer Host |
| CAP-DL-01–06 | Runtime Host | Constrained Device Host; Shared Appliance Host; Interaction Host |
| CAP-SUP-01–04 | none; supporting infrastructure is outside Host Role participation | none; these capabilities do not grant a Host Role |

The ranges above are exact references to the IDs in the Capability Model and apply to every ID within each range. A host may receive only the bounded, authorized projection that its role permits; inheritance neither grants a capability to every platform implementing a role nor changes an intentional absence.

## Host Role → Platform mapping

The Canonical Host Role Matrix is the complete Platform mapping. It records only implemented roles and deliberately does not repeat capability inventories. Platforms inherit relevant capability projections from their roles subject to the Capability Model.

## Architectural rationale and follow-up

Host Roles remove the false choice between a platform-defined architecture and feature-parity demands. They preserve canonical capabilities and Home Assistant ownership while allowing a platform to combine interaction, presentation, personal, appliance, ambient, voice or constrained participation as appropriate.

The next narrow increment is **CMB-09**, the formal Voice Interaction Host and constrained ESP32 capability-profile assessment. Pi assessments inherit Shared Appliance Host and Renderer Host; Apple and Windows inherit Interaction Host, Renderer Host and Rich Personal Host. Future Android, CarPlay, wearables, Meta Quest and other platforms must select Host Roles before proposing platform capabilities.
