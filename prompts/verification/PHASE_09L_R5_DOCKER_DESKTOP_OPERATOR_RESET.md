# Verification Program V1
## Phase 9L-R5 - Docker Desktop Operator Reset And Local HA Lab Qualification

Repository:

`pcvantol/djconnect`

Context:

Phase 9L-R4 failed before Home Assistant lab startup. Docker Desktop returned
server metadata, but the required stable Docker gate failed on probe 1: a
no-mount Home Assistant image `/bin/true` container remained in `Created` with
Docker events showing `create` and `attach`, but no `start` or `die`.

The repository-side lab architecture is already implemented and validated.

Do not introduce a new verification subsystem.
Do not change scenario expectations.
Do not execute Phase 9V.
Do not start Phase 10.

---

# Goal

Perform an operator-approved Docker Desktop runtime reset or reinstall outside
repository state, then qualify the existing canonical Local Home Assistant
Verification Lab.

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
- `prompts/verification/PHASE_09L_R4_DOCKER_DESKTOP_CLEAN_RUNTIME_REPAIR.md`
- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `docker/verification/`
- `verification/lab/`
- `tools/verification/environment/docker_ha.py`

Inspect actual runtime state before mutating anything.

---

# Scope

Only address:

- Docker Desktop runtime reset/reinstall performed or approved by the operator;
- stable repeated container-start behavior;
- live qualification of the existing `ha-profile` lab.

---

# Operator Reset Boundary

The previous non-destructive repairs were insufficient.

Before running more lab commands, perform one of these operator-approved
actions:

1. Docker Desktop Troubleshoot -> Restart Docker Desktop.
2. Docker Desktop Troubleshoot -> Clean / Purge data.
3. Docker Desktop Troubleshoot -> Reset to factory defaults.
4. Reinstall Docker Desktop.

Use the least destructive action that restores stable container starts.

Record which action was performed.

Do not delete repository files.
Do not touch production Home Assistant data from the repository.
Do not remove production containers or volumes through automation unless the
operator explicitly confirms that the selected Docker reset action may do so.

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

- the operator reset action is recorded;
- repeated no-mount probes start and exit cleanly, or Docker Desktop is
  documented as still blocking;
- the canonical `ha-profile` lab starts, or the start failure is documented;
- lab-only HA auth, REST, WebSocket, storage and log qualification pass, or the
  remaining blocker is documented;
- the Phase 9L report contains the final result;
- the next action is represented by exactly one prompt;
- Phase 9V is not executed automatically.

Stop after completion.
