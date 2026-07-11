# Verification Platform Scorecard

Status: PLATFORM QUALIFIED; HOME ASSISTANT BACKEND COVERAGE QUALIFIED WITH WARNINGS; APPLE LATEST RUNTIME QUALIFICATION BLOCKED

Scoring scale:

- 5 = proven end-to-end
- 4 = implemented with minor gaps
- 3 = implemented but not live-proven
- 2 = partial implementation
- 1 = documented only
- 0 = missing

| Area | Score | Deduction |
| --- | ---: | --- |
| Planning Engine | 4 | Correctly generated the five-case smoke plan and selected `ha-profile`; minor deduction because `PROFILE-002` still carries future rich-client resources into an HA-only plan as external requirements. |
| Execution Environment | 4 | Exact-SHA CI, Docker runtime discovery, dependency inspection, cleanup planning, lab qualification, default sandboxed parallel scenario waves and the generic runtime Docker release path are implemented; minor deduction because live runs still require approved local Docker access. |
| Home Assistant Adapter | 4 | Live REST/WebSocket/runtime/storage/log primitives executed across 195 Home Assistant backend and backend assertion-path scenarios; deeper product assertions remain scenario-driven future work. |
| Verification Core | 4 | Aggregated qualified runs, expanded HA backend mappings and preserved primitive diagnostics in summaries; minor deduction because successful primitive timing is still coarse. |
| Evidence Pipeline | 4 | Persisted immutable run evidence with environment, qualification, plan, scenario result files and summary-level diagnostics; richer request/response transcripts remain future adapter evidence work. |
| Verification Investigator | 4 | Primitive failures are extracted from run summaries and the Phase 9E-R websocket timeout rerun was classified without manual relabeling. |
| Reporting | 4 | Qualification report, scorecard and backlog are current, and execution summaries include total runtime plus scenario status counts; future reports can become more generated. |
| Repository Hygiene | 5 | Branch, SHA and working tree state were known before execution. |
| Build Qualification | 4 | Runtime/build metadata, Verification Platform runtime identity and lab image identity were captured; no production artifact signing was in Phase 9V scope. |
| GitHub CI | 5 | Exact-SHA CI inspected two successful GitHub Actions runs for the tested SHA. |
| Dogfooding Coverage | 4 | `tests/verification` passed 116 tests and catalog validation covered 231 scenarios; live Docker tests remain opt-in. |
| Home Assistant Backend Coverage | 4 | Phase 9E-R executed and qualified 195 HA backend or separable HA backend assertion-path scenarios; 28 client/hardware/release/voice-localization scenarios remain correctly deferred. |
| Apple Adapter | 3 | Thin Apple adapter primitives, Scenario Engine selection and Execution Environment simulator metadata are implemented and mock-tested; Phase 10E-R qualified an older selected iOS simulator runtime, and the latest Phase 10E-R2 rerun resolved stable iOS 26.5 but remains blocked until operator signing, target, DerivedData and UI healthcheck configuration are provided. iOS 27.0 evidence is future-beta only. |
| Overall | 4 | The platform is qualified for the next adapter phase with non-blocking framework improvements tracked. |

## Decision

VERIFICATION PLATFORM QUALIFIED

HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS

APPLE_ADAPTER_QUALIFIED_WITH_LIVE_RUNTIME_SKIPPED

APPLE_RUNTIME_QUALIFICATION_BLOCKED

APPLE_RUNTIME_QUALIFIED

APPLE_LATEST_RUNTIME_QUALIFICATION_BLOCKED

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
configuration was absent: isolated DerivedData, prepared Apple target JSON,
distribution signing expectations and UI healthcheck command/driver. Phase
10E-R2 is closed in this branch as blocked; continue only by resolving
`VPB-031`, `VPB-036`, `VPB-037` and `VPB-038`, then rerun Phase 10E-R2 before
Phase 10E retry or Phase 11.

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
outside this branch. The remaining blocking item is Apple Phase 10E-R2 stable
runtime qualification configuration.
