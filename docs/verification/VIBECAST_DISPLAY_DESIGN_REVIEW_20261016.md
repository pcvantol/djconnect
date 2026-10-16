# VibeCast display design review — 16 October 2026

Assignment `DJC-CORE-VIBECAST-DISPLAY-ADMISSION-V1-20261016`.
Review target: Core `7f8c05f645db3e6c14604c9593794cc901b05a41`, draft
[#1197](https://github.com/pcvantol/djconnect/pull/1197); API
`cf85081cbca28b66ddbcb8f0f61635fec55c510d`, draft
[#94](https://github.com/pcvantol/djconnect-api/pull/94).
The [canonical contract](../product/VIBECAST_DISPLAY_ADMISSION_V1.md) remains
**NOT_FROZEN / NO_RUNTIME_IMPLEMENTATION**. This receipt records independent
consumer/API input and follow-up experiments, not design approval or delivery.
Existing exact checkpoint reviews and32 successful CI checks do not close the
following runtime-design findings.

## Independent findings and disposition

| Finding | Owner | Evidence and required disposition |
| --- | --- | --- |
| P1: fresh TV has no authenticated selected-owner key/origin | Core/API/Apple | API source audit confirms APNs/install proofs are not HA-owner attestations; OOB/PAKE remains a proposal, not a qualified bootstrap |
| P1: ordinary navigation cannot enforce the draft's no-redirect rule | Core/receiver | Receiver measured Chromium/WebKit following302 off-origin; solve architecture/trust boundary before route freeze |
| P1: one-envelope wire does not specify a PAKE channel | API/Core/Apple/receiver | Current create/poll/submit/consume draft has no reviewed reverse exchange or bilateral confirmation; map a complete maintained protocol, loss/reorder/duplicate handling and original deadlines before implementation |
| Raw URL validation seam | Receiver/Core | Validate the authenticated raw string before constructing a normalized URL; otherwise default ports, case and dot segments may disappear before policy evaluation |
| OOB input and capability limits | Apple/receiver | Extra TV input, accessibility, shared-screen visibility, expiry, native/WASM support and restrictive CSP require actual review; no consumer source change or UX acceptance inferred |

The existing receiver owner independently ran all40 lexical cases in Python and
WHATWG URL, and six synthetic loopback browser cases: navigation follows302;
Fetch manual returns an opaque redirect without following; Fetch error rejects.
No real HA, public TLS/DNS, scanner, native wrapper, PAKE or physical TV was tested.

## Core follow-up: a framed surface is not an automatic solution

Core then tested an alternative solely to determine whether it could remove the
navigation finding. Twelve actual Chromium/WebKit cases used three temporary
loopback HTTP origins. The parent supplied a CSP restricted to the exact test
entry path and a sandboxed child with `allow-scripts allow-same-origin`, without
top-navigation permission. No credentials, real HA, public requests or grants
were involved; all servers, contexts and browsers were closed afterward.

| Case, in both engines | Measured result |
| --- | --- |
| Direct permitted entry | Child ready message received |
|302 to another origin | Parent frame-src policy blocked navigation; zero foreign requests |
|302 to a different path on the same origin | Redirect followed; child ready message identifies the different path, despite exact initial CSP path |
| Meta refresh to another origin | Blocked; zero foreign requests |
| Script navigation to another origin | Blocked; zero foreign requests |
| Child tries to navigate top window | Sandbox rejected; parent URL remained unchanged |

These results qualify **synthetic browser mechanics only**. They do not prove a
general network-egress fence, selected-HA framing support, safe content, TLS,
actual provider/media behavior or a hard no-redirect policy. Parent frame-src is
not a substitute for the child's own resource/connection policy. A child-ready
message supplies neither owner authentication nor Session authority.

The [reproducible probe](../../scripts/verification/vibecast_frame_fence_probe.mjs)
requires an existing Playwright installation and browser binaries; no dependency,
runner or product path is installed or changed by this experiment. Example:

```sh
DJC_PLAYWRIGHT_MODULE=/absolute/path/to/playwright/test/index.mjs \
PLAYWRIGHT_BROWSERS_PATH=/absolute/path/to/existing/browser/binaries \
node scripts/verification/vibecast_frame_fence_probe.mjs /tmp/frame-results.json
```

It binds only ephemeral loopback ports. Results contain synthetic cases only.
The default module name is `@playwright/test`; missing prerequisites fail rather
than downloading browsers. This optional experiment is not a new required CI
dependency or a replacement for the real HA/browser acceptance matrix.

## Decisions still required, with no implied selection

1. **Bootstrap/profile:** choose an independently authenticated owner-to-TV
   channel and exact implementation/profile. API identified Magic Wormhole
   client-to-client / Rust0.8.1 as an investigation candidate. Its mailbox,
   PAKE, key confirmation and encrypted application exchange are more than a
   single envelope. Its underlying spake2 library reports no independent audit.
   Neither the library nor a weakened derivative is selected by this receipt.
   OPAQUE alternatives introduce registration/server roles; no new central
   pairing registry is authorized. Pin license, release, audit scope, supported
   Swift/native and WASM/browser bridge, maintenance owner and independent vectors.
2. **Wire:** after choosing a complete profile, jointly specify its roles,
   directions/rounds and confirmation boundary; bind installation, raw route,
   transaction, browser key/generation and original expiry in the authenticated
   application context. The relay's ready state is not owner approval. Test
   first-submit abuse, reflection, substitution, reordering, duplicate delivery,
   lost messages, cancellation and retry without deadline renewal.
3. **Navigation:** either qualify an enforceable controlled surface, or explicitly
   review the selected HA/proxy as the trust boundary after the validated initial
   destination. The latter requires changing the current absolute no-redirect
   promise, direct-entry/proxy checks and accurate error/readiness semantics.
   A fetch precheck followed by navigation has a race and does not qualify either
   option. A framed surface changes UX, origin/storage/framing/CSP/fullscreen and
   compatibility; the experiment does not select that architecture.
4. **UX/revocation:** assess the extra A-only input separately from B's six digits;
   define entropy, trusted-endpoint attempt budgets, original expiry and what
   happens after disclosure. Recheck pairing immediately before release; an
   already disclosed destination cannot be recalled. B must independently
   require current owner/share/Session authority and never mint Session-end rights.

**One resume action:** obtain the joint Core/API/Apple/receiver design disposition
for the complete authenticated channel and navigation boundary, with independent
security/privacy and UX approval, then implement the existing selected Core
assignment. Do not merge an incomplete product, mark this family completed,
start another assignment or infer deployment authority from this checkpoint.
There is no missing general human merge/Finalization/cleanup permission.

## B implementation checkpoint: paired transitions, not full acceptance

After exact `ae2adfe9` B-design GO, Core implemented a partial Runtime-owned
authority/HTTP boundary. A remains unavailable. The optional
[real HA transition probe](../../scripts/verification/verify_display_admission_http.py)
runs in its own bounded networkless HA container with source mounted read-only,
ephemeral local TLS trust, ordinary production pairing, actual Profile storage,
Session Runtime and production HTTP views. External Spotify/knowledge I/O alone
is explicitly fixtured. No owner admin credential substitutes for device auth.

Measured chain: normal pairing persists the minted device token; existing
Session start and native owner-context read work; a same-origin browser creates
a claim; paired resolve/explicit consent/duplicate approval/one-time collection
work; the dedicated display bearer cannot access owner context; renewal is
idempotent and rejects skipped sequences; owner revoke removes only that display
and leaves its Session active; real privacy A→B→A storage commits permanently
withdraw the share; normal Session end removes remaining authority. The B
transitions cause **zero provider calls**. Missing/foreign Origin is denied.

The [real aiohttp adapter probe](../../scripts/verification/verify_display_http_adapter.py)
separately passes six cases for duplicate/nested JSON keys, invalid/deep JSON,
declared/chunked byte limits, TLS/query/duplicate-auth denial, current body release,
revocation after awaited headers, and the closed nine-route list. It uses real
HA/aiohttp dependencies, not a replacement response writer. These are adapter
cases, not full end-to-end display acceptance.

Independent partial technical/privacy review found two P2 races: capturing a
replacement pairing after an awaited Profile resolve, and source/privacy ABA
resurrection from current-field equality alone. Fixes capture the original
admission before awaiting, bind the existing monotone Profile authority revision,
and latch observed withdrawal. Targeted tests cover both findings. Final exact
candidate review still follows the remaining implementation and qualification.

These transition views are not yet registered/advertised by the product.
Snapshot, bounded WSS, shared renderer/local-static browser acceptance, long-run
resource qualification, A interoperability and native/physical acceptance remain
open. This checkpoint neither completes the assignment nor authorizes its merge.

## Subsequent joint-owner input and Core disposition

After this receipt's target1dcb367, the existing receiver owner acknowledged
direct navigation with an explicit selected-HA/proxy trust handoff as the
compatible design direction. Core now records that choice in the canonical
admission and both parent references. The direct200/no-login/no-redirect route
remains a real configured-route acceptance requirement, not an enforceable
promise about later top-level responses. Joint API/Apple/security/privacy/UX
review still precedes freeze; no native/HA/physical qualification is inferred.

API separately assessed full unchanged Magic Wormhole client-protocol transport
in existing Worker/DO as technically feasible, but requiring a compatible
bidirectional mailboxserver and a jointly reviewed application/wire revision.
The Rust client library is not the server. Ciphertext retransmission on mailbox
recovery must be distinguished from one-time destination acceptance. Router
nameplate/mailbox/side are not identity proofs. This is feasibility only: exact
stack audit scope, native/WASM interop, trusted-endpoint attempts and deadlines,
OOB UX and owner binding remain open. No library/profile is selected.

Core also recorded actual B gaps: old handoff returns a broader token (including
audience signals), owner serialization is not the new display allowlist, no
share/display principal is already delivered, and relay install ID is stored per
config entry. These require explicit qualified issuer/authority/media and atomic
lifecycle design, not assumed reuse. No runtime change accompanies this update.

## Primary basis

- [HTML navigation](https://html.spec.whatwg.org/multipage/nav-history-apis.html#dom-location-replace)
  and [Fetch redirect handling](https://fetch.spec.whatwg.org/#concept-request-redirect-mode).
- [CSP frame-src](https://www.w3.org/TR/CSP3/#directive-frame-src),
  [source matching](https://www.w3.org/TR/CSP3/#match-url-to-source-expression)
  and [iframe sandbox](https://html.spec.whatwg.org/multipage/iframe-embed-object.html#attr-iframe-sandbox).
  CSP3 is a Working Draft; measured engine behavior is separately scoped above.
- [SPAKE2 specification](https://www.rfc-editor.org/rfc/rfc9382.html#section-3.1),
  [RustCrypto spake2 0.4.0](https://docs.rs/spake2/0.4.0/spake2/) and
  [Magic Wormhole client protocol](https://magic-wormhole.readthedocs.io/en/latest/client-protocol.html).
  These are review inputs, not qualification of a new composed protocol.
