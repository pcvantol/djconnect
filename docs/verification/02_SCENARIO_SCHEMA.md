# DJConnect Verification Scenario Schema

Status: Canonical scenario model  
Scope owner: `pcvantol/djconnect`  
Applies to: all future DJConnect verification scenarios  
Schema files: `verification/schema/scenario.schema.yaml`,
`verification/schema/scenario.schema.json`

## Purpose

A Scenario is the smallest reusable verification asset in DJConnect.

Scenarios describe behavior. They do not describe implementation, scripts,
test framework mechanics, adapter internals or runner commands. A scenario
states what the platform must prove, what evidence is required and which
conditions must exist before and after execution.

Scenarios are platform-owned, not repository-owned. A repository may provide
an execution path, fixture, client build or adapter capability, but the
scenario itself belongs to the DJConnect platform. This keeps shared behavior
such as Profile resolution, privacy, localization, hardware readiness and
release qualification from being duplicated or redefined per client.

The Scenario Schema exists so every future scenario can be represented in a
stable, portable and automation-ready format.

## Canonical Schema

Every scenario eventually conforms to the canonical schema in:

- `verification/schema/scenario.schema.yaml`
- `verification/schema/scenario.schema.json`

The schema includes these top-level fields:

| Field | Purpose |
| --- | --- |
| `id` | Stable scenario identifier. |
| `title` | Short human-readable name. |
| `description` | Behavior being verified. |
| `purpose` | Why the scenario exists. |
| `owner` | Platform owner or owning verification domain. |
| `category` | Canonical scenario category. |
| `subcategory` | More specific grouping within the category. |
| `priority` | Verification importance. |
| `risk` | Risk addressed by the scenario. |
| `verification_level` | V0-V7 verification level. |
| `automation_level` | Current automation maturity. |
| `required_components` | Platform components needed to execute. |
| `supported_platforms` | Platforms where the scenario applies. |
| `required_locales` | Locale coverage required by the scenario. |
| `required_build_types` | Build types accepted for execution. |
| `required_capabilities` | Platform or client capabilities needed. |
| `required_profiles` | Profile fixtures or profile classes needed. |
| `required_backends` | Music backends needed. |
| `required_devices` | Devices or device classes needed. |
| `required_environment` | Environmental prerequisites. |
| `requires` | Logical runtime capabilities and lab resources required by the scenario. |
| `preconditions` | State that must already be true. |
| `setup` | Reproducible setup before execution. |
| `steps` | Atomic behavior-level actions. |
| `assertions` | Expected checks grouped by assertion type. |
| `expected_results` | Human and machine-readable expected outcomes. |
| `cleanup` | Required cleanup and isolation behavior. |
| `timeouts` | Timing limits for setup, execution and cleanup. |
| `retry_policy` | Whether and how retry is allowed. |
| `artifacts` | Evidence artifacts the run must collect. |
| `privacy_classification` | Privacy sensitivity of scenario and evidence. |
| `destructive` | Whether the scenario mutates or destroys state. |
| `tags` | Searchable labels. |
| `estimated_duration` | Expected duration for planning. |
| `manual_actions` | Explicit human checkpoints. |
| `future_notes` | Reserved design notes for future evolution. |
| `version` | Scenario version. |
| `schema_version` | Schema version the scenario uses. |

The schema is intentionally expressive. Not every field requires a long value,
but every scenario should make its assumptions explicit.

## Runtime Requirements

Every canonical scenario declares a `requires` block. This block is the
scenario-owned description of what runtime capabilities and resources must
exist before the scenario can execute.

Scenarios declare logical requirements only. They must not name Compose files,
container names, image tags, host paths or implementation commands.

The `requires` block may include:

- `capabilities`: mandatory logical capabilities;
- `optional_capabilities`: enhancements that may increase coverage;
- `services`: logical lab services such as `homeassistant`, `whisper`,
  `piper`, `fake_music_backend` or `music_assistant`;
- `integrations`: Home Assistant integrations such as `djconnect`;
- `bootstrap`: required prepared state such as `djconnect.loaded`;
- `resources`: network, persistence, external and virtual resources;
- `hardware`: physical resources such as `esp32` or `raspberry_pi`;
- `secrets`: named credentials such as `ha.access_token`;
- `persistence`: whether the scenario needs persistent lab state;
- `exclusive_resources`: resources that cannot be shared concurrently;
- `unresolved`: explicitly unresolved requirements.

Runtime capability identifiers are defined in
`verification/lab/capabilities.yaml`. The Scenario Catalog validator fails when
a canonical scenario has no `requires` block or references an unknown
capability or lab service.

The execution engine may run independent scenarios concurrently when parallel
execution is explicitly enabled. Scenarios that declare `depends_on` or
`dependencies` run only after their dependencies pass through the scheduler.
Scenarios that declare `requires.exclusive_resources` are never placed in the
same parallel wave as another scenario using the same exclusive resource.

