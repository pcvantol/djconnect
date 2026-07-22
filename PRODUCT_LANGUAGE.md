# DJConnect Product Language

This document defines the preferred product language for DJConnect across the website, apps, documentation, release notes, prompts and future store listings.

Use it to keep DJConnect understandable as one product instead of a collection of technical features.

## Core message

Primary line:

> Play your music. DJConnect brings it to life.

Short positioning:

> Your AI DJ for Home Assistant-powered music experiences.

Experience positioning:

> DJConnect turns music playback into an intelligent, personal and room-aware experience.

## Tier language

Community:

> Your AI DJ understands music.

Personal:

> Your AI DJ understands you.

Future Cloud:

> Your AI DJ can optionally follow you beyond one Home Assistant instance.

Do not describe Community as a trial, lite version or crippled product.

## Preferred terms

Use these terms consistently:

| Preferred term | Meaning |
| --- | --- |
| DJ Session | The primary coherent AI DJ listening experience, independent from any specific playback provider. |
| DJ Session Runtime | Server-owned, ephemeral runtime for one active DJ Session. Developer-facing; do not use as consumer UI copy. |
| Session Planner | The AI orchestration engine that continuously plans an active DJ Session. Developer-facing; do not use as consumer UI copy. |
| Session Flow | What the DJ is planning next in an active DJ Session; it is the primary experience, not the provider queue. |
| Session Capability | Runtime-owned statement of what an active session permits a renderer to do. Developer-facing; do not use as consumer UI copy. |
| Audience Signal | A listener contribution that the Session Planner may interpret; it is never a direct playback command. |
| Session Memory | The objective chronological record of events in one DJ Session; it performs no interpretation. |
| Session Timeline | The user-facing chronological story of one completed DJ Session; it is not a chat history. |
| Playback Context | Music Backend-owned playback information available to DJConnect, such as the current track, queue, state, device or room context. |
| DJConnect Profile | Primary identity for personal/shared DJConnect state |
| Music DNA | Opt-in evolving understanding of a person's musical identity from patterns across many DJ Sessions; it does not replace Session Memory. |
| Ask DJ | Conversational AI DJ experience |
| Insights | User-facing umbrella for track, artist, album, lyrics and mood intelligence |
| Broadcast Feed | Event-driven feed from an active DJ Session for local renderer consumption. Developer-facing; it is not video. |
| [VibeCast](docs/product/VIBECAST_ARCHITECTURE.md) | Ambient-first, minimally interactive DJConnect web-renderer experience for large displays and television devices. It is built on the Universal Receiver Web Platform and renders renderer-safe Broadcast projections locally. |
| Universal Receiver Web Platform | Shared projection-based web platform for Renderer Host connection, renderer-safe projections and reusable presentation primitives. Its Universal Receiver experience is the Interactive web product shell. |
| Google Cast Custom Web Receiver | The deferred VibeCast V1 television host. Google Cast launches it; it renders locally and does not receive a stream of sender pixels. |
| Discover | Recommendation and discovery experience |
| Music Backend | Provider adapter such as Spotify Direct or Music Assistant; it owns playback and provides Playback Context to DJConnect. |
| Music Account | Provider account binding used by a profile |
| Household Profile | Shared profile for shared devices and family spaces |
| Shared Room Profile | Shared profile for a room, area or satellite context |
| Guest Profile | Guest-safe shared profile with no personal leakage |
| Voice Satellite / HA Voice Satellite | Home Assistant voice endpoint that can invoke DJConnect through Assist; retain this external term for Home Assistant docs, entities, configuration and UI |
| [Audio Renderer Host](docs/technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md) | Internal DJConnect architectural term for a Renderer Host that renders approved audio presentation; a Home Assistant Voice Satellite is one implementation |
| [Ambient Light Renderer Host](docs/technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md) | Deferred internal DJConnect presentation role for approved ambient lighting; it is not a WLED, Hue or raw-audio integration |
| Request Context | Developer-facing resolver input describing where an interaction originated |
| Satellite mapping | Developer-facing mapping from an HA Voice Satellite to a DJConnect Profile |
| Personal | Paid/profile-level personalization tier |
| Community | Open-source/local-first foundation |
| Experimental | Feature exists for testing and may change |
| Preview | Feature is usable but not yet stable |
| Stable | Feature is part of the expected product experience |

