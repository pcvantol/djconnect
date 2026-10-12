# Session Forecast v1 — Vooruitblik · ±15 min

Assignment DJC-CORE-SESSION-FORECAST-V1-20261012;
[selection/design decision6123328620](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6123328620).
Status: pre-runtime contract preserved below; local Core implementation and early
ordinary paired HA qualification complete locally. Exact freeze reviews/protected delivery pending.
Same sole Core writer, actual base e26888fc164fac1e5cb41908fd922d5f9a05e0bd,
branch codex/session-forecast-v1, after closed album1154/1155.
No source/Finalization publication, consumer admission or installed acceptance.

## Foundation and ownership

Refine the existing [Direction Projection](../technical/SESSION_DIRECTION_PROJECTION_ARCHITECTURE.md),
not another Planner or product family. Current Runtime/Planner foundation is
15 minutes; internal Rolling Horizon's future product target is approximately
20 minutes. The public nominal window is900s, not a reservation, countdown,
queue promise or change to either internal policy. Only an allowlisted semantic
projection leaves Core; slots, generation/task IDs, confidence vectors, provider
responses, Music DNA, conversations and private history never do.

Planner supplies a bounded intention grounded in its actual current Strategy,
Direction, admissible contextual opportunities and supported capability subset.
Existing expression/presentation ownership realizes authored text for four
Personas and en/nl/de/fr/es. Runtime owns lifecycle and bounded revision;
Broadcast publishes an additive snapshot/update. It is mutable active state,
never an overwritten DJMoment, Flow item or historical fact.

## Pre-runtime inventory and policy

| Existing input/boundary | Forecast use | Excluded meaning |
| --- | --- | --- |
| SessionStartStrategy and timestamped SessionDirection | Actual Planner-supported musical/experience objective | Claim of provider playback control |
| Runtime Mood | Desired atmosphere and conditional target language | Verified sound/energy analysis or inevitable curve |
| Persona | Wording and presentation of identical semantics | Different facts or extra contributions |
| PresencePolicy/shared ledger | Off explicitly promises room for music; other states describe eligible conditional guidance | Extra Moment, guaranteed future contribution or budget reset |
| Accepted renderer-safe current playback | Current section with exact observed identity and freshness | Queue[0] promoted to upcoming forecast |
| Existing qualified/published current-source context | Bounded eligible artist/album/genre focus, respecting original source/channel rights | Provider response or proposed/failed Moment as published knowledge |
| Existing Planner allowed-intents/candidates | Small semantic opportunity allowlist; absence is meaningful | Export of Horizon/slots/internal ranking |
| Ordinary paired owner context/live subscriptions | Active device-bound Profile/session read and withdrawal | Broadcast grant authorizing owner operations |
| Existing Music Backend metadata boundaries | Qualified current imagery when provenance and display terms allow | Private Discovery grants or arbitrary external URL |

If no current evidence is usable, return limited/empty honest intentions and no
media claims. A contextful forecast must explain what the DJ can do with that
context, rather than emit only a Mood slogan. Selection is deterministic and
bounded; no quota forces two-to-four cards. Existing safe Silence remains.

## Versioned producer contract

Capability `session_forecast`, version1, `paired_device_bearer`, read-only,
active-device-bound-owner-session. Proposed GET
`/api/djconnect/v1/session/forecast/{session_id}` takes exact supported device
identity and contract_version1. No user credentials substituted for normal
pairing; Windows retirement preserved. Broadcast snapshot gains additive
`session_forecast`; existing live channel carries `forecast_changed` with the
same projection and ordinary sequence/watermark/recovery semantics.

Projection fields: `contract_version`, `session_id`, monotone `revision`,
`state` (`ready`, `limited`, `empty`, `expired`, `withdrawn`), `issued_at`,
`valid_until`, `nominal_window_seconds:900`, `supported_window_seconds`,
`current_anchor` (existing public playback `item_id` plus source URL, or null),
`summary`, bounded `sections[]` and `imagery[]`. Stable section IDs are
`current`, `guidance`, `aim`; each has authored title/text and explicit
`claim_type` (`current`, `intention`, `conditional_target`). A media anchor
is an exact typed subject with `role`, source link and qualification boundary.
No upcoming media is emitted unless a separately qualified Upcoming Playback
Projection supplies its exact identity/authority; recommendations/queue preview
are insufficient. Narrative-only v1 has no hard future-playback dependency.

Publication reads one coherent immutable projection under existing Runtime
ordering. Material context/Direction/Mood/Persona/presence/authority changes
reassess; repeated equivalent inputs/no-op settings are no-ops. Revisions are
Session-local, never reset by view toggle or reconnect. Projection validity
is bounded by original context/source deadlines and a short server freshness
ceiling; reads do not extend it. Existing observation ticks can publish expiry,
never timer-driven new narration or invented chapter progress. Expired reads
return no stale sections/art. End/replacement/unload/withdrawal clears content.
A newly qualified observation may create a fresh revision; a read never does.

## Artist imagery — direct human amendment

