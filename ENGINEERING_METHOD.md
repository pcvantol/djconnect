# DJConnect Engineering Method

**Status:** Canonical operational governance
**Version:** 2
**Scope:** Entire DJConnect platform

## Purpose

DJConnect is repository-driven. Current `main` is the canonical engineering
truth. Repository reality always overrides historical plans, prompts and
conversations; neither conversation history nor a prior prompt is required to
continue engineering work.

The repository must remain self-describing: a new AI engineering session can
establish the current state and safely continue from repository contents.

## Operating sequence

```text
Current main
  -> ENGINEERING_STATUS
  -> REPOSITORY_STATUS
  -> Management Summary
  -> Roadmap Index
  -> active roadmap and backlog
  -> Prompt Index
  -> Prompt History only when historical context is needed
```

`BOOTSTRAP.md` is the canonical onboarding entry point. The supporting
operational contracts are `AI_SESSION_INITIALIZATION.md`,
`PROMPT_GOVERNANCE.md`, `PROMPT_FINALIZATION.md` and
`REPOSITORY_HYGIENE.md`.

## Reality before planning

Before every engineering prompt, verify repository state, `ENGINEERING_STATUS`,
the active roadmap, the active backlog and implementation reality. If observed
repository reality differs from the expected state, stop and update planning
before proposing or starting implementation.

Before proposing implementation, establish whether the requested capability
already exists, is validated, is qualified, or is already supported by
repository evidence. Do not reimplement an existing outcome: close only the
remaining gaps, validate and qualify them, record documentation that changed,
then advance to the next increment.

Future work must be supported by current status, roadmap, backlog, accepted
audits, validated gaps or repository evidence. Historical prompt order is
informational only; engineering work is never invented from chat context.

## Ownership and protection

One prompt equals one engineering increment equals one reviewable pull request.
Every increment owns one coherent objective. The Engineering Method itself is
protected: normal implementation prompts must not modify it. Method changes
require a dedicated Engineering Governance prompt.

The Platform Architect owns repository analysis, architecture, prioritization,
engineering planning, prompt generation, governance and review. Codex owns
implementation, validation, documentation, tests, engineering evidence and a
reviewable pull request. Neither role may silently change architecture;
architecture changes require dedicated governance prompts.

Detailed execution rules live in the linked operational contracts so that this
document stays the single canonical method, not a duplicate playbook.
