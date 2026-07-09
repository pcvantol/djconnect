# DJConnect Platform Principles

These are the golden rules for DJConnect platform work. Use them before adding a feature, moving state, creating a new API contract or changing a sibling repository.

## Everything personal belongs to a DJConnect Profile

Personal preferences, Music DNA, Ask DJ history, recommendations, likes, privacy choices and entitlement state attach to a DJConnect Profile.

Example: A user's preferred DJ tone and recommendation history move with their DJConnect Profile across iPhone, Windows and Home Assistant.

Anti-example: Storing durable listening preferences only on one phone or one ESP32 device.

## Everything hardware/client/runtime-specific belongs to a Device

Hardware capabilities, firmware version, local URL, battery state, screen settings and runtime status belong to a Device.

Example: An ESP32 screen timeout is Device state.

Anti-example: Treating a device id as the owner of a user's Music DNA.

## Everything playback/provider-specific belongs behind a Music Backend

Provider APIs, provider account details, queue semantics, output selection and provider capabilities belong inside a Music Backend adapter.

Example: Spotify Direct and Music Assistant expose normalized Play Now actions through backend-aware contracts.

Anti-example: A client reconstructing Spotify-specific playback cards from old chat bubbles.

## Everything durable intelligence-related belongs to the backend

Durable recommendations, Music DNA, Ask DJ memory, Track Insight contracts and profile intelligence are backend-owned.

Example: The Home Assistant integration stores bounded Ask DJ history and serves it to all paired clients.

Anti-example: The Windows client building its own permanent Music DNA conclusions.

## Everything presentation-specific belongs to a Renderer/Client

Clients decide layout, platform interaction, animations, accessibility treatment and local presentation caches.

Example: Apple and Windows clients render the same backend-provided `playback_actions[]` with native controls.

Anti-example: The backend emitting client-specific screen layouts for every platform.

## Everything temporary belongs to a Session with expiry

Short-lived state such as follow-up confirmations, guest access, transient pairing context and temporary media URLs must expire.

Example: Ask DJ follow-up confirmation state expires after about 10 minutes.

Anti-example: Keeping a pending Yes/No action indefinitely in a client cache.

## Everything experimental belongs behind a Feature Flag

Preview, beta and experimental behavior must be explicitly gated and reversible.

Example: A future VibeCast Guest Companion preview is guarded by a feature flag before wider release.

Anti-example: Shipping an experimental insight feed as always-on behavior across all clients.

## Everything shared must be privacy-aware by default

Shared data must minimize personal detail, avoid secrets and respect profile boundaries.

Example: Diagnostics report whether a token is present, but never include token values, raw prompts, history or Music DNA dumps.

Anti-example: Including raw Ask DJ history or `bootstrap_proof` values in logs.

## Everything cross-repo starts from the canonical foundation

Cross-repository product, architecture, domain and governance decisions start in this repository's foundation docs.

Example: A new client capability class updates `CLIENT_CAPABILITY_MATRIX.md` and relevant ADRs before sibling repos implement divergent contracts.

Anti-example: A sibling repo redefining what a DJConnect Profile means in a local README.
