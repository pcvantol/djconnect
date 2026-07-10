# Verification Program V1
## Phase 9L-R3 - Docker Desktop Repair And Local HA Lab Qualification

Repository:

`pcvantol/djconnect`

Context:

Phase 9L-R2 isolated the remaining Local Home Assistant Verification Lab
blocker to local Docker Desktop/containerd container-start health.

The repository-side lab architecture is already implemented:

- canonical scenario requirements;
- capability catalog;
- service catalog;
- canonical lab profiles;
- modular Compose fragments;
- Planning Engine lab profile selection;
- Execution Environment profile resolution;
- lab-only Home Assistant auth bootstrap.

The Phase 9L-R2 run proved:

- the selected lab profile for `PROFILE-001` through `PROFILE-005` is
  `ha-profile`;
- the dedicated HA lab container is labeled correctly;
- the source SHA and source mount are correct;
- no production Home Assistant volume was used;
- `docker rm -f djconnect-verification-ha` succeeds;
- a no-mount `docker run` probe using a local image remains in `Created`;
- Docker Desktop restart returned HTTP 500 and later hung readiness checks.

Do not introduce a new verification subsystem.
Do not change scenario expectations.
Do not execute Phase 9V.
Do not start Phase 10.

---

# Goal

Repair or reset the local Docker Desktop/containerd runtime sufficiently that
containers can start, then qualify the existing canonical Local Home Assistant
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
- `prompts/verification/PHASE_09L_R2_DOCKER_RUNTIME_REMEDIATION.md`
- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `verification/lab/capabilities.yaml`
- `verification/lab/profiles/`
- `docker/verification/`
- `tools/verification/environment/docker_ha.py`

Inspect actual paths and runtime state before mutating anything.

---

# Scope

Only address:

- local Docker Desktop/containerd container-start health;
- then live qualification of the existing `ha-profile` lab.

---

# Required Actions

1. Verify repository hygiene.
2. Inspect Docker Desktop health.
3. Verify no dedicated verification containers are running.
4. Safely remove only dedicated verification containers that remain in
   `Created`, `Exited` or `Dead`.
5. Run a no-mount local image probe and require it to start and exit cleanly.
6. If Docker still cannot start containers, repair Docker Desktop outside
   repository state and stop with a NOT QUALIFIED report.
7. Start the canonical HA lab profile selected for `PROFILE-001` through
   `PROFILE-005`.
8. Confirm the selected profile is `ha-profile`.
9. Persist the resolved Compose command and effective configuration as
   evidence.
10. Bootstrap lab-only HA auth with the existing automation.
11. Run `lab ha doctor`.
12. Qualify REST, WebSocket, approved storage and logs.
13. Execute only:
    - `PROFILE-001`
    - `PROFILE-002`
    - `PROFILE-003`
    - `PROFILE-004`
    - `PROFILE-005`
14. Collect evidence.
15. Update the Phase 9L report.
16. Update backlog and prompt index.
17. Produce exactly one next prompt or remediation prompt.
18. Stop.

---

# Safety

- Do not touch production Home Assistant containers, volumes or config.
- Do not use production HA tokens.
- Do not commit secrets.
- Do not log tokens.
- Only remove containers, networks and volumes carrying dedicated verification
  names or labels.
- Preserve evidence before cleanup after failures.

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

# Acceptance Criteria

This remediation is complete when:

- a no-mount local image probe can start and exit cleanly, or the Docker
  Desktop failure is documented as still blocking;
- the canonical `ha-profile` lab starts, or the start failure is documented as
  still blocking;
- lab-only HA auth, REST, WebSocket, storage and log qualification pass, or the
  remaining blocker is documented;
- the Phase 9L report contains the final result;
- the next action is represented by exactly one prompt;
- Phase 9V is not executed automatically.

Stop after completion.
