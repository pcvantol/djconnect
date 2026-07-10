# DJConnect Verification Matrix

Status: Canonical Verification Matrix v1
Date: 2026-07-10
Scope owner: `pcvantol/djconnect`
Applies to: all future DJConnect verification adapters and runs

## Purpose

The Scenario Catalog defines what DJConnect must prove.

The Verification Matrix defines under which conditions each scenario should be
executed.

Together they generate concrete verification cases:

```text
Scenario
  x Verification Matrix
  -> Concrete Test Cases
```

A scenario is behavior. A matrix row is environment, platform, runtime and
qualification context. Adapters execute the generated cases without changing
the scenario's expected behavior.

This document is documentation only. It does not implement adapters, execute
scenarios or add runtime features.

## Philosophy

Scenarios must stay portable and durable. They should not be copied into
Apple-specific, Windows-specific or hardware-specific variants unless the
behavior itself is different.

The matrix avoids manually creating thousands of tests. Instead, the harness
will eventually:

1. Load a scenario.
2. Select one or more verification profiles.
3. Expand the scenario across relevant matrix dimensions.
4. Reduce combinations using coverage rules.
5. Produce executable cases for adapters.
6. Preserve evidence for the exact matrix conditions used.

The matrix is canonical, but it is not exhaustive brute force. It is a
controlled model for representative, risk-based and release-critical coverage.

## Canonical Dimensions

| Dimension | Canonical Values | Purpose |
| --- | --- | --- |
| Client Platform | Apple, Windows, Pi, ESP32, Voice Endpoint, Website, Release, Future Android, Future Cloud, Future Runtime | Selects platform family and adapter ownership. |
| Client Variant | iPhone, iPad, Mac, Watch, Catalyst, Native Windows ARM64, Pi, ESP32, Voice Endpoint, Browser, Release Artifact | Selects concrete runtime or artifact shape. |
| Screen Size | Compact, Regular, Large, Ultra, Landscape Display, TV, Embedded, Not Applicable | Captures layout and rendering pressure. |
| Orientation | Portrait, Landscape, Rotated, Not Applicable | Captures rotation and fixed-display behavior. |
| Appearance | Light, Dark, High Contrast, Future Theme | Captures visual theme and contrast behavior. |
| Localization | en, nl, de, fr, es, Representative, Not Applicable | Captures canonical five-language coverage. |
| Accessibility | VoiceOver, TalkBack future, Dynamic Type, Large Text, Bold Text, Reduce Motion, High Contrast, Keyboard Only, Screen Reader, Switch Control, Not Applicable | Captures inclusive access modes. |
| Runtime | Debug, Instrumented, Release-equivalent, Production Artifact, Simulator, Native, Hardware | Captures build/runtime evidence strength. |
| Hardware | Simulator, Physical Device, VM, Pi, ESP, Development Board, Production Hardware, Not Applicable | Captures physical execution target. |
| Operating System | Latest, Latest-1, Minimum Supported, Beta, Not Applicable | Captures supported version range without hardcoding a single current version. |
| Network | WiFi, Ethernet, LTE, Offline, Captive Portal, Packet Loss, High Latency, Slow Network, Intermittent, VPN, Not Applicable | Captures connectivity and transport risk. |
| Music Backend | Spotify Direct, Music Assistant, Fake Backend, Future Backend, Not Applicable | Captures provider-specific backend behavior. |
| Profile | Personal, Household, Guest, Kids, Shared Room, Not Applicable | Captures profile ownership and privacy boundaries. |
| Session | Normal, Private, Fresh, Resumed, Roaming, Not Applicable | Captures state and persistence semantics. |
| Lifecycle | Cold Start, Warm Start, Resume, Background, Foreground, Restart, Killed, Crash Recovery, Not Applicable | Captures restart and app/device lifecycle risk. |
| Build Qualification | Instrumented, Release-equivalent, Production Package, Store Build, Not Applicable | Captures confidence level for release decisions. |
| CI State | Local, CI, Nightly, Release Candidate, Production Qualification | Captures scheduling and promotion context. |

## Localization Coverage

The canonical localization set is exactly:

```text
en
nl
de
fr
es
```

