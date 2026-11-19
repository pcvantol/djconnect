# DJConnect Implementation Guidelines

These are platform-wide implementation rules for future DJConnect epics.

The foundation documents remain authoritative. Runtime code, tests and repository-local docs must conform to the foundation rather than silently redefining it.

## Clean Codex Sessions

Clean Codex or AI-agent sessions must start with
`BOOTSTRAP_CODEX_SESSION.md`.

The required startup order is:

1. read `BOOTSTRAP_CODEX_SESSION.md`;
2. read the local repository `AGENTS.md`;
3. read the current epic context;
4. read the active phase or implementation prompt.

After bootstrap, return a readiness summary and wait. Do not start
implementation until the user provides the next phase or implementation prompt.

## Core rules

- Always read the Foundation first.
- Prefer many small commits.
- Prefer many small PRs.
- Every phase must compile.
- Every phase must remain independently mergeable.
- Runtime changes must stay inside scope.
- Architecture comes before implementation.
- Do not duplicate contracts.
- Do not duplicate business logic.
- Backend owns intelligence.
- DJConnect Profiles own personal state.
- Devices own hardware, client and runtime state.
- Music Backends own playback/provider state.
- Clients own rendering, local UI affordances and control surfaces.
- Update documentation together with implementation.
- Never let code become the product specification.
- Use ADRs for decisions that change product identity, domain ownership, repository boundaries, privacy, release strategy or cross-repo contracts.

## Foundation first

Before implementation, read:

- `FOUNDATION_INDEX.md`
- `DJCONNECT_CONSTITUTION.md`
- `PRODUCT_VISION.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `DOMAIN_MODEL.md`
- `PLATFORM_PRINCIPLES.md`
- relevant ADRs under `docs/adr/`
- relevant discovery reports under `docs/discovery/`

## Phase discipline

Large changes must be split by architecture layer when possible:

1. domain model or storage;
2. resolver/use-case layer;
3. backend adapter or runtime behavior;
4. API/service/websocket contract;
5. client rendering;
6. migrations;
7. tests;
8. docs and release notes.

Every phase should be reviewable without requiring the whole Epic to be complete.

## Runtime scope

Runtime changes should do only what the phase requires.

Avoid:

- unrelated refactors;
- opportunistic UI redesign;
- new feature work outside the phase;
- cross-repo contract changes without foundation alignment;
- client-local business logic that belongs in the backend.

## Contract ownership

Contracts should be defined once and consumed consistently.

Use:

- canonical API docs;
- exported client fixtures;
- websocket capability declarations;
- typed client models;
- compatibility tests.

Do not let one client invent a private product contract that other clients must reverse-engineer later.

## Documentation

Documentation is part of implementation.

Update docs when implementation changes:

- user-facing behavior;
- API contracts;
- domain ownership;
- repository responsibilities;
- release process;
- privacy/security behavior;
- migration expectations.

## Review posture

Every phase review should ask whether the change strengthens the AI DJ experience and keeps the platform simpler as capabilities grow.

When in doubt, prefer the foundation over current implementation convenience.
