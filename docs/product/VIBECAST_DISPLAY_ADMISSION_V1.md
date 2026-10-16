# VibeCast display admission v1 — Core contract review

Assignment `DJC-CORE-VIBECAST-DISPLAY-ADMISSION-V1-20261016`,
[owner selection](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6222775045),
[ACK](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6224062979).
Base `1329ad1ce8bd066d65a08b3988261a44e2cac730`; existing Core writer,
branch `codex/vibecast-display-admission-v1`. Existing roadmap node `WEB::DISPLAY`.
Settings source1193/Finalization1194 and repair1195/Finalization1196 remain closed.

Status: **CONTRACT_REVIEW / NOT_FROZEN / NO_RUNTIME_IMPLEMENTATION**.
This is the required design before changing HA runtime. It is not a replacement
for the selected implementation. The
[onboarding authority](VIBECAST_ONBOARDING_GUEST_AUTHORITY_V1.md),
[distribution ownership](VIBECAST_WEB_ENTRY_DISTRIBUTION_V1.md) and
[Apple guest boundary](APPLE_VIBECAST_GUEST_MODE_V1.md) remain canonical parents.
API94 revision `cf85081cbca28b66ddbcb8f0f61635fec55c510d`, document0.1.0-draft,
proposed wire `djc-rendezvous/1`, is upstream **BLOCKED_CONTRACT_REVIEW**.
No rendezvous algorithm, signing suite or TV trust root is frozen here.

## Existing chain and the missing trust boundary

Core already authenticates paired owner requests against the loaded config entry,
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

**TRUST-1 is unresolved:** an adversary can copy a QR, encrypt to its public key,
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
| TRUST-1 | Independently authenticated TV trust-anchor bootstrap binding selected installation and approving paired host; enrollment, rotation, revocation, wrong-install and substitution vectors | OPEN; Core/API/Apple review requested |
| TRUST-2 | A reviewed standard sender-authenticated envelope/profile and supported library versions, with independent browser/native crypto vectors and original-expiry binding | OPEN; no custom ECDH/KDF/AEAD composition |
| ROUTE-1 | Adopt or correct the exact Core route/normalization corpus below; show actual redirect/reachability handling without central fetch | REVIEW_CANDIDATE |
| WIRE-1 | Apple/receiver comparison, cancellation, consume-loss and separate B-code states; exact interoperability acknowledgement | OPEN |

A reviewed out-of-band protocol is an alternative only after its commitment,
confirmation, entropy, retry/substitution bounds and implementation are specified.
A home-grown short hash comparison is not that protocol. RFC6189 is evidence
that a SAS protocol includes further machinery, not authorization to transplant
ZRTP into this product. Code-host/app compromise remains a stated trust-root
limit; it must not conceal a separately malicious-relay/key-substitution gap.

## Concrete trust-bootstrap proposal for joint review

Core proposes evaluating an **owner-generated out-of-band secret** with an
established reviewed password-authenticated key exchange implementation. The
already trusted owner app selects and validates its existing HA over ordinary
pairing, then shows a fresh A-only secret; the user transfers that secret to the
waiting TV. It is never present in the QR or rendezvous request. The resulting
reviewed authenticated channel would bind exactly that app-confirmed destination,
installation reference, browser transaction/generation and original expiry.
This avoids inventing a central owner registry or trusting a sender-supplied key.

