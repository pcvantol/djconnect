# Verification Platform Backlog

Status: active after Phase 13 Windows adapter qualification

Do not create GitHub issues automatically from this backlog.

## Product-development handoff

The Session Intelligence Runtime and Universal Receiver V1 foundation are
complete. The active Product Development Epic is Automated Session Intelligence
E2E Verification. Its Architecture, Developer Session Bootstrap, Deterministic
Scenario Driver, Immutable E2E Session Capture and Structural Invariant
Validator are complete, while the restricted `SI-GOLDEN-002` Verification Clock
implementation is pending validation/finalization as recorded in
[`docs/product/DEVELOPER_EXPERIENCE_ROADMAP.md`](../../product/DEVELOPER_EXPERIENCE_ROADMAP.md).
Bootstrap enables explicit approved Golden Scenario lifecycle setup for
headless verification rather than manual setup. This record
activates no Verification Platform implementation or simulation runtime. Future scenario, capture,
report and Golden Session work must reuse the canonical Runtime, Planner,
Knowledge Engine, DJ Moment Engine, Session Flow and Broadcast pipeline.

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
| VPB-031 | P0 | Product implementation defect | Resolved in `djconnect-app` commit `9d305764` on `main`/`origin/main`: `DJConnectError.profile` now maps to `profile_error` in the Apple watch-proxy error-code mapper. | Apple Client | `djconnect-app` | No | Done | Phase 10E-R2 follow-up |
| VPB-032 | P0 | Execution Environment / operator configuration issue | Apple verification now has to keep the Xcode/iOS simulator platform current and qualify only the latest eligible stable iOS simulator runtime for the active mode. Follow-up work prepared isolated DerivedData, latest-stable target JSON, the Xcode account/development-signing path and XCTest healthcheck configuration. iOS 27.0 remains available only through the `future_beta` route until it becomes stable. | Verification Execution Environment / Operator / Apple Adapter | `djconnect`, `djconnect-app` | No for current platform verification | Done | Phase 10E-R2 |
| VPB-033 | P2 | Release operations follow-up | Docker Hub secret provisioning for the publish workflow is intentionally operator-owned and will be configured outside this branch. Missing GitHub `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` does not block the framework code or documentation in this branch. | Operator / Release Operations | `djconnect` | No | S | Release operations follow-up |
| VPB-034 | P2 | Release operations follow-up | Resolved: the generic Verification Platform runtime now uses the dedicated Docker Hub repository `pcvantol/djconnect-verification-platform` in workflow defaults, CLI defaults and operator docs. | Operator / Release Operations | Docker Hub | No | Done | Release naming follow-up |
| VPB-035 | P1 | Runner infrastructure epic | Self-hosted runner support for labs, Apple simulators, hardware, SSH/serial and signing is deferred to a separate epic. Hosted GitHub runner support for non-mutating framework tests and Docker release publishing is implemented. | Platform Infrastructure | `djconnect` | No | L | Future self-hosted runner epic |
| VPB-036 | P0 | Apple operator configuration follow-up | Resolved for the local stable runtime path: `apple prepare-qualification-config` now emits an approved `DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA` path under `artifacts/verification/apple/DerivedData` and a prepared `DJCONNECT_VERIFICATION_APPLE_TARGET_JSON` for latest stable iOS 26.5. The July 11, 2026 rerun selected `D1DDCACC-2651-4EB9-A55E-2315C9314AA6` on `com.apple.CoreSimulator.SimRuntime.iOS-26-5`. | Operator / Apple Adapter / `djconnect-app` | `djconnect`, `djconnect-app` | No | Done | Phase 10E-R2 follow-up |
| VPB-037 | P0 | Apple Xcode account and signing follow-up | Resolved for current platform verification: the verifier now has an explicit `xcode_account` gate using `xcodebuild -allowProvisioningUpdates`, and local Xcode 27 beta build evidence resolved team `ZEML4LPXH4`, bundle `dev.djconnect.ios`, signing identity `Apple Development: Peter van Tol (4R93ZR43D5)` and profile `iOS Team Provisioning Profile: dev.djconnect.ios` / `00d91f4f-5a9e-4f13-8790-2393253068e7`. App Store/TestFlight distribution signing is intentionally deferred until release v1.0 readiness and is non-blocking for this platform verification phase. | Operator / Apple Release Engineering | `djconnect-app` | No for current platform verification; release-v1.0 readiness follow-up for App Store/TestFlight | Done for Phase 10E-R2 | Release v1.0 readiness |
| VPB-038 | P0 | Apple UI automation follow-up | Resolved as a prepared XCTest healthcheck path: `apple prepare-qualification-config` emits `DJCONNECT_VERIFICATION_APPLE_UI_DRIVER=xctest` and a latest-stable simulator `xcodebuild test` command for `DJConnectIOSUITests/DJConnectIOSUITests/testPrimaryTabsAreAvailable`. The runtime gate now skips UI healthcheck before mutation whenever prerequisite signing/build/target gates are blocked. | Apple Adapter / Apple Client / Operator | `djconnect`, `djconnect-app` | No | Done | Phase 10E-R2 follow-up |
| VPB-039 | P0 | Planning Engine / Scenario Engine mapping blocker | Resolved in Phase 10E-R3: smoke planning now selects `APPLE-001` as an Apple adapter executable case, the CLI can register the Apple adapter for scenario execution, env-file target JSON is loaded for execute commands, and Apple-only runs skip unrelated HA/Docker gates. `APPLE-001` passed through the Scenario Engine and Apple adapter. | Planning Engine / Scenario Engine / Apple Adapter | `djconnect` | No | Done | Phase 10E-R3 |
| VPB-040 | P0 | Raspberry Pi Adapter gap | Resolved in Phase 12: thin Raspberry Pi adapter, CLI registration, Scenario Engine routing, `PI-001` runtime smoke scenario and mock/unit primitive tests are implemented. Live runtime proof is skipped until a prepared Pi target and exact-SHA environment gates are available. | Raspberry Pi Adapter / Execution Environment / Planning Engine | `djconnect`, `djconnect-pi` | No for adapter implementation; live coverage remains future scope | Done | Phase 12 |
| VPB-041 | P1 | Scenario Catalog cleanup | Some Pi-relevant shared scenarios mention Pi in title or platform intent but still declare Apple/Windows runtime requirements. Phase 12 added a Pi-specific runtime smoke scenario instead of rewriting shared expectations. Broader Pi scenario coverage should only adjust shared scenario requirements when backed by canonical behavior. | Scenario Catalog / Planning Engine | `djconnect` | No | S | Phase 12E |
| VPB-042 | P0 | Raspberry Pi runtime environment issue | Resolved in Phase 12E: approved host-keychain `gh auth status` passed, exact-SHA CI inspected two successful runs for `d3813c275e910c9723f91d8f294a622d46fda206`, SSH to `rbpi-djconnect.local` passed, narrow sudoers restart passed and `PI-001` executed through the Scenario Engine and Raspberry Pi adapter with PASS evidence. | Execution Environment / Operator | `djconnect` | No | Done | Phase 12E |
| VPB-043 | P1 | Planning Engine / Scenario Catalog coverage gap | Resolved and qualified in Phase 12E-R: Pi runtime capability metadata now maps shared Pi product scenarios to the Raspberry Pi adapter, `PROFILE-010` and `ASKDJ-010` declare their Pi execution surface, full smoke planning exposes 9 Raspberry Pi cases instead of only `PI-001`, the focused remediation set passed in run `djv-20260712T093801Z-b5be5b3197`, and the full 9-case Pi smoke set passed in run `djv-20260712T094155Z-cf11275694`. | Planning Engine / Scenario Catalog / Raspberry Pi Adapter | `djconnect`, `djconnect-pi` | No | Done | Phase 12E-R |
| VPB-044 | P0 | Windows Adapter gap | Resolved in Phase 13: thin Windows adapter, CLI registration, Scenario Engine routing, `WIN-001` runtime smoke scenario, canonical `pcvantol/djconnect-windows` ownership metadata and mock/local primitive execution are implemented. `WIN-001` passed in run `djv-20260712T115323Z-0e7b518464`. | Windows Adapter / Execution Environment / Planning Engine | `djconnect`, `djconnect-windows` | No | Done | Phase 13 |
| VPB-045 | P1 | Windows runtime environment follow-up | Resolved in Phase 13E-R: the Parallels `Windows 11 Home` target JSON was prepared, `windows_dotnet_maintenance` passed and `WIN-001` reached the real `pcvantol/djconnect-windows` checkout in run `djv-20260712T123021Z-ccda65836f`. The phase is now blocked by a sibling Windows client build failure, not by missing target configuration. | Windows Adapter / Execution Environment / Operator | `djconnect`, `djconnect-windows` | No | Done | Phase 13E-R |
| VPB-049 | P0 | Windows client build blocker | Resolved in Phase 13E-R2: `StatusResponse` in `pcvantol/djconnect-windows` now deserializes backend-owned Profile / Music DNA metadata consumed by the ViewModel, Windows repo tests pass, the Parallels Windows build for `net10.0-windows10.0.19041.0` succeeds and `WIN-001` passed live in run `djv-20260712T135722Z-d09b6ec5ba`. | Windows Client / Windows Adapter / Execution Environment | `djconnect-windows`, `djconnect` | No | Done | Phase 13E-R2 |
| VPB-046 | P1 | Coverage improvement increment | Phase 15 Platform Test Coverage Improvement is inserted after Coverage Baseline 1, Phase 13E Windows live qualification and Phase 14 Cross-Platform Qualification, before Platform Baseline v1.0 Certification. Coverage must improve through meaningful tests, deeper verification and improved testability, not by excluding production code or manipulating scope. | Verification Coverage / Platform Repositories | `djconnect`, `djconnect-app`, `djconnect-pi`, `djconnect-windows` | No | L | Phase 15 Platform Test Coverage Improvement |
| VPB-047 | P1 | Windows coverage baseline dependency | Resolved by Windows Coverage Baseline 1: Runtime 1.1.0 ingested native Coverlet Cobertura for `pcvantol/djconnect-windows` commit `b205f087214eb5fe90c4129c2afa9dee7f836a82` as `COVERAGE_VALID`, with 72.45% line and 50.85% branch coverage. Coverage Baseline 1 remains unchanged and Windows can be included in a future coordinated four-platform coverage snapshot. | Windows Adapter / Coverage Runtime / Windows Client | `djconnect`, `djconnect-windows` | No | Done | Windows Coverage Baseline 1 |
| VPB-048 | P1 | Coverage scope guardrail | Before adding tests in Phase 15, verify production source roots and coverage scope for Home Assistant, Apple, Raspberry Pi and Windows. Coverage improvement must preserve `COVERAGE_VALID`, avoid production-code exclusions used only to improve percentages and track trends against immutable Coverage Baseline 1. | Coverage Runtime / Repository Maintainers | All platform repositories | No | M | Phase 15 Platform Test Coverage Improvement |

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

