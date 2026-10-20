# VibeCast display admission v1 — Core contract review

Assignment `DJC-CORE-VIBECAST-DISPLAY-ADMISSION-V1-20261016`,
[owner selection](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6222775045),
[ACK](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6224062979).
Base `1329ad1ce8bd066d65a08b3988261a44e2cac730`; existing Core writer,
branch `codex/vibecast-display-admission-v1`. Existing roadmap node `WEB::DISPLAY`.
Settings source1193/Finalization1194 and repair1195/Finalization1196 remain closed.

Current source readback, checked20October2026: **B_PROTECTED_SOURCE /
A_IMPLEMENTATION_CONTRACT_RELEASED / JOINT_ACCEPTANCE_OPEN**. PR1197 merged as
`c98cbf3e3114afb8b8212e18224a337b12af3e27`; current protected main8b221d07
includes the B handlers, shared shell and capability declaration. See the
[exact source/readback, fresh actual HA proof and consumer sequence](../verification/VIBECAST_B_PROTECTED_SOURCE_READBACK_20261020.md).
No installed public route or complete A→B/native/hardware acceptance is implied.
API's implementation agreement is separately protected-delivered by PR96
`2dade83f338ae5f931856934ab0c23b6f6c66f05` and Finalization97
`661e5770eb5249b1b02bbdc2426ba7e575fc8881`. Its
[limited implementation-contract precedence](https://github.com/pcvantol/djconnect-api/blob/2dade83f338ae5f931856934ab0c23b6f6c66f05/docs/rendezvous/IMPLEMENTATION_CONTRACT_RELEASE_V1.md)
supersedes old missing-ACK/NOT_FROZEN statements to its enumerated scope.
It does not enable the public service or waive actual native/operational gates.
The historical API94 review and design findings below are preserved provenance,
not a request to repeat already received implementation ACKs.

Historical pre-merge status: **A_CONTRACT_REVIEW / B_CORE_SOURCE_GO / DRAFT_NOT_MERGED**.
After exact independent B-design GO on ae2adfe9, B was implemented independently
with A unavailable. Runtime/discovery pin3cb9cf12 and fixture/candidate pin325aabc7
have independent technical/privacy and product/UX/privacy GO for B-Core.
Normal candidate registration includes bounded Runtime-owned authority, paired
HTTP transitions, dedicated snapshot/live, the shared-renderer host and generic
support discovery. Real isolated HA/browser proofs are scoped in the
[B contract](VIBECAST_DISPLAY_ADMISSION_B_V1.md). At that historical checkpoint
the candidate was not main or installed; current protected source is recorded
above. No secure-A, public-route, native or hardware acceptance is inferred.
The
[onboarding authority](VIBECAST_ONBOARDING_GUEST_AUTHORITY_V1.md),
[distribution ownership](VIBECAST_WEB_ENTRY_DISTRIBUTION_V1.md) and
[Apple guest boundary](APPLE_VIBECAST_GUEST_MODE_V1.md) remain canonical parents.
API94 current review revision `e6464e86cd214bd55661f14f238706332a53bd40`,
document0.2.0, is upstream **BLOCKED_CONTRACT_REVIEW**. The earlier0.1.0
proposal is historical. Owner corrections
[6224535256](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6224535256)
and [6224654453](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6224654453)
select code-free URL convenience A: **no additional TV secret, PAKE/OOB or
comparison-code step**. Only the separate existing HA six digits admit B.
No rendezvous algorithm, signing suite or TV trust root is frozen here.

## Existing chain and the missing trust boundary

The following preserved inventory describes main/base1329 before B; the current
candidate adds the separately reviewed display principal described below.
Core authenticates paired owner requests against the loaded config entry,
device token, current Profile and active Session. `broadcast_handoff.py` supplies
an independent browser claim secret and six-digit approval code, a300-second
memory-only claim, capacity64/per-source3 and owner attempt throttling. Collection
currently returns the Runtime Broadcast token; it does not create a per-display,
share-scoped grant. Restart forgets pending claims. This is a reuse point, not
proof that the new trust/share protocol already exists.

The API's existing APNs/bootstrap/install credential flow has no browser-verifiable
attestation of an existing Apple/HA pairing. Core's ordinary device bearer and
process-local history signing key are not public installation trust anchors.
The owner app's trusted local pairing does not automatically transfer to a TV.

**TRUST-1 technical review remains open:** an adversary can copy a QR, encrypt to its public key,
include its own installation/signing key and a valid-looking destination. A
signature verified with a key supplied in that same untrusted envelope merely
proves control of that key. TLS to an attacker-owned destination authenticates
that origin, not the owner's selected paired installation. A six-digit code for
phase B must not be used to excuse an unauthenticated phase A.

No implementation may equate QR possession, successful JWE decryption, a
self-supplied JWK, APNs bootstrap proof or install relay token with owner approval.
Do not silently introduce a central pairing registry, central HA probe/proxy,
new login or credential forwarding to close this gap.

### Review exits required from the existing owners

| Gate | Concrete required answer | Current state |
| --- | --- | --- |
| TRUST-1 | Owner-selected limited genuine-app reported-route guarantee; independent review must preserve its stated copied-QR/wrong-scanner risk and reject stronger identity claims | OWNER_LIMITED_CLAIM_SELECTED; SECURITY_REVIEW_OPEN; no independent HA attestation |
| TRUST-2 | App Attest candidate verifier, exact request/ciphertext digest/browser/generation/action/expiry binding, key/counter retention and real interoperability | OPEN; API KEY-STATE/Apple qualification unresolved |
| ROUTE-1 | Exact raw route corpus plus explicit direct-navigation trust handoff; qualify selected HA/proxy direct200 and failure behavior | CORE_DIRECTION_SELECTED; JOINT_REVIEW_OPEN |
| WIRE-1 | Code-free Apple/receiver handoff, cancellation, consume-loss and separate existing B-code states; exact interoperability acknowledgement | OPEN; no comparison/OOB UI |

## Current code-free trust proposal and actual reuse boundary

The owner's code-free product decision supersedes the previous A-only PAKE/OOB
proposal. Do not select a PAKE library, add TV input, add a comparison code or
silently re-pair a phone as an implementation prerequisite. The TV opens the
short URL; the already paired iPhone confirms its actual selected HA route;
A transfers only that destination to the same browser transaction. B independently
requires the existing HA-generated six digits, current owner consent and grants.

Existing source chain:

- `request_auth.resolve_runtime` and `authorize_runtime_device_request` validate
  the normal HA-issued device bearer and actual config entry/client identity.
- `profile_context.async_resolve_device_bound_request_context` resolves current
  device-to-Profile binding; `display_authority.resolve_display_owner` captures
  original pairing admission before awaits and rechecks current entry/generation,
  source/account/privacy and monotone withdrawal. This is **HA-local authority**.
- `display_origin.selected_ha_origin` uses supported HA `get_url` with external/
  cloud HTTPS, standard-port and no-IP constraints; it never guesses from request
  Host, QR, forwarded headers or browser input. The paired owner-context response
  will expose only that canonical public entry, with a paired-response trust
  label. It is not a public signature or independently verifiable HA receipt.
- Apple owns existing pairing-token storage, selected installation, App Attest
  availability/key and consent. Neither its HA bearer nor APNs/install/bootstrap
  credential is sent to the rendezvous service or a display.

The owner selected alternative (i), subject to technical qualification: genuine
app-instance App Attest and the
app's already paired HA response as the agreed destination source. This does
**not** establish independent HA-owner/install attestation or that the scanner
is the TV's intended owner. An otherwise legitimate paired scanner with a copied
QR may submit its own valid destination first. The owner has accepted that
specific risk for the limited address shortcut; independent technical/security
review remains open. B does not authenticate A.
The unselected stronger alternative (ii), if later required by a new decision,
requires a genuinely trusted HA issuer/enrollment chain. No such browser/API-
verifiable chain exists in current Core/APNs bootstrap. A same-envelope public
key or the existing bootstrap-proof handler does not provide it. No new central
HA account/credential registry or custom crypto composition is authorized here.

API94 review0.2.0 proposes a request-bound submit challenge including exact
ciphertext digest, browser transaction/generation, action and original expiry.
App Attest key/public-key/counter state spans transactions and is linkable device
information, not anonymous120-second relay state. Its retention, deletion,
recovery, re-attestation cadence and counter-versus-transaction crash ordering
are the concrete **KEY-STATE** gate. API owns verifier qualification and security
state; Apple owns App ID/prefix/environment/isSupported/distribution policy and
real assertions. Core neither chooses an unqualified verifier nor adds signing.

Before a new route confirmation, recheck current normal pairing, loaded entry,
Profile/source rights and selected external configuration. Disclosure cannot be
recalled after A has delivered a destination. No relay ready state promises
instant HA revocation. B's current owner/share/Session gates remain independent.
There is no missing generic human merge permission; technical/security/interop gates
are explicit and are not bypassed by the code-free product choice.

### Limited A product disposition — owner choice resolved, technical gates remain

The existing Apple owner conversation asked the concrete copied-active-QR risk
question and received the direct human response “ga verder”, then read back the
limited address-transfer interpretation. The owner subsequently replied
“akkoord”. Core independently read that original exchange; it does not rely
solely on another agent's claim of approval. The existing public
[disposition receipt6226306251](https://github.com/pcvantol/djconnect-api/pull/94#issuecomment-6226306251)
records the precise limited scope. This resolves the owner's choice of
alternative(i); do not keep asking that same high-level product question.

Accepted product boundary: a verified genuine DJConnect app instance reports
that it checked and explicitly confirmed its own existing paired HA route.
It does not prove the intended TV owner, independent HA ownership, physical TV
presence or a permanent HA issuer identity. Another genuine paired scanner with
a copied active QR can submit its own route first, including a misleading
external destination. This is the specifically disclosed residual risk of A.
The later six-digit HA admission protects B authority, not that earlier
navigation or phishing risk. No stronger authenticity statement is permitted.

This choice grants no crypto PASS, persistent central registry, new signing,
account/enrollment change, contractfreeze, consumer implementation, installation
or deployment. KEY-STATE finite retention/deletion/recovery/counter/crash ordering,
exact App Attest/JWE/verifier/WIRE interoperability and independent
security/privacy/UX review remain open with the existing API/Apple/receiver
owners. Core source and the read-only B contract are unchanged. No A runtime GO
or whole-assignment completion follows from the product disposition.

### Apple scanner interface review, 17 October — no new authority

The existing Apple writer's [source/interface review](https://github.com/pcvantol/djconnect-api/pull/94#issuecomment-6226236839)
reports a local documentary checkpoint6c21c15 atop1e8ecf2. Core did not fetch
those Apple commits; public lookup of base1e8ecf2 returned422. This is an
attributed consumer-owner report, not independently verified Apple Git blobs or
native execution. Core neither adopts nor changes the other writer's WIP.

| Boundary | Existing owner/source evidence | Scanner requirement and remaining proof |
| --- | --- | --- |
| Pairing and installation | Apple reports `DJConnectClient.pair`, `DJConnectPairingResponse.ha_remote_url`/`ha_install_id`, and `DJConnectAppModel.apply(pairingResponse:)`; one saved local/remote configuration and install ID | Show the actual configured installation explicitly. Do not invent a multi-install registry or silently pick a last-used installation. A future multi-install chooser needs its own existing authorized records. |
| Current HA route | Core `request_auth.py`, `profile_context.py`, `display_authority.resolve_display_owner`, `display_origin.selected_ha_origin`, `display_service.py` owner/context | Check the authenticated Hybrid context installation against the expected saved install ID, then read the current paired owner/context. Cached pairing URL alone is not scan-time route authority. Core issuer_epoch is only a process fence, not the installation ID. |
| In-flight change | Core captures pairing before Profile awaits and latches monotone withdrawal; Apple reports existing request/configuration checks | Scanner must add its own monotone flow invalidation for pairing/Profile/route ABA, cancellation, background, QR rotation and expiry. Recheck current owner context before release; changed route or epoch needs fresh explicit confirmation. A released address cannot be recalled. This is a consumer requirement, not an implemented native claim. |
| Genuine app and platform | Apple's [isSupported documentation](https://developer.apple.com/documentation/devicecheck/dcappattestservice/issupported), independently read through the official documentation JSON on17October | App Attest is unavailable on Mac, including Catalyst and iOS/iPadOS apps running on Apple silicon. Supported iPhone/iPad still require runtime checks. No unsigned/borrowed-assertion fallback; use the existing paired-iPhone route or an existing non-A route. |

The Apple owner reports no App Attest entitlement, implementation or real
key/assertion vectors in this checkpoint. Its signed local development artifact
is not a production App Attest qualification. App ID/prefix/environment must be
verified from the actual future signed artifact; do not infer distribution
identity from a Team ID or APNs entitlement. Development and production verifier
domains remain separate. Core adds no signing or Apple implementation.

A successful submit means **address sent**, never display connected. Lost submit
is uncertain; lost one-time consume needs a fresh QR. Cancel after a possible
commit does not promise remote recall. The original transaction/browser key,
generation and expiry remain binding across every await. These interface and
failure requirements refine WIRE-1 but do not close it. TRUST-1, KEY-STATE and
actual native/browser/verifier interoperability remain open. A genuine different
paired scanner can still win a copied QR with its own destination. The separate
limited-claim disposition below records that specific accepted product risk;
it does not infer acceptance merely from the no-extra-code UX decision.

## ROUTE-1 candidate: one exact external entry

The candidate HA page is **`/djconnect/vibecast/display`**, served from the
existing Core renderer source through a thin host adapter. Existing
`/djconnect/vibecast` and Cast integration remain separate compatibility surfaces.
Candidate source registers this page and the B routes through the normal
integration path. Its isolated synthetic-TLS proof is not qualification of a
real externally configured DNS/TLS/proxy route or an installed endpoint.

The authoritative selected installation returns its configured external origin
through an ordinary paired owner request. Never take that origin from a QR,
provider, browser field, forwarded Host header or a last-used installation guess.
The current Apple source report describes one configured installation; show it
explicitly. If multiple authorized records are supported later, require an
explicit chooser. Absence or unavailability of an external route produces a functional error, not a new
pairing, guessed hostname, HTTP downgrade or TLS bypass.

The route-review corpus is deliberately narrow:

- HTTPS, public canonical non-IDNA ASCII DNS hostname; default TLS port443 only.
  Unsupported configured custom ports are reported explicitly, not rewritten.
- Exact path `/djconnect/vibecast/display`; no trailing slash, query, fragment,
  userinfo, percent encoding, backslash, whitespace, IP literal, trailing dot or
  ambiguous encoded/dot-segment equivalent. Explicit `:443` is noncanonical;
  Core's separately validated configuration normalization must emit the canonical
  origin before publication, rather than letting consumers repair received URLs.
- The received origin must exactly equal the paired selected installation's
  previously authenticated canonical origin. IDNA conversion is not inferred
  from a TV label. All Unicode and `xn--` A-label hosts are unsupported in this v1 review profile, including otherwise valid names. This explicit fail-closed restriction avoids silently mixing IDNA2003/2008/UTS46 behavior. Widening it requires one reviewed interoperable normalization profile and new positive/negative vectors.
- No redirect parameter, alternate input destination or arbitrary redirect chain
  is authorized by A. Core selects direct top-level navigation with the explicit
  trust handoff below. Syntax validation does not prove DNS/public reachability
  or actual selected-HA/proxy direct200 behavior. The Worker never resolves or
  fetches HA.
- Live entry needs no-store, no-referrer, nosniff and a narrowly reviewed CSP;
  no third-party assets/analytics, credentials in URLs or persistent token cache.

The [synthetic route corpus](../../examples/client_contracts/vibecast_display_admission_v1/route-cases.json)
and independent Python/WHATWG-URL checks qualify this lexical decision only.
They do not qualify TLS, DNS, navigation, trust, HA handlers or consumer adoption.
IDNA/custom-port support remains outside this review profile. `example.org` names
are synthetic and are never fetched. A new navigation enforcement guarantee is
not silently inferred from passing these lexical checks.

### Core route decision: explicit trust handoff, joint review still open

The receiver owner reviewed exact `1dcb36732616798f59f4f9fcf3cb24581c393e77`
and acknowledged direct top-level navigation as compatible with the existing
web-first architecture. Core selects that design direction, subject to joint
API/Apple/security/privacy/UX review before freeze. No iframe, native wrapper or
new central HA proxy is selected.

Before initial navigation, the bootstrap must meet the explicitly selected
code-free trust guarantee above and validate the original raw exact HTTPS entry
URL, browser/transaction/generation and original expiry. No independent HA
attestation is implied by a paired app-instance assertion. It initiates only that
destination, without a secret or credential in the URL/history/referrer. API
ready state, TLS alone and a same-envelope key remain insufficient. TRUST-1/2
must close before this direction can be implemented as secure A.

**After the initial navigation, the authenticated selected HA and its configured
reverse proxy form the trusted execution boundary.** Their HTTP/content routing,
scripts and applicable service workers are not contained by the old bootstrap
page. The HA entry is required and must be qualified to return direct200 without
redirects, canonicalization or a login hop. This is a configuration/acceptance
property, not a claim that bootstrap JavaScript intercepts a later changed
response. That explicitly replaces this draft's earlier absolute browser-enforced
no-redirect promise; the restriction on unverified input destinations is retained.

A preliminary fetch cannot guarantee the response of a later navigation. Before
handoff the bootstrap reports its own validation/expiry failures. After handoff
it cannot reliably inspect cross-origin readiness or TLS/connection errors;
browser error UI may appear before HA loads. The HA page owns its B status and
recovery messages. Navigation initiation is never connected/admitted success.
Current independent B approval, scoped grants and source/media rights remain
mandatory. No user credentials or Session rights are obtained from navigation.

Real browser/selected-HA/proxy tests must prove the supported direct200 route and
document the unsupported redirect/login cases, including Refresh/meta/script/
service-worker behavior and failures. They must not assert that normal top-level
navigation blocks the redirect behavior already measured. Native/physical
acceptance and the whole contract freeze remain open.

### Independent review and measured navigation limits

The [16 October design-review receipt](../verification/VIBECAST_DISPLAY_DESIGN_REVIEW_20261016.md)
records the API/receiver findings and reproducible follow-up. Both validators
passed40 lexical cases, but ordinary navigation followed an off-origin302 in
Chromium/WebKit. A separate12-case framed-surface experiment blocked the tested
off-origin navigations/top escape while still following same-origin path
redirects. Neither a preflight fetch nor a sandbox satisfies the earlier absolute
no-redirect promise. A framed surface is **not selected**; actual
HA/proxy framing, CSP/storage, accessibility and media compatibility are untested.
The direct-navigation trust handoff above now states Core's design direction;
joint design review and real selected-route qualification remain before freeze.

The earlier PAKE/mailbox investigation in the review receipt is historical and
not the selected v1 path. API94 review0.2.0 now targets code-free App Attest with
the concrete trust/key-state gaps above. TRUST-1/2 and WIRE-1 remain OPEN. No A
runtime or consumer implementation is authorized by synthetic navigation results
or draft green checks alone; independently reviewed B work remains separate.

## A and B are independent transactions

| State/action | Authority and outcome | Failure/late result |
| --- | --- | --- |
| A waiting QR | Browser-only strong secret/key and immutable transaction/generation/deadline; temporary transaction ciphertext; separate App Attest key/counter state has an unresolved retention/recovery gate | Cancel/rotate destroys old browser keys; no stale consume retry; do not mislabel cross-transaction verifier state as anonymous120s state |
| A owner chooses installation | Existing paired owner, explicit selected destination and reviewed TRUST-1 approval bound to exact browser/transcript | Wrong/unpaired installation denied; no credential export |
| A consume | One original-deadline encrypted destination/context, once | Lost result starts fresh; no Session grant and no navigation before validation |
| B HA entry | No private content; browser creates a new strong claim at selected HA | Missing route/TLS/browser capability fails visibly |
| B six digits | Separate HA-generated six digits, with no A comparison or extra TV code; paired current Session owner approves exact claim/share/generation | B expiry/attempt limit/cancel/end prevents approval |
| B collect | Only browser's strong claim secret collects one scoped display grant | Code alone never collects, replays cannot replace a grant |
| Display live/recover | Existing Runtime/Flow/Broadcast projection through a display principal; recheck current share/session/grant/generation/source rights after awaits | Revoke/end/restart/original expiry clears cached/decoded presentation; no resurrection |
| Display leave | Close/revoke only this display | Never end DJ Session, close another display or stop music |
| Owner revoke / share close | Existing paired owner; distinct from Session end | Fence pending claims, connections, media and late callbacks |

B's exact endpoint schemas, claim/grant IDs, lease values, attempt/capacity budgets
and live transport received independent design review before runtime. The
implementation reuses the existing owner,
Runtime, Session, Flow and renderer; do not create a second planner/event bus or
forward the unscoped owner Broadcast bearer as the new display credential.
Grants require installation/Profile/Session/share/browser/purpose/generation and
original deadline binding; media needs separate qualified source/audience rights.
No owner history, DNA, Ask DJ, private forecast media, settings or playback/
queue/volume/end operation is available to a display. Missing Origin is not
native authority; wildcard CORS/cookie reuse is forbidden.

### B software qualification and preserved baseline inventory

The [B v1 contract](VIBECAST_DISPLAY_ADMISSION_B_V1.md) specifies the implemented
routes, authority bindings, budgets, consent, retries/leases, commit points and
shared projection/media fences. Source3cb9cf12/fixtures325aabc7 independently pass
B technical/privacy and UX review, actual HA transitions/live/resource checks,
both browser engines/orientations, original expiry/reconnect/end and generic
support discovery. Discovery exposes no route or consent and requires current
paired owner-context read. These B-only proofs do not close A's trust gate,
freeze the whole interoperable contract or qualify public/native/installed/TV.

Historical source inspection at base1329 confirms that its `BroadcastAuthorizationScope`
has only OWNER and there is no delivered share/display-grant identity. The old
Broadcast token also permits audience signals, and owner serialization defaults
to including owner-only data. Neither is a read-only display principal or an
explicit shared allowlist. B must add the bounded Runtime-owned authority and
source/audience-qualified projection; it must not reuse that credential at a TV.
Existing private media endpoints and query-string Broadcast-token delivery are
not templates for new display media/authentication.

`central_api.ensure_ha_install_id` reads/persists the runtime's config-entry value.
That helper alone does not prove one common installation identity across all
paired entries. `hybrid_service.PairedAuthority` provides actual entry, pairing,
Profile binding-generation and source/account/privacy fences. Reuse qualified
authority checks, but do not silently promote the relay install ID to a global
TV trust root, mutate existing pairing identities or couple B to private history
consent. Issuer/entry/Runtime-epoch semantics need an explicit reviewed mapping.

The candidate B implementation uses120s claims and60s online leases, distinct
from the unchanged legacy300s handoff. Atomic approval/one-time collection/revoke,
the existing Runtime lock, bounded reservations and original deadlines are
implemented and tested; renewal cannot extend an already expired authority.
The preceding inventory remains a baseline record, not a claim that candidate B
is still absent. Maximum-load/public-route and A/native/joint qualification are
separate and remain open. This is the pre-merge candidate record; the protected
source readback above supersedes its former not-delivered-to-main status.

## Legacy end authority: historical inventory before retirement

The following inventory is historical. Current main source1202/Finalization1203
removed that checkbox, grant machinery and generated renderer control; the
legacy endpoint is an effectless410 tombstone. The combined build preserves
that retirement. See [current contract](VIBECAST_RECEIVER_END_AUTHORITY_RETIREMENT_V1.md).


The pre-retirement `config_flow.py` exposed `vibecast_session_end_allowed`. In
`api_handlers.py:async_handle_session_broadcast_handoff_approve_payload`, true can
mint `end_grant`; the existing renderer can send it to
`/api/djconnect/v1/session/broadcast/control/end`. The receiver's Cast host tests
already check that untrusted `end_grant` is ignored, while its generated imported
HTML still contains the legacy handler. A grep alone does not prove deployment
or that every old host path is dead. Apple source search found no `end_grant`
reader; Pi and receiver adoption still need their existing owning proof.

New display admission must never mint, accept, forward or serialize end authority.
Owner scanner approval, display close, share close and Session end are separate.
Before retiring old flags/grants, pin actual consumers, audit live readers and
fence already-issued authority with explicit compatible errors. Preserve history,
pairing, shared Profiles, settings and the original source/consumer receipts.
No blind legacy removal or receiver/Swift write occurs in this contract step.

## Verification required before delivery

Real isolated HA tests must use ordinary paired owner auth and the actual
Runtime/claim/grant/Broadcast/media chain. Only external provider boundaries may
be fixtures. Include wrong installation/Profile/Origin/browser; QR tampering;
competing scan/claim/approve/collect; original-deadline equality; cancel/revoke/end
between every await; HA restart; lost responses; late sockets/snapshots; no-store,
source withdrawal and display attempts to call every owner mutation/end route.
Bound capacity, body sizes, attempts, memory, logs and a longer reconnect run.
Local/static shared renderer tests cover both orientations, current track,
Moments/attribution/readability/expiry/end. Native Apple->HA and physical TV
acceptance remain OPEN until actually measured. No Pages/API deployment,
provider/cost route, signing or hardware action is part of this Core step.

## Primary-source basis, checked 2026-10-16

[RFC7515 §10.3](https://www.rfc-editor.org/rfc/rfc7515.html#section-10.3)
requires an application to address key origin; a valid signature alone supplies
no application enrollment trust. [RFC8725](https://www.rfc-editor.org/rfc/rfc8725.html)
separates algorithm validation from issuer/key binding and input trust.
[RFC6189](https://www.rfc-editor.org/rfc/rfc6189.html) describes a specific
commitment/SAS protocol, not a generic comparison-code shortcut.
The [WHATWG URL standard](https://url.spec.whatwg.org/) informs cross-parser
normalization tests; it does not authorize arbitrary normalized destinations.
These sources establish constraints, not completed design/security acceptance.
