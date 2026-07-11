# Verification Platform Scorecard

Status: PLATFORM QUALIFIED; HOME ASSISTANT BACKEND COVERAGE NOT QUALIFIED

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
| Execution Environment | 4 | Exact-SHA CI, Docker runtime discovery, dependency inspection, cleanup planning and lab qualification passed; minor deduction because live runs still require approved local Docker access. |
| Home Assistant Adapter | 4 | Live REST/WebSocket runtime primitives executed for `PROFILE-001` through `PROFILE-005`; deeper product assertions remain scenario-driven future work. |
| Verification Core | 4 | Aggregated the qualified run and persisted per-scenario results; minor deduction because successful primitive timing is still coarse. |
| Evidence Pipeline | 4 | Persisted immutable run evidence with environment, qualification, plan and scenario result files; richer request/response transcripts remain future adapter evidence work. |
| Verification Investigator | 3 | Investigation workflow was dogfooded and enabled a correct manual classification; automated heuristics still reported the initial wrapper failure as `unknown`. |
| Reporting | 4 | Qualification report, scorecard and backlog are current; future reports can become more generated. |
| Repository Hygiene | 5 | Branch, SHA and working tree state were known before execution. |
| Build Qualification | 4 | Runtime/build metadata and lab image identity were captured; no production artifact signing was in Phase 9V scope. |
| GitHub CI | 5 | Exact-SHA CI inspected two successful GitHub Actions runs for the tested SHA. |
| Dogfooding Coverage | 4 | `tests/verification` passed 69 tests and catalog validation covered 231 scenarios; live Docker tests remain opt-in. |
| Home Assistant Backend Coverage | 1 | Phase 9E recomputed 223 HA/DJConnect-related scenarios and executed only the five currently mapped Profile scenarios. Broad HA backend coverage is not qualified until Scenario Engine mappings expand. |
| Overall | 4 | The platform is qualified for the next adapter phase with non-blocking framework improvements tracked. |

## Decision

VERIFICATION PLATFORM QUALIFIED

HOME_ASSISTANT_BACKEND_NOT_QUALIFIED

The Verification Platform itself remains qualified, but Phase 9E proved that
full Home Assistant backend coverage is not yet qualified. The prior platform
qualification is scoped to the first approved Profile scenario set and the
dedicated Home Assistant lab; future adapters still require their own
qualification before trust expands to those runtimes.

Phase 9E executed on 2026-07-11 and did not qualify broad Home Assistant
backend coverage. Phase 10 remains blocked until Phase 9E-R returns
`HOME_ASSISTANT_BACKEND_QUALIFIED` or
`HOME_ASSISTANT_BACKEND_QUALIFIED_WITH_WARNINGS` with Apple-safe warnings.
