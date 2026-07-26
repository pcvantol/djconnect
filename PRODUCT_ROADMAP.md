# DJConnect Product Roadmap

**Status:** Canonical Generation 2 product roadmap

## Product-maturity roadmap

This is the single active roadmap for DJConnect Product Development. It is
organized around product maturity rather than engineering mechanics. Every item
in the table below has this program as owner and uses exactly one canonical
status: Completed, Current execution, Planned, Deferred, Historical or
Retired. `ROADMAP_INDEX.md` owns cross-program navigation. Completed
foundations remain reference points, not active architecture work.

The public Community release defines the minimum lovable DJConnect product,
not the complete long-term product vision.

The roadmap governs product evolution. Platform implementations support the
product; they do not automatically determine product readiness.

### Phase 0 — Generation 2 Foundations

Completed: Product Definition, Product Philosophy Alignment, Capability
Architecture, Host Role Architecture, Raspberry Pi Platform Foundation and
Experience Foundation. These are durable authorities, not active roadmap work.

### Phase 1 — DJ Intelligence Evolution

**Current Product Initiative:** **DJ Intelligence Evolution** — establish the
minimum intelligence baseline required for the first convincing, canonical
DJConnect experience. It raises the existing context-aware Session planner
toward the intended AI DJ before that experience is frozen across renderer
surfaces. The repository-grounded evidence for this phase is
[`docs/product/DJ_INTELLIGENCE_CAPABILITY_REVIEW.md`](docs/product/DJ_INTELLIGENCE_CAPABILITY_REVIEW.md).

This is not a general AI research program and it does not reopen completed
foundations. Each candidate capability family must first be classified by its
current implementation maturity and by whether its gap is represented,
implicit or unrepresented in planning. The review identifies Knowledge
Strategy, bounded long-horizon/narrative planning, Audience Signals, Lyric
Intelligence and Performance Learning as candidate families; it authorizes none
of them automatically.

Automated Session Intelligence E2E Verification remains the current
engineering execution supporting this Product Initiative. It verifies existing
Session behaviour and does not itself define the product direction.

The built-in DJ Brain Capability Platform is current supporting architecture:
it constrains selection of existing trusted capabilities through Profile policy
and does not authorize new DJ Intelligence behaviour or alter the active E2E
workstream.

### Phase 2 — Reference Experience

Reference Experience begins only after the minimum DJ Intelligence baseline is
established. Its purpose is to design the canonical DJConnect experience around
the intended AI DJ rather than freeze renderer behaviour around today's
implementation. The Universal Receiver remains the first reference renderer;
it consumes the completed intelligence baseline and does not define it.

Every future user-facing slice in this phase follows:

```text
Experience Assessment → Experience Gap Analysis → Implementation → Experience Validation
```

This consumes `EXPERIENCE_FOUNDATION.md`; it does not recreate it.

The Reference Experience consumes the existing canonical renderer and
presentation boundaries: `docs/technical/RENDERER_HOST_CLASSIFICATION.md`,
`docs/technical/ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md`,
`docs/technical/AUDIO_RENDERER_HOST_ARCHITECTURE.md`,
`docs/technical/AMBIENT_LIGHT_RENDERER_HOST_ARCHITECTURE.md`,
`docs/product/VIBECAST_ARCHITECTURE.md` and
`docs/product/AUDIENCE_EXPERIENCE_ARCHITECTURE.md`. These references preserve
their established scope; this roadmap does not authorize their implementation.

| Phase | Initiative | Status | Dependencies |
| --- | --- | --- | --- |
| 0 | Product Definition and Community/Personal proposition | Completed | `docs/product/PRODUCT_DEFINITION.md` |
| 0 | Capability, Host Role, Pi and Experience foundations | Completed | `DJCONNECT_CAPABILITY_MODEL.md`, `HOST_ROLE_ARCHITECTURE.md`, `RASPBERRY_PI_PLATFORM_FOUNDATION.md`, `EXPERIENCE_FOUNDATION.md` |
| Historical | DJConnect V4 architecture and Runtime transition | Historical | `DJCONNECT_V4_COMPLETION_ROADMAP.md` |
| 1 | DJ Intelligence Evolution | Current execution | `docs/product/DJ_INTELLIGENCE_CAPABILITY_REVIEW.md`; completed Session Intelligence Runtime and existing maturity boundaries |
| 1 | Automated Session Intelligence E2E Verification | Current execution | `docs/product/DEVELOPER_EXPERIENCE_ROADMAP.md` |
| 2 | Universal Receiver Reference Experience | Planned | Minimum DJ Intelligence baseline; `docs/technical/UNIVERSAL_RECEIVER_ARCHITECTURE.md` |
| 2 | Renderer-safe Session experience and experience validation | Planned | Reference Experience assessment and existing renderer-safe projections |
| 2 | Interactive DJMoments capability family | Planned | Reference Experience; existing DJMoment, Planner, Knowledge, command/Ask DJ and renderer-safe Presentation boundaries; future assessment-first decision |
| 2 | Session Continuation capability family | Planned | Canonical DJMoment, active Session Runtime/Flow, Profile privacy and device-authorization boundaries, Renderer Host classification and a future assessment-first decision |
| Technical Design | Session Direction Projection | Planned | `docs/technical/SESSION_DIRECTION_PROJECTION_ARCHITECTURE.md`; dedicated Broadcast and renderer assessment before implementation |
| Technical Design | Sharing Experience | Planned | `docs/product/SHARING_EXPERIENCE_ARCHITECTURE.md`; user-initiated native Renderer Host assessment before any share implementation |
| 3 | Apple Premium Experience | Planned | Reference Experience, experience quality, polish, onboarding and release readiness for macOS, iPhone/iPad and Apple Watch |
| 3 | Apple Watch Moment-First Conversational Companion | Planned | Apple Premium Experience; CMB-07 Apple/Windows evidence; existing Watch companion evidence; active Session, privacy/device authorization and renderer-safe projection assessment |
| 4 | Public Release Readiness Assessment | Planned | Phase 3 evidence; it determines minimum public-release scope without authorizing features |
| 4 | Client Connectivity & Resilience qualification | Planned | endpoint, offline/cache and external HTTP qualification policy; no implementation authorization |
| 4 | HA Integration Onboarding & Configuration Experience Assessment (`HA-ONBOARDING-001`) | Planned | Client Connectivity & Resilience qualification; CMB-05/CMB-06/CMB-07/CMB-09 host-profile evidence; Profile, pairing and authorization architecture; Public Release Readiness context |
| 5 | Productization | Planned | Phase 4 assessment; no feature or paid-model commitment |
| 6 | Community Public Release | Planned | Productization and explicit release selection; complete local-first Community Edition |
| 7 | Desktop Platform Family | Deferred | First public Apple release; independent Platform Adoption assessment |
| 7 | Personal AI DJ evolution | Deferred | Community Public Release; existing Profile and Planner boundaries |
| 8 | Future Cloud evolution | Deferred | Long-term product direction; Community local-first foundation remains primary |
| Deferred | Ambient Light Renderer Host | Deferred | Universal Receiver maturity, Room Presentation Routing and real-hardware evaluation |
| Assessment | VibeCast release placement | Planned | Phase 3 decision: Community-defining Runtime Readiness or Platform-extending Platform Adoption |
| Deferred | Audience Experience and Ambient Reactions | Deferred | Audience validation, privacy policy and bounded renderer design |
| Deferred | Renderer discovery, pairing and authorization architecture | Deferred | Renderer Host classification and local-first device lifecycle requirements |
| Deferred | Voice experience delivery | Planned | Stable current/historical Moment contracts and Assist capability validation |
| Retired | Session Simulation and accelerated execution | Retired | A new approved time-dependent behavioral contract and separately authorized Pre-Flight would be required to revisit |
| 7 | Preferences and Music DNA expansion | Deferred | Existing Profile and Planner influence boundaries |
| 7 | Narrative Sequencing, Lyrics and Discover Evolution | Deferred | Existing Planner, Knowledge and DJ Moment Engine abstractions |
| Deferred | Audience Observation for Session Intelligence | Deferred | Audience Experience, privacy review and explicit bounded Planner-influence policy |
| Deferred | Playback Observation Stage 2 and Continue Stage 2 | Deferred | External Observation Boundary capability conditions |

