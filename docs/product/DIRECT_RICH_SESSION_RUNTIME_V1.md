# Direct rich Session runtime v1

Implementation contract, source qualification pending. This new namespace serves
the ONE existing rich Session widget and rich Session Live Activity. It is not
an installed/runtime/provider/native acceptance record. The rich v1 format,
legacy passive projection, widget v2/v3, status8 and other permission families
remain unchanged. API receives no private rich text, image URL or pixels.

## Original direct purpose

Profile `djconnect-direct-rich-v1` independently selects local Session display
and direct reads. Authorization consumes genuine paired owner intent plus current
loaded owner/private-read policy, active original Session/Broadcast and actual
source/field eligibility. Request booleans, a legacy SurfaceGrant, token, UUID,
matching digest or metadata row alone supply no original permission.

The first supported receiver channel is the exact original paired HTTPS origin
with normal native certificate validation, fixed original URL, no redirect,
trust bypass or automatic cross-origin retry. Apple retains actual pre-await
request/owner/clock capture and authenticated channel result. Authorization
headers alone are not response signatures. Existing qualified local HTTP policy
is unchanged; this new rich profile does not select it for positive publication.
No new operator certificate or signing-key setup is required by this channel.

New original direct-purpose maximum: 28,800,000 milliseconds from pre-await Core
wall/monotonic capture. It is not copied from an old eight-hour grant. Each actual
field/frame/prepared cover keeps its own original observation and at most120s
or shorter original source/presentation expiry. New genuine observations may
change a frame within the SAME purpose; reads, new UUIDs, rotations, pushes,
reconnects and process launches never renew the original purpose maximum.
At that maximum, close without automatic reauthorization.

Initial local rich display permission precedes Activity.request; no future
Activity ID is required to authorize that decision. Only the actual returned
native handle/attributes/ID can bind subsequent updates. Existing legacy Activity
inventory is not silently adopted as this new original permission. Apple owns
actual migration/retirement, native once/UNKNOWN, clock mapping and SDK guards.

## Closed HTTP protocol

All operations are POST under `/api/djconnect/v1/session/rich/`:

| Operation | Exact request fields in addition to contract_version=1 | Authentication |
| --- | --- | --- |
| authorize | operation_id,device_id,client_type,session_id,surface,enabled,os_snapshot_cache,locked_display | Actual paired owner |
| read | purpose_id | Independent RAM rich-read credential |
| asset | purpose_id,frame_id,asset_id | Independent RAM asset credential |
| status, withdraw | operation_id,device_id,client_type,session_id,surface | Actual paired owner of ORIGINAL stored scope |

surface is widget/live_activity; client_type ios/macos, with live_activity only
on ios. Exact canonical header/body identity must match. Authorization is one
ASCII Bearer header. Native generates and retains one lowercase canonical UUIDv4
operation before scheduling. It does not reuse legacy UUIDv7 or retry with a new
UUID. Both enable/cache must be true; Activity also requires locked display.
Paired authorize/status/withdraw require exactly one X-DJConnect-Device-ID and
X-DJConnect-Client-Type, each equal to the closed body's actual paired identity.
Read/asset send only their scoped family credential and closed body, without
ambient paired identity/owner credential fallback.
Disable is negative withdrawal, not a new purpose.
Negative authorize consent never returns the active success variant: it closes
the exact owned local rich scope before remote bookkeeping and returns403
rich_not_allowed, without reserving a new purpose or issuing credentials. The
separate status/withdraw routes acknowledge original known management state.
No negative authorize error instructs parent unpair, re-authentication or retry
with a fresh UUID. Read credential prefix
`djcrichread_`, asset prefix `djcrichasset_`, each followed by32 independently
random bytes encoded as43 canonical unpadded base64url characters. They cannot
substitute for each other, legacy widget, ordinary app or HA credentials.

Before decode: request<=8192 bytes, strict UTF8, no duplicate/unknown keys,
nonfinite numbers, booleans-as-integers or nesting>8. No query credentials/body
logging. Errors contain only fixed machine codes; every response has no-store,
nosniff and no-referrer. No endpoint fetches provider/model data, warms a source,
loads a cold Profile, learns auth, produces a Moment or performs playback.

