# DJConnect Capability Model v1.0

**Status:** Canonical current-state architecture and governance record

**Owner:** DJConnect Platform Foundation / Home Assistant

**Scope:** Repository-wide implemented capabilities and their platform projections
**Decision type:** Documentation-only; this model changes no Runtime, renderer, API or ownership behaviour.

## Purpose and authority

This is the canonical planning model for implemented DJConnect capabilities.
It records the capability once at its canonical owner and records the
platform-appropriate projections separately. It is not a client feature list,
an implementation backlog, or an entitlement catalogue.

Current `main` implementation evidence is authoritative. The historical
[`PLATFORM_DISCOVERY_REPORT.md`](PLATFORM_DISCOVERY_REPORT.md) remains evidence
of its 2026-07-09 audit; it is not authority for current capability state.

## Terms and stable identifiers

A **capability** is the smallest independently assessable product behaviour or
architectural responsibility. A **bundle** is a useful grouping, never the
lowest planning unit. A **projection** is a bounded presentation, input or
transport use of a canonical capability; it does not create a second owner.

No repository-wide identifier convention existed for product capabilities.
This model establishes `CAP-<BUNDLE>-<NN>`: an uppercase bundle mnemonic and
two-digit, append-only sequence. Identifiers are stable; a retired capability
keeps its identifier and is never reused.

Implementation classification is selected in this mandatory order:

`REUSE → CONFIGURE → EXTEND → NEW`

All catalogued capabilities are implemented on current `main`; their current
implementation classification is therefore `REUSE`. A future change may use a
different classification only after a Repository Capability Assessment.

Privacy classifications are: **personal** (profile-owned or sensitive),
**renderer-safe** (safe bounded projection), **operational** (device/service
operation), and **restricted** (authorization, credentials or security
material). Maturity is **Implemented**, **Planned**, or **Deprecated**.

## Bundle catalog and atomic capability catalog

