# DJ presence v1 — Planned design

Decision `DJC-DJ-PRESENCE-ROADMAP-DESIGN-V1-20261011`, product slice
`DJC-DJ-PRESENCE-V1`, [owner decision6110375785](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6110375785).
**Product status: Planned.** Documentary integration is authorized; product
implementation, native UI, browser/installed/hardware qualification are not
started or claimed. Core and Apple retain their existing writers. Generation2,
Phase1; no new lane, monitor, model/provider/TTS or automatic dispatch.

## Three independent dimensions

Mood selects this active Session's atmosphere. Persona selects how a contribution
is told. DJ presence selects how much space the DJ may proactively occupy,
including spacing and already supported connections. Calm mood with a talkative
DJ and energetic music with a nearly silent DJ are valid combinations.
Presence is not selected_mood, Persona, direction, start strategy, legacy numeric
Watch mood, voice volume or TTS enablement. It changes none of those dimensions.

## Five anchor positions and Apple experience

Native iPhone/iPad/macOS stepped slider: **DJ-aanwezigheid**, explanation
**Hoeveel vertelt de DJ tijdens je sessie?** The five positions are fixed design
intent; machine values and numeric budgets are not yet a published API.

| Position | Meaning |
|---|---|
| Alleen muziek | No new unsolicited content Moments. Music context, necessary controls/errors and explicit Ask DJ answers remain. |
| Af en toe | Occasional strong relevant contribution, leaving much space for music. |
| Gebalanceerd | Regular relevant contributions with rest and variation; proposed compatible default, subject to baseline calibration. |
| Praatgraag | More suitable contributions, available substantive variety and already supported callbacks/transitions. |
| Presentator | Widest substantive budget within safe timing and available qualified knowledge; no compulsory quota or complete radio-show claim. |

Before implementation, pin an exact policy table: internal values, numeric
spacing/quantity/readability budgets for every eligible path, verified default,
valid Mood/Persona combinations and an observable decision boundary. Do not
invent percentages or untested contributions per minute here. Pending/error
state must differ from server confirmation. Preserve search/scroll position and
Session controls. Five-language families en/nl/de/fr/es and native VoiceOver,
keyboard and value/state accessibility are Apple acceptance requirements;
these Dutch design anchors are not shipping localized product strings.

## Server-owned policy and production boundary

Effective presence is active Session/Runtime state, not an automatically learned
Profile preference. Planner consumes it through the existing
Runtime → Planner → Knowledge → Moment → Flow → Broadcast chain. Clients neither
filter cards to imitate policy nor fabricate Moments. Future persistent Profile
preferences require a separately designed extension.

Inventory all proactive entry paths before changing policy: track-start,
same-track factcards, eligible Genre/Artist/Album/Track, authorized Recommendation,
Transition and Session contributions. Changing only a factcard timer is
insufficient. Existing35/50second spacing,40–90second read-fit and six-card limits
are route-specific baseline observations, not a universal new slider contract.
Every necessary dosing change needs exact tests/review.

Only successfully published substantive Moments count/consume the presence
contribution budget. Proposals, rejected/expired/in-flight candidates and Silence
do not; independent source/system resource budgets still bound attempted work.
Presence is a preference/budget, not a guaranteed amount. A source-rich equivalent
trace must demonstrate different actual quantities/spacing across levels.
Eligibility, rights, attribution, language, current-track binding/freshness,
readability, deduplication and system/source budgets remain hard limits at every
level. Source-poor traces may yield Silence even at Presentator. Reuse available
authorized contents and bounded caches; no new sources, credentials, provider,
model, TTS, paid route or unlimited requests are authorized.

Accepted Alleen muziek stops future unsolicited production/publication, including
stale in-flight Knowledge results. Mood/Persona cannot override it. Existing
published immutable Moments/presentations keep normal visibility/expiry and
readonly history; no deletion, replacement talk bubble or filler. Internal
Silence/lifecycle events are not substantive contributions. Explicit Ask DJ
text/voice and necessary operational messages remain separate and functional.

Raising presence cannot replay missed/expired work, stack an overdue backlog or
reset budgets through repeated settings, reconnect or duplicate requests. Only
current suitable contributions are eligible. Lowering presence preserves current
presentation and constrains subsequent decisions. Pin the policy revision/decision
boundary for planning, asynchronous callbacks and final publication; preserve
immutable facts and presentation snapshots. No late unsolicited result under Off,
ABA loophole, same-track duplication or retrospective rewriting.

