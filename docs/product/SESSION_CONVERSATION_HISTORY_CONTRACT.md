# Session conversation and history — retained foundation and shared dialogue correction

## Corrective retained-entry compatibility — 18 October 2026

The current private producer also emits the four retention bases and two
source-free entry kinds below. Their omission from this consumer contract and
closed schema1 decoders caused an actual HTTP200 timeline to fail as a whole
on Apple40331. A successful server response is not successful client decoding.
The original separately reported HTTP404 remains a different open finding.

Every row retains the existing identity/order/timestamps, owner-only authority,
`historical_view_only:true` and `current_display_allowed:false`. Core revalidates
Profile/privacy, history grant, source ownership and rolling Session retention
before returning it. Consumer parsing does not grant access or upgrade a source.

| `kind` / `archive_basis` | Meaning and client boundary |
| --- | --- |
| `dj_moment` / `cc0_normalized_fields_v1` | Already admitted normalized CC0 facts; preserve accepted text and attribution. |
| `dj_moment` / `runtime_authored_direction_v1` | Core-authored Session direction/opening; no external fact authority or automatic playback. |
| `dj_moment` / `owner_metadata_narration_v1` | Bounded owner-private accepted metadata narration. Preserve text/attribution; Core's captured account/provider/entry check runs on every read. Never infer CC0, model-processing or shared-screen permission. Internal `source_context` and `session_media_reference` do not escape. |
| `dj_moment` / `public_artist_narration_v1` | Completely assessed researched expression, including the locally extended album family. Preserve exact accepted prose and `sources[]`/revision/license attribution. The creative text is not factual evidence for another answer. No client regeneration or inference of source roles. |
| `dj_publication` / absent | Stable publication receipt after an unqualified/withdrawn body. `content_state:"unavailable"`, typed `unavailable_reason`, `text:null`, `speech_available:false`. No body reconstruction, source/artwork reuse, replay or autoplay. |
| `dj_silence` / absent | Durable intentional silence, `moment_type:"silence"`, `content_state:"silence"`, `text:null`, `speech_available:false`. Keep identity/order; presentation may be subtle. No speech or invented filler. |

Optional `session_speech` and `session_media` remain separately validated
server descriptors. A stored text or recognized basis alone is no ready audio
asset or image grant. Replay uses the existing prepare owner and current active
Session voice, otherwise current Profile defaults; text_only/provider/source
withdrawal and expiry may refuse it. Never autoplay historical rows. Shared or
passive surface permissions do not follow from an owner history response.

After source withdrawal, an admitted metadata row projects as `dj_publication`
with the SAME `entry_id`/order and no retained body; no history rewrite or source
renewal occurs. Never label a metadata/researched body CC0 or Core direction to
make an older decoder accept it. Unknown/unqualified bases remain denied by
Core. A future unknown presentation shape must not silently become readable
content, speech or an executable action through a consumer fallback.

The original, immutable consumer sample is
[retention-bases-v1.json](../../examples/client_contracts/session_conversation_history/retention-bases-v1.json).
It contains one actual Core-projected mixed page, same-identity withdrawal and
refused unknown/expired/revoked/shared rows. Source inputs are synthetic
already-admitted rows; it is not generator, source-admission, installed, native
or audible evidence. `source_pins` bind the actual projection/speech modules;
the owning Core test preserves its original digest. Its manually assembled
tail envelope omitted `window_limit`; do not relax the consumer's real envelope
validation to accept that omission. The replacement
[retention-bases-v2.json](../../examples/client_contracts/session_conversation_history/retention-bases-v2.json)
uses the actual SQLite repository and query tail envelope, including
`window_limit:20`, plus negotiated schema2 and the truthful legacy409. Its
deterministic clock also covers summary projection. The owning test regenerates
and compares that complete fixture, not a hand-authored response substitute.

### Explicit retained-entry representation version2

The corrective representation uses `history_contract_version:2`, accepted as a
GET query/POST-open integer (GET strings `"1"`/`"2"` also accepted). Omitted
means1; booleans, other values and unsupported versions fail400 with
`unsupported_history_contract_version`. Discovery adds
`contract_versions.session_history_entries:2`; the existing
`session_conversation_history:1` and `session_flow_text_search:1` stay unchanged.
The version applies to list/timeline/tail/anchor/search/open; it is not a new
history, owner, retention or speech contract.

Version2 returns `schema_version:2`, `history_contract_version:2`, the exact
qualified rows above and all original identities, order, attribution and state.
Version1 keeps schema1 and its original four kinds/two bases unchanged. If the
requested page/entry/matches cannot be represented losslessly in1, return
HTTP409 `history_contract_upgrade_required`,
`required_history_contract_version:2`, `supported_history_contract_versions:[1,2]`,
without partial entries or source content. This is not HTTP404 or pairing/token
failure; do not clear pairing, clear history or retry forever. Old pages that
fit1 remain readable. No caller may change an unavailable row into another
retention basis. Query cursors are bound to this representation version as well
as the existing owner/revision/source/retention scope; they cannot cross versions.

