## Developer verification tools (1 November 2026)

The developer verification environment pins [coverage.py 7.17.0](https://pypi.org/project/coverage/7.17.0/), requiring Python 3.11 or newer, under [Apache-2.0](https://github.com/coveragepy/coveragepy/blob/7.17.0/LICENSE.txt). The isolated Pico developer environment pins [Ruff 0.17.2](https://github.com/astral-sh/ruff/releases/tag/0.17.2), requiring Python 3.7 or newer, under [MIT](https://github.com/astral-sh/ruff/blob/0.17.2/LICENSE). No upstream source is vendored or modified. Neither tool ships in the Home Assistant integration or Pico firmware. Older notices below retain their historical scopes.

## CI action pins (31 October 2026)

The build and verification workflows use the following unmodified upstream
actions. The five action entries, from four repositories, change 23 pinned
`uses` lines across 11 workflows. No action source is vendored into the Home
Assistant integration. Copyrights and any bundled dependency notices remain
with their upstream authors; an action repository's license does not relicense
the scanners, services or artifacts it invokes.

| Action | Repository-declared version and exact commit | Upstream license and source |
| --- | --- | --- |
| `actions/setup-python` | v7.1.0, `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | [MIT](https://github.com/actions/setup-python/blob/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0/LICENSE); [action source](https://github.com/actions/setup-python/blob/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0/action.yml) |
| `github/codeql-action/init` and `analyze` | v4.39.1, `9b3254085494b55a0f7c4c2b3d2d52cc712ce370` | [MIT action repository](https://github.com/github/codeql-action/blob/9b3254085494b55a0f7c4c2b3d2d52cc712ce370/LICENSE); [init](https://github.com/github/codeql-action/blob/9b3254085494b55a0f7c4c2b3d2d52cc712ce370/init/action.yml) and [analyze](https://github.com/github/codeql-action/blob/9b3254085494b55a0f7c4c2b3d2d52cc712ce370/analyze/action.yml) |
| `home-assistant/actions/hassfest` | `86d4564712fa02543c808e3a693dd04f9d3f8361`; existing governed immutable master exception, no semantic release tag asserted | [Apache-2.0](https://github.com/home-assistant/actions/blob/86d4564712fa02543c808e3a693dd04f9d3f8361/LICENSE); [exact upstream comparison](https://github.com/home-assistant/actions/compare/cd6f3635a740c84d8a14f6121a90068b8ece6bf6...86d4564712fa02543c808e3a693dd04f9d3f8361) |
| `docker/login-action` | v4.7.0, `81c6f93d4bc991e510b342a00b419b3bb4efc5c6` | [Apache-2.0](https://github.com/docker/login-action/blob/81c6f93d4bc991e510b342a00b419b3bb4efc5c6/LICENSE); [action source](https://github.com/docker/login-action/blob/81c6f93d4bc991e510b342a00b419b3bb4efc5c6/action.yml) |

These are CI tools, not new runtime dependencies. The integration manifest,
Python and interpreter selections, onboarding desired state and installed
runtime retain their separate existing versions. The maintenance record in
`TECHNICAL_DESIGN_DECISIONS.md` describes the preserved workflow boundaries.
Earlier notices below keep their original scopes.

## Home Assistant public AI Task schema type (25 October 2026)

The optional structured playback path uses [Probatio](https://github.com/frenck/probatio), supplied by the qualified Home Assistant2026.10.0 image as0.13.0, under the [MIT license](https://probatio.frenck.dev/project/license/). It is the public schema type accepted by HA’s AI Task API. No Probatio source is vendored or modified, and no additional package is installed by this feature. Home Assistant retains ownership of this framework dependency; other HA versions fail closed for the optional path until qualified. Previous notices remain below unchanged.

## Developer decoder compatibility qualification (24 October 2026)

The developer test environment pins [Pillow13.0.0](https://pypi.org/project/pillow/13.0.0/) under its existing MIT-CMU/HPND license. Pillow requires Python3.11 or newer, including the existing3.11 and3.14 checks. No upstream Pillow source is vendored or modified. A separate exact12.3.0 CI environment and the actual Home Assistant2026.10.0 image preserve the existing HA decoder baseline. The offline brand generator retains its separate13.0.0 pin. New fixtures contain only generated synthetic images and no owner media. This current developer scope supersedes the prior developer12.3 deferral; the historical notices below retain their runtime and delivery scope.

## Pico developer-tool Ruff pin (24 October 2026)

The isolated developer-tool environment uses [Ruff0.17.1](https://github.com/astral-sh/ruff/releases/tag/0.17.1), maintained by Astral and contributors under the [MIT license](https://github.com/astral-sh/ruff/blob/0.17.1/LICENSE). This lint tool is not included in a Pico firmware image or the Home Assistant integration package; no upstream Ruff source is vendored or modified. The Home Assistant image/decode qualification environment remains on Pillow12.3.0; the separate offline brand generator's Pillow13.0.0 pin remains unchanged.

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
`segno` and `defusedxml` separately:

- `aiohttp` for HTTP client/server helpers used through Home Assistant.
- `awesomeversion` for firmware version comparisons.
- `segno` for generating local inline SVG QR codes in app pairing flows.
- `defusedxml>=0.7.1` for RSS/Atom XML parsing with DTD, entities and external
  references forbidden, alongside DJConnect's byte/depth/node bounds. Christian
  Heimes and contributors retain their copyrights; the upstream package uses
  the Python Software Foundation License Version 2. Source and license:
  https://github.com/tiran/defusedxml/tree/v0.7.1 and
  https://github.com/tiran/defusedxml/blob/v0.7.1/LICENSE. No package source is
  vendored or modified by this integration. Home Assistant owns its installed
  version; the development qualification environment pins `defusedxml==0.7.1`.
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

## Brand V2 generation (build only)

Brand V2 uses the unmodified Inter4.1 variable font by The Inter Project Authors,
under SIL Open Font License1.1. The font is **not** covered by DJConnect's MIT
license; its full upstream license and source/archive SHA256 are preserved in
`tools/branding/fonts/LICENSE.txt` and `PROVENANCE.md`. Official source:
https://github.com/rsms/inter/releases/tag/v4.1. Outlined wordmarks are documents
produced using the font; SVG image marks embed the owner-approved raster source.

The offline asset generator uses [Pillow13.0.0](https://pypi.org/project/pillow/13.0.0/)
(MIT-CMU/HPND) and [fonttools4.67.0](https://pypi.org/project/fonttools/4.67.0/)
(MIT). These are pinned build-only tools in `tools/branding/requirements.txt`;
neither is added to the HA integration's runtime requirements. Generated native
and Website consumer exports do not relicense the font or any Spotify asset.

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

## Optional Wikimedia Commons artist imagery

The opt-in Session-media v2 adapter uses Wikimedia's MediaWiki APIs for public
artist image references and file metadata. Individual images retain their
recorded creator, credit and license; metadata availability or CC0 metadata does
not make a photograph MIT-licensed. Source/creator/license links must accompany
qualified display. Product source licensing remains MIT; the integration package
does not bundle these photographs. See
[artist photo contract2](docs/product/SESSION_ARTIST_PHOTO_V2.md).
