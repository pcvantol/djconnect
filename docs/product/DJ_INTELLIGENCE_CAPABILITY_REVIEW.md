# Repository-Grounded DJ Intelligence Capability Review

**Status:** Discovery and planning evidence, 2026-07-25. This report changes
no Runtime behaviour, capability ownership, API, product behaviour or roadmap
priority. It is not a new capability definition or an implementation plan.

## Method and authority

This review uses the current repository as its authority. The primary canonical
sources are the Product Definition, Capability Model, DJ Intelligence
Architecture and Maturity Model, Session Runtime and Horizon records, product
roadmap, Experience Foundation and Generation 2 reconciliation. The V4
completion roadmap is used only as historical transition evidence.

Implementation evidence was inspected in `session_runtime.py`,
`playback_observation.py`, `track_insight.py`, `music_dna.py`,
`music_discovery.py` and the associated Session Runtime, Track Insight, Music
DNA, Discovery, Playback Observation and presentation tests. A status in this
report therefore means **currently evidenced in this repository**, not a
promise of cross-platform Experience Qualification.

## Executive finding

DJConnect already has a real, server-owned Session Intelligence pipeline. For
an eligible observed track it can establish a Runtime, create a bounded
fifteen-minute rolling planning workspace, select one safe semantic intent,
assemble bounded Track Insight context, create an immutable DJMoment, append
it to Session Flow and publish renderer-safe projections. It can vary that one
decision by Start Strategy, Mood, Persona, Direction, Discover context and
Runtime-scoped Performance Memory.

It is not yet an autonomous long-horizon narrative DJ. Future slots are
currently silence-capable unless safe current-track context yields one
candidate; the implementation does not obtain a provider's upcoming playback
projection, control a queue, maintain a cross-track story, intentionally
schedule a future fact for later delivery, or learn a performance policy across
Sessions. Knowledge is deliberately bounded to Track Insight/provider metadata
and permitted personal context. Audience input is session-scoped presentation
state, not an intelligence input. Lyric acquisition and musical timing do not
exist.

## 1. Current DJ Intelligence

| Dimension | Implemented evidence | Boundary / not evidenced |
| --- | --- | --- |
| Understands | Safe current playback identity and Track Insight fields; artist, album, genre, production and related-work hints; Start Strategy, Mood, Persona, Direction, Discover context and Performance Memory. | No lyrics, structural song timing, external editorial/music-history retrieval, concert source, listener identity in shared output, or queue truth. |
| Plans | One deterministic intent through `Runtime -> Planner -> Knowledge Engine -> DJMoment Engine -> Session Flow -> Broadcast`; a rolling, Runtime-scoped planning window; prefetch readiness and invalidation; narrow Transition and Session Update policies. | No autonomous session strategy, multi-track narrative, provider queue control, persistent plan or generalized replanning policy. |
| Remembers | Current Session Flow and bounded Performance Memory; persistent Session lifecycle/history projections; opt-in Profile-owned Music DNA; revisioned Ask DJ history. | Planner working state, prefetch results and Performance Memory end with Runtime; raw prompts/audio and full listening history are excluded. |
| Presents | Immutable Track, Artist, Album, Genre, Recommendation, Transition, Session and Silence DJMoments; Presentation composition, Broadcast and renderer-safe Flow/playback projections. | No implemented Lyric, Concert, History, Audience or Discover DJMoment; renderer hosts do not own planning or facts. |
| Adapts | Mood/Persona/Direction can affect the next safe choice; Discover changes priority; Performance Memory avoids immediate repetition and supports narrow silence recovery. | No audience adaptation, emotional arc, learned pacing, feedback-driven replanning, or cross-session performance learning. |

The Capability Model records the Runtime, Planner, Knowledge intent resolution,
immutable DJMoment creation and Session Flow as implemented (`CAP-SI-02` through
`CAP-SI-06`). This establishes stable ownership, not completion of every
intelligence maturity stage.

## 2. Planning-horizon assessment

