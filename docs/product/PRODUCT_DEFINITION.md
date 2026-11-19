# DJConnect Product Definition 2.1

**Status:** Canonical product definition
**Owner:** DJConnect Product Development
**Source language:** English
**Scope:** Generation 2 product direction

## Purpose

This document defines the shared product model for Product Engineering and
Innovation Engineering. It captures user value, the Community/Personal
proposition, product boundaries and decision tests. It does not define epics,
implementation, architecture, release scope, pricing or a feature backlog.

`PRODUCT_ROADMAP.md` owns sequencing. `INNOVATION_LAB.md` owns unvalidated
ideas. Platform and client architecture remain owned by their existing
foundation records. `DJ_SESSION_DOMAIN_MODEL.md` defines the canonical product
vocabulary for the DJ Session model.

## Product in one sentence

DJConnect is a local-first AI DJ that hosts active DJ Sessions across the
Home Assistant-powered devices already in a home.

## Product promise

**Play your music. DJConnect brings it to life.**

DJConnect makes ordinary playback feel like one coherent music experience:
immediate to control, useful to ask, expressive to see and safe to share. It
works with existing music services and devices without making a provider, a
device or a cloud account the product's identity.

## Who it serves

| Audience | Need | DJConnect response |
| --- | --- | --- |
| Home Assistant music listener | Less friction between intention and music | One coherent AI DJ experience across control surfaces. |
| Personal listener | Continuity without invasive tracking | An opt-in DJConnect Profile that becomes more personal over time. |
| Household | Shared music without personal-data leakage | Household, room and guest-safe DJ Sessions with explicit boundaries. |
| Builder and early adopter | A capable local-first system across clients | One product model across supported control and presentation surfaces. |

## The DJ Session

A **DJ Session** is the primary DJConnect product experience. It is one
coherent AI DJ experience for a listening moment, not a menu of separate AI
capabilities for the user to assemble. Playback is context; the DJ Session is
the product.

Ask DJ, Discover, Track Insight, announcements, Music DNA and VibeCast remain
distinct capabilities. The DJ Session orchestrates them so that they appear as
the right contribution at the right moment, on the right surface and for the
right active profile or shared context. VibeCast is the broadcast capability of
an active session, rendered locally by a Universal Session Receiver rather than
streamed as video.

The DJ Session observes the listening context and enriches it. It does not own
playback: each Profile owns exactly one configured Music Backend, such as
Spotify Direct or Music Assistant. A DJ Session consumes the resulting
Playback Context and must remain valuable without requiring DJConnect to become
a music provider or playback owner.

During an active session, the server-owned Session Runtime continuously hosts
the moment through a Session Planner and its Session Flow. The Flow—not the
provider queue—is the primary expression of what the DJ plans next. A queue
may remain available as an advanced playback view.

The Planner plans what the DJ can contribute, while a future DJ Moment Engine
turns that contribution into one immutable presentation for the appropriate
surface. This keeps the DJ's personality and the current Session Mood coherent
without making a renderer responsible for creative interpretation. The
canonical presentation model is defined in
[`DJ_PRESENTATION_ARCHITECTURE.md`](DJ_PRESENTATION_ARCHITECTURE.md).

## Session Memory

**Session Memory** is the chronological record of what objectively happened
during one DJ Session. It provides the immediate context for future DJ
decisions and Ask DJ conversations within that session.

Typical Session Memory events include:

- playback changes and playback context;
- announcements and Track Insights;
- Discover recommendations and moments;
- Ask DJ interactions;
- user actions, likes, skips and queue changes; and
- meaningful room, profile or listening-context changes.

Session Memory records the session story; it is not a preference model, a
chat-history substitute or an implementation prescription. Community includes
local Session Memory as part of the complete local-first DJ Session.

## Music DNA

**Music DNA** is the evolving, opt-in understanding of a person's musical
identity derived from patterns across many DJ Sessions. It interprets Session
Memory to help the same AI DJ understand the listener more naturally over time.

