# DJConnect Architecture Decision Records

This index tracks architecture decisions that should remain understandable over time.

ADRs should be added under `docs/adr/` when a decision affects product identity, domain ownership, repository boundaries, privacy, release strategy or cross-repo contracts.

## ADR format

Each ADR should include:

- title;
- status;
- date;
- context;
- decision;
- consequences;
- alternatives considered;
- affected repositories;
- related foundation documents.

## Accepted ADRs

### ADR-0000 — Why DJConnect exists

**Status:** Accepted
**File:** `docs/adr/0000-why-djconnect-exists.md`

Decision to define DJConnect as an AI music platform centered on an AI DJ experience, with Home Assistant as the first local-first runtime, Music Backends as adapters, clients as renderers/control surfaces and DJConnect Profiles as personalization boundaries.

### ADR-0001 — DJConnect Profile is the primary identity

**Status:** Accepted
**File:** `docs/adr/0001-profile-is-primary-identity.md`

Decision to place personal state on DJConnect Profile instead of Device, Spotify account or Home Assistant user.

### ADR-0002 — Music backends are adapters

**Status:** Accepted  
**File:** `docs/adr/0002-music-backends-are-adapters.md`

Decision to keep Spotify Direct, Music Assistant and future providers behind a backend abstraction.

### ADR-0003 — Backend owns intelligence

**Status:** Accepted  
**File:** `docs/adr/0003-backend-owns-intelligence.md`

Decision that durable intelligence, Music DNA, recommendations and Ask DJ memory live in the backend rather than clients.

### ADR-0011 — Profile resolution uses Request Context

**Status:** Accepted
**File:** `docs/adr/0011-profile-resolution-uses-request-context.md`

Decision to keep one canonical Profile Resolver and resolve DJConnect Profiles
from a general Request Context instead of assuming every interaction originates
from a DJConnect Device.

### ADR-0012 — DJConnect supports one canonical five-language product set

**Status:** Accepted
**File:** `docs/adr/0012-canonical-five-language-product-set.md`

Decision that DJConnect's user-facing product surfaces support one canonical
language set, `en`, `nl`, `de`, `fr` and `es`, with English fallback,
machine-readable values left untranslated and CI validation for key and
placeholder parity where practical.

### ADR-0014 — DJ Session Runtime is the v4 active-session boundary

**Status:** Accepted
**File:** `docs/adr/0014-dj-session-runtime-boundary.md`

Decision to separate persistent Profile ownership from the server-owned,
ephemeral DJ Session Runtime and to place active session orchestration there.

### ADR-0015 — VibeCast is a Broadcast Capability

**Status:** Accepted
**File:** `docs/adr/0015-vibecast-broadcast-capability.md`

Decision to define VibeCast as an event-driven broadcast capability of an
active DJ Session, rendered locally by a Universal Session Receiver.

### ADR-0016 — Playback Instance Identity belongs to the Music Backend Observation Boundary

**Status:** Accepted
**File:** `docs/adr/0016-playback-instance-identity-observation-boundary.md`

Decision to separate Playback Control from Playback Observation and place
Playback Instance Identity, Current Playback Projection and normalized Track
Started observation in the Music Backend Observation Boundary. Runtime consumes
only an opaque, ephemeral identity.

### ADR-0017 — ESPHome is the preferred firmware platform for supported DJConnect ESP hardware

**Status:** Accepted
**File:** `docs/adr/0017-esphome-firmware-platform.md`

Decision to use a pinned, qualified community ESPHome hardware baseline as the
preferred firmware foundation for supported ESP boards while retaining existing
DJConnect contracts and the source/distribution repository boundary.

### ADR-0018 — Platform Device Distribution and Provisioning

**Status:** Accepted
**File:** `docs/adr/0018-platform-device-distribution-and-provisioning.md`

Decision to use one standalone, product-first Device Installer and one
artifact-truth repository for ESP, RP2 and Raspberry Pi device distribution.

### ADR-0019 — Engineering Platform uses one central installation store

**Status:** Accepted for Engineering Platform 2.x extraction
**File:** `docs/adr/0019-engineering-platform-central-installation-store.md`

Decision to install EP once per local user/machine, use one central
installation-owned database, and scope all EP operational data by the canonical
Workspace project ID.

