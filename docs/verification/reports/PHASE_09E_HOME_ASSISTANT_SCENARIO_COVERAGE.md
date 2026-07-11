# Phase 9E - Home Assistant Scenario Coverage

Status: HOME_ASSISTANT_BACKEND_NOT_QUALIFIED

Date: 2026-07-11
Repository: `pcvantol/djconnect`
Branch: `phase-09e-home-assistant-scenario-coverage`
Tested SHA: `8ffab1530f23e501794ff2b6855f733ab76a7c2a`

## Decision

Phase 9E did not qualify broad Home Assistant backend scenario coverage.

The dedicated local Home Assistant verification lab qualified on the current
SHA, and the currently supported Home Assistant adapter scenario batch passed:

- `PROFILE-001`: PASS
- `PROFILE-002`: PASS
- `PROFILE-003`: PASS
- `PROFILE-004`: PASS
- `PROFILE-005`: PASS

The blocking gap is coverage breadth. The canonical inventory contains 223
Home Assistant or DJConnect-backend-related scenarios, but the Scenario Engine
currently maps only the first five Profile scenarios to executable Home
Assistant primitives. The remaining HA backend domains are not qualified and
Phase 10 must remain blocked.

## Scenario Inventory

Inventory source: canonical YAML under `verification/scenarios/`.

| Metric | Count |
| --- | ---: |
| Total canonical scenarios | 231 |
| HA/DJConnect-related scenarios | 223 |
| HA-only scenarios | 103 |
| HA-primary cross-platform blocked scenarios | 24 |
| Hardware/client-dependent scenarios | 96 |
| Non-HA scenarios | 8 |
| Scenarios with client runtime requirements | 102 |
| Scenarios with hardware/runtime requirements | 96 |
| Scenarios with external requirements | 39 |
| Unresolved lab profile selections | 0 |

## Coverage Summary

| Result | Count |
| --- | ---: |
| Executed | 5 |
| Passed | 5 |
| Failed | 0 |
| Blocked | 98 |
| Deferred to client/hardware/external adapters | 120 |
| Skipped | 0 |
| Unresolved | 0 |

Blocked scenarios are HA-only scenarios that should be executable by the Home
Assistant backend verification path but do not yet have Scenario Engine
execution mappings. Deferred scenarios declare client, hardware or external
runtime requirements and require later adapter phases or explicit external
lab resources.

## Coverage By Domain

| Domain | Canonical | HA-related | Executed | Status |
| --- | ---: | ---: | ---: | --- |
| Ask DJ | 28 | 28 | 0 | Blocked |
| Backend | 8 | 8 | 0 | Blocked/deferred |
| Capabilities | 8 | 8 | 0 | Blocked |
| Discover | 16 | 16 | 0 | Blocked |
| Export | 6 | 6 | 0 | Blocked |
| Hardware | 10 | 10 | 0 | Deferred |
| Identity | 8 | 8 | 0 | Blocked |
| Import | 6 | 6 | 0 | Blocked |
| Localization | 10 | 10 | 0 | Blocked/deferred |
| Music DNA | 18 | 18 | 0 | Blocked |
| Networking | 8 | 8 | 0 | Blocked/deferred |
| Playback | 10 | 10 | 0 | Blocked |
| Privacy | 10 | 10 | 0 | Blocked |
| Profiles | 24 | 24 | 5 | Partially covered |
| Release | 8 | 0 | 0 | Deferred to release qualification |
| Resolver | 20 | 20 | 0 | Blocked |
| Setup | 25 | 25 | 0 | Blocked/deferred |
| Track Insight | 8 | 8 | 0 | Blocked |

## Coverage By Lab Profile

Smallest selected canonical profile per HA-related scenario:

| Lab profile | Scenarios |
| --- | ---: |
| `ha-minimal` | 33 |
| `ha-profile` | 100 |
| `ha-music` | 88 |
| `ha-assist` | 1 |
| `ha-full` | 1 |

Required services across HA-related scenarios:

