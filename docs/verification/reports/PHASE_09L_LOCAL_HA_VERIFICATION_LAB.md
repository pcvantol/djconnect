# Phase 09L - Local Home Assistant Verification Lab

Final result: LOCAL_VERIFICATION_LAB_QUALIFIED

Date: 2026-07-11
Repository: `pcvantol/djconnect`
Branch: `phase-09l-r4-docker-desktop-clean-runtime-repair`
Tested SHA: `b8dd999da0d069309086ebdd0fa613904902f29f`
Remediation phase: Phase 9L-R6

## Decision

Phase 9L-R6 qualified the dedicated local Home Assistant verification lab after
the operator approved Docker Desktop access to the macOS `Documents` folder.
That permission was the root cause of the R5 bind-mount failure: no-mount
containers could start, while containers mounting repository paths under
`/Users/pcvantol/Documents/...` remained in `Created`.

R6 also identified and fixed three Verification Framework defects discovered
during live qualification:

- lab auth bootstrap used the removed Home Assistant password grant and now
  uses Home Assistant's supported login-flow plus authorization-code exchange;
- the Home Assistant verification adapter had no native live WebSocket
  transport and now provides a thin stdlib WebSocket client;
- the `ha-profile` lab bootstrap now creates a lab-only DJConnect config entry
  so the promised `djconnect.loaded` capability is true after lab startup.

The final lab doctor returned `LOCAL_VERIFICATION_LAB_QUALIFIED`. The first
approved Profile scenario set executed through the Scenario Engine, Execution
Environment, Home Assistant adapter and live Home Assistant runtime:

- `PROFILE-001`: PASS;
- `PROFILE-002`: PASS;
- `PROFILE-003`: PASS;
- `PROFILE-004`: PASS;
- `PROFILE-005`: PASS.

Evidence run:
`artifacts/verification/evidence/djv-20260711T080007Z-69941deb88/`.

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

## Phase 9L-R3 Docker Desktop Repair Attempt

Observed on 2026-07-10:

- Repository hygiene was clean before the run.
- Docker Desktop initially returned only Docker client metadata and hung before
  returning server metadata.
- Docker Desktop was stopped with `osascript -e 'quit app "Docker"'`.
- Lingering Docker Desktop UI/helper processes remained after the quit request
  and were stopped explicitly.
- Docker Desktop was started again with `open -a Docker`.
- After restart, `docker version --format '{{json .}}'` returned both client
  and server metadata:
  - Docker Desktop `4.81.0`;
  - Docker Engine `29.6.1`;
  - containerd `v2.2.5`;
  - runc `1.3.6`;
  - LinuxKit kernel `6.12.76-linuxkit`.
- No `djconnect-verification-*` containers existed before the new probes.
- A no-mount probe using the already-local Home Assistant image and explicit
  `/bin/true` entrypoint started and exited successfully once:

  ```bash
  docker run --rm --name djconnect-verification-docker-probe \
    --entrypoint /bin/true ghcr.io/home-assistant/home-assistant:stable
  ```

- The canonical lab metadata selected `ha-profile`, `docker/verification/compose.base.yaml`,
  host port `18123` and tested SHA `2dbe7842bafc37fe962989a9bd89b41f1517d16b`.
- The existing local Home Assistant development container was still bound to
  host port `8123`; the verification lab remained separate on host port
  `18123`.
- `python3 -m tools.verification.cli lab ha start` created
  `djconnect-verification-ha` with the expected verification labels, source
  SHA, source fingerprint, dedicated config mount and read-only source mount.
- The dedicated lab container remained in `Created` state:
  - no `start` event appeared;
  - no logs were available;
  - host port `18123` was not bound;
  - Docker inspect showed empty `SandboxID`, `EndpointID`, `Gateway` and
    container IP fields.
- `docker rm -f djconnect-verification-ha` succeeded after the failed start.
- Follow-up isolation probes using the same Home Assistant image then also
  remained in `Created`, including:
  - no-mount `/bin/true`;
  - bind-mount `/config` and `/djconnect-source` `/bin/true`.
- The stuck Docker client processes ignored repeated interrupt signals and had
  to be stopped explicitly; the dedicated probe containers were then removed.
- Docker Desktop backend logs for the failed probe show
  `ContainerCreateCliLinux`, `ContainerStartCliLinux`, volume approval and
  port exposer calls, but Docker events show only `create`/`attach` for the
  failing probe and no matching `start`/`die`.

