# Known Limitations

Status: Initial list from accepted Epic 3/Epic 3B documents plus live
verification constraints.

## Accepted Baseline Limitations

| ID | Limitation | Impact | Classification | Owner |
| --- | --- | --- | --- | --- |
| KL-01 | Rich `resolved_profile` response metadata is not universal. | Clients may need to rely on `profile_id` and `music_dna_key` until richer metadata is added privacy-safely. | Non-blocking cleanup | `pcvantol/djconnect` |
| KL-02 | Polished Home Assistant mapping UI for Voice Endpoints, areas and playback zones remains follow-up UX work. | Admin mapping may require lower-level setup or developer-oriented flows during validation. | Warning | `pcvantol/djconnect` |
| KL-03 | Cross-repository fixture conformance dashboard is not yet formalized. | Client parity must be checked manually in this program. | Warning | All client repos |
| KL-04 | Formal required/optional/forbidden client parity belongs in Epic 5. | This program verifies practical parity but does not replace Epic 5 governance. | Non-blocking | Platform |
| KL-05 | Public product-language and distribution cleanup belong in Epic 6/Epic 8. | Not a blocker for Profile Platform runtime validation. | Non-blocking | Website/release repos |
| KL-06 | Profile-native migration of older HA-user keyed Ask DJ history may remain for older installs. | Existing installs need explicit verification and may need migration guidance. | Warning | `pcvantol/djconnect` |
| KL-07 | Voice Endpoint validation requires real HA Voice hardware/runtime metadata. | Cannot be marked PASS from source tests alone. | Verification dependency | `pcvantol/djconnect` |

## Verification Dependencies

| ID | Dependency | Needed for |
| --- | --- | --- |
| VD-01 | Real Spotify account with required scopes | Spotify Direct, recently played, top tracks/artists, account relink. |
| VD-02 | Music Assistant configured target player | Backend switching and backend capability errors. |
| VD-03 | Apple client builds | Apple parity, profile switching, private sessions. |
| VD-04 | Windows client build | Windows parity. |
| VD-05 | Raspberry Pi client device/runtime | Ambient shared/privacy verification. |
| VD-06 | ESP32 hardware and firmware | PTT, OTA, status, device mapping. |
| VD-07 | Home Assistant Voice Endpoint | Voice request context, area mapping and no identity guessing. |

## Current Blocking Unknowns

These are not confirmed bugs. They block a GO decision until evidence exists.

| ID | Unknown | Required resolution |
| --- | --- | --- |
| BU-01 | Real client capability discovery behavior across Apple, Windows, Pi and ESP32. | Execute capability scenarios C-01 through C-06. |
| BU-02 | Real Voice Endpoint Request Context extraction and mapping. | Execute V-01 through V-08. |
| BU-03 | Backend restart and export/import durability on a fresh HA instance. | Execute B-01 through B-05 and X-01 through X-06. |
| BU-04 | Privacy behavior on shared Pi/Voice/Guest contexts. | Execute PV-01 through PV-06 plus PI and Voice scenarios. |
| BU-05 | Backend switching from Spotify Direct to Music Assistant without state corruption. | Execute BS-01 through BS-05. |

## Limitation Review Rule

Any limitation may remain non-blocking only if:

- it does not leak secrets or personal profile data;
- it does not corrupt Profile, mapping, backend or export/import state;
- it does not force clients to implement their own resolver order;
- it is documented with a clear owner and follow-up path.