Use full coverage when the scenario validates user-facing copy, accessibility
labels, onboarding, release notes, website content, pairing, privacy copy,
error messages or layout fit.

Use representative coverage when language is present but not the primary risk.
The representative set is:

```text
en
nl
de
```

Use `Not Applicable` for protocol-only, source-only, checksum-only or
machine-readable scenarios.

Regional variants may be tested by adapters, but they must normalize to the
five canonical families in platform reports.

## Coverage States

| State | Meaning |
| --- | --- |
| Required | The scenario cannot be considered covered without this condition. |
| Recommended | The condition should be run for confidence, nightly or release flows. |
| Optional | Useful extra evidence, not required for the current gate. |
| Not Applicable | The dimension does not apply to this scenario or platform. |
| Blocked | The condition is required or desired, but no adapter, hardware, credential or environment currently exists. |

Coverage states are assigned per scenario category, verification profile and
run purpose. They are not hardcoded into scenario behavior.

## Matrix Generation

The harness should eventually expand scenarios through this pipeline:

```text
Scenario Catalog
  -> Scenario Filter
  -> Verification Profile
  -> Matrix Dimension Selection
  -> Combination Reduction
  -> Concrete Test Cases
  -> Adapter Execution
  -> Evidence and Report
```

Example:

```text
ASKDJ-001
  x Apple Verification Profile
  -> approximately 40 generated executions
```

The generated cases may cover iPhone, iPad, Mac and Watch; light and dark;
selected locales; simulator and physical device; normal and private sessions;
WiFi and offline error behavior; foreground, background and restart lifecycle.

Example:

```text
PROFILE-002
  x Pi Verification Profile
  -> approximately 18 generated executions
```

The generated cases may cover Pi hardware, shared profile and personal
profile, compact and landscape display, English/Dutch/German representative
locales, touch and remote input, restart, offline and resumed sessions.

The exact count is adapter configuration, not scenario design.

## Matrix Reduction

The matrix must remain practical. Use these reduction rules:

- Mandatory combinations always run for P0/P1 privacy, profile, pairing,
  capability and release-gate scenarios.
- Pairwise testing covers broad UI/runtime compatibility when the risk is
  interaction between dimensions rather than every full cross product.
- Risk-based selection adds extra combinations for areas with known drift,
  regressions or recent changes.
- Representative combinations prove broad platform behavior without exploding
  every screen, locale, network and OS permutation.
- Critical-path combinations run on every release candidate.
- Release combinations use release-equivalent or production artifacts only.
- Localization sampling uses all five languages for localization scenarios and
  representative locales elsewhere.
- Hardware sampling prefers production hardware for release gates and
  development boards for daily/nightly diagnostics.
- Blocked combinations stay visible in reports; they are not silently dropped.

## Reusable Verification Profiles

### Apple Verification Profile

Purpose: rich client behavior for iPhone, iPad, Mac and Watch.

Selected dimensions:

- Client Platform: Apple
- Client Variant: iPhone, iPad, Mac, Watch
- Screen Size: Compact, Regular, Large, Ultra where supported
- Orientation: Portrait and Landscape for iPhone/iPad; Not Applicable for
  Watch; Mac window sizes map to Screen Size
- Appearance: Light, Dark, High Contrast
- Localization: all five locales for localization/accessibility; representative
  for non-language scenarios
- Accessibility: VoiceOver, Dynamic Type, Large Text, Bold Text, Reduce Motion,
  High Contrast, Switch Control where supported
- Runtime: Simulator, Physical Device, Instrumented, Release-equivalent
- Hardware: Simulator and Physical Device
- OS: Latest, Latest-1, Minimum Supported, Beta for pre-release gates
- Network: WiFi, LTE where applicable, Offline, High Latency, Intermittent
- Profile: Personal, Household, Guest, Kids, Shared Room where UI supports it
- Session: Normal, Private, Fresh, Resumed, Roaming
- Lifecycle: Cold Start, Resume, Background, Foreground, Restart, Killed
- Build Qualification: Instrumented and Release-equivalent; Store Build for
  release qualification
- Special: APNs registration and delivery where notification scenarios apply

### Windows Verification Profile

Purpose: Windows client parity and native distribution confidence.

Selected dimensions:

