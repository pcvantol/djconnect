# Phase 12 Raspberry Pi Verification Adapter

Status: RASPBERRY_PI_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED
Date: 2026-07-12

## Executive Summary

Phase 12 implemented the thin Raspberry Pi Verification Adapter and wired it
into the existing Verification Platform without moving platform behavior into
adapter code.

The adapter is qualified for mock/unit primitive coverage, Scenario Engine
integration and planning integration. Live Raspberry Pi runtime proof is
explicitly skipped because no prepared live Pi target was configured, and the
local CLI execution attempt stopped before scenario mutation on the existing
`github_ci_status` environment gate.

Current decision:

```text
RASPBERRY_PI_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED
```

## Scope

Implemented:

- `tools/verification/raspberry_pi_adapter.py`
- `--raspberry-pi-adapter` CLI registration
- Scenario Engine routing for Raspberry Pi-only scenarios
- Raspberry Pi runtime primitive action mapping
- `PI-001` Raspberry Pi runtime smoke scenario
- Raspberry Pi adapter unit and Scenario Engine integration tests
- Scenario catalog count update

Not implemented:

- broad Raspberry Pi product scenario assertions;
- Home Assistant backend behavior inside the Pi adapter;
- profile resolver, Ask DJ or Music DNA expected behavior inside adapter code;
- destructive Pi operations;
- live Raspberry Pi hardware execution.

## Adapter Boundary

The Raspberry Pi adapter executes runtime primitives only:

- target identity validation;
- local or SSH command execution;
- launch, stop and restart commands;
- runtime metadata collection;
- local artifact metadata;
- sanitized log collection;
- screenshot evidence only when a screenshot command is explicitly configured.

Scenario expected behavior remains owned by canonical scenarios, Home Assistant
backend contracts and foundation documents.

## Runtime Configuration

The adapter supports configuration through:

```text
DJCONNECT_VERIFICATION_PI_TARGET_JSON
DJCONNECT_VERIFICATION_PI_EVIDENCE_DIR
DJCONNECT_VERIFICATION_PI_TIMEOUT
DJCONNECT_VERIFICATION_PI_ALLOW_SSH
DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE
```

SSH execution fails closed unless `DJCONNECT_VERIFICATION_PI_ALLOW_SSH` is
truthy. Secrets are not embedded in the target shape and command output is
redacted through the existing evidence redaction path.

## Scenario Coverage

Added:

```text
verification/scenarios/pi/PI-001_runtime_smoke_launches_collects_evidence_and_stops.yaml
```

The smoke planner now selects `PI-001` as a Raspberry Pi adapter executable
case:

```text
case_count: 46
by_platform: Apple 1, HA 44, Pi 1
PI-001 adapter: raspberry_pi
```

## Verification

Commands executed:

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli validate
/private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli plan --strategy smoke --policy smoke --format json
/private/tmp/djconnect-phase9e-venv/bin/python -m pytest tests/verification/test_raspberry_pi_adapter.py tests/verification/test_lab_requirements.py tests/verification/test_planning_engine.py
DJCONNECT_VERIFICATION_PI_TARGET_JSON='...' DJCONNECT_VERIFICATION_PI_EVIDENCE_DIR=/private/tmp/djconnect-phase12-pi/evidence /private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli --raspberry-pi-adapter execute --scenario-id PI-001
```

Results:

- Scenario validation passed: `validated 233 scenarios`.
- Smoke planning passed: 46 cases, including 1 Apple case, 44 Home Assistant
  cases and 1 Pi case.
- `PI-001` planned with adapter `raspberry_pi`.
- Focused tests passed: `21 passed`.
- Full verification tests passed: `132 passed`.
- `git diff --check` passed.
- CLI execution against a safe local fixture target stopped before scenario
  mutation on `github_ci_status`.

The execution gate failure is classified as an environment issue, not a
Raspberry Pi adapter defect:

```text
Verification stopped before scenario execution because required environment
gates failed: github_ci_status
```

Evidence:

```text
artifacts/verification/evidence/djv-20260712T055557Z-430181295a/
```

## Known Issues

- Live Raspberry Pi target JSON/SSH/hardware evidence is not configured.
- The local shell has no authenticated GitHub CLI for exact-SHA CI gating, so
  CLI execution stopped before scenario execution.
- Existing broader Pi-relevant scenarios remain future coverage. Phase 12 only
  qualifies the adapter primitive path.

## Readiness

The adapter is ready for a Raspberry Pi scenario coverage expansion phase that
first qualifies a prepared live Pi runtime or fails closed before mutation.

## Next Phase

Generated but not executed:

```text
prompts/verification/PHASE_12E_RASPBERRY_PI_SCENARIO_COVERAGE_EXPANSION.md
```

Do not begin Phase 12E automatically.
