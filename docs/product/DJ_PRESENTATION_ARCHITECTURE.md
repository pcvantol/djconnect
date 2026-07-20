# DJ Presentation Architecture

## Status

Canonical conceptual architecture. This document introduces no production
implementation, AI generation, voice, VibeCast, Ask DJ or renderer behaviour.

## Canonical performance pipeline

```text
Profile → Session Runtime → Session Planner → Knowledge Intent → DJ Moment Engine → DJ Moment → Broadcast → Renderers
```

The Planner plans a performance, not individual product features. It owns
timing and emits **Knowledge Intents**: what the DJ should communicate, such as
an Artist Story, Transition, Audience Response, Recommendation or Silence.
Knowledge Intents contain no presentation choices.

The **DJ Moment Engine** receives a Knowledge Intent plus the current Runtime
context, Session Mood and DJ Persona. It creates exactly one immutable **DJ
Moment**. The Engine owns creative execution; the Planner continues to own
timing.

## DJ Persona and Session Mood

A **DJ Persona** is a first-class behavioural identity: Home DJ, Radio DJ,
Club DJ, Festival DJ or Late Night Host are examples. It defines storytelling,
verbosity, humour, enthusiasm, pacing, interaction frequency, wording and
delivery style. It is neither a voice nor Session Mood. Future Premium Cloud
voices implement Personas; they are not Personas themselves.

**Session Mood** remains a dynamic Runtime property. A change affects only
future Presentation Intents and Moments. It never mutates an existing Moment.

## Presentation Intent and DJ Moment

A **Presentation Intent** is an immutable snapshot of how a Knowledge Intent
is delivered: Session Mood, DJ Persona, tone, delivery and voice style, visual
theme, energy, importance, maximum duration and channels such as Broadcast,
Voice, Owner and Shared.

A **DJ Moment** is the universal immutable presentation object. It contains
type, title, summary, content, artwork, Knowledge Intent, Presentation Intent,
actions, visibility, delivery and importance. Canonical types include Track,
Transition, Lyric, Artist, Album, Genre, Music History, Audience, Session,
Recommendation, Discover, Concert, Producer, Trivia and Silence. Silence is
explicit: a DJ may intentionally decide not to speak.

Follow-up actions belong to a Moment; renderers only present them. Renderers
never generate Moments or reinterpret Presentation Intent. Track Insight,
Lyrics Insight, Artist Story and Discover items are specializations of DJ
Moments, not Planner-owned presentation features.
