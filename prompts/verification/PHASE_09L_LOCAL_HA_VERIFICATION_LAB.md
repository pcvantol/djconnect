# Verification Program V1
## Phase 9L - Local Home Assistant Verification Lab

Repository: `pcvantol/djconnect`

Branch: follow `PROMPT_INDEX.md` and current PR instructions.

## Context

Phase 9V concluded:

`VERIFICATION PLATFORM NOT QUALIFIED`

Phase 9R implemented Docker HA discovery, exact-SHA CI qualification,
executable investigation and durable evidence. It also proved that the
existing local `homeassistant` container must not be used as the verification
runtime because it is not marked as a DJConnect verification/dev lab and does
not prove source/SHA identity.

This phase implements and qualifies a dedicated Docker-based local Home
Assistant verification lab.

Do not create a new Verification subsystem. Extend only existing Verification
subsystems:

- Verification Execution Environment;
- Verification Core;
- Verification Evidence;
- Home Assistant Verification Adapter;
- CLI surfaces already owned by the Verification Harness.

Do not execute Phase 10.

## Mission

Create a safe, reproducible local HA verification lab that can satisfy the live
runtime prerequisites for a fresh Phase 9V rerun.

The lab must be isolated from production Home Assistant data, secrets and
volumes.

Final result must be exactly one:

`LOCAL_VERIFICATION_LAB_QUALIFIED`

or

`LOCAL_VERIFICATION_LAB_NOT_QUALIFIED`

## Read First

Read:

