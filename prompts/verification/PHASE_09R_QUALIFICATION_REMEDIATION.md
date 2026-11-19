# Verification Program V1
## Phase 9R — Verification Platform Qualification Remediation

Repository: `pcvantol/djconnect`

## Context

Phase 9V concluded with:

`VERIFICATION PLATFORM NOT QUALIFIED`

Blocking findings:

1. the local Home Assistant runtime was not detected or qualified;
2. GitHub CLI authentication was invalid, so mandatory CI status could not be validated locally;
3. GitHub commit-status lookup returned no usable status data;
4. no executable Verification Investigator exists;
5. evidence is not persisted durably enough as immutable run artifacts;
6. live WebSocket and approved-storage paths are not qualified.

Important environment facts:

- the Home Assistant development environment already runs locally in Docker;
- local interactive verification may invoke `gh auth login` when `gh auth status` shows missing, expired or invalid authentication;
- non-interactive verification must never block waiting for login and must fail clearly when no approved credential is available.

Dogfooding already showed that Planning, Core, Execution Environment and the HA Adapter have tests, but the Investigator and the live Home Assistant paths remain insufficiently proven.

Phase 10 — Apple Verification Adapter remains blocked.

This phase remediates only the Phase 9V qualification blockers and then prepares a fresh Phase 9V rerun.

Do not add a new architecture layer.
Do not broaden the scenario set.
Do not begin Apple work.
Do not modify scenario expectations merely to make the qualification green.

---

# Mission

Turn every Phase 9V blocker into one of:

- fixed and verified;
- explicitly waived with evidence and approval;
- still blocked with a precise external prerequisite.

The target outcome is a reproducible fresh run of Phase 9V against the real local Docker-based HA development runtime.

The remediation loop is:

```text
Observe
  -> classify
  -> fix the owning subsystem
  -> run focused tests
  -> run the affected live probe
  -> run the relevant regression subset
  -> rerun Phase 9V with a new run ID
```

---

# Read first

Read completely:

- `AGENTS.md`;
- the Phase 9V qualification report;
- Verification Platform scorecard and backlog;
- Verification Vision and Architecture;
- Scenario Schema and Scenario Catalog;
- the exact `PROFILE-001` through `PROFILE-005` scenario definitions;
- Verification Matrix;
- Verification Data Framework;
- Verification Modes and Policies;
- Verification Planning Engine;
- Verification Core;
- Verification Execution Environment;
- Home Assistant Verification Adapter;
- Evidence model and redaction rules;
- Repository Hygiene and Build Qualification rules;
- Technical Design Reconstruction;
- HTTP and WebSocket inventories;
- storage and logging technical-design documents;
- current Docker/local HA development documentation;
- current CI workflows and required checks.

Treat Technical Design as the implementation-state reference and Foundation/Baseline as normative.

---

# Mandatory scope control

Allowed:

- targeted changes to existing Verification subsystems;
- Docker HA environment discovery and qualification;
- GitHub authentication/CI qualification improvements;
- an executable Investigator workflow inside the existing Verification Core;
- durable run-artifact persistence;
- live WebSocket qualification;
- approved DJConnect storage qualification;
- tests and documentation directly required by these blockers.

Not allowed:

- new product features;
- Apple, Windows, Pi, ESP32 or Voice adapter work;
- broad architecture redesign;
- a new top-level Verification subsystem;
- unrelated refactors;
- weakening of hygiene, CI or qualification requirements;
- automatic modification of canonical scenario expectations.

---

# Workstream 1 — Qualify the local Docker-based Home Assistant development runtime

The HA development runtime runs locally in Docker. Treat Docker as the authoritative HA execution environment for this phase.

## Discovery

Implement or complete deterministic discovery of the intended HA development container.

Record:

- Docker Engine version;
- Docker Compose version when used;
- container name;
- container ID;
- image repository and tag;
- image digest;
- container creation and start timestamps;
- container status/health;
- host OS and architecture;
- network mode;
- exposed ports and port mappings;
- relevant bind mounts;
- relevant named volumes;
- HA config path inside the container;
- HA storage path inside the container;
- mounted DJConnect source path;
- mounted source fingerprint and Git SHA;
- redacted container environment fingerprint.

Never log secrets from container environment variables.