- Client Platform: Windows
- Client Variant: Catalyst, Native Windows ARM64
- Screen Size: Regular, Large, Ultra
- Orientation: Landscape, Rotated where hardware supports it
- Appearance: Light, Dark, High Contrast
- Localization: all five for localization/accessibility; representative
  otherwise
- Accessibility: Keyboard Only, Screen Reader, Large Text, High Contrast
- Runtime: Instrumented, Release-equivalent, Native
- Hardware: VM and Native device
- OS: Latest, Latest-1, Minimum Supported, Beta where supported
- Network: WiFi, Ethernet, Offline, VPN, High Latency, Intermittent
- Profile: Personal, Household, Guest, Shared Room
- Lifecycle: Cold Start, Restart, Resume, Crash Recovery
- Build Qualification: Release-equivalent and Production Package
- Special: DPI/scaling coverage for 100 percent, 150 percent and 200 percent

### Pi Verification Profile

Purpose: Raspberry Pi ambient client and shared-room behavior.

Selected dimensions:

- Client Platform: Pi
- Client Variant: Pi
- Screen Size: Compact, Regular, Landscape Display, TV
- Orientation: Landscape, Rotated
- Appearance: Light, Dark, High Contrast where supported
- Localization: representative by default; all five for localized UI scenarios
- Accessibility: Large Text, Keyboard Only, Screen Reader where practical
- Runtime: Instrumented, Release-equivalent, Native, Hardware
- Hardware: Pi, Physical Device
- OS: Latest, Latest-1, Minimum Supported
- Network: WiFi, Ethernet, Offline, High Latency, Intermittent
- Profile: Household, Guest, Shared Room, Personal when explicitly selected
- Session: Normal, Fresh, Resumed, Roaming
- Lifecycle: Cold Start, Restart, Crash Recovery
- Special: SSH, remote input, touch input and shared profile display

### ESP32 Verification Profile

Purpose: embedded hardware, firmware, pairing, OTA, voice and device runtime.

Selected dimensions:

- Client Platform: ESP32
- Client Variant: ESP32
- Screen Size: Embedded
- Orientation: Not Applicable unless display variant rotates
- Appearance: Light, Dark or firmware-supported themes
- Localization: en and nl mandatory for firmware language behavior; all five
  only when firmware UI supports all five
- Accessibility: Not Applicable unless a firmware accessibility surface exists
- Runtime: Hardware, Instrumented firmware, Release-equivalent firmware
- Hardware: ESP, Development Board, Production Hardware
- OS: Not Applicable
- Network: WiFi, Offline, Captive Portal, Packet Loss, High Latency,
  Intermittent
- Profile: Household, Shared Room, Not Applicable for ESP-local state
- Session: Normal, Fresh, Resumed
- Lifecycle: Cold Start, Restart, Crash Recovery
- Build Qualification: Release-equivalent and Production Package for firmware
- Special: Serial, USB, OTA, battery, display variants, wake/PTT and speaker

### Voice Endpoint Verification Profile

Purpose: HA Voice Satellite and Voice Preview Edition context resolution.

Selected dimensions:

- Client Platform: Voice Endpoint
- Client Variant: Voice Endpoint
- Screen Size: Not Applicable
- Orientation: Not Applicable
- Appearance: Not Applicable
- Localization: representative for spoken/text responses; all five for
  localized voice response scenarios
- Accessibility: Voice input/output specific manual evidence where needed
- Runtime: Native, Hardware, Release-equivalent HA runtime
- Hardware: Physical voice device where required
- OS: Latest, Latest-1 and Minimum Supported HA/runtime where practical
- Network: WiFi, Ethernet, Offline, High Latency, Intermittent
- Music Backend: Spotify Direct, Music Assistant, Fake Backend
- Profile: Household, Guest, Shared Room, Personal only through explicit
  mapping
- Session: Normal, Private
- Lifecycle: Cold Start, Restart, Resume
- Special: Area, room, household, guest, private session, playback zone and
  Assist Pipeline mapping

### Website Verification Profile

Purpose: public product/docs website quality.

Selected dimensions:

