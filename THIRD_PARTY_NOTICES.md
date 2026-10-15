# Third-Party Notices

DJConnect includes a Home Assistant custom integration and is designed to work
with DJConnect devices. This file summarizes third-party projects, APIs and
trademarks that may be referenced by the integration.

For the maintained dependency inventory with repository-declared versions,
license models and source URLs, see `TECHNICAL_DESIGN_DECISIONS.md`.

## Home Assistant

The DJConnect Home Assistant integration uses Home Assistant custom integration
APIs, including config entries, diagnostics, HTTP views, services, entities,
Assist/conversation integration points, TTS helpers, Bluetooth discovery and
zeroconf/mDNS discovery.

Home Assistant and its components are open-source software. Their licenses and
copyrights remain with their respective authors and contributors.

## Python Packages And Home Assistant Dependencies

The integration uses these runtime packages/components. Home Assistant Core
provides `aiohttp` and `awesomeversion`; the integration manifest requests
`segno` separately:

- `aiohttp` for HTTP client/server helpers used through Home Assistant.
- `awesomeversion` for firmware version comparisons.
- `segno` for generating local inline SVG QR codes in app pairing flows.
- `voluptuous` for Home Assistant config-flow schemas.
- `zeroconf` / Home Assistant zeroconf support for local device discovery.
- Home Assistant `bluetooth` and `bluetooth_adapters` integrations for BLE WiFi
  provisioning.
- Home Assistant `conversation` and `assist_pipeline` integrations for HA-native
  Assist command processing.
- Home Assistant `tts` integration for generating temporary DJ response audio.
- Home Assistant `cloud` integration as an optional/late dependency for
  discovering the user's Nabu Casa external URL during Spotify OAuth setup.

If `async_timeout` is present in the Home Assistant runtime environment, its
license remains with its respective authors. DJConnect does not claim ownership
over third-party Python packages or Home Assistant components.

## DJConnect API Relay

Apple push notifications for iOS, macOS and watchOS clients are relayed through
the separate central `djconnect-api` service when configured. The Home Assistant
integration does not contain APNs provider credentials, does not persist APNs
tokens and treats push as a best-effort wake/sync signal only.

## Spotify API And Trademark Notice

DJConnect may reference Spotify APIs and Spotify playback concepts to provision
and control user-authorized Spotify playback.

Spotify is a trademark of Spotify AB. DJConnect is not affiliated with,
endorsed by, or sponsored by Spotify AB. References to Spotify APIs are API
usage only and do not imply endorsement, sponsorship, partnership or official
support by Spotify AB.

## Music Information APIs

Ask DJ may use external public music information APIs for non-mutating
informational answers. Technical track analysis can use MusicBrainz and
ListenBrainz metadata/context, with caching and rate-limit protection, to add
release, genre/tag or public listen context. This metadata does not represent
measured waveform, BPM, key, stems or exact arrangement-section analysis.
Concert agenda answers can use Bandsintown event data and return Bandsintown
source links to DJConnect clients. These references are API usage only and do
not imply endorsement, sponsorship, partnership or official support by
MusicBrainz, ListenBrainz, MetaBrainz Foundation or Bandsintown.

## DJConnect Firmware And Devices

Copyright (c) 2026 Peter van Tol.

DJConnect repositories are MIT-licensed unless a specific repository or
third-party dependency states otherwise.
The Home Assistant integration may be distributed separately for use with
DJConnect devices under the terms of `LICENSE`.

## VibeCast qualified factual cards and Spotify asset

The current-slice factual adapter uses only MusicBrainz core CC0 data (entity
identity, life-span and explicit relationships) and Wikidata structured CC0
localized descriptions with reciprocal artist identity. It excludes
MusicBrainz supplementary annotations/tags/ratings and Wikipedia article text.
Public resource attribution accompanies each visual fact. See the bounded
[source qualification contract](docs/product/VIBECAST_OWNER_REFINEMENTS_CONTRACT.md).

The inline white Spotify full logo in `vibecast.html` is the unchanged
`Full_Logo_White_RGB.svg` from Spotify's official
[2024 full-logo asset archive](https://developer.spotify.com/images/guidelines/design/2024-spotify-full-logo.zip).
Spotify retains its trademark and asset rights; the DJConnect MIT license does
not relicense this asset. Its use attributes Spotify metadata/artwork under the
[Spotify design guidelines](https://developer.spotify.com/documentation/design).
DJConnect remains independent of Spotify AB; no endorsement is implied.
