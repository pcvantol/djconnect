# Ask DJ live Help context — wire version 1

The two-owner R5 design review names this protocol revision; the actual wire
`schema_version` is **1**, not 5. This source contract accompanies the EN/NL
catalogue revision2. Normal protected Source/Final, installed readback and owning
Apple adoption remain separate release gates. The original EN/NL40 content run
40320113775 passed all40 cases with70/70 SDK responses; both Root and independent
ALL40 editorial reviews accepted it. This qualifies28 EN/NL entry-locale leaves,
not the42 unchanged pending DE/FR/ES leaves or real provider/device operation.

## 1. Read and exact query grammar

Source endpoint: `GET <paired-api-base>/ask_dj/help-context`. Existing credentials and paired origin policy, no learning of device identity, no cross-origin credential redirect, request/response `Cache-Control: no-store`, no cache or persistence. No GET body. The exact decoded query-key set is seven required keys plus one optional key:

| Key | Required | Value after exactly one normal URL-query decoding pass |
| --- | --- | --- |
| `schema_version` | yes | literal ASCII `1` |
| `request_id` | yes | fresh canonical lowercase UUIDv4, exactly 36 ASCII bytes, standard hyphen positions/version/variant |
| `surface` | yes | exactly `ask_dj` or `active_session` |
| `language` | yes | exactly `en`, `nl`, `de`, `fr` or `es`, matching adopted catalogue family; no locale normalization/fallback |
| `catalogue_id` | yes | exactly `ask_dj_examples_v1` |
| `catalogue_revision` | yes | canonical ASCII decimal `[1-9][0-9]{0,9}`, numerical range 1...2147483647, parsed strictly to integer |
| `catalogue_sha256` | yes | exactly 64 lowercase ASCII hex characters and exact adopted content hash |
| `session_id` | no | existing opaque own-session identifier, 1...256 UTF-8 bytes, no Unicode control scalars, no leading/trailing whitespace, otherwise exact/no normalization |

Reject duplicate decoded keys (even equal values), unknown keys, empty required values, malformed UTF-8/percent encoding, invalid grammar or oversized query (4096 encoded bytes). Validate a multi-value query collection before converting it to a dictionary. Encode literal plus as `%2B` under standard query encoding; never repeatedly decode or trim/coerce a value. No `true`, float, sign, exponent, whitespace, leading zero or Unicode-digit revision. Omission is the only no-session representation; empty, `null` and `None` strings are not omission. Session authorization is required in addition to syntax; exact comparison is against committed existing owned active-session state.

`ask_dj` without a session is Profile-global and has no current-session/track-dependent eligibility. `ask_dj` may explicitly carry the already observed own active session to obtain contextual entries, binding the observation to that session. `active_session` requires that session parameter. Core never substitutes an active session or another owner. One surface/session observation cannot serve another. No caller Profile UUID, model/provider/task setting, or arbitrary language/clock parameter.

## 2. Closed JSON response shapes

HTTP 200 JSON is a UTF-8 object of at most 16384 bytes, with **exactly these ten keys in both positive and negative cases**. JSON object key order is immaterial; duplicate JSON member names, unknown keys, missing keys and invalid types fail closed. All integer fields below require integer JSON number syntax and range, not bool, float/exponent or numeric string. No permissive default/coercion.

| Key | Positive (`available:true`) | Negative (`available:false`) |
| --- | --- | --- |
| `schema_version` | integer 1 | integer 1 |
| `request_id` | exact request UUID string | exact request UUID string |
| `surface` | exact request enum string | exact request enum string |
| `language` | exact request language string | exact request language string |
| `session_id` | exact requested session string, or JSON null if omitted | same echo rule |
| `track_id` | existing permitted current-media ID string, or JSON null | JSON null |
| `catalogue` | exact nonnull descriptor defined below, qualified true | descriptor or JSON null under the rule below |
| `available` | JSON bool true | JSON bool false |
| `observation_id` | fresh per-response canonical lowercase UUIDv4 string | JSON null |
| `eligible_entry_ids` | canonical ordered array defined below; may be empty | empty array |

Descriptor is **exactly FIVE existing fields**, deliberately retaining Apple's current Descriptor shape instead of inventing a sixth: `schema_version` integer1, `catalogue_id` exact string above, `revision` integer1...2147483647, `sha256` exact lowercase64hex, `qualified` JSON bool. No `status`, sixth field or unknown/duplicate members. Positive descriptor must equal the request's exact adopted source tuple, be producer-qualified and independently match the locally bundled qualified source. Negative descriptor is either the same exact requested tuple with qualified true/false when that source can safely be established, or explicit JSON null otherwise; never omit the key, return a different pin, or use it as an adoption offer. Negative options are empty regardless of descriptor. The private draft is not made qualified by this shape.

