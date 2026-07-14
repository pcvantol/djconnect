# DJConnect Repository Bootstrap

**Status:** Canonical repository onboarding

Start every clean engineering session from current `main`, then read the
following order. Do not use prior conversations as a substitute.

```text
BOOTSTRAP.md
  -> ENGINEERING_STATUS.md
  -> REPOSITORY_STATUS.md
  -> MANAGEMENT_SUMMARY.md
  -> ROADMAP_INDEX.md
  -> current active roadmap
  -> current active backlog
  -> PROMPT_INDEX.md
  -> docs/history/prompts/ only when historical context is required
```

The records have distinct responsibilities:

| Record | Responsibility |
| --- | --- |
| `BOOTSTRAP.md` | Repository onboarding and reading order. |
| `ENGINEERING_STATUS.md` | Operational engineering handoff, current increment, deferred work and recommended next prompt. |
| `REPOSITORY_STATUS.md` | Objective repository state. |
| `MANAGEMENT_SUMMARY.md` | Executive engineering summary. |
| `ROADMAP_INDEX.md` | Canonical roadmap navigation. |
| `PROMPT_INDEX.md` | Prompt lifecycle and navigation. |
| `docs/history/prompts/` | Immutable engineering history, never current-state authority. |

After reading, verify repository reality as required by
`AI_SESSION_INITIALIZATION.md`. If it differs from planning, stop and update
planning first. Continue with local `AGENTS.md`, applicable foundation and Meta
Engineering guidance only as required by the selected increment.

`BOOTSTRAP_CODEX_SESSION.md` remains the platform-wide supplemental bootstrap;
this file is the canonical repository-state entry point.