### Interactive DJMoments capability family

**Status:** Planned Product Development capability family. It is assessment-first,
outside the current Execution Horizon, and authorizes no assessment,
implementation, Runtime extension or new DJMoment type.

Interactive DJMoments are ordinary, immutable DJMoments through the existing
canonical path:

```text
Knowledge Engine -> Planner -> DJMoment Engine -> Interactive DJMoment
-> Renderer Host -> user response -> existing command / Ask DJ route
```

This is not a second Runtime, interaction engine, Planner, renderer
architecture or Music Backend path. The Planner alone may later decide whether
an Interactive DJMoment is appropriate, which type is selected and when it is
presented. The Knowledge Engine supplies only existing approved contextual
possibilities; the DJMoment Engine retains Moment realization. A renderer
never creates a Moment, changes its meaning or treats a local response as a
planning decision.

The family is intended to increase engaged, natural participation in an active
DJ Session while the AI DJ retains Session ownership. It is not gamification,
scoreboards, achievements, a standalone quiz mode or an educational
application. Existing Trivia remains an ordinary possible DJMoment type; this
future family concerns only an explicitly planned, interactive presentation and
response boundary.

Future examples may include Quiz, Guess the Track, Prediction, Poll, Challenge
and Vote Moments. A future Quiz Moment must be Planner-originated and use only
existing Knowledge context for the current artist, album, genre, Session,
previous Moments/stories or Session Direction. It must not retrieve arbitrary
trivia or create a standalone quiz database.

Renderer Hosts remain free to present one approved Moment locally: for example,
Apple may use haptics, animation or confetti; Pi may use simple animation; and
Voice may use spoken feedback. Those presentation choices never select the
Moment or alter Planner policy. A future Moment may carry optional,
renderer-safe follow-up actions such as Play Now, Play Next, Open Album or Open
Artist only when the existing action/command boundaries already permit them.
The user must explicitly invoke any action through an existing command route;
the Music Backend retains all playback ownership and never changes
autonomously.

Interactive DJMoments must never project credentials, provider payloads, queue
information, Music DNA, Ask DJ history or internal Runtime identities. Any
future response remains within the existing renderer and command/Ask DJ
boundaries. Future adaptive consideration may assess bounded active-Session
signals such as participation, skips, preferred interaction type or difficulty,
but this registration authorizes no persistent learning, Performance Memory
extension or preference mechanism.

A later assessment may investigate suitable Moment types, Planner-selection
policy, approved Knowledge context, renderer presentation, bounded
Performance-Memory influence, optional playback-action projections and privacy
boundaries. Any delivery must be separately authorized, preserve the existing
canonical path and solve one bounded interactive Session problem.

### Session Continuation capability family

**Status:** Planned Product Development capability family. It is
assessment-first, outside the current Execution Horizon, and authorizes no
assessment, implementation, notification, push, APNs, Runtime, Planner,
DJMoment, preference, deep-link or playback change.

**Product purpose:** calmly, contextually and privately invite a user back to
an already active DJ Session when a relevant DJMoment or interaction is ready.
It is never marketing, a generic engagement push, a streak mechanism, an
attention-extraction reminder or a request to start a new Session.

The future responsibility chain is deliberately separate:

```text
Active DJ Session
  -> Planner selects or prepares a relevant DJMoment
  -> Continuation Opportunity
  -> Continuation Policy
  -> privacy-safe Notification Projection
  -> Platform Notification Renderer
  -> user opens the existing Session
  -> Renderer fetches current authorized content
```

The Planner alone may determine that a Moment or interaction is relevant to an
active Session. It does not decide interruption frequency, platform routing,
lock-screen content, notification permissions, quiet hours or consent. A
future **Continuation Opportunity** is session-scoped, temporary and coupled
to an existing or prepared DJMoment; it is not itself a notification and has no
schema yet. A future **Continuation Policy** exclusively decides whether that
opportunity may be presented externally. Its later evidence may include active
Session/current-Moment validity, recent user activity, prior invitations,
preferences and quiet hours, Profile privacy, host authorization, Session
Mood, DJ Persona, Moment type, personal/shared context and prior open/ignore
signals. This registration defines neither policy values nor frequency.

The Notification Projection is a minimal, privacy-safe invitation, never the
complete immutable DJMoment. A future payload may carry only an opaque
continuation reference, a safe general category, a short expiry and a renderer
route. It must exclude questions or answers, stories/insights, media or
provider references, playback commands, credentials, Profile data, Runtime
identities and Planner or Knowledge context. Visible content is category-only:
it must not reveal artist, track, album or playlist names; Session Direction;
Profile, room or device names; Music DNA; Ask DJ content; provider data; queue;
listening history; or free text from a DJMoment. Persona, Mood and response
style may later affect only a bounded safe copy catalogue; generative
notification copy is not authorized.

