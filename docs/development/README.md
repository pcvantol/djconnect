# Development Documentation

This area contains repository-owned documentation for how Product & Platform
Architecture collaboration continues across engineering conversations. It does
not define product architecture, Runtime behaviour, capability ownership,
roadmap priority or implementation work.

## Collaboration navigation

`BOOTSTRAP.md` remains the single canonical repository entry point. It invokes
the Developer Handoff for Product & Platform Architect continuity, which then
consumes the existing Product Development workflow:

```text
Repository BOOTSTRAP
        ↓
Developer Handoff
        ↓
Product Development Workflow
        ↓
Future engineering process documentation
```

This is one navigation path, not a second bootstrap mechanism. The Developer
Handoff helps a new conversation interpret current repository evidence; it
does not replace repository synchronization, canonical governance or product
architecture.

## Current documents

- [Developer Handoff](DEVELOPER_HANDOFF.md) — the repository-first continuity
  workflow for a new ChatGPT Product & Platform Architect session.
- [Product Development workflow](../../ENGINEERING_PROGRAM_MODEL.md#product-development-assessment-workflow)
  — the canonical assessment-first delivery workflow, including its conditional
  DJ Intelligence and Golden Scenario assessments.
- [Local Agent Runner](LOCAL_AGENT_RUNNER.md) — the bounded, resumable local
  Codex CLI transaction runner for repository-grounded engineering work,
  including watcher, dashboard and local-report operation.
- [Engineering Inbox Protocol](../../tools/engineering/ENGINEERING_INBOX_PROTOCOL.md)
  — accepted prompt files, ordering and iCloud delivery boundaries.
- [Engineering Report Evidence Contract](../engineering/ENGINEERING_REPORTING.md)
  — how initial observations, final repository evidence and terminal reports
  are interpreted.

Future development-process documentation belongs here only when it explains
how collaboration or engineering work is performed. Product direction remains
in `docs/product/`, architecture remains in the foundation and technical
documents, and canonical engineering-method controls remain in `docs/meta/`
and `docs/governance/`.