Conclusion: Phase 9L-R3 improved Docker Desktop from "daemon cannot return
server metadata" to "one no-mount container can start", but the runtime still
does not provide reliable container-start semantics. The canonical local HA lab
therefore remains not qualified.

The old local Home Assistant development Compose file was inspected for
networking differences. It uses host port `8123`, `extra_hosts:
host.docker.internal:host-gateway`, `AIODNS_DISABLED=1`, explicit DNS servers,
`enable_ipv6: false`, and Home Assistant trusted proxy settings for
`127.0.0.1`, `::1`, `172.16.0.0/12` and `192.168.65.0/24`. Those settings may
be useful if the verification lab later reaches HTTP/WebSocket startup and
shows network/proxy errors. They do not explain the current R3 blocker because
the no-mount `/bin/true` probe has no Home Assistant networking dependency and
still returned to the `Created` failure mode after the first successful start.

## Phase 9L-R4 Docker Desktop Clean Runtime Attempt

Observed on 2026-07-10:

- The R3/R4 prompt state had been closed without merge, so the local R4 commit
  was restored from the local git object database onto branch
  `phase-09l-r4-docker-desktop-clean-runtime-repair`.
- Docker server metadata was available before the stable gate:
  - Docker Desktop `4.81.0`;
  - Docker Engine `29.6.1`;
  - containerd `v2.2.5`;
  - runc `1.3.6`;
  - LinuxKit kernel `6.12.76-linuxkit`.
- No `djconnect-verification-*` containers existed before the stable gate.
- The R4 stable Docker gate attempted the required no-mount probe:

  ```bash
  docker run --rm --name djconnect-verification-docker-probe \
    --entrypoint /bin/true ghcr.io/home-assistant/home-assistant:stable
  ```

- Probe 1 timed out after 30 seconds.
- The probe container remained in `Created` state.
- `docker inspect` showed:
  - no bind mounts;
  - `AutoRemove=true`;
  - `NetworkMode=bridge`;
  - `State.Status=created`;
  - `StartedAt=0001-01-01T00:00:00Z`;
  - empty `SandboxID`, `EndpointID`, `Gateway`, `IPAddress` and port fields.
- `docker logs` was empty because the container never reached `Running`.
- Docker events showed `container create` and `container attach`, but no
  matching `container start` or `container die`.
- Docker Desktop backend logs showed `ContainerCreateCliLinux`,
  `ContainerStartCliLinux`, volume approval and port exposer calls for the
  stuck probe.
- The dedicated probe container was removed with
  `docker rm -f djconnect-verification-docker-probe`.

Conclusion: Phase 9L-R4 failed before the HA lab was started. Docker Desktop
can answer daemon metadata requests, but it still cannot reliably start even a
no-mount `/bin/true` container from the already-local Home Assistant image. The
next action requires an operator-approved Docker Desktop runtime reset or
reinstall outside repository state.

## Phase 9L-R5 Docker Desktop Operator Reset Attempt

Observed on 2026-07-10:

- The branch remained `phase-09l-r4-docker-desktop-clean-runtime-repair`.
- Docker runtime state was inspected before mutation:
  - existing local Home Assistant development containers were present;
  - `homeassistant` was running on host port `8123`;
  - `music-assistant-server`, `wyoming-piper` and `wyoming-whisper` were
    stopped;
  - production-like Docker volumes and networks existed outside the dedicated
    verification namespace.
- Because existing Docker state included the old Home Assistant development
  environment, R5 used the least destructive allowed operator action:

  ```bash
  docker desktop restart
  ```

- Docker server metadata returned after restart:
  - Docker Desktop `4.81.0`;
  - Docker Engine `29.6.1`;
  - containerd `v2.2.5`;
  - runc `1.3.6`;
  - LinuxKit kernel `6.12.76-linuxkit`.
- The R5 stable Docker gate passed:
  - three sequential no-mount Home Assistant image probes started;
  - every probe emitted Docker `start` and `die` events;
  - every probe exited with code `0`;
  - no `djconnect-verification-docker-probe` container remained.
- The five approved Profile scenarios were planned individually. Each selected
  the canonical `ha-profile` lab profile.
- The canonical HA lab was started with:

  ```bash
  python3 -m tools.verification.cli lab ha start
  ```

- The dedicated lab container was created with:
  - `djconnect.verification=true`;
  - `djconnect.lab.profile=ha-profile`;
  - source SHA `4405c511dd66946aca249ea2acffe63dd83b3726`;
  - read-only source mount `/djconnect-source`;
  - dedicated config mount `/config`;
  - host port `18123`.