Platform Notification Renderers own only native presentation, delivery and
local user interaction inside those limits. Apple/APNs is transport and not the
capability owner. Product Development owns the Session Continuation experience;
Home Assistant Runtime retains active-Session status; Renderer Hosts retain
native presentation; and the Music Backend retains playback. A notification
never starts/resumes playback, changes a queue, activates Play Now or executes
an Ask DJ command. After opening, an ordinary Moment may still offer explicit
user actions only through existing command routes.

On opening, a future host must revalidate the active Session, opportunity
validity, profile/device and renderer authorization, Moment currentness and
consumption, and host eligibility. An expired or invalid opportunity may not
show stale content or fall back covertly: it goes safely to the current Session
or neutral status. Session Continuation exists only during an active Session;
it may not revive an ended Session, promote Discover content, start background
playback, automatically resume a Session or change Session Direction.

The family is independent of Interactive DJMoments. Interactive DJMoments
increase participation within a Session; Session Continuation invites a user
back to it. Either an Interactive DJMoment (for example Quiz, Prediction or
Poll) or a non-interactive Moment (for example Artist Story, Album Story,
Recommendation or Session Update) may later provide evidence for an
opportunity. Neither capability is the parent of the other.

Public delivery requires future opt-in or explicit configuration and a privacy
assessment of a master/per-profile/per-device control, permitted categories,
frequency, quiet hours, focus/sleep context, personal/shared profiles and
lock-screen privacy. The future policy must prohibit a fixed marketing cadence,
app-closed-only delivery, unbounded retries, multiple invitations for one
Moment, delivery after Session end, low-value Moments, interruption of an
already active participant, and retention or streak optimization.

A later **Session Continuation Capability Assessment** may examine existing
Planner and DJMoment evidence; opportunity lifecycle and ownership; policy,
consent, preferences and anti-spam limits; privacy-safe projections; safe
persona/Mood catalogues; deep links; expiry, consumption and revalidation;
Apple/APNs as one concrete renderer; shared profiles; content-free
observability; the independent Interactive DJMoments relationship; and release
and privacy qualification. Possible separately authorized follow-ons are a
Continuation Opportunity contract refinement, policy/consent model,
Notification Projection, deep-link/revalidation contract, Apple renderer
assessment, Apple privacy-safe push delivery, Interactive and non-interactive
reference slices, preference UX, and stale-opportunity recovery.

This family follows the existing DJMoment architecture, active Session Runtime
and Session Flow, Profile privacy/device authorization and Renderer Host
classification. Relevant native-surface/notification evidence and Public
Release Readiness plus privacy qualification are dependencies for any public
activation. It is not part of Native Surface Integration, even where a native
surface may later realize it, and does not change the current Execution
Horizon or any existing priority.

### Phase 3 — Apple Premium Experience

Apple is the first premium public implementation of the Reference Experience:
macOS, iPhone/iPad and Apple Watch are independently assessable Concrete Hosts.
This phase covers release polish, onboarding, release readiness and Experience
Qualification. It does not presume capability parity or add implementation
technology policy.

### Apple Watch Moment-First Conversational Companion

**Status:** Planned, assessment-first Product Development experience within
Apple Premium Experience. It is outside the current Execution Horizon and
authorizes no assessment, design finalization, watchOS/iPhone code, Runtime,
Planner, Knowledge, DJMoment, Broadcast, API, APNs, Profile or playback change.
No separate CMB identifier is introduced: this is a Phase 3 Apple Premium
Experience record, not a Platform Evolution capability-profile assessment.

**Product position:** Apple Watch is a moment-first, conversation-first
Concrete Renderer Host: a direct companion, compact DJMoment renderer,
micro-interaction surface and quick route to an active DJ Session. It is not a
Runtime or Session owner, Music Backend, configuration/Profile host, remote
control, Now Playing clone, playlist/queue editor, Session archive, full Ask
DJ chat client or miniature iPhone application.

During an active Session, the primary view is **Current DJMoment**. A later
experience assessment may qualify a bounded, renderer-safe active-Session card
stack through Digital Crown navigation and a separate compact Session
Projection:

```text
Current DJMoment <-> bounded active Session Flow cards
Current DJMoment <-> compact Session Projection
prominent action    -> Ask DJ Push to Talk
```

The stack is limited to a small, useful selection from the current active
Session; it is not Session History, an event log, unbounded scrolling or a
guarantee that every Flow record receives a Watch card. The assessment must
decide eligible Moment types, currentness, expiry/removal and the treatment of
Silence or technical records. The compact Session Projection may later use
renderer-safe current track, artist, artwork, playback state, Session Direction
and relevant Session Mood, with only a few explicit actions. Session Direction
is preferred context over queue detail. It is not a queue, playlist browser,
full iPhone Now Playing surface or future-track projection.

Without an active Session, **Ask DJ Push to Talk** is the sole primary
experience; no empty Flow, disabled Moment card, Now Playing view, history,
configuration or generic dashboard is shown. The future assessment decides
safe unavailable/unconfigured state copy. PTT remains a bounded request through
the existing Home Assistant STT and Ask DJ path, with an optional configured
speaker/authorized output and one compact current response projection. The
Watch has no local DJ Intelligence or presumed STT engine, retains no full Ask
DJ history and never starts a Session except through an already authorized Ask
DJ or Session Start Request contract. Input method, cancellation, timeout,
errors/retry, output selection, Watch-audio fallback, response length and
iPhone handoff remain assessment questions.

Apple Watch may later be a strong native Renderer Host for separately owned
Interactive DJMoments, such as Quiz, Poll, Prediction, Guess, Challenge or
Vote Moments. One-tap choices, haptics, bounded animation/confetti and explicit
follow-up actions are local presentation only; Planner, Knowledge and DJMoment
Engine retain content and intent ownership. It may also later render a small,
contextual set of **Audience Expressions** for a DJMoment. A user selection
must be sent as a stable semantic expression identifier, never a raw emoji;
emoji is merely Watch presentation. Audience Signals, any Performance Memory
effect and Planner influence remain separately deferred and require their own
ownership/privacy assessment. This is not a general like/dislike model.

