# Phase 13 Windows Verification Adapter

Status: `WINDOWS_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING`

Date: 2026-07-12

Branch: `codex/phase-13-windows-verification-adapter`

Base SHA: `f80b80383aa69f31ea91c79eb6fa80653218c6ec`

## Decision

Phase 13 implemented the first thin Windows Verification Adapter and qualified
it for mock/local primitive execution, CLI registration, Scenario Engine
routing and smoke planning.

Live Windows runtime qualification is not blocked by unknown availability:
the operator confirmed that Windows is available in Parallels on the local
workstation. The remaining live qualification step is to provide a prepared
Windows target JSON and commands that execute against the Parallels Windows VM
and the real `pcvantol/djconnect-windows` client artifact.

## Scope

Implemented:

- `tools/verification/windows_adapter.py`
- `--windows-adapter` CLI registration
- Scenario Engine routing for Windows-only runtime scenarios
- Planning Engine selection for Windows-only runtime capability scenarios
- `WIN-001` Windows runtime smoke scenario
- Windows adapter unit and Scenario Engine integration tests
- Windows smoke planning test coverage

Out of scope:

- Windows product behavior assertions
- UI automation driver selection
- broad shared HA/Apple/Windows product scenario remapping
- modifying `pcvantol/djconnect-windows`
- changing Coverage Baseline 1

## Ownership Mapping

The Windows adapter records the canonical Windows client repository as:

```text
pcvantol/djconnect-windows
```

The canonical adapter id is:

```text
windows_native_arm64
```

## Primitive Model

The Windows adapter executes runtime primitives only:

- `collect_environment`
- `validate_target_identity`
- `collect_app_metadata`
- `launch_app`
- `collect_logs`
- `capture_screenshot`
- `stop_app`
- `restart_app`

UI input, REST, websocket and platform service primitives fail closed until a
dedicated Windows driver or transport is selected by a later phase.

Supported target runtimes:

- `local`
- `remote`, gated by `DJCONNECT_VERIFICATION_WINDOWS_ALLOW_REMOTE`

Environment inputs:

- `DJCONNECT_VERIFICATION_WINDOWS_TARGET_JSON`
- `DJCONNECT_VERIFICATION_WINDOWS_EVIDENCE_DIR`
- `DJCONNECT_VERIFICATION_WINDOWS_TIMEOUT`
- `DJCONNECT_VERIFICATION_WINDOWS_ALLOW_REMOTE`

## Scenario Routing

`WIN-001` is the first Windows adapter-executable scenario:

```text
verification/scenarios/windows/WIN-001_runtime_smoke_launches_collects_evidence_and_stops.yaml
```

Smoke planning selects `WIN-001` as:

```text
platform: Windows
adapter: windows_native_arm64
required_hardware: windows_vm
```

The planner intentionally does not remap broad shared Home
Assistant/Apple/Windows product scenarios to the Windows adapter in Phase 13.
Those scenarios remain future Windows scenario coverage work so expected
behavior does not move into adapter primitives.

## Evidence

Mock/local adapter primitive evidence:

```text
artifacts/verification/evidence/djv-20260712T115323Z-0e7b518464/
```

Result:

```text
execute: 1 of 1 tests executed, status PASS (1 PASS), total 0.01s
```

The run used a mock-local target and recorded:

- adapter `windows_native_arm64`;
- client repository `pcvantol/djconnect-windows`;
- `WIN-001` Scenario Engine execution;
- sanitized primitive diagnostics;
- HA and Docker gates skipped because `WIN-001` does not require the HA lab;
- Windows development environment available with Parallels discovered.

An earlier sandboxed run stopped before scenario execution at
`github_ci_status` because host keychain-backed `gh` authentication was not
available inside the restricted sandbox. Host `gh auth status` passed, and the
rerun with host access passed.

## Verification Commands

```bash
python -m tools.verification.cli validate --scenario-id WIN-001
python -m pytest tests/verification/test_windows_adapter.py tests/verification/test_planning_engine.py
DJCONNECT_VERIFICATION_WINDOWS_TARGET_JSON='...' python -m tools.verification.cli --windows-adapter execute --scenario-id WIN-001
```

Final regression commands are recorded in the completion response for this
branch.

## Follow-Up

Next Windows qualification should provide a prepared Parallels Windows target
configuration that points at the real `djconnect-windows` artifact and runtime
commands, then rerun `WIN-001` through the CLI with evidence storage enabled.

Broader Windows product scenario coverage should be a later explicit phase
that maps shared rich-client scenarios to Windows execution surfaces without
placing product assertions in the adapter.
