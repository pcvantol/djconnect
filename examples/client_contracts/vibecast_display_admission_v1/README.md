# Display admission — contract-review corpus

Assignment `DJC-CORE-VIBECAST-DISPLAY-ADMISSION-V1-20261016`.
Status **REVIEW_CANDIDATE_NOT_FROZEN**; no live endpoint or crypto vector.

[Canonical Core review](../../../docs/product/VIBECAST_DISPLAY_ADMISSION_V1.md)
records the missing TRUST-1 anchor and independently required HA phase B.
`route-cases.json` has39 synthetic positive/negative lexical decisions. No case
fetches a destination or claims valid DNS, TLS, redirect behavior, pairing,
selected-owner trust, HA grants, native adoption or physical TV acceptance.

Run both independent consumers from repository root:

```sh
python3 scripts/verification/vibecast_display_route_contract.py
node scripts/verification/vibecast_display_route_contract.mjs
python3 -m unittest tests.test_vibecast_display_route_contract
```

The proposed HTTPS443/canonical-origin/exact-path policy remains subject to
Core/API/Apple/receiver review. Unsupported custom ports and redirect handling
are explicit review boundaries. A passing corpus is not protocol freeze.
