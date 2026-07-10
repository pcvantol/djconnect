# Phase 09L - Local Home Assistant Verification Lab

Final result: LOCAL_VERIFICATION_LAB_NOT_QUALIFIED

Date: 2026-07-10
Repository: `pcvantol/djconnect`
Branch: `codex-phase-09l-local-ha-verification-lab`
Tested SHA: `3e6f3eb76850a268b0148f5b0a51f82255fe0ea0`

## Decision

Phase 9L created the repository-native dedicated Docker Home Assistant
verification lab definition and safe lifecycle/doctor commands, but the lab is
not yet qualified for live Phase 9V execution.

The framework now fails closed with precise blockers instead of falling back to
an existing production-like `homeassistant` container.

## Lab Definition

Path:

```text
verification/lab/home_assistant/
```

Files:

- `verification/lab/home_assistant/compose.yaml`
- `verification/lab/home_assistant/configuration.yaml`
- `verification/lab/home_assistant/README.md`

Default runtime paths:

- Lab root: `artifacts/verification/lab/home_assistant`
- Config/storage: `artifacts/verification/lab/home_assistant/config`
- Log: `artifacts/verification/lab/home_assistant/config/home-assistant.log`

The runtime root is ignored by git through `.gitignore`.

## Safety Properties Implemented

- Dedicated container name: `djconnect-verification-ha`
- Default host port: `18123`
- Explicit verification label: `djconnect.verification=true`
- Phase label: `djconnect.phase=9L`
- Repository label: `djconnect.repository=pcvantol/djconnect`
- Source SHA label support
- Source fingerprint label support
- Dedicated runtime root under `artifacts/`
- DJConnect source mounted from this repository
- Production Home Assistant mount rejection
- Destructive `destroy` requires explicit `--allow-destructive`

## CLI

Implemented:

```bash
python3 -m tools.verification.cli lab ha metadata
python3 -m tools.verification.cli lab ha build
python3 -m tools.verification.cli lab ha start
python3 -m tools.verification.cli lab ha stop
python3 -m tools.verification.cli lab ha restart
python3 -m tools.verification.cli lab ha recreate
python3 -m tools.verification.cli lab ha fresh
python3 -m tools.verification.cli lab ha clean
python3 -m tools.verification.cli lab ha destroy --allow-destructive
python3 -m tools.verification.cli lab ha doctor
```

All lifecycle operations are scoped to the dedicated Compose definition.

## Environment Observed

Docker:

- Docker Engine reachable
- Docker Engine version: `29.6.1`
- Docker Desktop: `4.81.0`

Compose:

- Docker Compose reachable
- Compose version: `v5.3.0`

CI:

- Exact-SHA CI decision: `CI_PASS`
- Workflows inspected for SHA `3e6f3eb76850a268b0148f5b0a51f82255fe0ea0`:
  - `Validate Home Assistant custom integration`
  - `CodeQL`

## Live Qualification Attempt

Commands attempted:

```bash
python3 -m tools.verification.cli lab ha metadata
python3 -m tools.verification.cli lab ha doctor
python3 -m tools.verification.cli lab ha start
python3 -m tools.verification.cli lab ha doctor
```

Observed:

- Lab metadata command succeeded.
- Initial lab doctor failed because no dedicated lab container was selected.
- Lab start attempted through Docker Compose.
- Docker Compose created `djconnect-verification-ha`, but the lifecycle command
  timed out while running `docker compose up -d`.
- The dedicated lab container remained in `Created` state.
- Subsequent Docker inspect/log probing did not complete reliably.

No production Home Assistant container was mutated by the lab workflow.

## Qualification Gates

