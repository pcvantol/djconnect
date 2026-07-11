# Verification Platform Backlog

Status: active after Phase 9V rerun

Do not create GitHub issues automatically from this backlog.

| ID | Priority | Classification | Finding | Owner | Repository | Blocking | Effort | Recommended phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VPB-001 | P0 | Environment issue | Phase 9L-R6 qualified the dedicated local HA verification lab. Phase 9V rerun must continue to reject unmarked production-like HA runtimes and use only the dedicated verification lab. | Verification Environment / Operator | `djconnect` | No | Done | Phase 9L-R6; enforce in Phase 9V rerun |
| VPB-002 | P0 | Environment issue | `gh` authentication is available for the qualified Phase 9V rerun and exact-SHA CI passed. Keep the explicit auth gate for future live runs. | Operator / Verification Environment | `djconnect` | No | Done | Phase 9V rerun |
| VPB-003 | P0 | Verification Core defect | Executable Verification Investigator implemented inside Verification Core. Keep dogfooding tests in regression subset. | Verification Core | `djconnect` | No | Done | Phase 9R |
| VPB-004 | P0 | Verification Gap | Durable run artifact store implemented under the configured evidence directory. | Verification Core / Evidence | `djconnect` | No | Done | Phase 9R |
| VPB-005 | P0 | HA Adapter gap | Live websocket transport is implemented and was proven against the dedicated local HA lab in Phase 9L-R6. Keep it in the Phase 9V regression subset. | HA Adapter / Verification Environment | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-006 | P0 | Environment issue | Approved HA storage path is provided by the dedicated verification lab root and was live-proven in Phase 9L-R6. | Verification Environment / Operator | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-007 | P1 | Verification Data Framework gap | Run evidence should make deterministic seed and generator versions easier to inspect for generated datasets. Smoke data was sufficient for Phase 9V rerun, but richer data-driven phases need stronger evidence. | Data Framework / Planning Engine | `djconnect` | No | S | Phase 10 or Verification Core maintenance |
| VPB-008 | P1 | Planning Engine gap | Canonical planning selected the real scenario catalog in Phase 9V rerun. Keep CLI fail-closed behavior covered so examples/defaults are never treated as canonical execution scope. | Planning Engine / CLI | `djconnect` | No | S | Phase 10 regression |
| VPB-009 | P1 | Verification Gap | Exact-SHA CI qualification implemented; CI still requires valid local auth or approved token. | Execution Environment / Operator | `djconnect` | Blocks CI qualification | S | Phase 9R |
| VPB-010 | P1 | Dogfooding Gap | Investigator unit tests added to the verification regression subset. | Verification Core | `djconnect` | No | Done | Phase 9R |
| VPB-011 | P2 | Documentation issue | Qualification commands now use the canonical local HA lab profile. Continue improving concise operator docs as live adapter phases add more platforms. | Verification Docs | `djconnect` | No | S | Phase 10 follow-up |
| VPB-012 | P0 | Environment issue | Stale dedicated lab container cleanup was previously blocked by Docker Desktop/containerd. Phase 9L-R6 started a fresh dedicated lab successfully after Docker Desktop stabilization and Documents permission approval. | Verification Environment / Local Docker | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-013 | P0 | Environment issue | Generated lab-only HA auth is qualified. `lab ha bootstrap-auth` now uses the supported Home Assistant login-flow plus authorization-code exchange and produced a token for REST/WebSocket probes. | Verification Environment / Operator | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-014 | P0 | Verification Gap | Local HA lab doctor returned `LOCAL_VERIFICATION_LAB_QUALIFIED` in Phase 9L-R6. | Verification Environment | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-015 | P0 | Environment issue | Modular lab requirements, profiles and Compose fragments are implemented and validated; the canonical `ha-profile` was live-qualified in Phase 9L-R6. | Verification Environment / Local Docker | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-016 | P0 | Environment issue | Docker Desktop/containerd container-start instability was remediated enough for Phase 9L-R6 no-mount probes, bind-mount probe, lab startup and scenario execution to pass. | Local Docker / Operator | Local workstation | No | Done | Phase 9L-R6 |
| VPB-017 | P0 | Environment issue | The repeated `Created`-without-start behavior no longer blocks the canonical `ha-profile` lab after Phase 9L-R6. | Local Docker / Operator | Local workstation | No | Done | Phase 9L-R6 |
| VPB-018 | P0 | Environment issue | The R4 no-mount probe blocker was remediated before R6; repeated no-mount probes passed in Phase 9L-R6. | Local Docker / Operator | Local workstation | No | Done | Phase 9L-R6 |
| VPB-019 | P0 | Environment issue | Docker Desktop access to macOS `Documents` was approved by the operator. The bind-mount probe and local HA lab qualification passed in Phase 9L-R6; no Docker purge, factory reset or reinstall was required. | Local Docker / Operator | Local workstation | No | Done | Phase 9L-R6 |
| VPB-020 | P1 | Verification Gap | Automated Investigator classification reported the initial Phase 9V wrapper failure as `unknown` even though manual investigation identified missing runtime token caused by an unapproved Docker-access invocation. | Verification Core / Investigator | `djconnect` | No | S | Phase 10 regression or Verification Core maintenance |
| VPB-021 | P2 | Planning Engine gap | `PROFILE-002` correctly declares rich-client requirements, but HA-only smoke planning exposes `apple.runtime` and `windows.runtime` as external resources. Future adapter planning should make cross-runtime coverage intent more explicit. | Planning Engine / Scenario Catalog | `djconnect` | No | M | Phase 10 Apple Adapter |

## Regression Subset Required After Fixes

After any Phase 9V fix, rerun only the affected scenario(s), then run:

```bash
python3 -m unittest discover tests/verification
```

Phase 9V rerun reports:

VERIFICATION PLATFORM QUALIFIED

Phase 10 may start after the Phase 9V rerun report, scorecard, backlog and
prompt index are merged.
