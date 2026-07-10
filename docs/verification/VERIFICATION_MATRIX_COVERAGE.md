# Verification Matrix Coverage

Status: Coverage and traceability guide for Verification Matrix v1
Date: 2026-07-10

This document explains how the Verification Matrix maps to scenario
categories, platform principles, quality attributes, verification levels and
risk categories.

## Traceability By Dimension

| Matrix Dimension | Scenario Categories | Platform Principles | Quality Attributes | Verification Levels | Risk Categories |
| --- | --- | --- | --- | --- | --- |
| Client Platform | all, especially Setup, Capabilities, Hardware, Release | platform-wide parity, repository ownership | product consistency, contracts | V2-V7 | platform drift, unsupported client behavior |
| Client Variant | Setup, Ask DJ, Voice, Hardware, Localization | client-specific presentation without contract drift | UX parity, accessibility | V4-V6 | device-specific regressions |
| Screen Size | Localization, Ask DJ, Discover, Track Insight, Website | user-facing surfaces must remain usable | accessibility, layout, localization | V4, V6 | clipped text, inaccessible UI |
| Orientation | Apple, Pi, Website, Hardware | client UX adapts to runtime | layout, accessibility | V4, V5 | rotation/display failures |
| Appearance | Localization, Website, Client UI | visible UI remains readable | accessibility, visual quality | V4, V6 | low contrast, theme-only bugs |
| Localization | Localization, Setup, Privacy, Release, Website | five-language product contract | localization, accessibility | V0, V2, V4, V6 | missing keys, wrong language, layout overflow |
| Accessibility | Localization, Client UI, Website | inclusive user-facing surfaces | accessibility | V4, V6 | unusable controls or labels |
| Runtime | Setup, Capabilities, Release, Hardware | evidence strength matches gate | CI/CD, release quality | V0-V7 | debug-only pass, release artifact failure |
| Hardware | Hardware, Voice, ESP, Pi, Release | physical behavior must be proven physically | reliability, release quality | V5, V6 | simulator-only confidence |
| Operating System | Apple, Windows, Pi, Website | supported version ranges remain valid | compatibility | V4, V6 | min-version or beta drift |
| Network | Setup, Networking, Playback, Backend, Voice, Push | resilient local-first behavior | reliability, security | V3-V5 | stale pairing, bad offline behavior |
| Music Backend | Backend, Playback, Ask DJ, Discover, Track Insight | backend owns provider-specific behavior | contracts, privacy | V2, V3, V4 | provider drift, token leakage |
| Profile | Profiles, Resolver, Ask DJ, Music DNA, Privacy | Profile is primary identity | privacy, product consistency | V1-V4 | profile leakage or wrong owner |
| Session | Ask DJ, Privacy, Music DNA, Profiles | private and roaming behavior stays explicit | privacy, durability | V2-V4 | unintended persistence |
| Lifecycle | Setup, Ask DJ, Resolver, Storage, Hardware | restart/resume must preserve accepted state | reliability | V3-V5 | stale cache, lost mapping |
| Build Qualification | Release, Setup, Capabilities, Localization | release confidence uses representative artifacts | release quality, CI/CD | V6, V7 | unqualified artifact shipped |
| CI State | all | verification evidence is repeatable over time | CI/CD, reporting | V0-V7 | local-only or stale evidence |

## Coverage Rules By Scenario Category

