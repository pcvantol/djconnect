# ADR-0021 — Local Consumer API transport and authentication runtime

**Status:** Accepted for Phase 1 / Increment 2 architecture authorization
**Date:** 2026-08-30

## Context

ADR-0020 and Phase 1 / Increment 1 define the machine-readable Local Consumer
API v1 envelope, but deliberately add no transport or credential runtime. EP
must expose that contract without creating a second execution, provider,
storage, evidence or qualification authority. The existing Engineering Platform
remains the single canonical lifecycle and SQLite-writer authority.

## Decision

### Service and bind boundary

- Increment 2 will add one dedicated lightweight EP service process, managed by
  the existing per-user LaunchAgent tooling under the fixed label
  `com.djconnect.engineering-local-api`. It is independent of the watcher,
  dashboard relay and dashboard, so an API failure cannot interrupt Managed
  execution or make the dashboard unavailable.
- It will bind loopback-only to `127.0.0.1` (or the platform's exact IPv4
  loopback equivalent). Binding to `0.0.0.0`, LAN, Tailscale, public or other
  remote interfaces is not authorized.
- The EP-owned configuration key `local_consumer_api_port` has deterministic
  default `8766`. It accepts only integer ports `1024` through `65535` and
  rejects invalid configuration at service start; consumers cannot choose a
  bind address or port per request.
- The service will use Python's existing standard-library
  `ThreadingHTTPServer`/`BaseHTTPRequestHandler` pattern, not a new web
  framework. It serves JSON only: no templates, static files, proxying or
  generic routing.

### Surface, limits and health

- `GET /health` is unauthenticated and returns only bounded, non-secret
  liveness/readiness state, service identity and loaded contract version.
  Liveness means the API process can answer; readiness additionally requires
  the v1 contract, readable supported EP storage and initialized credential
  authority. It returns `NOT_READY` rather than inventing fallback state.
- `POST /v1/capabilities` is the sole authenticated Increment-2 endpoint. It
  accepts the existing v1 `"contract.foundation"` request envelope and returns
  a deterministic, read-only capability response. It never creates a run,
  prompt, queue action, retry, recovery, evidence, provider invocation,
  qualification record or PR.
- Other routes fail closed. `/v1/` is explicit contract routing; there is no
  unversioned consumer API surface.
- The future implementation enforces: 8192-byte request body; 16 KiB aggregate
  request headers; JSON nesting no deeper than the v1 envelope limit; 5-second
  header/read timeout; 15-second total request timeout; and at most 16 active
  request handlers. Oversize, malformed JSON and unsupported media types fail
  closed before application handling.

### Authentication, authorization and storage

- The only accepted credential carrier is `Authorization: Bearer <credential>`.
  Query, path, body and prompt carriers are rejected. Missing, malformed or
  invalid credentials map to HTTP `401` and `UNAUTHENTICATED`; a valid
  credential not authorized for the exact supplied `project_id` maps to HTTP
  `403` and `PROJECT_NOT_AUTHORIZED`. Neither outcome reveals another project.
- A credential resolves one canonical `consumer_id` plus exact authorized
  `project_id` scope; neither identity is inferred from IP address, user agent,
  labels, repository names, paths or prompt text.
- Credentials are high-entropy opaque bearer values. Future issuance generates
  at least 256 bits with `secrets.token_urlsafe(32)`. Verification uses
  `SHA-256("engineering-platform.local-api.verifier.v1\\0" || credential)`
  and `hmac.compare_digest`; its distinct deterministic fingerprint uses
  `SHA-256("engineering-platform.local-api.fingerprint.v1\\0" || credential)`.
  Domain separation prevents accidental reuse of either digest. A password KDF
  is not justified for an unguessable 256-bit bearer value.
- Increment 2 authorizes the smallest durable EP-owned storage migration,
  schema `39`, because authentication must survive the independently restarted
  service. It creates `local_api_credentials` with `credential_id`,
  `consumer_id`, `project_id`, binary `verifier`, binary `fingerprint`,
  `issued_at`, nullable `expires_at`, nullable `revoked_at` and nullable
  `replaced_by_credential_id`; unique indexes cover verifier and fingerprint,
  and an authorization index covers `(consumer_id, project_id, revoked_at)`.
  It contains no plaintext credential, no consumer-owned database and no
  prompt/evidence data. The existing controlled storage-activation workflow
  remains mandatory.
- Increment 2 implements verifier lookup, constant-time comparison,
  authorization middleware and a test-only in-memory credential fixture. It
  does not implement operator issuance, registration, rotation/revocation
  workflows or consumer Keychain use. Production with no active credential is
  still service-ready but rejects authenticated calls; it never falls back to
  anonymous access. Increment 3 owns those operator and consumer workflows.

### Isolation, observability and operation

- API requests use existing EP storage/service boundaries only. They do not
  acquire independent SQLite writer or lifecycle ownership, spawn an execution
  engine, initialize providers/provider context, or affect Managed execution
  telemetry and qualification.
- A pre-logging sanitizer discards raw headers and request bodies. Bounded API
  telemetry may retain method, versioned route, status class, duration,
  request ID and, after success, consumer/project identifiers. It never retains
  credentials, authorization headers, prompt text or secret-bearing values.
- The desired-state verifier and doctor gain a Local Consumer API row covering
  its LaunchAgent, loopback health endpoint and readiness. The service restarts
  through the existing owned LaunchAgent mechanism. A crash remains isolated
  from active Managed execution, watcher, provider children and dashboard.
- A clean normal Managed E2E is required after Increment-2 merge, controlled
  storage activation where needed and service restart. It proves non-
  interference only; it does not consume the new API.

## Consequences

The later Increment-2 implementation is narrow and independently operable,
while retaining the existing EP runtime as the sole authority. It can prove
loopback HTTP, credential verification and project authorization before any
consumer is cut over. Persistent credential metadata is intentionally limited
to verifier material; the only plaintext handoff and all consumer secret-store
integration remain Increment 3 work.

## Alternatives considered

1. **Host the API in the dashboard process.** Rejected: dashboard availability
   and consumer transport would share a failure/restart boundary.
2. **Use a temporary production credential.** Rejected: it would make durable
   authentication ambiguous and violate the no-plaintext policy.
3. **Use a password KDF for bearer verification.** Rejected: the specified
   bearer credentials are high entropy; domain-separated SHA-256 with
   constant-time comparison is appropriate and avoids unnecessary request cost.
4. **Defer all storage until Increment 3.** Rejected: an independently
   restartable production authentication runtime needs durable verifier state.

## Affected repositories

- `pcvantol/djconnect` until the later history-preserving EP extraction
- future `pcvantol/engineering-platform`
- future Forge/Workspace and DJConnect consumer adapters (not yet cut over)

## Related documents

- [ADR-0019](0019-engineering-platform-central-installation-store.md)
- [ADR-0020](0020-local-consumer-api-contract-and-credential-authority.md)
- [EP consumer contract](../development/ENGINEERING_PLATFORM_CONSUMER_CONTRACT.md)
- [EP extraction and migration plan](../development/ENGINEERING_PLATFORM_EXTRACTION_MIGRATION_PLAN.md)
