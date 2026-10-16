# VibeCast HA display admission B v1 — review candidate

Part of `DJC-CORE-VIBECAST-DISPLAY-ADMISSION-V1-20261016`, existing Core
writer, base1329ad1ce8bd066d65a08b3988261a44e2cac730 and draft1197.
Status **B_CORE_SOURCE_GO / DRAFT_NOT_MERGED / A_UNAVAILABLE**.
Exact B-design `ae2adfe9e162a00d00715e26418656976b6f02a2` received independent
technical/privacy and product/UX/privacy GO after the three concrete findings
were fixed. Independent isolated Core B implementation may proceed while A is
fully unavailable; no A crypto/profile value is a prerequisite for that work.
Current B source implementation includes Runtime-owned in-memory authority,
normal paired-owner fences, closed transitions, bounded HTTP/snapshot delivery,
one WSS writer per display and a thin host over the maintained shared renderer.
Its own isolated real HA HTTPS probe exercises ordinary pairing, Session start,
claim/resolve/explicit approve/one-time collect/renew, snapshot/live, Mood update,
socket replacement, revoke and Session end. Only external provider I/O is a
fixture; the pairing, Profile storage, Runtime and HTTP/WSS chain are real.
Chromium/WebKit exercise admission, current playback, an actual published Artist
Moment with unchanged text/source link, portrait/landscape geometry and clearing
at ordinary Session end. Their served app bytes match the separate static build
and its manifest digest; this is not receiver deployment/adoption. Normal product
registration is now connected and independently exercised by the real HA probe.
A bounded70.466s single-viewer run measured74 frames, three renewals, a256KiB peak
projection reservation, seven sampled HA tasks and292KiB RSS high-water increase.
Real preauth source-capacity denial/released slots and owner-effect denials pass.
Both browsers clear offline, recover a fresh live snapshot and discard the
originally expired Moment without clock rewriting. Combined owning coverage is
88%, including real-HA and adapter execution. Independent technical/privacy and
product/UX/privacy source reviews GO on candidate325aabc7, whose integration tree
equals producer3cb9cf12; A and broader maximum-load/public-route/native/joint
qualification remain open. B support discovery is declared, without asserting
route/consent/admission availability. This is B software evidence, not complete
product acceptance. Unit tests alone are not HA auth or product acceptance.
This refines the [parent admission contract](VIBECAST_DISPLAY_ADMISSION_V1.md),
not a second assignment. No endpoint or capability below exists merely because
it is described here. A's unresolved trust/profile/wire remains a separate gate;
this document neither authenticates A nor selects a crypto library or TV input.

## Authority and identity

The existing HTTP transport-capability projection adds
`session_broadcast.paired_display_admission` version1; HA WebSocket discovery
uses `fallbacks.session_broadcast_transport.paired_display_admission` with the
same value. `supported:true` declares
the implemented B protocol, not configured external reachability, an active
Session/share, consent, successful admission or A availability. The object has
`availability:"owner_context_required"`, `owner_context_path`, `entry_path`,
`requires_external_https:true`, owner/display authentication kinds,
`read_only:true` and `rendezvous_a:false`. The paired client must read owner
context and handle `display_external_url_unavailable`/current authority errors;
it must not construct/guess a destination from discovery. No concrete HA URL,
identity, credential or Session is exposed by capability discovery. Both
transports serialize the same declarative source. This B-only discovery is
independent of A and gives old consumers no new mandatory behavior.

B runs only at the selected HA HTTPS origin after an explicit owner action.
No A code, API state, redirect, QR, owner Broadcast token or invitation is B
authority. A display receives a new read-only principal with no reaction,
Ask DJ, settings, playback, queue, output, volume, share-close or Session-end
permission. Current owner routes continue using ordinary paired device auth.

Reuse the existing SessionRuntimeManager as Session/share state owner and
existing Flow/Broadcast as publication owner. No second planner/eventbus or
general token authority. New B state is bounded, memory-only and forgotten on
HA restart, last unload or Runtime end. No Runtime serialization or historical
display registry is introduced.

