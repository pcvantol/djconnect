# Phase 17 Platform Test Coverage Improvement

Status: Active

## Objective

Increase meaningful automated coverage across the qualified DJConnect platform
repositories without narrowing production coverage scope or changing the
immutable historical Coverage Baseline 1.

## Required Context

1. `BOOTSTRAP_CODEX_SESSION.md`
2. `BOOTSTRAP_CODEX_VERIFICATION.md`
3. `PROMPT_INDEX.md`
4. `PLATFORM_BACKLOG.md`
5. `CODE_COVERAGE_BASELINE_1.md`
6. `CODE_COVERAGE_WINDOWS_BASELINE_1.md`
7. `tools/verification/RUNTIME_COVERAGE.md`
8. `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

Read the local bootstrap and implementation guidance in each sibling repository
before modifying that repository.

## Preconditions

- Phase 16-R returned `CROSS_PLATFORM_QUALIFIED`.
- Coverage Baseline 1 remains immutable historical evidence.
- Windows Coverage Baseline 1 is available as the Windows starting point.
- Every submitted coverage report is generated for the exact repository SHA
  being qualified and is accepted as `COVERAGE_VALID`.

## Scope

- verify production source roots, exclusions and native coverage commands for
  Home Assistant, Apple, Raspberry Pi and Windows;
- identify uncovered paths from current native reports and select tests by
  product and regression risk;
- add meaningful tests or narrowly scoped testability improvements only when
  they exercise production behaviour;
- generate fresh native coverage reports and ingest normalized evidence through
  Verification Runtime `1.1.0`;
- compare results against Coverage Baseline 1 and Windows Coverage Baseline 1;
- publish a completion report, evidence references, investigation findings and
  a qualification decision.

## Out Of Scope

- changing production coverage scope, excluding valid production source, or
  removing difficult code from measurement;
- changing scenario expectations merely to make a result pass;
- Platform Baseline v1.0 certification;
- Software Assurance implementation;
- new verification architecture or product capabilities.

## Acceptance Criteria

- each participating repository's production scope and exclusions are recorded
  and policy-justified;
- critical uncovered paths are identified before tests are added;
- all reported coverage is `COVERAGE_VALID` for the exact measured SHA;
- Home Assistant, Apple and Windows improve measurably over their documented
  starting points, or a platform-specific external/runtime blocker is
  classified with evidence;
- Raspberry Pi does not regress;
- targeted regressions and native test suites pass;
- reports include trend analysis, known limitations and evidence locations;
- `git diff --check` passes.

## Completion

Follow `docs/meta/PHASE_COMPLETION_PROTOCOL.md`. Do not start Platform
Baseline v1.0 Certification or any deferred Software Assurance work after this
phase.