| Gate | Result | Notes |
| --- | --- | --- |
| Docker daemon reachable | PASS | Docker responded. |
| Docker Compose reachable | PASS | Compose responded. |
| Lab definition exists | PASS | Compose file exists in repository. |
| Exactly one intended lab container | BLOCKED | Container exists but did not become a qualified running candidate. |
| Expected port belongs to lab container | BLOCKED | Container remained `Created`; port ownership not proven. |
| Verification labels present | BLOCKED | Docker inspect did not complete reliably after start timeout. |
| Source SHA/fingerprint proven | BLOCKED | Runtime source identity not proven live. |
| No production volume detected | BLOCKED | Runtime mount inspection not completed live. |
| HA token provided externally | BLOCKED | `DJCONNECT_VERIFICATION_HA_TOKEN` not configured. |
| REST reachable | BLOCKED | Requires running lab and token. |
| WebSocket reachable | BLOCKED | Requires running lab and token. |
| Approved storage reachable | PASS | Dedicated path exists after lifecycle preparation. |
| Logs reachable | PASS path / BLOCKED runtime | Dedicated log path exists; live HA logs not available. |
| Exact-SHA CI | PASS | Existing CI is green for tested SHA. |
| Immutable evidence | PASS | Evidence run created under `artifacts/verification/evidence/`. |

## Evidence

Run ID:

```text
phase-09l-local-ha-lab-20260710T1450Z
```

Evidence files were written under:

```text
artifacts/verification/evidence/phase-09l-local-ha-lab-20260710T1450Z/
```

Artifacts are intentionally ignored by git.

Included:

- lab metadata;
- exact-SHA CI decision;
- summary;
- evidence index with checksums.

## Tests Run

```bash
python3 -m unittest tests.verification.test_phase_09l_local_ha_lab
python3 -m unittest tests.verification.test_phase_09r_remediation tests.verification.test_harness_scaffold tests.verification.test_planning_engine
```

Results:

- Phase 9L focused tests: 8 passed.
- Regression subset: 20 passed.
- Scenario validation covered 231 canonical scenarios.

## Implementation Summary

Implemented within existing Verification subsystems:

- HA lab Compose definition and configuration template;
- `HALocalVerificationLab` lifecycle and qualification workflow in the
  Execution Environment;
- Docker discovery support for explicit lab containers without hiding port
  failures;
- source SHA and source fingerprint metadata;
- production volume rejection;
- lab CLI commands under the existing Verification CLI;
- canonical scenario catalog default path;
- `.gitignore` protection for runtime artifacts;
- Phase 9L focused tests.

No new Verification architecture subsystem was introduced.

## Failure Classification

| Failure | Classification | Owner | Blocking | Recommended action |
| --- | --- | --- | --- | --- |
| Docker Compose start timed out and container remained `Created` | Environment issue | Verification Execution Environment / local Docker | Yes | Inspect Docker Desktop/Compose state, remove/recreate only the dedicated lab container with approved lifecycle commands, rerun lab doctor. |
| Docker inspect/log probe unreliable after start timeout | Environment issue | Local Docker | Yes | Stabilize Docker runtime before live qualification. |
| HA token missing | Environment issue | Operator / Verification Environment | Yes | Provide `DJCONNECT_VERIFICATION_HA_TOKEN` externally after the lab starts and a least-privilege token exists. |
| REST/WebSocket not qualified | Environment issue / HA Adapter live prerequisite | Yes | Rerun `lab ha doctor` after running lab and token are available. |

## Readiness For Phase 9V Rerun

Phase 9V rerun remains blocked.

Required before rerun:

1. Dedicated lab container reaches running state.
2. Docker inspect reports verification labels and source mount identity.
3. Expected host port `18123` is owned by the lab container.
4. A non-committed HA token is provided externally.
5. REST and WebSocket probes pass.
6. Approved storage and log collection are live-proven.
7. `python3 -m tools.verification.cli lab ha doctor` returns
   `LOCAL_VERIFICATION_LAB_QUALIFIED`.

Do not execute Phase 9V rerun or Phase 10 until this report changes to a
qualified result in a later commit.
