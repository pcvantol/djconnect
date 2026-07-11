# Verification Platform Backlog

Status: active after Phase 10

Do not create GitHub issues automatically from this backlog.

| ID | Priority | Classification | Finding | Owner | Repository | Blocking | Effort | Recommended phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VPB-001 | P0 | Environment issue | Phase 9L-R6 qualified the dedicated local HA verification lab. Phase 9V rerun must continue to reject unmarked production-like HA runtimes and use only the dedicated verification lab. | Verification Environment / Operator | `djconnect` | No | Done | Phase 9L-R6; enforce in Phase 9V rerun |
| VPB-002 | P0 | Environment issue | `gh` authentication is available for the qualified Phase 9V rerun and exact-SHA CI passed. Keep the explicit auth gate for future live runs. | Operator / Verification Environment | `djconnect` | No | Done | Phase 9V rerun |
| VPB-003 | P0 | Verification Core defect | Executable Verification Investigator implemented inside Verification Core. Keep dogfooding tests in regression subset. | Verification Core | `djconnect` | No | Done | Phase 9R |
| VPB-004 | P0 | Verification Gap | Durable run artifact store implemented under the configured evidence directory. | Verification Core / Evidence | `djconnect` | No | Done | Phase 9R |
| VPB-005 | P0 | HA Adapter gap | Live websocket transport is implemented and was proven against the dedicated local HA lab in Phase 9L-R6. Keep it in the Phase 9V regression subset. | HA Adapter / Verification Environment | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-006 | P0 | Environment issue | Approved HA storage path is provided by the dedicated verification lab root and was live-proven in Phase 9L-R6. | Verification Environment / Operator | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-007 | P1 | Verification Data Framework gap | Run evidence should make deterministic seed and generator versions easier to inspect for generated datasets. Smoke data was sufficient for Phase 9V rerun, but richer data-driven phases need stronger evidence. | Data Framework / Planning Engine | `djconnect` | No | S | Phase 9E |
| VPB-008 | P1 | Planning Engine gap | Canonical planning selected the real scenario catalog in Phase 9V rerun. Keep CLI fail-closed behavior covered so examples/defaults are never treated as canonical execution scope. | Planning Engine / CLI | `djconnect` | No | S | Phase 9E regression |
| VPB-009 | P1 | Verification Gap | Exact-SHA CI qualification implemented; CI still requires valid local auth or approved token. | Execution Environment / Operator | `djconnect` | Blocks CI qualification | S | Phase 9R |
| VPB-010 | P1 | Dogfooding Gap | Investigator unit tests added to the verification regression subset. | Verification Core | `djconnect` | No | Done | Phase 9R |
| VPB-011 | P2 | Documentation issue | Qualification commands now use the canonical local HA lab profile. Continue improving concise operator docs as live coverage phases add more scenario batches. | Verification Docs | `djconnect` | No | S | Phase 9E follow-up |
| VPB-012 | P0 | Environment issue | Stale dedicated lab container cleanup was previously blocked by Docker Desktop/containerd. Phase 9L-R6 started a fresh dedicated lab successfully after Docker Desktop stabilization and Documents permission approval. | Verification Environment / Local Docker | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-013 | P0 | Environment issue | Generated lab-only HA auth is qualified. `lab ha bootstrap-auth` now uses the supported Home Assistant login-flow plus authorization-code exchange and produced a token for REST/WebSocket probes. | Verification Environment / Operator | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-014 | P0 | Verification Gap | Local HA lab doctor returned `LOCAL_VERIFICATION_LAB_QUALIFIED` in Phase 9L-R6. | Verification Environment | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-015 | P0 | Environment issue | Modular lab requirements, profiles and Compose fragments are implemented and validated; the canonical `ha-profile` was live-qualified in Phase 9L-R6. | Verification Environment / Local Docker | `djconnect` | No | Done | Phase 9L-R6 |
| VPB-016 | P0 | Environment issue | Docker Desktop/containerd container-start instability was remediated enough for Phase 9L-R6 no-mount probes, bind-mount probe, lab startup and scenario execution to pass. | Local Docker / Operator | Local workstation | No | Done | Phase 9L-R6 |
| VPB-017 | P0 | Environment issue | The repeated `Created`-without-start behavior no longer blocks the canonical `ha-profile` lab after Phase 9L-R6. | Local Docker / Operator | Local workstation | No | Done | Phase 9L-R6 |
| VPB-018 | P0 | Environment issue | The R4 no-mount probe blocker was remediated before R6; repeated no-mount probes passed in Phase 9L-R6. | Local Docker / Operator | Local workstation | No | Done | Phase 9L-R6 |
| VPB-019 | P0 | Environment issue | Docker Desktop access to macOS `Documents` was approved by the operator. The bind-mount probe and local HA lab qualification passed in Phase 9L-R6; no Docker purge, factory reset or reinstall was required. | Local Docker / Operator | Local workstation | No | Done | Phase 9L-R6 |
| VPB-020 | P1 | Verification Gap | Automated Investigator classification reported the initial Phase 9V wrapper failure as `unknown` even though manual investigation identified missing runtime token caused by an unapproved Docker-access invocation. | Verification Core / Investigator | `djconnect` | No | S | Phase 9E regression or Verification Core maintenance |
| VPB-021 | P2 | Planning Engine gap | `PROFILE-002` correctly declares rich-client requirements, but HA-only smoke planning exposes `apple.runtime` and `windows.runtime` as external resources. Future coverage planning should make cross-runtime coverage intent more explicit. | Planning Engine / Scenario Catalog | `djconnect` | No | M | Phase 9E and Phase 10 Apple Adapter |
| VPB-022 | P0 | Verification Core defect | Phase 9E found 223 HA/DJConnect-related scenarios, but the Scenario Engine mapped only `PROFILE-001` through `PROFILE-005`. Phase 9E-R expanded executable Home Assistant backend mappings and qualified 195 HA backend or separable HA backend assertion-path scenarios. | Scenario Engine / Verification Core | `djconnect` | No | Done | Phase 9E-R |
| VPB-023 | P0 | Execution Environment / Adapter integration defect | HA adapter execution did not automatically reuse the dedicated lab-derived HA URL, token, storage and log configuration. Phase 9E-R now wires lab-derived config into adapter execution in-process without serializing token values. | Execution Environment / Home Assistant Adapter | `djconnect` | No | Done | Phase 9E-R |
| VPB-024 | P1 | Verification Core defect | Primitive failures from Phase 9E produced insufficient structured failure details for the Investigator. Phase 9E-R preserves primitive diagnostics in run summaries and the Investigator classified live websocket timeouts from summary evidence. | Verification Investigator | `djconnect` | No | Done | Phase 9E-R |
| VPB-025 | P2 | Environment issue | The regenerated separable backend batch saw two transient live websocket timeouts. The Investigator classified both as environment issues and the affected-scenario rerun passed. Keep this as a non-blocking local lab stability watch item. | Verification Environment / Local Docker | Local workstation | No | S | Phase 10 regression watch |
| VPB-026 | P1 | Apple Adapter gap | Live Apple simulator execution needs explicit `DJCONNECT_VERIFICATION_APPLE_TARGET_JSON`, evidence directory configuration and a built `.app` artifact from `djconnect-app`. Phase 10 mock/unit coverage passed, but live runtime proof was skipped. | Apple Adapter / Execution Environment / Operator | `djconnect`, `djconnect-app` | Blocks live Apple scenario pass | M | Phase 10E |
| VPB-027 | P1 | Planning Engine gap | Phase 10 added Apple adapter execution for Apple-only scenarios, while most catalog scenarios with `apple.runtime` are cross-runtime HA/Apple/Windows scenarios. Phase 10E must select the first Apple-executable set without inventing expected behavior in the adapter. | Planning Engine / Scenario Catalog | `djconnect` | No | M | Phase 10E |
| VPB-028 | P1 | Apple Adapter gap | UI input primitives currently fail closed because no XCTest/accessibility driver is configured. Choose the first supported driver only when a scenario requires UI input. | Apple Adapter / Apple Client | `djconnect`, `djconnect-app` | Blocks UI-driven Apple scenarios | M | Phase 10E or Apple UI remediation |
| VPB-029 | P2 | Apple Adapter gap | watchOS paired simulator orchestration and physical Apple Watch execution are not implemented in Phase 10. Physical devices must remain explicit opt-in. | Apple Adapter / Execution Environment / Operator | `djconnect`, `djconnect-app` | Blocks watchOS live coverage | L | Future Apple coverage phase |

## Regression Subset Required After Fixes

After any Phase 9E-R fix, rerun only the affected scenario batch, then run:

```bash
python3 -m pytest tests/verification
```

Phase 9V rerun reports:

VERIFICATION PLATFORM QUALIFIED

Phase 9E-R reports:

HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS

Phase 10 is unblocked. The Phase 9E-R warning is explicitly non-blocking for
Apple client adapter work.

Phase 10 reports:

APPLE_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED

Phase 10E is unblocked for Apple scenario coverage expansion. Live Apple
simulator/device execution must remain skipped or blocked unless explicit
target and artifact configuration is present.
