# Display admission — contract-review corpus

Assignment `DJC-CORE-VIBECAST-DISPLAY-ADMISSION-V1-20261016`.
Status **A_REVIEW_CANDIDATE_NOT_FROZEN**. The lexical corpus is not a crypto
vector or live route proof. B has the independently reviewed implementation
checkpoint described below; no A freeze or complete product delivery follows.

[Canonical Core review](../../../docs/product/VIBECAST_DISPLAY_ADMISSION_V1.md)
records the missing TRUST-1 anchor and independently required HA phase B.
`route-cases.json` has40 synthetic positive/negative lexical decisions. No case
fetches a destination or claims valid DNS, TLS, redirect behavior, pairing,
selected-owner trust, HA grants, native adoption or physical TV acceptance.

Run both independent consumers from repository root:

```sh
python3 scripts/verification/vibecast_display_route_contract.py
node scripts/verification/vibecast_display_route_contract.mjs
python3 -m unittest tests.test_vibecast_display_route_contract
```

The proposed HTTPS443/canonical-origin/exact-path policy remains subject to
Core/API/Apple/receiver review. Unsupported IDNA names/custom ports and redirect handling
are explicit review boundaries. A passing corpus is not protocol freeze.

## Actual B transport examples

`b-transport-actual-ha-v1.json` contains HTTP request/response and WSS snapshot
examples captured from the real isolated HA probe, using normal production
registration, ordinary device pairing, actual Profile storage and Session
Runtime. Only external providers are fixtures. Current producer code pin:
`3cb9cf129f31d419e8b2027e4dc1ba08fafdb9d8`;26 examples include B support
discovery and a missing-external-HTTPS owner-context failure. The discovery
record explicitly uses `response_projection` for its B-only subset, not a
pretended complete platform response. Consumer adoption remains separate.

All grant/claim secrets, nonces, issuer/browser/display/share opaque values and
six-digit codes are replaced with nonfunctional examples. Replacements preserve
cross-response equality and field shapes; they are derived from ordinal fixture
position, never from the original credential. Requests contain authentication
**kind**, never actual Authorization headers. Other IDs/timestamps belong only
to the synthetic ended lab Session, not a real user installation. Unexpected
private fields fail capture closed. These examples cannot be replayed as auth.

The captured owner context's `display_entry_url` and
`route_trust:"paired_owner_response"` provide the current existing-pairing route
source for the A discussion. They are not App Attest, independently trusted HA
issuer evidence, intended-TV-owner proof or a grant to enter the Session.

Consumer tests should cover pending/approved/consumed/expired claims, stale
binding/generation, source/Session withdrawal, missing external HTTPS config,
all denied owner capabilities and original deadlines. These examples do not
start an Apple/receiver assignment or qualify a public HA route/native/TV.

### Separate eight-viewer qualification receipt

`b-eight-viewer-qualification-v1.json` is an aggregate result of the opt-in real
HA eight-transport test at probe5528aa75. It is not an HTTP fixture, native test
or added live capability. It contains no usable credentials or authority IDs.
The source digest includes the probe and is independently rechecked; integration
bytes remain equal to producer3cb9cf12. Default26-example capture is preserved.
See the receipt's explicit no-claims and resource/reproduction boundaries.
