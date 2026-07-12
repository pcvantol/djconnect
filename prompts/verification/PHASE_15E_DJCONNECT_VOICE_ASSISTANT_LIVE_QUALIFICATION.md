# Phase 15E DJConnect Voice Assistant Live Qualification

Status: Future

Objective: Qualify the DJConnect Voice Assistant Verification Adapter against
a real Home Assistant Assist / DJConnect Conversation Agent runtime without
changing adapter ownership or scenario expected behavior.

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
11. `docs/verification/reports/PHASE_15_DJCONNECT_VOICE_ASSISTANT_ADAPTER_COMPLETION.md`
12. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Scope

Execute live qualification for the Voice Assistant adapter:

- qualify or recreate the local Home Assistant Assist lab safely;
- configure a real Voice Assistant target via
  `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_TARGET_JSON`;
- require explicit live opt-in through
  `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_ALLOW_LIVE=true`;
- execute the approved Voice Assistant smoke scenario set through the Scenario
  Engine and `voice_endpoint` adapter;
- collect sanitized evidence, run metadata and environment gates;
- produce a Phase 15E live qualification report.

## Out Of Scope

Do not implement:

- Phase 16 Cross-Platform Qualification;
- new Voice Assistant product behavior;
- new Ask DJ, Assist, STT or TTS semantics;
- ESP32, Apple, Raspberry Pi or Windows adapter changes;
- Software Assurance implementation;
- Platform Baseline certification.

## Acceptance Criteria

Phase 15E is complete when:

- the HA Assist lab is qualified for the current repository SHA;
- target configuration is present and redacted in evidence;
- live execution fails closed if mandatory target or live opt-in is missing;
- at least one Voice Assistant smoke scenario executes through
  `voice_endpoint` and passes;
- live run evidence records environment gates, adapter metadata, sanitized
  logs and scenario results;
- `git diff --check` passes;
- the completion report records verification, evidence, known blockers and a
  qualification decision.

Expected decision:

```text
VOICE_ASSISTANT_LIVE_QUALIFIED
```

If live execution cannot qualify, generate a remediation prompt instead of
starting Phase 16.

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`.

If Phase 15E qualifies, generate the Phase 16 Cross-Platform Qualification
prompt and update `PROMPT_INDEX.md`, but do not execute Phase 16.
