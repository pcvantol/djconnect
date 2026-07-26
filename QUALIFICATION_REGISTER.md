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
| CMB-02 — Platform capability profiles | Planned | No profile-validation decision is recorded. | Current contract and Concrete Host capability inventory. | Future Assessment | Platform Evolution | When CMB profile evidence is selected. |
| CMB-03 — Platform-only divergences | Planned | No disposition decision is recorded for each registered divergence. | Divergence register and owner evidence. | Future Assessment | Platform Evolution | After relevant capability-profile evidence. |
| CMB-05 — Pi 4-inch capability profile | `GO_PI_4_INCH_PROFILE_PARTIALLY_QUALIFIED` | Compact shared native appliance role, bounded playback, read-only Ask DJ and intentional rich-surface absences are qualified. | Target-hardware compact DJ projection evidence; shared-profile visibility evidence for existing rich personal surfaces. | Future Assessment | Platform Evolution / Pi Renderer Host | When target hardware and backend-resolved shared-profile visibility evidence are available. |
| CMB-06 — Pi 10-inch capability profile | `GO_PI_10_INCH_PROFILE_PARTIALLY_QUALIFIED` | Independent native shared wall profile with full active renderer-safe Session Flow and Presentation is qualified. | Concrete 10-inch hardware/appliance evidence; shared-wall Session Flow, Presentation and shared-profile visibility evidence. | Future Assessment | Platform Evolution / Pi Renderer Host | When concrete 10-inch target-hardware evidence is available. |
| CMB-07 — Apple–Windows atomic convergence | `GO_CMB07_APPLE_WINDOWS_CONVERGENCE_PARTIALLY_QUALIFIED` | Shared Profile context, Playback, queue/playlists, Ask DJ text/history/actions, Discover and Track Insight are qualified; platform-native presentation is not parity work. | Rich-renderer active-Session contract disposition for renderer-safe Session Flow, Direction and Current DJMoment. | Future Assessment | Platform Evolution | When current Apple/Windows and canonical renderer evidence is selected for a bounded contract decision. |
| CMB-09 — Voice Interaction Host and constrained ESP32 profiles | Planned | No role-profile decision is recorded. | HA Voice; Session Start Request; ESP32 contract evidence. | Execution Horizon | Platform Evolution | Current Execution Horizon selection. |
| CMB-12 — Apple Native Surface Integration | Planned, dependency-gated | The family is registered; no Apple surface inventory is assessed. | Existing Apple Renderer Host surface inventory; completed CMB-05/CMB-06/CMB-07 evidence. | Execution Horizon | Platform Evolution / Apple Renderer Host | After CMB-05, CMB-06 and CMB-07. |
| HA-ONBOARDING-001 — HA onboarding and configuration experience | Planned | The future installation-to-first-Session journey is registered but unassessed. | Connectivity evidence; CMB-05/CMB-06/CMB-07/CMB-09 host-profile evidence; Profile, pairing and authorization architecture; Public Release Readiness context. | Future Assessment | Product Development / Home Assistant Integration | After its recorded connectivity and host-profile dependencies. |
| Interactive DJMoments | Registered, assessment-first | Existing DJMoment path is preserved; no interactive capability assessment is recorded. | Reference Experience evidence and assessment of the existing DJMoment, Planner, Knowledge, command/Ask DJ and renderer-safe Presentation boundaries. | Future Assessment | Product Development | Reference Experience assessment. |
| Session Continuation | Registered, assessment-first | The invitation-back-to-active-Session family is registered; no capability assessment is recorded. | Active Session Runtime/Flow; Profile privacy; device authorization; Renderer Host classification evidence. | Future Assessment | Product Development | When its active-Session, privacy, authorization and renderer evidence is selected. |
| Apple Watch Moment-First Conversational Companion | Registered, assessment-first | The Apple Watch experience is registered; no Watch capability assessment is recorded. | Apple Premium Experience; CMB-07 evidence; existing Watch companion evidence; active Session, privacy/device authorization and renderer-safe projection assessment. | Future Assessment | Product Development / Apple Renderer Host | After relevant Apple and host-profile evidence. |

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