Authorize/read success EXACT keys: success=true,contract_version=1,profile_id,
operation_id,request_sha256,purpose_id,surface,state=active,
purpose_issued_at_ms,purpose_expires_at_ms,frame. Authorize ONLY additionally
read_credential,asset_credential. Original purpose times are ceil(original issue
UTC seconds*1000),floor(original expiry UTC seconds*1000), safe integers and never
read/response time. Exact represented arithmetic must be conservative.
Authorize request_sha256 binds the actual canonical authorize body; a read's
request_sha256 binds its actual canonical read body. Stored once request_hash
remains the original authorize digest. operation_id and purpose clocks remain
original across reads; a fresh request correlation is never a fresh purpose.

Status/withdraw known success EXACT keys: success,contract_version,profile_id,
operation_id,purpose_id,surface,state,purpose_issued_at_ms,purpose_expires_at_ms.
Status state active/withdrawn/expired/unknown; it returns neither frame nor secret
and is never positive permission recovery. A retained issued/reserved row without
its original live RAM handle reports unknown. Withdraw returns withdrawn after
synchronous local fencing and terminal metadata acknowledgement. Missing or
not-owned original operation returns404 rich_history_unknown without disclosure.

Error EXACT keys: success=false,contract_version=1,error. Allowed fixed codes:
invalid_request400,unauthorized401,rich_not_allowed403,rich_history_unknown404,
rich_asset_unavailable404,rich_purpose_consumed409,rich_frame_changed409,
rich_capacity409,rich_unavailable503,rich_frame_unavailable503. No raw exception
or private argument/body is returned. rich_frame_unavailable means a known
temporary frame/pending-write closure: preserve the original purpose deadline,
return no content, never reauthorize. rich_unavailable means terminal/lost/
uncertain purpose or owning lifetime: retire the rich scope irreversibly. A
403 rich_not_allowed is a local rich display/source denial, not an instruction
to unpair the parent device. No status-only handler invents parent unpair,
auth fallback, new UUID, new Activity or recovery authorization.
Asset success is original bytes with actual
MIME and the same closed response headers, never a JSON wrapper around pixels.

## Original once and ownership

Durable scope hash preimage is canonical JSON array:
`["DJC-DIRECT-RICH-PURPOSE-V1",pair_store_instance_id,persisted_auth_generation,entry_id,owner_profile_id,persistent_session_id,surface]`.
All coordinates come from real loaded paired objects and already acknowledged
PairJournal metadata. This endpoint cannot create pairing, Session, provider
source, that acknowledgement or a new consent UI. Random source UUID, memory
address, boot, transient settings revision and caller boolean are not scope keys.

Reserve scope and original operation before secret issue. Durable UNIQUE scope
and operation, max4096 retained records; no expiry eviction, row deletion or
fresh UUID to recover UNKNOWN. Schema20 metadata contains only hashes/UUIDs,
original issue/expiry and reserved/issued/withdrawn state. No credentials,
headers, rich text, pixels or retained runtime objects. Use actual platform
persistence transaction with FULL-sync acknowledgement and original pre/post
authorization guards; this does not claim physical power-loss/restore safety.
An uncertain commit/lost response consumes its original scope. Startup never
rehydrates positive ownership, secrets or clocks from metadata.

New pure paired capture independently checks one exact loaded supported entry,
real original token in runtime and entry data/options, current Profile/device
mapping, actual installation, retirement/transfer/unload state and persisted pair
generation. Do not widen old observe_pair or reinterpret its retired-family bit
as ordinary credential revocation. New-family capture has its own irreversible
negative latch and synchronous actual runtime-retirement hook.
The original ordinary pairing ACK also retains the actual persistence provider,
readiness object and database path from its genuine pairing continuation. Closing
and reopening that storage cannot turn an old RAM ACK into new-family identity
evidence, including when the first rich capture happens only after reopening.

Negative/history management does not require active Session, source, positive
consent or a read credential. It compares original owner/device/entry/Session/
surface/operation AND persisted pairing-generation relation. Same visible IDs
after re-pair do not take over another original generation's record.

## Purpose continuity versus attempt currentness