`issuer_epoch` is32 random bytes encoded base64url, generated once for this
loaded integration process, shared by B records and rotated on restart/unload.
It is a local stale-state fence, **not a persistent HA ID, signing key or A
trust anchor**. The independently authenticated selected origin supplies B's
installation boundary. The relay `ha_install_id` stored per config entry is
not redefined or migrated. Internal records also bind the exact approving
entry/generation, pairing-token fingerprint, current device→Profile binding
generation, Profile/Session, source/account/privacy and share consent.
These private identifiers/fingerprints are never sent to displays.

Owner context resolves current normal pairing and device-bound Profile. Reuse
the qualified checks underlying PairedAuthority; do not make display access
depend on permission to archive/read owner conversation history. Revalidate
after every await and at the commit/release boundary. No stored plaintext owner
bearer is needed in a display record. Revocation uses current loaded entries,
pairing fingerprints, Profile/source bindings and Runtime generations.
Capture the authenticated entry/token/generation before the first Profile await;
never adopt a replacement pairing from an in-flight old request. Reuse the
existing ProfilePlatformStorage `authority_revision` as the conservative monotone
withdrawal fence. A committed Profile-store change invalidates old B authority,
including A→B→A changes between reads; it requires fresh explicit admission.
This does not change or end the active Session. Ordinary Runtime Mood/Persona/
presence updates are not Profile-store commits. Once a validator observes loss
of authority it stays invalid, even if current fields later revert.

## Fixed proposed bounds, subject to independent design/load review

| Resource | Proposed v1 bound |
| --- | --- |
| Pending claims |64 globally,3 per network source; no eviction of another live claim |
| Claim/code lifetime |120s original monotonic deadline; no renewal |
| Code | Exactly six ASCII digits, CSPRNG; unique among pending claims |
| Claim ID / secret / browser nonce | Independent32-byte CSPRNG values; ID is not authority |
| Failed approvals |5 per claim and10 per current owner per60s; generic errors, no enumeration |
| Throttle bookkeeping |256 unexpired owner-window entries; deny new keys at capacity, no eviction/reset |
| Active shares | One per Runtime,16 globally; explicit owner consent only |
| Active/approved display reservations |8 per share,64 globally, included in capacity before collection |
| Share absolute lifetime | Explicit owner choice120–28,800s, default7,200s; never beyond Session end |
| Display online lease |60s, renewal request at20s; bounded by original share expiry and current authority |
| HTTP JSON / WSS preauth |4KiB body/message; first authentication within5s;16 preauth sockets globally,2 per source |
| Live displays | One live socket per display; new authenticated connection supersedes old connection generation |
| Outbound data |128KiB maximum serialized snapshot/frame; truncate nothing that removes attribution or changes facts |
| Writer backlog |16 frames and256KiB per display,4MiB globally; bounded reservations before allocation |
| Projection/write work | One writer and at most one current projection per display;8 projections globally; no task per event |
| Slow consumer |5s send timeout; overflow closes connection1013 and clears viewer state; no unbounded catch-up |

These are testable policy proposals, not measured qualification. Legacy handoff
300s/global64 behavior does not prove the new bounds. Derive wall-clock expiry
labels from the same captured monotonic deadline; equality means expired.
Network source is rate metadata, never identity or a spoofable forwarded header.
The hard global bound applies even when source attribution is uncertain.
An exhausted owner throttle denies further attempts without extending any claim.

## Proposed routes and closed request shapes

New routes use `contract_version:1` and reject unknown authority/effect fields.
All responses carry no-store, no-referrer and nosniff; the shell has a reviewed
self-only CSP. No cookie authentication, wildcard CORS, credentials in URLs,
localStorage/sessionStorage, analytics or payload logging. Browser POST and WSS
requests require exact configured selected HA Origin; absent/null/foreign Origin
is denied for display authority. Native owner requests use ordinary explicit
paired identity, not an Origin exemption for display credentials. No untrusted
Host/header URL guessing.

The public shell GET is the explicit exception: top-level navigation normally
has no Origin. It allocates no claim/grant/state, returns no private content and
accepts ordinary absent Origin; a supplied null/foreign Origin is denied. Harden
with CSP, frame-ancestors none and no-store/no-referrer/nosniff. GET serves the
shell only; it never counts as native or display authority. Authenticated context
and snapshot are POST pure reads, not GET requests that assume a browser can set
the forbidden Origin header. Qualify the real browser wire before implementation
acceptance; a mocked request dictionary does not prove this policy works.

