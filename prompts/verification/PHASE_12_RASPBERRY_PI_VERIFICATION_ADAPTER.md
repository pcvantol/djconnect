# Verification Program V1
## Phase 12 - Raspberry Pi Verification Adapter

Repository:

`pcvantol/djconnect`

## Context

Phase 11 returned:

```text
RASPBERRY_PI_ADAPTER_SELECTED
```

The Raspberry Pi adapter was selected because it adds the first non-Apple rich
client runtime path and proves ambient/shared-room evidence that is important
for Platform Baseline v1.0.

Do not begin this phase unless `PROMPT_INDEX.md` marks it active and the user
explicitly asks to execute it.

## Mission

Implement and qualify the thin Raspberry Pi Verification Adapter without
moving platform expected behavior into adapter code.

The adapter executes runtime primitives only. Scenarios, Home Assistant backend
contracts and foundation documents remain the source of expected behavior.

## Required Inputs

Read:

- `BOOTSTRAP_CODEX_SESSION.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md`
- `PROMPT_INDEX.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`
- `docs/verification/00_VERIFICATION_VISION.md`
- `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
- `docs/verification/02_SCENARIO_SCHEMA.md`
- `docs/verification/03_SCENARIO_CATALOG.md`
- `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
- `docs/verification/reports/PHASE_11_ADDITIONAL_PLATFORM_ADAPTER_SELECTION.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- existing adapter implementations under `tools/verification/`
- canonical scenarios under `verification/scenarios/`

## Scope

Implement:

- a thin Raspberry Pi adapter behind the existing `VerificationAdapter`
  interface;
- adapter configuration loaded from environment or prepared target JSON;
- safe runtime qualification for prepared local or SSH-based Pi targets;
- primitive actions for environment collection, launch, stop, restart, logs,
  screenshot/UI evidence when configured and artifact metadata;
- CLI registration for Raspberry Pi adapter execution;
- a first Raspberry Pi runtime smoke scenario that proves adapter primitives
  without inventing backend product assertions;
- unit tests and Scenario Engine integration tests;
- completion report, backlog, scorecard and prompt index updates.

Do not implement:

- broad Pi product scenario assertions before the runtime smoke path is
  qualified;
- Home Assistant backend behavior inside the Pi adapter;
- profile resolver, Ask DJ or Music DNA expected results inside adapter code;
- destructive Pi operations without explicit opt-in;
- production Pi state mutation without explicit operator approval.

## Runtime Configuration

The implementation should support a prepared target shape equivalent to:

```json
{
  "target_id": "djconnect-pi-local",
  "runtime": "ssh",
  "host": "example.local",
  "port": 22,
  "user": "pi",
  "app_path": "/opt/djconnect",
  "launch_command": "systemctl --user start djconnect",
  "stop_command": "systemctl --user stop djconnect",
  "log_command": "journalctl --user -u djconnect --since -2m --no-pager",
  "screenshot_command": ""
}
```

Secrets must be loaded externally by name and never serialized into evidence.

## Acceptance

Phase 12 is complete when:

- adapter code exists and follows the established thin adapter pattern;
- the CLI can register the Raspberry Pi adapter;
- the first Pi runtime smoke scenario plans as adapter-executable;
- mock/unit tests pass;
- live execution either qualifies with evidence or fails closed before
  mutation with a clear blocked report;
- evidence is redacted and persisted under the configured evidence directory;
- a Phase 12 completion report exists;
- `PROMPT_INDEX.md`, backlog and scorecard are updated;
- the next phase or remediation prompt is generated but not executed.

## Qualification Decisions

Phase 12 may report:

```text
RASPBERRY_PI_ADAPTER_QUALIFIED
RASPBERRY_PI_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED
RASPBERRY_PI_ADAPTER_NOT_QUALIFIED
RASPBERRY_PI_ADAPTER_BLOCKED
```

Use `QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED` only when adapter primitives,
planning and Scenario Engine integration are proven by mock/unit evidence and
live Pi runtime inputs are explicitly absent or deferred.

## Stop Condition

Stop after the Phase 12 completion protocol. Do not begin broad Raspberry Pi
scenario coverage or any later phase automatically.
