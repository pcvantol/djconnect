# DJConnect Verification Prompt Index

Status: canonical prompt navigation

This index tells clean Codex and AI-agent sessions which verification prompt is
active, what came before it and which evidence proves status. Chat history is
not required.

## Active Next Phase

Phase 9L has run and is not yet qualified. The active next work is to resolve
the Phase 9L blockers recorded in
`docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`, then rerun
Phase 9L doctor.

Use this clean-session prompt:

```text
Read BOOTSTRAP_CODEX_VERIFICATION.md and execute Phase 9L from PROMPT_INDEX.md.
```

## Prompt Table

| Phase | Title | Status | Canonical prompt path | Required predecessor | Output/report path | Merge requirement | Next phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Verification Vision | Complete | Historical chat prompt; reconstructed in docs | Platform Foundation | `docs/verification/00_VERIFICATION_VISION.md` | Merged to `main` | Phase 1 |
| 1 | Verification Architecture | Complete | Historical chat prompt; reconstructed in docs | Phase 0 | `docs/verification/01_VERIFICATION_ARCHITECTURE.md` | Merged to `main` | Phase 2 |
| 2 | Scenario Schema | Complete | Historical chat prompt; reconstructed in docs | Phase 1 | `docs/verification/02_SCENARIO_SCHEMA.md` | Merged to `main` | Phase 3 |
| 3 | Scenario Catalog | Complete | Historical chat prompt; reconstructed in docs | Phase 2 | `docs/verification/03_SCENARIO_CATALOG.md` | Merged to `main` | Phase 3A |
| 3A | Verification Matrix | Complete | Historical chat prompt; reconstructed in docs | Phase 3 | `docs/verification/03A_VERIFICATION_MATRIX.md` | Merged to `main` | Phase 4 |
| 4 | Verification Harness | Complete | Historical chat prompt; reconstructed in docs | Phase 3A | `docs/verification/04_VERIFICATION_HARNESS.md` | Merged to `main` | Verification Core |
| 6 | Technical Design Reconstruction | Complete | Historical chat prompt; reconstructed in docs | Platform Baseline | Technical design docs and `docs/verification/07_IMPLEMENTATION_GAP_ANALYSIS.md` references | Merged to `main` | Phase 7 |
| 7 | Platform Implementation Gap Analysis | Complete | Historical chat prompt; reconstructed in docs | Phase 6 | `docs/verification/07_IMPLEMENTATION_GAP_ANALYSIS.md` | Merged to `main` | Phase 8 |
| 8 | Verification Execution Environment | Complete | Historical chat prompt; reconstructed in docs | Phase 7 | `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md` | Merged to `main` | Phase 8A |
| 8A | Verification Data Framework | Complete | Historical chat prompt; reconstructed in docs | Phase 8 | `docs/verification/08A_VERIFICATION_DATA_FRAMEWORK.md` | Merged to `main` | Phase 8B |
| 8B | Verification Modes And Policies | Complete | Historical chat prompt; reconstructed in docs | Phase 8A | `docs/verification/08B_VERIFICATION_MODES.md`; `docs/verification/08B_VERIFICATION_POLICIES.md` | Merged to `main` | Phase 8C |
| 8C | Verification Planning Engine | Complete | Historical chat prompt; reconstructed in docs | Phase 8B | `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md` | Merged to `main` | Phase 9 |
| 9 | Home Assistant Verification Adapter | Complete | Historical chat prompt; reconstructed in docs | Phase 8C | `docs/verification/09_HOME_ASSISTANT_VERIFICATION_ADAPTER.md`; `docs/verification/reports/PHASE_09_HOME_ASSISTANT_ADAPTER_COMPLETION.md` | Merged to `main` | Phase 9V |
| 9V | Verification Platform Qualification | Not qualified | Historical chat prompt; reconstructed in report | Phase 9 | `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION.md`; `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`; `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md` | Reports committed to `main` | Phase 9R |
| 9R | Verification Platform Qualification Remediation | Remediated with external prerequisites | `prompts/verification/PHASE_09R_QUALIFICATION_REMEDIATION.md` | Phase 9V not qualified | `docs/verification/reports/PHASE_09R_QUALIFICATION_REMEDIATION.md` | PR #63 branch `docs/phase-09r-remediation-prompt-v2` | Phase 9L |
| 9L | Local HA Verification Lab | Not qualified | `prompts/verification/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md` | Phase 9R | `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md` | Merge only after review; rerun from `main` after fixes | Phase 9V rerun |
| 9V rerun | Verification Platform Qualification Rerun | Blocked pending Phase 9L | To be created only if needed after Phase 9L | Phase 9L qualified | `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION_RERUN.md` | Must merge before Phase 10 | Phase 10 |
| 10 | Apple Verification Adapter | Blocked | To be created after Phase 9V rerun qualifies the platform | Phase 9V rerun qualified | Future Phase 10 report | New PR after approval | Future adapter qualification |

## Status Rules

- `Complete` means repository evidence exists and the work has been merged or
  committed as a completed artifact.
- `Not qualified` means the phase ran and produced a negative decision.
- `Remediated with external prerequisites` means blockers were converted into
  checks or explicit prerequisites, but the platform is not yet qualified.
- `Active next phase` means a clean session should execute that prompt.
- `Blocked` means do not start the phase until the predecessor result changes.
- `Not qualified` means the phase produced required artifacts but still has
  blocking prerequisites.

Do not mark Phase 9L complete until repository evidence includes its local lab
qualification report and the final result line.
