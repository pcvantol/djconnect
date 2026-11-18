# Platform Release Engineering — Generation 1 Prompt 2

Status: complete; superseded by the explicitly authorized orchestration scope  
Predecessor: `PLATFORM_RELEASE_ARCHITECTURE_COMPLETE`

## Mission

Implement the canonical Platform Release Orchestrator in simulation-only mode,
including the release-planning and repository-discovery contract defined by
`docs/release/PLATFORM_RELEASE_ARCHITECTURE.md`.

## Required reading

- `docs/release/PLATFORM_RELEASE_ARCHITECTURE.md`
- `docs/release/PLATFORM_RELEASE_ROADMAP.md`
- `REPOSITORY_OWNERSHIP.md`
- `SOFTWARE_ASSURANCE_INTEGRATION.md`
- `SOFTWARE_ASSURANCE_EXECUTION_MODEL.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`

## Scope

- Implement repository discovery from Repository Ownership without making a
  second ownership source of truth.
- Implement manifest, release-plan, dependency-edge, mode/profile, readiness,
  artifact and rollback contracts with unit tests and a simulation CLI.
- Validate required, optional, distribution and future node handling.
- Produce a completion report and generate Prompt 3 without starting it.
- Update canonical navigation, roadmap and completion report according to the
  phase protocol.

## Out of scope

- Do not modify `REPOSITORY_OWNERSHIP.md` merely to make it machine-readable.
- Do not hardcode repository membership.
- Do not change repository versions, create tags, build production artifacts,
  execute a platform release, publish, deploy or announce a release.

## Acceptance criteria

- The runtime preserves Repository Ownership as canonical truth.
- A future repository can participate by declared ownership/role data without
  orchestrator code changes.
- Plan identity, evidence references, readiness conditions and rollback
  checkpoints are machine-readable.
- The runtime stays reusable and does not encode DJConnect product behaviour.
- A completion report, qualification decision and only the next prompt are
  generated; the next phase is not started.