Artist/band imagery may be prominent when it supports the narrative. Album or
track art is not a required substitute. Every admitted image has:

| Field | Meaning |
| --- | --- |
| subject | Exact typed artist/album/track identity and display name, never name-only matching |
| role | `current`, `contextual`, or `qualified_upcoming` |
| source_url | Canonical original source/resource with clickable provenance |
| attribution | Visible provider/creator/mark/link obligations, not a hidden tooltip |
| usage_basis | Explicit documented display/license basis and permitted audience |
| expires_at | Original asset deadline; visible validity also requires the earlier `forecast.valid_until`; neither renews on reads/cache |
| url | Managed HA renderer-safe resource; no undocumented hotlinking |
| cache_policy | Session-bound/no-store consumer policy and bounded producer cache |

`current` requires confirmed current playback and exact artist membership.
`contextual` requires a real qualified narrative anchor and explicit context
label; it is not next playback. `qualified_upcoming` requires a safe supported
upcoming claim and matching evidence. Art is supportive, never independent
playback proof. Unknown future artists are never inserted, even with “maybe”.
V1 may honestly omit upcoming anchors entirely. Public best-effort artist art
fetch is permitted only at bounded qualified-input preparation, not on reads,
with exact identity, provenance, usage basis, attribution, timeout/size/cache
limits and text/color fallback. Reuse allowed provider boundaries where possible;
no paid/model route, private source or uncontrolled URL fetch. Unknown license,
wrong subject, missing source/attribution, expired or revoked art is ineligible.
Private Discovery/Music DNA image grants cannot be reused in this audience.

Missing/failed art keeps authored text readable. Expiry/revocation removes URL
and already decoded pixels, releases element sources and local caches; decoder
failure falls back without fetching another unqualified image. Session end and
lost authority clear the entire forecast. Generic imagery never stands in for
a named musical anchor. No source-content crop/AI rewrite contrary to its terms.

## Consumers and acceptance

Apple owns Flow | Vooruitblik on iPhone/iPad/Mac, spacious cards and prominent
qualified artist art. Preserve header/controls, both views' scroll/search state
and unsent Ask DJ draft. Correct role/conditional labels, source links, large
text/VoiceOver/keyboard/reduced motion and five languages require Apple-owned
acceptance. Early pinned Core capability, fixtures and all states support an
independently admitted Apple implementation, never extending mood-toolbar WIP.

Core keeps one local/static renderer source. Shared compatibility/privacy/safe
fallback are mandatory; visible ambient composition is a separate qualified
subset. Unknown additive fields/events remain safe in renderer1.1. No shared
owner controls or private data. Pages/CAF/Cast/LG installed/hardware qualification
cannot be inferred from browser/API proof.

Pre/post acceptance uses real isolated HA pairing→owner read→Runtime→Planner→
projection→Broadcast, only external provider/SDK fixtures. Cover no/active/end,
all Mood/Persona/presence values, same-session changes, repeated reads/toggles
with zero lookups/plans/Moments/playback/budget effects, useful limited context,
unknown/stale/expired/revoked art, wrong/revoked/rebound Profile authority,
two-client/out-of-order/races/reconnect, no private Horizon/history leaks.
Measure update and resource bounds; independent five-language editorial and
technical/privacy reviews plus owning coverage/full regressions are required.

Canonical roadmap uses existing PROJ::ROADMAP::DIRECTION as parent and only
unique CONTRACT/CORE/APPLE/SHARED-COMPAT/JOINT subsets. Start/integration/AND
edges remain distinct. Visible VibeCast and optional upcoming track enrichment
remain open subsets. Album closure is writer order, not a functional dependency.
Preserve frozen history and delivered presence/artwork/album maintenance deltas.

Delivery requires real files/commits/PR/main, exact artifact/formal readback and
separate Finalization/cleanup with their own exact publication approvals.
Report documents/DAG, Core projection, Apple handoff, shared compatibility,
native view, visible ambient adoption, installed/hardware and joint separately.
Stop after this Forecast slice; no automatic consumer or next-slice dispatch.

## Concrete v1 bounds after pre-runtime technical review

Owner GET schema is exactly path session_id plus client_type/device_id/
contract_version query fields. Final readback under Runtime lock rechecks loaded
entry, ordinary device token/identity/type, enabled bound Profile and unchanged
account/provider/session authority; capability alone grants nothing. Shared
Broadcast only serializes the public allowlist. Owner withdrawal empties the
forecast alongside native-delivery withdrawal.

Projection freshness ceiling120s, never beyond accepted source validity. Pure
expired read preserves the stored revision/issued_at/valid_until but projects
`expired` with empty sections/imagery. An existing observation tick may commit
one invalidation revision; repeated expired ticks are no-ops. Consumer ordering
uses revision plus validity, never accepts an expired same-revision frame as
live. Material setting/track/authority invalidation is immediate. Routine
same-track qualified freshness updates publish at most once per30s, including
expiry recovery; reads/toggles never advance clocks or revision. At most three
sections and two images. supported_window_seconds is900 only for an actual
supported conditional semantic objective; zero otherwise. It promises no media.