| Route | Caller / exact purpose |
| --- | --- |
| GET `/djconnect/vibecast/display` | Public empty shell; direct200; no Session data |
| POST `/api/djconnect/v1/display/owner/context` | Paired owner; current Session and B epoch/limits/share metadata; pure read |
| POST `/api/djconnect/v1/display/claim` | Same-origin public browser; create one bounded claim |
| POST `/api/djconnect/v1/display/owner/resolve` | Paired owner plus code; resolve opaque claim ID/generation/deadline only |
| POST `/api/djconnect/v1/display/owner/approve` | Paired owner; approve exact claim and explicit existing/new share |
| POST `/api/djconnect/v1/display/collect` | Original browser claim secret; one-time dedicated display credential |
| POST `/api/djconnect/v1/display/cancel` | Original claim secret; cancel this pending/approved-uncollected claim only |
| POST `/api/djconnect/v1/display/renew` | Display bearer; renew current lease idempotently while consent remains valid |
| POST `/api/djconnect/v1/display/leave` | Display bearer; revoke itself only |
| POST `/api/djconnect/v1/display/owner/revoke` | Paired current owner; revoke exact display or close exact share, distinct from Session end |
| POST `/api/djconnect/v1/display/snapshot` | Display Authorization bearer plus closed context body; pure bounded shared snapshot |
| GET `/api/djconnect/v1/display/live` | Same-origin WSS; first bounded message authenticates display; no token in URL |

Owner requests include the existing paired `identity` object and required
`session_id` where Session authority is used. No client-selected Profile/account.
Context returns only the caller's actual active Session, `issuer_epoch`, limits,
and optional current `share_id`, `share_generation`, `expires_at`. It also returns
`display_entry_url`, the canonical configured external origin plus the fixed
entry path, and `route_trust:"paired_owner_response"`. This owner-only read is
the existing paired-app source of the destination for code-free A; it is neither
an independent HA-issuer attestation nor a QR/Session approval. No browser/QR
supplies or overrides that URL. Missing unsupported external configuration is
`display_external_url_unavailable`, with no HTTP/IP/Host fallback. No capability
is advertised until handlers, source fences and real-chain tests are delivered.
Snapshot body is exactly `{contract_version, issuer_epoch, display_id}`; its
bearer remains in Authorization, never body/query. Context includes version and
paired identity, plus the current session_id when available. POST reads perform
no write, renewal, provider lookup or publication.

Claim request is `{contract_version, browser_nonce}`. Response is
`{success, contract_version, issuer_epoch, claim_id, claim_secret, code,
browser_generation, expires_at, expires_in}`. No Profile, Session, device list,
media, owner token or grant. Six digits identify a claim but cannot poll/collect.
The browser retains the secret/nonce only in memory and never sends them to A.

Owner resolve is `{contract_version, identity, code}`; successful response has
`claim_id`, `browser_generation`, `issuer_epoch`, `expires_at`. Rate-limit failed
lookups. Resolving never approves or reveals claim_secret/browser nonce.

Approve is `{contract_version, identity, session_id, issuer_epoch, claim_id,
browser_generation, code, share}`. `share` is exactly one of:

```json
{"mode":"existing","share_id":"opaque-id","share_generation":1}
```

```json
{"mode":"create","consent":true,"lifetime_seconds":7200}
```

An explicit create approval atomically opens a share and reserves that display;
it neither starts a Session nor changes playback/planning. Existing share mode
never extends expiry. Owner UI must make creation/expiry clear; no implicit share
from a read, scan, lookup, connect or reconnect. Response has approval state,
opaque display/share IDs, generation and original deadlines; never a bearer.
The claim binds to this exact Session/Profile/approving entry/share thereafter.

