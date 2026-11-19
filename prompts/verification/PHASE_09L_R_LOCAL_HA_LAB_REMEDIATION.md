# Verification Program V1
## Phase 9L-R - Local Home Assistant Verification Lab Remediation

Repository: `pcvantol/djconnect`

## Context

Phase 9L produced:

`LOCAL_VERIFICATION_LAB_NOT_QUALIFIED`

The dedicated local HA verification lab definition exists and the framework
now fails closed, but live lab qualification is blocked.

Ground truth for this remediation:

- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- evidence run `phase-09l-local-ha-lab-20260710T1450Z`
- Phase 9L implementation under `verification/lab/home_assistant/`
- `HALocalVerificationLab` in `tools/verification/environment/docker_ha.py`

Do not assume Phase 9L is qualified.
Do not execute Phase 9V rerun.
Do not start Phase 10.

## Mission

Remediate only the proven Phase 9L blockers:

1. Docker Compose start timed out and left `djconnect-verification-ha` in
   `Created` state.
2. Docker inspect/log probes were unreliable after the start timeout.
3. `DJCONNECT_VERIFICATION_HA_TOKEN` was missing.
4. REST and WebSocket live probes could not qualify because the lab was not
   running and authenticated.

The target outcome is:

`LOCAL_VERIFICATION_LAB_QUALIFIED`

If that cannot be achieved, produce an updated NOT QUALIFIED report with the
smallest remaining external prerequisite.

## Read First

Read:

- `BOOTSTRAP_CODEX_VERIFICATION.md`;
- `PROMPT_INDEX.md`;
- `prompts/verification/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`;
- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`;
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`;
- `verification/lab/home_assistant/README.md`;
- `verification/lab/home_assistant/compose.yaml`;
- `tools/verification/environment/docker_ha.py`;
- `tools/verification/cli.py`;
- `tests/verification/test_phase_09l_local_ha_lab.py`;
- evidence under `artifacts/verification/evidence/phase-09l-local-ha-lab-20260710T1450Z/` when available locally.

Treat the existing Verification architecture as frozen.

## Scope Control

Allowed:

- fix the dedicated HA lab Compose definition;
- fix lab lifecycle commands and timeouts;
- fix lab discovery when a container is `Created`, unhealthy or has no ports;
- add safe cleanup for only the dedicated lab container;
- add better diagnostics for `Created`/stuck lab containers;
- add or document a safe local HA token bootstrap flow;
- add live REST/WebSocket qualification once the lab is running and a token is
  provided externally;
- update Phase 9L report, backlog, tests and prompt index;
- add focused tests for the remediated blockers.

Not allowed:

- mutate existing production-like `homeassistant` containers;
- delete unrelated Docker containers or volumes;
- commit secrets or generated runtime artifacts;
- weaken safety gates to mark an unproven runtime as qualified;
- change scenario expected behavior;
- create a new Verification subsystem;
- execute Phase 9V rerun;
- start Phase 10.

## Required Remediation Steps

### 1. Inspect Current Lab State

Inspect without destructive mutation:

```bash
docker ps -a --filter name=djconnect-verification-ha
docker inspect djconnect-verification-ha
docker compose -f verification/lab/home_assistant/compose.yaml ps
```

If Docker inspect hangs, record that as an environment issue and use only safe
Docker commands that complete.

### 2. Recover Only The Dedicated Lab Container

If `djconnect-verification-ha` is stuck in `Created` state, recover it using
only dedicated lab lifecycle commands or explicit dedicated-container Docker
commands.

Allowed cleanup targets:

- container named `djconnect-verification-ha`;
- volumes created by `djconnect-verification-ha` / `djconnect-verification-ha`
  compose project;
- runtime path `artifacts/verification/lab/home_assistant/`.

Do not touch any other Home Assistant container.

### 3. Fix Lifecycle Reliability

Make `lab ha start`, `recreate`, `fresh`, `clean` and `destroy` deterministic.

Requirements:

- lifecycle commands must time out with a clear diagnostic;
- a timed-out start must leave enough metadata for investigation;
- doctor must not hang when Docker inspect/logs hang;
- doctor must classify `Created`, `Exited`, `Restarting`, `Unhealthy`,
  missing port, missing label and wrong source SHA distinctly;
- `destroy` remains blocked without `--allow-destructive`.

### 4. Token Handling

Do not commit or print tokens.

Support one of:

- operator-provided `DJCONNECT_VERIFICATION_HA_TOKEN`;
- documented manual token creation after the lab starts;
- a safe, explicit local-only bootstrap helper that creates a token inside the
  dedicated lab without exposing it in logs.

If no token can be created safely, keep the lab NOT QUALIFIED and record the
operator prerequisite.

### 5. Qualify Live Runtime

Run:

```bash
python3 -m tools.verification.cli lab ha doctor
```

The doctor must prove:

- Docker daemon reachable;
- Docker Compose reachable;
- exactly one intended lab container selected;
- expected port belongs to that container;
- verification labels present;
- source SHA/fingerprint proven;
- no production volume detected;
- container running;
- token provided externally;
- REST probe passes;
- WebSocket probe passes;
- approved storage path reachable;
- logs reachable;
- exact-SHA CI remains qualified or explicitly blocked before live scenario
  execution.

### 6. Evidence

Create a new immutable evidence run under:

```text
artifacts/verification/evidence/
```

Record:

- run id;
- branch and SHA;
- Docker/Compose versions;
- lab metadata;
- lifecycle commands executed;
- token source status without token value;
- REST/WebSocket/storage/log probe results;
- exact-SHA CI decision;
- final lab doctor result;
- checksums.

Do not commit evidence artifacts.

### 7. Tests

Run:

```bash
python3 -m unittest tests.verification.test_phase_09l_local_ha_lab
python3 -m unittest tests.verification.test_home_assistant_adapter tests.verification.test_planning_engine tests.verification.test_execution_environment tests.verification.test_core_implementation tests.verification.test_harness_scaffold tests.verification.test_phase_09r_remediation tests.verification.test_phase_09l_local_ha_lab
git diff --check
```

Add focused tests for any lifecycle or doctor behavior changed.

## Deliverables

Update:

- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`;
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`;
- `PROMPT_INDEX.md`;
- tests and implementation files required by the remediation.

If qualified, the report must contain:

`LOCAL_VERIFICATION_LAB_QUALIFIED`

If not qualified, the report must contain:

`LOCAL_VERIFICATION_LAB_NOT_QUALIFIED`

with exact remaining blockers.

## Stop Condition

Stop after the updated Phase 9L remediation report.

Do not execute Phase 9V rerun.
Do not start Phase 10.
