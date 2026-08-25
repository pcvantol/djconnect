# Engineering Platform 2.x consumer contract

## Purpose

This contract lets DJConnect, Forge and Workspace consume an installed,
pinned Engineering Platform wheel without carrying EP source code or owning EP
execution data.

## Project registration

Before a consumer submits an Engineering Action, it registers one active
Workspace project with the local EP installation. Registration contains:

- `project_id`: immutable, opaque and canonical in Workspace;
- the validated local repository/workspace path;
- the project-specific writable Inbox root;
- consumer display metadata only, such as project name.

`project_id` is mandatory on every consumer-to-EP operation. Paths, repository
names and display names are not identities and cannot substitute for it.

## Ownership and isolation

EP keeps one installation-wide SQLite database. All EP execution data carries
`project_id` and is queried, queued, leased and displayed within that project
scope. Each project has an independent Inbox route and queue; an execution for
one project can never consume another project's prompt.

Workspace keeps its own planning state and canonical project registry.
Forge remains the owner of planning and Runtime Prompts. EP remains the owner
of execution lifecycle, telemetry, evidence, dashboard, Inbox and Prompt
History. The physical Inbox transport and Workspace API route remain parallel
ways to admit a prompt for the same registered project.

## Upgrade and compatibility

The local upgrade runs before the installed EP process becomes the writer:

1. create a recoverable backup of legacy EP state;
2. verify consumer and wheel compatibility;
3. register the legacy workspace as one canonical project;
4. migrate and backfill project-scoped EP records in place into the central
   installation store;
5. update launchd to the installed EP commands;
6. validate that only the installed EP writer is active.

The consumer pins the immutable EP 2.x wheel version. It must fail closed when
the requested contract version or canonical Workspace `project_id` is absent.
