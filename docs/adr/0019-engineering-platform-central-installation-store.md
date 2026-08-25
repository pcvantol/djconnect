# ADR-0019 — Engineering Platform uses one central installation store

**Status:** Accepted for the Engineering Platform 2.x extraction  
**Date:** 2026-08-25

## Context

Engineering Platform 1.x currently resolves its SQLite state from a consumer
workspace. That prevents one installed Execution Host from safely serving
multiple Workspace projects in parallel: each project gets a disconnected
queue, dashboard projection and evidence store.

Workspace is gaining multi-project support. A single installed Engineering
Platform must therefore execute and present several local projects without
making a repository checkout the installation boundary or creating two writers
for the same database.

## Decision

Engineering Platform 2.x will use exactly one installation-owned data root and
one SQLite database per local EP installation. On macOS the default data root
will be under the user's Application Support directory; other supported
platforms will resolve an equivalent per-user application-data location. It is
outside every consumer repository and outside the published wheel.

Workspace remains the authority for the canonical `project_id`. EP records
that opaque ID as `project_id` on every project-scoped operational record; it
does not mint, translate or infer a competing project identity. The consumer
contract registers the project ID, repository/workspace location and validated
Inbox root before EP accepts work for that project.

The central store contains EP-owned operational data, scoped by `project_id`:

- project registration and Inbox routing;
- one queue and one execution lease domain per project;
- execution lifecycle, telemetry, Prompt History, Engineering Reports and
  Execution Receipts;
- project-scoped dashboard preferences, logs and status projections.

Installation-wide configuration (EP version, provider capabilities and update
state) remains unscoped. Workspace/Forge planning data and the Workspace
database remain consumer-owned and are never written by EP.

The dashboard presents a project selector above project-scoped views. Every
queue, Inbox, execution, report, receipt, telemetry and Prompt History query
is filtered by the selected canonical `project_id`; no project has implicit
access to another project's records.

The migration creates a backup, registers the legacy workspace as one project,
backfills `project_id` atomically, validates Inbox ownership and then starts
the single installation-owned writer. Legacy per-workspace EP databases are
not retained as live writers. A failed migration leaves the prior installation
recoverable from its backup.

## Consequences

- Parallel local work is supported across projects, while ordering and leases
  remain isolated within each project.
- A published EP wheel can be installed once and used by several consumer
  workspaces without embedding EP source in those repositories.
- Consumer integrations must pass a canonical Workspace `project_id`; a path
  or repository name is insufficient identity.
- Existing 1.x local state requires an explicit, reversible upgrade rather
  than silent discovery from the current directory.

## Alternatives considered

1. Keep one EP database per workspace. Rejected: it makes one installed EP a
   collection of unrelated runtimes and cannot present or operate multiple
   projects coherently.
2. Put all project data in the Workspace database. Rejected: it would give the
   consumer ownership of EP execution lifecycle and evidence.
3. Use a cloud store. Rejected: EP remains local-first and must work without a
   network service.

## Affected repositories

- `pcvantol/engineering-platform` (new package, data migration and dashboard)
- `pcvantol/djconnect` (thin consumer contract and local upgrade bridge)
- Forge/Workspace (canonical project-ID and registration contract)

## Related documents

- [Engineering Platform migration report](../development/ENGINEERING_PLATFORM_MIGRATION_REPORT.md)
- [Engineering Platform consumer contract](../development/ENGINEERING_PLATFORM_CONSUMER_CONTRACT.md)
- [Engineering Platform architecture handbook](../engineering/ENGINEERING_PLATFORM_ARCHITECTURE_HANDBOOK.md)
