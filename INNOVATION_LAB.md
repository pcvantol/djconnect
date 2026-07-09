# DJConnect Innovation Lab

This document captures product ideas, experiments, long-term concepts, and design questions.

It is **not** a roadmap. Inclusion here does not imply commitment, priority, or implementation.

Ideas should be promoted to `PRODUCT_ROADMAP.md` only after they are aligned with the Constitution, product vision, design principles, architecture principles, and implementation capacity.

## Status labels

- 🟢 Vision: product direction or long-term concept.
- 🟡 Exploration: promising idea needing product/architecture discovery.
- 🔵 Research: external dependency or feasibility needs research.
- 🟣 Prototype: worth building experimentally.
- ⚫ Rejected: intentionally not planned.

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

Dependencies:

- lyrics provider;
- cached track lyrics;
- Insight Feed;
- profile privacy behavior;
- VibeCast active session state.

Constraints:

- do not use the term karaoke as the product feature name;
- do not persist sensitive lyric-derived user interpretations unless profile settings allow it;
- degrade gracefully if lyrics are unavailable.

### Live Lyrics Layer

**Status:** 🔵 Research  
**Domain:** VibeCast / Lyrics Intelligence

Display time-synced lyrics in VibeCast and potentially Track Insight.

Open questions:

- provider availability;
- synchronization quality;
- licensing;
- local caching;
- fallback behavior;
- whether LRCLIB coverage is sufficient for MVP.

### Hybrid VibeCast

**Status:** 🟢 Vision  
**Domain:** VibeCast / Insight Feed

VibeCast should become a hybrid presentation surface where artist, album, track, lyrics, mood, artwork, and insight information naturally combine into one ambient experience.

VibeCast should not require users to choose many separate modes. It should default to a coherent hybrid mode.

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

Open questions:

- local network only or Nabu Casa/remote option later;
- token lifetime after track change;
- whether love events are realtime-only or aggregated;
- whether this remains Community-only and intentionally non-personal.

## Personal Intelligence

### Profile Portability

**Status:** 🟢 Vision  
**Domain:** Personal / Profiles / Export-Import

Allow a DJConnect profile to move between Home Assistant installations.

Profile export may include:

- profile metadata;
- Music DNA;
- mood history/settings;
- DJ voice/response style;
- Ask DJ chat history;
- recommendation memory;
- likes/dislikes;
- optional device mappings;
- optional backend/account bindings without secrets.

OAuth tokens and provider secrets must not be exported by default. New installations should require account re-linking.

### Ask DJ Continuity

**Status:** 🟢 Vision  
**Domain:** Ask DJ / Profile

Ask DJ conversation history should be profile-bound, not device-bound.

Personal devices linked to the same profile should share context. Shared profiles should have separate shared history. Shared devices should not show personal history unless explicitly linked to a personal profile.

## Household Intelligence

### Household DJ Profiles

**Status:** 🟢 Vision  
**Domain:** Profiles / Household

Support profiles such as Household, Living Room, Kitchen, Kids, Guest, and Party.

These profiles should support shared experiences without leaking personal state.

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

## Design questions

- When should DJConnect speak, and when should it stay silent?
- How proactive should insights be?
- How much personality is too much personality?
- Should personal insights appear on shared screens?
- What is the right balance between magical automation and user control?
- How should DJConnect explain recommendations without feeling clinical?
- What data should never leave the local Home Assistant instance?
- How should future cloud features enhance rather than replace local-first Community?
