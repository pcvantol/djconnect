# Phase 10 Apple Adapter Completion

Status: APPLE_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED
Date: 2026-07-11
Branch: `codex/phase-10-apple-verification-adapter`

## Executive Summary

Phase 10 implemented the thin Apple Verification Adapter.

The adapter exposes Apple runtime primitives without owning scenario success,
Profile behavior, privacy logic, Music DNA behavior, localization decisions or
product assertions. It integrates with the existing Verification Execution
Environment and Scenario Engine.

Focused mock/unit verification and the broader verification regression subset
passed. Read-only local Apple tooling discovery confirmed Xcode and
CoreSimulator availability. Live Apple app install/launch/device execution was
skipped because no prepared Apple target JSON and app artifact were configured
for this repository run.

Decision:

```text
APPLE_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED
```

## Scope

Implemented runtime primitives:

- connect/initialize and disconnect/shutdown;
- discover available simulators;
- discover physical devices only when explicitly configured;
- validate target identity;
- install an app artifact on a simulator;
- uninstall an app artifact from a simulator;
- launch an app on a simulator;
- terminate an app on a simulator;
- reset app state only when destructive cleanup is explicitly enabled;
- collect app metadata;
- collect runtime metadata;
- collect sanitized adapter logs;
- collect simulator-scoped system logs;
- collect simulator screenshots when an evidence directory is configured;
- return raw structured primitive results.

Out of scope:

- app builds;
- Xcode selection;
- simulator creation/erase policy;
- physical-device provisioning;
- scenario assertions;
- UI behavior assertions;
- profile/privacy/product logic.

## Implementation

Code added or updated:

- `tools/verification/apple_adapter.py`;
- `tools/verification/environment/platforms.py`;
- `tools/verification/scenario/engine.py`;
- `tools/verification/environment/__init__.py`;
- `tools/verification/scenario/__init__.py`;
- `tests/verification/test_apple_adapter.py`;
- `docs/verification/10_APPLE_VERIFICATION_ADAPTER.md`.

The adapter consumes prepared target metadata from
`DJCONNECT_VERIFICATION_APPLE_TARGET_JSON`. It does not choose targets or build
artifacts.

The Scenario Engine now has an Apple adapter execution path for Apple-only
runtime scenarios. It still routes Home Assistant backend scenarios through the
Home Assistant adapter first.

The Execution Environment Apple controller now records Xcode version and
structured simulator metadata from `xcrun simctl list devices available --json`.

## Selected Initial Apple Scenario Set

The first approved set is adapter primitive qualification:

- simulator target discovery parsing;
- physical-device target discovery fail-closed behavior;
- target identity validation;
- app install/launch/terminate primitive modeling;
- screenshot evidence modeling;
- log/evidence redaction;
- unsupported target failure;
- Scenario Engine adapter selection;
- Execution Environment Apple metadata integration.

The broader catalog contains many scenarios with `apple.runtime`, but those
scenarios are cross-runtime product scenarios and need Phase 10E scenario
coverage expansion. Phase 10 did not invent missing client expected behavior
inside the adapter.

## Simulator And Physical-Device Coverage

Simulator coverage:

- mocked `xcrun simctl list devices available --json` parsing;
- live read-only `xcrun simctl list devices available --json` discovery;
- mocked `xcrun simctl install`;
- mocked `xcrun simctl launch`;
- mocked `xcrun simctl terminate`;
- mocked screenshot capture result and evidence item modeling.

Physical-device coverage:

- discovery is explicitly skipped unless physical execution is enabled;
- validation fails closed when a target is physical and opt-in is absent.

Live simulator/device app execution:

- simulator discovery passed;
- app install/launch/terminate skipped because no prepared Apple target JSON
  and app artifact were configured;
- physical-device execution skipped because no explicit physical-device
  opt-in/configuration was provided.

## Build Artifacts Used

No release or debug Apple app artifact was used for live execution in this
phase.

