# Phase 13E-R Windows Live Target Configuration Remediation

## Objective

Remediate the Phase 13E Windows live qualification blocker by preparing a
safe, redacted Windows target configuration and rerunning `WIN-001` against
the real `pcvantol/djconnect-windows` client artifact.

Do not begin Phase 14 Cross-Platform Qualification.

## Required Context

Read, in order:

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `AGENTS.md`
3. `docs/meta/README.md`
4. `BOOTSTRAP_CODEX_VERIFICATION.md`
5. `PROMPT_INDEX.md`
6. `docs/verification/reports/PHASE_13_WINDOWS_ADAPTER_COMPLETION.md`
7. `docs/verification/reports/PHASE_13E_WINDOWS_LIVE_QUALIFICATION.md`
8. `verification/scenarios/windows/WIN-001_runtime_smoke_launches_collects_evidence_and_stops.yaml`
9. `tools/verification/windows_adapter.py`
10. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Preconditions

- Phase 13E returned `WINDOWS_LIVE_QUALIFICATION_BLOCKED`.
- Windows is available through Parallels or an approved local Windows target.
- A real `pcvantol/djconnect-windows` artifact or checkout is available.
- Evidence storage is configured outside production user data.
- `windows_dotnet_maintenance` must pass before live scenario execution; every
  Windows runtime lab run updates/restores .NET MAUI workloads inside the
  Windows VM before `WIN-001`.
- No secrets, tokens, raw prompts, raw audio, Ask DJ history or Music DNA
  contents may be written into target JSON, logs or reports.

## Scope

In scope:

- preparing or documenting the redacted
  `DJCONNECT_VERIFICATION_WINDOWS_TARGET_JSON`
- configuring launch, stop, log and optional metadata commands for the real
  Windows client artifact
- executing `WIN-001` through `windows_native_arm64`
- collecting durable evidence
- updating Phase 13E remediation reports, backlog and prompt index

Out of scope:

- Phase 14 Cross-Platform Qualification
- Phase 15 Platform Test Coverage Improvement
- Software Assurance implementation
- broad Windows product behavior assertions
- Mac Catalyst build or runtime qualification
- UI automation driver selection
- modifying sibling repository source unless explicitly requested

## Required Verification

Run:

```bash
python -m tools.verification.cli validate --scenario-id WIN-001
python -m pytest tests/verification/test_windows_adapter.py tests/verification/test_planning_engine.py
DJCONNECT_VERIFICATION_WINDOWS_TARGET_JSON='...' DJCONNECT_VERIFICATION_EVIDENCE_DIR=artifacts/verification/evidence python -m tools.verification.cli --windows-adapter execute --scenario-id WIN-001
git diff --check
```

If live execution remains blocked, classify the blocker and update the report
without advancing phases.

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`.

Expected outputs:

- remediation report under `docs/verification/reports/`
- updated `PROMPT_INDEX.md`
- updated `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- persisted evidence under `artifacts/verification/evidence/`
- explicit qualification decision
- next prompt generated only if the phase qualifies or a different remediation
  is required

Stop after this phase. Do not begin Phase 14 automatically.