| Planning ability | Status | Repository evidence |
| --- | --- | --- |
| Choose the next semantic contribution | Implemented | `DJSessionPlanner.evaluate_track_started` and `PlanningRuntimeCoordinator` select and realize one safe intent. |
| Maintain a bounded future planning workspace | Implemented | `RollingSessionHorizon`, `PlanningWindow`, planned intents, readiness evaluation and invalidation are Runtime-scoped. |
| Plan across multiple observable tracks | Partial | Data structures accept `UpcomingPlaybackProjection`; current observer is Stage 1 current-track-only and supplies no upcoming entries, so future slots remain silence-capable. |
| Cancellable future knowledge preparation | Implemented | `KnowledgePrefetch`, readiness and `PreparedKnowledge` are generation-bound and invalidated/superseded safely. |
| Narrative sequence across Moments | Planned | Maturity `ME-4.1` and `PL-4.2` are gated; no semantic sequence contract exists. |
| Intentionally delay a fact to a musically chosen point | Absent | There is no musical structure/timing input, lyric timing or delayed-delivery policy. |
| Replan on normalized playback change | Partial | Horizon can replan on input change; live Stage 1 only observes Spotify current media identity and does not provide robust occurrence correctness or future context. |
| Adapt plans from feedback/audience | Deferred | Architecture explicitly excludes Audience Events from Planner input; no approved coarse observation exists. |
| Long-term performance optimization | Planned | Maturity Stage 4/5 only; Performance Memory is ephemeral and Music DNA is personal context, not Planner performance learning. |

## 3. Planner input matrix

| Input | Source / lifetime | Owner and privacy | Current use | Evidence / status |
| --- | --- | --- | --- | --- |
| Session Start Strategy | Authorized Session start; active Runtime | HA Session Runtime; operational | Initializes objective and Direction: Manual, Discover or Continue. | Implemented; `SessionStartStrategy`, start handling and maturity model. |
| Session Mood | Session start/client context; active Runtime | Runtime; session/personal as applicable | Affects priority, silence and Presentation Intent. | Implemented. |
| DJ Persona | Session start/client context; active Runtime | Runtime; session/personal as applicable | Affects performance profile, silence and delivery semantics. | Implemented. |
| Session Direction | Runtime-owned active state | Runtime; renderer-safe projection | Affects intent priority; narrow Session Update policy may revise it. | Implemented. |
| Current Playback Projection | Spotify Direct Stage 1 observer | Observation boundary; renderer-safe | Track Started eligibility and current-track planning. | Implemented, bounded; not occurrence-correct Stage 2. |
| Upcoming Playback Projection | Optional normalized model | Observation boundary; ephemeral | Can populate future slots and cap planning window. | Partial: model/runtime support exists, no current provider producer. |
| Track Insight hints | Track Insight service | HA Insight service; renderer-safe selected fields | Supplies safe intent-relevant evidence. | Implemented. |
| Discover context | Permitted Music DNA projection | Runtime/Profile; personal and opt-in | Avoids familiar artists/genres and favours exploration. | Implemented and bounded. |
| Performance Memory | Realized Flow/Moments; Runtime lifetime | Runtime; ephemeral/non-personal | Repetition avoidance, spacing, narrow silence recovery and Transition guard. | Implemented. |
| Session Memory / persistent Session | Session lifecycle and historical projections | Persistent Session owner; authorized history | Historical record and context boundary. | Partial Planner input: current Planner uses Runtime Flow/Performance Memory, not durable history as a general input. |
| Music DNA | Opt-in Profile snapshots | Profile platform; personal/opt-in | Discover context and Ask DJ/profile experience; bounded personalization. | Implemented as personal context; not demonstrated as broad Planner learning. |
| Ask DJ conversation state | Revisioned server history/pending follow-up | Conversation platform; personal | Conversation responses and follow-ups. | Implemented; no evidence it directs the Session Planner. |
| Recommendation state/feedback | Discovery recommendation interactions | Profile platform; personal/opt-in | Compact positive/negative discovery feedback and explicit play actions. | Implemented; no Session Planner consumption evidence. |
| Audience Signals | Session-authorized receiver signal endpoint | Runtime/Broadcast; session-scoped | Counts and recent activity are published as audience projection. | Implemented as projection only; no Planner decision, Playback, Memory or Music DNA use. |
| Playback behaviour (skip/replay) | No canonical normalized producer found | — | — | Absent as a Planner input; Stage 2 observation remains deferred. |