`eligible_entry_ids` has 0...14 strings for the current 14-entry catalogue. Each is 1...64 ASCII bytes, `[a-z][a-z0-9_.-]*`, an exact known ID in the pinned catalogue, once only. Array order is strictly the original catalogue entries' order, not lexical order, priority or selection order; unknown/duplicate/out-of-order entries invalidate the observation. This is an eligibility set serialized canonically, not a recommendation ranking. A future larger catalogue requires an explicitly reviewed bound change, no truncation. Media ID uses existing permitted identity semantics bounded to 1...1024 UTF-8 bytes, without control scalars or leading/trailing whitespace; no guessed/normalized identity. Track is nonnull only with a nonnull own active-session binding and its committed current media. Null track excludes entries requiring current-track context, even if local metadata remains visible.

Malformed request: HTTP400; missing/invalid/foreign authorization: existing HTTP401/403 policy with no positive body; optional scoped session lost/mismatched or committed observation unavailable: closed HTTP200 negative shape. Existing transport errors/non-200/decode errors close presentation. No new pairing-reset/configuration-repair behavior. When authorization is unknown, do not echo sensitive subject or return a fabricated negative observation. Observation UUID is presentation correlation only, never execution, model, pairing, push or bearer authority. Do not persist/log personal joins.

## 3. One base Help list, additional chip slots

Define server `eligible_entry_ids` as **base Help eligibility** for the exact source/surface/language/committed owner/session/configuration snapshot: the existing `for_help=True` behavior, including generic localized slot labels. It does NOT require filled artist/other slots merely to advertise a generic Help example. It DOES retain real existing route requires/contracts/current-context requirements. Generic slot labels do not invent a current track, artist, session or capability.

Core additionally gates **every actually model-dependent route class** against the genuinely qualified selected task/provider/model/effort/settings/prompt profile before including its ID. Root identifies `play.artist` and `play.quiet` as actual model-handover routes although they do not declare `agent_available`; checking only the two declared agent entries would be wrong. The internal dependency map must derive from reviewed actual route execution and receive coverage for all14 entries/70 localized cases, including negative configuration classes. No changing catalogue questions, entry IDs, requires or routes as a shortcut; no global agent boolean/medium-label grant. Missing qualification or an unclassified dependency closes affected entries.

Apple Help renders locally from exact pinned templates/group labels/generic slot labels, intersected with this server list and independently available local owner/surface/runtime predicates. It does not apply chip filled-slot constraints to generic Help. Server-only configuration/agent predicates are satisfied solely by the qualified per-entry server decision for that observation, not by setting a global `agent_available=true`; other local predicates remain additional narrowing constraints. This precisely replaces the current permanently-false agent gate only in a future reviewed adoption. It is not permission to bypass a missing observation.

Chips apply that same base ID list, then the existing `for_help=False` additional safe-filled-slot validation and independently current matching session/track/slot identity, then existing three-entry diversity selection. Generic labels never enter an executable draft. No arbitrary server text/sections in V1. Core typed Help uses the same base predicate and generic slot-label projection; parity is for equal snapshots, not different-time observations. Ordinary Ask DJ messages remain independent of observation IDs.

## 4. Original lifetime, revocation and click semantics

Proposed lifetime remains **15 original local logical seconds** from immediately before dispatch, measured using an injected continuous/monotonic clock. No server UTC, arrival renewal, playback30s reuse or assumed physical rate bound. Request generation/owner/surface/session/track/locale/connection/foreground/settings state is captured before await and rechecked on receipt. Changed then restored values cannot restore an old generation. Clear old positive state when invalidated or starting a required fresh open/read; no fallback to an earlier observation on error. A response at or after the original deadline is invalid.

Owner/binding/session/track/locale/settings/connection/background changes and received relevant configuration invalidations revoke immediately upon observation, even frozen/drafting/reading. Foreground requires a new read. V1 adds no event transport and cannot promise immediate remote-change detection: absent/lost events allow stale presentation only until the original logical deadline. Expiry hides without automatic polling, refill, rotation, Send or renewal; new explicit Help open/surface visit/user refresh/chip click can read again. Render/progress/callback traffic cannot refresh. Recheck deadline on access/render/tap; scheduler suspension confers no authority. Physical timing/suspend behavior requires separate acceptance evidence.