**Lyric Moment** is a possible Watch-specific micro presentation only: one
meaningful lyric fragment with short DJ context, never a full-song lyric,
karaoke, synchronized/scrolled viewer or substitute for a music-provider lyric
surface. Any future Lyric Moment remains behind deferred Lyrics Knowledge and
must separately qualify rights, licensed source/fragment scope, interpretation,
timing and renderer-safe projection. This record does not promote Lyrics
Knowledge or authorize lyric delivery.

Existing renderer-safe DJMoment actions may later appear only as explicit
user-initiated controls (for example Play Now, Play Next, Open Album, Open
Artist or Continue on iPhone) through existing command routes. The Music
Backend retains playback; a Moment never executes a command autonomously, and
no provider object, credential, queue or backend identity is projected.

Session Continuation remains an independent capability. Apple Watch can later
be a presentation surface for a valid continuation invitation, but it does not
own an Opportunity or Policy. The default future posture is iPhone-targeted
APNs with platform mirroring where available, not an architectural requirement
for a separate Watch push channel. Opening must fetch/revalidate current
authorized Session content and never show stale material. WatchConnectivity may
be a transport or optimization; Home Assistant Runtime, not iPhone-local state,
remains canonical.

All Watch presentation remains renderer-safe: never Music DNA, Ask DJ history,
Profile-management data, credentials/tokens, internal Runtime identities, full
queue, sensitive notification content or shared-profile content without valid
device/Profile authorization. Lockscreen and notification content remain
content-neutral under Session Continuation privacy principles.

A future **Apple Watch Moment-First Companion Experience Assessment** may
inventory current watchOS evidence and gaps; define Current DJMoment, bounded
Flow cards/Crown navigation and compact Session Projection; qualify PTT/current
answer and active/no-active-Session states; examine Interactive DJMoment,
Audience Expression, Lyric Moment and explicit-action presentation;
continuation opening/revalidation and iPhone/Watch invalidation; accessibility,
battery, latency/network constraints and privacy. The current Watch companion
implementation is evidence for that assessment, not approval of its present UI
as this target experience.

Possible separately authorized delivery candidates include Current DJMoment
projection; bounded Flow cards; Crown navigation; compact Session Projection;
PTT capture/current answer; Ask-DJ-only inactive state; one Interactive Moment
renderer; contextual expression renderer; Lyric Moment renderer; explicit
action projection; continuation-open/revalidation; state invalidation; and
experience/accessibility qualification. Each remains separately assessed,
authorized and bounded, without a parity requirement.

This work follows CMB-07 evidence without requiring Apple/Windows parity, is
related but not owned by CMB-12 Native Surface Integration, and remains
independent of Interactive DJMoments, Session Continuation, Audience Experience
and deferred Lyrics Knowledge. Public Release Readiness later determines any
release-critical Watch scope. It must not begin before relevant Apple/host
profile evidence unless the canonical roadmap explicitly changes.

### Phase 4 — Public Release Readiness Assessment

This is an assessment phase, not a feature-delivery phase. It determines the
minimum additional work needed for first public release, which may include
onboarding, Session Timeline, minimal Music DNA, recovery UX, release quality
or documentation. It may also conclude that some are unnecessary. No work is
authorized until that assessment selects it.

### HA Integration Onboarding & Configuration Experience Assessment (`HA-ONBOARDING-001`)

**Status:** Planned assessment-first Product Development capability. It is not
in the current Execution Horizon and authorizes neither an assessment nor an
implementation before its recorded dependencies are available.

**Product question:** Can a new user without DJConnect knowledge independently
reach a first successful DJ Session from a Home Assistant installation, through
understandable choices, clear device instructions and recoverable errors?

Product Development owns the user journey. The Home Assistant integration owns
any later Config Flow, Options Flow and onboarding delivery. Platform Evolution
contributes only required pairing, connectivity, privacy and qualification
evidence; it does not own the experience or authorize a parallel platform
onboarding flow.

The future assessment covers the existing journey only:

```text
Add integration -> configure first Profile -> select and authorize a Music
Backend -> optionally qualify Assist/voice -> pair first app or device -> map
device to Profile -> safely start the first DJ Session
```

It must assess, without changing the present contracts:

1. **Initial setup happy path:** one first Personal Profile, one backend or
   account, one first app/device, safe defaults, advanced settings deferred to
   Options and an explicit ready-for-first-Session outcome.
2. **Profile onboarding and CRUD:** creation, update, deletion, Personal /
   Household / Guest / Kids roles, privacy mode, response style, fallback
   Profile, device mappings and understandable Profile-scoped Music DNA,
   preferences and Ask DJ continuity.
3. **Music Backend selection and Spotify OAuth:** Spotify Direct, Music
   Assistant, any supported deferred choice, prerequisites, switching,
   unsuitable-backend handling, OAuth callback/scopes/market/cancellation and
   reauthorization without exposing credentials or tokens. The Music Backend
   remains playback owner.
4. **Assist Pipeline and voice readiness:** existing-pipeline selection,
   absent-pipeline guidance, optional voice versus a non-voice happy path, and
   clear boundaries among STT, TTS, Conversation Agent, Assist satellite and
   announcement speaker. DJConnect never silently configures Home Assistant
   Assist outside existing Home Assistant contracts.
5. **Concrete-host onboarding:** Apple, Windows, Pi 4-inch, Pi 10-inch, ESP32
   and Voice Interaction Host instructions, only where their future profile
   evidence permits. It may assess version/compatibility, local-network,
   pairing start, pair-code or supported QR guidance, successful pairing,
   Profile mapping and recovery; it must not invent downloads, public
   distribution claims or a QR flow.
6. **Options and recovery UX:** clear separation of saving settings, Profile
   management, backend change, Spotify reauthorization, pairing retry/full
   repair, reassignment, fallback Profile and existing voice/announcement
   settings without exposing technical state or credentials.
7. **Language, accessibility, privacy and completion:** five-language product
   terminology and constrained-flow accessibility; no display or logging of
   refresh/install/device tokens, credentials, private Profile data, Music DNA,
   Ask DJ history or internal pairing/runtime identities. It must define
   evidence that a valid Profile, backend, paired/mapped host and optional voice
   readiness make a first Session safe to start, never automatic to start.

The assessment follows Client Connectivity & Resilience qualification and the
relevant CMB-05/CMB-06/CMB-07/CMB-09 host-profile evidence. It is a required
readiness input for Public Release Readiness Assessment and may inform later
Apple Premium Experience onboarding/polish; it does not move either phase or
change their priorities.

