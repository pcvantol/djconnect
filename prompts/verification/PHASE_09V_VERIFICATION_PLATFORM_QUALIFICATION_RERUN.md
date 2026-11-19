# Verification Program V1
## Phase 9V - Verification Platform Qualification Rerun

Repository:

`pcvantol/djconnect`

Context:

Phase 9L-R6 qualified the dedicated local Home Assistant verification lab after
Docker Desktop access to the macOS `Documents` folder was approved. The lab can
now start the canonical `ha-profile`, bootstrap lab-only Home Assistant auth,
qualify REST and WebSocket, load the DJConnect integration and execute
`PROFILE-001` through `PROFILE-005` through the Home Assistant adapter.

This phase reruns the Verification Platform Qualification.

This is not a product feature phase.

This is not an adapter implementation phase.

This phase decides whether the Verification Platform itself is qualified for
Phase 10.

---

# Mission

Execute the first complete, evidence-backed verification platform qualification
cycle after Phase 9L-R6.

Prove that the complete verification pipeline functions end to end:

```text
Scenario Catalog

Verification Matrix

Verification Data Framework

Verification Mode

Verification Policy

Planning Engine

Execution Environment

Local Home Assistant Verification Lab

Home Assistant Verification Adapter

Home Assistant Runtime

Evidence

Verification Core

Verification Investigator workflow

Qualification Report
```

The purpose is to qualify the Verification Platform.

Do not broaden the scope into product validation.

---

# Read first

Read completely:

- `AGENTS.md`
- `BOOTSTRAP_CODEX_SESSION.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md`
- `PROMPT_INDEX.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`
- Verification Vision
- Verification Architecture
- Scenario Schema
- Scenario Catalog
- Verification Matrix
- Verification Data Framework
- Verification Modes
- Verification Policies
- Verification Planning Engine
- Verification Execution Environment
- Home Assistant Verification Adapter documentation
- Technical Design Reconstruction
- Platform Implementation Gap Analysis
- `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION.md`
- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- Current Docker and Compose definitions
- Current lab capability, service and profile catalogs
- Current verification tests

Inspect actual paths and file names before changing anything.

Do not invent duplicate canonical documents.

---

# Scope

Execute only the first approved scenario set:

- `PROFILE-001`
- `PROFILE-002`
- `PROFILE-003`
- `PROFILE-004`
- `PROFILE-005`

Use the canonical local Home Assistant verification lab.

Use the Planning Engine.

Use deterministic verification data.

Use the Verification Execution Environment.

Use the Home Assistant Verification Adapter.

Use the Verification Core and Investigator workflow.

Do not execute the complete scenario catalog.

Do not start Phase 10.

---

# Mandatory gates

Before scenario execution, verify:

- repository hygiene;
- current branch and exact SHA;
- working tree state;
- GitHub CI status for the exact SHA where possible;
- toolchain validation;
- dependency status;
- scenario catalog validation;
- lab capability catalog validation;
- lab service catalog validation;
- lab profile validation;
- Planning Engine profile selection;
- Docker daemon health;
- Docker Compose health;
- no stale dedicated verification containers;
- no production HA container or volume use;
- dedicated lab source fingerprint;
- Home Assistant lab health;
- REST probe;
- WebSocket probe;
- `djconnect.loaded`;
- approved storage access;
- log access;
- evidence directory readiness;
- configuration and secret redaction.

If any mandatory gate fails:

1. Stop scenario execution.
2. Preserve evidence.
3. Produce the qualification report.
4. Generate a narrowly scoped remediation prompt.
5. Do not continue to Phase 10.

---

# Planning

Use the Planning Engine to generate the execution plan.

Record:

- selected policy;
- selected modes;
- selected matrix profile;
- selected data profile;
- selected scenario IDs;
- generated test cases;
- aggregated runtime requirements;
- selected lab profile;
- selected Compose fragments;
- bootstrap actions;
- required secrets;
- required hardware;
- execution order;
- estimated runtime;
- evidence requirements.

Persist the plan as evidence.

The Planning Engine plans only.

It must not execute Docker or configure Home Assistant.

---

# Lab qualification

Use the canonical local HA lab.

The lab must prove:

- smallest satisfying profile selection for `PROFILE-001` through
  `PROFILE-005`;
- canonical `ha-profile` selection;
- deterministic Compose fragment resolution;
- dedicated verification network and volumes;
- lab-only Home Assistant auth;
- no production resources;
- REST readiness;
- WebSocket readiness;
- DJConnect integration loaded;
- approved storage access;
- log access;
- capability-level readiness.

