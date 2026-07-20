# DJConnect Architecture Principles

These principles describe where responsibilities live in the DJConnect platform.

## Canonical model

```text
Interaction / Request
  -> Request Context
  -> Profile Resolver
  -> DJConnect Profile
  -> Music Backend / Music Account
  -> DJ Session Runtime
  -> Session Planner / Broadcast Engine
  -> Session Flow / Broadcast Feed
  -> Renderer
```

## Primary domain concepts

### Profile

A Profile is the source of truth for personal DJConnect state:

- exactly one Music Backend binding and selected Music Account;
- Music DNA;
- settings and preferences;
- mood state;
- DJ voice tone;
- response style;
- Ask DJ conversation history;
- session history;
- recommendation history;
- likes/dislikes;
- fallback playback zone/player;
- privacy mode;
- tier/capabilities.

Multiple devices may link to the same profile.

A Profile is server-owned. Clients do not store Profile state. A Music Backend
belongs to a Profile, never to a DJ Session.

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

### DJ Session Runtime

A DJ Session Runtime is server-owned and ephemeral. It exists only while a DJ
Session is active and owns Playback Context, Session Planner, Conversation
Engine, Session Memory, Session Flow, Broadcast Engine, Audience Signals and
Runtime State. It may write only permitted durable outcomes back to its owning
Profile when the session ends.

### Session Planner and Session Flow

The Planner plans Knowledge Intents, not renderer features. The canonical
presentation path is `Knowledge Intent → DJ Moment Engine → immutable DJ
Moment → Broadcast → Renderer`; see `docs/product/DJ_PRESENTATION_ARCHITECTURE.md`.

The Session Planner is the central AI orchestration engine. It continuously
plans approximately the next fifteen minutes and replans from playback,
interaction, audience signals, conversation, mood, backend availability and
permitted Music DNA. It produces Session Flow, not a static playlist.

Session Flow is the primary DJConnect experience of what the DJ plans next:
current track, announcements, Track Insights, Discover moments, musical
direction and planned transitions. The backend queue remains provider-owned and
can be shown only as an advanced playback view.

The canonical Runtime lifecycle, state ownership, typed Session Flow, Broadcast
Feed, Audience Signal, Room Voice, Renderer and Session Capability contracts
are defined in `DJ_SESSION_RUNTIME_CONTRACTS.md`.

### Broadcast Engine and Broadcast Feed

The Broadcast Engine publishes an event-driven Broadcast Feed for an active
session. It is neither video streaming nor server-rendered video. VibeCast is
the session's Broadcast Capability; a Universal Session Receiver renders the
feed locally.

### Insight Feed

The Insight Feed remains the normalized internal stream of DJConnect
intelligence events and cards. The Session Runtime selects permitted items for
Session Flow and the Broadcast Engine publishes the resulting event-driven
Broadcast Feed. Renderers consume the Broadcast Feed or another explicitly
scoped session contract, not an unbounded intelligence stream.

## Profile resolution

All intents, services, API endpoints, and client calls should resolve profile context through one central resolver.

Profile resolution accepts a general request context, not only a DJConnect
Device. Devices are important request sources, but not every interaction
originates from a DJConnect Device. Voice Endpoints such as Home Assistant
Voice Satellites, automations, services, Home Assistant user context, room/area context, playback
players and future speaker recognition all use the same canonical
`ProfileResolver`.

Do not implement separate identity resolution paths per client, service,
websocket endpoint, Assist surface or integration entrypoint.

Resolution priority:

1. explicit `profile_id` from DJConnect client/request;
2. linked profile for `device_id`;
3. explicit Voice Endpoint mapping;
4. mapped Home Assistant `user_id` hint if available;
5. area/room mapping;
6. playback zone/player mapping, when configured;
7. configured fallback profile;
8. clear `profile_required` error.

Home Assistant `user_id` is useful but not authoritative. Voice Endpoints
should normally resolve by explicit Voice Endpoint mapping, area/room mapping or
fallback, not by speaker identity. Future speaker recognition may provide a
hint, but it must not silently override explicit profile selection.

Tie-breaking must be deterministic:

- explicit profile selection always wins;
- invalid explicit profiles return an error instead of falling through to a
  different personal profile;
- linked DJConnect device profiles beat inferred room/area mappings;
- explicit Voice Endpoint mappings beat inferred area mappings;
- shared room Voice Endpoints default to shared, room, household or guest-safe
  profiles unless explicitly configured otherwise.

Current Epic 3B runtime support accepts explicit profile, device, Voice
Endpoint, Home Assistant user, area/room and playback player/zone signals
through `ProfileResolutionContext`. Speaker-recognition signals remain future
hints and must still route through the same `ProfileResolver`.

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

### Personal Experience renderers

Examples: iPhone, iPad, macOS, Windows and Apple Watch.

Capabilities may include Ask DJ, Music DNA, Track Insight, Discover, VibeCast control, profile settings, notifications, and rich insight rendering.

### Shared Experience renderers

Examples: Browser, TV, Chromecast, Raspberry Pi, desktop and guest phones.

Capabilities may include now playing, light insights, Discover feed, read-only Ask DJ stream, playback controls, and household context.

### Room Experience renderers

Examples: ESP32, firmware remotes and Home Assistant Voice Satellites.

Capabilities may include intents, push-to-talk, playback controls, and short TTS DJ response playback.

## Repository responsibilities

### `pcvantol/djconnect`

Home Assistant integration, local platform core, music backend abstraction, profile resolution, intelligence orchestration, services, websocket/API endpoints, local storage, and source-of-truth documentation.

### `pcvantol/djconnect-api`

Central API, APNs relay, install/device trust, future entitlement boundary, future cloud profile capabilities. It should not become the primary local intelligence source.

### `pcvantol/djconnect-app`

One native application shell with Owner, Guest and Demo runtimes; its UI is
capability-driven rather than mode-driven.

### `pcvantol/djconnect-windows`

Windows Personal Experience renderer and Universal Session Receiver host where
its capabilities allow.

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