- The lab container remained in `Created` state:
  - no Docker `start` event;
  - no container logs;
  - no host port binding;
  - empty network sandbox and endpoint fields.
- The hang was isolated with additional probes:
  - HA image with the same lab bind mounts and `/bin/true` also remained in
    `Created`;
  - Docker events showed `create` and `attach`, but no `start`/`die`;
  - after that mount failure, an HA image probe on a temporary dedicated
    verification network without mounts also remained in `Created`.
- Dedicated verification containers and temporary verification networks were
  removed after evidence collection.

Conclusion: R5 restored simple no-mount container starts, but the canonical HA
lab remains not qualified. The immediate blocker is now Docker Desktop
file-sharing/bind-mount startup for the repository paths used by the lab. A
destructive Docker Desktop Clean/Purge data, factory reset or reinstall may be
required, but it must be performed explicitly by the operator because existing
non-verification Docker state is present.

Post-run operator finding on 2026-07-11: the blocking bind-mount behavior
matched a macOS permission popup requiring Docker Desktop access to the
`Documents` folder. This explains why no-mount probes passed while containers
that mounted repository paths under `/Users/pcvantol/Documents/...` remained in
`Created`. Phase 9L-R6 should first remediate and prove Docker Desktop
Documents access before considering destructive Docker Desktop purge, factory
reset or reinstall actions.

## Phase 9L-R6 Documents Permission And Lab Qualification

Observed on 2026-07-11:

- Docker Desktop access to the macOS `Documents` folder was approved by the
  operator.
- Docker Desktop server metadata returned successfully:
  - Docker Desktop `4.81.0`;
  - Docker Engine `29.6.1`;
  - containerd `v2.2.5`;
  - runc `1.3.6`;
  - LinuxKit kernel `6.12.76-linuxkit`.
- No dedicated `djconnect-verification-*` containers or networks were present
  before the R6 gate.
- Three sequential no-mount Home Assistant image probes exited with code `0`.
- A bind-mount probe using the lab source and config paths exited with code
  `0`.
- `PROFILE-001` through `PROFILE-005` each selected the canonical `ha-profile`
  lab profile.
- `python3 -m tools.verification.cli lab ha start` started
  `djconnect-verification-ha` successfully.
- `python3 -m tools.verification.cli lab ha bootstrap-auth` created/used
  lab-only Home Assistant credentials and returned a redacted access token.
- `python3 -m tools.verification.cli lab ha doctor` returned
  `LOCAL_VERIFICATION_LAB_QUALIFIED`.
- The live scenario execution run
  `djv-20260711T080007Z-69941deb88` returned `PASS` for:
  - `PROFILE-001`;
  - `PROFILE-002`;
  - `PROFILE-003`;
  - `PROFILE-004`;
  - `PROFILE-005`.

Framework fixes applied during R6:

- Home Assistant lab auth bootstrap now uses the supported login-flow plus
  authorization-code exchange instead of the removed password grant.
- The Home Assistant verification adapter now has a thin stdlib WebSocket
  transport for live runtime primitives.
- The `ha-profile` lab layout now creates an idempotent lab-only DJConnect
  config entry so `djconnect.loaded` is true when HA starts.
- After evidence collection, `python3 -m tools.verification.cli lab ha stop`
  stopped the dedicated lab container cleanly with Home Assistant exit code
  `0`.

Conclusion: Phase 9L-R6 qualifies the local Home Assistant verification lab.
Phase 9V rerun is now the correct next phase. Phase 10 remains blocked until
Phase 9V rerun qualifies the full verification platform.

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

## Final Environment Observed

Docker:

- Docker Engine reachable.
- Docker Engine version: `29.6.1`.
- Docker Desktop: `4.81.0`.
- containerd: `v2.2.5`.
- runc: `1.3.6`.
- Kernel: `6.12.76-linuxkit`.

Compose:

- Docker Compose reachable.
- Compose version: `v5.3.0`.

Dedicated lab container:

- Name: `djconnect-verification-ha`.
- Image: `ghcr.io/home-assistant/home-assistant:stable`.
- Host port: `18123`.
- Verification labels: present.
- Source mount: repository source mounted read-only at `/djconnect-source`.
- Config mount: dedicated verification config mounted at `/config`.
- Production resources: not mounted.

Token/auth:

- `DJCONNECT_VERIFICATION_HA_TOKEN` was not required from the operator.
- `lab ha bootstrap-auth` generated lab-only Home Assistant credentials under
  the ignored lab root.