## Environment identity and safety

Before any mutation, prove that the selected runtime is the intended development instance.

Validation must include:

- Docker daemon reachable;
- exactly one intended HA development container selected;
- the expected host port belongs to that container;
- the runtime is explicitly configured or marked as a verification/development environment;
- it is not the user's production HA instance;
- the mounted DJConnect source matches the recorded repository SHA;
- DJConnect is loaded from the intended source path;
- the verification fixture namespace is safe to use;
- logs, REST, WebSocket and approved storage are accessible.

If environment identity cannot be proven, return `BLOCKED_ENVIRONMENT` before mutation.

## Runtime operations

Support and distinguish:

- `start`: start an existing stopped container;
- `stop`: stop the intended container;
- `restart`: restart the same container while preserving its configured persistent state;
- `recreate`: create a new container from the pinned image/config while retaining only explicitly approved volumes;
- `fresh`: use a dedicated disposable container and disposable verification storage.

Do not remove unrelated containers or volumes.
Do not wipe persistent HA storage unless a selected scenario explicitly requires a fresh state.

## Readiness

Implement or complete a deterministic command following existing CLI conventions, for example:

```bash
verification doctor --environment ha-docker
```

It must report structured results for:

- Docker available;
- intended container found;
- container image/digest recorded;
- container running and healthy;
- HA reachable on the expected port;
- authentication valid;
- DJConnect integration loaded;
- capabilities available;
- REST reachable;
- WebSocket reachable;
- approved storage accessible;
- logs accessible;
- mounted source matches the recorded SHA;
- environment safe for verification mutations.

## Docker cleanup and reproducibility

Before each qualification attempt:

1. identify and stop stale duplicate HA development containers where safe;
2. verify that only the intended container owns the HA host port;
3. archive or rotate dedicated verification logs;
4. remove stale Python bytecode from the mounted DJConnect integration;
5. verify the mounted source tree is clean and matches the recorded SHA;
6. remove old run-specific temporary files;
7. recreate the container only when required by the chosen qualification mode;
8. preserve persistent state unless the scenario explicitly requests fresh state;
9. record every Docker command executed;
10. record image and container digests in the reproducibility manifest.

Add unit/mock tests for discovery, ambiguity, wrong-port ownership, wrong-source SHA, unhealthy container and unsafe environment classification.

---

# Workstream 2 — Interactive GitHub CLI authentication and exact-SHA CI qualification

CI qualification must remain mandatory for the exact tested SHA.

## Interactive local authentication

When running locally in an interactive terminal:

1. execute `gh auth status`;
2. when authentication is missing, expired or invalid:
   - explain that GitHub authentication is required for CI qualification;
   - invoke `gh auth login` using its normal interactive browser/device flow;
   - never attempt to type credentials on behalf of the user;
   - never capture, print or persist the token;
   - after completion, run `gh auth status` again;
3. continue only when authentication succeeds;
4. otherwise stop with `BLOCKED_CI_AUTH`.

Provide an explicit option consistent with the existing CLI, such as:

```bash
verification doctor --fix-auth
verification run --interactive-auth
```

Do not show a login prompt on every run. Prompt only after authentication validation fails.

## Non-interactive behavior

When no TTY is available:

- never wait for interactive login;
- use an existing approved `GH_TOKEN` or configured credential source when available;
- never log the token;
- otherwise return `BLOCKED_CI_AUTH` with actionable setup guidance.

## CI data sources

Do not couple CI qualification exclusively to `gh`.

Use a layered strategy:

1. validated GitHub CLI/API result for the exact SHA;
2. GitHub Actions workflow runs for the exact SHA;
3. required jobs and conclusions;
4. combined commit status/check runs where available;
5. workflow artifact metadata.

The implementation must distinguish:

- no CI workflow configured;
- workflow not triggered for the SHA;
- workflow queued/running;
- workflow passed;
- workflow failed;
- workflow cancelled/timed out;
- authentication unavailable;
- API returned no data;
- commit statuses empty but workflow runs present;
- SHA mismatch.

An empty commit-status response is never success.
A passing run for another SHA is never accepted.
A local green build never overrides failing required CI.

## Exact-SHA report

Record:

- repository;
- tested SHA;
- workflow names;
- run IDs;
- event types;
- job names;
- conclusions;
- artifact names/IDs;
- waivers and reasons;
- final CI decision.

Return one of:

- `CI_PASS`;
- `CI_PASS_WITH_NON_BLOCKING_WARNINGS`;
- `CI_RUNNING`;
- `CI_FAIL`;
- `CI_NOT_CONFIGURED`;
- `CI_AUTH_REQUIRED`;
- `CI_NO_DATA`;
- `CI_SHA_MISMATCH`.

Add deterministic tests for all states, especially empty responses and SHA mismatch.

---

# Workstream 3 — Implement an executable Verification Investigator workflow

Implement the Verification Investigator as an executable workflow inside the existing Verification Core.

Do not introduce a new top-level architecture subsystem.

## Inputs

The Investigator consumes an immutable evidence bundle containing where available:

- run metadata;
- environment snapshot;
- reproducibility manifest;
- qualification gates;
- execution plan;
- scenario/test-case definitions and versions;
- data generator seed/version;
- matrix/mode/policy selection;
- assertions and observed results;
- adapter operations;
- requests and responses;
- HA/DJConnect/verification logs;
- storage snapshots and diffs;
- CI metadata;
- timing and error information.

## Output model

Produce a structured investigation result with at least:

```text
failure_id
run_id
scenario_id
test_case_id
classification
confidence
evidence_references
probable_owner
owning_repository
blocking_status
recommended_action
rerun_scope
regression_scope
human_review_required
notes
```

## Canonical classifications

Support:

- `scenario_defect`;
- `scenario_ambiguity`;
- `data_generator_defect`;
- `matrix_defect`;
- `mode_defect`;
- `policy_defect`;
- `planning_engine_defect`;
- `verification_core_defect`;
- `execution_environment_defect`;
- `ha_adapter_defect`;
- `product_implementation_defect`;
- `technical_design_mismatch`;
- `foundation_mismatch`;
- `environment_issue`;
- `ci_qualification_issue`;
- `documentation_issue`;
- `unknown`.

## Safety rules

The Investigator must never:

- change expected results automatically;
- modify product or verification code automatically;
- classify with certainty unsupported by evidence;
- hide contradictory evidence;
- convert skipped/blocked checks into passes;
- propose Foundation changes without recommending an ADR and human review.

Use confidence thresholds. Low-confidence findings require human review.

## CLI

Integrate with the existing CLI, for example:

```bash
verification investigate <run-id>
verification investigate <run-id> --scenario PROFILE-001
verification investigate <run-id> --failure <failure-id>
```

## Tests

Add deterministic tests using synthetic evidence bundles for:

- adapter failure;
- runtime unavailable;
- product assertion mismatch;
- scenario ambiguity;
- storage cleanup failure;
- CI unavailable;
- conflicting evidence;
- unknown classification;
- low-confidence human-review requirement.

The Investigator's own output must be persisted and referenced by reports.

---

# Workstream 4 — Durable, immutable and crash-tolerant evidence persistence

Implement or complete durable run-artifact persistence.

Each run uses a unique directory:

```text
artifacts/<run-id>/
```

Never reuse or overwrite a run directory.

## Required run-level artifacts

Where applicable persist:

```text
environment.json
reproducibility-manifest.json
execution-plan.json
qualification.json
ci.json
summary.json
summary.md
results.xml
evidence-index.json
investigation.json
commands.jsonl
```

## Required scenario-level structure

```text
artifacts/<run-id>/scenarios/<scenario-id>/<test-case-id>/
  result.json
  adapter.log
  ha.log
  djconnect.log
  verification.log
  requests.jsonl
  responses.jsonl
  timing.json
  fixture-manifest.json
  storage-before.json
  storage-after.json
  metadata.json
  investigation.json
```

Only require files that apply to the test case, but record absent/not-applicable artifacts explicitly in the evidence index.

## Persistence requirements

- atomic writes where practical;
- write-to-temp then rename for critical JSON documents;
- explicit flush/finalize lifecycle;
- preserve partial evidence after crashes or cancellation;
- mark incomplete runs as `PARTIAL` rather than deleting them;
- redact before persistence;
- checksum important artifacts;
- record artifact schema versions;
- immutable paths referenced from reports;
- reopen and validate historical runs;
- retention policy that never silently removes the latest failed/blocked run;
- safe handling of large logs through rotation/chunking when necessary.