This is a concrete candidate, **not a selected crypto suite or runtime GO**.
Joint review must establish an interoperable maintained browser/native/library
profile (including key confirmation and protected application transcript), secret
entropy, strict active-attempt/transaction/global budgets, no offline guessing,
original deadline, cancellation, and no replacement after a failed attempt.
[RFC9382](https://www.rfc-editor.org/rfc/rfc9382.html) and
[RFC9383](https://www.rfc-editor.org/rfc/rfc9383.html) are published Informational
PAKE specifications to assess, not permission to implement their primitives
ourselves or evidence of a qualified application profile. No fake encryption vectors or model-only PAKE success will count.

Product review must assess the additional TV input against the requested scan/
approve flow and distinguish A's owner-to-TV confirmation from B's separate
TV-to-owner six-digit admission. This candidate cannot silently replace the
existing comparison-only UX. If that extra independently trusted channel is
rejected, a separately qualified enrollment/issuer trust root is required;
there is no safe QR-only fallback that simply calls an untrusted key verified.

Revocation needs an explicit reviewed limit: an already emitted encrypted
A-destination may remain readable until its original short expiry and cannot be
recalled after disclosure. Before issuing any new approval, Core rechecks current
pairing/entry/Profile and selected route. Before navigation/admission, the chosen
protocol must define how current revocation is checked or bound; the API cannot
claim instant HA revocation from an offline signature. B independently rechecks
the current paired owner/share/Session and confers no rights from stale A.
API and Apple must approve or supply an equally concrete alternative before
TRUST-1/2 is closed. No human publication permission is missing for this work;
what is missing is a reviewed technical/UX contract and interoperable evidence.

## ROUTE-1 candidate: one exact external entry

The proposed new HA page is **`/djconnect/vibecast/display`**, served from the
existing Core renderer source through a thin host adapter. Existing
`/djconnect/vibecast` and Cast integration remain separate compatibility surfaces.
This document does not register that page or any new HTTP endpoint yet.

The authoritative selected installation returns its configured external origin
through an ordinary paired owner request. Never take that origin from a QR,
provider, browser field, forwarded Host header or a last-used installation guess.
An explicit chooser resolves multiple already paired installations; absence or
unavailability of an external route produces a functional error, not a new
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
- No redirect parameter or redirect chain is authorized. Syntax validation does
  not prove DNS/public reachability or absence of proxy redirects. These need
  real browser/selected-HA tests. The Worker never resolves or fetches HA.
- Live entry needs no-store, no-referrer, nosniff and a narrowly reviewed CSP;
  no third-party assets/analytics, credentials in URLs or persistent token cache.

The [synthetic route corpus](../../examples/client_contracts/vibecast_display_admission_v1/route-cases.json)
and independent Python/WHATWG-URL checks qualify this lexical decision only.
They do not qualify TLS, DNS, navigation, trust, HA handlers or consumer adoption.
IDNA/custom-port support and an enforceable browser redirect fence are review items,
not silently implemented exceptions. `example.org` names are synthetic and are
never fetched.

## A and B are independent transactions

| State/action | Authority and outcome | Failure/late result |
| --- | --- | --- |
| A waiting QR | Browser-only strong secret/key and immutable transaction/generation/deadline; API temporary ciphertext only | Cancel/rotate destroys old keys; no stale consume retry |
| A owner chooses installation | Existing paired owner, explicit selected destination and reviewed TRUST-1 approval bound to exact browser/transcript | Wrong/unpaired installation denied; no credential export |
| A consume | One original-deadline encrypted destination/context, once | Lost result starts fresh; no Session grant and no navigation before validation |
| B HA entry | No private content; browser creates a new strong claim at selected HA | Missing route/TLS/browser capability fails visibly |
| B six digits | Separate HA-generated six digits, independent of A comparison; paired current Session owner approves exact claim/share/generation | B expiry/attempt limit/cancel/end prevents approval |
| B collect | Only browser's strong claim secret collects one scoped display grant | Code alone never collects, replays cannot replace a grant |
| Display live/recover | Existing Runtime/Flow/Broadcast projection through a display principal; recheck current share/session/grant/generation/source rights after awaits | Revoke/end/restart/original expiry clears cached/decoded presentation; no resurrection |
| Display leave | Close/revoke only this display | Never end DJ Session, close another display or stop music |
| Owner revoke / share close | Existing paired owner; distinct from Session end | Fence pending claims, connections, media and late callbacks |

B's exact endpoint schemas, claim/grant IDs, lease values, attempt/capacity budgets
and live transport need design review before runtime. Reuse the existing owner,
Runtime, Session, Flow and renderer; do not create a second planner/event bus or
forward the unscoped owner Broadcast bearer as the new display credential.
Grants require installation/Profile/Session/share/browser/purpose/generation and
original deadline binding; media needs separate qualified source/audience rights.
No owner history, DNA, Ask DJ, private forecast media, settings or playback/
queue/volume/end operation is available to a display. Missing Origin is not
native authority; wildcard CORS/cookie reuse is forbidden.

## Legacy end authority: inventory before retirement

`config_flow.py` currently exposes `vibecast_session_end_allowed`. In
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