Healthy containers alone are not sufficient.

The lab must return:

```text
LOCAL_VERIFICATION_LAB_QUALIFIED
```

before scenario execution.

---

# Data

Use deterministic generated verification data.

Record:

- seed;
- run ID;
- scenario IDs;
- generator versions;
- data profile;
- schema versions.

Everything must be reproducible.

---

# Execution

Execute every generated test case for:

- `PROFILE-001`
- `PROFILE-002`
- `PROFILE-003`
- `PROFILE-004`
- `PROFILE-005`

For every execution collect:

- environment metadata;
- lab metadata;
- runtime metadata;
- adapter operation logs;
- requests;
- responses;
- storage snapshots where applicable;
- capabilities;
- timing;
- errors;
- evidence index.

Skipped tests are not PASS.

Live tests must require explicit local environment qualification.

---

# Dogfooding

This phase is the acceptance test of the Verification Platform itself.

Verify that the framework subsystems have sufficient tests and evidence:

- Planning Engine;
- Execution Environment;
- local HA lab;
- Home Assistant Adapter;
- Verification Core;
- Verification Investigator workflow;
- evidence store;
- scenario catalog validation;
- lab requirement validation.

If a run fails because the Planning Engine selects the wrong profile, the
Execution Environment produces an incomplete snapshot, the adapter misreports a
runtime primitive or the Investigator misclassifies a failure, classify it as a
Verification Framework defect.

Do not classify framework defects as product bugs.

---

# Investigation

Every failure must be analysed before fixing.

Classify each failure as exactly one:

- Scenario defect
- Scenario ambiguity
- Verification Core defect
- Planning Engine defect
- Execution Environment defect
- Home Assistant Adapter defect
- Local HA Lab defect
- DJConnect implementation defect
- Technical Design mismatch
- Foundation mismatch
- Environment issue
- Documentation issue
- External dependency
- Unknown

For every classification include:

- confidence;
- evidence;
- owning subsystem;
- recommended action;
- blocking status.

---

# Fix cycle

If a defect is clearly identified:

1. Implement the smallest safe fix.
2. Re-run only the affected scenario or gate.
3. If that passes, run the approved regression subset.
4. Record every fix.
5. Record every rerun.

Do not rewrite Foundation or expected results merely to make tests pass.

Do not introduce new verification architecture subsystems.

If an architecture extension appears necessary, extend only an existing
Verification subsystem and document the reason.

---

# Metrics

Capture:

- planning duration;
- environment preparation duration;
- lab startup duration;
- auth bootstrap duration;
- doctor duration;
- scenario duration;
- adapter overhead;
- storage snapshot duration;
- report generation duration;
- evidence size;
- Docker restart/recreate time when used.

These are observations, not pass/fail criteria unless the phase defines a
specific threshold.

---

# Deliverables

Create or update:

- `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION_RERUN.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`

If qualified, create the Phase 10 prompt:

- `prompts/verification/PHASE_10_APPLE_VERIFICATION_ADAPTER.md`

If not qualified, create a narrowly scoped remediation prompt:

- `prompts/verification/PHASE_09V_R*_*.md`

Update:

- `PROMPT_INDEX.md`
- bootstrap documents only if the active phase pointer or workflow genuinely
  requires it.

Do not execute the next phase.

---

# Final decision

The qualification report must end with exactly one:

```text
VERIFICATION PLATFORM QUALIFIED
```

or

```text
VERIFICATION PLATFORM NOT QUALIFIED
```

Explain every blocking issue.

---

# Acceptance criteria

This phase is complete when:

- mandatory gates were executed;
- the Planning Engine generated the plan;
- the local HA lab was qualified or the failure was reported;
- `PROFILE-001` through `PROFILE-005` were executed if gates passed;
- evidence was collected;
- the Verification Investigator workflow classified every failure;
- framework dogfooding was assessed;
- tests and validation were run;
- scorecard and backlog were updated;
- a qualification report exists;
- exactly one next prompt exists:
  - Phase 10 if qualified;
  - remediation if not qualified;
- `PROMPT_INDEX.md` points to the next clean-session action;
- no important engineering knowledge remains only in chat.

After completing the implementation work, complete the phase according to:

```text
docs/meta/PHASE_COMPLETION_PROTOCOL.md
```

Stop after the qualification report and next prompt.

Do not begin the Apple Verification Adapter automatically.
