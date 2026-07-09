# DJConnect Domain Model

This document defines the shared domain language for DJConnect. It bridges the Product Vision, Constitution and implementation work across all repositories.

When a feature needs persistent state, routing, identity, privacy, capabilities or cross-client behavior, use this document to decide where it belongs.

## Canonical flow

```text
Household
  -> Profile
    -> Device
    -> Music Backend / Music Account
      -> Playback Zone
        -> Intelligence Engine
          -> Insight Feed
            -> Renderer / Client
```

A simpler request-time view:

```text
Request
  -> resolve Profile
  -> resolve Music Backend
  -> resolve Music Account
  -> resolve Playback Target
  -> execute Use Case
  -> publish Insight / Response
  -> render on Client
```

## Household

A Household is the local DJConnect installation context. In the current platform, this is usually one Home Assistant instance.

A Household owns:

- profiles;
- device mappings;
- music backend configuration;
- shared rooms/zones;
- fallback profile behavior;
- local privacy defaults;
- export/import of non-secret household configuration.

A Household is not the same as a Home Assistant user account. Home Assistant users may be hints, but the Household is the DJConnect local platform boundary.

## Profile

A DJConnect Profile is the primary identity. It is the source of truth for personal or shared DJConnect state.

Profile types:

- `personal`
- `household`
- `room`
- `guest`
- `kids`
- `party`

A Profile owns:

- Music DNA;
- mood state;
- DJ voice tone and response style;
- Ask DJ conversation history;
- recommendation history;
- likes/dislikes;
- preferred music backend;
- preferred music account;
- fallback playback zone/player;
- privacy mode;
- feature flags and experimental settings;
- Personal/Community/Cloud entitlement state where applicable.

Multiple devices may link to the same Profile. When they do, personal state roams across those devices because it is profile-owned.

## Device

A Device is hardware, client, runtime and UI context.

Device-owned state:

- device ID;
- device name;
- device type / client type;
- platform;
- capabilities;
- linked profile ID;
- default room/player;
- microphone/speaker/display support;
- notification support;
- last seen;
- local pairing/runtime metadata.

A Device must not own persistent Music DNA, Ask DJ history, recommendation memory, profile mood or long-term DJ response style.

## Music Backend

A Music Backend is a provider adapter behind a normalized DJConnect interface.

Examples:

- Spotify Direct;
- Music Assistant;
- future Tidal Direct;
- future Qobuz Direct;
- future local/cloud music backends.

A Music Backend owns provider-specific playback, provider capabilities, credentials, queue behavior, library access and supported actions.

Core features should depend on normalized backend capabilities, not directly on Spotify or Music Assistant specifics.

## Music Account

A Music Account is a backend/provider account binding.

A Music Account may be:

- personal;
- shared;
- household-owned;
- linked to one profile;
- shared by multiple profiles.

Music accounts may reference provider identifiers, but OAuth tokens and secrets must not be exported by default.

## Playback Zone

A Playback Zone is the target where playback happens.

Examples:

- living room;
- kitchen;
- bedroom;
- headphones;
- active Spotify device;
- Music Assistant player/group.

Playback Zone ownership belongs to backend integration and household configuration. A profile may have a preferred or fallback zone.

## Intelligence Engine

The Intelligence Engine coordinates DJConnect intelligence.

It may use:

- current track metadata;
- backend capabilities;
- profile Music DNA;
- mood;
- listening context;
- lyrics;
- artist/album data;
- safe external knowledge sources;
- Home Assistant context where appropriate.

The Intelligence Engine publishes insight cards/events and Ask DJ responses. It must avoid leaking personal profile state to shared devices unless explicitly configured.

## Intelligence Provider

An Intelligence Provider generates a specific kind of insight.

Examples:

- Track Insight;
- Lyrics Explain;
- Artist Insight;
- Album Insight;
- Mood Insight;
- Recommendation Insight;
- Trivia Insight;
- Production Notes;
- Song Structure.

Providers publish normalized output to the Insight Feed instead of becoming standalone product silos.

## Insight Feed

The Insight Feed is the normalized stream of DJConnect intelligence.

It may contain:

- insight cards;
- structured text segments;
- images;
- sources;
- timed events;
- mood layers;
- recommendation cards;
- VibeCast layers;
- Ask DJ facts;
- guest-safe items.

Renderers decide how much of the feed to show based on capabilities, privacy mode, profile type and user settings.

## Renderer / Client

A Renderer or Client presents DJConnect capabilities.

Client classes:

- Intelligence Client: Apple, Windows, future Android/web;
- Ambient Client: Raspberry Pi / household display;
- Voice/Control Client: ESP32, HA Voice Assist satellites;
- Presentation Client: VibeCast / AirPlay / TV;
- Immersive Client: future VR/MR.

Clients render platform capabilities. They should not own durable intelligence or fork backend business logic.

## Capability

A Capability describes what a client, backend, profile or feature can do.

Examples:

- `ask_dj`
- `ask_dj_voice`
- `track_insight`
- `vibecast`
- `lyrics_live`
- `lyrics_explain`
- `music_discovery`
- `music_dna`
- `guest_companion`
- `profile_export`
- `background_audio`
- `notifications`

Capabilities should be explicit and detectable. Clients should not infer support by parsing versions when a capability contract exists.

## Feature Flag

A Feature Flag controls feature availability by maturity, audience, profile, client and/or deployment.

Feature maturity:

- experimental;
- preview;
- beta;
- stable;
- deprecated;
- removed.

Feature flags should be profile-aware where the experience is personal and device-aware where the feature depends on hardware/client capability.

## Session

A Session is a temporary activity context.

Examples:

- Ask DJ chat session;
- VibeCast session;
- guest companion session;
- on-the-go listening session;
- private session;
- party session.

Sessions may have tokens, TTLs, privacy rules and scoped state. They should expire predictably.

## Privacy modes

Profile or session privacy modes may include:

- normal;
- private;
- shared;
- guest-safe.

Private mode avoids persistence. Shared and guest-safe modes avoid personal Music DNA, private history and sensitive context.

## Ownership checklist

When adding a feature, ask:

1. Is this personal? Put it on Profile.
2. Is this hardware/client runtime? Put it on Device.
3. Is this provider playback behavior? Put it behind Music Backend.
4. Is this generated intelligence? Put it in the backend and publish through Insight Feed.
5. Is this presentation? Put it in a Renderer.
6. Is this temporary? Make it a Session with expiry.
7. Is this experimental? Put it behind Feature Flags.

## Implementation status

Epic 3 Phase 1 establishes the runtime-neutral core domain under
`custom_components/djconnect/domain/`.

The Phase 1 domain layer defines:

- Profile-owned personal state and references;
- Device-owned runtime state;
- Household-owned registrations and defaults;
- Music Backend registrations and capabilities;
- Music Account bindings;
- Playback Zone targets;
- one canonical Profile Resolver with the foundation-defined resolution priority.

Phase 1 intentionally does not implement persistence, config/options flow,
services, API/websocket changes, Ask DJ migration, Music DNA migration,
export/import or client changes.

Epic 3 Phase 2 adds durable Profile Platform storage through
`ProfilePlatformStorage` in `custom_components/djconnect/domain/storage.py`.
The storage schema persists Household, Profile, Device, Music Backend, Music
Account, Playback Zone, fallback and privacy-default state. OAuth tokens and
provider secrets remain outside profile/account metadata.

Phase 2 also wires the Home Assistant config/options flow to create and manage
the minimum Profile Platform state. It intentionally does not rewire services,
REST/websocket APIs, Ask DJ history, Music DNA, recommendations, export/import
or clients.
