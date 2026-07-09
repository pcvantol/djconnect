# DJConnect Architecture Principles

These principles describe where responsibilities live in the DJConnect platform.

## Canonical model

```text
Device
  -> DJConnect Profile
    -> Music Backend / Music Account
      -> Intelligence Engine
        -> Insight Feed
          -> Renderer / Client
```

## Primary domain concepts

### Profile

A Profile is the source of truth for personal DJConnect state:

- Music DNA;
- mood state;
- DJ voice tone;
- response style;
- Ask DJ conversation history;
- recommendation history;
- likes/dislikes;
- preferred music backend;
- preferred music account;
- fallback playback zone/player;
- privacy mode;
- tier/capabilities.

Multiple devices may link to the same profile.

### Device

A Device represents hardware, client, runtime, and UI context:

- device ID;
- device name;
- device type;
- default room/player;
- capabilities;
- linked profile ID;
- last seen state;
- notification settings;
- microphone/speaker/display constraints.

A Device does not own Music DNA, persistent mood, response style, or long-term conversation history.

### Music Backend

A Music Backend adapter owns playback/provider-specific behavior:

- Spotify Direct;
- Music Assistant;
- future Tidal Direct;
- future Qobuz Direct;
- future local or cloud providers.

A backend exposes normalized capabilities and provider-specific operations through an adapter boundary.

### Music Account

A Music Account is a provider/backend account binding.

Profiles may have one default music account, and multiple profiles may share the same account.

Do not require every profile to have a unique provider account.

### Insight Feed

The Insight Feed is the normalized stream of DJConnect intelligence events and cards.

Renderers consume this feed according to capabilities.

## Profile resolution

All intents, services, API endpoints, and client calls should resolve profile context through one central resolver.

Resolution priority:

1. explicit `profile_id` from DJConnect client/request;
2. linked profile for `device_id`;
3. mapped Home Assistant `user_id` hint if available;
4. room/satellite mapping;
5. configured fallback profile;
6. clear `profile_required` error.

Home Assistant `user_id` is useful but not authoritative. Voice satellites should normally resolve by device/room/fallback, not by speaker identity.

## Backend resolution

After resolving `profile_id`:

1. load the profile;
2. resolve default backend;
3. resolve default music account;
4. resolve playback target/player/zone;
5. execute through the selected backend adapter.

Playback, Ask DJ, Track Insight, recommendations, mood changes, VibeCast, and DJ responses should all accept or resolve profile context before acting.

## Intelligence ownership

Persistent intelligence belongs in the backend/integration layer.

Clients may:

- render insight cards;
- show local UI state;
- cache short-lived presentation data;
- provide user input;
- display platform capabilities.

Clients should not:

- own Music DNA;
- own persistent recommendation state;
- own canonical Ask DJ memory;
- implement backend-specific business logic;
- fork the product model per platform.

## Client capability classes

### Intelligence clients

Examples: Apple apps, Windows client, future Android/web.

Capabilities may include Ask DJ, Music DNA, Track Insight, Discover, VibeCast control, profile settings, notifications, and rich insight rendering.

### Ambient clients

Examples: Pi wall display, household screen.

Capabilities may include now playing, light insights, Discover feed, read-only Ask DJ stream, playback controls, and household context.

### Voice/control clients

Examples: ESP32, firmware remotes, HA Voice Assist satellites.

Capabilities may include intents, push-to-talk, playback controls, and short TTS DJ response playback.

### Presentation clients

Examples: VibeCast/AirPlay/TV renderers.

Capabilities may include artwork, lyrics, insight layers, mood visuals, artist/album context, and guest-facing visuals.

## Repository responsibilities

### `pcvantol/djconnect`

Home Assistant integration, local platform core, music backend abstraction, profile resolution, intelligence orchestration, services, websocket/API endpoints, local storage, and source-of-truth documentation.

### `pcvantol/djconnect-api`

Central API, APNs relay, install/device trust, future entitlement boundary, future cloud profile capabilities. It should not become the primary local intelligence source.

### `pcvantol/djconnect-app`

Apple first-party intelligence client and renderer.

### `pcvantol/djconnect-windows`

Windows first-party intelligence client and renderer.

### `pcvantol/djconnect-pi`

Community household display / ambient client.

### `pcvantol/djconnect-esp32` and `pcvantol/djconnect-firmware`

Community firmware/control clients focused on physical controls, lightweight voice/TTS, device identity, and reliable local interaction.

### Release repositories

Release repositories publish artifacts, binaries, release notes, and community deliverables. They should be treated as distribution surfaces, not product-logic owners.

### `pcvantol/djconnect-website`

Product story, onboarding, community/personal positioning, documentation entry points, and public communication.

## CI/CD and quality principles

DJConnect is a multi-repository platform. CI/CD should protect the platform, not only individual repositories.

Recommended platform-wide checks:

- linting and formatting per language;
- unit tests for core logic;
- profile/backend resolver tests;
- typed API contract validation where possible;
- release artifact integrity checks;
- dependency/security scanning;
- secret scanning;
- release notes consistency;
- privacy regression checks for exports, logs, and guest surfaces;
- branch protection and PR review before `main`.

## Security and privacy principles

- Do not export OAuth tokens/secrets by default.
- Do not expose personal profile data on shared devices by default.
- Guest endpoints must be temporary, scoped, and read-only unless explicitly designed otherwise.
- Local unauthenticated endpoints must use scoped tokens and predictable expiry.
- Logs should avoid tokens, secrets, raw personal chat history, and private Music DNA details.

## Change management

Large architecture changes should be split into:

1. domain model/storage;
2. resolver;
3. backend routing;
4. services/API;
5. config/options flow;
6. client rendering;
7. docs and website updates;
8. tests and release notes.

Avoid one giant implementation PR when the change alters platform concepts.