| Category | Required Dimensions | Recommended Dimensions | Usually Not Applicable |
| --- | --- | --- | --- |
| Setup | Client Platform, Runtime, Network, Lifecycle, Build Qualification | Localization, Profile, OS | Screen Size for backend-only setup |
| Profiles | Profile, Session, Lifecycle, Client Platform | Localization for displayed profile UI | Hardware for pure resolver/store checks |
| Resolver | Profile, Session, Lifecycle, Client Platform | Voice area/room/playback zone via Voice profile | Appearance |
| Ask DJ | Client Platform, Profile, Session, Lifecycle, Backend | Localization, Network, Appearance | Hardware unless ESP/Voice PTT |
| Music DNA | Profile, Session, Backend, Lifecycle | Export/import and privacy profile overlays | Orientation |
| Discover | Profile, Backend, Client Platform | Localization, Network, Appearance | Hardware except Pi display |
| Track Insight | Backend, Lifecycle, Client Platform | Localization/display profiles | Hardware except client display checks |
| Playback | Backend, Network, Client Platform, Profile | ESP/Voice profiles for device output | Screen Size for backend-only command tests |
| Backend | Music Backend, Network, Runtime, Lifecycle | Release-equivalent build | Screen Size, Appearance |
| Privacy | Profile, Session, Evidence, Lifecycle | All platforms that store/display/relay data | None by default |
| Localization | Localization, Screen Size, Appearance, Accessibility | OS and release-equivalent build | Music Backend unless copy depends on backend |
| Capabilities | Client Platform, Runtime, Build Qualification | Network fallback, lifecycle | Localization unless capability is user-facing |
| Voice | Voice Endpoint/Apple/ESP, Profile, Session, Network | Hardware, Assist Pipeline, lifecycle | Screen Size |
| Hardware | Hardware, Network, Lifecycle, Runtime | Release-equivalent build, firmware variant | Website/browser-only dimensions |
| Networking | Network, Client Platform, Lifecycle | Profile/session where identity is involved | Appearance |
| Release | Build Qualification, Runtime, CI State, Localization | Hardware smoke for firmware | Session unless release notes mention it |
| Export | Profile, Session, Runtime, Build Qualification | Localization for UI-triggered export | Appearance for API-only export |
| Import | Profile, Session, Runtime, Lifecycle | Localization for UI-triggered import | Appearance for API-only import |

## Representative Coverage Sets

### Smoke

Use for local or CI quick checks:

- Client Platform: one target platform
- Locale: en
- Appearance: Light
- Network: WiFi or Fake Backend
- Runtime: Debug or Instrumented
- Session: Normal
- Lifecycle: Cold Start

### Nightly

Use for recurring confidence:

- Representative locales: en, nl, de
- Appearance: Light and Dark
- Network: WiFi, Offline, High Latency
- Runtime: Instrumented or Release-equivalent
- OS: Latest and Minimum Supported where practical
- Profiles: Personal, Household, Guest
- Sessions: Normal and Private

### Release Candidate

Use before release qualification:

- All five locales for user-facing surfaces
- Release-equivalent or Production Package builds
- Latest, Latest-1 and Minimum Supported OS where practical
- Critical hardware where applicable
- Spotify Direct and Music Assistant where backend behavior is in scope
- Privacy and localization profiles must be included

### Production Qualification

Use for final readiness decisions:

- Production artifacts or store builds
- Checksums/manifests/release notes
- Store/distribution metadata
- Website and release copy in all five locales
- Known limitations and blocked combinations explicitly reported

## Required Versus Representative Locale Coverage

| Scenario Type | Locale Coverage |
| --- | --- |
| Localization scenarios | all five locales |
| Public website/release/store copy | all five locales |
| Onboarding/pairing/user-facing errors | all five locales for release; representative for nightly |
| Accessibility labels | all five where localized |
| Backend protocol or machine-readable contract | Not Applicable |
| UI flows where copy is incidental | representative |

## Blocked Coverage Policy

Blocked coverage is a first-class result. It should appear in generated reports
with:

- scenario id;
- matrix profile;
- blocked dimension;
- reason;
- owner;
- recommended next phase;
- whether the block affects release readiness.

Known Phase 7 blocked areas include Apple live/APNs evidence, ESP hardware,
Pi hardware, Voice Endpoint live hardware, website adapter, release adapter
and live music backend fixtures.

## Coverage Completion

Matrix coverage is complete for a scenario only when:

1. Required dimensions have passed or are explicitly accepted as not
   applicable.
2. Blocked required dimensions are tracked as release blockers or accepted
   limitations.
3. Evidence records include selected matrix values.
4. Reduction rules are documented.
5. The result does not imply untested platforms, variants, locales, hardware or
   release artifacts passed.

## Adapter Readiness Implication

Future adapter phases should start by declaring which matrix profiles they can
execute. For example, the Home Assistant adapter can execute backend-owned
profile, resolver, HTTP, websocket, privacy, export and import cases, but it
must leave Apple, Windows, Pi, ESP32, website and release matrix cases blocked
or not applicable until those adapters exist.
