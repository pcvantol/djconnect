# DJConnect Innovation Lab

This document captures product ideas, experiments, long-term concepts, and design questions.

It is **not** a roadmap. Inclusion here does not imply commitment, priority, or implementation.

Ideas should be promoted to `PRODUCT_ROADMAP.md` only after they align with the Constitution, Product Vision, Design Principles, Architecture Principles, and implementation capacity.

The active Innovation Lab work register is `INNOVATION_BACKLOG.md`; promotion
rules are owned by `INNOVATION_PROMOTION_POLICY.md`. The labels below describe
idea maturity, not an additional roadmap-status system.

Runtime evolution research belongs in `docs/research/`, not in the Innovation
Lab. Product ideas remain here; strategic runtime questions such as Home
Assistant-only, standalone runtime, hosted runtime or cloud runtime belong to
`docs/research/R0_RUNTIME_INDEPENDENCE.md`.

## Status labels

- 🟢 Vision: product direction or long-term concept.
- 🟡 Exploration: promising idea needing product/architecture discovery.
- 🔵 Research: external dependency or feasibility needs research.
- 🟣 Prototype: worth building experimentally.
- ⚫ Rejected: intentionally not planned.

---

## Music Intelligence

### Lyrics Explain

**Status:** 🟡 Exploration  
**Domain:** Music Intelligence / Ask DJ / VibeCast / Track Insight

Explain, summarize, translate, and contextualize lyrics without turning DJConnect into a karaoke product.

Potential capabilities:

- song meaning summary;
- translation;
- symbolism and themes;
- timed insight cards synced to track progress;
- Ask DJ explanations;
- VibeCast lyric/context layers;
- Track Insight dynamic lyric facts.

Constraints:

- do not use karaoke as the product feature name;
- degrade gracefully if lyrics are unavailable;
- consider licensing and provider coverage before implementation.

### Live Lyrics Layer

**Status:** 🔵 Research  
**Domain:** VibeCast / Lyrics Intelligence

Display time-synced lyrics in VibeCast and potentially Track Insight.

Open questions:

- provider availability;
- synchronization quality;
- licensing;
- local caching;
- LRCLIB coverage and reliability;
- fallback behavior.

### Hybrid VibeCast

**Status:** 🟢 Vision  
**Domain:** VibeCast / Insight Feed

VibeCast should become a hybrid presentation surface where artist, album, track, lyrics, mood, artwork, and insight information naturally combine into one ambient experience.

VibeCast should not require users to choose many separate modes. It should default to a coherent hybrid mode.

---

## VibeCast and Guest Experiences

### VibeCast Guest Companion

**Status:** 🟡 Exploration  
**Domain:** VibeCast / Household / Guest Experience  
**Tier:** Community candidate

VibeCast shows a QR code that opens a temporary mobile-first local web page for the current track. Guests can access it without the DJConnect app or Home Assistant login.

Concept:

- local Home Assistant custom endpoint;
- temporary token in QR code;
- active only while VibeCast is active and the track is playing;
- readonly mobile one-pager;
- DJConnect styling and current VibeCast mood theme;
- artwork, track info, Track Insight, artist trivia, Wikipedia deep links, Discogs links, album/artist/track links;
- Up Next section with the next three queued tracks if available;
- no personal profile data;
- no playback control;
- no guest identity.

Potential extension: **Give Love**

Guests can tap a heart button repeatedly. VibeCast receives aggregated love intensity and renders a temporary hearts layer. The amount and speed of hearts depends on realtime tap intensity.

Architecture fit:

```text
VibeCast Session
  -> guest companion token
  -> temporary local HA endpoint
  -> QR rendered in VibeCast
  -> guest mobile page
  -> readonly track companion
  -> optional love events
  -> HA pushes love intensity to VibeCast layer
```

Constraints:

- no personal Music DNA;
- no Ask DJ personal history;
- no OAuth tokens;
- no Home Assistant administration;
- token must be scoped to VibeCast session and current/near-current track;
- endpoint must expire automatically;
- rate limiting should exist for love events.

