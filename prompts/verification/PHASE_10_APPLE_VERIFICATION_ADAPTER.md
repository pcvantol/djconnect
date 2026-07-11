# Verification Program V1
## Phase 10 — Apple Verification Adapter

Repository:

`pcvantol/djconnect`

Apple application source repository:

`pcvantol/djconnect-app`

Context:

The Verification Platform has been qualified by Phase 9V rerun.

Home Assistant backend scenario coverage must first be qualified by Phase 9E.
Do not execute this Phase 10 prompt until Phase 9E returns
`HOME_ASSISTANT_BACKEND_QUALIFIED` or
`HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS` with every warning explicitly
non-blocking for Apple client work.

Completed:

- Verification Vision
- Verification Architecture
- Scenario Schema
- Scenario Catalog
- Verification Matrix
- Verification Harness Architecture
- Verification Core
- Verification Core Refinement
- Technical Design Reconstruction
- Platform Implementation Gap Analysis
- Verification Execution Environment
- Verification Data Framework
- Verification Modes
- Verification Policies
- Verification Planning Engine
- Home Assistant Verification Adapter
- Local Home Assistant Verification Lab
- Verification Platform Qualification Rerun
- Home Assistant Scenario Coverage Expansion

No new verification architecture subsystem may be introduced.

When implementation reveals that the architecture needs an extension, extend
only an existing Verification subsystem unless explicit approval is given.

---

# Mission

Implement the Apple Verification Adapter.

The adapter must enable evidence-backed verification of DJConnect Apple
clients:

- iOS;
- iPadOS;
- macOS;
- watchOS;
- Catalyst where applicable;
- simulator behavior;
- physical-device behavior where explicitly configured;
- multi-device profile behavior where selected scenarios require it.

The adapter remains thin.

It answers only:

```text
How do I perform this operation on an Apple runtime?
```

It never answers:

```text
Was this scenario successful?
```

Scenario success remains owned by the Scenario Engine and Verification Core.

---

# Read first

Read completely:

