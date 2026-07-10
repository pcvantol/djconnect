# Verification Platform Backlog

Status: active after Phase 9V

Do not create GitHub issues automatically from this backlog.

| ID | Priority | Classification | Finding | Owner | Repository | Blocking | Effort | Recommended phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VPB-001 | P0 | Environment issue | Local Home Assistant development runtime missing from qualification environment. | Verification Environment | `djconnect` | Blocks Phase 9V | M | Phase 9V rerun |
| VPB-002 | P0 | Environment issue | `gh` token invalid; mandatory GitHub CI status cannot be verified through CLI. | Operator / Verification Environment | `djconnect` | Blocks Phase 9V | S | Phase 9V rerun |
| VPB-003 | P0 | Verification Core defect | No executable Verification Investigator exists to emit classification artifacts. | Verification Core | `djconnect` | Blocks Phase 9V acceptance | M | Phase 9V fix |
| VPB-004 | P0 | Verification Gap | Qualification evidence is not persisted as durable artifacts under `artifacts/`. | Verification Core / Evidence | `djconnect` | Blocks Phase 9V acceptance | M | Phase 9V fix |
| VPB-005 | P0 | HA Adapter gap | Live websocket transport is not implemented or injected for HA runtime qualification. | HA Adapter | `djconnect` | Blocks live HA qualification | M | Phase 9V fix |
| VPB-006 | P0 | Environment issue | Approved HA storage directory is not configured; storage snapshots cannot run. | Verification Environment | `djconnect` | Blocks PROFILE-001..005 live evidence | S | Phase 9V rerun |
| VPB-007 | P1 | Verification Data Framework gap | Run evidence does not include deterministic seed and generator versions. | Data Framework / Planning Engine | `djconnect` | Blocks reproducibility acceptance | S | Phase 9V fix |
| VPB-008 | P1 | Planning Engine gap | CLI planning defaults to schema examples unless scenario path is externally overridden. | Planning Engine / CLI | `djconnect` | Risk for operator error | S | Phase 9V fix |
| VPB-009 | P1 | Verification Gap | GitHub connector returned no statuses for the tested SHA; accepted CI source of truth is undefined. | Execution Environment | `djconnect` | Blocks CI qualification | S | Phase 9V fix |
| VPB-010 | P1 | Dogfooding Gap | Investigator has no unit, integration or regression tests. | Verification Core | `djconnect` | Blocks dogfooding acceptance | M | Phase 9V fix |
| VPB-011 | P2 | Documentation issue | Qualification commands need a canonical local HA setup profile. | Verification Docs | `djconnect` | Non-blocking after tooling fixes | S | Phase 9V follow-up |

## Regression Subset Required After Fixes

After any Phase 9V fix, rerun only the affected scenario(s), then run:

```bash
python3 -m unittest discover tests/verification
```

Do not start Phase 10 until Phase 9V reports:

VERIFICATION PLATFORM QUALIFIED