---

## Personal Intelligence

### Profile Portability

**Status:** 🟢 Vision  
**Domain:** Personal / Profiles / Export-Import

Allow a DJConnect Profile to move between Home Assistant installations.

Profile export may include profile metadata, Music DNA, mood settings/history, DJ voice/response style, Ask DJ chat history, recommendation memory, likes/dislikes, optional device mappings, and optional backend/account bindings without secrets.

OAuth tokens and provider secrets must not be exported by default. New installations should require account re-linking.

### Ask DJ Continuity

**Status:** 🟢 Vision  
**Domain:** Ask DJ / Profile

Ask DJ conversation history should be profile-bound, not device-bound.

Personal devices linked to the same profile should share context. Shared profiles should have separate shared history. Shared devices should not show personal history unless explicitly linked to a personal profile.

### Household DJ Profiles

**Status:** 🟢 Vision  
**Domain:** Profiles / Household

Support profiles such as Household, Living Room, Kitchen, Kids, Guest, and Party. These profiles should support shared experiences without leaking personal state.

---

## Discover

### Forgotten Favorites

**Status:** 🟡 Exploration

Surface tracks or artists the profile used to love but has not listened to recently.

### Hidden Gems

**Status:** 🟡 Exploration

Recommend lesser-known tracks aligned with Music DNA.

### Recommendation Explanations

**Status:** 🟢 Vision

Every recommendation should be explainable: why this track, why now, why for this profile.

---

## Immersive / VR / MR Experiences

### DJConnect VR Experience

**Status:** 🟡 Exploration  
**Domain:** VR / MR / Spatial Computing / Personal Intelligence / VibeCast  
**Potential clients:** Meta Quest, future Apple Vision Pro, future spatial web

DJConnect should not become another music player in VR. The opportunity is to create something only DJConnect can do because it combines AI, Home Assistant, music backends, profile intelligence, VibeCast-style visuals, and spatial presence.

#### Favorite direction: AI DJ avatar in your room

Your living room becomes a virtual club or listening lounge.

- An AI DJ avatar appears near the TV or music zone.
- It reacts to what is playing.
- It tells artist trivia, track context and mood notes.
- It can announce tracks like a radio DJ.
- It can be interrupted naturally:
  - “Play something more energetic.”
  - “More trance from 2005.”
  - “What is this track?”

Unique angle: not a chatbot window, but a spatial DJ personality that feels physically present in the room.

#### Spatial Music Journey

The listener walks through music as spatial worlds:

- rock as a stadium;
- ambient as a forest;
- techno as a warehouse;
- trance as a futuristic tunnel.

Scenes could be generated from BPM, energy, genre, lyrics and mood.

#### Spotify Wrapped Live / Music Year World

A 3D experience of the profile's listening history:

- favorite artists as floating objects;
- timeline of the music year;
- genres as planets or clusters;
- personalized Music DNA landscape.

This is highly shareable but depends on mature profile intelligence and privacy controls.

#### DJConnect Party Mode

Multiple headsets or guests in the same room:

- people vote on music;
- AI DJ explains or mediates the vibe;
- spatial audio and visuals react to the room;
- quizzes or lightweight guest interactions may be added.

Constraint: avoid becoming a social network or complex party platform.

#### Music Discovery Galaxy

Commercially promising concept: the user's library and recommendations become a galaxy.

- each artist is a star;
- genres are clusters;
- related artists are spatially close;
- the user flies through taste and recommendations;
- Ask DJ can create discovery routes, for example: “Show me artists between Above & Beyond and London Grammar.”

This uses spatial computing as a meaningful discovery interface rather than a gimmick.

#### DJConnect MR Visualizer

Likely fastest prototype:

- lasers, particles and projections in the living room;
- album art floating in space;
- mood-reactive visual layers;
- VibeCast Insight Feed rendered in mixed reality;
- synchronized with current playback.

This could be a modern mixed-reality evolution of music visualizers.

#### Priority if researched later

