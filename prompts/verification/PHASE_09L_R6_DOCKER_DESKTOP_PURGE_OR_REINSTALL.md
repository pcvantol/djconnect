# Verification Program V1
## Phase 9L-R6 - Docker Desktop Purge Or Reinstall And Local HA Lab Qualification

Repository:

`pcvantol/djconnect`

Context:

Phase 9L-R5 performed the least destructive allowed Docker Desktop operator
action: `docker desktop restart`.

After the restart:

- three sequential no-mount Home Assistant image probes passed;
- all five approved Profile scenarios selected `ha-profile`;
- the canonical HA lab still remained in `Created`;
- a direct HA image probe with the lab bind mounts also remained in `Created`;
- after the bind-mount failure, a temporary dedicated-network probe also
  returned to the `Created` failure mode.

The remaining blocker is Docker Desktop file-sharing/bind-mount startup for the
repository paths used by the lab.

Do not introduce a new verification subsystem.
Do not change scenario expectations.
Do not execute Phase 9V.
Do not start Phase 10.

---

# Goal

Perform an explicit operator-approved Docker Desktop Clean/Purge data, factory
reset or reinstall outside repository state, then qualify the existing
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
- `prompts/verification/PHASE_09L_R5_DOCKER_DESKTOP_OPERATOR_RESET.md`
- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `docker/verification/`
- `verification/lab/`
- `tools/verification/environment/docker_ha.py`

Inspect actual runtime state before mutating anything.

---

# Operator Confirmation

This phase may remove existing Docker containers, images, networks and volumes,
including the old local Home Assistant development environment.

Do not perform purge, factory reset or reinstall unless the operator explicitly
confirms that this Docker Desktop data loss is acceptable.

Repository files must not be deleted.

---

# Required Reset Action

Perform one operator-approved action:

1. Docker Desktop Troubleshoot -> Clean / Purge data.
2. Docker Desktop Troubleshoot -> Reset to factory defaults.
3. Reinstall Docker Desktop.

Record exactly which action was performed.

After reset, start Docker Desktop and wait for Docker server metadata.

---

# Stable Docker Gate

Before starting the lab, prove Docker can start containers repeatedly.

Run the Home Assistant image probe at least three times sequentially:

```bash
docker run --rm --name djconnect-verification-docker-probe \
  --entrypoint /bin/true ghcr.io/home-assistant/home-assistant:stable
```

Each run must:

- emit a Docker `start` event;
- exit with code `0`;
- leave no `djconnect-verification-docker-probe` container behind.

Then run a bind-mount probe using the same repository paths as the lab:

```bash
docker run --rm --name djconnect-verification-probe-mounts \
  --entrypoint /bin/true \
  -v "$PWD/custom_components/djconnect:/djconnect-source:ro" \
  -v "$PWD/artifacts/verification/lab/home_assistant/config:/config" \
  ghcr.io/home-assistant/home-assistant:stable
```

The bind-mount probe must also start, exit with code `0`, and leave no
container behind.

If any probe remains in `Created`, stop, collect Docker/container logs, update
the report and return `LOCAL_VERIFICATION_LAB_NOT_QUALIFIED`.

---

# Lab Qualification

After the stable Docker and bind-mount gates pass:

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

- the destructive operator reset action is recorded;
- no-mount and bind-mount probes start and exit cleanly, or Docker Desktop is
  documented as still blocking;
- the canonical `ha-profile` lab starts, or the start failure is documented;
- lab-only HA auth, REST, WebSocket, storage and log qualification pass, or the
  remaining blocker is documented;
- the Phase 9L report contains the final result;
- the next action is represented by exactly one prompt;
- Phase 9V is not executed automatically.

Stop after completion.
