# DJConnect Constitution

This document is the highest-level source of truth for DJConnect product and architecture decisions.

When a prompt, issue, implementation detail, or repository-specific document conflicts with this Constitution, the Constitution wins unless it is explicitly amended.

## Mission

**Play your music. DJConnect brings it to life.**

DJConnect is an AI music companion and platform for Home Assistant-powered music experiences.

DJConnect is not merely a Spotify client, a Music Assistant frontend, a Home Assistant dashboard, or a collection of disconnected AI features. It connects music backends, profiles, devices, renderers, and intelligence into one coherent listening experience.

## Product promise

The user starts music. DJConnect does the rest.

DJConnect should make music feel richer, more contextual, more personal, and more alive without making users manage internal AI modules.

## Core laws

### Law 1: Everything personal belongs to a DJConnect Profile

Music DNA, mood, DJ personality, response style, recommendations, likes/dislikes, conversation memory, privacy preferences, and continuity belong to a Profile.

A Profile owns exactly one Music Backend binding, its settings and preferences,
conversation history and session history. Clients never store Profile state.

A user should feel like they have one personal DJ available across all personal devices linked to the same profile.

### Law 2: Everything hardware-related belongs to a Device

A Device owns hardware, client, runtime, and UI context: device ID, device name, device type, capabilities, default room/player, microphone/speaker settings, notifications, display constraints, wake-word behavior, and last-seen state.

Devices must not own persistent personal intelligence.

### Law 3: Everything playback/provider-specific belongs to the Music Backend

Playback control, provider credentials, queues, players, zones, capabilities,
library access and provider-specific behavior belong behind Music Backend
adapters. Their Playback Control Boundary owns control, queue and transport;
their Playback Observation Boundary owns normalized current-playback observation
and opaque Playback Instance Identity.

A Music Backend belongs to a Profile, never to a DJ Session. Playback is
context for the DJ Session, not the product's primary ownership boundary.

Spotify Direct, Music Assistant, Tidal Direct, Qobuz Direct, and future providers are adapters, not the platform.

### Law 4: Profiles are the primary identity

The primary DJConnect identity is the DJConnect Profile.

It is not the Spotify account, not the Home Assistant user, not the device, and not the client platform.

Home Assistant user IDs may be used as hints, but never as the core identity model.

### Law 5: Music backend agnostic by design

No product feature should assume Spotify unless it lives in a Spotify-specific adapter.

Ask DJ, Track Insight, Lyrics Intelligence, VibeCast, Discover, recommendations, Music DNA, and profile state must depend on normalized music domain concepts and backend capabilities.

### Law 6: The backend owns intelligence

Persistent intelligence is generated, stored, and coordinated by the DJConnect Home Assistant integration or platform backend.

Clients render capabilities. Clients may provide local UI affordances and transient rendering state, but they must not become independent sources of persistent intelligence.

### Law 7: Clients are equal platform citizens

No client owns product features.

Apple, Windows, Pi, ESP32, future Android, web, VibeCast, and other clients expose platform capabilities according to their strengths and constraints.

A feature belongs to DJConnect, not to a single client implementation.

### Law 8: Shared devices are room-first; personal devices are profile-first

Personal devices such as phones, watches, laptops, and desktops should usually resolve to a personal profile.

Shared devices such as living-room displays, kitchen satellites, family hubs, and guest-facing screens should usually resolve to a household, room, kids, or guest profile.

### Law 9: Community must feel complete

Community should be a strong, useful, and coherent DJConnect experience.

Personal adds personalization, continuity, and premium identity-level capabilities. It must not feel like Community was intentionally crippled.

### Law 10: The product should become simpler as capabilities grow

New features must reduce conceptual friction, not increase it.

Users should not need to understand every underlying intelligence provider. They should experience one coherent DJ.

### Law 11: Shortest path to first success

Initial setup should create the minimum working experience.

Advanced household, multi-user, device, account, and privacy management belongs in options or management flows.

### Law 12: Graceful degradation

Missing data should reduce richness, not break the experience.

No lyrics should fall back to Track Insight. No Music DNA should fall back to generic recommendations. No Personal should fall back to Community Intelligence. No cloud should fall back to local capabilities.

### Law 13: Every feature must enrich listening

A feature should make listening richer, easier, more contextual, more personal, more social, more beautiful, or more reliable.

If it does not improve the listening experience, it probably does not belong in DJConnect.

### Law 14: The Session Runtime owns the active DJ Session

Every active DJ Session has a server-owned, ephemeral Session Runtime. It owns
active Session orchestration, Session Planner, Conversation Engine, Session
Memory, Session Flow, Broadcast Engine, Audience Signals and Runtime State. It
may consume a validated bounded playback observation, but Playback Context and
Playback Instance Identity remain owned by the Music Backend Observation
Boundary. When the session ends, the Runtime ends; only permitted durable
outcomes may be written back to its Profile.

### Law 15: Session Flow is primary

The Session Planner continuously plans the next listening period and produces
Session Flow: what the DJ intends to do next. A provider queue remains
backend-owned and may be available as an advanced view, but is not the primary
DJConnect experience.

### Law 16: VibeCast is a Broadcast Capability

The Broadcast Engine publishes an event-driven Broadcast Feed for an active DJ
Session. VibeCast is rendered locally by a Universal Session Receiver; it is
not video streaming or server-rendered video.

## Anti-goals

DJConnect should not become:

- a Spotify-only client;
- a Music Assistant-only frontend;
- a generic Home Assistant dashboard;
- a social network;
- a cloud-only service;
- a vendor-locked ecosystem;
- a collection of disconnected AI experiments;
- a system where every client implements its own business logic;
- a system where personal state is scattered across devices.

## Design maxim

**Everything personal belongs to a Profile.**  
**Everything hardware-related belongs to a Device.**  
**Everything playback/provider-specific belongs to the Music Backend.**