## 4. Knowledge source matrix

| Knowledge source | State | Owner / current use | Backlog representation |
| --- | --- | --- | --- |
| Provider current-track metadata | Implemented | Music Backend/Track Insight; safe track, artist, album, artwork and media identity. | Represented by current Insight and observation capability. |
| Artist, album, genre, production and related-work hints | Implemented | Track Insight -> Knowledge Engine's deterministic primary-evidence selection. | `KE-2.2` current. |
| Recommendations / Discover feed | Implemented | Discovery service and optional Music DNA context; playback requires explicit action. | Current Discover Stage 2. |
| Recently played and profile snapshot | Implemented | Music Backend/Profile-owned Music DNA; informative and opt-in. | Capability Model `CAP-IN-03`, `CAP-PS-02`. |
| Session Flow / prior Moments | Implemented | Runtime-owned Performance Memory and current Flow. | Current Planner/Moment maturity. |
| Persistent Session history | Partial | Persistent Session owns historical projections; not a demonstrated general Knowledge Engine input. | Persistent Session roadmap. |
| Music DNA | Implemented, opt-in | Profile-owned compact snapshots and personal context. | Capability Model `CAP-PS-01..03`. |
| Audience observations | Deferred | Audience architecture prohibits Planner use of raw events/projections. | Represented: Audience Experience and `PL-3.2` deferred. |
| Concerts | Planned/gated | Requires bounded attributable source contract before Knowledge Engine use. | `KE-3.1`. |
| Music history, biographies, collaborations, credits | Partial/Planned | Production/credit hint may exist in Track Insight; no source-qualified retrieval for history/biography/collaboration. | Historical context is `KE-3.2` gated; biography/collaboration are implicit only. |
| External editorial/music sources | Planned | Architecture permits only future qualified retrieval. | Maturity Stage 3; no concrete source capability. |
| Lyrics and synchronized lyrics | Absent | No acquisition/provider/retention/timing implementation. | Lyrics is represented in historical V4 evidence, Product Roadmap and Innovation Lab; not a current canonical capability. |
| Verse/chorus/bridge timing | Absent | No musical-structure source or timing model. | Unrepresented as an explicit atomic capability. |
| Emotional/energy analysis | Partial | Mood is supplied Runtime context; Track Insight visual/mood fields exist. | Long-term emotional arc remains Stage 4 direction, not a knowledge source contract. |

## 5. DJMoment capability matrix

| DJMoment | Trigger and Planner decision | Knowledge dependency | Presentation / projection | Status |
| --- | --- | --- | --- | --- |
| Track | Eligible current-track path; fallback/default context | Safe Track Insight/current metadata | Immutable Moment, Session Flow, Broadcast and Presentation composition. | Implemented |
| Artist | Track Started deterministic selection | Artist/production evidence | Same canonical projection path. | Implemented |
| Album | Track Started deterministic selection | Release/album evidence | Same canonical projection path. | Implemented |
| Genre | Track Started deterministic selection | Genre/subgenre evidence | Same canonical projection path. | Implemented |
| Recommendation | Track Started/Discover selection | Related-work evidence | Immutable semantic actions; explicit playback remains separate. | Implemented |
| Session Update | Planner-approved direction change / narrow silence recovery | Safe Direction, Strategy, Mood, Performance Memory context | Session Moment through existing Flow/Broadcast. | Partial |
| Transition | Exploring Recommendation after an allowed preceding contribution | Existing Flow relationship and safe existing context | One immutable NEXT Transition; no-transition is silent. | Partial |
| Silence | Planner policy or safe fallback | None | Immutable silence contribution / Flow. | Implemented |
| Discover | No dedicated Moment type | Existing Recommendation/Artist/Album/Genre types | Discover is a Start Strategy, not a Moment. | Intentional absence |
| Concert, Music History, Producer/biography, Audience, Lyric | No current Planner/Moment realization | Missing source/policy or prohibited Audience path | No renderer projection. | Planned, Deferred or Absent as noted above |