This is the smallest truthful compatibility correction. **Older closed clients
cannot display newly typed rows until updated**, and may show their generic
error for the explicit upgrade requirement. Do not claim an offline iPhone or
Watch works because a newer client decodes. A compatibility notice disguised
as an actual DJ direction or conversation would manufacture provenance; no
such relabeling, hidden row loss or privacy bypass is permitted. Actual old/new
native acceptance and coordinated deployment remain separate gates.

Current source qualification:46 owning tests PASS, including paired list,
detail/tail/anchor/search/open, both cross-version cursor directions, compatible
legacy pages, invalid versions, source withdrawal and privacy denial. An
independent technical review reproduced46 PASS with no remaining scoped P1/P2.
This is no installed producer pin. The existing Apple writer separately reports
real iPad read/reopen and stop/start/archive read acceptance of its baseline
decoder fix; neither that report nor local Core tests close the older HTTP404.

## Selected single-pipeline dialogue correction

Assignment `DJC-CORE-ASKDJ-CONTEXTUAL-DIALOGUE-V1-20261013` fixes the generic-versus-Session dialogue/acceptance split while retaining this delivered history/search foundation.
[Experience](ASK_DJ_CONVERSATIONAL_EXPERIENCE_V1.md) and [common producer contract](ASK_DJ_CONTEXTUAL_DIALOGUE_CONTRACT_V1.md) pin the design before runtime edits. They qualify one Ask DJ implementation and bounded common context; Session adds optional authority/context/Flow references only. The former quote-only reply, separate historywriter scope and broad Session lock are baseline findings to repair, not completed conversational intelligence. New narrow reactive CC0 processing supersedes only this document's earlier blanket no-model rule for those explicitly qualified facts; Spotify/archive scanning and unknown-source processing stay excluded. Literal search/navigation and old archive rights remain unchanged. Current qualification/publication is pending.

## Selected ambient producer convergence

[Ambient convergence v1](AMBIENT_FACT_MOMENT_CONVERGENCE_V1.md) removes independent proactivity from playback-status reads. Existing qualified Runtime/Planner/Knowledge/Moment/Flow/Broadcast publication remains the only unsolicited content path; generated Track Insight interpretation is not source-fact proof. Explicit Ask DJ and previously stored ambient/system records retain their contracts; no history import, filtering or new source/model is added. Core source #1158 is protected delivered as `6114c5a05600f6b066d4e1f057f236841fe4f574` with exact archive/formal readback PASS. Apple/joint qualification remains separately open; full narrative Stage4 is not promoted.


Assignment `DJC-CORE-SESSION-CONVERSATION-HISTORY-V1-20261008`, including literal
Session text-search addendum `DJC-SESSION-FLOW-TEXT-SEARCH-V1-20261008`.
Base `cb7bf8440c43d2c2f733bba3713b88c6b332c4da`. This is an early **draft**
producer contract. Exact producer SHA/state is pinned externally in #1101/#87;
it is not a main merge, installed HA-dev, native UI or live-provider receipt.

## Existing ownership and capabilities

The existing Session Runtime, persistent Session repository, historical
projection repository/query service, Ask DJ authority, HA Store and HTTP
transport remain owners. There is no second Runtime/chat backend/history store
or local consumer intelligence. The canonical storage/Session documents and
`SYNC_PROMPTS.md` point here. Old generic HA-user history is unchanged; new
Session conversations use a server-resolved `profile:` namespace in that same
Ask DJ Store. Timeline rows contain only conversation references, not a copy of
chat history. Music DNA opt-in is neither changed nor enabled by history queries.

Capability flags `session_conversation_history` and `session_flow_text_search`,
and matching `contract_versions` entries, are additive version1 fields in the
existing capabilities response. HTTP is the canonical history fallback.
Existing HA WebSocket Ask DJ delegates to the same message handler. New
history reads/search/open use HTTP; they are not Broadcast subscription commands.
Storage-not-ready returns503. An owner Session/history grant is required even
when a capability is advertised; guest/shared privacy returns403.

## Concrete routes and authentication

All new requests use the existing paired device bearer, exact `device_id` and
canonical `client_type`. GET identity may be in query plus existing device
header; POST identity is JSON. The actual paired device→Profile mapping wins;
client Profile/HA-user/room hints cannot select someone else's Session.
Profile/default privacy is the minimum, so a payload cannot upgrade guest/shared
access. All new Session JSON and contextual Ask DJ/history responses are
`Cache-Control: no-store`, `Referrer-Policy: no-referrer`, including errors.

| Route | Request | Response and authority |
| --- | --- | --- |
| GET `/api/djconnect/v1/session/history` | identity; optional `limit`, `cursor`, `include_active` | Recent owner Sessions, revision, next cursor,90-day retention. Default archive statuses ENDED/INTERRUPTED; explicit active inclusion remains distinct. |
| GET `/api/djconnect/v1/session/history/{session_id}` | identity; optional `limit`, `cursor` | Session header plus accepted chronological entry projections. |
| GET `/api/djconnect/v1/session/history/{session_id}/search` | identity; `q`; optional `limit`, `cursor` | Literal matches over authorized server entries, previews/highlights and honest coverage. |
| POST `/api/djconnect/v1/session/history/open` | identity; typed `action` | Revalidated Session+entry; navigation only, archive readonly; never starts playback or a Runtime. |
| POST `/api/djconnect/v1/ask_dj/message` | existing fields + required `client_message_id` for new contextual/history turns; `conversation_context` | Existing Ask DJ content route, confirmed turn/reference context and canonical conversation entry IDs. |
| GET `/api/djconnect/v1/ask_dj/history` | existing identity + `conversation_scope: profile` | Existing Store's bounded Profile conversation projection, not another Profile's or generic HA-user history. |
| POST `/api/djconnect/v1/ask_dj/history/clear` | existing identity + `conversation_scope: profile` | Clear only this Profile namespace; reference-backed timeline/search content withdraws. |
| POST `/api/djconnect/v1/voice` | existing WAV/identity; contextual headers below | Existing STT transcript→same Ask DJ message authority/turn path; no raw voice archive. |

