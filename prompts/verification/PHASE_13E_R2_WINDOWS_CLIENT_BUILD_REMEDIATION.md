# Phase 13E-R2 Windows Client Build Remediation And Live Qualification

## Objective

Unblock Windows live qualification by fixing the `pcvantol/djconnect-windows`
build failure discovered in Phase 13E-R, then rerun `WIN-001` against the real
Windows client runtime through the prepared Parallels target configuration.

Do not begin Phase 14 Cross-Platform Qualification.

## Required Context

Read, in order:

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `AGENTS.md`
3. `docs/meta/README.md`
4. `BOOTSTRAP_CODEX_VERIFICATION.md`
5. `PROMPT_INDEX.md`
6. `docs/verification/reports/PHASE_13E_R_WINDOWS_LIVE_TARGET_CONFIGURATION_REMEDIATION.md`
7. `verification/scenarios/windows/WIN-001_runtime_smoke_launches_collects_evidence_and_stops.yaml`
8. `tools/verification/windows_adapter.py`
9. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

Also read the relevant `pcvantol/djconnect-windows` repository bootstrap and
local implementation docs before changing sibling source.

## Preconditions

- Phase 13E-R returned `WINDOWS_LIVE_TARGET_CONFIGURED_CLIENT_BUILD_BLOCKED`.
- Windows is available through Parallels as `Windows 11 Home`.
- The Windows checkout is available inside the VM at
  `C:\Mac\Home\Documents\GitHub\djconnect-windows`.
- `windows_dotnet_maintenance` must pass before live scenario execution.
- No secrets, tokens, raw prompts, raw audio, Ask DJ history or Music DNA
  contents may be written into target JSON, logs or reports.

## Scope

In scope:

- fixing the Windows `StatusResponse` model/build mismatch in
  `pcvantol/djconnect-windows`
- resolving the Windows VM Git safe-directory metadata warning if needed for
  reliable evidence
- rebuilding the Windows client for `net10.0-windows10.0.19041.0`
- rerunning `WIN-001` through `windows_native_arm64`
- collecting durable evidence
- updating Phase 13E-R2 reports, backlog and prompt index

Out of scope:

- Phase 14 Cross-Platform Qualification
- Phase 15 Platform Test Coverage Improvement
- Software Assurance implementation
- broad Windows product behavior assertions
- Mac Catalyst build or runtime qualification
- UI automation driver selection

## Required Verification

Run:

```bash
python -m tools.verification.cli validate --scenario-id WIN-001
python -m pytest tests/verification/test_windows_adapter.py tests/verification/test_planning_engine.py
DJCONNECT_VERIFICATION_WINDOWS_TARGET_JSON='...' DJCONNECT_VERIFICATION_WINDOWS_ALLOW_REMOTE=1 DJCONNECT_VERIFICATION_EVIDENCE_DIR=artifacts/verification/evidence python -m tools.verification.cli --windows-adapter execute --scenario-id WIN-001
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
