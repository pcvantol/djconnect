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

## Initial ADR backlog

### ADR-0001 — DJConnect Profile is the primary identity

**Status:** Planned

Decision to place personal state on DJConnect Profile instead of Device, Spotify account or Home Assistant user.

### ADR-0002 — Music backends are adapters

**Status:** Planned

Decision to keep Spotify Direct, Music Assistant and future providers behind a backend abstraction.

### ADR-0003 — Backend owns intelligence

**Status:** Planned

Decision that durable intelligence, Music DNA, recommendations and Ask DJ memory live in the backend rather than clients.

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
