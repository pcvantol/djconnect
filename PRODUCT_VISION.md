# DJConnect Product Vision

## Vision

DJConnect is an AI DJ.

It hosts a living **DJ Session**: a musical experience shaped by music,
storytelling, recommendations, transitions, atmosphere, audience interaction
and personality. Music playback is performed by the configured Music Backend.
The DJ Session is the product.

**Play your music. DJConnect brings it to life.**

## What DJConnect is

DJConnect is not an AI-enhanced music player or a collection of AI music
features. It is one AI DJ, present across the devices in a home, that hosts a
coherent musical occasion.

The AI DJ understands music, the current session and its audience. In the
Personal experience it may also understand the listener through explicit,
opt-in personal context. It chooses when a contribution will make the session
better and when the music should be allowed to breathe. It guides a musical
journey; it does not behave like a chatbot waiting for a command.

## What DJConnect is not

DJConnect is not primarily:

- a Spotify app;
- a Music Assistant frontend;
- a remote control;
- a Home Assistant dashboard;
- a lyrics app;
- a karaoke product;
- a social network; or
- a cloud-only service.

Those systems may provide playback, inputs, renderers or integrations. They
are not the product identity.

## The DJ Session

The primary user experience is the active DJ Session, not playback alone. A
session combines music, AI, storytelling, recommendations, transitions,
atmosphere, audience interaction and personality into one hosted experience.

Playback remains essential and immediately controllable, but it is one
component of the experience. The configured Music Backend performs playback;
DJConnect turns the listening moment into an evening with a DJ.

## DJ Moments

A **DJ Moment** is the primary building block of a DJ Session. Everything the
DJ intentionally does becomes a Moment: a Track Story, Artist Story, Album
Story, Genre Story, Recommendation, Session Update, Transition, Concert
Suggestion, Trivia or Silence.

DJ Moments are not notifications. They are contributions to the performance.
Track Insight, Discover, recommendations, artist stories and similar
experiences are different presentations of Moments, not disconnected product
features.

Silence is a Moment too. A good DJ intentionally chooses not to interrupt the
music when no contribution would improve it.

## Session Flow

The **Session Flow** is the narrative timeline of the DJ Session. Instead of
experiencing a playlist or queue as the primary story, people experience a
chronological flow of music and DJ Moments.

It can include Session Started, Track Started, DJ Moment, Recommendation,
Transition, Mood Change, Silence and Session Finished. Audience Experience is
parallel participant context rather than a Session Flow item or DJMoment. The
Flow tells the story of the evening while playback queues remain useful
infrastructure for people who need them.

## Current Session State

The primary DJ Session experience should remain intentionally simple. It
centres on current playback, playback controls, output device and one **Current
Session State** card.

That card represents the most relevant active Session item, most often a DJ
Moment. People can continue from it into the complete Session Flow whenever
they want to revisit or understand the wider story.

## The three dimensions of a DJ Session

Every DJ Session is defined by three independent runtime dimensions. Together
they describe the purpose of the occasion, its atmosphere and the way the DJ
performs. None is a shorthand for either of the others.

### Session Start Strategy — why does the Session exist?

A **Session Start Strategy** represents the listener's intent and defines the
objective with which the Session begins. It does not define the emotional
atmosphere.

- **Continue** resumes an existing DJ Session where continuity is available.
- **Manual** keeps the listener in control of the musical direction.
- **Discover** asks the AI DJ to actively help the listener discover music.

The Strategy initializes Runtime state and the initial planning approach. It
does not itself execute playback, define a queue or generate a DJ Moment.

### Session Mood — how should the Session feel?

**Session Mood** is selected independently from Session Start Strategy. It is
the emotional atmosphere of the active Session: for example Focus, Chill,
Party, Deep or Energy within the product's canonical mood model. A client may
choose the initial Mood when the Session starts, and the Planner may gradually
evolve it during the Session.

Mood influences Planner behaviour, Presentation Intent and the presentation of
future DJ Moments. It does not change the objective established by the Session
Start Strategy, and it never rewrites earlier Moments.

### DJ Persona — how should the DJ perform?

A **DJ Persona** defines how the DJ behaves: storytelling, interaction
frequency, tone of voice, humour and presentation style. Home DJ, Radio DJ,
Club DJ and Festival DJ are examples. Persona is independent from both Session
Start Strategy and Session Mood, and remains distinct from Voice.

Future Premium Cloud voices are implementations of Personas, not an
additional Session dimension.

### Independent combinations

The three dimensions deliberately compose without changing each other's
meaning:

| Session Start Strategy | Session Mood | DJ Persona |
| --- | --- | --- |
| Discover | Focus | Home DJ |
| Manual | Party | Festival DJ |
| Continue | Deep | Radio DJ |

These combinations describe different Sessions: a focused exploration led by a
warm Home DJ; a listener-directed party hosted by a Festival DJ; or a deep,
continuous session performed by a Radio DJ.

Future Premium Cloud experiences may add expressive voices, premium Personas,
richer storytelling, enhanced presentation and more advanced DJ behaviour.
These are experience extensions, not a replacement for the local-first DJ
Session.

## One Session across devices

Phone, Watch, Mac, Windows, television, Raspberry Pi, Voice and guest devices
all participate in the same DJ Session. Each device presents that Session in a
way appropriate to its capabilities and setting.

Presentation adapts to the device. The meaning of the Session, its Moments and
its Flow remains identical.

## Community, Personal and Future Premium Cloud

### Community

**Your AI DJ understands music.**

Community is the complete local-first DJ Session: musical understanding,
shared moments and a provider-neutral listening experience. It is never a
crippled trial.

### Personal

**Your AI DJ understands you.**

Personal makes the same DJ more personal through opt-in Music DNA and eligible
profile continuity. It remains profile-centric and must never expose private
history or personal reasoning in a shared session.

### Future Premium Cloud

**Your AI DJ has a recognizable personality.**

Future Premium Cloud may add expressive voices, premium DJ Personas, richer
storytelling, enhanced presentation and advanced DJ behaviour. It centres on
the quality of the hosted experience, not technical capability for its own
sake.

## Product language

Prefer language that describes a hosted DJ Session and its performance:

- AI DJ;
- DJ Session;
- DJ Moment;
- Session Flow;
- Current Session State;
- Music DNA; and
- shared or personal DJ experience.

Avoid leading with providers, APIs, WebSocket payloads, device/backend
mappings, AI modules or isolated feature names. The user is not assembling
software. They are sharing an evening with an AI DJ.

## Guiding principles

- The Session is the product.
- Playback is infrastructure.
- Everything the DJ intentionally does becomes a DJ Moment.
- The Session Flow tells the story of the evening.
- The AI DJ performs rather than reacts.
- Session Start Strategy answers why the Session exists.
- Session Mood answers how the Session should feel.
- DJ Persona answers how the DJ should perform.
- Session objective, atmosphere and DJ behaviour remain independent.
- Every device experiences the same Session.
- Presentation adapts to the device; meaning remains identical.
- The user is not controlling software. The user is sharing an evening with an
  AI DJ.
