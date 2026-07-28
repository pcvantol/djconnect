# DJConnect Qualification Register

**Status:** Canonical current Generation 2 qualification index

## Purpose and use

This register is the single current-state index of objective qualification
items remaining for active Generation 2 assessment capabilities. It is neither
a roadmap, backlog, TODO list nor implementation plan. Canonical capability
records retain detailed evidence, ownership and outcomes; this document only
makes remaining qualification status discoverable without reconstructing old PRs.

It includes only active Product Development, Platform Evolution and Public
Release Readiness-relevant capabilities. Historical Generation 1 work, closed
governance/migration work and completed capabilities with no remaining current
qualification item are intentionally absent.

## Current qualification records

| Capability | Assessment status | Qualification summary | Remaining qualification items | Disposition | Future assessment owner | Assessment trigger |
| --- | --- | --- | --- | --- | --- | --- |
| Client Connectivity & Resilience | `GO_CLIENT_CONNECTIVITY_PARTIALLY_QUALIFIED` | Existing ownership, HTTP fallback, Broadcast recovery and token/privacy boundaries are qualified. | External HTTPS behavior; timeout; HA restart recovery; reconnect; offline/cache; stale-token behavior. | Public Release Readiness | Platform Evolution / Public Release Readiness | Public Release Readiness Assessment. |
| Component Release Mode | `GO_COMPONENT_RELEASE_MODE_PARTIALLY_QUALIFIED` | Existing Repository Ownership, Platform Release Architecture, manifest/runtime and the HACS 3.3.1 component-patch record identify canonical release units and their patch, evidence and governance boundaries. The completed Component Release Qualification assessment found no canonical selected-source or dependency/evidence closure in the existing Runtime. | Establish the minimum canonical selected-source input and dependency/evidence closure before a generic fail-closed one-component path can be qualified. | Future Refinement | Platform Evolution / Platform Release | Component Release Scope Refinement, using the completed `docs/release/COMPONENT_RELEASE_QUALIFICATION_ASSESSMENT.md` evidence. |
| CMB-02 — Platform capability profiles | `GO_CMB02_PLATFORM_CAPABILITY_PROFILES_PARTIALLY_QUALIFIED` | Canonical capability-to-role-to-host profiles and intentional absences are consistent across current Concrete Hosts. | No independent CMB-02 item: its retained evidence is exactly the normalized CMB-05/CMB-06/CMB-07/CMB-12 items below. | Reconciled meta-record | Existing owning assessment | When a listed host-specific assessment is selected. |
| CMB-05 — Pi 4-inch capability profile | `GO_PI_4_INCH_PROFILE_PARTIALLY_QUALIFIED` | Compact shared native appliance role, bounded playback, read-only Ask DJ and intentional rich-surface absences are qualified. | Target-hardware compact DJ projection evidence; shared-profile visibility evidence for existing rich personal surfaces. | Retain | Platform Evolution / Pi Renderer Host | When target hardware and backend-resolved shared-profile visibility evidence are available. |
| CMB-06 — Pi 10-inch capability profile | `GO_PI_10_INCH_PROFILE_PARTIALLY_QUALIFIED` | Independent native shared wall profile with full active renderer-safe Session Flow and Presentation is qualified. | Concrete 10-inch hardware/appliance evidence; shared-wall Session Flow, Presentation and shared-profile visibility evidence. | Retain | Platform Evolution / Pi Renderer Host | When concrete 10-inch target-hardware evidence is available. |
| CMB-07 — Apple–Windows atomic convergence | `GO_CMB07_APPLE_WINDOWS_CONVERGENCE_PARTIALLY_QUALIFIED` | Shared Profile context, Playback, queue/playlists, Ask DJ text/history/actions, Discover and Track Insight are qualified; platform-native presentation is not parity work. | One normalized rich-renderer active-Session contract disposition for renderer-safe Session Flow, Direction and Current DJMoment. | Split into Future Assessment | Platform Evolution | When current Apple/Windows and canonical renderer evidence is selected for a bounded contract decision. |
| CMB-12 — Apple Native Surface Integration | `GO_CMB12_APPLE_NATIVE_SURFACES_PARTIALLY_QUALIFIED` | Existing Apple widgets, Live Activity/Dynamic Island/Lock Screen, App Icon navigation, custom links, Share Sheet, notification registration and separate Watch evidence are classified. | Apple Session-control lifecycle invocation qualification; its repeated active-Session projection item is normalized under CMB-07. | Split into Future Assessment | Platform Evolution / Apple Renderer Host | When an existing authorized lifecycle request and its privacy/authorization evidence are selected. |
| HA-ONBOARDING-001 — HA onboarding and configuration experience | Planned | The future installation-to-first-Session journey is registered but unassessed. | Connectivity evidence; CMB-05/CMB-06/CMB-07/CMB-09 host-profile evidence; Profile, pairing and authorization architecture; Public Release Readiness context. | Future Assessment | Product Development / Home Assistant Integration | After its recorded connectivity and host-profile dependencies. |
| Interactive DJMoments | Registered, assessment-first | Existing DJMoment path is preserved; no interactive capability assessment is recorded. | Reference Experience evidence and assessment of the existing DJMoment, Planner, Knowledge, command/Ask DJ and renderer-safe Presentation boundaries. | Future Assessment | Product Development | Reference Experience assessment. |
| Session Continuation | Registered, assessment-first | The invitation-back-to-active-Session family is registered; no capability assessment is recorded. | Active Session Runtime/Flow; Profile privacy; device authorization; Renderer Host classification evidence. | Future Assessment | Product Development | When its active-Session, privacy, authorization and renderer evidence is selected. |
| Apple Watch Moment-First Conversational Companion | Registered, assessment-first | The Apple Watch experience is registered; no Watch capability assessment is recorded. | Apple Premium Experience; CMB-07 evidence; existing Watch companion evidence; active Session, privacy/device authorization and renderer-safe projection assessment. | Future Assessment | Product Development / Apple Renderer Host | After relevant Apple and host-profile evidence. |

