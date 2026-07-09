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
Interaction / Request
  -> Request Context
  -> Profile Resolver
  -> DJConnect Profile
  -> Music Backend / Music Account
  -> Playback Zone
  -> Use Case / Intelligence
  -> Client or Renderer
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

## Request Context

A Request Context describes where and how a DJConnect interaction originated.
The current implementation names this typed input `ProfileResolutionContext`.

A Request Context may contain:

- `explicit_profile_id`;
- `device_id`;
- `client_type`;
- `ha_user_id`;
- `satellite_id`;
- `ha_device_id`;
- `area_id`;
- `room_id`;
- `player_id`;
- `playback_zone_id`;
- `session_id`;
- request source/type;
- future `speaker_identity_hint`.

Request Context is temporary resolver input. It is not an identity by itself,
not durable personal state and not a replacement for Profile. It exists so the
Profile Resolver can deterministically select the correct DJConnect Profile
before personal state, backend routing or intelligence behavior is used.

Not every interaction source is a registered DJConnect Device. Apple, Windows,
Raspberry Pi and ESP32 clients are commonly registered devices. Home Assistant
Voice Assist satellites, automations, service calls, Home Assistant user
context, room/area context, playback players and future speaker recognition may
all provide resolver signals without becoming Device-owned identity.

## Device

A Device is hardware, client, runtime and UI context.

A DJConnect Device is a paired or registered DJConnect client or hardware
runtime. Examples:

- Apple app installation;
- Windows app installation;
- Raspberry Pi client;
- ESP32 client.

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

## Home Assistant Voice Satellite

A Home Assistant Voice Satellite is a Home Assistant voice endpoint that invokes
DJConnect through Assist.

It may be represented by:

- Home Assistant device ID;
- satellite/entity ID;
- area/room association;
- Assist pipeline context.

An HA Voice Satellite is a request source and resolution signal. It does not
need to become a full DJConnect Device solely to resolve a Profile. Registering
it as a DJConnect Device is appropriate only when registration creates real
product value, such as runtime capability tracking, device settings, pairing or
release/update ownership.

Shared room-based satellites should normally resolve to shared, room, household,
guest-safe or kids profiles through explicit satellite mapping, area/room
mapping or fallback. They should not write personal Music DNA merely because no
speaker identity was detected.

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

The canonical target resolution priority is:

1. explicit `profile_id`;
2. linked DJConnect Profile for `device_id`;
3. explicit satellite mapping;
4. Home Assistant `user_id` mapping/hint, when available;
5. area/room mapping;
6. playback zone/player mapping, when configured;
7. configured fallback profile;
8. structured `ProfileRequired` error.

Resolution must be deterministic. Explicit profile selection has highest
priority, and an invalid explicit profile must return a structured error rather
than silently selecting a different personal profile. Explicit device mapping
beats inferred room mapping. Explicit satellite mapping beats area mapping. A
shared satellite should default to a shared, room or household profile unless
explicitly configured otherwise. Future speaker recognition may become a hint,
but it must never silently override explicit profile selection and is not part
of the current implementation.

Current Epic 3 runtime implementation uses `ProfileResolutionContext` with
`profile_id`, `device_id`, `ha_user_id` and `room_id`, and resolves in this
implemented order:

1. explicit `profile_id`;
2. `device_id` mapping;
3. Home Assistant `user_id` hint;
4. room mapping;
5. fallback profile;
6. `ProfileRequired`.

Satellite, HA device, area, player/playback zone and speaker-identity fields are
foundation-level target inputs for a follow-up implementation. Until those
fields exist in code, services must not create separate client-specific identity
resolution paths.

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

Epic 3 Phase 3 wires services and integration API entrypoints through
`custom_components/djconnect/profile_context.py`. Runtime requests can carry
optional `profile_id` and `device_id`; the shared request context resolves the
Profile with the canonical resolver, enriches current adapter payloads with a
profile-scoped `music_dna_key`, and exposes profile-derived backend/account/zone
metadata. Phase 3 keeps Ask DJ, Music DNA and Discovery storage adapters in
place so Phase 4 can migrate durable state without changing service/API
signatures again.

Epic 3 Phase 4 completes the Profile Platform with
`custom_components/djconnect/profile_privacy.py` and
`custom_components/djconnect/profile_export.py`. Privacy policy is resolved once
per Profile request and controls whether Ask DJ history, Music DNA,
recommendations, likes/dislikes and mood may persist. Export/import operates on
the explicit Profile Platform storage schema and excludes OAuth tokens, provider
secrets, Home Assistant tokens, APNs tokens, device tokens and raw credentials
by default. Clear/reset flows remove profile-owned personal references without
deleting the Profile.
