# Phase 9V Verification Platform Qualification Rerun

Status: canonical completion report

Date: 2026-07-11

Final decision:

```text
VERIFICATION PLATFORM QUALIFIED
```

## Executive Summary

Phase 9V was rerun after Phase 9L-R6 qualified the dedicated Docker-based
local Home Assistant verification lab.

The complete verification pipeline executed the first approved Profile scenario
set through the canonical planner, execution environment, Home Assistant
Verification Adapter, evidence store and Verification Core.

The qualified evidence run is:

```text
artifacts/verification/evidence/djv-20260711T091949Z-a0c9568562/
```

The rerun proves:

- planning works for the approved first scenario set;
- the dedicated local HA lab can be used as the live runtime;
- exact-SHA CI qualification works;
- the HA adapter can execute the required runtime primitives;
- evidence is persisted under immutable per-run directories;
- the verification regression subset passes;
- failures can be investigated, classified and rerun without broadening scope.

## Scope

Only the approved first scenario set was executed:

- `PROFILE-001`
- `PROFILE-002`
- `PROFILE-003`
- `PROFILE-004`
- `PROFILE-005`

No additional scenario catalog scope was executed.

No Apple, Windows, Pi, ESP32 or Voice Endpoint adapter work was started.

## Repository And Environment

Repository: `pcvantol/djconnect`

Branch: `phase-09v-verification-platform-rerun`

Tested SHA:

```text
eafee269beef3ff30819fe66d386779e5258a6c7
```

Host: `MBP-van-Peter`

OS: `Darwin 25.5.0`

Architecture: `arm64`

Timezone: `CET`

Python: `3.11.7`

Docker:

```text
Docker version 29.6.1, build 8900f1d
Docker Desktop 4.81.0 (232925)
```

Home Assistant lab image:

```text
ghcr.io/home-assistant/home-assistant:2026.7.2
```

DJConnect integration version:

```text
3.2.50
```

## Mandatory Gates

Mandatory gates passed in the qualified run evidence.

| Gate | Result | Evidence |
| --- | --- | --- |
| Repository SHA known | PASS | `qualification.json` snapshot |
| GitHub workflow discovery | PASS | 7 workflows discovered |
| Exact-SHA GitHub CI | PASS | 2 successful runs inspected |
| Docker HA runtime discovery | PASS | Dedicated `djconnect-verification-ha` runtime |
| Dependency inspection | PASS | 1 Python manifest inspected |
| Cleanup planning | PASS | Soft cleanup planned |
| Secrets loading | PASS | No secret values logged |

Exact-SHA CI inspected:

- `Validate Home Assistant custom integration`: success
- `CodeQL`: success

## Execution Plan

Planning command selected:

- policy: `smoke`
- strategy: `smoke`
- mode: `functional`
- data profile: `smoke`
- matrix profile: `Smoke Test Profile`
- generated cases: 5
- estimated runtime: 60 seconds

Plan ID:

```text
plan-smoke-smoke-20260711T091952Z
```

Selected lab profile:

```text
ha-profile
```

Selected service:

```text
homeassistant
```

Compose fragment:

```text
docker/verification/compose.base.yaml
```

Missing capabilities:

```text
[]
```

Unresolved requirements:

```text
[]
```

The plan recorded `apple.runtime` and `windows.runtime` as external resources
because `PROFILE-002` models rich-client profile switching. This did not block
the HA-only qualification run because the selected scenario primitives for this
phase executed through the Home Assistant adapter and the lab plan had no
missing or unresolved requirements. Rich-client runtime verification remains
owned by future adapter phases.

## Scenario Results

Qualified run:

```text
djv-20260711T091949Z-a0c9568562
```

| Scenario | Result | Evidence |
| --- | --- | --- |
| `PROFILE-001` | PASS | `scenarios/PROFILE-001/PROFILE-001-functional-smoke-test-profile-smoke/result.json` |
| `PROFILE-002` | PASS | `scenarios/PROFILE-002/PROFILE-002-functional-smoke-test-profile-smoke/result.json` |
| `PROFILE-003` | PASS | `scenarios/PROFILE-003/PROFILE-003-functional-smoke-test-profile-smoke/result.json` |
| `PROFILE-004` | PASS | `scenarios/PROFILE-004/PROFILE-004-functional-smoke-test-profile-smoke/result.json` |
| `PROFILE-005` | PASS | `scenarios/PROFILE-005/PROFILE-005-functional-smoke-test-profile-smoke/result.json` |