- `AGENTS.md`
- `BOOTSTRAP_CODEX_SESSION.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md`
- `PROMPT_INDEX.md`
- `docs/meta/README.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`
- `docs/verification/00_VERIFICATION_VISION.md`
- `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
- `docs/verification/02_SCENARIO_SCHEMA.md`
- `docs/verification/03_SCENARIO_CATALOG.md`
- `docs/verification/03A_VERIFICATION_MATRIX.md`
- `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`
- `docs/verification/08A_VERIFICATION_DATA_FRAMEWORK.md`
- `docs/verification/08B_VERIFICATION_MODES.md`
- `docs/verification/08B_VERIFICATION_POLICIES.md`
- `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
- `docs/verification/09_HOME_ASSISTANT_VERIFICATION_ADAPTER.md`
- `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION_RERUN.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- current Apple client source in `pcvantol/djconnect-app`
- current Apple build, test and automation conventions in `pcvantol/djconnect-app`
- current Verification Execution Environment Apple tooling support
- current Scenario Catalog entries that require Apple runtime capabilities
- current lab capability catalog and scenario requirement declarations

Inspect actual paths and naming conventions before changing anything.

Do not invent duplicate canonical documents.

---

# Scope

Implement only the runtime primitives required to execute the first approved
Apple scenario set.

Start scenario-driven.

Do not implement every conceivable Apple automation operation.

The initial scenario set should be selected by the Planning Engine from
canonical scenarios that require Apple runtime capabilities and can be executed
with available local Apple tooling.

If the catalog does not yet contain enough Apple-executable scenario detail,
classify that as a Scenario Gap and create a narrowly scoped remediation prompt.
Do not invent expected behavior inside the adapter.

---

# Responsibilities

The Apple Verification Adapter owns runtime execution only.

Support primitives such as:

- connect to an Apple runtime target;
- disconnect;
- discover available simulators;
- discover configured physical devices;
- validate target identity;
- install an app artifact;
- uninstall an app artifact;
- launch app;
- terminate app;
- reset app state;
- send supported UI/runtime input;
- collect app logs;
- collect system logs scoped to the target;
- collect screenshots;
- collect screen recordings where supported;
- collect runtime metadata;
- collect app metadata;
- collect simulator/device metadata;
- wait for app state;
- expose raw structured operation results.

The adapter must not own:

- build tooling;
- Xcode discovery;
- simulator creation;
- simulator erase policy;
- physical-device provisioning;
- artifact storage;
- evidence storage;
- CI inspection;
- cleanup policy;
- scenario assertions;
- profile logic;
- privacy logic;
- localization decisions;
- business rules.

Those responsibilities remain with the Verification Execution Environment,
Scenario Engine and Verification Core.

---

# Execution Environment Integration

Use the existing Verification Execution Environment for:

- Xcode discovery;
- `xcrun` and simulator tooling;
- build qualification;
- artifact metadata;
- signing and entitlement metadata;
- GitHub CI metadata;
- environment snapshots;
- evidence storage;
- cleanup;
- secrets and local configuration.

Do not duplicate these concerns in the Apple adapter.

---

# Planning Integration

The Planning Engine must decide:

- selected scenarios;
- Apple client variant;
- simulator versus physical device;
- matrix dimensions;
- data profiles;
- verification modes;
- policies;
- required build type;
- required runtime target;
- required evidence.

The Apple adapter receives a prepared execution target and performs operations
against it.

If no configured Apple target can satisfy a plan, fail closed and report the
unresolved requirement.

---

# Runtime Targets

Support canonical targets where available:

- iPhone simulator;
- iPad simulator;
- macOS app runtime;
- watchOS simulator paired with a compatible iPhone simulator;
- physical iPhone;
- physical iPad;
- physical Apple Watch;
- Catalyst/macOS target where the Apple app supports it.

Physical device execution must require explicit local configuration and must
never be assumed.

---

# Safety

The adapter must:

- never commit provisioning profiles, certificates, secrets or device tokens;
- never log credentials, OAuth material, HA tokens, pairing tokens or private
  Ask DJ content;
- redact sensitive values in operation arguments and evidence;
- avoid destructive simulator/device operations unless the plan and execution
  policy explicitly allow them;
- scope cleanup to verification-owned app state and artifacts;
- preserve evidence before cleanup after failures.

---

# Evidence

For every operation collect:

- timestamp;
- run ID;
- scenario ID;
- target ID;
- client variant;
- operation name;
- duration;
- command/tool used where safe;
- redacted arguments;
- raw structured result;
- errors;
- log references;
- screenshot references where applicable;
- artifact references.

Store evidence through the existing Verification Core and Execution Environment
evidence pipeline.

---

# Tests

Add focused tests for:

- adapter configuration parsing;
- simulator target discovery parsing;
- physical-device target discovery parsing where mockable;
- app install/launch/terminate primitive modeling;
- screenshot/log evidence modeling;
- redaction;
- target identity validation;
- unsupported target failure;
- timeout handling;
- integration with Planning Engine adapter selection;
- integration with Execution Environment Apple target metadata.

Use mocks for local Apple tooling by default.

Live Apple tests must require explicit opt-in.

Skipped live tests remain `SKIPPED`, never `PASS`.

---

# Documentation

Create or update:

- `docs/verification/10_APPLE_VERIFICATION_ADAPTER.md`
- `docs/verification/reports/PHASE_10_APPLE_ADAPTER_COMPLETION.md`
- adapter registry documentation where present;
- Verification Execution Environment Apple guidance if implementation reality
  changes;
- Planning Engine documentation only if the adapter requires factual planning
  behavior updates;
- Verification backlog and scorecards.

Do not rewrite Technical Design unless implementation reveals a factual error.
If a factual error is found:

- correct it with evidence;
- record the correction;
- do not silently alter history.

---

# Completion Report

The Phase 10 completion report must include:

- implemented runtime primitives;
- selected initial Apple scenario set;
- simulator and physical-device coverage;
- build artifacts used;
- environment used;
- Apple tooling versions;
- GitHub CI status for tested SHA;
- tests run;
- evidence produced;
- live tests passed/skipped/blocked;
- known limitations;
- remaining Apple-only gaps;
- readiness for the next adapter phase.

---

# Acceptance Criteria

Phase 10 is complete when:

- a thin Apple Verification Adapter exists;
- it contains no Scenario logic;
- it contains no Verification logic;
- it contains no Profile, privacy, Music DNA or product assertions;
- it integrates with the existing Execution Environment;
- Planning Engine can select Apple runtime requirements and fail closed when
  no target is available;
- simulator discovery works where local Xcode supports it;
- app install/launch/terminate primitives are implemented or explicitly
  blocked with evidence;
- logs, screenshots and runtime metadata are collected where supported;
- evidence is redacted and persisted;
- unit and mock tests pass;
- live Apple tests either pass or are explicitly reported as skipped/blocked;
- documentation and completion report exist;
- the Phase Completion Protocol has been executed;
- no next platform adapter work has started.

---

# Stop Condition

After completing Phase 10:

- create the completion report;
- update scorecards/backlog/prompt index;
- generate either the next phase prompt or a remediation prompt;
- commit and push;
- stop.

Do not begin the next platform adapter automatically.
