# Phase 16-R Cross-Platform Qualification Environment Remediation

Status: Qualified

Objective: Remediate the Phase 16 environment blockers and rerun
cross-platform qualification across Home Assistant, Apple, Raspberry Pi,
Windows, ESP32 and DJConnect Voice Assistant.

## Required Context

Read, in order:

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `BOOTSTRAP_CODEX_VERIFICATION.md`
3. `PROMPT_INDEX.md`
4. `prompts/verification/PHASE_16_CROSS_PLATFORM_QUALIFICATION.md`
5. `docs/verification/reports/PHASE_16_CROSS_PLATFORM_QUALIFICATION.md`
6. `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`
7. `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
8. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Scope

Remediate only the Phase 16 environment blockers:

- stop and discard stale Home Assistant verification lab state safely;
- create or qualify the required current-SHA lab profile for the Phase 16
  cross-platform smoke plan;
- use the built-in prepare refresh gate:
  `python3 -m tools.verification.cli prepare --refresh-ha-lab`;
- prove the lab is safe for repository SHA
  `07178bad48d3bb8ad977e6b9070abfdf444889b4` or the then-current active SHA;
- ensure port `18123` is free or owned by the qualified verification lab;
- start the prepared Parallels `Windows 11 Home` VM;
- rerun the Windows `.NET` maintenance gate;
- rerun the canonical cross-platform smoke plan;
- execute selected scenarios through the Scenario Engine and thin adapters
  once gates pass;
- collect sanitized evidence, adapter metadata, environment gates and scenario
  results;
- update the Phase 16 completion report or create a Phase 16-R report.

## Out Of Scope

Do not implement:

- Platform Test Coverage Improvement;
- Platform Baseline certification;
- Software Assurance implementation;
- new product behavior;
- new verification architecture;
- scenario expected-result changes;
- client, firmware or backend feature changes.

## Acceptance Criteria

Phase 16-R is complete when:

- the stale HA lab blocker from Phase 16 is remediated or explicitly
  superseded by a qualified clean lab;
- the Phase 16 smoke plan is regenerated through the canonical planner;
- exact-SHA CI status is qualified or explicitly classified before mutation;
- all mandatory environment gates pass before live mutation;
- the selected cross-platform scenario set executes, or any remaining blocker
  is classified before mutation;
- Home Assistant, Apple, Raspberry Pi, Windows, ESP32 and Voice Assistant
  qualification evidence is linked or refreshed as required;
- evidence records adapter metadata, environment gates, scenario results and
  known limitations;
- `git diff --check` passes;
- the completion report records verification, evidence, known blockers and a
  qualification decision.

Expected decision:

```text
CROSS_PLATFORM_QUALIFIED
```

If cross-platform qualification still cannot pass, generate the next focused
remediation prompt instead of starting Platform Test Coverage Improvement.

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`.

If Phase 16-R qualifies, generate the Platform Test Coverage Improvement prompt
and update `PROMPT_INDEX.md`, but do not execute it automatically.