Run summary:

```json
{
  "result_state": "PASS",
  "run_id": "djv-20260711T091949Z-a0c9568562",
  "schema_version": 1,
  "state": "PASS"
}
```

## Evidence Summary

The qualified run persisted:

- `summary.json`
- `qualification.json`
- `execution-plan.json`
- `environment.json`
- `evidence-index.json`
- per-scenario result files for all five Profile scenarios

Evidence is stored under the immutable run directory:

```text
artifacts/verification/evidence/djv-20260711T091949Z-a0c9568562/
```

The evidence includes environment metadata, Docker runtime metadata, exact-SHA
CI metadata, run identity, execution plan and per-scenario results.

## Investigation And Fix Cycle

An initial execution attempt failed:

```text
artifacts/verification/evidence/djv-20260711T091806Z-525c8213ce/
```

The per-scenario failure message was:

```text
Failed primitives: websocket_request.
```

Manual investigation found the root cause was not a DJConnect product defect.
The first wrapper invocation ran without approved Docker access, so the lab
token could not be resolved from the dedicated runtime and the adapter executed
without a Home Assistant access token.

Classification:

- classification: Execution Environment invocation issue
- confidence: high
- owning subsystem: Verification Execution Environment / local operator
  invocation
- blocking status: resolved by affected rerun
- recommended action: keep live Docker/HA execution behind explicit approved
  runtime access and improve automated Investigator classification for missing
  runtime token cases

Affected rerun:

```text
djv-20260711T091949Z-a0c9568562
```

The affected rerun passed all five selected scenarios. The approved regression
subset then passed.

The automated Investigator currently reported the initial failed run as
`unknown` because the failed evidence bundle did not expose a sufficiently
structured failure item for the heuristic. This is a non-blocking framework
improvement captured in the backlog.

## Regression And Dogfooding

The verification framework regression subset passed:

```text
python3 -m unittest discover tests/verification
Ran 69 tests in 22.222s
OK
```

Scenario catalog validation passed:

```text
python3 -m tools.verification.cli validate
validated 231 scenarios
```

Python compile validation passed:

```text
python3 -m py_compile tools/verification/environment/docker_ha.py tools/verification/home_assistant_adapter.py tools/verification/planning/planner.py tools/verification/core/investigator.py
```

## Performance Observations

Observed planning output estimated 60 seconds for the selected smoke set.

The qualified execution persisted immediate per-scenario results; the current
scenario primitive executor records duration as `0.0` for the successful
runtime primitive executions. More granular adapter timing should be added when
the platform begins adapter-specific qualification.

The HA lab runtime was already started by Phase 9L-R6 and was reused safely for
this qualification rerun.

## Known Limitations

- Automated Investigator classification remains coarse when a failed evidence
  bundle only records primitive failure text.
- `PROFILE-002` includes future rich-client runtime resources in its logical
  requirements. The HA-only qualification path is valid, but Apple and Windows
  runtime semantics still require their own adapter phases.
- Successful scenario results currently prove runtime primitive execution
  through the adapter; deeper product assertions remain scenario-engine and
  adapter-growth work for later phases.
- The local workstation has missing toolchains that are irrelevant to this HA
  qualification scope, such as `espidf` and `msbuild`.

## Recommendations

- Start Phase 9E: Home Assistant Scenario Coverage Expansion.
- Keep the first Apple adapter scope scenario-driven and thin.
- Do not introduce new verification architecture layers.
- Improve Investigator failure extraction for missing token, sandbox and
  runtime-access cases during the next Verification Core maintenance window.
- Preserve exact-SHA CI and dedicated lab qualification as mandatory gates for
  live verification runs.

## Readiness For Home Assistant Scenario Coverage Expansion

The Verification Platform is qualified for broad Home Assistant backend
scenario coverage expansion.

Phase 9E may start after this report, scorecard, backlog and prompt index are
merged.

Phase 10 Apple Verification Adapter remains blocked until Phase 9E qualifies
broad Home Assistant backend scenario coverage. The first five Profile
scenarios prove the Verification Platform pipeline, not full HA backend
coverage.

Final decision:

```text
VERIFICATION PLATFORM QUALIFIED
```
