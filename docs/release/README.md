# Platform Release Engineering

Status: canonical navigation  
Scope owner: `pcvantol/djconnect`

Platform Release Engineering is the reusable, platform-wide release control
model. It coordinates participating repositories without making a repository
release process the source of truth.

## Canonical documents

- `PLATFORM_RELEASE_ARCHITECTURE.md` is the frozen Generation 1 release
  architecture: versioning, lifecycle, qualification, certification, dry-run,
  rollback, evidence and orchestration.
- `PLATFORM_RELEASE_ROADMAP.md` sequences the later implementation prompts.
- `PROMPT_01_RELEASE_ARCHITECTURE_COMPLETION.md` records the architecture-phase
  outcome.
- `RUNTIME.md` documents the simulation-only Release Orchestrator runtime.
- `PROMPT_02_RELEASE_ORCHESTRATOR_COMPLETION.md` records the implementation
  outcome and qualification evidence.

The architecture consumes repository membership from
[`REPOSITORY_OWNERSHIP.md`](../../REPOSITORY_OWNERSHIP.md). It consumes
behavioural evidence from the Verification Platform and assurance evidence
from the Software Assurance Platform. It does not replace either system.

## Boundaries

This directory defines release architecture and future release-engineering
work. It does not contain release automation, repository version files,
release tags, publication configuration, credentials or product artifacts.

The Verification Runtime has its own independent product lifecycle. Its
compatibility evidence may be consumed by a platform release, but a runtime
release is not automatically a DJConnect platform release.
