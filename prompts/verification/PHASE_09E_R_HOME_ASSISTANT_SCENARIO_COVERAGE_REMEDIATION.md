# Verification Program V1
## Phase 9E-R - Home Assistant Scenario Coverage Remediation

Repository:

`pcvantol/djconnect`

## Context

Phase 9E returned:

```text
HOME_ASSISTANT_BACKEND_NOT_QUALIFIED
```

The dedicated local Home Assistant lab qualified on SHA
`8ffab1530f23e501794ff2b6855f733ab76a7c2a`, and the currently supported
adapter batch passed:

- `PROFILE-001`
- `PROFILE-002`
- `PROFILE-003`
- `PROFILE-004`
- `PROFILE-005`

Phase 9E did not qualify broad Home Assistant backend coverage because the
Scenario Engine currently maps only those five Profile scenarios to executable
Home Assistant primitives. The inventory contains 223 HA/DJConnect-related
scenarios, including 103 HA-only scenarios.

Phase 10 remains blocked.

## Mission

Remediate only the proven Phase 9E blockers:

1. Expand executable Scenario Engine / Verification Core mappings for the
   HA-only Home Assistant backend scenario set.
2. Wire dedicated lab-derived Home Assistant URL, token, storage and log
   configuration into HA adapter execution without exposing secrets.
3. Improve structured primitive-failure evidence so the Investigator no longer
   classifies primitive failures as only `unknown`.
4. Rerun staged Phase 9E batches and produce an updated backend qualification
   decision.

Do not implement client adapters.
Do not start Phase 10.
Do not rewrite scenario expectations to make runs pass.

## Required Inputs

Read:

- `BOOTSTRAP_CODEX_VERIFICATION.md`
- `PROMPT_INDEX.md`
- `prompts/verification/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE_EXPANSION.md`
- `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.md`
- `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.json`
- `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
- `docs/verification/09_HOME_ASSISTANT_VERIFICATION_ADAPTER.md`
- canonical scenarios under `verification/scenarios/`
- `tools/verification/scenario/engine.py`
- `tools/verification/home_assistant_adapter.py`
- `tools/verification/environment/docker_ha.py`
- `tools/verification/core/investigator.py`

## Scope

Start with HA-only scenarios selected from the Phase 9E inventory. Keep the
first remediation batch narrow:

- HA core smoke;
- setup/capability/transport scenarios satisfied by `ha-minimal`;
- Profile and Resolver scenarios satisfied by `ha-profile`;
- privacy, diagnostics, storage and persistence scenarios satisfied by
  `ha-profile`.

After that passes, continue only to the next HA backend batch:

- Ask DJ and Music DNA scenarios that can run with deterministic fixtures;
- playback, Track Insight and fake backend scenarios using `ha-music`;
- Assist backend scenarios using `ha-assist`.

Scenarios with Apple, Windows, Pi, ESP32, Voice Endpoint, release artifact,
Spotify live API or other external runtime requirements must remain deferred
unless the scenario has a clearly separable HA-only assertion path.

## Acceptance

Phase 9E-R succeeds only if it produces one of:

```text
HOME_ASSISTANT_BACKEND_QUALIFIED
HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS
HOME_ASSISTANT_BACKEND_NOT_QUALIFIED
HOME_ASSISTANT_BACKEND_BLOCKED
```

Phase 10 may start only for `HOME_ASSISTANT_BACKEND_QUALIFIED` or
`HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS` with every warning explicitly
non-blocking for Apple client work.

## Outputs

Update:

- `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.md`
- `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.json`
- `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `PROMPT_INDEX.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md`

If still not qualified, generate the next narrowly scoped remediation prompt.
If qualified, generate the Phase 10 prompt and do not execute it.