| ID | Atomic capability | Bundle | Canonical owner | Dependencies | Maturity | Privacy | Supported projection types | Class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAP-ID-01 | Profile lifecycle | Identity and Policy | HA Profile Platform | persistent storage | Implemented | personal | Apple, Windows, Pi, HA client API contracts | REUSE |
| CAP-ID-02 | Profile resolution | Identity and Policy | HA Profile Platform | request/device/room context | Implemented | personal | all request sources | REUSE |
| CAP-ID-03 | Profile privacy policy | Identity and Policy | HA Profile Platform | profile resolution | Implemented | personal | rich, shared and voice-safe responses | REUSE |
| CAP-ID-04 | Device-to-profile mapping | Identity and Policy | HA Profile Platform | device registry | Implemented | personal | Apple, Windows, Pi, ESP32, Voice Hosts | REUSE |
| CAP-ID-05 | Portable profile import/export | Identity and Policy | HA Profile Platform | profile lifecycle, redaction | Implemented | personal | Apple and Windows; HA services | REUSE |
| CAP-PB-01 | Music-backend registration | Playback | HA Music Backend boundary | backend configuration | Implemented | restricted | HA only | REUSE |
| CAP-PB-02 | Backend capability negotiation | Playback | HA Music Backend boundary | backend registration | Implemented | renderer-safe | all client contracts | REUSE |
| CAP-PB-03 | Playback command orchestration | Playback | HA Music Backend boundary | authorization, backend capabilities | Implemented | restricted | bounded client/voice actions | REUSE |
| CAP-PB-04 | Normalized playback observation | Playback | HA Playback Platform | backend observation | Implemented | renderer-safe | Runtime and renderer projections | REUSE |
| CAP-PB-05 | Output-target selection | Playback | HA Music Backend boundary | output capability | Implemented | operational | rich clients and bounded actions | REUSE |
| CAP-SI-01 | Persistent Session lifecycle | Session Intelligence | HA Session Platform | Profile, persistence | Implemented | personal | owner-authorized history | REUSE |
| CAP-SI-02 | Ephemeral Session Runtime | Session Intelligence | HA Session Runtime | active Session, playback context | Implemented | personal | no direct client projection | REUSE |
| CAP-SI-03 | Session Planner | Session Intelligence | HA Session Runtime | Runtime context | Implemented | personal | Session Flow only | REUSE |
| CAP-SI-04 | Knowledge intent resolution | Session Intelligence | HA Session Runtime | Planner, approved knowledge | Implemented | personal | DJMoment/projection only | REUSE |
| CAP-SI-05 | Immutable DJMoment creation | Session Intelligence | HA DJ Moment Engine | Planner and knowledge intent | Implemented | renderer-safe | Broadcast and renderer hosts | REUSE |
| CAP-SI-06 | Session Flow | Session Intelligence | HA Session Runtime | Planner, DJMoments | Implemented | renderer-safe | owner and authorized renderers | REUSE |
| CAP-SI-07 | Authorized Session Start Request | Session Intelligence | HA Session Runtime | Profile resolution, command authorization, existing Start Strategy model | Implemented | restricted | Voice, Apple, Windows and other eligible Interaction Hosts | REUSE |
| CAP-BP-01 | Renderer-safe Broadcast snapshot | Broadcast and Presentation | HA Broadcast | active Runtime | Implemented | renderer-safe | Universal Receiver, native renderers | REUSE |
| CAP-BP-02 | Session-scoped Broadcast authorization | Broadcast and Presentation | HA Broadcast | active Session, authorization | Implemented | restricted | unpaired Universal Receiver participation | REUSE |
| CAP-BP-03 | Broadcast WebSocket delivery | Broadcast and Presentation | HA Broadcast | snapshot and authorization | Implemented | renderer-safe | Apple, Windows, Pi, Universal Receiver | REUSE |
| CAP-BP-04 | Broadcast recovery cursor | Broadcast and Presentation | HA Broadcast | bounded replay log | Implemented | restricted | authorized renderer recovery | REUSE |
| CAP-BP-05 | Universal Receiver hosting | Broadcast and Presentation | HA | Broadcast and session authorization | Implemented | renderer-safe | unpaired browser/TV receiver | REUSE |
| CAP-BP-06 | Presentation composition | Broadcast and Presentation | HA Presentation Platform | immutable DJMoment | Implemented | renderer-safe | eligible visual/audio/ambient hosts | REUSE |
| CAP-CV-01 | Ask DJ request routing | Ask DJ / Conversation | HA Conversation Agent | profile and backend context | Implemented | personal | Apple, Windows, Pi text, voice hosts | REUSE |
| CAP-CV-02 | Revisioned conversation history | Ask DJ / Conversation | HA Conversation Platform | profile/privacy policy | Implemented | personal | rich clients; Pi where authorized | REUSE |
| CAP-CV-03 | Client-message deduplication | Ask DJ / Conversation | HA Conversation Platform | authenticated request identity | Implemented | operational | all Ask DJ request clients | REUSE |
| CAP-CV-04 | Server-owned follow-ups | Ask DJ / Conversation | HA Conversation Platform | compact pending state | Implemented | personal | rich-client confirmation controls | REUSE |
| CAP-CV-05 | Safe unknown/injection fallback | Ask DJ / Conversation | HA Conversation Platform | request routing | Implemented | operational | all conversation projections | REUSE |
| CAP-CV-06 | Retry of eligible requests | Ask DJ / Conversation | HA Conversation Platform | stored retryable context | Implemented | personal | rich clients | REUSE |
| CAP-PS-01 | Music DNA opt-in | Personalization | HA Profile Platform | profile privacy policy | Implemented | personal | rich-client settings/dashboard | REUSE |
| CAP-PS-02 | Compact profile knowledge snapshots | Personalization | HA Profile Platform | opt-in, backend observation | Implemented | personal | authorized rich-client dashboard | REUSE |
| CAP-PS-03 | Privacy-safe memory writes | Personalization | HA Profile Platform | privacy mode and opt-in | Implemented | personal | no direct raw-memory projection | REUSE |
| CAP-PS-04 | Recommendation feedback | Personalization | HA Profile Platform | authorized recommendation action | Implemented | personal | rich-client bounded actions | REUSE |
| CAP-IN-01 | Track Insight generation | Insight and Discovery | HA Insight service | playback/backend metadata | Implemented | renderer-safe | Apple, Windows, Pi | REUSE |
| CAP-IN-02 | Music Discovery feed | Insight and Discovery | HA Discovery service | profile context, backend capabilities | Implemented | personal | Apple, Windows, Pi read-heavy | REUSE |
| CAP-IN-03 | Recently-played query | Insight and Discovery | HA Music Backend boundary | backend capability | Implemented | personal | rich-client informative lists | REUSE |
| CAP-IN-04 | Recommendation proposal | Insight and Discovery | HA Discovery service | profile context, backend capability | Implemented | personal | rich-client action cards | REUSE |
| CAP-VR-01 | Assist/STT integration | Voice and Response | HA Conversation Agent | HA Assist/STT | Implemented | restricted | ESP32 and Voice Interaction Hosts; Apple PTT | REUSE |
| CAP-VR-02 | Push-to-talk request intake | Voice and Response | HA Voice boundary | device/voice authorization | Implemented | operational | ESP32, Voice Interaction Hosts and Apple where supported | REUSE |
| CAP-VR-03 | Audio-response policy | Voice and Response | HA Conversation Agent | request context, HA TTS | Implemented | operational | voice and rich client responses | REUSE |
| CAP-VR-04 | Temporary DJ response media | Voice and Response | HA TTS/response service | HA TTS | Implemented | restricted | device-local response playback | REUSE |
| CAP-VR-05 | Device DJ response delivery | Voice and Response | HA device boundary | paired device local API | Implemented | operational | ESP32 device hosts | REUSE |
| CAP-DL-01 | Device pairing and token rotation | Device Lifecycle | HA Device Platform | device local API | Implemented | restricted | ESP32, Pi, Apple, Windows | REUSE |
| CAP-DL-02 | Capability discovery | Device Lifecycle | HA and device platforms | pairing/status contracts | Implemented | operational | all clients and device hosts | REUSE |
| CAP-DL-03 | Runtime network discovery | Device Lifecycle | HA Device Platform | local URL, mDNS | Implemented | operational | ESP32 and Pi; HA runtime | REUSE |
| CAP-DL-04 | BLE Wi-Fi provisioning | Device Lifecycle | ESP32 Device Host | BLE hardware | Implemented | restricted | constrained ESP32 only | REUSE |
| CAP-DL-05 | Firmware OTA | Device Lifecycle | ESP32 Device Host / HA | firmware manifest, device state | Implemented | restricted | constrained ESP32 only | REUSE |
| CAP-DL-06 | Device status and settings | Device Lifecycle | Device host / HA | paired device status | Implemented | operational | family-specific client/device UI | REUSE |
| CAP-SUP-01 | Per-install bootstrap proof | Supporting Infrastructure | Central API / HA | push registration | Implemented | restricted | Apple only | REUSE |
| CAP-SUP-02 | APNs relay | Supporting Infrastructure | Central API | per-install token | Implemented | restricted | Apple only | REUSE |
| CAP-SUP-03 | Product/onboarding publication | Supporting Infrastructure | Website | canonical product language | Implemented | renderer-safe | public web | REUSE |
| CAP-SUP-04 | Artifact distribution metadata | Supporting Infrastructure | release repositories | source release process | Implemented | operational | firmware, Pi and Apple artifacts | REUSE |

