# Verification Program V1
## Phase 11 - Additional Platform Adapter Selection

Repository:

`pcvantol/djconnect`

## Context

Phase 10E-R3 returned:

```text
APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS
```

The first Apple executable scenario set now plans and executes through the
Scenario Engine and Apple adapter. Remaining Apple warnings are non-blocking
for selecting the next platform adapter.

## Mission

Select and scope the next platform adapter phase from the canonical
Verification roadmap without beginning implementation until this prompt is
explicitly executed.

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
- `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- canonical scenarios under `verification/scenarios/`

## Scope

Determine the next adapter from currently deferred platform runtimes, such as
Windows, Raspberry Pi, ESP32, Voice Endpoint, Website or Release, using:

- canonical scenario coverage need;
- available local tooling;
- runtime readiness;
- adapter boundary clarity;
- evidence value for Platform Baseline v1.0.

Do not implement the selected adapter in this selection phase unless a future
prompt explicitly defines that implementation scope.

## Acceptance

Phase 11 selection is complete when:

- the next adapter target is chosen with evidence-backed rationale;
- blocking prerequisites are listed;
- a concrete implementation prompt for the selected adapter is generated;
- `PROMPT_INDEX.md`, backlog and scorecard are updated;
- no adapter implementation has started.

## Stop Condition

Stop after generating the selected adapter implementation prompt. Do not begin
that implementation automatically.
