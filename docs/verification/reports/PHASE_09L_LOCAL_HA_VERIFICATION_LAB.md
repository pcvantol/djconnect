# Phase 09L - Local Home Assistant Verification Lab

Final result: LOCAL_VERIFICATION_LAB_NOT_QUALIFIED

Date: 2026-07-10
Repository: `pcvantol/djconnect`
Branch: `phase-09l-r2-docker-runtime-remediation`
Tested SHA: `7cd3f78823928bd499a509dcaf241923f1175b41`
Remediation phase: Phase 9L-R2

## Decision

Phase 9L-R remediated the proven framework blockers from the first Phase 9L
run by making the local HA lab doctor and lifecycle commands fail closed with
clear diagnostics instead of hanging or collapsing distinct failures into one
generic blocker.

Phase 9L-R2 verified that Docker can now remove the stale dedicated
`djconnect-verification-ha` container, but the local HA verification lab is
still not qualified for live Phase 9V execution because the local Docker
Desktop/containerd runtime cannot start containers. A dedicated HA lab start
created the expected labeled container with the correct source SHA and mounts,
but it remained in `Created` state with no logs or bound ports. A no-mount
`docker run` probe using the already-local Home Assistant image also remained
in `Created` state. After restarting Docker Desktop, `docker version` returned
an HTTP 500 and then hung while reconnecting.

The remaining live blocker is now a narrow external Docker Desktop/runtime
prerequisite. Lab-only Home Assistant auth bootstrap has been added so a fresh
dedicated lab can create verification credentials and request a runtime access
token without committing secrets.

During the modular lab refinement, Phase 9L also stopped treating the local HA
lab as a monolithic container. Scenarios now declare logical requirements,
the Planning Engine aggregates those requirements, and the Execution
Environment resolves them to canonical lab profiles and deterministic Compose
fragments.

No production Home Assistant container or volume was mutated.

## Phase 9L-R2 Docker Runtime Remediation Attempt

Observed on 2026-07-10:

- Docker Desktop server initially responded to `docker version`.
- No dedicated `djconnect-verification-*` containers were present before the
  R2 run.
- `python3 -m tools.verification.cli lab ha metadata` selected `ha-profile`
  and resolved to `docker/verification/compose.base.yaml`.
- `python3 -m tools.verification.cli lab ha start` invoked Docker Compose but
  hung while the dedicated lab container remained in `Created` state.
- `docker inspect djconnect-verification-ha` succeeded and showed:
  - `djconnect.verification=true`;
  - `djconnect.lab.profile=ha-profile`;
  - `djconnect.source_sha=7cd3f78823928bd499a509dcaf241923f1175b41`;
  - source mounted read-only at `/djconnect-source`;
  - dedicated config mounted at `/config`;
  - no production volume mount.
- `docker rm -f djconnect-verification-ha` succeeded.
- A no-mount probe,
  `docker run --rm --name djconnect-verification-docker-probe ghcr.io/home-assistant/home-assistant:stable /bin/true`,
  also remained in `Created` state.
- The no-mount probe was removed with
  `docker rm -f djconnect-verification-docker-probe`.
- Docker Desktop was restarted with `osascript -e 'quit app "Docker"'` and
  `open -a Docker`.
- After restart, `docker version` returned an HTTP 500 for `/v1.55/version` and
  subsequent readiness checks hung before returning server metadata.
- Docker and container logs were inspected after the 500/hung readiness
  failure. Container logs were empty/unavailable because the failed probe
  containers never reached `Running`. Docker Desktop host logs showed repeated
  backend and VM connectivity failures:
  - `com.docker.backend.apiproxy` repeatedly logged
    `connect tcp 192.168.65.7:2376: no route to host`;
  - `com.docker.backend.services` repeatedly logged connection refusal for
    `/run/guest-services/stats.sock`;
  - `ContainerEventTracker` logged that it could not connect to the Docker
    daemon at `unix:///var/run/docker.sock`;
  - `/pause/events` also returned connection refused.

Conclusion: Phase 9L-R2 isolated the remaining blocker to local Docker
Desktop/containerd container-start health, not the DJConnect Compose profile,
Home Assistant configuration, source mount, lab auth, or scenario planning.

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

## Phase 9L-R Remediation Implemented

Implemented within the existing Verification Execution Environment:

- Docker inspect now uses a short timeout for lab discovery.
- Lab discovery now preserves a diagnostic runtime from `docker ps` when
  `docker inspect` is unavailable or times out.
- Lab doctor now classifies `Created`, `Exited`, `Dead` and inspect-unavailable
  states distinctly.
- REST and WebSocket probes now fail closed until the dedicated lab container is
  running and a token is provided.
