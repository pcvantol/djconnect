# DJ Session Vision

**Status:** Canonical product experience vision  
**Owner:** DJConnect Product Development  
**Scope:** The desired experience of every DJ Session

## Introduction

DJConnect is **a personal AI DJ that hosts listening sessions**.

Music providers play music. DJConnect hosts the experience around it: the
flow, the sense of occasion, the helpful context and the personality that make
listening feel intentional. A listener should feel accompanied by their DJ,
not surrounded by a collection of AI features.

This vision describes the experience DJConnect should create. It does not
define implementation, UI layouts, storage, synchronization, architecture or
roadmap sequencing. `PRODUCT_DEFINITION.md` defines product direction and
`DJ_SESSION_DOMAIN_MODEL.md` defines the shared product vocabulary.

## North Star

The **DJ Session is the product**. The AI DJ is the primary experience, and
every individual capability exists only to strengthen that hosted listening
session.

People should think about their DJ, never about AI modules. The experience
should feel like one calm, capable presence that understands the music, notices
the moment and knows when a contribution will make the session better.

## Primary Experience

A DJ Session is the primary DJConnect experience. People do not open
DJConnect merely to operate playback; they open it to experience a hosted
listening session.

Playback remains immediately available when people need it, but it is no
longer the product. The product is the feeling that music has a host: someone
who can set the tone, answer a question, add useful context, surface a fitting
next idea and let a moment breathe.

## Relationship with Playback

Playback belongs to the configured **Music Backend**. Spotify Direct and Music
Assistant are examples of Music Backends that play music.

DJConnect enriches playback; it never owns playback. The DJ Session uses the
listening moment to host a better experience without making the listener think
about providers, accounts or playback machinery.

A future Continue Session may join one observed playback occurrence only through
the Music Backend Observation Boundary and the deferred contract in
[`CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md`](CONTINUE_CURRENT_PLAYBACK_CONTINUITY.md).
It never turns the DJ Session into a playback owner.

## DJ Session Lifecycle

The conceptual shape of a DJ Session is:

```text
Idle
  ↓
Start DJ Session
  ↓
Active Session
  ↓
End Session
  ↓
Session Timeline
  ↓
Music DNA learns (opt-in)
```

This is an experience model, not an implementation model. A session begins
when the listener enters a listening moment, becomes active as the DJ hosts
that moment, and ends with a story worth revisiting. Opted-in Music DNA may
help the same DJ become more personal in future sessions, without changing the
fact that the listener experiences one continuous DJ.

## Session Mood

**Session Mood** belongs to a DJ Session, not to the application as a whole.
It expresses how the listener wants their DJ to host this particular moment.

Chill, Groove, Energy and Party are examples of Session Mood. A mood affects
the announcement style, recommendation style, visual atmosphere and overall
session personality. It should shape the character of the present listening
moment without trapping the listener in a permanent global setting.

## Capability Orchestration

Ask DJ, Track Insight, Discover, Announcements, VibeCast and Music DNA are not
separate products. They are expressions of one AI DJ.

The DJ brings forward the right capability only when it strengthens the
session: an answer when a listener is curious, an insight when it adds meaning,
a recommendation when it fits the flow, a visual moment when the room benefits
from it, or a personal touch when the listener has opted in. No capability
should compete for attention simply because it is available.

## Silence

A good DJ does not speak continuously. Silence is part of the experience.

The DJ should interrupt only when it adds value: to welcome a moment, answer a
question, illuminate something meaningful, help a decision or make the
session feel more alive. Quiet confidence is preferable to constant
commentary.

## Session Timeline

The Session Timeline is the story of a completed DJ Session. It is not a chat
history.

It is the chronological representation of everything meaningful that happened
during the session: music, contributions from the DJ, questions, discoveries,
choices and moments that gave the listening experience its character. It lets
the listener remember a session as an experience rather than reconstructing it
from disconnected feature activity.

## Community and Personal

### Community

Community means the DJ understands music. It hosts a complete local-first DJ
Session with musical understanding, helpful context and shared listening
moments.

### Personal

Personal means the same DJ gradually understands the listener through opt-in
Music DNA. It does not create a second DJ or a separate kind of session. The
listener encounters one DJ that becomes increasingly personal over time, while
remaining respectful of the context in which the session is shared.

## Product Principles

- Every feature should strengthen the DJ Session.
- Playback should never dominate the experience.
- Technology should remain invisible.
- Context is more valuable than volume.
- Personality should feel authentic.
- Every interaction should feel intentional.
- The experience should remain calm and premium.
- Session quality is more important than feature quantity.

## Decision Filter

Every future Product Engineering proposal must answer one permanent question:

> Does this make the DJ Session better?

If the answer is no, the capability should be reconsidered. A useful feature
is not enough on its own; it must help the AI DJ host a more coherent,
meaningful and enjoyable listening session.