- Client Platform: Website
- Client Variant: Browser
- Screen Size: Compact, Regular, Large, Ultra
- Orientation: Portrait, Landscape
- Appearance: Light, Dark, High Contrast where supported
- Localization: all five for public copy
- Accessibility: Keyboard Only, Screen Reader, High Contrast, Reduce Motion
- Runtime: Production Artifact, Release-equivalent
- Hardware: Not Applicable
- OS: Latest and Latest-1 browser platforms
- Network: WiFi, Slow Network, Offline for cached pages where applicable
- Build Qualification: Production Package
- CI State: CI, Nightly, Release Candidate, Production Qualification

### Release Qualification Profile

Purpose: release artifacts, notes, manifests, checksums and distribution
readiness.

Selected dimensions:

- Client Platform: Release
- Client Variant: Release Artifact
- Runtime: Production Artifact
- Hardware: Not Applicable unless firmware hardware smoke is part of the gate
- Localization: all five for release/install/store copy
- Build Qualification: Production Package, Store Build
- CI State: Release Candidate and Production Qualification
- Network: Not Applicable except download/install smoke checks

### Smoke Test Profile

Purpose: fast confidence before deeper verification.

Selected dimensions:

- One primary platform or adapter
- Default locale `en`
- Light appearance
- Latest OS/runtime
- Fake Backend where acceptable
- Normal session
- Cold Start
- CI or Local

### Regression Profile

Purpose: run changed or high-risk scenario families after code changes.

Selected dimensions:

- Changed platform plus any contract consumers
- Representative locales
- Light and Dark
- Latest and Minimum Supported OS where practical
- Fake Backend plus one live backend for backend changes
- Normal and Private session for profile/privacy changes

### Localization Profile

Purpose: language parity and layout safety.

Selected dimensions:

- All supported client platforms with user-facing copy
- All five locales
- Compact and Large/Ultra screen sizes
- Light, Dark and High Contrast
- Large Text or Dynamic Type where supported
- Release-equivalent builds for release gates

### Performance Profile

Purpose: latency, startup, rendering and transport confidence.

Selected dimensions:

- Release-equivalent builds
- Latest OS/runtime
- WiFi, High Latency and Slow Network
- Cold Start, Warm Start and Resume
- Representative profile/session combinations
- Fake Backend for stable baselines plus live backend where provider latency is
  part of the risk

### Privacy Profile

Purpose: no leakage across profiles, logs, evidence, exports, imports or shared
devices.

Selected dimensions:

- Personal, Household, Guest, Kids and Shared Room profiles
- Normal and Private sessions
- Fresh, Resumed and Roaming sessions
- Restart and Crash Recovery where state is involved
- All platforms that can display, store, export, log or relay profile data
- Evidence redaction required for every generated case

## Platform-Specific Guidance

Apple verification must include iPhone, iPad, Mac and Watch; portrait and
landscape where supported; light and dark; all five locales for language
surfaces; Dynamic Type and VoiceOver; simulator and physical device;
release-equivalent and instrumented builds; APNs; offline and WiFi; restart,
background, foreground and killed lifecycle; and multiple iOS/watchOS versions.

Windows verification must treat Catalyst and Native Windows ARM64 separately.
It must include DPI/scaling coverage, light/dark/high contrast, all five
locales for localized UI, offline and restart behavior, VM evidence and native
device evidence.

Raspberry Pi verification must include SSH, remote input, supported screen
sizes, locales, restart, shared profile behavior, touch where configured and
offline behavior.

ESP32 verification must include serial, OTA, USB, battery, WiFi, restart,
display variants, locales that firmware supports and firmware variants.

Voice Endpoint verification must include area, room, household, guest, private
session, playback zone, Assist Pipeline and offline/error behavior.

## Adapter Contract

Future adapters should record these matrix fields for every execution:

- scenario id and scenario version;
- verification profile name;
- selected matrix dimensions;
- reduction rule used;
- adapter name and version;
- repository SHA or artifact version;
- operating system/runtime version;
- build qualification;
- locale and appearance;
- profile/session/lifecycle state;
- network and backend mode;
- evidence paths and redaction status.

If an adapter cannot satisfy a required matrix condition, it must report
`Blocked`, not `Passed`.

## Acceptance

This matrix is accepted when future phases can select scenarios, select a
verification profile, expand concrete cases and report coverage without
duplicating scenario behavior.