Possible later, separately authorized delivery slices are: Initial Setup Happy
Path; Profile Setup/CRUD UX; Music Backend prerequisite guidance; Spotify OAuth
and reauthorization UX; Assist Pipeline guidance; host-specific pairing
instructions; Options/Recovery information architecture; localized accessible
flow copy; and first-Session readiness feedback. Each must solve one bounded
user problem, preserve existing backend and ownership boundaries, and have its
own tests and authorization. No broad onboarding rewrite is implied.

For every capability requiring a renderer, the assessment determines whether
it is **Community-defining** or **Platform-extending**. Community-defining
capability is Runtime Readiness work because it is required for the Community
promise. Platform-extending capability is Platform Adoption work because it
extends reach without changing that promise. Renderer implementation alone
never determines roadmap placement.

VibeCast is an explicit assessment decision: does Community v4.0 fulfil its
product promise without VibeCast? If yes, VibeCast remains Platform Adoption
work. If no, it becomes Runtime Readiness work through the Universal Receiver
renderer. This roadmap does not predetermine the outcome.

### Runtime Readiness — Community Public Release gate

Runtime Readiness is the minimum functional completeness required before
Community Public Release. It is a release gate owned by Home Assistant, the
sole Runtime Host, and determines whether the Community product promise can be
fulfilled independently of any one renderer.

Its evidence covers the existing Session Runtime, Planner, Knowledge, DJMoment,
Presentation, Broadcast, Ask DJ, Track Insight, Discover, Session Memory,
capability contracts, pairing and APNs support where required for Apple. This
is a release-readiness classification, not a new capability or implementation
commitment.

### Phase 5 — Productization

Productization prepares DJConnect to become a public product. It may assess
and select bounded work in these categories:

- distribution: TestFlight strategy, internal testing, external beta and a
  release-candidate process;
- App Store readiness: metadata, screenshots, categories, review notes and
  marketing assets;
- platform readiness: supported iOS/macOS versions and devices, unsupported
  devices, and accessibility review;
- release engineering: signing, certificates, notarization, CI/CD, App Store
  Connect and Mac App Store preparation;
- compliance: privacy review, entitlements, legal texts and licenses; and
- product operations: support mailbox/procedures, ticket intake, release notes
  and localization approval.

Commercial readiness is assessment only. It may examine a Community-only
launch, StoreKit readiness, subscription feasibility and migration strategy.
No paid model is authorized, and the assessment may conclude that the first
public release remains Community-only.

### Phase 6 — Community Public Release

This is the first public product milestone: a complete Community Edition that
is local-first, requires no cloud account, is not a trial and is not a reduced
product. Apple is its first public consumer implementation and premium
reference, without becoming product or Runtime owner. Only work explicitly
selected by the Release Readiness Assessment and Productization is implemented;
Personal capabilities are not automatically included.

### Independent Platform Adoption

Platform Adoption is the independent, non-release-gating stream that brings
the completed Runtime to additional Concrete Hosts when it does not block the
current product milestone. It includes Raspberry Pi, ESPHome Voice, the
Desktop Platform Family, Website, Universal Receiver renderer and ESP32.

Apple remains the first public consumer product and the premium reference
implementation of the Community product; it does not own the product or
Runtime. The current Desktop Concrete Host is Windows and follows the first
public Apple release. A future Linux host requires its own assessment; no
implementation technology decision is introduced.

### Phase 7+ — Long-term evolution

Personal AI DJ evolution follows Community Public Release. Future Cloud capabilities are
long-term and extend the same local-first AI DJ; neither defines the minimum
lovable product.

The retained material after this section is **Historical** pre-Generation 2
product and release memory. It is not an active roadmap, does not establish
current ownership, priority, pricing or implementation commitments, and must
not be used to bypass the table above.

Innovation Lab is the source of potential future product candidates. A
candidate appears in this roadmap only after an explicit GO and promotion
decision; its receiving Product Development record then has a new owner and a
new `Planned` or `Backlog` status.

## Session Intelligence Runtime milestone

The Session Intelligence Runtime Integration Epic is complete. The server now
uses one canonical Runtime lifecycle for every supported Track Started decision:
Planner selection, Knowledge resolution, DJ Moment realization, Session Flow
publication and Broadcast distribution. The legacy Track Started path is only
bounded runtime protection for lifecycle failure.

Future intelligence capabilities extend the existing Planner, Knowledge Engine
and DJ Moment Engine abstractions; they do not create another Runtime pipeline.
The active roadmap now moves from runtime-architecture construction to DJ
Intelligence Evolution. Universal Receiver V1 has an operational foundation;
**Automated Session Intelligence E2E Verification** is the current supporting
engineering Epic. Its Architecture and the first bounded Developer Session
Bootstrap, Deterministic Scenario Driver, Immutable E2E Session Capture and
Structural Invariant Validator, Qualification Policy and Verification Clock
Architecture are complete. `SI-GOLDEN-001` through `SI-GOLDEN-003` are
executable and structurally verifiable; CI Smoke Suite is next.
Audience Intelligence remains deferred and is not an active priority.

Canonical product roadmap for all DJConnect repositories. This file lives only
in the Home Assistant integration repo `pcvantol/djconnect` and is the leading
product roadmap for:

- `pcvantol/djconnect`
- `pcvantol/djconnect-app`
- `pcvantol/djconnect-esp32`
- `pcvantol/djconnect-windows`
- `pcvantol/djconnect-website`
- `pcvantol/djconnect-pi`
- `pcvantol/djconnect-api`

This roadmap is broader than `TODO.md`: not every idea here is committed scope.
Use it to shape releases, validate demand and decide what belongs in the free
local/Home Assistant product versus optional premium features.

Product Strategy lives in `docs/product/PRODUCT_STRATEGY.md`. The Generation 2
table above is the active Product Development roadmap; the retained sections
below are pre-Generation 2 product and release memory only. Innovation Labs
remain the canonical home for unvalidated product ideas.

## Product Proposition

DJConnect. Muziekbediening met karakter.

Core promise:

- Fast physical music control without opening a phone.
- Natural voice-driven music requests through Home Assistant Assist.
- A calm now-playing experience for shared living spaces.
- Local-first control, with Home Assistant owning backend credentials.
- One shared backend contract across ESP32 hardware, Apple clients, Raspberry
  Pi/Linux clients, Windows client and the website/docs experience.