Music DNA does not replace Session Memory and is not the primary chronological
record of events. Session Memory says what happened in a session; Music DNA
interprets recurring patterns across sessions. It remains profile-centric,
explicitly opt-in and unavailable to shared, guest or room surfaces unless the
active profile and request context explicitly allow it.

## DJ Session Timeline

The **DJ Session Timeline** is the user-facing chronological presentation of
Session Memory for one completed DJ Session. It is the story of that listening
experience, not a chat history.

It may present played tracks, announcements, Track Insights, Ask DJ
conversations, Discover moments, recommendations and significant user
interactions. The Timeline helps a person revisit what happened; it does not
turn every event into a separate product or expose private context on a shared
surface.

## Community and Personal proposition

### Community — your AI DJ understands music

Community is the complete, open-source and local-first DJ Session. It includes
local Session Memory, Track Insight, Discover, Ask DJ and a provider-neutral
playback experience, while playback itself remains owned by the configured
Music Backend.

Community gives a household useful music control, music understanding and
shared experiences without requiring a DJConnect account. It is never a trial,
a crippled product or a negative comparison point for Personal.

### Personal — your AI DJ understands you

Personal is the same DJ Session experience becoming increasingly personal
through opt-in Music DNA. It does not introduce a different DJ. It lets the
same AI DJ better understand the listener through patterns across their DJ
Sessions, including appropriate continuity for eligible personal devices.

Personal is profile-centric, not device-centric. It never authorizes personal
history, Session Memory or Music DNA to appear on a shared, guest or room
surface unless the active profile and request context explicitly allow it.

### Future Cloud — optional extension

Future cloud capabilities may enhance portability, hosted intelligence,
personas, voices or synchronization. They extend, never replace, the
Community local-first foundation. They are not committed by this definition.

## Experience model

The product should feel like one DJ Session rather than a set of technical
modules:

1. **Control** — start, adjust or move music with low friction.
2. **Understand** — ask about music and receive useful, evidence-based context.
3. **Remember the moment** — retain the chronological Session Memory needed to
   keep the session coherent.
4. **Continue personally** — use opted-in Music DNA to make later eligible
   sessions more relevant.
5. **Share** — make rooms, households and guests welcome without leaking
   private context.
6. **Bring it to life** — present the right amount of personality, insight and
   visual richness for the moment and surface.

## Product boundaries

DJConnect is not primarily a music provider app, a Home Assistant dashboard, a
remote-control utility, a lyrics-only app, a social network or a cloud-only
service. Music providers and Home Assistant are essential integrations; they
do not replace the DJConnect product identity.

The product must not:

- require a DJConnect account for the valuable local Community experience;
- treat provider credentials or implementation detail as user value;
- imply that DJConnect owns playback when the Music Backend does;
- infer or expose personal history on shared surfaces;
- claim knowledge that available evidence does not support; or
- promote Innovation Lab ideas to delivery commitments without an explicit
  promotion decision.

## Decision tests

Before Product Engineering accepts a new capability, its product case should
answer yes to all applicable questions:

- Does it make the DJ Session more coherent through control, understanding,
  Session Memory, personal continuity, sharing or expression?
- Is the value clear without leading with provider, protocol or implementation
  detail?
- Does it preserve a complete local-first Community DJ Session?
- Are Session Memory, Music DNA, profile, household, room, guest and
  private-session responsibilities explicit?
- Does it preserve Music Backend ownership of playback?
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

- Website redesign may use this proposition and DJ Session model as its
  product-copy baseline.
- Multi-user Profiles, Music DNA and Ask DJ must preserve the Session Memory,
  Music DNA and shared-surface boundaries defined here.
- Playback Experience, Discover, Track Insight, Voice and VibeCast must be
  evaluated as contributions to one DJ Session, not independent feature silos.
- New product copy must use the canonical terminology in `PRODUCT_LANGUAGE.md`
  and meet the five-language contract.

## Relationship to the roadmap

This refinement changes no roadmap sequencing and authorizes no automatic
implementation. Each later roadmap initiative still requires its own selected,
reviewable Product Engineering increment.
