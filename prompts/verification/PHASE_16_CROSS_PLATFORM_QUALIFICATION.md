# Phase 16 Cross-Platform Qualification

Status: Future

Objective: Qualify DJConnect across the currently qualified primary platform
runtimes: Home Assistant, Apple, Raspberry Pi, Windows, ESP32 and DJConnect
Voice Assistant.

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
11. Current completion reports for Phases 9E-R, 10E-R3, 12E-R, 13E-R2, 14E
    and 15E-R
12. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Scope

Execute cross-platform qualification only:

- select the approved cross-platform smoke scenario set through the canonical
  planner;
- verify exact-SHA CI status and environment gates;
- reuse only qualified runtimes or recreate clean lab state where required;
- execute selected scenarios through the appropriate thin adapters;
- collect sanitized evidence and run metadata;
- produce a Phase 16 cross-platform qualification report.

## Out Of Scope

Do not implement:

- new product behavior;
- new verification architecture;
- Software Assurance implementation;
- Platform Test Coverage Improvement;
- Platform Baseline certification.

## Acceptance Criteria

Phase 16 is complete when:

- Home Assistant, Apple, Raspberry Pi, Windows, ESP32 and Voice Assistant
  qualification evidence is linked or refreshed as required;
- the selected cross-platform scenario set executes or any blocker is
  classified before mutation;
- evidence records adapter metadata, environment gates, scenario results and
  known limitations;
- `git diff --check` passes;
- the completion report records verification, evidence, known blockers and a
  qualification decision.

Expected decision:

```text
CROSS_PLATFORM_QUALIFIED
```

If cross-platform qualification cannot pass, generate a focused remediation
prompt instead of starting Platform Test Coverage Improvement.

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`.

If Phase 16 qualifies, generate the Platform Test Coverage Improvement prompt
and update `PROMPT_INDEX.md`, but do not execute it automatically.