- The generated token was passed only through process environment for live
  adapter execution and was not printed or committed.

## Final Qualification Gates

| Gate | Result | Notes |
| --- | --- | --- |
| Docker daemon reachable | PASS | Docker responded with server metadata. |
| Docker Compose reachable | PASS | Compose responded. |
| No-mount Docker probes | PASS | Three sequential HA image `/bin/true` probes exited `0`. |
| Repository bind-mount probe | PASS | Source/config bind mounts under `Documents` worked after operator approval. |
| Lab definition exists | PASS | Canonical profile and Compose definition exist in repository. |
| Expected lab profile selected | PASS | `PROFILE-001` through `PROFILE-005` selected `ha-profile`. |
| Dedicated container running | PASS | `lab ha start` started `djconnect-verification-ha`. |
| No production volume detected | PASS | Lab uses dedicated verification paths only. |
| HA auth available | PASS | Lab-only auth bootstrap succeeded. |
| REST reachable | PASS | Doctor REST probe passed. |
| WebSocket reachable | PASS | Doctor WebSocket probe and adapter capabilities call passed. |
| DJConnect loaded | PASS | Lab-only config entry loaded the `djconnect` integration. |
| Approved storage reachable | PASS | Dedicated `.storage` path is available. |
| Logs reachable | PASS | Lab log path is available for evidence collection. |
| Immutable evidence | PASS | Scenario evidence was written under a per-run artifact path. |

## Evidence

Final scenario run ID:

```text
djv-20260711T080007Z-69941deb88
```

Evidence files were written under:

```text
artifacts/verification/evidence/djv-20260711T080007Z-69941deb88/
```

Artifacts are intentionally ignored by git.

Included evidence:

- run metadata;
- environment metadata;
- scenario execution records;
- Home Assistant adapter operation logs;
- HTTP/WebSocket operation timing and result metadata;
- storage/log artifact references;
- final summary.

Additional requirement coverage reports:

```text
docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.md
docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.json
```

## Tests Run

Focused tests:

```bash
python3 -m unittest tests.verification.test_phase_09l_local_ha_lab
python3 -m unittest tests.verification.test_home_assistant_adapter tests.verification.test_phase_09l_local_ha_lab
```

Regression and validation:

```bash
python3 -m unittest discover tests/verification
python3 -m tools.verification.cli validate
```

Results:

- Home Assistant adapter and Phase 9L focused tests passed.
- Full `tests/verification` discovery passed.
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

| Finding | Classification | Owner | Blocking | Outcome |
| --- | --- | --- | --- | --- |
| Dedicated lab container remained in `Created` state during earlier attempts | Environment issue | Local Docker / Operator | No | Remediated by Docker Desktop stabilization and Documents permission approval. |
| Docker Desktop Documents permission blocked repository bind mounts | Environment issue | Local Docker / Operator | No | Remediated in R6; bind-mount probe passed. |
| Home Assistant password grant is unsupported in HA 2026 | Verification Execution Environment defect | Verification Environment | No | Remediated in R6 by using login-flow plus authorization-code token exchange. |
| HA adapter live WebSocket transport was unavailable | Home Assistant Adapter defect | Home Assistant Adapter | No | Remediated in R6 with a thin stdlib WebSocket transport. |
| `ha-profile` promised `djconnect.loaded` but did not configure DJConnect | Verification Execution Environment defect | Verification Environment | No | Remediated in R6 with an idempotent lab-only DJConnect config entry. |

## Remaining External Prerequisites

No remaining external prerequisite blocks the local HA lab.

The lab remains scoped to the local verification environment. It does not
replace Phase 9V's full platform qualification gates for repository hygiene,
exact-SHA CI, dogfooding coverage, investigation and reporting.

## Readiness For Phase 9V Rerun

Phase 9V rerun may start after this Phase 9L-R6 result is reviewed and merged.

Qualified evidence:

1. Dedicated lab container reaches `running` state.
2. Docker inspect reports verification labels and source mount identity.
3. Expected host port `18123` is owned by the lab container.
4. HA auth is available through generated lab credentials.
5. REST and WebSocket probes pass.
6. Approved storage and log collection are live-proven.
7. `python3 -m tools.verification.cli lab ha doctor` returns
   `LOCAL_VERIFICATION_LAB_QUALIFIED`.
8. `PROFILE-001` through `PROFILE-005` execute through the HA adapter and pass.

Do not execute Phase 9V rerun or Phase 10 in this phase.
