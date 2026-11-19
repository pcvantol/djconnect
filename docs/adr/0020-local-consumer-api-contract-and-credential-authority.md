# ADR-0020 — Local Consumer API contract and credential authority

**Status:** Accepted for Phase 1 / Increment 1  
**Date:** 2026-08-30

## Context

Engineering Platform 2.x must become an independently installed, local-first
Execution Operations Platform without allowing consumers to depend on Python
internals, repository paths, EP storage or lifecycle authority. ADR-0019
already establishes installation ownership and canonical `project_id` scope.
The remaining boundary decisions are the public consumer contract, its eventual
transport, and the authority and storage rules for consumer authentication.

## Decision

- The canonical Local Consumer API is **HTTP with versioned JSON contracts**.
  Contract identity is independent of bind or exposure policy. Runtime exposure
  defaults fail-closed and configuration-controlled; a later implementation may
  begin loopback-only.
- Unix-domain sockets are not the canonical public consumer contract. They may
  later be an internal or optional local transport only if they preserve the
  same versioned JSON contract. Consumers must not use a socket path as API
  identity.
- EP owns credential issuance, credential identity/fingerprint, validation,
  revocation, rotation and metadata. Each registered consumer/project
  relationship receives one opaque cryptographically random bearer credential,
  scoped to its consumer identity and canonical `project_id`.
- EP never persists reusable plaintext bearer credentials after issuance. A
  later authentication runtime persists only a bounded verifier/fingerprint and
  metadata required for validation. Credentials never enter logs, reports,
  Prompt History or dashboard projections.
- A consumer stores its credential in its OS-native secret store; on macOS this
  is Apple Keychain. Repository files, committed environment files, consumer
  SQLite, Prompt History and Engineering Reports are prohibited storage.
- `project_id` is the authorization scope. A mutable project label is display
  metadata and cannot authorize a request.
- Phase 1 / Increment 1 — **Local Consumer API Contract Foundation** is
  contract-only. It authorizes schemas, validation, normalization, stable
  errors and safe rendering, but no live transport, credential runtime,
  Keychain integration, consumer cutover or storage migration.

## Consequences

Future consumers can integrate through a language-neutral, testable API while
EP retains execution and credential authority. A request must carry explicit
version, project scope and consumer/authentication envelope information; an
unknown or incompatible contract fails closed. Consumer-provided prompt text
cannot grant itself authorization or modify credential policy.

The initial contract defines deterministic Unicode and newline normalization,
empty/null handling, bounded identifiers and stable serialization. It rejects
malformed input rather than repairing it silently. Stable machine-readable
errors are non-secret-bearing and never expose authorization headers, bearer
values, provider secrets, stack traces or internal database content.

## Alternatives considered

1. **Unix-domain socket as public API.** Rejected: it couples consumers to a
   filesystem implementation detail and is not the portable public boundary.
2. **OAuth, mTLS or external identity infrastructure in Phase 1.** Rejected:
   it broadens a local contract foundation beyond the required bounded scope.
3. **Consumer-owned credentials or direct EP SQLite access.** Rejected: both
   violate EP authority and create competing ownership of security or lifecycle
   state.

## Affected repositories

- `pcvantol/engineering-platform` (future Local Consumer API and credential
  authority runtime)
- `pcvantol/djconnect` (future thin consumer adapter only)
- Forge/Workspace (future scoped consumers using native secret storage)

## Related documents

- [ADR-0019](0019-engineering-platform-central-installation-store.md)
- [EP extraction and migration plan](../development/ENGINEERING_PLATFORM_EXTRACTION_MIGRATION_PLAN.md)
- [EP consumer contract](../development/ENGINEERING_PLATFORM_CONSUMER_CONTRACT.md)