## Capability-profile assessment follow-up reconciliation

This assessment reconciles only the Remaining Qualification Items inherited
from CMB-05, CMB-06, CMB-07, CMB-09 and CMB-12. It creates no capability,
implementation authority, roadmap priority or Execution Horizon change. The
original source assessments remain immutable evidence; the table records their
current disposition.

| Original assessment and item | Original reason | Current repository evidence | Current status | Recommended disposition |
| --- | --- | --- | --- | --- |
| CMB-05 — target-hardware compact DJ projection | The Pi source established the QML contract but not the deployed 4-inch Current DJMoment result. | `PI_4_INCH_CAPABILITY_PROFILE_ASSESSMENT.md` still identifies no actual 4-inch appliance evidence; later Pi Family documentation only summarizes the same assessment. | Open. | **Retain** — future **Pi 4-inch target-hardware compact projection assessment**; require identified target hardware plus deployed Current DJMoment and bounded playback/QML evidence. |
| CMB-05 — shared-profile visibility | Rich Music DNA, Discover and conversation-history surfaces needed shared-appliance privacy reconciliation. | No later assessment supplies backend-resolved shared-profile visibility for those existing Pi 4-inch surfaces. | Open. | **Retain** — future **Pi 4-inch shared-profile visibility assessment**; require current backend profile-resolution and actual shared-appliance surface evidence. |
| CMB-06 — concrete 10-inch hardware and appliance | No source identified a 10.1-inch portrait display, touch/mount/deployment path or target-hardware operation. | The Pi repository remains evidence for shared QML/appliance foundations, not a concrete 10-inch appliance. | Open. | **Retain** — future **Pi 10-inch concrete appliance assessment**; require selected target hardware, native deployment, continuous-presence and shared-room evidence. |
| CMB-06 — shared-wall projection | Existing renderer-safe Session Flow, Presentation and shared-profile visibility needed concrete-host qualification. | No later assessment supplies concrete 10-inch shared-wall projection evidence. | Open. | **Retain** — future **Pi 10-inch shared-wall projection assessment**; require concrete-host Session Flow, Presentation and bounded shared-profile visibility evidence. |
| CMB-07 — rich-renderer active-Session contract disposition | Decide whether Session Flow, Session Direction and Current DJMoment are shared requirements, divergence or separately selected capabilities. | CMB-12 explicitly retains this same question; Apple has source evidence while Windows lacks an active-Session projection. Neither assessment resolves the cross-renderer contract. | Open, normalized once. | **Split into Future Assessment** — **Rich-renderer active-Session contract assessment**; require current Apple/Windows source and canonical renderer-projection evidence. |
| CMB-12 — repeated active-Session projection disposition | CMB-12 repeated the CMB-07 question before new Apple Session or Information payloads can be claimed. | CMB-12 names this item as retained from CMB-07; it contributes no independent qualification gap. | Closed as a duplicate register entry; the underlying question remains above. | **No Longer Applicable** as a separate item — retain only the normalized CMB-07 future assessment. |
| CMB-12 — Apple Session-control lifecycle invocation | Existing App Icon and custom links prove navigation, not an existing authorized lifecycle request with privacy/authorization boundaries. | The Apple native-surface inventory still contains no App Intent, Siri, Spotlight, Handoff or Universal Link lifecycle invocation evidence. | Open. | **Split into Future Assessment** — **Apple Session-control lifecycle invocation assessment**; require an existing authorized lifecycle request plus its privacy and authorization evidence. |

### CMB-09 confirmation

CMB-09 recorded `GO_CMB09_VOICE_HOST_PROFILE_QUALIFIED` with **no Remaining
Qualification Item and no implementation follow-up**. This reconciliation
found no later repository evidence that reopens one; CMB-09 therefore adds no
row to the active register.

### Reconciliation outcome

The five requested source assessments contained seven original open items:
four are retained, two are split into bounded Future Assessments and one
duplicate CMB-12 register entry is no longer applicable as a separate item.
No item is newly classified as Already Qualified. The register now contains six
unique active qualification items from this follow-up and remains consistent
with CMB-02's meta-level profile-validation result.

## Governance boundary

An assessment records its result, a concise qualification summary, any objective
remaining qualification items and their existing disposition in this register.
It does not create a new roadmap item, reorder the Execution Horizon or
authorize implementation. A Finalization verifies that the register reflects
the merged assessment result before it records reconciled repository state.

A future Public Release Readiness Assessment starts by reviewing every
remaining item in this register. It determines, from then-current repository
evidence, whether each item is resolved, accepted, requires implementation or
is no longer relevant. That future assessment remains the only authority for
those decisions.