Suggestion strips are exactly three or zero, including partial revocation during frozen state: if any retained chip is no longer valid, hide all three without frozen refill. Help reference sections can have fewer examples and remain independent of that count rule. On click disable duplicate clicks and capture original ID/prompt/trio, owner/subject/generation and empty-draft edit revision; perform a fresh read. Only if the original chosen prompt and all three retained chips remain valid under the new observation and unchanged local state may the original prompt be copied to the draft. Failure, expiry, changed draft or revoked trio copies nothing, does not rotate to another item, and preserves user draft. Never autosend. Existing Send uses ordinary Ask DJ and server-side execution checks; the state may change after observation and before Send.

## 5. Implemented read boundaries and qualification class

The integration's normal `async_setup` establishes one committed Profile
observation owner. Weak keys and weak values in the registry plus an independent
outside-domain witness bind that original HA lifetime. A reader, storage factory,
entry setup or successful later load cannot bootstrap or repair missing history.
A pre-existing untracked storage manager remains unavailable until a genuine new
HA startup. This conservative first-flow boundary preserves existing Profile
operations; Help does not warm storage. Public HA's once-per-component setup
future is the supported lifecycle boundary, not arbitrary manual setup after
complete deletion of Python history.

Both real storage factories publish through one revision hook. Every supported
Household stage/restore/commit advances revision before publication. Queued,
in-flight and compensating load/save/onboarding transitions retain the original
owner; failures or cancellation uncertainty remain closed across replacement.
Hassless staging has no observational authority. Missing/split anchors, module
reload, manager/Store replacement, pending writers, uncommitted state and unknown
selected runtime/source metadata produce unavailable observations. Ordinary
storage locks, shielded writes, compensation and execution behavior are retained.
The bounded guarantee covers supported writers and lifecycle hooks, not arbitrary
mutation of every private Python field.

The read uses exact already loaded entry/device/token/Profile bindings and the
current selected provider/account chain. It rejects transfer fences, stale
provider references, retired entries, unknown auth and ambiguous identity. It
never calls the learning authenticator, `DJConnectRuntime.config` (which may
construct adapters), a storage factory, Store I/O, provider/model or recovery.
Explicit Session reads require its committed current source tuple, settings
state and original wall/monotonic media/Forecast deadlines. Global reads never
borrow the active Session. The detached body is serialized and checked again
without an await; no original deadline is renewed by projection or receipt.

All14 entries have an explicit internal configuration class. The four actual
model-dependent routes are `play.artist`, `play.cooking`, `play.quiet` and
`listen.artist`, including the two whose historical requires omit agent metadata.
They require the loaded official HA2026.10 OpenAI conversation entity and matching
explicit public AI Task: `gpt-6-luna`, `medium`, exactly3000 output tokens,
store/web/code tools disabled, no household LLM API, the exact qualified static
music-only prompt, and matching public entry/subentry/registry revisions. The
conversation provider's pinned absent service-tier default is `auto`; the Task
must state `auto` or `default`. Unknown, legacy, mismatched or changed-and-restored
configuration closes those four entries. The ten direct-read routes do not
inherit the qualification harness's language-judge dependency.

The current per-entry configuration mask is shared by R5, typed Help and the
reference chip selector. Free Ask DJ Send is not restricted to catalogue questions
and requires no observation ID. Generic Help placeholders never imply a filled
current artist slot or an automatic send.

The catalogue's additive `qualification_evidence` object records original content
and editorial receipt hashes and the per-locale scope. It is evidence metadata,
not a sixth field in the closed five-field R5 descriptor, a provider-health claim
or permission for Apple to adopt an unreviewed pin. Existing templates, IDs,
routes, requires, order and the42 pending locale objects are preserved.

## 6. Evidence and remaining gates

See the corresponding EN/NL publication verification record for exact original
run/artifact/report/editorial hashes and the semantic bridge. Actual isolated HA
R5 tests include loaded public Task metadata, paired loopback HTTP, committed
Store, unknown/configuration/transfer/writer/expiry negatives and no-effect read
instrumentation. These cost-free transport/guard tests do not replace the
original paid content result and are not native, audio, APNs or installed proof.
Apple owns bounded client-clock/decoder/UX tests and exact catalogue adoption.
