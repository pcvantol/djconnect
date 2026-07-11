# Verification Matrix Reference

Status: Canonical reference for adapter authors
Date: 2026-07-10
Runtime default: versioned Verification Platform engine with parallel execution
enabled unless an operator or policy disables it.

This reference is the compact lookup table for the canonical matrix dimensions
defined in `03A_VERIFICATION_MATRIX.md`.

## Dimension Reference

| Dimension | Values |
| --- | --- |
| Client Platform | Apple, Windows, Pi, ESP32, Voice Endpoint, Website, Release, Future Android, Future Cloud, Future Runtime |
| Client Variant | iPhone, iPad, Mac, Watch, Catalyst, Native Windows ARM64, Pi, ESP32, Voice Endpoint, Browser, Release Artifact |
| Screen Size | Compact, Regular, Large, Ultra, Landscape Display, TV, Embedded, Not Applicable |
| Orientation | Portrait, Landscape, Rotated, Not Applicable |
| Appearance | Light, Dark, High Contrast, Future Theme |
| Localization | en, nl, de, fr, es, Representative, Not Applicable |
| Accessibility | VoiceOver, TalkBack future, Dynamic Type, Large Text, Bold Text, Reduce Motion, High Contrast, Keyboard Only, Screen Reader, Switch Control, Not Applicable |
| Runtime | Debug, Instrumented, Release-equivalent, Production Artifact, Simulator, Native, Hardware |
| Hardware | Simulator, Physical Device, VM, Pi, ESP, Development Board, Production Hardware, Not Applicable |
| Operating System | Latest, Latest-1, Minimum Supported, Beta, Not Applicable |
| Network | WiFi, Ethernet, LTE, Offline, Captive Portal, Packet Loss, High Latency, Slow Network, Intermittent, VPN, Not Applicable |
| Music Backend | Spotify Direct, Music Assistant, Fake Backend, Future Backend, Not Applicable |
| Profile | Personal, Household, Guest, Kids, Shared Room, Not Applicable |
| Session | Normal, Private, Fresh, Resumed, Roaming, Not Applicable |
| Lifecycle | Cold Start, Warm Start, Resume, Background, Foreground, Restart, Killed, Crash Recovery, Not Applicable |
| Build Qualification | Instrumented, Release-equivalent, Production Package, Store Build, Not Applicable |
| CI State | Local, CI, Nightly, Release Candidate, Production Qualification |

`Latest` means the latest eligible stable runtime for the active verification
mode. Beta operating systems, Xcode beta and Home Assistant beta are not
selected by default stable qualification; they require the isolated
`future_beta` test mode and produce advisory evidence.

## Coverage State Reference

| State | Use when |
| --- | --- |
| Required | The condition is needed for the scenario or release gate to count. |
| Recommended | The condition materially improves confidence, but is not mandatory for the current gate. |
| Optional | The condition is useful for additional evidence or debugging. |
| Not Applicable | The dimension has no meaning for this scenario/platform. |
| Blocked | The condition is desired or required, but current adapters, hardware, accounts or artifacts cannot execute it. |

## Profile Reference

| Profile | Primary Purpose | Typical Verification Levels |
| --- | --- | --- |
| Apple Verification Profile | Rich Apple client parity, PTT, APNs, localization and accessibility | V2, V4, V6 |
| Windows Verification Profile | Windows client parity, native ARM64/Catalyst, DPI/scaling and secure storage | V2, V4, V6 |
| Pi Verification Profile | Ambient shared-room display, Pi runtime, update and local API behavior | V2, V4, V5, V6 |
| ESP Verification Profile | Firmware, pairing, voice, OTA, display, serial and power behavior | V2, V5, V6 |
| Voice Endpoint Verification Profile | HA Voice context resolution, Assist Pipeline, room/area/profile mapping | V3, V5 |
| Website Verification Profile | Public website layout, localization, accessibility, metadata and links | V0, V2, V4, V6 |
| Release Qualification Profile | Artifacts, manifests, checksums, notes, store/distribution readiness | V0, V6, V7 |
| Smoke Test Profile | Fast confidence on a narrow representative subset | V0, V1, V2, V3 |
| Regression Profile | Changed or high-risk behavior after implementation changes | V1, V2, V3, V4 |
| Localization Profile | Five-language parity and layout/accessibility safety | V0, V2, V4, V6 |
| Performance Profile | Startup, latency, rendering and transport timing | V3, V4, V5 |
| Privacy Profile | Profile isolation, redaction, private sessions, export/import safety | V1, V2, V3, V4, V6 |

## Scenario Category Defaults

| Scenario Category | Default Profiles | Default Matrix Emphasis |
| --- | --- | --- |
| Setup | Smoke, Apple, Windows, Pi, ESP, Voice Endpoint | platform, variant, network, lifecycle, build qualification |
| Profiles | Privacy, Regression, Apple, Windows, Pi, Voice Endpoint | profile, session, lifecycle, client platform |
| Resolver | Privacy, Voice Endpoint, Regression | profile, request source, voice area/room/playback zone, lifecycle |
| Ask DJ | Apple, Windows, Pi, Privacy, Regression | profile, session, lifecycle, locale, backend |
| Music DNA | Privacy, Apple, Windows, Regression | profile, opt-in state, session, backend, export/import |
| Discover | Apple, Windows, Pi, Regression | profile, backend, locale, network |
| Track Insight | Apple, Windows, Regression | backend, cache/lifecycle, locale where displayed |
| Playback | Apple, Windows, ESP, Voice Endpoint, Regression | backend, device/client platform, network, profile |
| Backend | Regression, Performance, Release Qualification | backend, network, lifecycle, build qualification |
| Privacy | Privacy | profile, session, evidence, logs, export/import, shared devices |
| Localization | Localization | locale, screen size, appearance, accessibility |
| Capabilities | Smoke, Regression, Apple, Windows, Pi, ESP | platform, runtime, fallback transport, build |
| Voice | Voice Endpoint, Apple, ESP, Privacy | voice hardware/runtime, profile, session, network |
| Hardware | ESP, Pi, Voice Endpoint | hardware, lifecycle, network, firmware/build |
| Networking | Smoke, Regression, Apple, Windows, Pi, ESP | network conditions, lifecycle, pairing/session |
| Release | Release Qualification, Localization, Privacy | production artifacts, checksums, release copy, store/distribution |
| Export | Privacy, Regression | profile, session, storage, build qualification |
| Import | Privacy, Regression | profile, schema/version, storage, lifecycle |

## Generated Case Record

A concrete generated test case should be identifiable without reading adapter
implementation:

```text
case_id: ASKDJ-001.apple.iphone.dark.nl.private.restart.wifi
scenario_id: ASKDJ-001
profile: Apple Verification Profile
client_platform: Apple
client_variant: iPhone
appearance: Dark
localization: nl
profile_type: Personal
session: Private
lifecycle: Restart
network: WiFi
backend: Fake Backend
build_qualification: Instrumented
coverage_state: Required
reduction_rule: critical-path
```

Adapters may choose a different machine-readable ID shape, but reports must
preserve the same semantic fields.

## Execution Metadata

Every generated case and run summary should preserve:

- `verification_runtime.name`
- `verification_runtime.version`
- `verification_runtime.schema_version`
- parallel execution mode and worker count;
- total scenario count, executed scenario count and status buckets;
- `execution_summary.total_execution_seconds`;
- host preflight outcome for local lab runs;
- runtime channel, where applicable: `stable` or `future_beta`.
