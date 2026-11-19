# Phase 15 DJConnect Voice Assistant Verification Adapter

Status: Ready

Objective: Implement and mock-qualify the thin DJConnect Voice Assistant
Verification Adapter so the Verification Platform can execute Voice Assistant
runtime scenarios through the Scenario Engine without beginning live Voice
Assistant qualification.

## Required Context

Read, in order:

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `BOOTSTRAP_CODEX_VERIFICATION.md`
3. `PROMPT_INDEX.md`
4. `docs/verification/00_VERIFICATION_VISION.md`
5. `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
6. `docs/verification/02_SCENARIO_SCHEMA.md`
7. `docs/verification/03_SCENARIO_CATALOG.md`
8. `docs/verification/03A_VERIFICATION_MATRIX.md`
9. `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`
10. `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
11. `docs/verification/reports/PHASE_14E_ESP_LIVE_QUALIFICATION.md`
12. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Scope

Implement:

- a thin Voice Assistant verification adapter;
- CLI registration for the adapter;
- Scenario Engine routing for DJConnect Voice Assistant scenarios;
- planning integration for Voice Endpoint / Voice Assistant cases;
- focused adapter and planner tests;
- a Phase 15 completion report.

The adapter should stay a runtime primitive layer. It must not own scenario
expected behavior, Home Assistant product logic or conversation-agent
semantics.

## Out Of Scope

Do not implement:

- Phase 15E live Voice Assistant qualification;
- Phase 16 Cross-Platform Qualification;
- ESP32, Apple, Raspberry Pi or Windows adapter changes beyond shared routing
  required for Voice Assistant selection;
- Home Assistant product behavior changes unless a focused test reveals a
  genuine implementation defect required for adapter qualification;
- Software Assurance implementation;
- Platform Baseline certification.

## Acceptance Criteria

Phase 15 is complete when:

- the adapter can be registered from the CLI;
- a Voice Assistant smoke scenario routes to the adapter through the Scenario
  Engine;
- missing target configuration fails closed before live mutation;
- mock/local primitive tests pass;
- planning selects Voice Assistant scenarios with the expected adapter and
  resource metadata;
- `git diff --check` passes;
- the completion report records verification, evidence, known blockers and a
  qualification decision.

Expected decision:

```text
VOICE_ASSISTANT_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING
```

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`.

If Phase 15 qualifies, generate the Phase 15E live qualification prompt and
update `PROMPT_INDEX.md`, but do not execute Phase 15E.
