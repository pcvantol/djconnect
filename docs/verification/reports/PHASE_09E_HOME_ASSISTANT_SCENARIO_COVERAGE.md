# Phase 9E-R - Home Assistant Scenario Coverage

Status: HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS

Date: 2026-07-11
Repository: `pcvantol/djconnect`
Branch: `phase-09e-r-home-assistant-scenario-coverage-remediation`
Tested SHA: `a400dab0efc7f9ab71609078ec16930dce9f61a8`

## Decision

Phase 9E-R qualifies broad Home Assistant backend scenario coverage with
non-blocking warnings.

The dedicated local Home Assistant lab returned
`LOCAL_VERIFICATION_LAB_QUALIFIED` on the current branch SHA. The Scenario
Engine now maps HA-only scenarios and separable HA backend assertion paths to
Home Assistant adapter primitives, the CLI wires lab-derived URL/token/storage
and log configuration into adapter execution without serializing secrets, and
primitive failures are preserved in run summaries for Investigator
classification.

Phase 10 may start. The only warning is non-blocking for Apple work: one
regenerated 79-scenario batch saw two transient live websocket timeouts
(`DISCOVER-015`, `TRACKINSIGHT-003`). The Investigator classified both as
`environment_issue` with `affected_scenario` rerun scope, and the affected
rerun passed.

## Scenario Inventory

Inventory source: canonical YAML under `verification/scenarios/`.

| Metric | Count |
| --- | ---: |
| Total canonical scenarios | 231 |
| HA/DJConnect-related scenarios | 223 |
| Executed HA backend or HA backend assertion-path scenarios | 195 |
| Deferred client/hardware/release/voice-localization scenarios | 28 |
| Non-HA scenarios | 8 |
| Unresolved lab profile selections | 0 |

## Coverage Summary

| Result | Count |
| --- | ---: |
| Executed | 195 |
| Passed | 195 |
| Failed after affected rerun | 0 |
| Blocked HA backend scenarios | 0 |
| Deferred to client/hardware/release/voice adapter phases | 28 |
| Skipped | 0 |
| Unresolved | 0 |

## Coverage By Domain

| Domain | Canonical | HA-related | Executed | Status |
| --- | ---: | ---: | ---: | --- |
| Ask DJ | 28 | 28 | 28 | Qualified HA backend path |
| Backend | 8 | 8 | 8 | Qualified |
| Capabilities | 8 | 8 | 8 | Qualified HA backend path |
| Discover | 16 | 16 | 16 | Qualified HA backend path |
| Export | 6 | 6 | 6 | Qualified |
| Hardware | 10 | 10 | 0 | Deferred to hardware/ESP32 adapter |
| Identity | 8 | 8 | 0 | Deferred to Voice Endpoint adapter |
| Import | 6 | 6 | 6 | Qualified |
| Localization | 10 | 10 | 0 | Deferred to client/release adapters |
| Music DNA | 18 | 18 | 18 | Qualified |
| Networking | 8 | 8 | 8 | Qualified |
| Playback | 10 | 10 | 10 | Qualified |
| Privacy | 10 | 10 | 10 | Qualified |
| Profiles | 24 | 24 | 24 | Qualified HA backend path |
| Release | 8 | 0 | 0 | Deferred to release qualification |
| Resolver | 20 | 20 | 20 | Qualified |
| Setup | 25 | 25 | 25 | Qualified |
| Track Insight | 8 | 8 | 8 | Qualified HA backend path |

## Evidence Index

| Evidence | Path |
| --- | --- |
| HA profile/setup/resolver/privacy/export/import batch | `artifacts/verification/evidence/djv-20260711T102421Z-ccf1cb4e6a/` |
| Music DNA/backend/playback/networking batch | `artifacts/verification/evidence/djv-20260711T102725Z-3664892062/` |
| Separable backend batch with 77/79 pass and two websocket timeouts | `artifacts/verification/evidence/djv-20260711T102849Z-cf26e0d150/` |
| Investigator classification for websocket timeouts | `artifacts/verification/evidence/djv-20260711T102849Z-cf26e0d150/investigation.json` |
| Affected-scenario rerun for `DISCOVER-015`, `TRACKINSIGHT-003` | `artifacts/verification/evidence/djv-20260711T103327Z-5dc6021c6a/` |
| Machine-readable report | `docs/verification/reports/PHASE_09E_HOME_ASSISTANT_SCENARIO_COVERAGE.json` |

Regression subset:

```text
python -m pytest tests/verification
74 passed in 24.52s
```

Repository hygiene:

```text
git diff --check
PASS
```

## Failure Ownership

| Finding | Classification | Owner | Blocking | Recommended action |
| --- | --- | --- | --- | --- |
| Phase 9E could execute only `PROFILE-001` through `PROFILE-005`. | Remediated Verification Core defect | Scenario Engine / Verification Core | No | Keep HA backend primitive mappings covered by regression tests. |
| HA adapter execution required manual lab token/config wiring. | Remediated Execution Environment / Adapter integration defect | Execution Environment / Home Assistant Adapter | No | Continue using in-process lab-derived adapter config; never serialize token values. |
| Primitive failures were not available in summary-level investigation bundles. | Remediated Verification Core defect | Evidence / Investigator | No | Run summaries now preserve scenario diagnostics through finalization. |
| Two regenerated live websocket primitives timed out. | Environment issue | Dedicated local HA lab runtime | No | Affected-scenario rerun passed; warning is non-blocking for Apple adapter work. |

## Readiness For Phase 10

Phase 10 is unblocked.

Final Phase 9E-R decision:

```text
HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS
```

The warning is explicitly non-blocking for Apple client work because it was a
transient local HA websocket timeout, was classified by the Investigator, and
passed on affected-scenario rerun.