- WebSocket qualification now has a live Home Assistant websocket probe for
  token-authenticated `get_config`.
- Lab auth bootstrap now creates a verification-only Home Assistant user
  through the HA onboarding API for fresh dedicated labs and requests a fresh
  access token from generated local credentials.
- Lifecycle `start`, `recreate` and `fresh` attempt safe recovery of only the
  dedicated stale lab container before Compose startup.
- Lifecycle diagnostics now include scoped container summary and log-tail
  availability without blocking indefinitely.
- Source SHA matching now requires the runtime source SHA label to match the
  current repository SHA.
- Focused tests cover created-state classification, inspect timeout fallback,
  scoped stale-container recovery, generated lab auth and no-token WebSocket
  blocking.
- Modular lab composition was added so scenarios declare logical runtime
  requirements and the Planning Engine selects the smallest canonical lab
  profile instead of defaulting to a monolithic HA container.
- Canonical capabilities, lab services, lab profiles and Compose fragments now
  live under `verification/lab/` and `docker/verification/`.
- The canonical scenario catalog now has explicit `requires` declarations for
  all 231 scenarios.

No new Verification architecture subsystem was introduced.

## Environment Observed

Docker:

- Docker Engine reachable
- Docker Engine version: `29.6.1`
- Docker Desktop: `4.81.0`

Compose:

- Docker Compose reachable
- Compose version: `v5.3.0`

Dedicated lab container:

- Name: `djconnect-verification-ha`
- Image: `ghcr.io/home-assistant/home-assistant:stable`
- State: `Created`
- Host port: not bound because the container is not running
- Verification labels: visible through `docker ps` fallback metadata
- Runtime source SHA label: stale from earlier run
  `3e6f3eb76850a268b0148f5b0a51f82255fe0ea0`
- Current tested SHA: `6248b5d65016f8f2eefdd07d7725fb69c0fbada5`

Token/auth:

- `DJCONNECT_VERIFICATION_HA_TOKEN` was not configured during the original
  live attempt.
- Phase 9L-R now supports `lab ha bootstrap-auth` for fresh dedicated labs.
- Bootstrap stores generated lab credentials only under the ignored lab root
  and redacts tokens from metadata/evidence.

## Live Qualification Attempt

Commands executed:

```bash
docker ps -a --filter name=djconnect-verification-ha
docker inspect djconnect-verification-ha
docker compose -f verification/lab/home_assistant/compose.yaml ps
python3 -m tools.verification.cli lab ha doctor
python3 -m tools.verification.cli lab ha start
```

Observed:

- `docker ps` completed and showed `djconnect-verification-ha` in `Created`
  state.
- `docker inspect djconnect-verification-ha` did not complete within the
  allowed inspection window.
- Compose `ps` completed but did not report a running service row.
- `lab ha doctor` returned `LOCAL_VERIFICATION_LAB_NOT_QUALIFIED` and
  classified:
  - inspect unavailable;
  - container stuck in `Created`;
  - missing port ownership;
  - source identity not live-proven;
  - runtime not safe for verification;
  - missing HA token before auth bootstrap was implemented;
  - REST/WebSocket blocked before running runtime and token.
- `lab ha start` attempted scoped stale-container recovery.
- Recovery failed because `docker rm -f djconnect-verification-ha` timed out
  after 30 seconds.

## Qualification Gates

| Gate | Result | Notes |
| --- | --- | --- |
| Docker daemon reachable | PASS | Docker responded to version and ps commands. |
| Docker Compose reachable | PASS | Compose responded. |
| Lab definition exists | PASS | Compose file exists in repository. |
| Exactly one intended lab container | PASS | The dedicated container was selected by name. |
| Container not stuck | FAIL | Container is in `Created` state. |
| Docker inspect completed | FAIL | Inspect timed out; fallback metadata was used. |
| Expected port belongs to lab container | BLOCKED | Container is not running and no port is bound. |
| Verification labels present | PASS | Fallback metadata includes verification labels. |
| Source SHA/fingerprint proven | FAIL | Runtime source mount and current SHA are not live-proven. |
| No production volume detected | PASS | No production mount was observed from fallback metadata. |
| Runtime safe for verification | FAIL | Safety requires running, inspectable runtime with matching source identity. |
| HA token available | BLOCKED | Requires running lab; token can come from `DJCONNECT_VERIFICATION_HA_TOKEN` or generated lab credentials. |
| REST reachable | BLOCKED | Requires running lab and token. |
| WebSocket reachable | BLOCKED | Requires running lab and token. |
| Approved storage reachable | PASS | Dedicated config/storage path exists. |
| Logs reachable | BLOCKED | `docker logs` timed out while container is stuck. |
| Immutable evidence | PASS | Evidence run created under `artifacts/verification/evidence/`. |

