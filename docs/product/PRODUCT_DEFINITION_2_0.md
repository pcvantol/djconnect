# DJConnect Product Definition 2.0

**Status:** Canonical product definition
**Owner:** DJConnect Product Development
**Source language:** English
**Scope:** Generation 2 product direction

## Purpose

This document translates the established Product Strategy into one shared
product definition for Product Engineering and Innovation Engineering. It
defines the user value, proposition, boundaries and decision tests that guide
future work; it does not define epics, implementation, architecture, release
scope, pricing or a feature backlog.

`PRODUCT_ROADMAP.md` owns sequencing. `INNOVATION_LAB.md` owns unvalidated
ideas. Platform and client architecture remain owned by their existing
foundation records.

## Product in one sentence

DJConnect is a local-first AI DJ that makes music feel more alive, personal and
shared across the Home Assistant-powered devices already in a home.

## Product promise

**Play your music. DJConnect brings it to life.**

DJConnect should make ordinary playback feel like one coherent music
experience: immediate to control, useful to ask, expressive to see and safe to
share. It works with existing music services and devices without making a
provider, a device or a cloud account the product's identity.

## Who it serves

| Audience | Need | DJConnect response |
| --- | --- | --- |
| Home Assistant music listener | Less friction between intention and music | Fast physical, voice and rich-client control. |
| Personal listener | Continuity without invasive tracking | A DJConnect Profile with opt-in Music DNA, memory and recommendations. |
| Household | Shared music without personal-data leakage | Household, room and guest-safe experiences with explicit boundaries. |
| Builder and early adopter | A capable local-first system that works across clients | One product model across supported control and presentation surfaces. |

## Community and Personal proposition

### Community — your AI DJ understands music

Community is the complete, open-source and local-first foundation. It gives a
household useful music control, music understanding and shared experiences
without requiring a DJConnect account. It is never a trial, a crippled product
or a negative comparison point for Personal.

Community value includes the local music experience, provider-neutral Music
Backend support, device and room control, shared-safe Insights and the
cross-client foundation needed to enjoy DJConnect at home.

### Personal — your AI DJ understands you

Personal adds profile-level continuity where a person explicitly chooses it.
It may use Music DNA, personal Ask DJ continuity, preferences, mood and
recommendations to make the same DJConnect Profile feel consistent across that
person's eligible devices.

Personal is profile-centric, not device-centric. It never authorizes personal
history or preference data to appear on a shared, guest or room surface unless
the active profile and request context explicitly allow it.

### Future Cloud — optional extension

Future cloud capabilities may enhance portability, hosted intelligence,
personas, voices or synchronization. They must extend, never replace, the
Community local-first foundation. They are not committed by this definition.

## Experience model

The product should feel like one DJ, not a set of technical modules:

1. **Control** — start, adjust or move music with low friction.
2. **Understand** — ask about music and receive useful, evidence-based context.
3. **Continue** — carry opted-in personal continuity across eligible devices.
4. **Share** — make rooms, households and guests welcome without leaking
   private context.
5. **Bring it to life** — present the right amount of personality, insight and
   visual richness for the moment and surface.

Ask DJ, Music DNA, Insights, Discover and VibeCast are named experiences that
serve this model. They are not separate products or client-owned intelligence
silos.

## Product boundaries

DJConnect is not primarily a music provider app, a Home Assistant dashboard, a
remote-control utility, a lyrics-only app, a social network or a cloud-only
service. Music providers and Home Assistant are essential integrations; they
do not replace the DJConnect product identity.

The product must not:

- require a DJConnect account for the valuable local Community experience;
- treat provider credentials or implementation detail as user value;
- infer or expose personal history on shared surfaces;
- claim knowledge that available evidence does not support; or
- promote Innovation Lab ideas to delivery commitments without an explicit
  promotion decision.

## Decision tests

Before Product Engineering accepts a new capability, its product case should
answer yes to all applicable questions:

- Does it make music control, understanding, continuity, sharing or expression
  meaningfully better?
- Is the value clear without leading with provider, protocol or implementation
  detail?
- Does it preserve a complete local-first Community experience?
- Are profile, household, room, guest and private-session boundaries explicit?
- Does it fit the shared cross-client model rather than creating a client-owned
  product fork?
- Is it validated product work, rather than an Innovation Lab hypothesis?

## Canonical proposition copy

The following user-facing source copy establishes the Community/Personal
proposition. Feature names remain invariant where required by
`LOCALIZATION_STANDARD.md`.

| Locale | Community | Personal |
| --- | --- | --- |
| `en` | Your AI DJ understands music. | Your AI DJ understands you. |
| `nl` | Je AI-dj begrijpt muziek. | Je AI-dj begrijpt jou. |
| `de` | Dein KI-DJ versteht Musik. | Dein KI-DJ versteht dich. |
| `fr` | Votre DJ IA comprend la musique. | Votre DJ IA vous comprend. |
| `es` | Tu DJ con IA entiende la música. | Tu DJ con IA te entiende. |

User-facing implementations must localize surrounding copy for all five
canonical language families: `en`, `nl`, `de`, `fr` and `es`.

## Consequences for future work

- Website redesign may use this proposition as its product-copy baseline.
- Multi-user Profiles, Music DNA and Ask DJ must preserve the Personal and
  shared-surface boundaries defined here.
- Playback Experience, Discover, Track Insight, Voice and VibeCast must be
  evaluated as parts of the one-DJ experience, not independent feature silos.
- New product copy must use the canonical terminology in `PRODUCT_LANGUAGE.md`
  and meet the five-language contract.

## Relationship to the roadmap

This definition completes the first Generation 2 roadmap item, **Product
Definition and Community/Personal proposition**. It authorizes no automatic
implementation: each later roadmap initiative still requires its own selected,
reviewable Product Engineering increment.