Collect/cancel require `{contract_version, issuer_epoch, claim_id, claim_secret,
browser_generation, browser_nonce}`. A pending collect returns only pending.
First valid approved collect atomically creates one `djcd_` display bearer and
returns `{state:"admitted", display_id, grant_token, issuer_epoch, session_id,
share_id, share_generation, lease_revision:0, lease_expires_at,
share_expires_at, capabilities}`. No owner/end/invitation credential.
Capabilities explicitly deny all owner/guest effects. Collection consumes claim
authority once; token hash/purpose and the full private binding remain server-side.
Lost one-time collection requires fresh admission; no plaintext token replay
cache. Its abandoned reservation expires within the original claim/lease bound.

Only a current display bearer authenticates snapshot/live/renew/leave. Those
routes reject owner Broadcast tokens, claim secrets and invitations. Ordinary
owner APIs reject display credentials regardless of asserted device_id. WSS
first message is `{type:"authenticate", contract_version, grant_token,
issuer_epoch, display_id, connection_nonce}`. No data precedes authentication.
Only transport ping/close is accepted afterward; audience signals and all
mutations return `display_read_only`. B never accepts `end_grant`.

## State, idempotence and commit points

Claim state: pending → approved → collected, or terminal cancelled/expired.
Same claim ID/generation is never recreated. Approve retry with the same full
binding returns the same public approval summary without opening a share again,
extending deadlines or reserving another display. Different binding returns409.
Resolve requires strong claim ID before approve, so expiry followed by reuse of
the same six digits can never retarget an old retry. Once the claim and display
are terminal, retry fails404/410; it does not reconstruct state from a code.

Runtime manager owns B coordination under its existing lock. New B claims,
share records, reservations, approval/collection/renew/revoke transitions use
that same owner rather than nesting the legacy handoff-manager lock. Capture
immutable entry/Profile/Runtime/source fences; prepare awaited authority/source
work outside the commit lock; validate synchronous current fences again under
the lock before committing. No provider/storage await while holding that lock.
Cancellation before commit changes nothing; after commit it cannot fabricate a
rollback or repeat the effect. Publication/WS delivery failure is not a second
approval. Legacy handoff stays separate until audited retirement.

Renew request includes current bearer, epoch/display binding and monotonically
increasing `renew_sequence`, starting1. Server accepts only the next sequence;
the immediately repeated sequence returns the same recorded lease result,
without extending again. Older/out-of-order sequences fail409. Expired leases
cannot be renewed even if a previous response was lost. Renewal rechecks active
share/Session, approving entry, current pairing/Profile/source rights and original
absolute share deadline. Pure reads do not renew. Client rejects stale revisions.

Connection generation fences late snapshots/events from superseded sockets.
Reconnect within the current lease uses a fresh authorized shared snapshot,
not replay of owner/private history or old display effects. Page reload/state
loss needs new admission; no secret recovery from browser storage. Lease expiry,
offline resume, revoke, Session/share end or authority loss immediately clears
cards, decoded media and pending callbacks. An expired viewer cannot resurrect
content after a late successful HTTP/WSS response.

Use the existing bounded-writer/backpressure pattern explicitly; merely using
WSS does not inherit it. Each display owns one long-lived writer. Callbacks queue
bounded invalidation descriptors/revisions, never retain old private/content
frames or spawn a task per publication. Coalesce consecutive invalidations to a
fresh shared snapshot; never replay historical effects. Enforce both queue count
and serialized-byte budgets globally and per display before reservation. Bound
in-flight projection output too; an oversized item fails closed or falls back
without dropping attribution/changing fact text. At most one projection per
display and8 globally; waiting work is one bounded invalidation flag/display.

Build/send under current issuer/share/lease/entry/Profile/source/generation
fences. Check after projection awaits and immediately before each actual send;
discard stale queued work. Revocation/end fences the generation and cancels the
writer before further content release. A send already started cannot recall
bytes already delivered; if authority changes while awaiting it, cancel/close
and issue no later data. Sendtimeout5s or overflow closes1013, releases queue/
task/socket reservations and leaves only the original still-current lease.
Client clears content and may reconnect with backoff only within that lease;
it does not renew expiry or build a backlog. Test blocked sends plus revoke/end,
not only an empty queue. Actual byte/task/resource accounting remains a runtime
qualification requirement, not proof supplied by these proposed limits.