Ordinary mood/Persona/Presence/playback/observation changes preserve the original
purpose maximum. Each attempt captures exact current settings/three axes,
Broadcast/content epoch and real loaded committed Profile observation before
its first await and rechecks them after every await and at actual response.
Concurrent change closes that attempt, not the purpose; next pure read may use
new actual state under the same original purpose. No fictitious new observation.
Silence/music_only/current-content withdrawal retain existing field suppression.

Actual owner/privacy/source/account/pair/consent changes, end/replacement or
purpose expiration retire the entire scope permanently, including A->B->A.
Profile commit's synchronous hook compares security relation, not unrelated
cosmetic fields. Do not use old SourceAdoption.current as the new purpose's
lifetime authority: that separate family intentionally retires on normal style
changes. Do not pin global storage revision for eight hours.

Actual profile_observation.capture_committed is required per attempt: no pending,
queued, uncertain, split-anchor, replaced-manager/store, cold or uncommitted
Household may produce a frame/secret/pixels. Preserve original owner/manager/
store/lifetime while later genuinely committed aesthetic snapshots may differ.
Known in-progress writes suspend positive attempts; unknown/uncertain/owner loss
irreversibly retires through the real lifetime hook. Equality cannot rearm it.
Local withdrawal closes/scrubs/cancels before any awaited terminal write; late
commit/error/cancel cannot restore original clock, credentials or permission.

## Closed frame and prepared artwork

Frame exact fields: schema_version=1,binding_id,generation,session_id,
delivery_sequence,frame_id,state,observed_at_ms,expires_at_ms,playback_state,
mood,presence,persona,contribution,now_playing,artwork,contribution_status,
now_playing_status,artwork_status. No native uptime/as_of/ambient Profile data.
binding_id=purpose_id; generation is one original independent server UUIDv4.
Times are ORIGINAL broadcast observation and min(original+120s,purpose expiry),
with ceil observation/floor expiry. Native independently maps original source
and per-field bounds; Core never manufactures receivedAt/receivedUptime/rho.

Contribution/music reuse unchanged actual passive-v2 source/field selection,
not its grant or credential. Contribution exact keys: moment_id,published_at,
text,persona,source_attribution,usage_basis,expires_at,rights. Research adds ONLY
sources,expression_license and retains revision_url in source_attribution.
Ordinary sourced attribution is provider,url,license; actual Runtime-authored
direction has the exact empty attribution object and its own usage_basis.
Research sources preserve
the existing exact SOURCE_FIELDS and mandatory CC-BY-SA attribution. Text<=640
Unicode scalars/2560 UTF8 bytes; no summary/truncation to fit. Invalid/unsupported
content is unavailable, never a relabelled partial fact.
Music exact keys: item_id,subject_uri,track,artist,album,observed_at,expires_at,
source_url,attribution,usage_basis. Each optional field is independently null or
the actual qualified unchanged source structure; source times remain original
timezone-aware ISO8601 strings, explicitly not Foundation Date numbers.

Artwork0..2 independent slots. Exact keys: slot,asset_id,subject,role,
media_revision,captured_at,expires_at,source_url,attribution,alt_text,width,height,
crop_allowed,usage_basis,rights,bytes_sha256,byte_length,mime_type. Omit the legacy
image_path. Subject EXACT provider=spotify,uri,type plus optional album_uri;
role contextual_cover/current_cover; slots contribution/now_playing.
Rights EXACT passive_cache=true,os_snapshot=true,external_relay=false,
watch_replication=false. Five alt_text keys en,nl,de,fr,es and original Spotify
source/mark survive. No artist-photo/owner-URL/relay permission inferred.

Use already prepared PNG/JPEG original bytes<=256000 per slot, each dimension
1..4096, product<=16000000, one complete image. Native independently validates
original bytes before staging; actual serialized native successor cache<=1000000.
Core JSON reply<=16384 UTF8 bytes. Wrong/unsupported art clears only its slot;
independently valid text survives. New asset read validates exact current frame,
registry object/subject/slot/media revision/original expiry/authority and original
digest/length/MIME before returning those unchanged bytes. No on-read decode,
recode, URL fetch or historical image archive. New frame invalidates old slots.

## Primitive domain and canonical equality