`CAP-SI` is reserved for Session Intelligence and `CAP-SUP` for Supporting
Infrastructure. The catalog contains no reused identifiers.

## Platform capability matrix

State legend: **S** Supported; **P** Planned; **IA** Intentional absence;
**PS** Platform-specific; **U** Unknown / requires evidence; **D** Deprecated.
An absence is not a defect unless the divergence register marks it for a future
decision.

| Capability bundle | HA | Apple | Windows | Pi 4-inch | Pi 10-inch | ESPHome Voice Hosts | constrained ESP32 | Universal Receiver | Central API | Website | Release/artifact repositories |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Identity and Policy | S owner | S projection | S projection | S shared projection | U | IA persistent UI | IA persistent UI | IA | IA | IA | IA |
| Playback | S owner | S controls | S controls | S bounded controls | U | S bounded voice actions | S physical controls | S renderer-safe playback projection | IA | IA | IA |
| Session Intelligence | S owner | S projection | S projection | S bounded projection | U | S interaction projection | S short projection | S renderer-safe projection | IA | IA | IA |
| Broadcast and Presentation | S owner | S consumer | S consumer | S consumer | U | S complementary audio response projection where applicable | IA visual projection | S hosted consumer | IA | IA | IA |
| Ask DJ / Conversation | S owner | S rich | S rich | S text/read-heavy | U | S inside and outside Session | IA chat history | IA | IA | IA | IA |
| Personalization | S owner | S authorized | S authorized | S privacy-limited | U | IA | IA | IA | IA | IA | IA |
| Insight and Discovery | S owner | S rich | S rich | S read-heavy | U | IA | IA | IA | IA | IA | IA |
| Voice and Response | S owner | S where supported | PS text/audio client | IA PTT | U | S | S | IA | IA | IA | IA |
| Device Lifecycle | S orchestration | PS app lifecycle | PS app lifecycle | PS appliance lifecycle | U | PS HA-managed host | S hardware lifecycle | IA | IA | IA | PS distribution |
| Supporting Infrastructure | S HA side | S bootstrap consumer | IA | IA | IA | IA | IA | IA | S relay-only | S product/onboarding surface | S artifact distribution metadata |