Phase 10E-R3 reports:

APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS

Phase 11 reports:

RASPBERRY_PI_ADAPTER_SELECTED

Phase 12 reports:

RASPBERRY_PI_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED

Phase 12E reports:

RASPBERRY_PI_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS

Phase 13 reports:

WINDOWS_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING

Coverage Baseline 1 reports:

CROSS_PLATFORM_COVERAGE_BASELINE_ESTABLISHED

Windows Coverage Baseline 1 reports:

WINDOWS_COVERAGE_BASELINE_ESTABLISHED

Phase 15 is now registered as the Platform Test Coverage Improvement increment
after Coverage Baseline 1, Windows Coverage Baseline 1, Phase 13E Windows live
qualification and Phase 14 Cross-Platform Qualification, before Platform
Baseline v1.0 Certification. Coverage Baseline 1 remains immutable historical
evidence.

Framework runtime, Docker release workflow and regular CI are not blocked by
Docker Hub secret provisioning, Docker repository naming or self-hosted runner
availability; those are tracked as follow-ups above. Phase 10E-R2's App
Store/TestFlight distribution-signing gap is explicitly non-blocking for the
current platform verification phase and moves to release-v1.0 readiness. Phase
10E-R3 resolved the planner/scenario mapping blocker, and the Phase 10E retry
after R3 qualified the first Apple executable scenario set with non-blocking
warnings. Phase 11 selected Raspberry Pi as the next adapter. Phase 12
implemented and mock-qualified the thin Raspberry Pi adapter with live runtime
skipped. Phase 12E qualified the live Raspberry Pi runtime smoke path with
non-blocking warnings. Phase 12E-R resolved and qualified the Pi product
scenario mapping warning; smoke planning now exposes multiple Raspberry Pi
adapter cases and the first broader Pi product batch passed.
