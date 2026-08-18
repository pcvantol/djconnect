# Tool Output Amplification

- Prompt ID: `tool-output-amplification`
- Title: Tool Output Amplification
- Generation: Engineering Platform Generation 1
- Engineering program: Platform Evolution
- Branch: `codex/tool-output-amplification`
- Commit: `8303dea0ce313b36a3a68b15e2c3616338b66e4f`
- Pull request: [#884](https://github.com/pcvantol/djconnect/pull/884)
- Decision: merged implementation; dedicated governance-only Finalization required
- Execution date: 2026-08-18
- Created: 2026-08-18
- Updated: 2026-08-18

## Outcome

Added invocation-local proxies that bound oversized Git, GitHub, search and
test output at the provider tool boundary. Small output and source reads remain
exact. Bounded output exposes `MORE_EVIDENCE_AVAILABLE`; the provider can rerun
the same narrow command with `DJCONNECT_EVIDENCE_EXPAND=1`. Failed-test output
preserves failure identity, assertion and diagnostic context.

## Validation

- Focused evidence-projection, execution-host and provider-usage tests passed.
- Full Engineering Platform suite passed (489 tests).
- Scoped Ruff and Bandit passed for the new surface.
- `git diff --check` passed.
- CodeQL passed after scoping the temporary environment to the fixed Codex launcher.

## Known limitations

The deterministic fixture measures projected tool-output bytes, not provider
tokens or credits. It reduced fixture output from 12,865 to 4,507 bytes
(64.97%). No real Managed benchmark ran.

## Deferred work

No lifecycle, retry/resume/dismiss, validation policy, reviewer count or
independence, model selection, provider routing/accounting, credit rates, Forge
or delivery authority behavior changed.

## Recommended next prompt

Complete this dedicated Finalization and safe Workspace Cleanup, then select
the next bounded capability from canonical roadmap and backlog evidence.
