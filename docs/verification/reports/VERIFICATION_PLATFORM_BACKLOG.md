# Verification Platform Backlog

Status: active after Phase 9V

Do not create GitHub issues automatically from this backlog.

| ID | Priority | Classification | Finding | Owner | Repository | Blocking | Effort | Recommended phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VPB-001 | P0 | Environment issue | Local HA runtime is now discovered through Docker, but the observed `homeassistant` container is not proven safe because it lacks a verification/dev marker and source mount to this repo. | Verification Environment / Operator | `djconnect` | Blocks Phase 9V | S | Phase 9V rerun |
| VPB-002 | P0 | Environment issue | `gh` authentication remains an operator prerequisite; the framework now fails clearly and supports interactive repair. | Operator / Verification Environment | `djconnect` | Blocks Phase 9V | S | Phase 9V rerun |
| VPB-003 | P0 | Verification Core defect | Executable Verification Investigator implemented inside Verification Core. Keep dogfooding tests in regression subset. | Verification Core | `djconnect` | No | Done | Phase 9R |
| VPB-004 | P0 | Verification Gap | Durable run artifact store implemented under the configured evidence directory. | Verification Core / Evidence | `djconnect` | No | Done | Phase 9R |
| VPB-005 | P0 | HA Adapter gap | Live websocket transport remains unqualified until the safe HA Docker runtime and token are available. | HA Adapter / Verification Environment | `djconnect` | Blocks live HA qualification | M | Phase 9V rerun |
| VPB-006 | P0 | Environment issue | Approved HA storage path remains an external runtime configuration prerequisite. | Verification Environment / Operator | `djconnect` | Blocks PROFILE-001..005 live evidence | S | Phase 9V rerun |
| VPB-007 | P1 | Verification Data Framework gap | Run evidence does not include deterministic seed and generator versions. | Data Framework / Planning Engine | `djconnect` | Blocks reproducibility acceptance | S | Phase 9V rerun |
| VPB-008 | P1 | Planning Engine gap | CLI planning defaults to schema examples unless scenario path is externally overridden. | Planning Engine / CLI | `djconnect` | Risk for operator error | S | Phase 9V rerun |
| VPB-009 | P1 | Verification Gap | Exact-SHA CI qualification implemented; CI still requires valid local auth or approved token. | Execution Environment / Operator | `djconnect` | Blocks CI qualification | S | Phase 9R |
| VPB-010 | P1 | Dogfooding Gap | Investigator unit tests added to the verification regression subset. | Verification Core | `djconnect` | No | Done | Phase 9R |
| VPB-011 | P2 | Documentation issue | Qualification commands need a canonical local HA setup profile. | Verification Docs | `djconnect` | Non-blocking after tooling fixes | S | Phase 9V follow-up |

## Regression Subset Required After Fixes

After any Phase 9V fix, rerun only the affected scenario(s), then run:

```bash
python3 -m unittest discover tests/verification
```

Do not start Phase 10 until Phase 9V reports:

VERIFICATION PLATFORM QUALIFIED
