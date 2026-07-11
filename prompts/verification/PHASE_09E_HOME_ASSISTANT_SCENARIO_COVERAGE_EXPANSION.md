# Verification Program V1
## Phase 9E — Home Assistant Scenario Coverage Expansion

Repository:

`pcvantol/djconnect`

Context:

Phase 9V rerun qualified the Verification Platform itself. It proved that the
pipeline can plan, prepare, execute, observe, collect evidence, report and
support investigation using the first approved Profile scenario set.

Phase 9V did not qualify full Home Assistant backend coverage.

Before starting any client adapter, DJConnect must qualify broad Home
Assistant backend scenario coverage.

This phase expands execution from platform qualification to Home Assistant
backend behavior qualification.

---

# Mission

Execute and close coverage for canonical scenarios where Home Assistant is:

- the sole runtime under test;
- the primary implementation owner;
- the backend participant required before client validation;
- the authoritative source for profile, resolver, persistence, privacy,
  capability, API, service, voice-backend, music-backend or intelligence
  behavior.

The result of this phase is a Home Assistant backend qualification decision.

Do not implement client adapters.

Do not execute Phase 10.

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
- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION_RERUN.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.md`
- `docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.json`
- `verification/schema/scenario.schema.yaml`
- `verification/lab/capabilities.yaml`
- all canonical scenarios under `verification/scenarios/`
- current Home Assistant integration implementation under
  `custom_components/djconnect/`
- current Verification Core, Planning Engine, Execution Environment and Home
  Assistant Adapter implementation under `tools/verification/`

Inspect actual file names and paths before changing anything.

Do not infer completion from chat history when repository evidence differs.

---

# Scope Discovery

Before executing scenarios, produce a scenario inventory from repository data.

Use the canonical scenario files and their `requires` declarations.

The inventory must:

- count all canonical scenarios;
- identify all scenarios requiring Home Assistant or DJConnect backend
  capabilities;
- group scenarios by functional domain;
- distinguish:
  - HA-only;
  - HA-primary;
  - cross-platform blocked;
  - hardware/client dependent;
- identify required lab profiles and services;
- identify required modes and data profiles;
- identify required secrets;
- identify unresolved capabilities;
- identify scenarios deferred to client, hardware, release or external adapter
  phases.

Do not hardcode estimates such as 100 or 150.

At the time this prompt was created, repository inventory showed:

- 231 canonical scenario files;
- 223 scenarios declaring HA/DJConnect runtime capabilities;
- 111 scenarios that appear HA-only or HA-primary without client/hardware
  runtime requirements;
- 112 scenarios with client runtime requirements;
- 44 scenarios with hardware/runtime requirements;
- 0 scenarios with unresolved `requires` declarations.

These are not acceptance counts. Phase 9E must recompute exact counts from the
current repository state and persist the inventory as evidence.

---

# Required Domains

At minimum evaluate applicable scenarios for:

- Profile Platform;
- Profile Resolver;
- Request Context;
- pairing server-side behavior;
- authentication and authorization;
- capability discovery;
- REST;
- WebSocket;
- HA services;
- storage;
- persistence;
- restart/recovery;
- privacy;
- Private Session;
- Music DNA backend;
- Ask DJ backend;
- Track Insight backend;
- playback orchestration;
- Music Backend abstraction;
- export/import;
- migrations;
- localization of backend-owned text where applicable;
- error handling;
- malformed input;
- boundary validation;
- security payloads;
- injection resistance;
- logging and redaction;
- diagnostics;
- Assist pipeline backend behavior where HA owns it;
- Whisper/Piper lab profile selection where required;
- fake backend and Music Assistant lab profiles where required.

If a domain has canonical scenarios but cannot be executed yet, classify it as
blocked or deferred with evidence. Do not silently omit it.

---

# Planning And Lab Selection

Use scenario `requires` declarations.

The Planning Engine must:

- aggregate required capabilities;
- resolve transitive capability dependencies;
- select the smallest valid canonical lab profile per scenario batch;
- provision modular sidecars only when required;
- fail closed on unresolved capabilities;
- persist the execution plan as evidence;
- record selected lab profile per batch;
- record required secrets, services, bootstrap actions and readiness gates;
- report scenarios that require client, hardware or external runtime resources.

The Execution Environment must prepare the selected lab profile.

The Home Assistant Adapter must not decide which containers, sidecars,
integrations or pipelines exist.

Do not use one `ha-full` run by default when a smaller canonical profile
satisfies the batch.

---

# Execution Strategy

Do not execute one uncontrolled giant run.

Use staged batches:

1. HA core smoke;
2. Profile and resolver;
3. transport and services;
4. storage and persistence;
5. privacy and diagnostics;
6. Ask DJ and Music DNA;
7. playback and music backends;
8. Assist/voice backend;
9. security and robustness;
10. HA regression closure.

Each batch must:

- use a unique run ID;
- preserve evidence;
- record the selected scenario IDs;
- record selected policy, modes, matrix profile, data profiles and lab profile;
- execute only scenarios selected for that batch;
- classify failures before fixing;
- run focused remediation only for clearly owned defects;
- rerun affected scenarios after remediation;
- run the relevant regression subset;
- update the coverage report.

Do not broaden scope after a failure. Fix the owning subsystem and rerun only
the affected batch plus the relevant regression subset.

---

# Data And Modes

Use the existing:

- Verification Data Framework;
- deterministic seeds;
- Functional mode;
- Boundary mode;
- Security mode;
- Privacy mode;
- Resilience mode;
- Localization mode where applicable.

Do not multiply every scenario across every possible combination.

Use policy- and risk-based selection.

Record:

- seed;
- run ID;
- scenario IDs;
- generator IDs;
- generator versions;
- data profile versions;
- mode selection rationale.

---

# Lab Profiles

Use canonical lab profiles under:

```text
verification/lab/profiles/
```

Expected profile usage:

- `ha-minimal` for HA runtime, REST, WebSocket, services and basic capability
  checks;
- `ha-profile` for profile, resolver, approved storage, persistence and
  restart-sensitive backend scenarios;
- `ha-music` for fake backend, Music Assistant and playback target scenarios
  that require music resources;
- `ha-assist` for Assist, STT, TTS, Whisper, Piper and voice-backend
  scenarios;
- `ha-full` only for full qualification or debugging when smaller profiles do
  not satisfy the selected batch.

If a profile promises a capability but readiness cannot prove it, classify the
failure as Execution Environment, lab profile, bootstrap or adapter defect
before touching product code.

---

# Failure Classification

Every failed or blocked scenario must be classified as exactly one:

- Scenario defect;
- Scenario ambiguity;
- Verification Core defect;
- Planning Engine defect;
- Execution Environment defect;
- Home Assistant Adapter defect;
- DJConnect Home Assistant implementation defect;
- Technical Design mismatch;
- Foundation mismatch;
- Environment issue;
- Documentation issue;
- External dependency;
- Unknown.

Each classification must include:

- confidence;
- evidence path;
- owning subsystem;
- blocking status;
- recommended action;
- rerun scope.

Do not relabel framework failures as product bugs.

Do not modify scenario expected results merely to make the run pass.

---

# Coverage Outputs

Create or update:

```text
docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.md
docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.json
```

The report must include:

- HA scenario inventory;
- total canonical scenario count;
- HA-related scenario count;
- HA-only scenario count;
- HA-primary scenario count;
- cross-platform blocked scenario count;
- hardware/client dependent scenario count;
- executed scenario count;
- passed;
- failed;
- blocked;
- skipped;
- unresolved;
- coverage by domain;
- coverage by mode;
- coverage by lab profile;
- scenarios deferred to client/hardware adapters;
- evidence index;
- failure ownership summary;
- fixes applied;
- reruns;
- remaining HA backend gaps;
- recommendations;
- readiness for Phase 10.

Also update:

- `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `PROMPT_INDEX.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md` when the active-phase pointer changes.

