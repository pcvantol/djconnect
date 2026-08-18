# Provider Invocation Terminology Guard

- Prompt ID: `provider-invocation-terminology-guard`
- Title: Provider Invocation Terminology Guard
- Generation: Engineering Platform Generation 1
- Engineering program: Platform Evolution
- Branch: `codex/provider-invocation-terminology-guard`
- Commit: `6d7df9c728deb547603e41ba2146452c398f309a`
- Pull request: [#881](https://github.com/pcvantol/djconnect/pull/881)
- Decision: merged implementation; dedicated governance-only Finalization required
- Execution date: 2026-08-18
- Created: 2026-08-18
- Updated: 2026-08-18

## Outcome

Added focused regression coverage for the existing user-facing provider usage
projections. The guard ensures that **Provider Invocation Cumulative Input**
cannot be relabelled as `context size`, `active context` or `request context`.
It retains `Actual Single-Request Context: UNAVAILABLE` rather than inventing
an unavailable measurement.

## Validation

- Focused execution-host terminology coverage passed.
- `python3 -m unittest tests.engineering.test_execution_host` passed (136 tests).
- Focused Operations Console browser coverage passed.
- No runtime reporting or telemetry design changed.

## Known limitations

Provider Invocation Cumulative Input is cumulative usage, not a simultaneous
context-size measurement. Actual Single-Request Context remains unavailable.

## Deferred work

No lifecycle, retry/resume/dismiss, validation, reviewer independence, model
selection, provider routing/accounting, credit rates, Forge or delivery
authority behavior changed.

## Recommended next prompt

Select the next bounded capability from canonical roadmap and backlog evidence
after this Finalization merges and Workspace Cleanup establishes
`WORKSPACE_READY`.