## Release Cycle Rule

Every release must review this roadmap.

- Update `pcvantol/djconnect/PRODUCT_ROADMAP.md` even when the release or
  product change originates in another DJConnect repo.
- Do not keep repo-local `PRODUCT_ROADMAP.md` copies in sibling repos. If a
  sibling repo contains one, remove it and reference the canonical HA repo file
  instead.
- Move implemented items from unchecked to checked in the relevant category.
- Add the implementing major.minor version in parentheses, for example
  `[x] Queue supports up to 100 items (3.1)`.
- If an item ships only for one client, mark the client explicitly, for example
  `[x] ESP32 screenshot endpoint (3.1, ESP32)`.
- Do not remove shipped ideas immediately; keep checked items as product memory
  until a later roadmap cleanup.
- Update README, changelog, handoff, fresh-chat bootstrap prompt, tests and
  design decisions when a roadmap item changes product behavior or public
  contract. Cross-repo contract changes belong only in
  `pcvantol/djconnect/SYNC_PROMPTS.md`.

## Production Release Must-Haves

### General Product Development

- [x] Stable `3.2.x` client/integration compatibility policy, with clear
  major.minor mismatch errors and no automatic token wipe.
- [x] Redacted diagnostics for support without bearer tokens, Spotify tokens,
  WiFi passwords, Home Assistant tokens or temporary media URLs.
- [ ] Clear error states for unpaired, stale token, backend unavailable, version
  mismatch, Home Assistant unreachable, STT failed and TTS failed.
- [ ] Release hygiene across all repos: docs, changelog, handoff, technical
  design decisions, canonical roadmap, tests and cleanup reviewed before every
  release; cross-repo sync prompts are reviewed only in
  `pcvantol/djconnect/SYNC_PROMPTS.md`.
- [ ] Public download/update path for every released client.
- [ ] Manual smoke checklist for website, Home Assistant integration, ESP32,
  Apple clients, Raspberry Pi client and Windows client.

### HACS / Home Assistant Integration

- [ ] Stable HACS installation path with polished icon, description, website
  link, README rendering and restart/repair text.
- [ ] Robust Spotify OAuth refresh-token rotation without normal playback repair
  loops.
- [ ] Clear Spotify Direct Premium/Developer-app requirement, Music Assistant
  alternative and resilient Spotify reauthorization flow.
- [ ] Reliable Assist STT/TTS setup guidance and diagnostics.
- [ ] Stable entity model per client type:
  ESP32 hardware entities, app-like client runtime entities and backend/playback
  entities without irrelevant controls.
- [ ] HA sensors stay stable after status sync and do not fall back to unknown
  after initial valid values.
- [x] Split transport/pairing model where ESP32/Raspberry Pi stay local-device
  clients and iPhone/iPad, Apple Watch, macOS and Windows become inbound-only remote-capable app clients
  after local pairing (3.2, HA/client contract).
- [x] Add an internal DJConnect use-case layer and Spotify Direct backend
  adapter boundary so migrated command, Ask DJ, processor and entity paths no
  longer call Spotify helpers directly (3.2, HA).
- [x] Add a small Music Assistant backend adapter behind the DJConnect use-case
  layer without rebuilding provider registries, universal library search,
  queue/grouping engines or Music Assistant setup flows (3.2, HA).
- [x] Add an explicit Home Assistant options-flow action to switch between
  Spotify Direct and Music Assistant without removing the integration, while
  preserving pairing/history/memory and bumping `music_backend_revision` (3.2,
  HA).
- [x] Harden backend/client contracts with backend summary fields, backend-aware
  playback actions, stale-action rejection and unsupported capability errors
  for client implementation prompts (3.2, HA).
- [x] Add HA/AI tool surfaces as thin wrappers over DJConnect use-cases, never
  as direct Spotify or Music Assistant calls (3.2, HA).
- [ ] mDNS pairing plus manual Client adres fallback for ESP32/Raspberry Pi
  networks where Bonjour is filtered, stale or unavailable.
- [x] Queue/up-next response returns max 100 real backend items, artwork URLs,
  context URI and no artificial duplicate padding (3.2, HA).
- [x] Ask DJ server-side chat history sync supports bounded history,
  cross-device clear, retention metadata and client cache trimming (3.1, HA).
- [x] Ask DJ supports confirmation-style follow-up actions with Ja/Nee buttons
  and server-side pending follow-up execution (3.1, HA).
- [x] Ask DJ supports morning startup suggestions from listening memory and
  sleep phrases that pause playback (3.1, HA).
- [x] Ask DJ recommendations can return Play Now actions with artwork without
  mutating playback until explicit confirmation (3.1, HA).
- [x] Ask DJ hardened fallback handles gibberish and prompt-injection-like
  requests without playback mutation or prompt disclosure (3.1, HA).
- [x] Ask DJ recent-played questions return read-only track, album, artist and
  playlist-context lists with art/icon metadata from Spotify recently played
  data (3.1.77, HA/client contract).
- [x] Keep backend playback state out of separate Home Assistant playback
  entities; clients, Ask DJ and DJConnect commands own playback UX while HA
  remains the credential/backend orchestrator (3.2, HA).
- [x] Add a premium-ready VibeCast backend feed for Apple clients, with macOS
  and iOS sharing the same endpoint, response contract, item kinds, disabled
  reasons, structured text model and polling/cache semantics (3.2, HA/client
  contract).
- [x] Last STT text, resolved Spotify result, DJ announcement and last track are
  visible through focused entities or redacted status/debug attributes, without
  low-value standalone command/STT sensors (3.2, HA).
- [ ] DJ announcement prompt is configurable, multiline and isolated from
  Spotify search/device lookup prompts.
- [x] DJConnect is exposed as a Home Assistant Assist conversation agent for
  Assist satellites such as Voice Preview Edition, with compact relevant
  options (3.1, HA).
- [x] ESP32 wake-word toggle is exposed as a native HA switch and filtered out
  for iOS, macOS, Raspberry Pi and Windows clients (3.1, ESP32/HA).
- [x] DJ announcement generation includes the concrete Spotify track returned
  by the just-executed artist playback command when Spotify provides one (3.1,
  HA).
- [x] End-to-end and contract tests cover pairing, voice/PTT, HA STT provider
  compatibility, Spotify search, queue, refresh-token rotation, mDNS discovery,
  non-ESP entity filtering, backend switching and OTA offers (3.2, HA).