## Stable IDs

Scenario IDs are permanent.

Format:

```text
PREFIX-NNN
```

Rules:

- `PREFIX` is uppercase and represents a stable domain family.
- `NNN` is a three-digit sequence number.
- IDs are never renumbered.
- Deprecated scenarios stay reserved.
- A replacement scenario receives a new ID and may reference the deprecated
  ID in `future_notes`.
- IDs are platform identifiers, not repository filenames.

Examples:

- `PROFILE-001`
- `PROFILE-002`
- `ASKDJ-001`
- `DNA-004`
- `PRIVACY-002`
- `LOCALIZATION-015`
- `VOICE-007`
- `ESP-004`
- `PI-011`
- `APPLE-006`
- `WINDOWS-009`
- `EXPORT-003`
- `PERFORMANCE-004`
- `REGRESSION-008`

Common prefixes include:

| Prefix | Domain |
| --- | --- |
| `SETUP` | Setup and onboarding |
| `PROFILE` | DJConnect Profile behavior |
| `IDENTITY` | Identity and request context |
| `RESOLVER` | Profile Resolver behavior |
| `ASKDJ` | Ask DJ behavior |
| `DNA` | Music DNA behavior |
| `DISCOVER` | Discover behavior |
| `TRACK` | Track Insight behavior |
| `PLAYBACK` | Playback behavior |
| `BACKEND` | Music Backend behavior |
| `PRIVACY` | Privacy and redaction |
| `LOCALIZATION` | Localization |
| `PERFORMANCE` | Performance |
| `HARDWARE` | Hardware |
| `NETWORK` | Networking |
| `CAPABILITY` | Capability discovery |
| `RELEASE` | Release qualification |
| `REGRESSION` | Regression protection |
| `EXPORT` | Export behavior |
| `IMPORT` | Import behavior |
| `CLOUD` | Future cloud |
| `FUTURE` | Reserved future behavior |
| `VOICE` | Voice Endpoint and voice flows |
| `ESP` | ESP32 device-specific behavior |
| `PI` | Raspberry Pi behavior |
| `APPLE` | Apple client behavior |
| `WINDOWS` | Windows client behavior |

## Categories

Canonical categories are:

- `Setup`
- `Profiles`
- `Identity`
- `Resolver`
- `Ask DJ`
- `Music DNA`
- `Discover`
- `Track Insight`
- `Playback`
- `Backend`
- `Privacy`
- `Localization`
- `Performance`
- `Hardware`
- `Networking`
- `Capabilities`
- `Release`
- `Regression`
- `Export`
- `Import`
- `Cloud`
- `Future`

Categories describe platform behavior, not repository ownership. Use
`subcategory` for a narrower grouping such as `profile_resolution`,
`history_sync`, `firmware_ota`, `locale_fallback` or `artifact_integrity`.

## Verification Levels

DJConnect scenarios use levels V0 through V7.

| Level | Name | Meaning |
| --- | --- | --- |
| `V0` | Static | Validate files, schemas, metadata, catalogs, manifests and source-level constraints without executing product flows. |
| `V1` | Unit | Verify isolated logic such as resolver order, redaction or parsing. |
| `V2` | Contract | Verify producer/consumer payload, fixture, capability, API or localization contracts. |
| `V3` | Integration | Verify backend/runtime flows across multiple components. |
| `V4` | Client E2E | Verify real client user journeys and rendering behavior. |
| `V5` | Hardware | Verify physical device, audio, display, BLE, OTA, serial or power behavior. |
| `V6` | Release Qualification | Verify release-equivalent artifacts, signing, checksums, release notes, store/distribution readiness and compatibility. |
| `V7` | Production Readiness | Verify final platform readiness using evidence, known limitations, blocking issues and release promises. |

Levels may overlap. Choose the highest level that represents the primary risk
being proven.

## Automation Levels

Automation levels describe current execution maturity.

| Level | Meaning | Example |
| --- | --- | --- |
| `FULL` | Runs automatically without human intervention in a prepared environment. | Schema validation, unit fixture, contract fixture. |
| `ENVIRONMENT_DEPENDENT` | Automated once required services, accounts, hardware or credentials exist. | Live Spotify backend, hardware lab OTA check. |
| `SEMI_AUTOMATED` | Automation performs part of the scenario, but human confirmation is required. | Audio quality confirmation after generated playback. |
| `MANUAL` | Human execution is currently required. | Press physical PTT, confirm LED or vibration. |

Promotion path:

```text
MANUAL
  -> SEMI_AUTOMATED
  -> ENVIRONMENT_DEPENDENT
  -> FULL
```

Promotion should preserve the same scenario ID. The execution method changes;
the behavior being proven does not.