Current factual contributions are therefore limited to safe current-track,
artist/production, release, genre and related-work facts plus Session state and
the narrow Transition rationale. They do not include lyric text/meaning, timed
lyrics, verified biography/history/concert facts, audience interpretation or a
multi-Moment narrative.

## 6. Audience Signal assessment

There are two different repository states that must not be conflated:

1. `AUDIENCE_EXPERIENCE_ARCHITECTURE.md` is canonical for the broader product
   capability and says reaction intake, event storage and Planner influence are
   deferred. It permits no raw audience signal to affect Session Intelligence.
2. The current Runtime nevertheless exposes a narrow broadcast-token-gated
   `async_submit_audience_signal_with_broadcast_token` path. It accepts a fixed
   signal vocabulary, aggregates totals/recent activity in `DJSessionPlanner`,
   and publishes a renderer-safe audience projection. It does not mutate
   playback, Session Flow, Performance Memory, Music DNA or Planner selection.

| Signal / behaviour | Playback | Session Memory / Performance Memory | Music DNA | Planner | Current conclusion |
| --- | --- | --- | --- | --- | --- |
| Receiver `more_energy`, `less_energy`, `chill`, `dance`, suggestions | No | No | No | No decision use; only marked pending | Implemented session-scoped projection, canonical-document drift. |
| Like/dislike Discovery feedback | No automatic playback | No demonstrated Session Runtime use | Compact positive/negative profile feedback where authorized | No | Implemented recommendation feedback, not Audience Intelligence. |
| Skip/replay | No normalized signal input | No | No | No | Absent. |
| “Tell me more” / “talk less” | No canonical intake | No | No | No | Absent. |
| DJMoment feedback / guest feedback / VibeCast reaction | No beyond narrow receiver signals | No | No | No | Deferred/partial only; full Audience Experience remains deferred. |
| Engagement timing/repeated audience behaviour | No | No | No | No | Absent; future coarse observation is separately governed. |

**Classification:** an Audience Signal capability is **implicit and partially
implemented**, but it is not a canonical active Planner capability. The report
recommends reconciliation of this documentation/code mismatch before either
surface expands.

## 7. Lyric Intelligence assessment

The target capability—explaining a verse, chorus or line at exactly the
musically appropriate moment—does not currently exist. No repository evidence
shows lyric acquisition, synchronized lyric timestamps, section detection,
line timing, copyright policy enforcement in Runtime, lyric-specific Knowledge
Context, Lyric Intent/Moment, or timing-aware renderer projection.

It requires at least these atomic capabilities, none of which should be
silently inferred from Track Insight:

| Required atomic capability | Current state | Representation |
| --- | --- | --- |
| Copyright-safe lyric source qualification and attribution | Absent | Represented in historical V4 Lyrics sequence and Innovation Lab; not Capability Model. |
| Acquisition and bounded cache/retention policy | Absent | Implicit only. |
| Synchronization/timestamp normalization | Absent | Innovation Lab mentions Live Lyrics; no canonical atomic capability. |
| Verse/chorus/bridge and line-boundary detection | Absent | Unrepresented. |
| Planner policy for relevance, timing, delay and no-lyric fallback | Absent | Historical V4 mentions Horizon-aware lyric intent; no current maturity cell. |
| Copyright-safe explanation/excerpt policy | Absent | Represented conceptually in V4 and Innovation Lab; needs canonical policy. |
| Lyric Knowledge Context and Lyric DJMoment realization | Absent | Historical V4 only; no current `KnowledgeIntentType`/`DJMomentType`. |
| Renderer-safe timed visual/audio projection | Absent | Innovation Lab/VibeCast concept only. |
| Provider support and graceful degradation | Absent | Implicit only. |

The correct conclusion is not that lyrics are merely a renderer gap: they need
source, rights, timing, Planner, Knowledge, Moment and presentation decisions.

## 8. Backlog traceability and missing-capability inventory

