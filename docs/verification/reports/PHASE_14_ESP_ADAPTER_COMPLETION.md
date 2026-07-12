# Phase 14 ESP Verification Adapter Completion

Status: Completed

Decision:

```text
ESP_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING
```

## Scope

Phase 14 implemented the thin ESP32 Verification Adapter and prepared the
verification tooling for ESP lab runs. The adapter is intentionally
mock-qualified only. Live hardware execution remains Phase 14E scope.

## Implementation

- Added `tools/verification/esp32_adapter.py`.
- Added `--esp32-adapter` CLI registration.
- Added Scenario Engine routing for ESP32 hardware scenarios.
- Added ESP32 planner and adapter regression tests.
- Added canonical Phase 14 prompt for ESP adapter work.
- Removed the stale Phase 14 cross-platform prompt; cross-platform
  qualification is now Phase 16 per `PROMPT_INDEX.md`.

## Lab Readiness

The adapter reads target configuration from
`DJCONNECT_VERIFICATION_ESP32_TARGET_JSON` and evidence location from
`DJCONNECT_VERIFICATION_ESP32_EVIDENCE_DIR`.

Live serial execution requires:

```text
DJCONNECT_VERIFICATION_ESP32_ALLOW_SERIAL=true
```

Firmware flashing also requires:

```text
DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE=true
```

Without those explicit gates, the adapter fails closed before serial or flash
mutation.

## Verification

Required verification:

```text
python -m pytest tests/verification
git diff --check
```

Additional planner smoke:

```text
python -m tools.verification.cli --root /Users/pcvantol/Documents/GitHub/djconnect plan --scenario-id HARDWARE-001 --strategy hardware --policy hardware --format json
```

The planner returned ESP32 cases with `adapter: "esp32"` and required resource
`esp32`.

The verification run passed on the local repository:

```text
160 passed in 86.41s
```

Generated Python cache folders were removed before verification. The test run
re-created normal Python cache folders only.

## Blockers

No Phase 14 implementation blockers remain.

Known Phase 14E prerequisites:

- real ESP hardware target JSON;
- configured serial port;
- selected firmware build or source checkout command;
- explicit live serial opt-in;
- explicit destructive opt-in for flashing or OTA mutation;
- isolated evidence directory.

## Next Phase

Phase 14E ESP Live Qualification may start only from an explicit future
operator prompt. Do not begin it automatically.
