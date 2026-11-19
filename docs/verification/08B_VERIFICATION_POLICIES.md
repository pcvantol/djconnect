# Verification Program V1 Phase 8B - Verification Policies

Status: Implemented
Date: 2026-07-10
Scope: canonical verification policies; no adapters; no execution

## Purpose

Verification Policies determine which verification work should run.

Scenarios define what behavior should hold. Modes define what is evaluated.
Policies define execution scope.

```text
Scenario
  -> Mode
  -> Policy
  -> Execution Scope
```

The same scenario can run under different policies:

```text
PROFILE-001 -> Functional -> Smoke
PROFILE-001 -> Security -> Nightly
PROFILE-001 -> Performance -> Release Candidate
```

The scenario remains unchanged.

## Policy Philosophy

Policies never redefine scenarios or modes. They compose them.

A policy decides:

- included modes;
- excluded modes;
- platforms;
- matrix profiles;
- data profiles;
- build types;
- environment requirements;
- timeout budget;
- parallelization;
- evidence level;
- approval requirements;
- blocking severity;
- exit criteria.

Policies are reusable across local development, pull requests, CI, nightly
runs, release candidates and production qualification.

## Relationship To Other Artifacts

| Artifact | Responsibility |
| --- | --- |
| Scenario | Behavior. |
| Mode | Evaluation lens. |
| Policy | Scope and gate. |
| Matrix | Environment combinations required by the policy. |
| Data Framework | Data profiles required by the policy. |
| Execution Environment | Prepares and restores the run environment. |
| Adapter | Executes primitive platform actions selected by the core. |

## Canonical Policies

The canonical policy catalog lives in:

```text
verification/policies/catalog/policies.json
```

Each policy records:

- included modes;
- excluded modes;
- included platforms;
- excluded platforms;
- required matrix profiles;
- required data profiles;
- required build types;
- required environment;
- timeout budget;
- parallelization;
- evidence level;
- approval requirement;
- blocking severity;
- exit criteria.

## Smoke

Purpose: critical only, fast feedback in a few minutes.

Smoke uses Functional mode with Smoke data and a narrow representative matrix.
It should be cheap enough for local use and early CI.

## Pull Request

Purpose: changed areas only.

Pull Request policy is dependency-aware and scenario-impact aware. It should
avoid unnecessary execution while still covering changed contracts, data,
privacy, localization and platform surfaces.

## Local Developer

Purpose: fast deterministic debugging.

Local Developer policy prioritizes repeatability, readable evidence and narrow
scope. It must avoid destructive operations unless explicitly approved.

## Regression

Purpose: broad platform-wide confidence with moderate runtime.

Regression policy composes Functional, Boundary, Privacy, Localization,
Compatibility and Resilience where practical.

## Security

Purpose: security-only verification.

Security policy includes Security and Boundary modes, injection payloads,
authentication/authorization cases, malformed payloads and hostile encodings.

## Privacy

Purpose: personal data protection.

Privacy policy includes Privacy, Boundary and Security modes for profile
isolation, shared profiles, guests, private sessions, logging, diagnostics and
export/import behavior.

## Localization

Purpose: five-language confidence.

Localization policy includes Localization and Accessibility-adjacent checks
with the canonical five languages and representative matrix profiles.

## Accessibility

Purpose: accessibility-only verification.

Accessibility policy includes Accessibility and Localization modes for client
and website surfaces that expose user-facing UI.

## Hardware

Purpose: physical device evidence.

Hardware policy includes physical-device matrix profiles for Apple, Pi, ESP32
and Voice Endpoint. It does not run without the necessary hardware environment.

## Release Candidate

Purpose: everything required before release.

Release Candidate policy uses release-equivalent builds, signed artifacts, CI
green status and blocking modes required for release confidence.

Policy composition:

```text
Release Candidate
  = Functional
  + Privacy
  + Localization
  + Accessibility
  + Compatibility
  + Resilience
  + Release Qualification
```

## Production Qualification

Purpose: final gate.

Production Qualification policy validates all blocking evidence, release
promises, manual confirmations where required and accepted limitations.

## Nightly

Purpose: everything practical.

Nightly policy includes broad regression, long-running scenarios, performance,
stress, compatibility and slow cross-platform combinations.

## Research

Purpose: experimental verification.

Research policy is non-blocking. It may include unfinished scenarios, future
AI evaluation, experimental adapters or exploratory datasets.

## Policy Composition

Policies reuse modes. A composed policy lists modes by ID and may add required
matrix/data/build constraints. It must not duplicate mode definitions.

Examples live in:

```text
verification/modes/examples/release_candidate_composition.json
```

## Blocking Severity

Policies use blocking severity to decide release readiness:

- `none` - never blocks; useful for research.
- `advisory` - reports risk but does not block.
- `warning` - requires acknowledgement.
- `blocking` - must pass or be explicitly waived.
- `release_blocking` - blocks release qualification.

## Evidence Levels

Policies use evidence levels:

- `summary` - result only.
- `structured` - machine-readable metadata and selected evidence.
- `full_redacted` - complete redacted evidence bundle.
- `manual_attestation` - human confirmation required.

## Traceability

Every policy references:

- release gates;
- development workflow;
- CI usage;
- nightly usage;
- local development usage;
- required modes;
- required matrix profiles;
- required data profiles.

This gives the future planning engine enough information to select scenarios,
modes, matrix combinations and datasets without adapter-specific decisions.

## Acceptance

Verification Policies are canonical when future planning can compose scenarios,
modes, matrix profiles and data profiles into an execution plan while scenarios
remain unchanged and adapters remain thin.