| Service | Scenarios |
| --- | ---: |
| `homeassistant` | 223 |
| `fake_music_backend` | 47 |
| `music_assistant` | 8 |
| `whisper` | 1 |
| `piper` | 1 |

Required secrets:

| Secret name | Scenarios |
| --- | ---: |
| `ha.access_token` | 223 |
| `spotify.access_token` | 18 |

## Coverage By Mode

Executed mode coverage:

| Mode | Executed | Passed |
| --- | ---: | ---: |
| Functional | 5 | 5 |
| Boundary | 0 | 0 |
| Security | 0 | 0 |
| Privacy | 0 | 0 |
| Resilience | 0 | 0 |
| Localization | 0 | 0 |

The Phase 9E acceptance target required broader staged mode coverage. That
target remains unmet.

## Evidence Index

| Evidence | Path |
| --- | --- |
| Scenario inventory | `artifacts/verification/phase-09e-scenario-inventory.json` |
| Qualified lab doctor | `artifacts/verification/phase-09e-lab-doctor.json` |
| Initial adapter run without explicit token/storage env | `artifacts/verification/evidence/djv-20260711T094425Z-dea478d0b1/` |
| Explicit URL/storage run still missing token | `artifacts/verification/evidence/djv-20260711T094516Z-660862c9a4/` |
| Passing supported batch | `artifacts/verification/evidence/djv-20260711T094553Z-61af356688/` |

Regression subset:

```text
/private/tmp/djconnect-phase9e-venv/bin/python -m pytest tests/verification
69 passed in 18.98s
```

## Failure Ownership

| Finding | Classification | Owner | Blocking | Recommended action |
| --- | --- | --- | --- | --- |
| Broad HA backend scenario coverage cannot execute beyond `PROFILE-001` through `PROFILE-005`. | Verification Core defect | Scenario Engine / Verification Core | Yes | Add canonical Home Assistant execution mappings and assertions for the HA-only Phase 9E scenario set. |
| HA adapter execution does not automatically reuse the lab doctor token source. | Execution Environment / Adapter integration defect | Execution Environment / Home Assistant Adapter | No for the rerun, Yes for unattended coverage | Wire lab-derived token, URL, storage and log configuration into adapter execution without exposing secrets. |
| Automated Investigator still reports evidence bundles without structured failure items as `unknown`. | Verification Core defect | Verification Investigator | No | Add structured failure extraction for primitive failures. |

No DJConnect Home Assistant product implementation defect was proven by this
phase. The failure is a verification coverage and execution-mapping gap.

## Fixes Applied

No product code or verification code fixes were applied in Phase 9E.

The only runtime remediation was recreating the dedicated verification lab so
its labels matched the current SHA, then rerunning the supported batch with a
lab-derived token held only in process memory.

## Reruns

| Run | Result | Notes |
| --- | --- | --- |
| `djv-20260711T094425Z-dea478d0b1` | FAIL | Adapter run lacked explicit token/storage configuration. |
| `djv-20260711T094516Z-660862c9a4` | FAIL | URL/storage/log paths were explicit, but token was still absent. |
| `djv-20260711T094553Z-61af356688` | PASS | `PROFILE-001` through `PROFILE-005` passed with lab-derived token. |

## Remaining HA Backend Gaps

The next remediation must expand executable HA coverage in staged batches:

1. HA core smoke, setup, capability and transport scenarios.
2. Profile and resolver scenarios beyond `PROFILE-005`.
3. Services, storage, persistence, privacy and diagnostics.
4. Ask DJ, Music DNA, playback, Track Insight and fake music backend coverage.
5. Assist/voice backend coverage using `ha-assist`.
6. Security, malformed input, injection and robustness coverage.

The remediation must keep adapters thin and place scenario interpretation in
the Scenario Engine / Verification Core.

## Readiness For Phase 10

Phase 10 is blocked.

Final Phase 9E decision:

```text
HOME_ASSISTANT_BACKEND_NOT_QUALIFIED
```

Next prompt:

```text
prompts/verification/PHASE_09E_R_HOME_ASSISTANT_SCENARIO_COVERAGE_REMEDIATION.md
```
