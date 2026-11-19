# Primary Agent Tool-Loop Churn

- Prompt ID: `primary-agent-tool-loop-churn`
- Title: Primary Agent Tool-Loop Churn
- Generation: Engineering Platform Generation 1
- Engineering program: Platform Evolution
- Branch: `codex/primary-agent-tool-loop-ledger`
- Commit: `9196497397ee68ae98948f8e05d149ad260b2d5e`
- Pull request: [#879](https://github.com/pcvantol/djconnect/pull/879)
- Decision: merged implementation; dedicated governance-only Finalization required
- Execution date: 2026-08-18
- Created: 2026-08-18
- Updated: 2026-08-18

## Outcome

Added an ephemeral primary-provider investigation ledger with identifier-only
facts and conservative invalidation at mutation and lifecycle boundaries. The
primary prompt now reuses unchanged investigation facts and prefers bounded
Git queries, while the existing reviewer reasoning boundary remains intact.
The context-churn projection adds derived `tool_loop_operations` telemetry
from existing command events without a database-schema change.

## Validation

- `python3 -m unittest discover -s tests/engineering -p 'test_*.py'` passed (481 tests).
- Scoped Ruff and Bandit passed for the new and clean changed surfaces.
- `git diff --check` passed.
- No real Managed Engineering Platform benchmark ran.

## Known limitations

The deterministic fixture measures observed tool-loop operations only. It does
not attribute provider tokens to individual commands or claim token savings.

## Deferred work

No lifecycle, retry/resume/dismiss, validation, reviewer selection or
independence, model selection, provider routing/accounting, credit rates,
Forge or delivery authority behavior changed.

## Recommended next prompt

Select the next bounded capability from canonical roadmap and backlog evidence
after this Finalization merges and Workspace Cleanup establishes
`WORKSPACE_READY`.
