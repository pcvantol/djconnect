# Verification Platform Scorecard

Status: PLATFORM QUALIFIED; HOME ASSISTANT BACKEND COVERAGE QUALIFIED WITH WARNINGS; APPLE SCENARIO COVERAGE QUALIFIED WITH WARNINGS; RASPBERRY PI SCENARIO COVERAGE QUALIFIED WITH WARNINGS; WINDOWS LIVE QUALIFIED; WINDOWS COVERAGE BASELINE ESTABLISHED

Scoring scale:

- 5 = proven end-to-end
- 4 = implemented with minor gaps
- 3 = implemented but not live-proven
- 2 = partial implementation
- 1 = documented only
- 0 = missing

| Area | Score | Deduction |
| --- | ---: | --- |
| Planning Engine | 4 | Smoke planning now selects first Apple, Raspberry Pi and Windows adapter executable cases while preserving the HA smoke set; broader cross-runtime selection remains future work. |
| Execution Environment | 4 | Exact-SHA CI, Docker runtime discovery, dependency inspection, cleanup planning, lab qualification, scenario-aware Apple-only gates, default sandboxed parallel scenario waves and the generic runtime Docker release path are implemented; minor deduction because some live runs still require approved local Docker or simulator access. |
| Home Assistant Adapter | 4 | Live REST/WebSocket/runtime/storage/log primitives executed across 195 Home Assistant backend and backend assertion-path scenarios; deeper product assertions remain scenario-driven future work. |
| Verification Core | 4 | Aggregated qualified runs, expanded HA backend mappings and preserved primitive diagnostics in summaries; minor deduction because successful primitive timing is still coarse. |
| Evidence Pipeline | 4 | Persisted immutable run evidence with environment, qualification, plan, scenario result files and summary-level diagnostics; richer request/response transcripts remain future adapter evidence work. |
| Coverage Baseline | 4 | Runtime 1.1.0 ingested Home Assistant, Apple and Raspberry Pi native coverage as immutable Coverage Baseline 1; Windows Coverage Baseline 1 is now separately established as a post-Baseline-1 record. |
| Verification Investigator | 4 | Primitive failures are extracted from run summaries and the Phase 9E-R websocket timeout rerun was classified without manual relabeling. |
| Reporting | 4 | Qualification report, scorecard and backlog are current, and execution summaries include total runtime plus scenario status counts; future reports can become more generated. |
| Repository Hygiene | 5 | Branch, SHA and working tree state were known before execution. |
| Build Qualification | 4 | Runtime/build metadata, Verification Platform runtime identity and lab image identity were captured; no production artifact signing was in Phase 9V scope. |
| GitHub CI | 5 | Exact-SHA CI inspected two successful GitHub Actions runs for the tested SHA. |
| Dogfooding Coverage | 4 | Focused verification tests passed 52 tests and catalog validation covered 232 scenarios; live Docker tests remain opt-in. |
| Home Assistant Backend Coverage | 4 | Phase 9E-R executed and qualified 195 HA backend or separable HA backend assertion-path scenarios; 28 client/hardware/release/voice-localization scenarios remain correctly deferred. |
| Apple Adapter | 4 | Thin Apple adapter primitives, Scenario Engine selection and Execution Environment simulator metadata are implemented, mock-tested and live-proven for `APPLE-001`; broader Apple product/UI scenarios remain future coverage. iOS 27.0 evidence is future-beta only, and App Store/TestFlight signing is deferred to release v1.0 readiness. |
| Raspberry Pi Adapter | 4 | Thin Raspberry Pi adapter primitives, CLI registration, Scenario Engine routing and live `PI-001` execution are qualified; broader Pi product scenarios need canonical execution-surface mapping. |
| Windows Adapter | 4 | Thin Windows adapter primitives, canonical `pcvantol/djconnect-windows` ownership metadata, CLI registration, Scenario Engine routing, `WIN-001` mock/local execution and live Parallels Windows execution are qualified. |
| Adapter Roadmap | 4 | Phase 13E-R2 qualified Windows live execution, and Windows Coverage Baseline 1 establishes the first validated Windows coverage starting point for later four-platform reporting. |
| Overall | 4 | The platform is qualified for the next adapter phase with non-blocking framework improvements tracked. |

## Decision

VERIFICATION PLATFORM QUALIFIED

HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS

APPLE_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED

APPLE_RUNTIME_QUALIFICATION_BLOCKED

APPLE_RUNTIME_QUALIFIED

APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED

APPLE_RUNTIME_QUALIFIED_SCENARIO_SELECTION_BLOCKED

APPLE_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS

RASPBERRY_PI_ADAPTER_SELECTED

RASPBERRY_PI_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED

RASPBERRY_PI_SCENARIO_COVERAGE_QUALIFIED_WITH_WARNINGS

WINDOWS_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_PENDING

WINDOWS_LIVE_QUALIFIED

