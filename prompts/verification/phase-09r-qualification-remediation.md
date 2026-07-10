# Verification Program V1
## Phase 9R — Verification Platform Qualification Remediation

Repository: `pcvantol/djconnect`

## Context

Phase 9V concluded:

`VERIFICATION PLATFORM NOT QUALIFIED`

Blocking findings:

1. the local Home Assistant runtime was not detected or qualified;
2. local `gh` authentication was invalid, so mandatory CI status could not be validated through the CLI;
3. the GitHub connector returned no usable commit-status result;
4. no executable Verification Investigator exists;
5. evidence is not persisted durably enough as immutable run artifacts;
6. the live WebSocket and approved DJConnect storage paths are not qualified.

Additional environment facts:

- the local Home Assistant development runtime runs in Docker;
- local interactive verification runs may launch `gh auth login` when `gh auth status` reports missing or invalid authentication;
- non-interactive runs must never wait for an interactive login.

Dogfooding showed that Planning, Core, Execution Environment and the HA Adapter have tests, but the Investigator and live HA paths remain insufficiently proven.

Phase 10 — Apple Verification Adapter remains blocked.

This phase remediates only the qualification blockers and prepares a clean Phase 9V rerun.

Do not add new architecture layers.
Do not broaden the scenario set.
Do not begin Apple work.

---

## Mission

Turn each Phase 9V blocker into one of:

- fixed and verified;
- safely waived with explicit evidence;
- still blocked with a precise external prerequisite.

The required outcome is a reproducible, evidence-backed rerun of Phase 9V against the local Docker-based Home Assistant development runtime.

---

## Read first

Read completely:

- `AGENTS.md`;
- the Phase 9V qualification report;
- Verification Platform scorecard and backlog;
- Verification Core;
- Verification Planning Engine;
- Verification Execution Environment;
- Verification Data Framework;
- Verification Modes and Policies;
- Home Assistant Verification Adapter;
- Evidence model and run-artifact model;
- Repository Hygiene and Build Qualification rules;
- current CI integration;
- current Docker-based HA development documentation/configuration;
- Technical Design Reconstruction;
- exact definitions for `PROFILE-001` through `PROFILE-005`.

Use current repository paths and interfaces. Do not invent parallel implementations when an existing subsystem can be extended.

---

# Workstream 1 — Qualify the Docker-based Home Assistant development runtime

Treat Docker as the authoritative local HA execution environment.

Implement or complete runtime discovery and qualification for the intended HA development container.

Required discovery data:

- Docker Engine version;
- Docker Compose version where applicable;
- container name;
- container ID;
- image repository/tag;
- image digest;
- creation/start timestamp;
- container health/status;
- exposed ports;
- network mode;
- relevant bind mounts;
- relevant volumes;
- HA config path inside the container;
- HA storage path inside the container;
- mounted DJConnect integration path;
- mounted source fingerprint and expected Git SHA;
- container environment fingerprint with secrets redacted.

Required validation:

- Docker daemon reachable;
- intended HA container found;
- no duplicate stale HA dev container owns the same port;
- container is running and healthy, or can be started deterministically;
- runtime is explicitly identified as development/test and not production;
- HA is reachable on the expected URL/port;
- authentication works;
- DJConnect loads from the recorded source SHA;
- REST is reachable;
- WebSocket is reachable;
- approved DJConnect storage is mounted and accessible;
- container logs are accessible;
- runtime is safe for namespaced verification mutations.

Add a deterministic preflight command following current CLI conventions, for example:

```bash
verification doctor --environment ha-docker
```

It must return structured results and one of:

- `READY`;
- `BLOCKED_DOCKER_UNAVAILABLE`;
- `BLOCKED_CONTAINER_NOT_FOUND`;
- `BLOCKED_WRONG_RUNTIME`;
- `BLOCKED_SOURCE_SHA_MISMATCH`;
- `BLOCKED_HA_UNHEALTHY`;
- `BLOCKED_AUTHENTICATION`;
- `BLOCKED_STORAGE`;
- `BLOCKED_ENVIRONMENT`.

Support and document three distinct lifecycle operations:

- `restart`: same container, same persistent state;
- `recreate`: new container, same approved persistent volumes;
- `fresh`: new container with a dedicated disposable verification storage volume.

Do not remove unrelated containers or volumes.
Do not wipe persistent state unless the selected scenario explicitly requires a fresh environment.

Before each qualification run:

1. stop stale duplicate HA development containers;
2. verify only the intended container owns the configured HA port;
3. archive or clear dedicated verification logs;
4. remove stale Python bytecode from the mounted DJConnect integration;
5. verify mounted source matches the recorded SHA;
6. recreate only when the run requires a clean runtime;
7. record every Docker command executed;
8. write container/image metadata to the reproducibility manifest.

If the runtime cannot be proven safe, stop before mutation.

---

# Workstream 2 — Interactive GitHub CLI authentication and CI qualification

Fix CI qualification while keeping the local developer workflow practical.

## Interactive local authentication

When running locally in an interactive terminal:

