# Verification Program V1
## Phase 10E - Apple Scenario Coverage Expansion

Repository:

`pcvantol/djconnect`

Apple application source repository:

`pcvantol/djconnect-app`

Context:

Phase 10 implemented and qualified the thin Apple Verification Adapter with
mock/unit primitive coverage. Live Apple simulator/device execution was
explicitly skipped because no prepared target JSON and app artifact were
configured.

Do not execute this prompt until Phase 10 returns
`APPLE_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED` or a stronger Apple adapter
qualification result.

No new verification architecture subsystem may be introduced.

---

# Mission

Expand Apple scenario coverage using the Phase 10 Apple Verification Adapter.

Start from canonical scenarios that declare Apple runtime capabilities and
select the first executable Apple scenario set that can run with available
local Apple tooling and prepared artifacts.

The adapter remains thin. Scenario success remains owned by the Scenario Engine
and Verification Core.

---

# Read first

Read completely:

- `BOOTSTRAP_CODEX_SESSION.md`
- `AGENTS.md`
- `docs/meta/README.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md`
- `PROMPT_INDEX.md`
- `docs/verification/00_VERIFICATION_VISION.md`
- `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
- `docs/verification/02_SCENARIO_SCHEMA.md`
- `docs/verification/03_SCENARIO_CATALOG.md`
- `docs/verification/03A_VERIFICATION_MATRIX.md`
- `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`
- `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
- `docs/verification/10_APPLE_VERIFICATION_ADAPTER.md`
- `docs/verification/reports/PHASE_10_APPLE_ADAPTER_COMPLETION.md`
- current Apple client source in `pcvantol/djconnect-app`
- current Apple build/test/automation conventions in `pcvantol/djconnect-app`

Inspect actual paths and naming conventions before changing anything.

---

# Scope

Implement only the scenario execution coverage required for the first approved
Apple scenario set.

Do not implement every conceivable Apple UI automation operation.

If canonical scenarios do not contain enough Apple-executable detail, classify
that as a Scenario Gap and create a remediation prompt. Do not invent expected
behavior inside the adapter.

---

# Required Work

1. Select the first Apple-executable scenario set through the Planning Engine.
2. Confirm available Apple tooling and prepared target/artifact configuration.
3. Execute mock/unit coverage first.
4. Execute live simulator coverage only when explicit local Apple target JSON
   and app artifact configuration are present.
5. Keep physical-device tests skipped unless explicitly configured.
6. Persist evidence through the existing evidence pipeline.
7. Classify failures with the Investigator workflow.
8. Fix only the owning subsystem.
9. Update reports, backlog, scorecard and prompt index.

---

# Acceptance Criteria

Phase 10E is complete when:

- the first Apple scenario set is selected from canonical scenarios;
- the Planning Engine records Apple runtime requirements and fails closed when
  no target is available;
- Apple adapter primitives execute for selected scenarios or are explicitly
  skipped/blocked with evidence;
- live simulator/device results are never reported as passed unless they
  actually ran;
- evidence is redacted and persisted;
- focused tests pass;
- a Phase 10E completion report exists;
- backlog, scorecard and prompt index are current;
- the next prompt or remediation prompt is generated;
- no next platform adapter work has started.

---

# Stop Condition

After completing Phase 10E:

- create the completion report;
- update scorecards/backlog/prompt index;
- generate either the next phase prompt or a remediation prompt;
- commit and push;
- stop.

Do not begin the next platform adapter automatically.
