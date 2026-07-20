# ADR-0002: Music backends are adapters

## Status

Accepted

## Context

DJConnect started with strong Spotify Direct assumptions. Music Assistant support and future provider ambitions require a cleaner model.

The product vision is not “Spotify with AI”. DJConnect should enrich music playback regardless of whether playback comes from Spotify Direct, Music Assistant or future providers such as Tidal, Qobuz or local music sources.

## Decision

Music providers are represented as Music Backend adapters behind a normalized DJConnect use-case layer.

Spotify Direct, Music Assistant and future providers must not define the core product model.

Core product features such as Ask DJ, Insights, VibeCast, Discover and Music DNA should depend on normalized backend capabilities and current playback context.

Provider-specific logic belongs inside backend adapters.

## Consequences

- Spotify-specific code should not leak into core intelligence or client contracts.
- Clients should render backend-owned payloads rather than reconstruct provider-specific cards.
- Backend capability flags are required for graceful degradation.
- Music Assistant support should not become a full Music Assistant clone inside DJConnect.
- Future providers can be added by implementing adapters and capability mappings.
- For Continue Current Playback Continuity, adapters translate provider state
  into the canonical safe projection, own Playback Instance Identity and
  normalize Track Started observations without exposing raw payloads to Runtime;
  see `docs/product/CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`.

## Alternatives considered

### Spotify-first core

Rejected. It blocks backend agnosticism and weakens the platform story.

### Music Assistant as the only abstraction

Rejected. DJConnect should support Music Assistant, but not become only a Music Assistant frontend.

### Client-side provider logic

Rejected. It would fragment behavior across clients and violate backend-owned intelligence.

## Affected repositories

- `pcvantol/djconnect`
- all clients consuming backend contracts
- website/product docs

## Related documents

- `DJCONNECT_CONSTITUTION.md`
- `ARCHITECTURE_PRINCIPLES.md`
- `DOMAIN_MODEL.md`
- `SYNC_PROMPTS.md`