WINDOWS_COVERAGE_BASELINE_ESTABLISHED

The Verification Platform itself remains qualified, and Phase 9E-R qualifies
broad Home Assistant backend coverage with one non-blocking warning. The
warning was a transient local HA websocket timeout affecting two scenarios in a
regenerated batch; the Investigator classified it as an environment issue and
the affected-scenario rerun passed.

Phase 10 completed the thin Apple adapter with mock/unit evidence. Phase 10E
executed the mandatory Apple Runtime Qualification gate first and correctly
failed closed. Phase 10E-R then qualified the originally selected local iOS
simulator runtime path. The later latest-runtime requirement added toolchain
maintenance and target freshness enforcement. The latest Phase 10E-R2 rerun
passed toolchain maintenance with Xcode 26.6 and stable iOS 26.5 available, but
runtime qualification blocked before live mutation because required operator
configuration was absent. Follow-up work resolved the committed `djconnect-app`
clean-clone fix, latest-stable target/DerivedData configuration, XCTest
healthcheck configuration and the local Xcode account/development-signing path.
App Store/TestFlight distribution signing is intentionally deferred until
release v1.0 readiness and is non-blocking for current platform verification.
Phase 10E retry initially qualified the latest eligible simulator runtime but
stopped before broad Apple scenario execution because the planner selected no
Apple adapter executable cases. Phase 10E-R3 resolved that blocker, and the
Phase 10E retry after R3 confirmed the result: smoke planning selects
`APPLE-001`, runtime qualification passed again on iOS 26.5, and `APPLE-001`
executed through the Scenario Engine and Apple adapter with PASS evidence.
Remaining Apple warnings are non-blocking for Phase 11 adapter selection.

Phase 11 selected Raspberry Pi as the next adapter because it provides the
first non-Apple rich client runtime path and covers ambient/shared-room
evidence that is important for Platform Baseline v1.0. The selection phase did
not implement adapter code. The generated Phase 12 prompt owns Raspberry Pi
adapter implementation and must be executed only when explicitly started.

Phase 12 implemented the thin Raspberry Pi adapter and qualified it with mock
and Scenario Engine evidence. Phase 12E then qualified the live Raspberry Pi
runtime path against `rbpi-djconnect.local`: host-keychain GitHub auth passed,
exact-SHA CI inspected two successful runs, SSH and narrow sudoers restart
passed, `djconnect-client` and `djconnect-api` were active after restart, and
`PI-001` executed through the Scenario Engine and Raspberry Pi adapter with
PASS evidence in
`artifacts/verification/evidence/djv-20260712T065051Z-7468abf4dd/`.
Phase 12E-R resolved and qualified the remaining Pi product scenario mapping
warning: canonical smoke planning now exposes 9 Raspberry Pi adapter cases,
including shared-room Profile, Ask DJ shared context, capabilities and Track
Insight coverage, without moving expected behavior into adapter code.
`PROFILE-010`, `CAPABILITIES-005`, `ASKDJ-010` and `TRACKINSIGHT-005` passed in
run `djv-20260712T093801Z-b5be5b3197`, followed by all 9 Pi smoke cases passing
in run `djv-20260712T094155Z-cf11275694`.

Phase 13 implemented the first thin Windows adapter. Smoke planning now selects
`WIN-001` as a Windows adapter case with adapter `windows_native_arm64` and
resource `windows_vm`. `WIN-001` passed through the Scenario Engine and Windows
adapter in mock/local mode in run `djv-20260712T115323Z-0e7b518464`, recording
canonical Windows client ownership as `pcvantol/djconnect-windows`. The local
workstation has Parallels available and the operator confirmed Windows is
available there; live Windows qualification remains pending only a prepared
Windows target JSON and real client artifact/runtime commands.

Parallel execution is now the default for workstation runs. The harness detects
available CPU capacity dynamically, using Apple Silicon performance/efficiency
core metadata when available, and keeps the worker count bounded for local
stability. Operators can tune with `DJCONNECT_VERIFICATION_PARALLEL_WORKERS` or
`--workers <n>`, and can force sequential execution with
`DJCONNECT_VERIFICATION_PARALLEL=0` or `--no-parallel`. Dependencies and
declared exclusive resources remain fail-closed gates before scenarios share a
wave.

Verification Platform runtime release packaging is now available as a generic
Docker image path for runtime version `1.0.0`. The image is intentionally
engine-only: DJConnect scenario catalogs, product checkouts, Home Assistant lab
state, Apple artifacts, secrets and evidence are supplied externally at run
time.

Framework CI, runtime versioning and Docker release workflow readiness are not
blocked in this branch. Docker Hub secret provisioning, Docker repository
renaming and self-hosted runner infrastructure are operator/platform follow-ups
outside this branch. The remaining Apple items are non-blocking future
coverage: broader Apple product/UI scenarios, watchOS paired simulators,
physical devices and App Store/TestFlight distribution signing.