## Evidence

Run ID:

```text
phase-09l-r-local-ha-lab-20260710T153557Z
```

Evidence files were written under:

```text
artifacts/verification/evidence/phase-09l-r-local-ha-lab-20260710T153557Z/
```

Artifacts are intentionally ignored by git.

Included:

- run metadata;
- lab metadata;
- Docker/Compose/lab command results;
- final summary;
- evidence index with checksums.

Additional requirement coverage reports:

```text
docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.md
docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.json
```

## Tests Run

Focused tests:

```bash
python3 -m unittest tests.verification.test_phase_09l_local_ha_lab
```

Regression subset:

```bash
python3 -m unittest tests.verification.test_home_assistant_adapter tests.verification.test_planning_engine tests.verification.test_execution_environment tests.verification.test_core_implementation tests.verification.test_harness_scaffold tests.verification.test_phase_09r_remediation tests.verification.test_phase_09l_local_ha_lab
```

Results:

- Focused modular lab and Phase 9L/9R/planning tests: 34 passed.
- Full `tests/verification` discovery: 66 passed.
- Scenario validation covered 231 canonical scenarios.

The modular lab refinement validates:

- 231 of 231 canonical scenarios have `requires` declarations;
- 0 unresolved scenario requirement mappings;
- capability catalog contains 46 capabilities;
- service catalog contains 6 modular services;
- lab profile catalog contains 5 canonical profiles;
- `PROFILE-001` through `PROFILE-005` select `ha-profile`;
- Assist requirements select `ha-assist`;
- music requirements select `ha-music`;
- combined Assist and music requirements select `ha-full`.

## Failure Classification

| Failure | Classification | Owner | Blocking | Recommended action |
| --- | --- | --- | --- | --- |
| Dedicated lab container remains in `Created` state | Environment issue | Local Docker / Verification Environment | Yes | Repair Docker Desktop/containerd container-start health, then rerun `lab ha start`. |
| No-mount Docker probe remains in `Created` state | Environment issue | Local Docker | Yes | Stabilize Docker Desktop/containerd before retrying the HA lab. |
| Docker Desktop restart returned HTTP 500 and later hung on `docker version` | Environment issue | Local Docker | Yes | Repair or reset Docker Desktop runtime; do not use production HA containers as a workaround. |
| Docker Desktop logs show `no route to host` to `192.168.65.7:2376` and guest-service connection refusals | Environment issue | Local Docker / Docker Desktop VM | Yes | Treat as Docker Desktop VM/engine connectivity failure before attempting more lab changes. |
| Runtime source identity is stale/unproven | Environment issue | Verification Environment | Yes | After stale-container removal, recreate the dedicated lab so labels match the tested SHA. |
| HA auth could not be qualified live | Environment issue | Verification Environment | Yes | After Docker recovery, run `lab ha bootstrap-auth` or provide `DJCONNECT_VERIFICATION_HA_TOKEN`, then rerun `lab ha doctor`. |
| REST/WebSocket not qualified | Environment issue / HA Adapter live prerequisite | Yes | Rerun `lab ha doctor` after the lab is running and the token is available. |

## Remaining External Prerequisites

Smallest remaining prerequisites:

1. Restore Docker Desktop/containerd behavior so a no-mount local image probe
   can start and exit cleanly.

2. Verify Docker runtime health with a no-mount probe before starting the lab.

3. Rerun:

   ```bash
   python3 -m tools.verification.cli lab ha start
   python3 -m tools.verification.cli lab ha doctor
   ```

4. Bootstrap lab-only HA auth:

   ```bash
   python3 -m tools.verification.cli lab ha bootstrap-auth
   ```

   Alternatively, provide a non-committed existing token through
   `DJCONNECT_VERIFICATION_HA_TOKEN`.

5. Rerun:

   ```bash
   python3 -m tools.verification.cli lab ha doctor
   ```

## Readiness For Phase 9V Rerun

Phase 9V rerun remains blocked.

Required before rerun:

1. Dedicated lab container reaches running state.
2. Docker inspect reports verification labels and current source mount identity.
3. Expected host port `18123` is owned by the lab container.
4. HA auth is available through generated lab credentials or
   `DJCONNECT_VERIFICATION_HA_TOKEN`.
5. REST and WebSocket probes pass.
6. Approved storage and log collection are live-proven.
7. `python3 -m tools.verification.cli lab ha doctor` returns
   `LOCAL_VERIFICATION_LAB_QUALIFIED`.

Do not execute Phase 9V rerun or Phase 10 until this report changes to a
qualified result in a later commit.