V1 uses Spotify's existing provider/account boundary for exact current artist
IDs only, not a name search. Its artist endpoint documents artist images plus
resource-link and Spotify-mark obligations:
[official artist API](https://developer.spotify.com/documentation/web-api/reference/get-an-artist).
No cropping/overlays/AI alteration, offline download feature or persistent art.
A qualified text anchor does not independently license an image. Images require
separate exact response-subject verification, display usage basis and audience.
No qualified future playback projection exists in this slice, so future artist
images remain absent. Contextual role remains explicit and unpopulated for
Spotify imagery whose supplied basis is current display only; text fallback is
valid. Other public-source adapters require their own proven identity/license
basis, not an arbitrary URL passed by a client.

Preparation: one primary current artist, one in-flight task per Session, at most
12 preparation attempts per Session; no reset on Off, setting changes/reconnect.
Metadata request deadline4s through existing Spotify backend; CDN request4s,
HTTPS exact i.scdn.co/image path, no redirects/custom ports/query, at most2MiB,
PNG/JPEG/WebP only with validated format/size. At most two active in-memory
assets; original asset deadline at most300s, negative result cached60s, no disk
cache. Input preparation may fetch; HTTP/projection/image reads fetch nothing.
No source retries on repeated read/toggle. Failed/unavailable/429 or withdrawn
metadata/art gives honest text/color fallback without another source lookup.

Managed Forecast image grants are unpredictable, headerless display references
bound to Session, exact typed subject, role, accepted current track, Profile,
source entry/account/authoritygeneration and original minimum deadline. Each
read rechecks those bindings; paused/stopped/replaced/ended/withdrawn context
fails closed. After every await, preparation rechecks authority and snapshot
before admission. Tokens/bytes never enter history/diagnostics/Flow. Private
Discovery grants are never imported. Expiry/revocation emits safe empty image
state and consumers release already decoded pixels/cache. Pure read rejection
creates no update, plan, Moment, budget or lookup.

## Early actual producer qualification (local, unpublished)

Twenty ordinary paired HA Persona/language chains deliver owner-read/live and
current-artist image bytes through the actual managed route. Repeated forecast
and image reads cause zero additional provider calls, plans, Moments or budgets;
reconnect preserves deadlines, wrong authority/session/end fail closed.
[Actual transport fixtures](../../examples/client_contracts/session_forecast_v1/transport-fixtures.json)
and [source hashes/qualification](../../examples/client_contracts/session_forecast_v1/qualification-summary.json)
are early local evidence, not an installed/native/hardware or finished-source
claim. Only external Spotify metadata and CDN response boundaries are fixtures.
Owned timer listeners are removed after genuine pending work settles solely
to isolate pure-read effects; provider timing is modeled, no long-duration PASS
is inferred. Full race/browser/expiry/coverage/regression/editorial checks remain.

### Artist-image claim lifetime and review corrections

The managed byte lease and narrative claim have separate clocks. Consumers must
remove images, including already decoded pixels and local cache references, at
`min(forecast.valid_until, image.expires_at)`. A withdrawn, empty or expired
Forecast removes all visible images immediately; receiving image bytes alone
never establishes playback or a forthcoming artist. Missing/failed art leaves
the narrative and attributed text readable, with a neutral placeholder.

Only a newly accepted provider playback observation renews the 120-second
current-context freshness lease. Mood, Persona, presence, direction, reads,
reconnect and late artwork completion can re-realize still-valid content but
cannot extend its original source deadline or revive an expired current claim.
The artwork's independent 300-second memory lease cannot extend that claim.
Provider runtime/entry identity and unload generation, active backend,
account/backend relationship and Profile membership fence both owner reads and
managed bytes. Normal OAuth credential rotation preserves canonical authority.

Current-role artist imagery is implemented first. Contextual and qualified
upcoming roles are schema-reserved and remain absent until their own safe
claim and display-rights admission succeeds. No subsequent artist is invented.
Apple's prominent artist composition and VibeCast's visible Forecast adoption
require separate consumer qualification; Core transport alone is not that PASS.

An exact same-artist image may support a different newly observed current track
without another remote lookup. Admission rechecks exact artist identity and
canonical current source authority, uses a new opaque grant scoped to that
current track, and retains the original bytes, provenance and asset deadline.
The old grant does not authorize the new track. This reuse does not reset the
12-attempt budget, backoff or freshness lease, and retains no chain of old assets.

A playback-change/pause frame omits Forecast until a matching current realization
commits; it never invents a different projection under an existing revision.
Consumers remove a displayed current anchor when its item ID differs from current
playback, independently of Forecast revision ordering. Readable current art follows
the matching qualified current anchor. Historical replay frames omit Forecast.
If recovery spans a forecast_changed event, the existing snapshot_required route
returns one coherent current snapshot rather than replaying mutable intent as
history. A consumer rejecting revision <= last_revision therefore cannot accept
a fabricated limited projection and suppress the ready projection at that revision.
