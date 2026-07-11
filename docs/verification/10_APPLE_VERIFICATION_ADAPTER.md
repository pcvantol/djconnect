# Verification Program V1
## Phase 10 - Apple Verification Adapter

Status: Implemented
Date: 2026-07-11

The Apple Verification Adapter exposes Apple runtime primitives to the
Verification Core while remaining intentionally thin.

It answers only:

> How do I perform this operation on an Apple runtime?

It never decides whether a scenario succeeded. Scenario interpretation,
assertions, privacy behavior, profile behavior and product pass/fail decisions
remain owned by the Scenario Engine and Verification Core.

## Responsibility Boundary

The adapter owns runtime execution primitives:

- target identity validation;
- simulator discovery;
- physical-device discovery when explicitly enabled;
- app artifact installation;
- app uninstallation;
- app launch;
- app termination;
- app-state reset when destructive cleanup is explicitly enabled;
- app metadata collection;
- runtime metadata collection;
- sanitized runtime operation logs;
- simulator-scoped system log collection;
- simulator screenshots when an evidence directory is configured;
- raw structured operation results.

The adapter does not own:

- Xcode discovery;
- build tooling;
- simulator creation;
- simulator erase policy;
- physical-device provisioning;
- artifact storage;
- evidence directory selection;
- CI inspection;
- cleanup policy outside verification-owned app state;
- scenario assertions;
- Profile logic;
- privacy logic;
- Music DNA logic;
- localization decisions;
- DJConnect business rules.

Those responsibilities remain with the Verification Execution Environment,
Scenario Engine and Verification Core.

## Configuration

Configuration is externalized through environment variables:

- `DJCONNECT_VERIFICATION_APPLE_TARGET_JSON`;
- `DJCONNECT_VERIFICATION_APPLE_TIMEOUT`;
- `DJCONNECT_VERIFICATION_APPLE_ALLOW_PHYSICAL`;
- `DJCONNECT_VERIFICATION_APPLE_EVIDENCE_DIR`;
- `DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE`.

`DJCONNECT_VERIFICATION_APPLE_TARGET_JSON` is a JSON object containing prepared
target metadata from the Execution Environment or operator configuration:

```json
{
  "target_id": "iphone-simulator",
  "variant": "ios",
  "runtime": "simulator",
  "name": "iPhone",
  "udid": "SIMULATOR-UDID",
  "bundle_id": "dev.djconnect.ios",
  "app_path": "/path/to/DJConnect.app"
}
```

Physical-device execution is fail-closed unless
`DJCONNECT_VERIFICATION_APPLE_ALLOW_PHYSICAL=true` is set.

Destructive app-state reset is fail-closed unless
`DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE=true` is set.

## Runtime API

Implemented primitives:

- `initialize()`;
- `shutdown()`;
- `health()`;
- `discover_simulators()`;
- `discover_physical_devices()`;
- `validate_target_identity()`;
- `install_app()`;
- `uninstall_app()`;
- `launch_app()`;
- `terminate_app()`;
- `reset_app_state()`;
- `collect_app_metadata()`;
- `collect_environment()`;
- `collect_logs()`;
- `capture_screenshot()`;
- `collect_artifact_metadata()`;
- `cleanup()`;
- `reset()`;
- `execute_action()`.

Unsupported platform-generic primitives such as REST, websocket, Home
Assistant services and UI input return structured `CapabilityUnavailable`
results instead of pretending to succeed.

## Execution Environment Integration

The Execution Environment remains responsible for Apple tooling discovery. Its
Apple platform controller records:

- `xcodebuild` path;
- `xcrun` path;
- Xcode version where available;
- available simulator metadata from `xcrun simctl list devices available
  --json`;
- physical-device discovery as skipped unless explicitly configured.

The adapter consumes a prepared target and performs operations against it. It
does not choose the target, build the app or create simulators.

## Scenario Engine Integration

The Scenario Engine can execute Apple-only scenarios through the `apple`
adapter when scenarios declare Apple platforms or Apple runtime capabilities.
For the initial primitive set it expands Apple runtime requirements into:

- collect runtime environment;
- discover simulators;
- validate target identity;
- collect app metadata;
- install app;
- launch app;
- collect logs;
- terminate app.

Scenario pass/fail remains owned by the Scenario Engine. The adapter only
returns primitive success, failure and raw structured data.

## Evidence And Redaction

Every adapter operation records:

- timestamp;
- operation name;
- target ID;
- client variant;
- duration;
- redacted command;
- return code;
- redacted output;
- structured data.

Redaction covers keys and command parts containing:

- `token`;
- `password`;
- `secret`;
- `proof`;
- `authorization`;
- `prompt`;
- `history`;
- `memory`;
- `raw_audio`.

Screenshots are written only when an evidence directory is configured and the
target is a simulator.

## Initial Apple Scenario Set

The first approved Phase 10 set is primitive qualification rather than broad
Apple product coverage:

- Apple adapter unit scenario fixture `APPLE-UNIT-001`;
- simulator discovery parsing;
- target identity validation;
- physical-device fail-closed behavior;
- app install/launch/terminate primitive modeling;
- screenshot evidence modeling;
- log evidence modeling;
- redaction;
- Scenario Engine adapter selection;
- Execution Environment Apple simulator metadata.

The canonical catalog already contains many scenarios requiring
`apple.runtime`, but most are cross-runtime product scenarios with Home
Assistant and Windows requirements. Phase 10 does not invent missing
client-specific expected behavior inside the adapter.

## Current Limitations

- Live simulator execution requires a prepared app artifact and target JSON.
- Physical-device execution requires explicit local configuration and remains
  skipped by default.
- UI input requires a future configured XCTest or accessibility driver.
- Watch pairing automation is not implemented in Phase 10.
- Catalyst/macOS launch support is represented in target metadata but only
  simulator command primitives are implemented in this phase.
- Broad Apple scenario coverage is deferred to Phase 10E.

## Qualification

Focused mock/unit coverage passed:

```bash
python3 -m unittest tests.verification.test_apple_adapter
```

Broader verification regression passed:

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m pytest tests/verification
```

Result:

```text
87 passed
```

Read-only local Apple discovery found Xcode 26.6 and available simulator
runtimes when `simctl` was run outside the sandbox.

Live Apple app install/launch tests were not executed in Phase 10 because no
prepared Apple target JSON and app artifact were configured for this repository
run. Skipped live tests remain skipped, not passed.