1. execute `gh auth status`;
2. if authentication is valid, continue;
3. if authentication is missing, expired or invalid:
   - explain that GitHub authentication is required for exact-SHA CI qualification;
   - start `gh auth login`;
   - allow the user to complete the browser/device flow;
   - never automate credential entry;
   - never capture or persist the token;
   - rerun `gh auth status` after completion;
4. if authentication still fails, stop with `BLOCKED_CI_AUTH`.

Add or support a clear local option following existing CLI conventions, for example:

```bash
verification doctor --fix-auth
verification run --interactive-auth
```

Do not show the interactive login on every run. Trigger it only when authentication validation fails and a TTY is available.

## Non-interactive execution

For CI/nightly/non-TTY execution:

- never wait for interactive login;
- use an approved `GH_TOKEN` or configured credential source when present;
- otherwise stop with `BLOCKED_CI_AUTH` and actionable instructions;
- never log token values.

## Exact-SHA CI qualification

Do not couple qualification exclusively to the `gh` CLI.

Preferred evidence order:

1. authenticated GitHub CLI/API data for the exact SHA;
2. GitHub Actions workflow runs for the exact SHA;
3. required jobs and conclusions;
4. workflow artifacts and metadata;
5. connector data where available.

Distinguish explicitly:

- no workflow configured;
- workflow not triggered;
- workflow queued/running;
- workflow passed;
- workflow failed;
- workflow cancelled/timed out;
- authentication unavailable;
- provider returned no data;
- commit-status endpoint empty;
- SHA mismatch.

Rules:

- never accept CI from another SHA;
- never treat an empty status response as success;
- record workflow run IDs, workflow names, job names and conclusions;
- record artifacts where relevant;
- allow a documented waiver only when required CI genuinely does not exist;
- a local green build does not override failing required CI.

Add tests for:

- valid auth;
- invalid auth with TTY;
- invalid auth without TTY;
- successful post-login recheck;
- failed post-login recheck;
- empty commit-status result;
- no workflows;
- running workflow;
- failed workflow;
- successful exact-SHA workflow;
- SHA mismatch.

---

# Workstream 3 — Implement the executable Verification Investigator

Implement the Verification Investigator as a workflow inside the existing Verification Core.

Do not create a new architecture subsystem.

The Investigator consumes:

- scenario result;
- scenario assertions;
- generated test-case metadata;
- execution plan;
- adapter operations;
- environment snapshot;
- logs;
- requests/responses;
- storage diffs;
- CI metadata;
- build/runtime qualification metadata;
- evidence index.

It produces a structured investigation record with at least:

```text
failure_id
run_id
scenario_id
test_case_id
classification
confidence
evidence_references
probable_owner
blocking_status
recommended_action
rerun_scope
human_review_required
```

Canonical classifications:

- `scenario_defect`;
- `scenario_ambiguity`;
- `data_generator_defect`;
- `matrix_defect`;
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

Rules:

- never change expected results automatically;
- never modify product code automatically;
- never claim certainty unsupported by evidence;
- confidence below the configured threshold requires human review;
- Foundation or architecture mismatches require an ADR proposal;
- recommended fixes must identify the owning subsystem/repository;
- Investigator output is advisory until accepted by the execution workflow or human reviewer.

Add CLI integration using existing conventions, for example:

```bash
verification investigate <run-id>
verification investigate <run-id> --scenario PROFILE-001
```

Add deterministic tests using synthetic evidence bundles for every major classification, including `unknown`.

---

# Workstream 4 — Durable, immutable run artifact persistence

Implement durable, append-only run artifact persistence.

Every run must have a unique directory:

```text
artifacts/<run-id>/
```

A run directory must never be reused or overwritten.

Required run-level artifacts:

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
```

Required scenario/test-case structure:

```text
artifacts/<run-id>/scenarios/<scenario-id>/<test-case-id>/
  result.json
  adapter.log
  ha.log
  djconnect.log
  requests.jsonl
  responses.jsonl
  timing.json
  fixture-manifest.json
  storage-before.json
  storage-after.json
  metadata.json