The adjacent Apple source repository was inspected at:

```text
../djconnect-app
```

Observed Apple conventions:

- project: `DJConnectApp.xcodeproj`;
- schemes include `DJConnectIOS`, `DJConnectMac` and `DJConnectWatch`;
- release script validates Swift tests and unsigned iOS/macOS builds.

## Environment Used

Repository:

```text
/Users/pcvantol/Documents/GitHub/djconnect
```

Apple client source:

```text
/Users/pcvantol/Documents/GitHub/djconnect-app
```

Python runner:

```text
python3 -m unittest
```

## Apple Tooling Versions

Read-only local Apple tooling discovery:

```text
Xcode 26.6
Build version 17F113
```

`xcrun simctl list devices available --json` succeeded outside the sandbox and
reported available iOS/iPadOS, watchOS, tvOS and xrOS simulator runtimes.

The first sandboxed `simctl` probe failed with CoreSimulator access errors
while opening `~/Library/Logs/CoreSimulator`; the read-only escalated rerun
passed. This is an environment/sandbox distinction, not an adapter failure.

## GitHub CI Status

Exact-SHA GitHub CI was not queried in this Phase 10 local implementation run.
The Phase 10 code path was verified locally with focused unit tests.

## Tests Run

Passed:

```bash
python3 -m unittest tests.verification.test_apple_adapter
```

Result:

```text
Ran 10 tests in 0.031s
OK
```

Broader verification regression:

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m pytest tests/verification
```

Result:

```text
87 passed in 27.63s
```

`pytest` was attempted first but was unavailable in the local Python 3.14
environment:

```text
No module named pytest
```

## Evidence Produced

Evidence is in-repository and reproducible:

- adapter source implementation;
- adapter documentation;
- focused unit tests;
- broader verification regression output recorded in this completion report;
- read-only Apple tooling discovery output recorded in this completion report;
- structured primitive result and evidence item modeling in tests.

No live screenshot, system log or app runtime artifact was produced because
live Apple app execution was skipped.

## Investigation

During verification, two lightweight import side effects were found:

- importing `tools.verification.environment.platforms` eagerly imported the
  full execution environment and required PyYAML;
- importing `tools.verification.scenario.engine` eagerly imported the scenario
  validator and required PyYAML.

Both were classified as execution-framework ergonomics issues and remediated
with lazy package exports. The underlying validator/lab paths still use PyYAML
where appropriate.

## Known Issues

- Live Apple simulator execution still needs configured target metadata and a
  built `.app` artifact.
- Physical-device execution remains skipped until explicitly configured.
- UI input is not implemented without a configured XCTest or accessibility
  driver.
- Watch pairing and paired watch simulator orchestration are deferred.
- Catalyst/macOS live app primitives are not yet implemented beyond metadata
  modeling and fail-closed behavior.

## Backlog And Gaps

Remaining Apple-only gaps are tracked in the Verification Platform Backlog:

- live simulator target configuration;
- live app artifact handoff from the Apple repo;
- UI automation driver selection;
- watchOS paired simulator orchestration;
- physical-device operator prerequisites;
- Phase 10E Apple scenario coverage expansion.

## Readiness

The Apple adapter is ready for Phase 10E scenario coverage expansion.

Phase 10E should select the first Apple-executable catalog scenarios, provide
or require prepared Apple targets and artifacts, and keep live tests skipped
unless local Apple runtime configuration is explicit.

## Qualification Decision

```text
APPLE_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED
```

The adapter is qualified for mock/unit primitive coverage and planning/engine
integration. Live Apple runtime proof is explicitly deferred and must not be
reported as passed until an opt-in live run produces evidence.

## Next Phase

Generate and execute Phase 10E: Apple Scenario Coverage Expansion from a clean
session.

Clean-session bootstrap command:

```text
Read BOOTSTRAP_CODEX_VERIFICATION.md and execute Phase 10E from PROMPT_INDEX.md.
```