`open_session` is a typed navigation action:

```json
{"kind":"open_session","session_id":"session-…","entry_id":"entry-…","navigation_only":true}
```

It is not a DJConnect playback command, Moment executable action, generic
execution/deeplink engine or credential. Unknown action fields are rejected.
Wrong Profile/missing/expired target produces `history_unavailable`404; an
explicit wrong Profile hint produces403. Opening always rechecks current data.

## Entries, turns and context

Session IDs are existing durable aggregate IDs. Entry IDs are durable server
projection IDs. `order` is the monotonically accepted chronological sequence
in that Session, independent of semantic live Flow placement and Broadcast
watermarks. Entry kinds are `playback_observed`, `dj_moment`,
`conversation_user`, `conversation_dj`. Every entry includes `occurred_at` and
`retained_until`, plus kind-specific permitted body fields. Conversation entries
also expose confirmed `turn_id`, role, input type, original message/client IDs
and server-validated context. Internal Store references are not client authority.

The additive request context is:

```json
{"conversation_context":{"session_id":"session-current","selected_entry":{"session_id":"session-current-or-old","entry_id":"entry-…"}}}
```

`session_id:null` means the current standalone conversation. A selected old
entry is only a reference: a new question is persisted in current Profile
conversation and, when supplied/valid, the current Session; it never appends to
an old archive. A supplied active Session must be the actual current Runtime.
Implicit playback context captures its item ID. Completion rechecks owner,
Session and implicit track; changes return `session_context_changed`409 rather
than silently attaching the answer elsewhere. An explicitly selected entry
remains the captured subject across a track change, subject to revalidation.

One Profile lock serializes contextual exchanges. Completed retries use the
existing history's client-message identity and confirmed request digest; changed
text/context under that identity returns `client_message_conflict`409. Confirmed
question/answer references are added in one existing SQLite transaction, after
the existing Store accepts the exchange. A storage failure is not success; a failed reference transaction removes its
new Store exchange. Completed retained exchanges are reused without repeating Ask DJ. No
pending client bubble or generated text is used to reconstruct Session identity.
The bounded existing1000-message retention remains; trimmed/cleared message
references have no searchable/renderable text. Clear also retains at most1000
opaque request hashes in that existing Profile Store state, including registered
in-flight requests. Replaying a cleared ID cannot resurrect its content; use a
new ID for a new question. No question text, raw identifier or model knowledge is
retained in those hashes. The short Store/reference acceptance commit uses the
existing Runtime lock so end cannot split an acknowledged Session turn; model
work remains outside that lock. Caller cancellation completes this whole short
acceptance unit, including reference storage and postguards, before releasing
the Runtime lock; repeated cancellation cannot orphan a Store-only turn.
Administrative global cleanup retains the same bounded request tombstones;
the legacy device-wide clear route leaves private Profile namespaces and their
clear revisions intact. Legacy ambient history writes exclude those namespaces.
Archives are not mutated by
later standalone questions. Private-session policy can answer without persisting.

For voice, `X-DJConnect-Conversation-Scope: profile` selects this existing
completion path. Send `X-DJConnect-Client-Message-ID`, optional active
`X-DJConnect-Session-ID`, optional `X-DJConnect-Entry-ID` and
`X-DJConnect-Reference-Session-ID`, and existing language/locale headers.
The transcript is handled as `input_type: voice`; `transcript` and
`recognized_text` remain compatible. No new TTS/provider/audio route is added.
Declared STT completion fixtures do not prove real microphone acceptance.

## Historical field qualification and privacy

Live source freshness/display deadlines and historical-use permission differ.
The older `native_delivery` grant alone authorizes no durable archive. This
candidate's archival mapper independently admits only already-qualified CC0
MusicBrainz/Wikidata normalized fields with exact matching original attribution,
and internally validated Runtime Session Direction text. Unknown/provider/raw
or unqualified source cards, Spotify album-release Moments and derived
Transitions do not become archived text. Both original links on a shared-producer
Moment survive independently qualified storage. Immutable Moment meaning and
Persona text stay unchanged; no generated text becomes identity evidence. All
history entries explicitly set `historical_view_only:true` and
`current_display_allowed:false`, including entries read during an ACTIVE Session.
Current native display always uses the existing live `native_delivery` grant;
an archive permission never restores an expired Now Playing/current contribution.