## Supported Languages

DJConnect's canonical user-facing product languages are:

- English
- Dutch
- German
- French
- Spanish

The canonical locale families are `en`, `nl`, `de`, `fr` and `es`; see
`LOCALIZATION_STANDARD.md` for the full platform contract.

Preferred terms must be translated consistently across clients, website and
release surfaces. Brand and feature names may remain invariant where the
product language requires it, including `DJConnect`, `Music DNA`, `Ask DJ` and
`VibeCast`.

Machine-readable terms such as API paths, JSON keys, service names, protocol
values and error codes remain untranslated. Consumer copy should be natural in
each locale, not direct word-for-word translation from English.

## Avoid or restrict

| Avoid | Prefer | Reason |
| --- | --- | --- |
| Spotify profile | DJConnect Profile | Spotify is only a backend/account binding |
| Backend profile | DJConnect Profile | Avoid identity confusion |
| HA user profile | DJConnect Profile | HA user is only a hint |
| Request Context as a feature name | Profile, device, room or voice context | Developer-facing term, not consumer-facing copy |
| Speaker recognition supported | Future speaker recognition hint | Not in current product scope |
| Karaoke | Live Lyrics / Lyrics Explain | DJConnect is not a karaoke product |
| AI assistant | AI DJ | More specific and emotional |
| Track Analysis | Insights / Track Insight | Analysis sounds technical |
| SpotifyDJ | DJConnect | Old name / provider-specific |
| Cloud required | Optional cloud extension | Community remains local-first |
| Free vs paid | Community vs Personal | More value-oriented |
| Feature locked | Personal capability | Avoid negative framing |
| Queue as the main experience | Session Flow | The backend queue remains an advanced playback view. |
| VibeCast video stream | VibeCast web-renderer experience | VibeCast is event-driven and rendered client-side. |
| Universal Session Receiver | Universal Receiver Web Platform / Universal Receiver | The older term conflates the shared web platform, its Interactive experience and VibeCast. |
| Native Google TV app / Android TV app | Google Cast Custom Web Receiver | Native television applications are not VibeCast V1 scope. |
| AirPlay stream / mirrored VibeCast | Local VibeCast Custom Web Receiver rendering | Sender-side pixel or video streaming contradicts Renderer Host ownership. |

## Feature naming rules

Good names should:

- describe the experience, not the implementation;
- work on multiple clients;
- avoid provider names unless provider-specific;
- fit under the larger DJConnect Intelligence model;
- be understandable on the website and in app UI.

Examples:

- `Lyrics Explain` is acceptable as a feature concept.
- `Live Lyrics Layer` is acceptable for VibeCast/Insight rendering.
- `On-the-Go DJ` is acceptable for mobile listening companion ideas.
- `VibeCast Guest Companion` is acceptable for QR guest pages.
- `Give Love` is acceptable for guest hearts/reactions.

## Client language

Do not describe features as owned by one client.

Use:

> Apple client supports VibeCast control.

Avoid:

> VibeCast is an Apple feature.

Use:

> Windows renders the same Insight Feed with desktop affordances.

Avoid:

> Windows has different insight logic.

## Backend language

Use:

> Spotify Direct backend
> Music Assistant backend
> Music Backend adapter

Avoid:

> Spotify mode owns recommendations
> Music Assistant profile

Backend choice affects playback capability. It should not redefine the DJConnect product model.

## Privacy language

Use plain language:

- Private session: DJConnect does not save this listening/chat context.
- Shared profile: designed for rooms, family spaces and guests.
- Export: excludes OAuth tokens and secrets by default.
- Music DNA: your DJConnect taste memory.

Avoid implying hidden tracking or vague AI memory.

## Store and website language

Prefer benefit-led copy:

- “Ask your music questions.”
- “See why a track matters.”
- “Turn your TV into a living music display.”
- “Let your AI DJ learn your taste.”
- “Keep one DJ across your devices.”

Avoid implementation-first copy:

- “Uses Spotify Web API.”
- “Calls Home Assistant services.”
- “Runs backend processors.”

Technical details belong in developer docs.
