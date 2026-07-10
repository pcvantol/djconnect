# Verification Program V1
## Phase 9L-R4 - Docker Desktop Clean Runtime Repair And Local HA Lab Qualification

Repository:

`pcvantol/djconnect`

Context:

Phase 9L-R3 improved Docker Desktop from a daemon/server-metadata hang to one
successful no-mount Home Assistant image start, but the runtime did not remain
stable. The canonical `ha-profile` lab container and follow-up no-mount probes
again remained in `Created` state without `start` events or container logs.

The repository-side lab architecture is already implemented and validated.

Do not introduce a new verification subsystem.
Do not change scenario expectations.
Do not execute Phase 9V.
Do not start Phase 10.

---

# Goal

Restore a stable local Docker Desktop runtime, then qualify the existing
canonical Local Home Assistant Verification Lab.

The final result must be exactly one of:

```text
LOCAL_VERIFICATION_LAB_QUALIFIED
```

or

```text
LOCAL_VERIFICATION_LAB_NOT_QUALIFIED
```

---

# Read First

Read completely:

- `AGENTS.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md`
- `PROMPT_INDEX.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`
- `prompts/verification/PHASE_09L_R3_DOCKER_DESKTOP_REPAIR.md`
- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `docker/verification/`
- `verification/lab/`
- `tools/verification/environment/docker_ha.py`

Inspect actual paths and runtime state before mutating anything.

---

# Scope

Only address:

- local Docker Desktop/containerd container-start stability;
- then live qualification of the existing `ha-profile` lab.

Do not broaden scenario scope.

---

# Runtime Repair

Use the least destructive repair that proves stable container-start behavior.

Allowed without additional architecture changes:

1. Stop Docker Desktop.
2. Stop lingering Docker Desktop helper/client processes.
3. Start Docker Desktop.
4. Disable Docker Desktop Resource Saver if it is causing VM pause/resume
   instability.
5. Restart Docker Desktop from the UI or CLI.
6. Run Docker Desktop diagnostics.
7. Reset only Docker Desktop runtime state when explicitly approved by the
   operator.
8. Reinstall Docker Desktop only when explicitly approved by the operator.

Do not delete repository files.
Do not touch production Home Assistant data.
Do not remove production containers or volumes.

If a Docker Desktop factory reset or reinstall is required, stop and record it
as an operator action unless explicit approval is already present.

---

# Stable Docker Gate

Before starting the lab, prove Docker can start containers repeatedly.

Run the already-local Home Assistant image probe at least three times
sequentially:

```bash
docker run --rm --name djconnect-verification-docker-probe \
  --entrypoint /bin/true ghcr.io/home-assistant/home-assistant:stable
```

Each run must:

- emit a Docker `start` event;
- exit with code `0`;
- leave no `djconnect-verification-docker-probe` container behind.

If any probe remains in `Created`, stop, collect Docker/container logs, update
the report and return `LOCAL_VERIFICATION_LAB_NOT_QUALIFIED`.

---

# Lab Qualification

After the stable Docker gate passes:

1. Verify no dedicated verification containers are running.
2. Remove only dedicated `djconnect-verification-*` containers in `Created`,
   `Exited` or `Dead`.
3. Confirm `PROFILE-001` through `PROFILE-005` select `ha-profile`.
4. Start the canonical HA lab:

   ```bash
   python3 -m tools.verification.cli lab ha start
   ```

5. Persist the resolved Compose command and effective configuration as
   evidence.
6. Bootstrap lab-only HA auth:

   ```bash
   python3 -m tools.verification.cli lab ha bootstrap-auth
   ```

7. Run:

   ```bash
   python3 -m tools.verification.cli lab ha doctor
   ```

8. Qualify REST, WebSocket, approved storage and logs.
9. Execute only:
   - `PROFILE-001`
   - `PROFILE-002`
   - `PROFILE-003`
   - `PROFILE-004`
   - `PROFILE-005`
10. Collect evidence.

---

# Networking Follow-Up

The old local Home Assistant development Compose/configuration may be used as
reference only after containers reliably start.

If the lab reaches HA startup but fails on HTTP, WebSocket, proxy or DNS
behavior, compare the verification lab with the old dev setup and consider the
safe verification-only equivalents of:

- `host.docker.internal:host-gateway`;
- `AIODNS_DISABLED=1`;
- explicit DNS servers;
- bridge network with IPv6 disabled;
- Home Assistant `trusted_proxies` for local Docker Desktop networks.

Do not copy production URLs, ngrok URLs, production secrets or production
volumes into the verification lab.

---

# Validation

Run:

```bash
python3 -m unittest tests.verification.test_lab_requirements tests.verification.test_phase_09l_local_ha_lab tests.verification.test_phase_09r_remediation tests.verification.test_planning_engine
python3 -m unittest discover tests/verification
python3 -m tools.verification.cli validate
git diff --check
```

Live Docker checks must be reported as live evidence, not as unit-test pass.

---

# Deliverables

Update:

- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `PROMPT_INDEX.md`

Create exactly one next prompt if the lab is still not qualified, or create the
Phase 9V rerun prompt if the lab is qualified.

---

# Acceptance Criteria

This remediation is complete when:

- repeated no-mount probes start and exit cleanly, or Docker Desktop is
  documented as still blocking;
- the canonical `ha-profile` lab starts, or the start failure is documented;
- lab-only HA auth, REST, WebSocket, storage and log qualification pass, or the
  remaining blocker is documented;
- the Phase 9L report contains the final result;
- the next action is represented by exactly one prompt;
- Phase 9V is not executed automatically.

Stop after completion.
