# Phase 09R - Verification Platform Qualification Remediation

Status: REMEDIATED WITH EXTERNAL PREREQUISITES

Date: 2026-07-10
Timezone: Europe/Amsterdam
Repository: `pcvantol/djconnect`
Branch: `docs/phase-09r-remediation-prompt-v2`

## Decision

Phase 9R converted the Phase 9V blockers into executable framework checks,
durable evidence paths and explicit external prerequisites. It did not add a
new verification architecture layer and did not broaden the approved scenario
set.

Phase 9V can be rerun after the external prerequisites below are satisfied.

## Remediated Blockers

| Phase 9V blocker | Phase 9R result | Status |
| --- | --- | --- |
| Local HA runtime not detected | Added deterministic Docker Home Assistant discovery and safety qualification in the Execution Environment. | Remediated |
| Invalid `gh` auth | Added non-blocking auth status and interactive repair support through existing CLI conventions. | Remediated, operator action required |
| No exact-SHA CI status | Added exact-SHA GitHub Actions qualification with explicit pass/fail/running/no-data/auth decisions. | Remediated, auth required |
| No executable Investigator | Added executable Investigator inside Verification Core with durable JSON output. | Remediated |
| Evidence not durable enough | Added immutable run-store layout under the configured evidence directory. | Remediated |
| Live WebSocket/storage not qualified | Added HA Docker safety gate and retained live WebSocket/storage as blocked until a safe HA dev runtime is proven. | External prerequisite |

## Docker HA Observation

Docker Desktop was started and the existing Home Assistant container was
started.

Observed container:

- Name: `homeassistant`
- Image: `ghcr.io/home-assistant/home-assistant:stable`
- HA version label: `2026.6.3`
- Status: running
- Port: `0.0.0.0:8123->8123/tcp`
- Config mount: `<local-ha-config-root>` -> `/config`

The new Docker safety gate intentionally failed:

`Docker Home Assistant runtime is not proven safe`

Reason:

- the container is not marked as a DJConnect verification/development runtime;
- the mounted config does not prove that DJConnect is loaded from this repository;
- no source mount matching the current repository SHA was found;
- mutation safety cannot be proven.

This is classified as `BLOCKED_ENVIRONMENT`, not a product defect.

## GitHub CI Observation

GitHub CI qualification now requires exact-SHA Actions data. Non-interactive
runs fail clearly when no valid credential is available. Interactive repair is
available through:

```bash
python3 -m tools.verification.cli --root <repo-root> doctor --fix-auth --interactive-auth
```

If the operator shell cannot complete `gh auth login`, the prerequisite remains
blocked outside the Verification Framework.

## New Commands

```bash
python3 -m tools.verification.cli --root <repo-root> doctor --environment ha-docker
python3 -m tools.verification.cli --root <repo-root> doctor --fix-auth
python3 -m tools.verification.cli --root <repo-root> runs list
python3 -m tools.verification.cli --root <repo-root> runs verify <run-id>
python3 -m tools.verification.cli --root <repo-root> investigate <run-id>
```

## Tests

Focused remediation tests:

```bash
python3 -m unittest tests.verification.test_phase_09r_remediation
```

Regression subset:

```bash
python3 -m unittest \
  tests.verification.test_home_assistant_adapter \
  tests.verification.test_planning_engine \
  tests.verification.test_execution_environment \
  tests.verification.test_core_implementation \
  tests.verification.test_harness_scaffold \
  tests.verification.test_phase_09r_remediation
```

Both commands passed during remediation.

## Remaining External Prerequisites

Phase 9V remains blocked until:

- a dedicated HA verification/dev container is labelled or configured as safe;
- that container mounts or loads the DJConnect source from this repository;
- the mounted source can be matched to the tested Git SHA;
- an approved HA token is provided without committing or logging it;
- approved HA storage and log paths are configured;
- `gh auth status` succeeds or an approved `GH_TOKEN` is available;
- exact-SHA CI data is visible for the tested commit.

## Fresh Phase 9V Rerun

After prerequisites are satisfied, rerun Phase 9V with a new run ID and preserve
all artifacts under the evidence directory. The approved scenario scope remains:

- `PROFILE-001`
- `PROFILE-002`
- `PROFILE-003`
- `PROFILE-004`
- `PROFILE-005`

Do not start Phase 10 until Phase 9V returns:

`VERIFICATION PLATFORM QUALIFIED`