## Components

`required_components` declares which platform components are involved.

Supported component values include:

- `HA`
- `Apple`
- `Windows Catalyst`
- `Windows Native ARM64`
- `Pi`
- `ESP32`
- `Voice Endpoint`
- `Spotify Direct`
- `Music Assistant`
- `Website`
- `Release Repo`
- `Future Android`
- `Future Runtime`
- `Future Cloud`

A scenario may target one or many components. The component list does not
assign expected behavior to adapters; it only identifies what must participate
or be available.

## Build Types

`required_build_types` declares which build classes can satisfy the scenario.

Supported values:

- `Debug`
- `Instrumented`
- `Release-equivalent`
- `Production artifact`
- `Simulator`
- `Native`
- `Hardware`
- `Mixed`

`Debug` builds are useful for local development and diagnosis.

`Instrumented` builds expose additional verification diagnostics or hooks.

`Release-equivalent` builds are materially equivalent to what users receive
and remain authoritative for release confidence.

`Production artifact` means the actual distributed artifact or package.

`Simulator` means an emulator or simulator build is acceptable.

`Native` means platform-native execution is required.

`Hardware` means physical hardware is required.

`Mixed` means multiple build classes participate.

## Required Locales

`required_locales` declares locale coverage.

Valid values are:

- `en`
- `nl`
- `de`
- `fr`
- `es`
- `all`
- `representative`
- `not_applicable`

Some scenarios require all canonical languages, especially localization,
onboarding, public website, release copy, accessibility label and user-facing
error scenarios.

Other scenarios may require representative coverage when the behavior is not
language-specific but includes rendered UI.

Backend-only, protocol-only and machine-readable scenarios may use
`not_applicable`.

Regional variants may be tested by adapters, but scenarios normalize expected
coverage to the canonical five language families.

## Preconditions

`preconditions` describe state that must exist before execution.

They may include:

- Profiles;
- Devices;
- Mappings;
- Accounts;
- Backend;
- Music;
- Household;
- Environment;
- Hardware;
- Network;
- Locale;
- Build;
- CI.

Preconditions should be observable and reproducible. They should not rely on
private memory or unstated local knowledge.

## Setup

`setup` describes how the required state is created or selected for the run.

Setup may include:

- seed data;
- environment;
- profiles;
- devices;
- accounts;
- mock data;
- live data.

Setup should explain what must be reproducible while staying independent of a
specific runner implementation.

## Steps

`steps` are deterministic, numbered and atomic.

Each step should describe one behavior-level action. Steps must avoid
implementation details such as shell commands, adapter method names, UI
automation selectors or internal test function names.

Good step:

```text
Send an Ask DJ message from the Apple client using Peter Profile.
```

Avoid:

```text
Call adapter.apple.tap("#ask-dj-send-button").
```

## Assertions

Assertions are separated by type so evidence can be collected and reported
clearly.

Supported assertion groups:

- `backend`
- `client`
- `hardware`
- `privacy`
- `localization`
- `performance`

Backend assertions verify state, APIs, contracts, storage, resolver behavior,
backend routing and diagnostics.

Client assertions verify rendering, local cache behavior, capability use,
native UI behavior and user-facing copy.

Hardware assertions verify physical controls, audio, display, BLE, OTA,
serial, power and device runtime behavior.

Privacy assertions verify data minimization, redaction, private sessions,
shared contexts and evidence safety.

Localization assertions verify locale coverage, fallback, placeholder
consistency and absence of raw keys.

Performance assertions verify timing, responsiveness, latency, stability and
resource use.

## Expected Results

`expected_results` has both machine-readable and human-readable forms.

Machine-readable expected results use stable outcome codes, booleans, numeric
thresholds, field names or structured values.

Human-readable expected results explain what a maintainer or reviewer should
understand from the scenario.

Both are required because machines need precise checks and humans need context.

## Evidence

`artifacts` describes required evidence.

Supported evidence types include:

- `logs`
- `screenshots`
- `serial_logs`
- `requests`
- `responses`
- `environment_snapshot`
- `artifact_metadata`
- `checksums`
- `ci_results`
- `video`
- `audio`
- `memory_dumps`

Video, audio and memory dumps are allowed only where justified. They may carry
higher privacy risk and must follow `privacy_classification` and redaction
rules.

## Cleanup

`cleanup` describes how the scenario remains isolated.

Cleanup may include:

- environment cleanup;
- profile cleanup;
- cache cleanup;
- log cleanup;
- artifact cleanup;
- scenario isolation.

Cleanup should say whether state is deleted, reset, expired, retained as
evidence or intentionally left in place for a later scenario.

## Retry

`retry_policy` supports:

- `NONE`
- `ONE_RETRY`
- `CONTROLLED_RETRY`
- `MANUAL_RETRY`