Strict UTF8, no normalization/coercion/floats anywhere in this new wire. All keys
ASCII; safe integers actual non-Boolean0..9007199254740991. All UUIDs canonical
lowercase v4. session_id1..128 ASCII alphanumeric/underscore/hyphen; asset_id32
base64url; media_revision/item_id lowercasehex24; digests lowercasehex64.
Other IDs<=128 characters, URLs<=2048 UTF8 bytes, ordinary labels<=512 UTF8 bytes.
Total cap applies without dropping mandatory attribution. mood {value:null-or-
chill/groove/energy/party,revision:safe int}; presence music_only/occasional/
balanced/presenter; persona home_dj/radio_dj/club_dj/festival_dj; playback
playing/paused/stopped/unknown. Unknown values do not escape into response JSON.

Each field status exact {state,reason}. Pairs: available/qualified;
suppressed/presence_music_only or intentional_silence;
stale/original_snapshot_expired; unavailable with source_not_qualified,
original_deadline_expired,copy_too_long,representation_not_supported,
no_publication,no_observation,subject_changed,playback_inactive,
no_eligible_context,not_prepared,no_matching_subject,asset_not_supported.
Stale frame clears text/music/art and keeps original observation,expiry,sequence;
repeated stale reads do not anchor to now. Whole-purpose withdrawal has no frame.

The machine schema has a closed root union and compiled operation-to-named-
definition bindings. A consumer MUST select its exact operation's request or
response entrypoint; the whole union is not an endpoint authorization selector.
Operation response bindings name the positive variant only; every non-2xx
response uses only error_response, never an inferred success or fallback.
Raw byte/duplicate/numeric-token preflight precedes schema validation: ordinary
JSON Schema integer semantics alone cannot distinguish lexical1 from1.0.

Canonical request/frame hashing: recursively validated domain, UTF8 sorted-key
compact JSON, ensure_ascii=false, no BOM/newline/normalization, allow_nan=false.
frame_id hashes ALL frame fields except itself; no delivery-time member exists.
Identical actual source therefore yields identical equality token. Active->stale
changes it once. Per-field original source expiry is bounded by frame and purpose;
local native render caps never replace the recorded source observation/expiry.

## Delivery boundary

Actual HTTP/SQLite/pure projection/registry implementation and causal isolated HA
tests, independent whole/exact reviews, protected Source plus own originals and
separate Final plus own originals are required. Software fixtures do not grant
original native clock/storage/SDK/OS lifecycle, actual APNs enrollment/custody/
host-app token/environment/provider delivery or physical receipt. No operational
activation, key generation or duplicated deployment is part of this increment.
Existing24 requests/nine gates, Help/free AskDJ/VibeCast/Pi/HA scopes are retained.

## Current source composition (unreleased)

The current candidate now composes `direct_rich_context` with the actual
`RichPurposeJournal` and `DirectRichService`, created only by normal integration
setup after persistence initialization. Five registered `DirectRichView` routes
use original pre-body UTC/monotonic capture. An original scope is latched before
the first journal await; reserve and issued acknowledgements precede independent
RAM-only read/asset credentials. Local context retirement closes credentials
synchronously before remote bookkeeping. Management uses the actual committed
paired owner without requiring an ACTIVE Session; metadata never restores a
positive purpose or lost secrets. A negative authorization also retires its exact
stored scope after a process restart, without issuing a new purpose.

`direct_rich_frame` projects the already accepted Session, original field
observations and existing prepared assets. It creates no image registry and
fetches no content. Original complete PNG/JPEG bytes and actual dimensions are
verified; unsupported cover bytes omit that cover only. Frame hashes include
original observation time, so a genuine same-content observation may change the
frame while retaining delivery_sequence and the original purpose deadline.
The warm service retains at most32 purpose attempts per setup lifetime with no
eviction or refund; durable metadata retains its independent4096-record limit.

These are candidate implementation facts, not protected Source, installed HA,
original native clock, provider admission or iPhone acceptance. In particular
Python monotonic values do not establish a rate bound to Apple's Mach continuous
clock. The genuine cross-domain rate/suspend profile and actual API operator,
native enrollment and signed APNs environment remain separate required inputs.