### Website / Docs

- [ ] Canonical domain, SEO metadata, sitemap, redirects and social preview are
  current.
- [ ] Setup page remains the single source for installation guidance.
- [ ] Compatibility matrix for ESP32, iOS, macOS, Raspberry Pi/Linux, Windows
  and Home Assistant versions.
- [ ] Troubleshooting pages for Spotify OAuth, STT failed, TTS failed, mDNS
  discovery, Client adres, OTA and pairing reset.
- [ ] Product screenshots/videos show PTT, queue, DJ announcement, hardware UI
  and Home Assistant entities.
- [ ] Privacy notice accurately describes website and product behavior.
- [ ] Aggregate download/HACS counters remain cookieless.
- [ ] Link checker, translation coverage and Playwright smoke checks run in
  release validation.

### ESP32 Firmware

- [ ] Stable Home Assistant pairing with model-specific device IDs,
  `client_type=esp32`, mDNS discovery, pairing token storage and stale-pairing
  recovery.
- [ ] OTA reliability with board-specific firmware selection, SHA256
  verification, low-memory handling, useful progress/errors and safe reboot.
- [ ] Wake-word and PTT reliability: Okay Nabu false positives/misses, silence
  auto-stop, WAV capture quality, STT failure handling and DJ-announcement
  playback.
- [ ] Playback command reliability from device, web and HA: play/pause,
  previous, next, volume, shuffle, repeat, output transfer, standard playlist
  and queue item playback.
- [ ] Power and battery stability: no low-battery flicker, predictable
  charging/deep-sleep behavior and first input after screen-off only wakes the
  display.
- [ ] Web portal polish: mobile layout, album art popover, queue refresh, games,
  settings, diagnostics and OTA upload in the DJConnect blue/purple style.
- [ ] LilyGO T-Embed S3 builds, manifests, docs and OTA selection remain in
  lockstep.
- [ ] Serial/web logs remain atomic, searchable and useful for support.
- [x] Up Next stores and renders up to 100 queue items from Home Assistant
  before local truncation (3.1, ESP32).
- [x] Local debug screenshot and screen-open endpoints support automated screen
  capture in development firmware (3.1, ESP32).

### Apple Clients: iOS / macOS

- [x] Stable inbound app pairing through Home Assistant with one persistent
  device ID per installation and no client-hosted local API requirement (3.2,
  iPhone/iPad, Apple Watch, macOS and Windows contract).
- [ ] Clear LAN pairing and remote URL guidance.
- [ ] Current playback, queue, DJ announcement and status views match the shared
  Home Assistant contract.
- [ ] App-side diagnostics copy/export with redaction and issue-template links.
- [ ] Demo mode remains local and does not create Home Assistant devices.
- [ ] App Store/TestFlight readiness checklist for permissions, privacy copy,
  onboarding and failure states.

### Raspberry Pi / Linux Client

- [ ] Stable pairing with persistent `djconnect-raspberry-pi-XXXXXXXXXXXX`
  device ID.
- [ ] mDNS advertisement and pairing-info endpoint for HA discovery.
- [ ] Kiosk/full-screen now-playing wall display with album art, queue and DJ
  announcement.
- [ ] Touch/mouse/keyboard input model for playback, queue and settings.
- [ ] Capability reporting so HA does not require unsupported local audio,
  voice or DJ-response endpoints.
- [ ] Safe startup service, update flow and diagnostics for unattended displays.

## Killer Features

### General

- [ ] Natural music request to real playback: artist, track, album, playlist,
  mood and intent start on the right output.
- [ ] Personal DJ announcements based on resolved music metadata and the user's
  custom DJ prompt.
- [ ] One Home Assistant hub, many clients: ESP32, iOS, macOS, Raspberry Pi,
  Windows and website/docs share one pairing and protocol model.
- [ ] Privacy-first local control: no DJConnect account required for core use.
- [ ] Personal music memory for preferred artists, disliked results, common
  playlists and announcement style.

### HACS / Home Assistant

- [ ] Setup health check screen: Spotify Premium, OAuth, STT, TTS, playback
  device, mDNS and client reachability in one place.
- [ ] Built-in test wizard: STT test, TTS test, Spotify play test, DJ
  announcement test and pairing callback test.
- [ ] Routine hooks for Home Assistant automations when music is requested,
  playback starts, output changes or DJ announcement is generated.

### Website / Docs

- [ ] Guided "How to start" wizard with exact HACS repo, Spotify Premium
  requirement, HA Assist setup and client pairing steps.
- [ ] Release-aware update dashboard showing latest integration/client/firmware
  versions and compatibility.
- [ ] Public product demo with screenshots and short videos per client.

### ESP32 Firmware

- [ ] Always-listening "oke nabu" with local wake-word detection, LED/listening
  feedback and no cloud wake-word dependency.
- [ ] Room-aware hardware remote: one-touch output transfer to known rooms with
  remembered preferred output.
- [ ] Standard playlist button starts configured playlist, enables shuffle and
  disables repeat.
- [ ] Local visual personality: animated splash, LED ring states, game LED
  feedback, DJ-announcement ring and battery/charging states.
- [ ] Smart queue view with album art, per-item play, refresh and no fake
  duplicated current tracks.

### Apple Clients

- [ ] iOS widgets for quick playback, voice request and current track.
- [ ] macOS menu bar mini remote.
- [ ] Continuity-friendly handoff between Mac/iPhone/iPad and room devices.
- [ ] Voice/debug replay UI for the last WAV/STT/TTS response where HA exposes
  safe debug media.
- [x] Ask DJ chat consumes server-side history, clear revisions, retention
  metadata, Play Now actions and confirmation actions from the HA backend
  contract (3.1, iOS/macOS/watchOS/Raspberry Pi/Windows). ESP32 intentionally stays
  outside Ask DJ chat/history.

### Raspberry Pi / Linux

- [ ] Shared now-playing wall: cover art, current track, next item, clock and DJ
  text for living-room display.
- [ ] Party display mode with guest QR code, queue and host moderation status.
- [ ] HyperPixel/kiosk themes optimized for wall-mounted displays.

## New Feature Ideas

### General Product Development

- [ ] Configurable standard playlist from HA, web portal, Apple client and
  device menu.
- [ ] DJ modes: concise, enthusiastic, radio host, kid-friendly, Dutch/English
  mixed or no-spoken-announcement.
