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
| DJConnect Profile | Primary identity for personal/shared DJConnect state |
| Music DNA | User-facing personal music taste and memory |
| Ask DJ | Conversational AI DJ experience |
| Insights | User-facing umbrella for track, artist, album, lyrics and mood intelligence |
| VibeCast | Shared visual presentation experience for TV/AirPlay/large screens |
| Discover | Recommendation and discovery experience |
| Music Backend | Provider adapter such as Spotify Direct or Music Assistant |
| Music Account | Provider account binding used by a profile |
| Household Profile | Shared profile for shared devices and family spaces |
| Shared Room Profile | Shared profile for a room, area or satellite context |
| Guest Profile | Guest-safe shared profile with no personal leakage |
| Voice Satellite / HA Voice Satellite | Home Assistant voice endpoint that can invoke DJConnect through Assist |
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
