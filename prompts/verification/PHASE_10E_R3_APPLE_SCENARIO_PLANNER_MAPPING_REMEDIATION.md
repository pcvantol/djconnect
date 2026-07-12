# Verification Program V1
## Phase 10E-R3 - Apple Scenario Planner Mapping Remediation

Repository:

`pcvantol/djconnect`

Apple application source repository:

`pcvantol/djconnect-app`

## Context

Phase 10E retry returned:

```text
APPLE_RUNTIME_QUALIFIED_SCENARIO_SELECTION_BLOCKED
```

The mandatory Apple Runtime Qualification gate passed on the latest eligible
stable iOS simulator runtime with release-equivalent simulator build,
development signing, isolated DerivedData, install, launch, screenshot, scoped
log collection and XCTest UI healthcheck evidence.

Broad Apple scenario execution did not start because the canonical smoke
planner selected only Home Assistant cases and exposed no Apple adapter
executable scenario set.

## Mission

Remediate only the proven Phase 10E retry blocker:

1. Make the Planning Engine and Scenario Engine expose the first canonical
   Apple adapter executable scenario set after Apple runtime qualification.
2. Preserve the existing architecture boundary: scenarios define behavior,
   the planner selects executable scope and the Apple adapter remains a thin
   runtime primitive layer.
3. Execute the first approved Apple scenario set with persisted evidence.
4. Produce an updated Apple scenario coverage decision.

Do not invent Apple product expected behavior inside the adapter.
Do not start Phase 11.
Do not begin deferred Software Assurance implementation work.

## Required Inputs

Read:

- `BOOTSTRAP_CODEX_SESSION.md`
- `AGENTS.md`
- `docs/meta/README.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md`
- `PROMPT_INDEX.md`
- `prompts/verification/PHASE_10E_APPLE_SCENARIO_COVERAGE_EXPANSION.md`
- `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md`
- `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.json`
- `docs/verification/02_SCENARIO_SCHEMA.md`
- `docs/verification/03_SCENARIO_CATALOG.md`
- `docs/verification/03A_VERIFICATION_MATRIX.md`
- `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
- `docs/verification/10_APPLE_VERIFICATION_ADAPTER.md`
- canonical scenarios under `verification/scenarios/`
- `tools/verification/scenario/engine.py`
- Planning Engine implementation files under `tools/verification/`
- Apple adapter implementation files under `tools/verification/`
- current Apple client build/test conventions in `pcvantol/djconnect-app`

## Scope

Start with the smallest Apple executable scenario set that is already grounded
in canonical scenario behavior and current adapter/runtime primitives.

Allowed remediation targets:

- planner filtering or adapter selection defects that prevent Apple-capable
  scenarios from becoming executable;
- scenario-engine mapping gaps for Apple runtime primitive coverage;
- metadata/reporting gaps that hide why Apple scenarios are selected, skipped
  or blocked;
- focused canonical scenario metadata corrections when the scenario already
  describes Apple behavior but lacks executable mapping metadata.

Out of scope:

- new verification architecture subsystems;
- broad UI journey automation beyond the first approved scenario set;
- watchOS paired simulator orchestration;
- physical-device execution unless explicit local opt-in exists;
- App Store/TestFlight distribution signing;
- Software Assurance implementation epics.

## Required Work

1. Confirm Phase 10E runtime qualification evidence and prerequisites.
2. Re-run the canonical planner command and record the current Apple selection
   failure.
3. Identify whether the blocker is planner filtering, scenario metadata,
   scenario-engine mapping, adapter capability declaration or a combination.
4. Apply the narrowest remediation in the owning subsystem.
5. Run focused unit tests for the changed subsystem.
6. Run the canonical planning command and confirm an Apple adapter executable
   scenario set is selected.
7. Execute mock/unit Apple adapter coverage first.
8. Execute live simulator coverage only through the qualified Apple runtime
   configuration and only for the selected Apple scenario set.
9. Persist evidence through the existing evidence pipeline.
10. Classify any failures with the Investigator workflow.
11. Update reports, backlog, scorecard and prompt index.

## Acceptance

Phase 10E-R3 may report:

```text
APPLE_SCENARIO_COVERAGE_QUALIFIED
APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS
APPLE_SCENARIO_COVERAGE_NOT_QUALIFIED
APPLE_SCENARIO_COVERAGE_BLOCKED
```

Apple scenario coverage may be qualified only when:

- the mandatory Apple Runtime Qualification gate remains qualified or is
  explicitly rerun with passing evidence;
- the planner selects at least one Apple adapter executable scenario set from
  canonical scenarios;
- selected Apple scenarios execute through the Scenario Engine and Apple
  adapter without adapter-owned expected behavior;
- live simulator results are reported as passed only when they actually ran;
- skipped physical-device, watchOS or distribution-signing paths are recorded
  as skipped/deferred, not passed;
- evidence is persisted and redacted;
- focused tests and `git diff --check` pass;
- the Phase 10E completion report is updated with the Phase 10E-R3 result;
- backlog, scorecard and `PROMPT_INDEX.md` are current;
- the next prompt is generated but not executed.

Phase 11 may start only for `APPLE_SCENARIO_COVERAGE_QUALIFIED` or
`APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS` with every warning
explicitly non-blocking for the next platform adapter phase.

## Outputs

Update:

- `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md`
- `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.json`
- `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `PROMPT_INDEX.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md` if the clean-session active status changes

If still not qualified, generate the next narrowly scoped remediation prompt.
If qualified, generate the Phase 11 prompt and do not execute it.