## Owner contract, lifecycle and privacy

Plan a distinct versioned presence capability, write and authoritative readback
contract. Exact route/schema/values remain open qualification details; no existing
API is declared by this document and the Mood endpoint is not extended implicitly.
Reuse only the needed qualified [active Mood owner-auth/order subset](ACTIVE_SESSION_MOOD_V1.md):
ordinary device pairing/bearer, server-bound owner, active Session, final authority
fence, proportional CAS/idempotence and Session-scoped late-response handling.
Mood handling does not determine presence frequency.

Two ownerclients, conflicts, old replies, pairing withdrawal, Profile switch,
wrong/ended Session and reconnect need real proof. No mutation on rejection;
no Session restart, playback/queue/backend/Mood/Persona change. Readonly paired-live,
Broadcast Tokens and view-end grants acquire no write rights. Private Ask DJ
questions, archives/history/search and owneridentity remain outside shared VibeCast.

## V1 versus richer narrative mode

V1 qualifies real adjustable dosing of already supported valid contributions
and their existing variation/connections. A slider-only change or longer copy
cannot satisfy it. [Contextual fact planning](CONTEXTUAL_FACT_PLANNING_CONTRACT.md)
and [expressive variation](EXPRESSIVE_CONTEXT_VARIATION_V1.md) retain eligibility,
facts/attribution, published-only memory, dosing and Silence boundaries.

Richer narrative presenter mode is a later **Planned** maturity extension inside
the broader retained narrative/lyrics/Discover family (currently Deferred in the
owning roadmap). It requires independent qualification for new substantive
connections, callbacks and storylines. Existing qualified Genre→Track and
shared-producer relations may be reused within their exact boundaries. Presentator
v1 does not unlock all Moment types, future-track planning, lyrics, biographies,
Audience adaptation or cross-Session learning. Broader deferred work is not
promoted or made a retrospective v1 completion gate. See
[DJ intelligence maturity](DJ_INTELLIGENCE_MATURITY.md).

## Delivery ownership, dependencies and readiness

Core owns policy/default/ownercontract/fixtures and actual proactive regulation.
Apple #87 owns native slider/confirmation on its existing writer. Core shared
renderer + VibeCast #10 own local HA/Pi and static consumer compatibility; no
second renderer or receiver HTML copy. Joint Core/Apple receipts qualify the
product, not an extra writerlane. Mood completion orders selection softly;
writer occupancy remains a separate resource/admission check.

DoR for a separately selected product implementation: exact policy table and
calibrated default; complete proactive-path inventory; pinned own capability/
schema/fixtures; owner/resource admission and explicit effect authorization.
Apple contract-dependent integration can start from a pinned early candidate
and fixtures, without waiting for all Core Finalization documents. Independent
UX preparation alone proves no connected functionality.

DoD requires Core policy AND native Apple control AND both renderer compatibility
receipts, bound to exact producer/consumer candidates. Software preparation has
no hard gate on Cast hardware, LG installation, public Apple/HACS release,
Windows infrastructure retirement, new knowledge sources or full narrative AI.
Native/browser/installed/hardware claims and gates remain separate.

## Joint acceptance specification — future tests, not PASS receipts

A. Same source-rich Session trace, identical Mood/Persona/tracks: zero unsolicited
content at Alleen muziek, distinguishable actual published quantity/spacing
elsewhere, same content quality; count all proactive paths and Silence reasons,
without guaranteed quotas.

B. Calm+high presence and energetic+low presence prove orthogonality; changing
presence never changes Mood/Persona or the other Session dimensions.

C. Mid-track low→high→off→resume, long-running generation and reconnect: no late
unsolicited publish while off, duplicates, catch-up stack, budget-reset repetition
or changed earlier Moment/presentation bytes.

D. Actual ordinary pairing→ownerrequest→policy→Runtime/Planner→Flow/Broadcast,
two clients/revisions/conflicts, delayed replies, withdrawn/ended/wrong-Profile
requests; rejected requests mutate nothing. Ask DJ text/voice and readonly
history/search remain usable at Alleen muziek.

E. Native iPhone/iPad/Mac slider, accessibility and all five languages; identical
content/timing in local portrait and static landscape VibeCast, with readability,
search position and private-content isolation. Browser/model evidence does not
prove physical Pi/CAF/TV or installed acceptance.
