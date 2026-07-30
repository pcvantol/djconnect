# Local Agent Runner and Resumable Engineering Transactions

- **Prompt ID:** `local-agent-runner`
- **Title:** Local Agent Runner and Resumable Engineering Transactions
- **Generation and program:** Generation 2 — Platform Evolution developer enablement
- **Branch:** `codex/local-agent-runner`
- **Implementation commit:** `938227c4291e9d8c0b1adbb06b518aaa49312233`
- **Pull request:** [#600](https://github.com/pcvantol/djconnect/pull/600)
- **Merge commit:** `1145f1e31a2f0504632b466c0a0abdcfea3007f4`
- **Decision and execution date:** 2026-07-30 — implemented and merged

## Objective

Provide the smallest useful local, repository-scoped foreground runner for one
bounded Codex CLI engineering transaction, including safe resume state and
terminal-evidence polling.

## Result

`./tools/engineering/dj-engineer` invokes Codex CLI with canonical repository
instructions and the supplied prompt. Its atomic Git-ignored checkpoint is
advisory only; repository and GitHub evidence determine continuation and
completion. Pending CI is never successful completion. The runner has no merge,
release, deployment, daemon, remote-control, Runtime or product authority.

## Validation

- `python3 -m unittest discover -s tests`
- `python3 -m unittest tests.engineering.test_dj_engineer tests.test_capability_completion_lifecycle`
- `python3 -m ruff check tools/engineering tests/engineering`
- `python3 -m tools.software_assurance.validate`
- `python3 -m bandit -c pyproject.toml -r tools/engineering --severity-level medium`
- `git diff --check`
- Required PR checks, Trusted Delivery and Owner Authorization passed; Owner
  Authorization was not required for normal risk.

## Known limitations

The first version is foreground-only and single-repository. It intentionally
does not implement automatic merge, release, deployment, CI repair,
multi-repository coordination, scheduling, notifications or remote control.

## Deferred work

Any automatic merge/finalization capability remains a separately qualified
future increment; it is not authorized by this local-runner implementation.

## Recommended next prompt

Return to the canonical Product Development or Platform Evolution queue and
select work only from current repository evidence.