| Gap | Classification | Evidence / recommended documentation correction |
| --- | --- | --- |
| Multi-track planning, dynamic replanning, narrative sequencing and pacing | Represented | DJ Intelligence Maturity Stage 4, Rolling Horizon architecture and Product Roadmap. Keep deferred until one bounded policy cell is selected. |
| Provider-normalized upcoming playback / Stage 2 observation | Represented | Product Roadmap and Live Playback Observation. External capability-gated. |
| Audience observation and adaptive planning | Represented | Audience Experience Architecture, `PL-3.2`, Product Roadmap. Keep deferred and coarse/privacy-bounded. |
| Concert and historical knowledge | Represented | `KE-3.1` and `KE-3.2` gated. |
| Lyrics explanation and Live Lyrics | Represented but non-canonical | Historical V4 record and Innovation Lab; Product Roadmap names Lyrics. Promote only through a future capability assessment, not this review. |
| Artist biography, collaborations and comprehensive credits | Implicit | Architecture mentions external music knowledge; no source-qualified atomic backlog item. |
| Verse/chorus/bridge identification and exact musical line timing | Unrepresented | Add as separate prerequisites only if a future Lyrics capability assessment is approved. |
| Explicit listener controls: “tell me more”, “talk less” and DJMoment feedback | Unrepresented | No canonical capability or maturity cell; do not treat Ask DJ chat as a substitute. |
| Skip/replay as normalized, privacy-safe Planner evidence | Implicit | Observation and Performance Memory work exists, but no bounded signal contract or policy. |
| Emotional pacing model | Implicit | Mood/Direction exist; Stage 4 emotional arc is directional rather than an explicit input/model. |
| Persona adaptation from observed interaction | Unrepresented | Persona is supplied context; no learning/adaptation contract exists. |
| External editorial provenance/reliability policy | Implicit | Architecture requires reliable filtered knowledge; no concrete source/provenance capability is represented. |

## 9. Documentation-only recommendations

These are corrections to planning clarity, not priority changes or authorization
to implement:

1. Reconcile `AUDIENCE_EXPERIENCE_ARCHITECTURE.md` with the currently
   implemented bounded receiver-signal projection. State its exact privacy,
   lifetime and non-influence boundary, or explicitly retire it after a
   repository capability assessment.
2. Create a future **Lyrics Knowledge Capability Assessment** before any lyric
   rendering work. It must decompose rights/source, retention, synchronization,
   structural timing, Planner policy, Knowledge/Moment realization and safe
   presentation.
3. Add explicit discovery backlog entries—only when prioritized—for: musical
   structure/timing, listener verbosity feedback, normalized skip/replay
   semantics, source provenance and persona adaptation. They are currently
   implicit or unrepresented rather than authorized features.
4. Treat `UpcomingPlaybackProjection` as a supported Runtime/planning model
   with no current provider producer, rather than evidence of actual
   multi-track planning. This removes ambiguity between implemented architecture
   and live operational capability.

## Validation and authority conclusion

This review inspected canonical product, capability, roadmap, Experience and
Generation 2 records; current Runtime/knowledge implementation; and focused
test/scenario evidence. Historical V4 material is cited only for traceability,
not as current authority. No Runtime, renderer, API, ownership, capability or
roadmap file was changed by the review.

### Concise answers

- **How smart is the DJ today?** A deterministic, session-owned contextual DJ
  for the observed current track, with bounded rolling planning mechanics and
  safe metadata-based Moments—not yet an autonomous narrative DJ.
- **Highest-value missing Planner inputs:** trusted upcoming playback,
  normalized skip/replay and explicit listener verbosity/Moment feedback; only
  later, separately governed coarse audience observation.
- **Highest-value missing knowledge:** source-qualified external music/history
  knowledge, provider-normalized future playback facts and a copyright-safe
  Lyrics Knowledge stack.
- **Missing DJMoment types:** Lyrics, Concert, History, Audience and a real
  Discover Moment; richer Transition and Session Update policy also remain.
- **Audience Signals:** narrow, session-scoped receiver projection exists;
  planner, playback and learning influence do not.
- **Lyric Intelligence:** absent end to end; partial ideas exist in historical
  and Innovation records only.
- **Represented gaps:** horizon/multi-track direction, narrative, audience,
  observation Stage 2, concert/history and lyrics at broad planning level.
- **Important unrepresented gaps:** musical structure/line timing, listener
  verbosity/Moment feedback, normalized skip/replay, persona adaptation and
  explicit source-provenance capability.