```

Requirements:

- atomic writes where practical;
- explicit flush/finalize lifecycle;
- preserve partial evidence after process crashes;
- redact before persistence;
- checksum important artifacts;
- record schema versions;
- reference immutable evidence paths from reports;
- reopen and inspect historical runs;
- verify artifact integrity;
- support retention without silently deleting the newest failed run;
- never mix artifacts from different runs.

Add CLI support following existing conventions, for example:

```bash
verification runs list
verification runs show <run-id>
verification runs verify <run-id>
```

Never persist:

- HA tokens;
- GitHub tokens;
- OAuth credentials;
- provider secrets;
- unrelated HA configuration;
- raw private Ask DJ history;
- full private Music DNA;
- unredacted authentication headers.

---

# Workstream 5 — Qualify the live WebSocket path

Qualify the real Home Assistant WebSocket path against the Docker runtime.

Verify:

- authentication;
- connection lifecycle;
- one documented successful command;
- request/response correlation;
- subscription;
- event receipt;
- unsubscribe;
- timeout behavior;
- reconnect behavior;
- controlled malformed-command handling;
- structured/redacted logging;
- durable evidence persistence.

Use actual documented HA/DJConnect WebSocket commands from the route inventory.
Do not invent synthetic commands when real commands exist.

Add:

- unit tests;
- mock transport tests;
- explicit opt-in live tests;
- one successful live command case;
- one controlled error case;
- one reconnect/subscription case where supported.

Skipped live tests remain `SKIPPED`, never `PASS`.

---

# Workstream 6 — Qualify approved DJConnect storage

Qualify only the approved DJConnect storage paths documented by Technical Design.

Verify:

- storage discovery;
- safe read;
- snapshot;
- checksum;
- diff;
- persistence over container/HA restart;
- namespaced fixture changes;
- cleanup;
- post-run comparison;
- redaction;
- failure recovery.

Direct storage mutation is prohibited unless all are true:

- no supported public API exists;
- mutation is explicitly test-only;
- the exact storage namespace is verified;
- a pre-mutation snapshot exists;
- restore is explicitly enabled;
- namespaced fixtures are used;
- no non-test objects can be changed.

At least one live scenario must prove:

1. namespaced fixture created;
2. storage snapshot captured;
3. HA/container restarted using the correct lifecycle operation;
4. fixture persisted;
5. fixture removed;
6. non-test state remained unchanged.

---

# Workstream 7 — Tests and dogfooding

Before the qualification rerun, execute and record:

- Verification Core tests;
- Planning Engine tests;
- Execution Environment tests;
- Data Framework tests;
- Modes/Policies tests;
- HA Adapter tests;
- Investigator tests;
- evidence persistence tests;
- schema validation;
- scenario catalog validation;
- Docker runtime preflight;
- live WebSocket qualification tests;
- live approved-storage qualification tests;
- CI qualification tests.

The framework must dogfood:

- its own evidence persistence;
- its own Investigator;
- its own CI qualification;
- its own environment snapshot;
- its own rerun planning;
- its own immutable run history.

Record exact commands, timestamps and outcomes.

---

# Workstream 8 — Rerun strategy

Do not rerun all scenarios after every change.

Use this order:

1. unit/mock tests for the changed subsystem;
2. blocker-specific live probe;
3. affected scenario only;
4. relevant regression subset;
5. full `PROFILE-001` through `PROFILE-005` qualification set.

Use the same deterministic seed where comparison is useful.
Create a new run ID for every qualification attempt.
Never overwrite original Phase 9V evidence.

---

# Repository hygiene and implementation policy

Before code changes:

- fetch/prune remotes;
- verify current branch and SHA;
- verify relevant open PRs;
- verify clean worktree;
- verify no unpushed commits;
- verify required CI where possible;
- clean old dedicated verification logs/artifacts;
- create a dedicated branch from current `main`.

If dependency/tooling updates are required:

- make them in a separate focused PR;
- merge;
- restart Phase 9R from clean `main`;
- do not silently mutate lockfiles during qualification.

Only make changes necessary to remove Phase 9V blockers.
Do not redesign product architecture.
Do not broaden scenario scope.

---

# Reporting

Create:

`docs/verification/reports/PHASE_09R_QUALIFICATION_REMEDIATION.md`

Include:

- original blockers;
- root cause per blocker;
- remediation per blocker;
- files changed;
- tests added;
- Docker HA environment details;
- interactive `gh auth` behavior;
- exact-SHA CI qualification behavior;
- Investigator status;
- evidence persistence status;
- WebSocket qualification;
- storage qualification;
- dogfooding results;
- remaining limitations;
- rerun IDs;
- final readiness for a Phase 9V rerun.

Update as needed:

- Verification Platform backlog;
- Implementation Gap Analysis;
- Execution Environment documentation;
- HA Adapter documentation;
- Evidence documentation;
- CI qualification documentation.

Do not rewrite the original Phase 9V report.

---

# Acceptance criteria

Phase 9R is complete only when:

- the Docker-based local HA runtime is discovered and reproducibly qualified;
- preflight proves it is the intended safe development runtime;
- mounted DJConnect source matches the recorded SHA;
- interactive local `gh auth login` is offered only when required and a TTY exists;
- non-interactive runs fail fast without credentials;
- exact-SHA CI qualification works without treating empty status responses as success;
- the Verification Investigator is executable;
- Investigator output is structured and evidence-backed;
- run artifacts persist durably and immutably;
- partial/failed runs preserve evidence;
- historical run integrity can be verified;
- live WebSocket behavior is qualified;
- approved DJConnect storage behavior is qualified;
- all relevant unit/mock/live tests are recorded;
- no new architecture layer was introduced;
- the platform is ready for a fresh Phase 9V rerun.

When complete:

Stop.

Do not begin Phase 10.

Return:

- completion summary;
- commits;
- tests and live probes executed;
- remaining blockers;
- PR link;
- exact command or prompt for the new Phase 9V rerun.