`NONE` means failures are final for that run.

`ONE_RETRY` allows one automatic retry for known transient risks.

`CONTROLLED_RETRY` allows bounded retries with explicit reason, delay and
maximum attempts.

`MANUAL_RETRY` requires human decision before re-execution.

Retry must never hide a deterministic failure, data leak or destructive side
effect. Reports must record retry count and final outcome.

## Privacy Classification

`privacy_classification` describes scenario and evidence sensitivity.

Supported classifications:

- `Public`
- `Internal`
- `Contains profile data`
- `Contains Music DNA`
- `Contains Ask DJ`
- `Contains secrets`
- `Requires redaction`

Classifications may be combined. A scenario that contains profile data and
requires redaction should list both.

`Contains secrets` scenarios require special handling and should generally
avoid storing raw evidence.

## Destructive Flag

`destructive` is always explicit.

`false` means the scenario should not intentionally destroy user, profile,
device, account or release state.

`true` means destructive behavior is expected or possible. Examples include:

- factory reset;
- export overwrite;
- profile deletion;
- cache purge;
- account unlink;
- firmware rollback;
- storage migration test.

Destructive scenarios require clear setup, confirmation, cleanup and evidence
rules.

## Manual Actions

`manual_actions` records explicit human checkpoints.

Examples:

- press PTT;
- speak wakeword;
- confirm audio;
- confirm LED;
- confirm vibration;

Manual actions remain part of the scenario. They are not hidden in notes. This
lets future automation replace or reduce them without changing the scenario
behavior.

## Versioning

There are two versions:

- `schema_version`;
- `version`.

`schema_version` identifies the schema used by the scenario document.

`version` identifies the scenario itself.

Schema changes should be backward compatible whenever possible. Additive
fields are preferred. Renaming or removing fields requires a migration note
and a new schema version.

Scenario version increments when expected behavior, required evidence,
required components, preconditions, assertions or cleanup meaningfully change.
Editorial changes do not require a version bump unless they affect execution
or interpretation.

## Validation Rules

Required fields:

- `id`
- `title`
- `description`
- `purpose`
- `owner`
- `category`
- `priority`
- `risk`
- `verification_level`
- `automation_level`
- `required_components`
- `supported_platforms`
- `required_locales`
- `required_build_types`
- `preconditions`
- `setup`
- `steps`
- `assertions`
- `expected_results`
- `cleanup`
- `timeouts`
- `retry_policy`
- `artifacts`
- `privacy_classification`
- `destructive`
- `tags`
- `estimated_duration`
- `version`
- `schema_version`

Optional fields:

- `subcategory`
- `required_capabilities`
- `required_profiles`
- `required_backends`
- `required_devices`
- `required_environment`
- `manual_actions`
- `future_notes`

Forbidden combinations:

- `destructive: true` with an empty cleanup plan.
- `privacy_classification` containing `Contains secrets` without `Requires redaction`.
- `automation_level: FULL` with non-empty `manual_actions`.
- `verification_level: V5` without a hardware component or hardware device.
- `required_locales: all` mixed with individual locale values.
- `required_locales: not_applicable` mixed with locale values.
- `retry_policy.mode: NONE` with a retry count greater than zero.

ID validation:

- IDs must match `^[A-Z]+-[0-9]{3}$`.
- The prefix must be an accepted scenario family.
- IDs are globally unique.
- Deprecated IDs remain reserved.

Placeholder validation:

- User-facing localized strings referenced by a scenario must use stable keys
  or named placeholders.
- Placeholder names and counts must match across required locales.

Locale validation:

- Locale values must be one of the canonical five languages, `all`,
  `representative` or `not_applicable`.
- Scenarios with category `Localization` should normally use `all`.

Version validation:

- `schema_version` must be supported by the schema validator.
- `version` must be a positive integer.
- Scenario migrations must preserve ID history.

Schema validation:

- Scenario files must validate against the JSON or YAML schema before entering
  the Scenario Catalog.
- Schema validation proves structure, not behavior. Scenario review still
  verifies that the expected behavior matches the platform foundation.

## Future Extensions

The schema reserves room for future verification without requiring a new
platform model.

Future extensions may include:

- cloud;
- performance history;
- nightly verification;
- hardware farms;
- store validation;
- accessibility;
- security scans;
- AI evaluation.

Future fields should be additive where possible. New execution technology
should attach to the same scenario model rather than replacing scenarios with
tool-specific definitions.

## Example Scenarios

Complete examples live under:

```text
verification/schema/examples/
```

Initial examples:

- `PROFILE-001.yaml`
- `ASKDJ-001.yaml`
- `ESP-001.yaml`
- `LOCALIZATION-001.yaml`
- `VOICE-001.yaml`

These examples are schema examples, not the full Scenario Catalog.
