# VibeCast B protected-source readback — 20 October 2026

The existing API owner requested the exact HA destination and separate screen
admission for the actual Apple simulator integration. This readback preserves
the existing Core WIP; it creates no consumer writer or deployment.

## Source and consumer boundary

GitHub confirms [PR1197](https://github.com/pcvantol/djconnect/pull/1197)
merged on 18 October 2026 at 10:41:55 UTC as
`c98cbf3e3114afb8b8212e18224a337b12af3e27`, candidate
`a5840acdffa99a8c1180d90b714c3c0fb9d983c2`. Current protected main is
`8b221d07fe2215d9516d18fe92c832332c7a16ab`. The registered B transport,
service, authority, origin, admission and capability files in the current WIP
are byte-equal to that protected source. Earlier draft/not-merged wording is
historical. This readback does not establish a separately verified Finalization
for the entire1197 consolidation or close its remaining functional acceptance.

`register_http_views` registers the B transitions, shell and live route.
The shared transport capability advertises version1 B support with
`owner_context_required` and `rendezvous_a:false`. A remains separate.

The A implementation agreement is protected-delivered through API PR96
`2dade83f338ae5f931856934ab0c23b6f6c66f05` and separate Finalization97
`661e5770eb5249b1b02bbdc2426ba7e575fc8881`. Its current
[implementation-contract release](https://github.com/pcvantol/djconnect-api/blob/2dade83f338ae5f931856934ab0c23b6f6c66f05/docs/rendezvous/IMPLEMENTATION_CONTRACT_RELEASE_V1.md)
fixes `djc-rendezvous/1-implementation.1` / wire `djc-rendezvous/1` and
explicitly supersedes enumerated old missing-ACK/HOLD/NOT_FROZEN wording.
No repeat unchanged receiver/Apple ACK is requested. Public service/configuration,
genuine native trust, consumer activation and complete A→B remain separate gates.

The normally paired app first reads `POST /api/djconnect/v1/transport/context`
and compares its current `ha_install_id` with the explicitly selected saved
installation. It then reads `POST /api/djconnect/v1/display/owner/context`
using its paired bearer and `{contract_version:1,identity:{device_id,client_type}}`,
optionally its current `session_id`. Current owner types are `ios` and `macos`.
Only that authenticated response supplies `display_entry_url`,
`route_trust:"paired_owner_response"`, epoch, actual Session or null, limits
and optional share metadata. `issuer_epoch` is a process fence, not an install
ID or attestation key. An entry's relay ID is not a global trust root.

A may transport that exact destination/context through its separately qualified
transaction. No owner/display bearer, Session start, share consent or B admission
follows from scanning, submitting, consuming or navigating. The browser navigates
to the selected external HTTPS origin plus `/djconnect/vibecast/display`, then
creates B's separate original120s claim and six digits. The app resolves those
digits and explicitly approves the exact claim/epoch/generation/code/current
Session and share. Only the original browser's secret/nonce binding can collect
one dedicated `djcd_` display bearer. Display leave, owner revoke and Session end
remain distinct. No active Session means no automatic Session creation.

Exact schemas/codes remain owned by `display_service.py`, `display_authority.py`,
`display_origin.py` and the [B contract](../product/VIBECAST_DISPLAY_ADMISSION_B_V1.md).
The [actual HA examples](../../examples/client_contracts/vibecast_display_admission_v1/b-transport-actual-ha-v1.json)
contain nonfunctional substituted credentials, not consumer authentication.
No live hostname is qualified from examples, tunnel inventory, QR, Host headers
or cached pairing alone. Authenticated current owner context supplies the origin;
missing config fails `display_external_url_unavailable`. Exact canonical public
ASCII HTTPS/default port/fixed path, without query/fragment, is required.
Direct200 without redirect/login is a real selected deployment qualification.

The current B-owner whitelist is an implementation boundary; it does not prove
that the newly selected Pi feature-parity target is already implemented.

## Fresh actual isolated HA execution

At09:49UTC, the unchanged owning probe ran from a fresh export of protected
main8b221d07. Probe SHA256
`93bef13bcb49fe568b60f46921dd4005c94f8d2cf25d41491f38393901580114`;
existing image
`ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4`.
Network disabled, source read-only, private tmpfs configuration/loopback TLS,
1GiB/two CPUs/dropped capabilities. No live credential read or installation.

Exit0: `REAL_ISOLATED_HA_HTTPS_DISPLAY_TRANSITIONS_SNAPSHOT_BASIC_LIVE`.
All twelve owning groups passed: ordinary pairing/current owner context;
claim/resolve/explicit approval retry/one-time collect; owner-effect/private
Ask DJ denial; closed shared snapshot; preauth capacity/released slots; actual
WSS/Mood/superseded generation; origin/idempotent renewal; revoke preserving
Session; Profile privacy A→B→A withdrawal; Session-end revocation; and discovery
versus actual admission/missing HTTPS. Provider calls during B: **0**.
Aggregate181 source-file digest
`424a42d3ebf7935b68289d51a37d4d8a03fa195260962bcbd4f4ab40a600a7b5`;
log SHA256 `03fb40a68bb77485ae1bca4b9b8106bcbd33874bd5a9a04657f87bb0fbcfc039`.
Private evidence:
`artifacts/core-contextual-sixhour-20261020/b-protected-8b221d07-20261020/`.

Older70s/eight-viewer/browser qualification was not repeated. This proves the
current isolated B software chain, not selected public TLS/proxy/direct200,
native simulator pairing, A interoperability, installed renderer, CAF, TV,
audible speech or complete product acceptance.

Apple owns the actual saved HA record, secret-local authenticated current context,
ordinary binary and simulator execution. API owns exact A profile/wire/router/
module/edge admission. Receiver owns real validated navigation and qualified
bundle adoption. No secrets belong in chat; no old fixture substitutes for these
joint inputs. Existing owners received this exact sequence and proof boundary.