### ADR-0020 — Local Consumer API contract and credential authority

**Status:** Accepted for Phase 1 / Increment 1
**File:** `docs/adr/0020-local-consumer-api-contract-and-credential-authority.md`

Decision that HTTP with versioned JSON is the public Local Consumer API
contract; EP owns opaque per-consumer/project bearer credentials; consumers use
native secret storage; and the initial increment is contract-only.

### ADR-0021 — Local Consumer API transport and authentication runtime

**Status:** Accepted for Phase 1 / Increment 2 architecture authorization
**File:** `docs/adr/0021-local-consumer-api-transport-and-authentication-runtime.md`

Decision to use a dedicated loopback-only EP Local Consumer API LaunchAgent,
the v1 `/health` and read-only `/v1/capabilities` boundary, durable
domain-separated verifier metadata in EP storage schema 39, and a strict split
between Increment-2 authentication runtime and Increment-3 issuance/Keychain
work.

### ADR-0022 — Consumer registration and OS credential integration

**Status:** Accepted for Phase 1 / Increment 3 architecture authorization
**File:** `docs/adr/0022-consumer-registration-and-os-credential-integration.md`

Decision to add explicit EP-owned consumer/project registration, production
credential lifecycle and macOS Keychain-backed consumer storage in a future
Increment 3 implementation. It requires schema 40 for registrations, reuses
the qualified schema-39 verifier path, and authorizes neither Local API
mutation nor consumer cutover.

### ADR-0023 — EP central-store migration guardrails

**Status:** Accepted for Phase 2 / Increment 1 control contract
**File:** `docs/adr/0023-ep-central-store-migration-guardrails.md`

Decision to define one portable installation data-root/store contract and
fail-closed future central-store migration controls without moving the current
schema-40 sole authority.

### ADR-0024 — EP controlled central-store cutover

**Status:** Accepted for Phase 2 / Increment 3 architecture authorization; not implemented
**File:** `docs/adr/0024-ep-controlled-central-store-cutover.md`

Decision to authorize a durable-freeze, one-writer, schema-40 cutover to the
installation-owned central store, with direct legacy rollback only before the
first central production write.

### ADR-0025 — EP control provenance and baseline-delta recovery

**Status:** Accepted for architecture authorization; not implemented
**File:** `docs/adr/0025-ep-control-provenance-and-baseline-delta-recovery.md`

Decision to add future immutable provenance for authority-independent controls,
while allowing the current contaminated pre-write incident to use exact
baseline-delta comparison and fail closed on every unexplained delta.

## ADR backlog

### ADR-0013 — Platform Baseline v1.0 certification boundary

**Status:** Planned

Decision to formalize how Platform Baseline certification decisions are made,
which evidence is mandatory, and how non-certification keeps the platform in
Platform Qualification before Business-first Engineering.

### ADR-0004 — Community and Personal tier model

**Status:** Planned

Decision that Community should feel complete and Personal adds profile-level personalization.

### ADR-0005 — Insight Feed as shared intelligence contract

**Status:** Planned

Decision to unify Track Insight, Lyrics Explain, Artist/Album Insight, Discover and VibeCast around a shared backend-owned feed model.

### ADR-0006 — Client capability classes

**Status:** Planned

Decision to classify clients as Intelligence, Ambient, Voice/Control, Presentation and Immersive clients.

### ADR-0007 — Central API as trust/relay boundary

**Status:** Planned

Decision that `api.djconnect.dev` starts as APNs/trust relay and future entitlement boundary, not as the primary local intelligence source.

### ADR-0008 — Release repositories are distribution surfaces

**Status:** Planned

Decision that release repos publish artifacts and notes but do not own product logic.

### ADR-0009 — Feature flags and experimental maturity

**Status:** Planned

Decision to manage experimental, preview, beta, stable and deprecated capabilities explicitly.

### ADR-0010 — Guest-facing endpoints are temporary and scoped

**Status:** Planned

Decision for VibeCast Guest Companion and similar features to use scoped temporary tokens, no personal data and automatic expiry.

## Creating a new ADR

1. Add a file under `docs/adr/NNNN-short-title.md`.
2. Update this index.
3. Link related roadmap or Innovation Lab items.
4. Update `ARCHITECTURE_PRINCIPLES.md` if the decision changes platform rules.
