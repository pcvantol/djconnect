# Verification Platform Backlog

Status: active after Phase 10E-R2 latest-runtime gate

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
| VPB-009 | P1 | Verification Gap | Exact-SHA CI qualification is implemented and regular repository CI now runs the Verification Platform unit suite. Local `gh` auth remains useful for workstation-side CI inspection, but it no longer blocks framework CI qualification. | Execution Environment / Operator | `djconnect` | No | Done | Phase 10E-R2 framework hardening |
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
| VPB-030 | P0 | Environment issue | Phase 10E added and executed `python3 -m tools.verification.cli apple qualify-runtime`; the gate correctly returned `APPLE_RUNTIME_QUALIFICATION_BLOCKED` because release-equivalent build command, prepared simulator target JSON, isolated DerivedData, install/launch artifact, screenshot/log evidence and UI automation healthcheck were not configured. | Verification Execution Environment / Apple Adapter / Operator | `djconnect`, `djconnect-app` | Blocks broad Apple scenario execution | M | Phase 10E-R |
| VPB-031 | P0 | Product implementation defect | Phase 10E-R found the iOS Release simulator build failed because `DJConnectError.profile` was not handled in the Apple watch-proxy error-code mapper. A local `djconnect-app` fix maps it to `profile_error`; commit that cross-repo fix before treating Phase 10E retry as clean-clone reproducible. | Apple Client | `djconnect-app` | Blocks clean reproducibility until committed | S | Phase 10E retry prerequisite |
| VPB-032 | P0 | Execution Environment / operator configuration issue | Apple verification now has to keep the Xcode/iOS simulator platform current and qualify only the latest eligible stable iOS simulator runtime for the active mode. The latest rerun passed toolchain maintenance with Xcode 26.6 and stable iOS 26.5, then failed closed before live mutation because isolated DerivedData, prepared Apple target JSON, distribution signing expectations and UI healthcheck command/driver were not configured. iOS 27.0 remains available only through the `future_beta` route. | Verification Execution Environment / Operator / Apple Adapter | `djconnect`, `djconnect-app` | Blocks Phase 10E retry and broad Apple scenario execution | M | Phase 10E-R2 |
| VPB-033 | P2 | Release operations follow-up | Docker Hub secret provisioning for the publish workflow is intentionally operator-owned and will be configured outside this branch. Missing GitHub `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` does not block the framework code or documentation in this branch. | Operator / Release Operations | `djconnect` | No | S | Release operations follow-up |
| VPB-034 | P2 | Release operations follow-up | Docker repository naming may be improved later, for example by moving the generic runtime to a clearer verification-platform-specific Docker repository. The current published `pcvantol/djconnect` tags remain valid for this branch. | Operator / Release Operations | Docker Hub | No | S | Release naming follow-up |
| VPB-035 | P1 | Runner infrastructure epic | Self-hosted runner support for labs, Apple simulators, hardware, SSH/serial and signing is deferred to a separate epic. Hosted GitHub runner support for non-mutating framework tests and Docker release publishing is implemented. | Platform Infrastructure | `djconnect` | No | L | Future self-hosted runner epic |
| VPB-036 | P0 | Apple operator configuration follow-up | Provide the stable Apple qualification workspace inputs for the latest eligible stable iOS simulator: approved `DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA` and prepared `DJCONNECT_VERIFICATION_APPLE_TARGET_JSON` that resolves to the current stable runtime, currently iOS 26.5 in the July 11, 2026 evidence. | Operator / Apple Adapter / `djconnect-app` | `djconnect`, `djconnect-app` | Blocks Phase 10E retry and broad Apple scenario execution | S | Phase 10E-R2 reopen prerequisite |
| VPB-037 | P0 | Apple release signing follow-up | Provide release-equivalent signing expectations for the Apple qualification gate: `DJCONNECT_VERIFICATION_APPLE_DISTRIBUTION_IDENTITY`, `DJCONNECT_VERIFICATION_APPLE_TEAM_ID`, `DJCONNECT_VERIFICATION_APPLE_BUNDLE_ID` and `DJCONNECT_VERIFICATION_APPLE_PROVISIONING_PROFILE`, sourced from the operator keychain/provisioning profile inventory. | Operator / Apple Release Engineering | `djconnect-app` | Blocks Phase 10E retry and broad Apple scenario execution | S | Phase 10E-R2 reopen prerequisite |
| VPB-038 | P0 | Apple UI automation follow-up | Provide the UI healthcheck path for the latest-stable simulator qualification: `DJCONNECT_VERIFICATION_APPLE_UI_DRIVER` and `DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND`, preferably using XCTest/accessibility so install, launch, screenshot and scoped logs are validated before scenario mutation. | Apple Adapter / Apple Client / Operator | `djconnect`, `djconnect-app` | Blocks Phase 10E retry and broad Apple scenario execution | M | Phase 10E-R2 reopen prerequisite |

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

Phase 10E reports:

APPLE_RUNTIME_QUALIFICATION_BLOCKED

Phase 10E-R reports:

APPLE_RUNTIME_QUALIFIED

Phase 10E-R2 reports:

APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED

Framework runtime, Docker release workflow and regular CI are not blocked by
Docker Hub secret provisioning, Docker repository naming or self-hosted runner
availability; those are tracked as follow-ups above. Phase 10E-R2 is closed in
this branch as `APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED`. Phase 10E retry
remains blocked until `VPB-031`, `VPB-036`, `VPB-037` and `VPB-038` are
resolved and a Phase 10E-R2 rerun returns `APPLE_LATEST_RUNTIME_QUALIFIED`.
Phase 11 remains blocked until Apple scenario coverage itself has reported.