1. AI DJ avatar in your room.
2. Music Discovery Galaxy.
3. Spatial Music Journey.
4. MR Visualizer as fastest prototype path.

Core proposition:

> Talk to an AI DJ that knows your music, your profile, your home, and appears as a spatial personality in your living room.

Constraints:

- no VR-only product fork;
- no separate VR music player;
- no persistent personal data on shared/guest headsets without explicit profile resolution;
- use the same Profile, Music Backend and Insight Feed architecture;
- clients render platform capabilities rather than owning intelligence.

---

## Future Cloud

Do not market these as current features until ready.

### Premium DJ Voices

**Status:** 🔵 Research

Cloud-hosted premium voices and DJ personas.

### Cloud Profile Sync

**Status:** 🟢 Vision

Optional cloud sync for profiles across Home Assistant installations and clients.

### Entitlement Layer

**Status:** 🟢 Vision

The central API may become the trust and entitlement boundary for Personal and future Cloud features.

---

## Crazy Ideas

These are intentionally unconstrained.

- Meta Quest VibeCast;
- AR concert companion;
- AI festival companion;
- smart lighting from lyrics and mood;
- Watch haptic beat mode;
- DJConnect for cars / CarPlay-style continuity;
- live concert companion;
- party voting without becoming a social network.

---

## Rejected or constrained ideas

### Full karaoke product

**Status:** ⚫ Rejected / constrained

DJConnect may provide live lyrics and lyric explanations, but it should not become a full karaoke product.

### Social network

**Status:** ⚫ Rejected

DJConnect may support guest reactions and sharing, but it should not become a social network.

### Music library manager

**Status:** ⚫ Rejected

Library management belongs to music backends such as Music Assistant or provider apps.

---

## Design questions

- When should DJConnect speak, and when should it stay silent?
- How proactive should insights be?
- How much personality is too much personality?
- Should personal insights appear on shared screens?
- What is the right balance between magical automation and user control?
- How should DJConnect explain recommendations without feeling clinical?
- What data should never leave the local Home Assistant instance?
- How should future cloud features enhance rather than replace local-first Community?
- When does an immersive experience add value instead of becoming a gimmick?

---

## Epic 2 discovery recommendations

These ideas came from Platform Discovery. They are not committed roadmap items.

### Ambient Client capability budget

**Status:** 🟡 Exploration  
**Domain:** Client Capability Classes / Raspberry Pi / Shared Devices

Define how rich an Ambient Client should become before it stops being ambient.

The Raspberry Pi client can render Track Insight, Music DNA and Music Discovery in a room display context, but the platform needs explicit shared-screen privacy and capability boundaries.

Open questions:

- Which Music DNA blocks are safe on shared displays?
- Should Pi support profile switching or only room/household profiles?
- Which actions should require an explicitly linked personal profile?

### Contract Fixture Compatibility Dashboard

**Status:** 🟡 Exploration  
**Domain:** Developer Experience / Platform Quality

The Home Assistant repo exports contract fixtures and Apple, Windows and Pi consume them. A compatibility dashboard could show which clients pass which fixture families.

Open questions:

- Should fixture conformance be published in release notes?
- Should release repositories include fixture manifest versions?
- Can CI collect client conformance without creating cross-repo coupling?

### Foundation language lint

**Status:** 🟡 Exploration  
**Domain:** Product Language / Website / Release Repositories

Add lightweight checks for avoid terms such as `Spotify profile`, stale `Client API URL`, trial/lite tier language or client-owned intelligence language in public docs.

Open questions:

- Which terms should fail CI and which should warn?
- How should historical changelog entries be handled?

### Shared device privacy preview

**Status:** 🟡 Exploration  
**Domain:** Privacy / Profiles / Shared Devices

Create product mockups or contract examples showing how household, room, guest and personal profiles behave on Pi and VibeCast before Profile Architecture reaches implementation.

Open questions:

- What should a default shared profile reveal?
- How does a user temporarily personalize a shared device?
- How does private mode interact with VibeCast and guest companion?
