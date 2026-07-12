# Phase 14 Cross-Platform Qualification

## Objective

Qualify the currently prepared DJConnect platform runtime set across Home
Assistant, Apple, Raspberry Pi and Windows using the canonical Verification
Program evidence model.

Do not begin Phase 15 Platform Test Coverage Improvement.

## Required Context

Read, in order:

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `AGENTS.md`
3. `docs/meta/README.md`
4. `BOOTSTRAP_CODEX_VERIFICATION.md`
5. `PROMPT_INDEX.md`
6. `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION_RERUN.md`
7. `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.md`
8. `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md`
9. `docs/verification/reports/PHASE_12E_R_RASPBERRY_PI_PRODUCT_SCENARIO_MAPPING.md`
10. `docs/verification/reports/PHASE_13E_R2_WINDOWS_CLIENT_BUILD_REMEDIATION.md`
11. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Preconditions

- Phase 9V rerun returned `VERIFICATION PLATFORM QUALIFIED`.
- Home Assistant backend coverage is qualified with only non-blocking warnings.
- Apple runtime/scenario smoke coverage is qualified with only non-blocking
  warnings.
- Raspberry Pi runtime and mapped product smoke coverage is qualified.
- Phase 13E-R2 returned `WINDOWS_LIVE_QUALIFIED`.
- Evidence storage is configured outside production user data.
- No secrets, tokens, raw prompts, raw audio, Ask DJ history or Music DNA
  contents may be written into logs or reports.

## Scope

In scope:

- selecting the canonical cross-platform qualification scenario set
- verifying Home Assistant, Apple, Raspberry Pi and Windows evidence readiness
- executing or confirming required current smoke/runtime gates
- collecting durable evidence
- updating cross-platform qualification reports, backlog and prompt index

Out of scope:

- Phase 15 Platform Test Coverage Improvement
- Software Assurance implementation
- Platform Baseline v1.0 Certification
- adding broad new scenario coverage
- manipulating coverage scope
- changing platform architecture

## Required Verification

Run the scenario selection and execution commands documented by the current
Verification Program for cross-platform qualification. At minimum, include the
current smoke/runtime scenario coverage for Home Assistant, Apple, Raspberry Pi
and Windows, and run:

```bash
python -m pytest tests/verification
git diff --check
```

If any runtime or scenario gate remains blocked, classify the blocker and
generate a remediation prompt without advancing to Phase 15.

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`.

Expected outputs:

- cross-platform qualification report under `docs/verification/reports/`
- updated `PROMPT_INDEX.md`
- updated `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- persisted evidence under `artifacts/verification/evidence/`
- explicit qualification decision
- Phase 15 prompt only if cross-platform qualification passes

Stop after this phase. Do not begin Phase 15 automatically.
