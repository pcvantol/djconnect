# DJConnect Verification Codex Bootstrap

Status: canonical clean-session entrypoint for verification work

Use this document when a clean Codex or AI-agent session works on the
DJConnect Verification Program.

Minimal clean-session instruction:

```text
Read BOOTSTRAP_CODEX_VERIFICATION.md and execute the active phase referenced in
PROMPT_INDEX.md.
```

## Purpose

The Verification Program proves that DJConnect behaves as designed across the
Home Assistant integration, clients, firmware, hardware, release artifacts and
future runtime surfaces.

The repository is the durable source of context. Chat history is not required
and must not be treated as canonical.

## Current Status

The Verification Foundation, Core, Execution Environment, Data Framework,
Modes, Policies, Planning Engine, Home Assistant Verification Adapter and
dedicated local Home Assistant verification lab exist.

Phase 9V rerun concluded:

```text
VERIFICATION PLATFORM QUALIFIED
```

Phase 9V qualifies the Verification Platform. It does not qualify broad
DJConnect Home Assistant backend scenario coverage.

The platform is ready for Phase 9E: Home Assistant Scenario Coverage
Expansion. Phase 10 Apple Verification Adapter remains blocked until Phase 9E
returns `HOME_ASSISTANT_BACKEND_QUALIFIED` or
`HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS` with all warnings explicitly
non-blocking for Apple client work.

The active next phase is listed in `PROMPT_INDEX.md`.

## Required Reading Order

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `AGENTS.md`
3. `docs/meta/README.md`
4. `BOOTSTRAP_CODEX_VERIFICATION.md`
5. `PROMPT_INDEX.md`
6. Active prompt under `prompts/verification/`
7. `docs/verification/00_VERIFICATION_VISION.md`
8. `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
9. `docs/verification/02_SCENARIO_SCHEMA.md`
10. `docs/verification/03_SCENARIO_CATALOG.md`
11. `docs/verification/03A_VERIFICATION_MATRIX.md`
12. `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`
13. `docs/verification/08A_VERIFICATION_DATA_FRAMEWORK.md`
14. `docs/verification/08B_VERIFICATION_MODES.md`
15. `docs/verification/08B_VERIFICATION_POLICIES.md`
16. `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
17. `docs/verification/09_HOME_ASSISTANT_VERIFICATION_ADAPTER.md`
18. Current reports under `docs/verification/reports/`
19. Current backlog and scorecards under `docs/verification/`

Read implementation files only after the canonical documents establish the
responsibility boundary.

Meta Engineering defines the repository-first, evidence-first AI-agent
workflow used while executing verification phases. It does not redefine
verification behavior.

## Frozen Boundaries

- Verification Core owns verification behavior and result aggregation.
- Planning Engine owns scenario, matrix, data, mode and policy expansion into
  executable plans.
- Execution Environment owns tooling, builds, Docker, CI, SSH, serial,
  simulators, VMs, artifacts, secrets loading by name and cleanup.
- Platform adapters remain thin execution layers.
- Scenarios define expected behavior.
- Matrix, Data, Modes and Policies define test variation and scope.
- Verification Investigator is a workflow inside the existing Verification
  system, not a new architecture layer.

Foundation, accepted baselines, scenario expected results and architecture may
not be changed merely to make tests pass.

No new verification subsystem may be introduced without explicit approval. If
implementation needs an extension, extend an existing Verification subsystem.

## Workflow

Work scenario-first and evidence-first:

1. Select the active phase from `PROMPT_INDEX.md`.
2. Confirm predecessors and stop conditions.
3. Plan from scenarios, matrix, data, modes and policies.
4. Prepare the Execution Environment.
5. Execute only through thin adapters.
6. Persist evidence under the configured evidence directory.
7. Classify failures with the Investigator workflow.
8. Fix the owning subsystem only.
9. Rerun affected scenarios and the documented regression subset.
10. Update reports, backlog and prompt status.

## Merge And Review Discipline

- Work on the branch named by the active prompt or user instruction.
- Do not open a second PR when the prompt says to update an existing PR.
- Keep commits logical and reviewable.
- Run focused tests plus `git diff --check` before pushing.
- Do not merge until required review/override and CI expectations are met.
- After merge, return to `main` only when the user asks or the phase workflow
  requires it.

## Live Verification Requirements

Live verification may run only when mandatory gates pass:

- repository branch, SHA and working tree are known;
- exact-SHA CI status is qualified or explicitly blocked;
- Docker/HA runtime identity is proven safe;
- no production HA volumes, tokens or config are used;
- approved storage and log paths are configured;
- secrets are loaded externally and never logged;
- destructive operations require explicit opt-in;
- evidence is durable and redacted.

If any live gate fails, stop before mutation and produce a report.

## Failure Investigation

Failures must be classified as one owning class, for example:

- scenario defect;
- scenario ambiguity;
- Verification Core defect;
- Planning Engine defect;
- Execution Environment defect;
- Home Assistant Adapter defect;
- product implementation defect;
- technical design mismatch;
- foundation mismatch;
- environment issue;
- documentation issue;
- unknown.

The Investigator records confidence, evidence, owner, blocking status,
recommended action and rerun scope. Do not relabel framework failures as
product bugs.

## Stop Conditions

Stop immediately when:

- the active prompt is completed;
- a mandatory gate fails before live mutation;
- the prompt scope would require a new architecture subsystem;
- the work would modify scenario expectations only to make a run green;
- secrets or production state would be exposed;
- the next platform adapter would begin before the current phase is qualified.

## Prompt Location

Canonical task prompts live under:

```text
prompts/verification/
```

`PROMPT_INDEX.md` is the canonical navigation file for prompt status,
predecessors, reports and next phase selection.

## Continue From Current Main

A clean session should fetch and inspect the current branch requested by the
user. If starting from `main`, read `PROMPT_INDEX.md`, create or switch to the
branch required by the active prompt, then execute only that phase.