- [ ] Party mode with locked simple controls, high brightness, persistent queue
  and limited settings access.
- [ ] Quiet hours to dim screens, lower cue volume and suppress non-critical
  sounds.
- [ ] Accessibility mode with bigger text, reduced animation and high contrast.
- [ ] Listening history with replay or add-to-playlist actions after an
  explicit user confirmation.
- [ ] Multi-room scene buttons for cooking, dinner, party, focus and sleep.
- [ ] Typed music search in clients: search by album, artist or track name from
  ESP/web, Apple, Raspberry Pi and Windows clients, then let Home Assistant resolve and
  start the selected result through the shared backend playback contract.

### HACS / Home Assistant

- [x] Expanded Dutch/English local fallback parser for explicit artist, track,
  album, playlist and default-playlist commands (3.1, HA).
- [x] Guarded post-STT fuzzy correction for likely English artist, track,
  album and playlist recognition mistakes before Spotify intent parsing
  (3.1, HA).
- [ ] Parsed intent debug attributes: media type, query, artist, title,
  playlist, market and Spotify result.
- [ ] Correction/follow-up commands: "niet deze", "de live versie", "meer zoals
  dit", "speel het album hiervan".
- [ ] Search result disambiguation when Spotify returns weak matches.
- [ ] Artist radio fallback when direct artist start is unavailable.
- [ ] Playlist name search across user playlists first, then public playlists.
- [ ] Repair issues for missing STT provider, missing TTS provider, missing
  Spotify Premium/device and invalid Client adres.
- [ ] Optional persistent debug history with last N requests, redacted by
  default.
- [ ] More granular sensors for backend health, client health and Spotify auth
  state.
- [ ] HA automation blueprint pack for low battery, startup, pairing issues, DJ
  response errors, OTA notifications, parties and quiet hours.

### Website / Docs

- [ ] Dedicated troubleshooting pages for common support logs.
- [ ] Product architecture page explaining local-first design and where secrets
  live.
- [ ] Download/release page with board-specific firmware and app links.
- [ ] Support intake page that points users to redacted diagnostics.
- [ ] Roadmap page generated from this canonical file or a curated subset.

### ESP32 Firmware

- [ ] Favorite outputs pinned above live output discovery.
- [ ] Queue search/filter in the web portal for long queues.
- [ ] Album art cache controls: size, clear cache and age/count cap.
- [ ] One-click web UI to capture all screens and download a zip/contact sheet.
- [ ] Hardware self-test for display, buttons, encoder, speaker, mic, LED ring,
  WiFi and battery.
- [ ] Guided captive setup wizard for WiFi, HA pairing, language, brightness and
  speaker cue volume.
- [ ] Voice debug tools showing last WAV duration/size, STT text, TTS URL status
  and provider error body.
- [ ] Offline-friendly setup screen with QR/deeplink to HA integration
  instructions.
- [ ] Better battery, charging and OTA safety telemetry.

### Apple Clients

- [ ] Local demo mode metadata with clear "not connected to HA" boundaries.
- [ ] Client-side "can Home Assistant reach me?" indicator.
- [ ] Queue editor: reorder, remove or pin upcoming tracks when backend support
  is available.
- [ ] Rich album art popover and lock-screen/current-track affordances.
- [ ] Share diagnostics into GitHub issue template.
- [ ] Apple Watch request/cancel controls.

### Raspberry Pi / Linux

- [ ] Safe local update service and rollback instructions.
- [ ] Configurable display themes and burn-in protection.
- [ ] Touch-first queue and output switcher.
- [ ] Offline fallback screen with pairing recovery steps.
- [ ] Local logs/diagnostics page for kiosk deployments.

## Premium / Paid Feature Candidates

Premium ideas should add convenience, polish or optional hosted services while
keeping the core local/Home Assistant experience useful without payment.

### General Premium

- [ ] Advanced DJ personalities with curated style packs, multi-language voices,
  seasonal themes and custom prompt presets.
- [ ] Household profiles with per-user music preferences, language, family-safe
  rules and announcement tone.
- [ ] Smart music memory: favorite artists by room/time, request history,
  negative feedback and "more like this" suggestions.
- [ ] Advanced analytics: privacy-preserving request summaries, room usage,
  top artists and client usage.
- [ ] Remote support mode with time-limited, opt-in diagnostics sharing.
- [ ] Priority support, setup review or assisted onboarding.

### HACS / Home Assistant Premium

- [ ] Advanced automation recipe pack for parties, dinner, bedtime, wake-up
  music, quiet hours and scenes.
- [ ] Cloud-assisted diagnostics bundle with redacted setup health report.
- [ ] Hosted release/update dashboard for installed client versions and firmware
  readiness.

### Website Premium

- [ ] Account-backed optional theme/personality downloads.
- [ ] Support dashboard for premium users.
- [ ] Hosted guest request pages, only when privacy model is explicit.

### ESP32 Premium

- [ ] Premium LED/screen themes, animated idle screens and seasonal packs.
- [ ] Hardware bundle provisioning/support flow.
- [ ] Advanced local self-test and support bundle export.

### Apple Client Premium

- [ ] iOS widgets, Apple Watch controls and macOS menu bar extras.
- [ ] Premium queue editing tools and saved queue templates.
- [ ] Cross-device sync for DJ persona/profile settings.

### Raspberry Pi / Linux Premium

- [ ] Premium wall-display themes.
- [ ] Multi-display orchestration for synchronized rooms.
- [ ] Party-mode display with guest voting/moderation.

## Free vs Paid Guardrails

- Core pairing, local control, Home Assistant integration, basic PTT, basic DJ
  announcement and essential entities remain free.
- Paid features must not require DJConnect to collect Spotify credentials.
- Paid features should be optional enhancements, not mandatory infrastructure
  for local control.
- ESP32, Apple and Raspberry Pi/Linux clients remain usable with the free Home
  Assistant integration.
- Any hosted premium service needs a clear privacy model before implementation.
- Premium must not weaken the local-first default experience.

## Parking Lot

- [ ] Support future playback providers beyond Spotify through the generic HA
  playback command proxy.
- [ ] Local non-cloud LLM/DJ announcement generation if HA exposes a reliable
  local model path.
- [ ] Signed firmware manifests.
- [ ] Hardware bundle SKU planning.
- [ ] White-label hardware provisioning process.
- [ ] App Store/TestFlight production-readiness scope.
