# Platform Release Engineering — Generation 1 Prompt 3

Status: generated; not active until explicitly authorized  
Predecessor: `PLATFORM_RELEASE_ORCHESTRATOR_QUALIFIED`

## Mission

Execute and qualify the first complete Platform Release Dry Run using the
simulation-only Platform Release Orchestrator.

## Required reading

- `docs/release/PLATFORM_RELEASE_ARCHITECTURE.md`
- `docs/release/RUNTIME.md`
- `docs/release/PROMPT_02_RELEASE_ORCHESTRATOR_COMPLETION.md`
- `REPOSITORY_OWNERSHIP.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Scope

- Prepare an immutable candidate fact bundle for the selected platform train:
  ownership snapshot, versions, source SHAs and authoritative evidence states.
- Run `tools.release` in `dry_run` mode and persist the generated reports as
  non-production evidence.
- Validate manifest schema, execution plan, readiness, qualification plan,
  artifact plan and rollback plan.
- Investigate any `NOT_READY` or `BLOCKED` state before claiming qualification.

## Non-negotiable constraints

- Do not modify any repository version.
- Do not create tags, releases, deployments, publications, store submissions
  or announcements.
- Do not use production credentials or mutate a distribution channel.
- Do not change the runtime to hide missing evidence; classify and report it.

## Acceptance criteria

- A complete, non-publishing Release Manifest and supporting plans exist as
  dry-run evidence.
- Every required readiness condition is either `READY` or explicitly blocks
  the dry-run decision.
- The result is `PASS`, `PASS WITH WARNINGS`, `NOT QUALIFIED` or `BLOCKED`
  based on evidence.
- Completion reporting and Prompt 4 generation occur only after the dry-run
  outcome is known; Prompt 4 is not started.
