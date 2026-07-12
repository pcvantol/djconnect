# Phase 15E-R DJConnect Voice Assistant Live Qualification Remediation

Status: Future

Objective: Remediate the Phase 15E live qualification blockers and qualify the
DJConnect Voice Assistant Verification Adapter against a real Home Assistant
Assist / DJConnect Conversation Agent runtime.

## Required Context

Read, in order:

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `BOOTSTRAP_CODEX_VERIFICATION.md`
3. `PROMPT_INDEX.md`
4. `prompts/verification/PHASE_15E_DJCONNECT_VOICE_ASSISTANT_LIVE_QUALIFICATION.md`
5. `docs/verification/reports/PHASE_15E_DJCONNECT_VOICE_ASSISTANT_LIVE_QUALIFICATION.md`
6. `docs/verification/reports/PHASE_15_DJCONNECT_VOICE_ASSISTANT_ADAPTER_COMPLETION.md`
7. `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`
8. `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
9. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Scope

Remediate only the Phase 15E live-readiness blockers:

- stop and discard the stale local Home Assistant verification lab safely;
- always spin up a clean `ha-assist` Home Assistant lab for Voice Assistant
  live qualification; do not reuse the previous `ha-profile` lab state;
- ensure the lab profile satisfies `ha-assist` requirements for the current
  repository SHA;
- configure a real Voice Assistant target via
  `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_TARGET_JSON`;
- require explicit live opt-in through
  `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_ALLOW_LIVE=true`;
- rerun the approved Voice Assistant smoke scenario set through the Scenario
  Engine and `voice_endpoint` adapter;
- collect sanitized evidence, environment gates and scenario results;
- update the Phase 15E report or create a Phase 15E-R completion report.

## Out Of Scope

Do not implement:

- Phase 16 Cross-Platform Qualification;
- new Voice Assistant product behavior;
- new Ask DJ, Assist, STT or TTS semantics;
- ESP32, Apple, Raspberry Pi or Windows adapter changes;
- Software Assurance implementation;
- Platform Baseline certification.

## Acceptance Criteria

Phase 15E-R is complete when:

- the stale HA lab blocker from
  `artifacts/verification/evidence/djv-20260712T154526Z-1d6103fdd3/` is
  remediated or explicitly superseded by a qualified clean lab. Follow-up
  evidence `artifacts/verification/evidence/djv-20260712T155121Z-61f8232037/`
  qualified a clean `ha-assist` HA container for the current SHA and exposed
  the remaining target-config blocker. A later sidecar check found and fixed
  Piper startup configuration, after which the clean lab still needs a passing
  HA websocket doctor probe before live Voice Assistant mutation;
- the HA Assist lab is freshly created and qualified for the current repository
  SHA;
- target configuration is present and redacted in evidence;
- live opt-in is explicit;
- at least one Voice Assistant smoke scenario executes through
  `voice_endpoint` and passes;
- evidence records environment gates, adapter metadata, sanitized logs and
  scenario results;
- `git diff --check` passes;
- the completion report records verification, evidence, known blockers and a
  qualification decision.

Expected decision:

```text
VOICE_ASSISTANT_LIVE_QUALIFIED
```

If live execution still cannot qualify, generate the next focused remediation
prompt instead of starting Phase 16.

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`.

If Phase 15E-R qualifies, generate the Phase 16 Cross-Platform Qualification
prompt and update `PROMPT_INDEX.md`, but do not execute Phase 16.