MusicBrainz [core data license](https://musicbrainz.org/doc/About/Data_License)
and Wikidata [structured-data copyright](https://www.wikidata.org/wiki/Wikidata:Copyright)
are field-specific CC0 bases; supplementary annotations/article text are not
substituted. Spotify [policy](https://developer.spotify.com/policy) permits
necessary personal-data retention with deletion on disconnect, and requires
attribution/content links. [Developer terms](https://developer.spotify.com/terms)
remain applicable. Historical playback entries are compact Core observations
of actual `playing` metadata tied to the underlying content/link, with no
artwork/audio/provider payload. Spotify attribution is explicit. They prove
observed playback, not full listening, provider occurrence identity or correct
repeat counts. Historical queries realize those results locally through the
existing Ask DJ authority; archive/Spotify content is not sent to a model.
The source/account revocation/deletion closure remains a final-qualification gate.

Owner questions, answers, searches, snippets, histories and links are never
published to VibeCast/room/guest Broadcast. Current shared Moments retain their
existing live source/dose/Persona/Flow semantics. A Profile can share legitimate
access across its mapped devices, never by equal display names or a HA-user hint.
All response data is temporary client projection; no disk cache is granted.

## Literal text search and paging

Search scope is exactly one authorized active or historical Session. It includes
eligible Moment and conversation text and displayed track/artist/album fields,
including entries outside already-loaded client pages. It calls no model/provider,
mutates no Session/playback/archived text, and does not activate Music DNA.

Matching is Unicode NFKC then casefold, without fuzzy/semantic expansion or
removing diacritics. Original stored text is unchanged. Highlights are original
UTF-16 start/length ranges at normalized character-cluster boundaries; Apple can
use NSRange without splitting a surrogate pair or combining cluster. Words,
substrings and phrases are supported. Up to100 highlights per entry are returned.

Entry/search reads scan at most250 rows per step; response `limit` is1–50
(default20). Results echo query and revision. Signed opaque cursors bind Profile,
Session, exact query/mode and revision. Invalid/changed cursors return409 and
require a fresh first page; restart invalidates process-local query cursors.
No Broadcast cursor or signing credential is persisted/exposed. Search
`returned_count` counts this page; `total_count` exists only for a wholly
scanned unpaginated result. `complete`/`next_cursor` distinguish bounded scans;
clients must not call an incomplete count total. Client request generation and
returned query/revision prevent an old response overwriting a newer search.
Archive navigation/search must preserve the active Session and reading position.

## Additive consumer alignment after the first immutable draft

The canonical HTTP capability response now advertises the same version1 flags
and `contract_versions` as WebSocket. Advertisement alone conveys no data grant.
The same timeline GET accepts `window=tail` or `window=anchor`, `limit`1–50 and,
for an anchor, `anchor_entry_id`. Do not combine a window with a page cursor.
`tail` scans at most250 latest accepted rows and returns up to the requested
number of qualified entries in increasing canonical `order`. `anchor` first
revalidates that owner entry, then returns it and later qualified entries in
increasing order, also with a250-row scan budget. Wrong/withdrawn anchors fail404.

Window responses retain `session`, `entries`, `revision`, and add `window`,
`anchor_entry_id`, `window_limit`, `scanned_order_min`, `scanned_order_max`,
`scan_complete`. `next_cursor:null` means a window, not full-timeline coverage.
`scan_complete` describes the bounded candidate read, not all Session history.
Reissue tail to discover fresh entries and anchor to revalidate a visible window;
merge only returned canonical entry IDs/orders and do not clear unrelated loaded
pages or move scroll based on this response. Concurrent mutation returns409 and
requires repeating that same bounded request. No private entry IDs are added to
Broadcast. A fresh tail uses no old revision cursor.

The independent early review's privacy/highlight gaps are repaired: effective
request privacy also gates Profile history/clear; completion rechecks current
Profile privacy before and after Store save; selected-entry answers retain
revalidated transitive dependencies; NFKC highlighting handles cross-character
composition. Store writers stage a copy under one writer lock and expose it
only after acknowledgement. Failed saves do not create cached deduplication
success; a rejected post-save grant rolls back to the previous committed Store.
This additive draft still requires the final acceptance work listed below.

## Connected withdrawal and lifecycle maintenance

Playback observations retain only a captured internal backend/account/provider
entry binding, never credentials. HTTP/query projection rechecks that original
account is active, still linked to this Profile, matches its original backend,
and retains the original configured source entry. A different current default
account never substitutes for that binding. Typed Spotify Repair state withdraws
its source authority without parsing error text. Internal bindings are omitted
from returned playback bodies. Grant changes participate in query revisions, including provider account
identity and persisted typed Repair state. Direct opens repeat the Session,
Store and grant revision check after projection, just like timeline and search.

The existing historical retention service now removes expired accepted entries
and corresponding projections, disables expired Session archive eligibility,
and advances revisions. Persistence bootstrap owns one hourly housekeeping
registration, preserves it on reload and disposes it at final shutdown; setup
also schedules a coalesced initial maintenance run. This is storage maintenance,
not a new DJ/assistant monitor. HA Store pruning removes expired Profile turns
and exchanges derived from withdrawn targets. Other HA-user scopes retain their
existing retention semantics. Source scans use bounded stable-ID batches;
permanent source-entry removal and confirmed final credential revocation erase
that source's playback rows in bounded batches within the canonical transaction.
Profile deletion erases only its own projections and Profile conversation scope;
device reassignment never transfers that history. Existing Profile personal-state
Ask DJ clear also clears the exact Profile conversation namespace.

Historical/Session turns are excluded from model prompt history. The actual HA
actor remains distinct from the server-derived Profile Store namespace. Private
Session minima cannot be upgraded by a later normal request. Confirmed implicit
playback dependencies are revalidated just like selected references; transient
audio, proxy media and executable controls remain in the live response, not the
new Profile archive. Historical
matching and selected-entry quotation use the qualified local realization through
the existing Ask DJ authority; archive records are not model input. Ordinary
HA-user chat prompt behavior remains unchanged. `input_type:voice` is confirmed
only by the existing server STT completion route; a JSON text client cannot claim
voice provenance. Synthetic STT fixtures prove that completion path only.

## Real producer receipts and qualification state

[`schema.json`](../../examples/client_contracts/session_conversation_history/schema.json)
and [`producer-receipt.json`](../../examples/client_contracts/session_conversation_history/producer-receipt.json)
are actual outputs of existing Runtime→SQLite→Ask DJ→query/application handlers
with bounded synthetic input. Session A records playback, a real proactive
Session Direction Moment and distinct text/voice-derived contextual turns. End
and a new persistence/query instance retain six ordered entries. A later question
finds Metallica on stored playback evidence and revalidates the readonly open
entry, without changing A. Additional tests use the actual existing voice
completion path and UTF-16 Unicode ranges. Fixtures are not personal history,
a live-provider run, HA-dev installation or native voice/UI acceptance.

Before tests fail against the exact base for absent list/timeline/playbackmatch/
open/search behavior; initial harness import/observation-name diagnostics are
retained separately and not called product failures. Old generic histories remain
in their existing authority; missing historical playback is never backfilled.

The connected producer is qualified through the real HA SDK HTTP router,
DJConnectRuntime bearer/identity checks, SQLite and HA Store reload in an isolated
networkless harness. [`http-producer-receipt.json`](../../examples/client_contracts/session_conversation_history/http-producer-receipt.json)
records eleven actual loopback requests and hashes of all executed integration
source, schema and harness files. Source/account registration and STT completion
are explicit synthetic fixture adapters; these receipts prove no provider,
microphone, installed HA-dev or native UI outcome. Unit regressions cover late
track/end/privacy/clear, rollback, idempotency, qualified dependencies, expiry,
Unicode and five locales. Native acceptance remains Apple-owned.

Final acceptance still requires independent exact-candidate review, all required
checks, protected source delivery/readback and mandatory Finalization. Every
later wire/rights delta is separately pinned; consumers never import mutable WIP.
Publication and installation each retain their specific authority. Stop after
this one selected Core assignment.

## Protected source delivery and Finalization

PR [#1132](https://github.com/pcvantol/djconnect/pull/1132) merged as
`30eba3749a5d16322b5bd45695e6adc25750805d` from exact reviewed
`19b815612319291cc7e4ab1fca4718667f173970` (equal tree
d08283c47ea75cf5e049cd22a9d2244f05110e52). The owner separately approved this
source merge/internal SHA publication and exactly two unused Xcode caches.
[Completion history](../history/prompts/2026-10-09-session-conversation-history-finalization.md)
records source/main artifact qualification and the independent review corrections.
This separate documentation Finalization still requires its own concrete
publication approval. No HA-dev installation, real microphone/provider or
Apple native acceptance follows from a Core producer receipt.

## Corrective HTTP Profile-history delivery — 2026-10-09

Actual Apple consumer finding6076360592 / #87 6076359873 exposed a gap omitted
from the original eleven-request HTTP proof: GET query scope/identity was
lost before the existing handler, returning anonymous legacy history instead
of Profile history. The bounded corrective assignment
`DJC-CORE-PROFILE-HISTORY-HTTP-SCOPE-FIX-V1-20261009` forwards only device_id,
client_type, client_id, conversation_scope, profile_id and privacy_mode, plus
existing integer since_revision. Owner/user namespace comes exclusively from
the authenticated existing handler, never query user_id/owner_profile_id.
Legacy unscoped behavior and the existing Profile-history50-message bound
remain unchanged; no new endpoint/history authority/client workaround.

Corrected actual-HA HTTP proof checks owner/message IDs, revision sync,
wrong existing Profile/clienttype/bearer, shared privacy, forged namespaces,
legacy isolation, reload, clear and an in-flight GET concurrent with actual
HTTP clear (409, no messages), then timeline withdrawal. Version1 schema
additively covers the existing Profile-history response. Source/account/STT
fixture adapters remain explicit; no native/microphone/provider/installation
claim. Exact corrective producer receipt, review, protected delivery and its
separate Finalization are bound through the owning issues; predecessor
qualification/cleanup receipts remain historical and are not reopened.

Corrective source [PR#1134](https://github.com/pcvantol/djconnect/pull/1134)
protected merged2337e06f514dfa2d847d9de26189a10bc618b555 from reviewed
4ada2b611f5195090bdb1fe52b28749ad539a100, equal treec61a74fa93fec1dc7e06316c4467f14f5e342818.
[Corrective completion](../history/prompts/2026-10-09-profile-history-http-scope-fix-finalization.md)
records exact software/producer and source/main qualification. This separate
Finalization needs its own publication approval; source approval is not inherited.

## Planned Session entry, history and native-surface refinement

The combined documentary decision `DJC-SESSION-ENTRY-LIFECYCLE-HISTORY-DESIGN-V1-20261012` (including Apple addendum C) is defined in [Session Entry Lifecycle Experience V1](SESSION_ENTRY_LIFECYCLE_EXPERIENCE_V1.md), [Session History Summary V1](SESSION_HISTORY_SUMMARY_V1.md), [Apple Session Native Surfaces V1](APPLE_SESSION_NATIVE_SURFACES_V1.md).
It preserves this contract and its delivered capabilities. New lifecycle replacement/intent operations, qualified history aggregates and passive native-surface rights remain **Planned**, with separate producer/consumer acceptance. Navigation is read-only; foreground owner display rights do not grant widget storage or category-invitation content. No Runtime, provider or consumer implementation is introduced by the design.

## Private Session summary acceptance v1

See [connected summary contract](SESSION_HISTORY_SUMMARY_ACCEPTANCE_V1.md)
and [summary projection](SESSION_HISTORY_SUMMARY_V1.md). Existing owners
provide a version6 compact Session aggregate and non-evicted bounded acceptance
keys; no full Moment-body archival right follows from a semantic count.
Registration and count commit together before Runtime publication/budget debit;
reads only project a provisional open Mood interval, without writes or providers.
Old stores remain unknown, restart leaves unobserved Mood time unknown, and
owner/source/privacy/retention withdrawal applies to derived totals.
No summary enters shared Broadcast, notifications or diagnostics.


## Shared reactive dialogue and bounded Moment drilldown

The selected [common Ask DJ contract](ASK_DJ_CONTEXTUAL_DIALOGUE_CONTRACT_V1.md)
uses the existing conversation owner for both screens; optional Session/Moment
context does not create a second pipeline. The [Moment Track Insight subset](MOMENT_TRACK_INSIGHT_DRILLDOWN_V1.md)
adds an exact, temporary owner read through the existing full detail service.
This is one bounded connected correction; full interactive/narrative maturity,
native adoption, entry/lifecycle and joint acceptance remain independently Planned/open.
No model/provider lookup occurs merely by rendering a navigation offer.

## Subject-bound Session artwork

The additive, independently scoped media projection and explicit historical
preparation are defined in [Session artwork delivery v1](SESSION_ARTWORK_DELIVERY_CONTRACT_V1.md).
It does not widen semantic text archival rights, native current-display admission,
shared-screen access or existing pure history-query semantics. Implementation
and qualification are owned by the admitted Session Moment artwork slice.

## Private installed compatibility follow-up

The minimal history-only derivative has now been installed and qualified on
HA-dev, separately from the full local source candidate. Capability2 and paired
v1/v2 protocol reads are verified; source/worktree fixture hashes must not be
misrepresented as that installed derivative's module hashes. Exact scope and
[installation evidence](../verification/HISTORY_ENTRY_COMPATIBILITY_20261018.md)
retain the private-development, original404 and native/audio boundaries.

## Selected manual deletion of an archived Session — 18 October2026

Direct owner request, verified in the existing Apple task: allow a confirmed
manual deletion of one earlier Session from the user's Profile. Core owns durable
erasure; Apple owns its red trash action, confirmation and localized rendering.
The whole/bulk producer is now implemented in the current Core source increment;
[qualification and delivery](../verification/OWNER_ARCHIVE_DELETION_20261021.md)
remain separate from installed/native acceptance. Individual content deletion is
still OPEN under #1225.
The existing history-entry representation2 and rolling retention remain separate.

Discovery: `capabilities.session_history_delete:true` plus
`contract_versions.session_history_delete:1`. No advertisement until the complete
producer operation is implemented and qualified. Absent/unknown capability means
no destructive action. No client-invented endpoint or automatic mutation replay.

`POST /api/djconnect/v1/session/history/delete`, existing paired device bearer and
identity, `Cache-Control:no-store` / `Referrer-Policy:no-referrer` on all outcomes:

```json
{"device_id":"<paired device>","client_type":"ios","session_id":"<earlier Session>","expected_revision":"<exact session.revision>","operation_id":"<new UUIDv7>","confirmed":true}
```

Only an explicit confirmed user action sends this request. The resolved paired
Profile is authoritative; a supplied Profile hint never chooses another owner.
`expected_revision` is the exact opaque `session.revision` from a fresh existing
authorized **detail** read before confirmation, negotiating history-entry2 when
required. The list currently returns an integer SQL sync revision; it is not the
delete compare-and-swap token. Do not convert that integer, parse or reconstruct
the opaque detail revision. A changed detail requires a new confirmation. `operation_id` is a new UUIDv7
for this deliberate operation, not a chat ID. Reuse the existing bounded operation
journal clock: five-minute lifetime and30-second future skew; no automatic
renewal or retry. The receipt binds the resolved owner and exact paired-device/
connection authority as well as the target/revision. The owner must still authorize any
reply, including replay of a completed receipt.

Success200 is returned only after durable erasure and grant fencing:

```json
{"success":true,"schema_version":1,"operation_id":"<same UUID>","owner_profile_id":"<resolved Profile>","deleted_session_id":"<exact target>","deleted":true}
```

The client verifies operation, target and resolved owner against its captured
request/connection epoch before removing that Session and returning to history.
Then refresh through existing reads. Do not clear pairing, all Profile history,
Music DNA, preferences or another Session. No playback, speaker or Session-start/
stop action belongs to deletion. Already delivered external audio cannot be
recalled by a history response; clients stop their own deleted-source replay.

| HTTP / `error` | Contract |
| --- | --- |
|400 `invalid_history_delete_request` | Missing/malformed target, UUID, revision or `confirmed:true`. No mutation. |
|401/403 | Existing pairing/Profile/privacy authorization errors; no personal target content. |
|404 `history_unavailable` | Unknown or other-owner target, including an independently deleted Session; no existence leak. |
|409 `session_not_archived` | OPENING/ACTIVE or actual active Runtime target; never end it implicitly. |
|409 `history_revision_conflict` | Target revision changed before durable commit. Refresh and require a fresh confirmation. |
|409 `history_delete_operation_conflict` | An existing operation ID is reused with different target/revision or device-binding inputs within the same owner. Cross-owner lookup remains404. No second effect. |
|503 `history_unavailable` | Definitive pre-commit storage failure, no successful erasure receipt. |
|503 `history_delete_outcome_unknown` | Completion is not yet proven. Do not claim deletion or automatically resend. Read-only refresh is allowed. |

Only ENDED/INTERRUPTED Sessions are eligible; the persistent and actual Runtime
lifecycle are checked under the existing owners at commit. Recording opt-out
must not prevent explicit erasure of one's already retained data. Within the existing journal lifetime, exact repeated
completed operation inputs return the same bounded durable receipt after fresh
owner authorization, without another deletion; they never recreate a Session.
The client never automatically retries this mutation after reconnect, timeout,
Profile switch or stale callback. A deliberate retry still needs user confirmation.

Erase the target's persistent Session, summary, Moment/observation/conversation
projections and corresponding Profile conversation data through existing owners.
Do not purge another Session or the Profile. Pending source/model/history writes
cannot recreate its content. Before success, revoke/fence all target history media,
speech/audio/cache/navigation grants, including in-flight prepare/read callbacks.
List/detail/tail/anchor/search/open/deep-link and old cursors must not recover the
erased target. Existing literal query authorization remains mandatory. No raw
prompts, text, images or audio are kept in the bounded operation receipt.

Qualification must use synthetic owner records and the actual storage/paired
handler boundaries: owner/cross-owner, all terminal/active states, stale revision,
duplicate/conflicting operation, concurrent acceptance/prepare/read/delete,
storage failure/unknown outcome, restart durability and all reopen paths. No real
personal Session deletion is authorized as a test by this contract. Producer
fixtures and exact qualified source/installed pin follow before consumer live GO.

## Selected bulk deletion of earlier Sessions — 18 October2026

The additional direct owner request is one confirmed operation that removes all
earlier Sessions from the resolved Profile, independent of the currently loaded
page, search filter or client. It is not a client loop over single deletion and
not Profile clear. This producer follows the single-deletion Store/SQLite recovery boundary; see
[actual source qualification](../verification/OWNER_ARCHIVE_DELETION_20261021.md).
Capability1 is distinct from individual-content deletion and installed acceptance.

Discovery is `capabilities.session_history_bulk_delete:true` and
`contract_versions.session_history_bulk_delete:1`. Missing/unknown version hides
the action. Single Session deletion remains a separate capability.

Immediately before showing confirmation, the paired client issues an owner-only
`GET /api/djconnect/v1/session/history/delete_snapshot`. This performs no deletion,
Session lifecycle or playback action. It returns:

```json
{"success":true,"schema_version":1,"owner_profile_id":"<resolved Profile>","snapshot_id":"<opaque server token>","target_count":12,"created_at":"<server UTC>","expires_at":"<server UTC>"}
```

The token binds the paired owner/device authority and the complete server-owned
set of retained ENDED/INTERRUPTED Sessions, with each exact internal/public
revision, at this preparation instant. No client IDs, filter, loaded list or
client clock defines that set. It expires after five minutes; a server restart or
changed device/owner authority invalidates it. Confirmation identifies the count
and this captured set. Sessions ending after preparation are deliberately outside
the confirmation and remain retained, even if they end before the user confirms.
The current ACTIVE/OPENING Session and another Profile are always outside it.
Zero targets permits a no-op informational result; do not offer a destructive
confirmation or issue the mutation. A refreshed snapshot requires new consent.

After explicit confirmation only:

`POST /api/djconnect/v1/session/history/delete_all`

```json
{"device_id":"<paired device>","client_type":"ios","snapshot_id":"<exact prepared token>","operation_id":"<new UUIDv7>","confirmed":true}
```

Use the same five-minute/30-second-skew journal and fresh authorization as single
delete. Bind operation receipt to owner, device/connection authority and exact
snapshot membership/digest; never re-resolve a newer set under the old consent.
At commit, validate every captured target's original revision and terminal and
actual Runtime state under the existing owners. A new terminal Session outside
the set does not conflict and is never added. A changed/withdrawn/already erased
captured target, stale token or privacy/source revision changes fail409
`history_delete_snapshot_conflict` before any target erasure. Refresh read-only
and ask for a new explicit confirmation; never replay the POST automatically.

Success200 only after the entire captured set is durably erased and fenced:

```json
{"success":true,"schema_version":1,"operation_id":"<same UUIDv7>","owner_profile_id":"<resolved Profile>","snapshot_id":"<same token>","deleted":true,"deleted_session_count":12}
```

Client admission checks owner, operation, snapshot, schema, exact captured count
and its connection/confirmation epoch. A valid receipt invalidates all local
archive projections, cursors, archive navigation and historical media/speech
leases and fences outstanding archive reads/prepares. Reload remaining archives
through normal owner reads; a Session completed after the snapshot reappears from
the server. An open archive returns to that refreshed list. Conservative archive
projection invalidation is not deletion of those newly completed Sessions. The
active Session's live Flow, current settings and live speech grants are separate
and remain intact. No oversized client-provided list or response list is needed
to revoke the captured archive view safely.

The producer erases only captured Sessions and their corresponding persistent
summaries, Moments, observations, conversation projections and Profile Store
turns. Reuse existing single-delete owners/fences as one server transaction, not
per-target commits that can partially succeed. Fence queued writers, history
media/audio, dependent references and retained replay before success. Preserve
non-target Sessions, Profile preferences, Music DNA, pairing, speakers and
playback. A conversation in a surviving Session that depends on a deleted target
loses that dependency's readable body/replay through the existing dependency
validator; never retain an orphan quotation. No original source text/audio goes
in snapshots or operation receipts.

Errors reuse single-delete authorization/no-store rules:400
`invalid_history_delete_request`;404 `history_unavailable` for unknown or
other-owner snapshot without disclosure;409 `history_delete_snapshot_conflict`;
409 `history_delete_operation_conflict` for altered same-owner operation inputs;
503 `history_unavailable` for proven precommit failure;503
`history_delete_outcome_unknown` for unproven completion. No partial success,
automatic replay/renewal or optimistic UI deletion. Only an exact completed
receipt may return idempotent success within its journal lifetime after fresh
owner authorization, without new erasure.

Connected qualification uses synthetic data: unloaded/filtered/page-boundary
archives; terminal snapshot and concurrent new completion; active/other-owner
isolation; target revision change; token expiry/restart/device change; duplicate/
conflicting operations; Store/SQLite/journal failure and unknown outcomes;
concurrent pending writes/read/prepare; durable restart and every reopen path.
No personal Session is deleted for qualification. Exact producer fixtures and pin
are pending; client UI tests do not establish producer or installed completion.


19October additive source derivative:
[retention-bases-v2-touch-20261019.json](../../examples/client_contracts/session_conversation_history/retention-bases-v2-touch-20261019.json)
retains exactly the delivered schema2 projection/speech outputs while pinning the
updated shared speech producer. Original schema1/schema2 receipts remain unchanged;
ephemeral touch reactions never become retained Session entries.


## Current Profile-default history readback — 2026-10-20

The current GET Ask DJ history handler treats an omitted conversation_scope as
profile, using the authenticated device's actual bound Profile. Explicit
conversation_scope: profile remains valid and produces the same namespace.
Explicit legacy scope requires an authenticated HA user; device-only legacy
requests return ha_user_required401 without messages. Clients must not interpret
an omitted scope as anonymous legacy history. This is a readback of the current
producer, not a new endpoint, identity override or cross-Profile permission.
The older corrective qualification above describes its historical source.

The current isolated HA verifier uses real ConfigEntries lifecycle and ordinary
pairing in both Profile and music-only modes, preserving the final stored-token,
owner, privacy and source fences. An actual HA no-tools agent class/static
configuration is registered, while response transport and STT remain explicit
synthetic fixtures. Its26/28 receipts prove the bounded loopback/history/reload/
clear path only; no API key, actual model, native microphone, installed client,
artwork/action lifecycle or audible acceptance follows. See the current
[afternoon qualification](../verification/CONTEXTUAL_DJ_AFTERNOON_20261020.md).
### Erasure safety foundation — source qualification, not producer completion

The [18October safety foundation](../verification/ARCHIVED_SESSION_ERASURE_SAFETY_20261018.md)
adds targeted Store pruning, pending-context/retry withdrawal and durable-header
checks for delayed projection writers. Client clear revision still advances when
stored exchanges disappear; a separate validated internal counter preserves the
privacy revision of independent accepted live speech. Normal/full clear remains
a privacy withdrawal. Unknown Store acknowledgements block stale history access
until the same Store owner reloads and reapplies the erasure.

These are internal prerequisites. Single/bulk endpoints, the durable cross-owner
operation coordinator, snapshot admission and all producer-completion gates
remain **OPEN**. Neither deletion capability is advertised. A protected merge of
this foundation cannot close the manual deletion function or consumer acceptance.
