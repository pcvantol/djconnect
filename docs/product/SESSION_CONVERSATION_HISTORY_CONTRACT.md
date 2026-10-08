# Session conversation and history — connected Core candidate

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
the existing Store accepts the exchange. A storage failure is not success;
retries reuse retained canonical exchange data without repeating Ask DJ. No
pending client bubble or generated text is used to reconstruct Session identity.
The bounded existing1000-message retention remains; trimmed/cleared message
references have no searchable/renderable text. Archives are not mutated by
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
Persona text stay unchanged; no generated text becomes identity evidence.

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

This early candidate is **not final acceptance**. Bounded whole-archive paging,
physical retention/deletion/account revocation closure, stronger race/save-failure
and privacy negatives, HA SDK/HTTP integration and independent exact review are
still required before final freeze. Later additive or rights changes receive
an explicit pinned delta; consumers never import mutable WIP. Source/Apple
contract/native product evidence remain separate. Source and Finalization
publication and installation each need their specific authority. Stop after
this one selected Core assignment.