## Commands

Support existing CLI conventions, for example:

```bash
verification runs list
verification runs show <run-id>
verification runs verify <run-id>
verification runs evidence <run-id>
```

## Redaction

Never persist:

- HA access tokens;
- GitHub tokens;
- OAuth/provider secrets;
- APNs credentials/tokens;
- unrelated HA configuration;
- raw personal Ask DJ history;
- raw Music DNA contents;
- production identifiers where synthetic identifiers suffice.

Add tests for atomic writes, partial runs, crash recovery, checksums, immutable paths, reopening and redaction.

---

# Workstream 5 — Qualify the live WebSocket path

Use the real local Docker HA runtime and actual documented Home Assistant/DJConnect WebSocket commands.

Do not invent synthetic commands when real commands exist.

Qualify:

- authentication handshake;
- connection lifecycle;
- successful request/response;
- message IDs/correlation;
- subscription;
- event receipt;
- unsubscribe;
- controlled timeout;
- reconnect;
- malformed/unsupported command handling;
- authentication failure handling;
- redacted structured logging;
- durable evidence persistence.

Required test layers:

- unit tests;
- mocked transport tests;
- explicit opt-in live tests against Docker HA;
- one successful live command;
- one controlled error case;
- one subscribe/event/unsubscribe case when supported;
- one reconnect case.

Skipped live tests remain `SKIPPED`, never `PASS`.

Record raw protocol observations after canonical redaction so that the Verification Core, not the adapter, evaluates semantics.

---

# Workstream 6 — Qualify approved DJConnect storage paths

Qualify only the storage paths explicitly approved by Technical Design.

Never browse or modify arbitrary unrelated Home Assistant storage.

Qualify:

- approved storage discovery;
- read;
- snapshot;
- checksum;
- diff;
- persistence over container/HA restart;
- safe namespaced fixture changes;
- cleanup;
- post-run comparison;
- redaction;
- failure recovery.

## Direct mutation safeguards

Direct storage mutation is prohibited unless all are true:

- no supported public API/service exists for the required fixture operation;
- mutation is explicitly test-only;
- the exact DJConnect storage namespace is verified;
- runtime identity is confirmed as safe development/verification;
- a pre-mutation snapshot exists;
- restore is explicitly enabled;
- the mutation code rejects non-verification IDs;
- cleanup is idempotent;
- no non-test object can be changed.

## Required live persistence probe

At least one controlled live probe must prove:

1. create a namespaced verification fixture through the preferred public interface;
2. capture approved storage snapshot/checksum;
3. restart the Docker HA container or HA runtime according to the scenario;
4. wait for readiness;
5. prove the fixture persisted through raw observation and Scenario Engine assertion;
6. remove the fixture;
7. compare post-run storage with the pre-run state;
8. prove non-test state remained unchanged.

Preserve evidence before cleanup when a failure occurs.

---

# Workstream 7 — Repository hygiene, tooling and dependencies

Before implementation and each live qualification attempt:

- fetch and prune remotes;
- verify branch and exact SHA;
- verify clean working tree;
- verify no unpushed commits;
- verify no relevant open PRs affecting this scope;
- verify required CI for the baseline SHA;
- record Python, Docker, Home Assistant development tooling and package-manager versions;
- inspect third-party dependency freshness and security status;
- distinguish supported-but-outdated from unsupported/security-blocking;
- never silently update dependencies or lockfiles during qualification.

If tooling or dependency updates are required:

1. create a dedicated update commit/PR;
2. run CI;
3. merge;
4. restart remediation/qualification from clean `main`.

Record all decisions in the completion report.

---

# Workstream 8 — Dogfooding tests

Before rerunning Phase 9V, execute and record:

- Verification Core tests;
- Planning Engine tests;
- Execution Environment tests;
- Verification Data Framework tests;
- Modes and Policies tests;
- HA Adapter unit and mock tests;
- Investigator tests;
- evidence persistence tests;
- Docker discovery/safety tests;
- CI authentication/status tests;
- scenario schema validation;
- scenario catalog validation;
- live Docker HA preflight;
- live WebSocket probes;
- live approved-storage probes.