---

# Acceptance Decision

The final Phase 9E decision must be exactly one of:

```text
HOME_ASSISTANT_BACKEND_QUALIFIED
HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS
HOME_ASSISTANT_BACKEND_NOT_QUALIFIED
HOME_ASSISTANT_BACKEND_BLOCKED
```

Phase 10 may start only for:

```text
HOME_ASSISTANT_BACKEND_QUALIFIED
HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS
```

For `HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS`, every warning must be
explicitly non-blocking for Apple client work.

If Phase 9E is not qualified or blocked, generate a narrowly scoped Phase 9E
remediation prompt that addresses only proven remaining blockers.

---

# Completion Protocol

Complete the current phase according to:

```text
docs/meta/PHASE_COMPLETION_PROTOCOL.md
```

At completion, produce exactly one of:

- a Phase 10 prompt when Home Assistant backend coverage is qualified or
  qualified with non-blocking warnings;
- a narrowly scoped Phase 9E remediation prompt when Home Assistant backend
  coverage is not qualified or blocked.

Do not execute the next phase automatically.

Do not begin the Apple Verification Adapter.

---

# Stop Condition

Stop after Phase 9E reports, coverage outputs, prompt index updates and the
next prompt/remediation prompt are committed and pushed.

Return:

- files created and updated;
- exact scenario inventory counts;
- executed scenario count;
- passed, failed, blocked, skipped and unresolved counts;
- coverage by domain;
- coverage by mode;
- coverage by lab profile;
- scenarios deferred to client/hardware adapters;
- failure ownership summary;
- completion/qualification decision;
- commit SHA;
- PR link;
- next prompt path;
- exact clean-session bootstrap command.
