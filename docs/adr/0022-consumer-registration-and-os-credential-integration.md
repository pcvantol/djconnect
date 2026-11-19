# ADR-0022 — Consumer registration and OS credential integration

**Status:** Implemented and qualified (Phase 1 / Increment 3)
**Date:** 2026-08-31

## Context

ADR-0020 defines the Local Consumer API identity and credential-authority
boundary. ADR-0021 implements and qualifies its loopback-only bearer verifier
path, including schema-39 verifier metadata, without a production registration,
issuance or native-secret-store workflow. Increment 2a is deliberately limited
to one short-lived qualification credential and is not a production lifecycle.

Real consumers need an explicit, auditable relationship to an exact project,
one-time credential delivery, safe rotation and a native macOS secret store.
This must not create an execution endpoint, a second authentication path or a
consumer-owned credential authority.

## Decision

### Ownership and identity

- Engineering Platform (EP) owns consumer registration, production credential
  issuance, verifier/fingerprint persistence, credential identifiers, exact
  `project_id` authorization, rotation, revocation and authentication.
- A `consumer_id` is an immutable, lower-case canonical identifier matching
  the existing v1 identifier grammar. It identifies a logical consumer, never
  a label, IP address, user agent, prompt, path or individual secret.
- A registration is the explicit pair `(consumer_id, project_id)`. It is a
  separate authority record from a credential; wildcard project scope is not
  authorized.
- Workspace supplies canonical project identity and mutable display/checkout
  metadata. It may coordinate a local consumer bootstrap, but never owns the
  EP verifier database or authorization decision. Forge and DJConnect remain
  unmodified consumers in this increment.

### Registration and credential lifecycle

- Registrations have `ACTIVE`, `DISABLED` and `REVOKED` status. Re-registering
  an identical active pair is idempotent. Disable is idempotent and makes every
  credential of that registration fail authorization without deleting its
  non-secret evidence; a revoked registration is not re-enabled.
- Production credentials have purpose `PRODUCTION_CONSUMER`; Increment-2a
  `QUALIFICATION` credentials retain their separate namespace and policy.
- A production credential is issued only for an active registration. EP
  generates an opaque high-entropy bearer, persists only the existing
  domain-separated verifier and fingerprint plus bounded metadata, and shows
  plaintext exactly once to the invoking operator. EP cannot retrieve it later.
- One registration may have a bounded maximum of two active production
  credentials. This permits a single replacement during rotation or a
  new-machine transition, while preventing unbounded accumulation. The exact
  limit is enforced by the future implementation.
- Revocation is idempotent, immediate for authentication, and retains only
  bounded non-secret audit metadata. A revoked bearer is never reactivated or
  reused. Increment 3 permits no production hard-delete; test cleanup may use
  isolated test storage only.
- Rotation is fail-safe: issue replacement, write it to the consumer secret
  store, verify it through the existing API path, then revoke the old
  credential. If storage or verification fails, the old credential remains
  active. A lost secret is unrecoverable: issue a replacement and revoke the
  old credential. A new Mac receives a new credential; no secret is synced
  through repository files. Logical consumer identity remains stable unless a
  later consumer contract explicitly requires installation identities.

### Storage and operator surface

- Schema 39 is sufficient only for credential verifier records. Schema 40 is
  required for the separate EP-owned `local_api_consumer_registrations` table:
  canonical `consumer_id`, exact `project_id`, status, `created_at`,
  `updated_at`, nullable `disabled_at`, nullable `revoked_at`, and bounded
  non-secret operator/audit metadata. It has a unique `(consumer_id,
  project_id)` key. No plaintext secret or consumer-owned state is stored.
- Schema 40 was activated through the existing controlled storage safety gates,
  never during ordinary storage open.
- The bounded operator CLI will provide `consumer-register`, `consumer-status`,
  `consumer-disable`, `credential-issue`, `credential-status`,
  `credential-revoke` and `credential-rotate`. Create/revoke/disable retries
  return stable idempotent results. Status and audit output contain identifiers,
  scope, state and timestamps only; never bearer plaintext.

### macOS secret-store boundary

- Apple Keychain is the canonical macOS consumer secret store. The service is
  `Engineering Platform Local Consumer API`; the account is
  `<consumer_id>:<project_id>`. A consumer-side credential-provider abstraction
  supplies `get_credential(consumer_id, project_id)`; raw Keychain commands do
  not spread through consumer code.
- The consumer-side bootstrap tool writes, reads, replaces and deletes its own
  Keychain item in the current macOS user context. The Local API service never
  reads that plaintext. If Workspace coordinates bootstrap, it acts only as
  that consumer-side secret-store client.
- Keychain unavailable, denied, missing or conflicting-item states fail closed
  with actionable operator guidance. There is no file, environment-variable or
  repository fallback. Diagnostics report only present/missing and safe scope
  metadata; normal commands never print a retrieved secret.

### Runtime and operational boundaries

- Production credentials use exactly the ADR-0021 path: `Authorization:
  Bearer` → verifier/fingerprint lookup → consumer identity → exact project
  authorization → v1 endpoint. No magic header, debug bypass or secondary
  verifier is authorized.
- Local API remains loopback-only and read-only. Increment 3 authorizes no
  endpoint that creates Engineering runs and no Forge, Workspace or DJConnect
  cutover.
- Server doctor verifies credential authority and registration storage, but
  never treats an individual consumer Keychain item as server readiness.
  Consumer bootstrap diagnostics may separately report credential present or
  missing.
- Lifecycle events record only bounded action, credential ID/fingerprint,
  consumer/project scope, timestamp and safe operator identity where available.
  Plaintext is prohibited from logs, errors, reports, Prompt History,
  dashboard, doctor, shell output beyond one-time issuance and generated
  scripts. Prompts have no authority to perform registration, credential or
  Keychain operations.

## Consequences

Increment 3 implementation may add the schema-40 registration migration,
bounded operator lifecycle commands and macOS Keychain provider, while reusing
the qualified bearer runtime. Required coverage includes registration,
issuance, Keychain abstraction, authentication, rotation, revocation,
redaction, prompt safety, zero Engineering-execution side effects, migration,
doctor and extraction regressions. Post-merge qualification creates one
production-style test registration, stores and rotates a Keychain credential,
proves new/old authentication behavior, cleans it up and then proves a clean
Managed E2E remains qualified.

## Alternatives considered

1. **Reuse schema 39 for registrations.** Rejected: verifier rows cannot
   represent registration status or its independent lifecycle without coupling
   identity authority to individual secrets.
2. **Immediate replacement without overlap.** Rejected: a Keychain write or
   verification failure could lock a consumer out.
3. **File or environment fallback when Keychain fails.** Rejected: it creates
   plaintext persistence outside the approved OS secret store.
4. **Consumer-owned verifier storage or direct SQLite access.** Rejected: it
   violates EP authority and creates divergent authorization state.

## Related documents

- [ADR-0020](0020-local-consumer-api-contract-and-credential-authority.md)
- [ADR-0021](0021-local-consumer-api-transport-and-authentication-runtime.md)
- [EP consumer contract](../development/ENGINEERING_PLATFORM_CONSUMER_CONTRACT.md)
- [EP extraction and migration plan](../development/ENGINEERING_PLATFORM_EXTRACTION_MIGRATION_PLAN.md)