The framework must dogfood:

- its own environment snapshot;
- its own command log;
- its own evidence persistence;
- its own Investigator;
- its own CI qualification;
- its own rerun selection.

Do not claim dogfooding success without durable evidence from the current SHA.

---

# Workstream 9 — Failure ownership and fix cycle

For every failed probe or test:

1. preserve evidence;
2. run the Investigator;
3. classify the failure;
4. record confidence and evidence references;
5. identify the owning subsystem/repository;
6. decide whether human review is required;
7. apply only the smallest unambiguous fix;
8. commit fixes separately by owning subsystem;
9. create a new run ID;
10. rerun the changed subsystem's tests;
11. rerun the failed live probe;
12. rerun the relevant regression subset;
13. only then rerun the full five-scenario Phase 9V set.

Do not change the canonical expected behavior to fit current implementation.
Do not conflate environment failures with product failures.
Do not merge unrelated fixes.

---

# Phase 9V rerun preparation

Do not execute the final Phase 9V rerun until all remediation acceptance criteria are met.

Prepare an exact rerun command or follow-up prompt that:

- creates a new immutable run ID;
- runs full hygiene;
- validates interactive/non-interactive GitHub auth behavior;
- qualifies exact-SHA CI;
- discovers and qualifies Docker HA;
- generates the execution plan;
- runs only `PROFILE-001` through `PROFILE-005`;
- persists all evidence;
- invokes the Investigator for failures;
- creates the qualification report;
- stops before Phase 10.

Never overwrite the original failed Phase 9V evidence.

---

# Documentation and reports

Create:

`docs/verification/reports/PHASE_09R_QUALIFICATION_REMEDIATION.md`

Include:

- original blockers;
- root-cause classification;
- remediation per blocker;
- files and subsystems changed;
- Docker HA environment identity and metadata;
- GitHub authentication workflow;
- exact-SHA CI qualification behavior;
- Investigator implementation/status;
- evidence persistence implementation/status;
- live WebSocket qualification results;
- approved-storage qualification results;
- tests and commands executed;
- run IDs and immutable evidence paths;
- remaining limitations;
- explicit readiness for Phase 9V rerun.

Update as needed:

- Verification Platform backlog;
- Execution Environment documentation;
- HA Adapter documentation;
- Evidence Standard;
- CLI documentation;
- Implementation Gap Analysis status.

Do not rewrite the original Phase 9V report.

---

# Commit strategy

Use small logical commits, for example:

1. Docker HA environment discovery and safety qualification;
2. interactive `gh` auth and exact-SHA CI qualification;
3. durable evidence persistence and run-history commands;
4. executable Verification Investigator;
5. live WebSocket qualification;
6. approved-storage qualification;
7. dogfooding tests and documentation.

Do not combine unrelated product changes.

---

# Acceptance criteria

Phase 9R is complete only when:

- the local Docker HA runtime is discovered deterministically;
- container/image/source/config metadata are recorded;
- the runtime is proven to be the intended safe development environment;
- REST, WebSocket, logs and approved storage are reachable;
- local interactive runs can recover from invalid/missing `gh` auth through `gh auth login`;
- non-interactive runs never hang for auth;
- CI is qualified for the exact SHA;
- empty status responses are not treated as success;
- the Verification Investigator is executable and evidence-backed;
- low-confidence findings require human review;
- evidence is durable, immutable, redacted and crash-tolerant;
- historical/partial runs can be reopened and validated;
- live WebSocket success, error, subscription and reconnect paths are qualified where supported;
- approved DJConnect storage snapshot/diff/restart/cleanup behavior is qualified;
- no non-test HA data is modified;
- all relevant unit/mock/live tests are recorded;
- no new architecture subsystem was introduced;
- a fresh Phase 9V rerun is now possible.

Final Phase 9R result must be one of:

- `READY_FOR_PHASE_9V_RERUN`;
- `BLOCKED_WITH_EXTERNAL_PREREQUISITE`;
- `REMEDIATION_INCOMPLETE`.

When complete:

Stop.

Do not begin Phase 10.
Do not automatically execute Apple verification.
Return the exact recommended Phase 9V rerun command/prompt and the remaining blockers, if any.
