# Verification Program V1 Phase 8B - Verification Modes

Status: Implemented
Date: 2026-07-10
Scope: canonical verification modes; no adapters; no execution

## Purpose

Verification Modes define what quality attribute is being evaluated.

Scenarios define behavior. The Verification Matrix defines where behavior is
executed. The Verification Data Framework defines which values are used.
Verification Modes define the evaluation lens.

```text
Scenario
  -> Verification Matrix
  -> Verification Data
  -> Verification Mode
  -> Verification Policy
  -> Execution Plan
```

A scenario remains reusable. `PROFILE-001` can be evaluated as Functional in a
Smoke policy, Security in a Nightly policy or Performance in a Release
Qualification policy without changing the scenario.

## Mode Philosophy

Modes must not duplicate scenarios. A mode does not define a user journey or a
product rule. It defines the type of evidence, assertions, metrics and exit
criteria used to evaluate a scenario.

Modes are platform assets. Adapters may support a mode, but they do not own the
meaning of the mode.

## Relationship To Other Artifacts

| Artifact | Responsibility |
| --- | --- |
| Scenario | What behavior must hold. |
| Verification Matrix | Where and under which environment conditions behavior is executed. |
| Verification Data | With what values, payloads, boundaries and datasets behavior is exercised. |
| Verification Mode | Which quality attribute is evaluated. |
| Verification Policy | Which modes, scenarios, platforms, data profiles and matrix profiles should run. |
| Execution Environment | Prepares and restores the world around execution. |
| Platform Adapter | Performs platform-specific primitive actions. |

## Canonical Modes

The canonical mode catalog lives in:

```text
verification/modes/catalog/modes.json
```

Every mode records:

- purpose;
- scope;
- assertions;
- evidence;
- metrics;
- exit criteria;
- recommended data profiles;
- applicable scenario categories;
- required matrix dimensions;
- typical runtime;
- typical cost;
- traceability to quality attributes, platform principles and risks.

## Functional

Purpose: validate expected behavior in nominal conditions.

Functional mode focuses on happy path, core contracts, accepted platform
ownership and expected structured responses. It is the default mode for smoke,
pull request and regression verification.

Recommended data profiles: Smoke, Regression.

Typical cost: low.

## Boundary

Purpose: validate limits and edge conditions.

Boundary mode covers min, max, overflow, underflow, optional fields, required
fields, field lengths, empty values and unexpected values.

Recommended data profiles: Boundary, Regression.

Typical cost: medium.

## Security

Purpose: validate hostile input and security controls.

Security mode covers injection, authentication, authorization, secrets,
privilege, malformed payloads, unexpected encodings, header manipulation,
replay, rate limiting, prompt injection and related abuse cases.

Recommended data profiles: Security, Boundary, Chaos.

Typical cost: medium to high.

## Privacy

Purpose: validate personal data protection and redaction.

Privacy mode covers profile isolation, household separation, guest behavior,
private session behavior, data persistence, logs, diagnostics, export, secrets
and redaction.

Recommended data profiles: Security, Regression, Migration.

Typical cost: medium.

## Localization

Purpose: validate the canonical five-language contract and language stress
behavior.

Localization mode covers English, Dutch, German, French, Spanish, fallback,
missing translations, formatting, pluralization, Unicode, RTL stress, long
strings, truncation and layout.

Recommended data profiles: Localization, Accessibility.

Typical cost: medium.

## Accessibility

Purpose: validate inclusive access.

Accessibility mode covers Dynamic Type, VoiceOver, keyboard, contrast, large
text, screen reader, focus and reduced motion.

Recommended data profiles: Accessibility, Localization.

Typical cost: medium to high.

## Compatibility

Purpose: validate supported versions, clients, APIs and schema evolution.

Compatibility mode covers supported OS versions, supported clients, supported
APIs, backward compatibility, forward compatibility and migration readiness.

Recommended data profiles: Compatibility, Migration, Regression.

Typical cost: medium.

## Performance

Purpose: validate resource and latency behavior.

Performance mode covers latency, memory, CPU, storage, network, rendering,
profile resolution and Ask DJ timings.

Recommended data profiles: Performance, Regression.

Typical cost: high.

## Resilience

Purpose: validate recovery from disruption.

Resilience mode covers restart, reconnect, offline behavior, network loss,
timeout, recovery and persistence.

Recommended data profiles: Regression, Boundary, Performance.

Typical cost: medium to high.

## Chaos

Purpose: validate behavior under random and partial failures.

Chaos mode covers random failures, partial failures, service loss, storage
corruption, unexpected shutdown and random delays.

Recommended data profiles: Chaos, Security, Performance.

Typical cost: high. Not enabled by default.

## Release Qualification

Purpose: validate release readiness from release-equivalent evidence.

Release Qualification mode covers release-equivalent builds, signing,
artifacts, CI, environment metadata and critical scenarios only.

Recommended data profiles: Smoke, Regression, Localization, Privacy,
Compatibility.

Typical cost: high.

## Nightly

Purpose: validate broad, slower, practical regression coverage.

Nightly mode covers broad regression, slow tests, long-running scenarios,
stress data and cross-platform combinations.

Recommended data profiles: Regression, Boundary, Security, Localization,
Performance, Compatibility.

Typical cost: high.

## Migration

Purpose: validate state evolution.

Migration mode covers import, export, upgrade, downgrade, schema evolution and
legacy compatibility.

Recommended data profiles: Migration, Compatibility, Boundary.

Typical cost: medium.

## AI Evaluation

Purpose: reserve a future mode for AI quality evaluation.

AI Evaluation mode is not implemented yet. Future scope may include prompt
quality, LLM behavior, recommendation quality and insight quality.

Recommended data profiles: future AI-generated and curated evaluation sets.

Typical cost: unknown.

## Traceability

Every mode references:

- quality attributes;
- platform principles;
- scenario categories;
- risk categories;
- Verification Matrix dimensions;
- Verification Data profiles.

This allows future planning engines to select a mode without encoding
platform decisions in adapters.

## Acceptance

Verification Modes are canonical when future policies can select modes, modes
can select data profiles and matrix dimensions, and scenarios remain unchanged.
