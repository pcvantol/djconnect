# Phase 14 ESP Verification Adapter

## Objective

Implement and mock-qualify the thin ESP32 Verification Adapter so the
Verification Program can prepare ESP lab runs without using broad
cross-platform qualification or mutating real hardware by default.

Target decision:

```text
ESP_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING
```

Do not begin Phase 14E ESP Live Qualification.

## Required Context

Read, in order:

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `AGENTS.md`
3. `docs/meta/README.md`
4. `BOOTSTRAP_CODEX_VERIFICATION.md`
5. `PROMPT_INDEX.md`
6. `docs/verification/00_VERIFICATION_VISION.md`
7. `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
8. `docs/verification/02_SCENARIO_SCHEMA.md`
9. `docs/verification/03_SCENARIO_CATALOG.md`
10. `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`
11. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Preconditions

- Phase 13E-R2 returned `WINDOWS_LIVE_QUALIFIED`.
- Platform Lifecycle State remains Platform Qualification.
- Platform Baseline v1.0 is not certified.
- Software Assurance implementation remains deferred.
- ESP live hardware mutation is out of scope unless a later live phase provides
  explicit target configuration and destructive-operation approval.

## Scope

In scope:

- ESP32 adapter target configuration from external environment variables
- sanitized build, firmware metadata, serial/log, reset and flash primitives
- fail-closed destructive flash behavior
- Scenario Engine routing for ESP32 hardware scenarios
- CLI adapter registration for lab runs
- focused mock/unit verification
- clean build/test folder hygiene before completion

Out of scope:

- real ESP hardware qualification
- OTA mutation against a physical device
- BLE provisioning execution
- broad cross-platform qualification
- Voice Assistant adapter work
- Software Assurance implementation
- Platform Baseline v1.0 certification

## Required Verification

Run:

```bash
python -m pytest tests/verification
git diff --check
```

Also verify the ESP hardware planner path can select ESP32 adapter cases.

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`.

Expected outputs:

- ESP adapter implementation under `tools/verification/`
- focused ESP adapter tests under `tests/verification/`
- updated prompt index and completion report
- explicit qualification decision

Stop after this phase. Do not begin Phase 14E automatically.