The optional [Origin wire probe](../../scripts/verification/vibecast_origin_wire_probe.mjs)
measures actual Chromium/WebKit GET/POST/upgrade header behavior on own temporary
loopback servers using the same existing Playwright prerequisites as the frame
probe. It uses synthetic strings, no real credentials, and deliberately refuses
the upgrade. It proves neither HA authentication nor successful B/live transport.

Entry removal/re-pair/Profile reassignment invalidates displays approved by that
entry; loss of the share-creating consent closes that share and all displays.
Another current paired device on the same Profile may explicitly revoke or
create/approve a new share; it does not silently inherit old consent. Session
end/restart closes all related state. Display leave never closes the share or
owner Session. Already delivered bytes/screenshots cannot be recalled.

## Shared projection and media

Build a closed server allowlist from existing immutable publications/current
playback, not an owner response with fields hidden by renderer CSS. Required
identity fields are contract version, issuer/display/share/Session generation,
coherent projection revision and as_of. Allow qualified public current-track
labels, approved non-Silence shared Moments with immutable fact text, sources/
attribution and original expiry. Optional `session_presentation` is exactly
`{mood, persona, presence}` containing only qualified current active-Session enum
labels under the explicit share policy. Unknown/unqualified labels are omitted;
never infer them from Profile defaults or rewrite a published Moment's original
Persona/Mood. No settings/default snapshot, settings revision, voice, gender,
announcement_output, provider/pipeline or device preference appears here. These
three presentation labels confer no settings read/write capability.
No Planner/Horizon, owner Flow conversation, Ask DJ/history/DNA, account/device/
Profile IDs, prompts, source payloads or private native deliveries are serialized.
Unknown fields are denied. Display reads never generate a Moment or provider call.

`SESSION_SHARED`/`PUBLIC_BROADCAST` labels alone are not proof of audience/source
rights. Revalidate current publication qualification, audience, channel, locale,
source/account/edition/subject and original deadline before projection and again
after any await. Source withdrawal invalidates live items and queued projections.
Forecast is included only when its text/media are independently qualified for
this share; otherwise absent, not copied from private owner projection.

No owner session_media/speech/image URL or private Discovery grant is forwarded.
Shared media needs a separate display-purpose object/source/subject/account/
share-generation capability with expiry=min(asset, publication, share, lease).
If this cannot be qualified, deliver text/fallback without artwork/audio. For
qualified authenticated bytes, the thin host may use bounded fetch+object URLs;
only its own registered object URLs are renderable and all are revoked/decoded
buffers cleared on expiry/withdrawal/end. No arbitrary blob URL allowance, direct
provider hotlink, token query, asset persistence or automatic speech generation.

## Failure codes and real acceptance before delivery

Machine codes: `display_contract_unsupported`, `display_origin_denied`,
`display_external_url_unavailable`, `display_tls_required`,
`display_capacity`, `display_claim_unavailable`, `display_code_invalid`,
`display_rate_limited`, `display_context_changed`, `display_share_unavailable`,
`display_grant_invalid`, `display_lease_expired`, `display_read_only`.
400 malformed;401 unknown credential;403 authority/origin/purpose;
404 generic unavailable claim/session;409 stale binding/sequence;
410 expired locally known authority;429 budget;503 unavailable integration.
No response distinguishes another Profile's Session existence. Shared renderer
functional messages ship in en/nl/de/fr/es before runtime acceptance.

Design review must assess these bounds, new endpoint/capability naming,
multi-device consent/revocation, UI clarity and safe independent B qualification
while A remains unavailable. Neither this proposal nor a schema-only test is
permission to bypass that review or advertise working display admission.

Then prove actual isolated HA pairing→Runtime→claim→owner approval→collect→
scoped snapshot/live→revoke/end, and all private/effect route denials. Include
duplicate/racing approve/collect/renew, cancellation at each await, storage/source
failure, wrong origin/entry/Profile/Session/share/purpose/browser/generation,
expiry equality, failed sends, reconnect/reload/restart, source withdrawal and
bounded capacity/long runs. Test local/static shared renderer portrait/landscape,
facts/links/readability/expiry/end with genuinely admitted display credentials.
External provider boundaries alone may be fixtures. Native Apple/TV, public
TLS/proxy acceptance and A remain separately open until actually measured.