- `BOOTSTRAP_CODEX_VERIFICATION.md`;
- `PROMPT_INDEX.md`;
- `AGENTS.md`;
- `docs/verification/08_VERIFICATION_EXECUTION_ENVIRONMENT.md`;
- `docs/verification/09_HOME_ASSISTANT_VERIFICATION_ADAPTER.md`;
- `docs/verification/reports/PHASE_09V_VERIFICATION_PLATFORM_QUALIFICATION.md`;
- `docs/verification/reports/PHASE_09R_QUALIFICATION_REMEDIATION.md`;
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`;
- `prompts/verification/PHASE_09R_QUALIFICATION_REMEDIATION.md`;
- current Docker/Compose files in this repository, if any;
- current verification CLI implementation;
- current evidence/run-store implementation;
- current HA adapter implementation.

Treat the existing architecture as frozen.

## Scope

Allowed:

- dedicated Dockerfile or Compose definition for the verification lab;
- lab configuration templates with no secrets;
- Execution Environment Docker lab lifecycle support;
- CLI commands for lab build/start/stop/restart/recreate/fresh/clean/destroy;
- HA runtime qualification probes;
- exact-SHA CI qualification integration;
- deterministic seed/generator metadata in evidence;
- Planning CLI fail-closed improvements;
- immutable per-run artifacts;
- report and backlog updates;
- unit/mock tests and safe local integration probes.

Not allowed:

- product feature work;
- Apple, Windows, Pi, ESP32 or Voice adapter work;
- scenario expectation changes merely to pass verification;
- use of production HA volumes, tokens or config;
- committing secrets;
- new top-level Verification architecture subsystem.

## Workstream 1 - Inspect Existing Docker State

Inspect existing Docker and Compose setup without mutating it.

Record:

- Docker Engine version;
- Docker Compose version;
- running/stopped Home Assistant containers;
- container labels;
- port mappings;
- bind mounts;
- named volumes;
- image tags and digests;
- whether any container is safe for verification.

If an existing container is not explicitly marked as verification/dev and does
not mount this repository as the DJConnect source, classify it as unsafe and do
not mutate it.

## Workstream 2 - Dedicated Lab Definition

Create a dedicated lab definition if no suitable one exists.

Requirements:

- dedicated Home Assistant container name;
- explicit verification labels, including `djconnect.verification=true`;
- no production volumes;
- no production secrets;
- no copied production config;
- dedicated config directory or volume;
- dedicated storage directory or volume;
- dedicated log directory or volume;
- DJConnect source mounted read-only or copied from the tested repository
  state according to the chosen lab mode;
- exact repository SHA recorded;
- source fingerprint recorded;
- HA image tag pinned or recorded;
- image digest recorded when available;
- host port configurable, defaulting to a non-conflicting verification port
  when `8123` is already owned by another container;
- fixture namespace configured for verification only.

The lab definition may live under a repository-native verification path, for
example:

```text
verification/lab/home_assistant/
```

Use actual repository naming conventions after inspection.

## Workstream 3 - Secrets And Tokens

Secrets must be externalized.

Support:

- HA token through environment variable or ignored local config;
- GitHub token through `GH_TOKEN` for non-interactive runs;
- interactive `gh auth login` only when the run is local and attached to a TTY;
- clear non-interactive failure when neither `gh auth status` nor `GH_TOKEN`
  can satisfy CI qualification.

Never:

- commit tokens;
- print tokens;
- write tokens to evidence;
- copy tokens into Docker Compose files.

## Workstream 4 - Lifecycle Commands

Extend the existing CLI conventions with safe lab lifecycle operations.

Support:

- `build` - build or pull the dedicated lab image/config;
- `start` - start the intended lab container;
- `stop` - stop only the intended lab container;
- `restart` - restart only the intended lab container;
- `recreate` - recreate the intended lab while preserving only approved lab
  volumes;
- `fresh` - create a disposable clean lab state;
- `clean` - remove run-specific logs/temp files only;
- `destroy` - remove the dedicated lab container and approved lab volumes only,
  requiring explicit destructive opt-in.

Never remove unrelated containers or volumes.

## Workstream 5 - Qualification Gates

The lab doctor must fail closed unless all required gates pass:

- Docker daemon reachable;
- Compose available or not required;
- exactly one intended lab container selected;
- expected host port belongs to that container;
- explicit verification/dev labels present;
- no production HA config/volume detected;
- repository source mount or copy matches recorded SHA/fingerprint;
- HA starts and responds to REST;
- authentication works with the configured token;
- WebSocket connects and can perform a harmless command;
- DJConnect integration is loaded from the intended source;
- approved storage path is reachable;
- logs are reachable;
- fixture namespace is safe;
- exact-SHA CI is qualified or explicitly blocked before live scenario
  execution;
- all evidence paths are under the configured artifact/evidence root.

If any gate fails, stop before scenario execution and produce a lab report.

## Workstream 6 - REST, WebSocket, Storage And Logs

Qualify runtime primitives without asserting product behavior:

- REST: `/api/`, `/api/config` and at least one harmless authenticated route;
- WebSocket: connect, authenticate, send harmless command, receive response,
  close cleanly;
- storage: snapshot only approved DJConnect storage keys or record absent keys;
- logs: collect sanitized HA logs from the dedicated lab only.

The adapter must return raw structured results and leave success evaluation to
the Verification Core.

## Workstream 7 - Deterministic Evidence

Every qualification run must persist immutable evidence including:

- run ID;
- environment ID;
- correlation ID;
- repository branch and SHA;
- source fingerprint;
- Docker/Compose versions;
- HA image tag and digest;
- container metadata;
- lab config fingerprint;
- exact-SHA CI decision;
- data seed;
- generator versions;
- data profile;
- matrix profile;
- mode and policy;
- REST/WebSocket/storage/log probe results;
- redaction manifest;
- checksums.

Never overwrite a previous run.

## Workstream 8 - Planning Fail-Closed Behavior

Ensure the Planning CLI cannot silently plan from the wrong scenario source.

Requirements:

- canonical scenario path must be explicit or repository-defaulted;
- missing canonical scenario files must fail;
- schema examples must not be accepted as the live scenario catalog for Phase
  9V qualification;
- generated plan must list scenario IDs, matrix profile, data profile, mode,
  policy, expected adapter and expected evidence.

## Workstream 9 - Tests

Add focused tests for:

- lab container discovery;
- unsafe existing HA container classification;
- explicit verification label recognition;
- wrong port ownership;
- wrong source SHA/fingerprint;
- production volume rejection;
- no-token auth classification;
- `GH_TOKEN` non-interactive behavior;
- interactive auth gating;
- WebSocket probe result handling;
- approved storage allowlist;
- immutable evidence persistence;
- planning fail-closed scenario path behavior;
- lifecycle command safety.

Run the affected tests and the verification regression subset documented in
the Phase 9R report.

## Workstream 10 - Report

Create:

```text
docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md
```

Include:

- final result line;
- environment;
- Docker/Compose versions;
- lab definition path;
- image and digest;
- container labels;
- source SHA/fingerprint;
- safety decision;
- REST/WebSocket/storage/log qualification;
- CI qualification;
- evidence path;
- tests run;
- failures and classifications;
- unresolved external prerequisites;
- readiness for Phase 9V rerun.

Update:

- `PROMPT_INDEX.md`;
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`;
- verification README/navigation files where useful.

## Acceptance Criteria

Phase 9L is complete when:

- a dedicated Docker-based HA verification lab exists or an existing lab is
  proven suitable;
- production HA state cannot be mutated by the lab workflow;
- lab lifecycle commands are safe and scoped;
- lab qualification fails closed;
- REST, WebSocket, approved storage and logs are qualified or reported as
  blocking;
- exact-SHA CI qualification behavior is deterministic;
- deterministic data seed and generator versions are included in evidence;
- planning uses the canonical scenario catalog and fails closed otherwise;
- immutable evidence artifacts are produced;
- tests pass;
- report exists with one final result line;
- Phase 9V rerun is either unblocked or has precise remaining prerequisites.

Stop after the Phase 9L report.

Do not execute Phase 9V rerun unless a later prompt explicitly asks for it.
Do not start Phase 10.
