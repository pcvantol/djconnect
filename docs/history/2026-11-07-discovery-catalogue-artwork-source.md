# Discover catalogue fallback artwork source qualification

## 2026-11-07 — Preserve exact Spotify artwork in the Discover catalogue fallback

#### Repository Status

Bounded Core correction from reconciled main
`c4d9ee2b2fd00577297abc0faa7d84c197a915fe` (#1511 / #1512).
HA-dev debug `a909e8036f72a9d787a79d11caf505a738dd2e4b` and the original #1439
overlay remain installed until protected delivery qualifies.

#### Management Summary

The normal paired Discover feed returned six catalogue-fallback tracks
without image URL, expiry or attribution. Four bounded existing Spotify
catalogue searches returned those same six exact track identities, with
album URI and Spotify CDN image URL. The old search normalizer discarded
the validated reference needed by the Discover projector. On exact
predecessor product, isolated paired HA reproduces the missing image
despite an exact track/album/CDN provider response.

The private catalogue search request retains the existing normalized
artwork reference from the same Spotify response, only for exact playable
track and album identity and the permitted image CDN. Conflicting album
identity, local or relinked results and unavailable art still produce
placeholders. Ordinary search JSON cannot opt into the private reference.
The existing owner/profile/expiry-bound image route delivers the original
asset; no extra catalogue lookup, provider grant, playback effect, wire
field, or App-specific workaround was introduced. Raw catalogue URLs and
private references are never inserted into the Discover response.

The isolated paired real-HA reproduction now returns the original album
attribution, bounded image lease and exact fixture PNG, with no extra
track lookup. Wrong album ID stays without image, and a public request
cannot ask for the internal reference. Existing clear, owner, expiry,
rotation, and provider replacement tests remain. All 42 isolated HA
groups, 4,735 canonical tests with 11 existing skips, 172 framework, 18
document checks, Ruff and Bandit pass. No native or installed acceptance
is inferred from the fixtures. Historical receipts stay frozen.

#### Roadmap Position

Generation 2 Product Development / Phase 1 Platform Qualification unchanged.
Same optional image contract and catalogue fallback. All five UI languages
and Help 28/42 unchanged.

#### Rolling Horizon (Execution Horizon — Next 5 Planned)

Derived afresh from docs/roadmap/v1/djconnect-platform-v1.json and CATALOGUE.md;
producer edges SETTINGS-4/6/8/10/12 retain the same prerequisites. These entries
do not issue prompts or grant execution/native dispatch authority.

1. **SETTINGS::APPLE::EDITOR — One Jouw DJ editor and shared Session quick controls**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

2. **SETTINGS::PI::ADOPTION — Pi allowed shared Session settings and legacy disposition**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

3. **SETTINGS::ESP32::ADOPTION — ESP32 Assist/voice/settings compatibility and legacy disposition**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

4. **SETTINGS::VIBECAST::COMPAT — Shared renderer allowed Session fields without Profile preferences**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

5. **SETTINGS::WEBSITE::COPY — Six-parameter scope/help and obsolete settings copy audit**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

#### Blocked Items

Exact-head Source checks/Owner Authorization, merge, complete independent
main CI, original #1439 debug composition, HA-dev install/readback and a
separate Final remain. Matching ordinary installed response and native
rendering require independent verification after READY.

#### Deferred Items

Golden remains execute:false. Physical Watch, signing/restore, retained
latest #1486 and APNs remain independent. Keep the timer stopped and retain
WIP, rollback and private evidence.

#### Repository State

Repository State: `MERGED_RECONCILED` for predecessor only. This Source
requires its own protected merge and separate Final.

#### Workspace State

Workspace State: `NOT_READY` until protected delivery and own Final cleanup.
See [qualification](docs/verification/DISCOVERY_CATALOGUE_ARTWORK_20261107.md).

<!-- discovery-catalogue-artwork-source-20261107-end -->