ESPHome Voice Interaction Hosts deliberately have no Session Flow UI, queue
browsing, artwork or rich conversation history. Those are **Intentional
absence**, not missing Voice Host projections. Their bounded interaction and
complementary audio response projections do not make them Session owners.

## Divergence and convergence register

| Divergence | Classification | Current disposition | Required future decision |
| --- | --- | --- | --- |
| ESP32 has physical controls, BLE and OTA but no personal/chat surfaces | intentional constrained profile | retain | Review only when constrained-host capability profile changes. |
| ESPHome Voice Hosts provide two-way voice but no Session/Profile ownership | platform-specific capability | retain | Assess a formal Voice Host capability profile before expansion. |
| Pi is shared/read-heavy rather than a rich personal client | intentional constrained profile | retain | Perform Pi 4-inch and Pi 10-inch assessments before new UI work. |
| Pi 10-inch projection | Unknown / requires evidence | no inference | Assess separately; do not inherit Pi 4-inch scope automatically. |
| Apple and Windows rich-client surfaces differ | missing projection / requires evidence | no automatic convergence | Atomic Apple–Windows comparison and explicit disposition. |
| Universal Receiver/VibeCast differs from paired clients | platform-specific capability | retain | Decompose receiver and VibeCast experiences before roadmap work. |
| Apple-local minigames | candidate for canonical promotion or retirement | no current promotion | Decide whether each remains an optional local feature, becomes a shared capability, or retires. |
| Historical discovery describes Profile/Runtime/Presentation as conceptual | stale documentation | superseded for current state | Preserve as dated evidence; do not use it for current planning. |
| Central API or website becoming Runtime owners | implementation inconsistency risk | prohibited by current boundary | Require Architecture Review before any scope expansion. |

## Engineering principles

### Capability-First Development

Every proposed capability begins with a **Repository Capability Assessment**:
identify the atomic capability, existing canonical owner, current projections,
dependencies, privacy class and evidence. The assessment must demonstrate the
preference `REUSE → CONFIGURE → EXTEND → NEW` before implementation is
authorized.

### Capability Decomposition

No feature, marketing term or UX bundle is an implementation unit. It must be
decomposed into atomic canonical capabilities and assessed independently.

### Platform Projection

A capability exists canonically once. Clients, Renderer Hosts and device hosts
provide role-appropriate projections. Intentional role differences do not
create parity defects.

### Multimodal Session Coordination

Multiple Interaction and Renderer Hosts may participate concurrently in one DJ
Session. The Session remains the sole coordinator of context, decisions,
canonical events and authorized actions. Hosts complement each other through
bounded input and presentation projections; they do not coordinate directly or
duplicate Session intelligence.

### Capability Convergence Review

Major increments and public-release preparation must reverse-check relevant
capabilities against this model. Each observed divergence receives one
disposition: **promote**, **retain as intentionally platform-specific**,
**converge**, or **retire**. A review records a decision; it does not itself
authorize product implementation.

## Preserved architecture boundaries

Home Assistant owns Profile/privacy, playback orchestration, Session Runtime,
Planner, Knowledge, DJMoments, Session Flow, Presentation, Broadcast,
Universal Receiver hosting, Session authorization and command authorization.
Eligible Interaction Hosts may submit an authorized Session Start Request; the
Home Assistant Runtime creates and owns the Session, resolving the request
through the existing Start Strategy model. Native clients and Pi consume
canonical contracts. Universal Receiver is browser-based, unpaired and valid
only for an authorized active Session; its session-scoped authorization applies
to that unpaired Receiver participation and never replaces registered-device
authorization for native hosts. VibeCast is an experience mode over that
contract. ESPHome Voice Interaction Hosts use the HA DJConnect Conversation
Agent for two-way interaction but own neither it nor Session intelligence.

Voice has two operating contexts. Outside an active Session, Ask DJ remains
available and may submit an authorized Session Start Request. Inside an active
Session, Ask DJ and bounded voice actions use that active Session context.
The Central API is APNs relay/minimal Apple bootstrap support only. The Website
is a standalone product, onboarding, documentation, distribution and support
surface. Release repositories remain artifact-only.

## Related planning

[`CAPABILITY_MODEL_BACKLOG.md`](CAPABILITY_MODEL_BACKLOG.md) contains the
assessment-first backlog projection. It authorizes no implementation.
