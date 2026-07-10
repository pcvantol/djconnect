# Verification Program V1
## Phase 9L-R2 - Docker Runtime Remediation And Local HA Lab Qualification

Repository:

`pcvantol/djconnect`

Context:

Phase 9L and Phase 9L-R implemented the Local Home Assistant Verification Lab,
lab-only HA auth bootstrap, fail-closed diagnostics and modular lab composition.

The modular refinement is complete:

- canonical scenarios declare logical runtime requirements;
- the capability catalog exists;
- service definitions exist;
- canonical lab profiles exist;
- Docker Compose fragments are modular;
- the Planning Engine selects the smallest satisfying profile;
- the Execution Environment resolves profiles to Compose fragments;
- all 231 canonical scenarios validate;
- `PROFILE-001` through `PROFILE-005` select `ha-profile`.

The lab is still not live-qualified because the local Docker Desktop/runtime
could not remove or start the dedicated lab container.

This remediation is narrowly scoped.

Do not introduce a new architecture layer.
Do not add new lab profiles unless the existing validated catalog is factually
wrong.
Do not execute Phase 9V.
Do not start Phase 10.

---

# Goal

Recover the local Docker runtime and complete live qualification of the
existing canonical Local Home Assistant Verification Lab.

The desired final result is exactly one of:

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
- `prompts/verification/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `prompts/verification/PHASE_09L_R_LOCAL_HA_LAB_REMEDIATION.md`
- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/PHASE_09L_LAB_REQUIREMENT_COVERAGE.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `verification/lab/capabilities.yaml`
- `verification/lab/services/`
- `verification/lab/profiles/`
- `docker/verification/`
- `tools/verification/environment/docker_ha.py`
- `tools/verification/lab/`
- `tests/verification/test_lab_requirements.py`
- current Docker and Compose files

Inspect actual paths and commands before changing anything.

---

# Scope

Only address the proven remaining blocker:

- Docker Desktop/containerd cannot reliably remove/start the dedicated
  `djconnect-verification-ha` lab container.

Then live-qualify the existing lab.

---

# Required Actions

1. Verify repository hygiene.
2. Inspect Docker Desktop/runtime health.
3. Inspect the dedicated lab container state.
4. Inspect Docker logs and container logs where available.
5. Safely remove only dedicated verification lab containers and volumes.
6. Start the selected canonical lab profile for the first five Profile
   scenarios.
7. Confirm the selected profile is `ha-profile`.
8. Persist the resolved Compose command and effective configuration as
   evidence.
9. Bootstrap lab-only HA auth using the existing automation.
10. Run the HA lab doctor.
11. Qualify REST, WebSocket, approved storage and logs.
12. Execute only the approved Phase 9L scenario subset:
    - `PROFILE-001`
    - `PROFILE-002`
    - `PROFILE-003`
    - `PROFILE-004`
    - `PROFILE-005`
13. Collect evidence.
14. Update the Phase 9L report.
15. Update backlog and prompt index.
16. Produce the next prompt according to the Phase Completion Protocol.
17. Stop.

---

# Safety

- Do not touch production Home Assistant containers, volumes or config.
- Do not use production HA tokens.
- Do not commit secrets.
- Do not log tokens.
- Only remove containers, networks and volumes carrying the dedicated
  verification labels or names.
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

Run live Docker tests only through the existing explicit Phase 9L lab commands.
Skipped live tests remain `SKIPPED`, never `PASS`.

---

# Deliverables

Update or create:

- `docs/verification/reports/PHASE_09L_LOCAL_HA_VERIFICATION_LAB.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `PROMPT_INDEX.md`
- evidence under `artifacts/verification/evidence/` (ignored by git)
- next prompt under `prompts/verification/`

Do not create new architecture documents unless a factual implementation change
requires documentation correction.

---

# Acceptance Criteria

This remediation is complete when:

- stale dedicated Docker lab resources are removed safely;
- the selected canonical profile for `PROFILE-001` through `PROFILE-005` is
  `ha-profile`;
- the resolved Compose fragments are deterministic;
- the dedicated HA lab starts;
- lab-only HA auth is bootstrapped without committed secrets;
- REST and WebSocket probes pass;
- approved storage and log collection pass;
- capability-level readiness reports all required `ha-profile` capabilities as
  qualified;
- the Phase 9L final result is updated to either
  `LOCAL_VERIFICATION_LAB_QUALIFIED` or
  `LOCAL_VERIFICATION_LAB_NOT_QUALIFIED`;
- the next action is represented by exactly one next prompt or remediation
  prompt;
- the next phase is not executed automatically.

Stop after completion.
