# DJConnect

<p align="center">
  <img src="https://raw.githubusercontent.com/pcvantol/djconnect/main/assets/djconnect/djconnect-logo.svg" alt="DJConnect" width="760">
</p>

DJConnect. Muziekbediening met karakter.

DJConnect is a Home Assistant custom integration for DJConnect devices and apps.
Ask for music, let Home Assistant handle playback, and get a personal DJ-style
response back on your DJConnect client.

Website: [https://djconnect.dev](https://djconnect.dev)

## What You Get

- Pair DJConnect ESP32, Raspberry Pi, iPhone/iPad, Apple Watch, macOS and
  Windows clients with Home Assistant.
- Choose **Spotify Direct** or **Music Assistant** as the music backend.
- Control playback from DJConnect commands, app screens, Assist satellites or
  Home Assistant entities.
- Use Ask DJ for music requests, recommendations, follow-up questions and
  recent listening questions.
- Export server-side Ask DJ chat history through the HTTP-only backend route
  when clients need a user download.
- Use VibeCast on Apple clients for premium-ready live track/artist vibe
  bubbles from the current Home Assistant music backend context.
- Keep Music DNA opt-in and server-side in Home Assistant, with HTTP-only
  export/import for Apple client JSON downloads and restores after opt-in.
- Use Home Assistant Assist/STT/TTS for voice and DJ responses.
- Let realtime client mood choose the DJ announcement profile; the configured
  DJ voice profile is the fallback when no mood is provided. Home Assistant
  Assist/TTS still owns the actual spoken voice.
- Update supported ESP32 firmware through the Home Assistant update entity.
- Keep credentials in Home Assistant. DJConnect clients do not receive Spotify
  OAuth tokens.

## Requirements

- Home Assistant with HACS installed.
- A configured Home Assistant Assist pipeline with STT and TTS.
- A DJConnect ESP32 device, Raspberry Pi client, iOS/macOS/watchOS app or
  Windows client on the same local network during pairing.
- For ESP32 devices: 2.4 GHz WiFi.
- For Spotify Direct: Spotify Premium, a Spotify Developer app Client ID and a
  Home Assistant external HTTPS URL, preferably Nabu Casa.
- For Music Assistant: Music Assistant installed/configured in Home Assistant
  with a usable player.

## Install Through HACS

1. Open **HACS -> Integrations** in Home Assistant.
2. Open **Custom repositories**.
3. Add `https://github.com/pcvantol/djconnect`.
4. Select category `Integration`.
5. Install **DJConnect**.
6. Restart Home Assistant.
7. Go to **Settings -> Devices & services -> Add integration -> DJConnect**.

HACS deeplink:

```text
https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration
```

## Add DJConnect

The setup flow starts with a route choice:

- **Assist Conversation Agent**: use DJConnect DJ from Home Assistant Assist
  satellites without pairing a separate client.
- **DJConnect local device**: pair an ESP32 or Raspberry Pi client on your LAN.
- **DJConnect app**: pair iPhone/iPad, Apple Watch, macOS or Windows.
- **ESP32 WiFi over Bluetooth**: optionally write WiFi credentials before
  pairing an ESP32 device.

After that, choose the music backend:

- **Spotify Direct**: DJConnect runs Spotify OAuth in Home Assistant and uses the
  Spotify Web API for playback, devices, playlists, recent listening and
  recommendations.
- **Music Assistant**: Music Assistant owns provider login and DJConnect controls
  one selected Music Assistant player.

You can change the music backend later from the DJConnect options flow. Pairing,
device tokens, Ask DJ history and Music DNA stay in place.

## Spotify Direct Setup

Spotify Direct uses PKCE with a Spotify Developer app you create yourself.
DJConnect needs the app's Client ID, not a Client Secret.

1. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Start the DJConnect setup flow in Home Assistant.
3. Copy the exact redirect URI shown by DJConnect into the Spotify Developer app.
4. Enter the Spotify Client ID in DJConnect.
5. Approve Spotify access when Home Assistant opens the Spotify authorization
   page.

With Nabu Casa, the redirect URI usually looks like:

```text
https://<your-nabu-casa-id>.ui.nabu.casa/api/djconnect/v1/spotify/callback
```

If your Home Assistant external URL changes, update the redirect URI in Spotify
and reauthorize DJConnect.

## Common Entities

DJConnect keeps music-backend playback state inside the integration and clients
instead of exposing separate Spotify/Music Assistant playback entities in Home
Assistant. Common entities include:

- status, last command and corrected STT sensors
- test voice and refresh device-info buttons
- firmware update and ESP hardware/settings entities for supported ESP32 devices
- Raspberry Pi restart/shutdown buttons
- APNs readiness diagnostics for Apple app clients

Entity IDs can differ if Home Assistant renames the device or entities.

## Apple Push Notifications

iOS, macOS and Apple Watch clients register APNs tokens through
`POST /api/djconnect/v1/push/register`. Home Assistant validates the paired client
identity and forwards only the redacted registration metadata to the DJConnect
relay; APNs provider keys and raw APNs tokens are never stored in Home Assistant.

Development-signed Apple builds may send `push_environment: "development"` when
their APNs entitlement targets the sandbox. DJConnect normalizes that to
canonical `sandbox` in relay calls, status and registration responses. Production
builds must send `push_environment: "production"`. If registration reports
`invalid_bootstrap_proof` or `missing_bootstrap_proof`, pair the app with Home
Assistant again so the client receives a fresh bootstrap proof, then restart the
app to retry push registration.
When Music DNA is enabled, Home Assistant sends at most one daily
`music_discovery_ready` APNs wake/sync hint around 08:00 local time with
`body:"Je nieuwe aanbevelingen staan klaar!"`, `open_target:"music_discovery"`
and a deeplink to Ontdek. Clients should open Ontdek and refresh the Music
Discovery backend feed; the push never contains recommendation contents.

## VibeCast

Apple clients can poll `GET /api/djconnect/v1/vibecast` with their paired
DJConnect device token to receive cacheable structured bubbles for the current
track. The response uses backend-neutral playback context and a small safe
rich-text model instead of HTML or Markdown. If VibeCast is disabled, premium is
unavailable, playback is inactive, the backend is unavailable or generation
fails, the route still returns JSON with `enabled:false`, a stable `reason` and
empty `items[]`; clients should hide or degrade the feature and never show raw
errors. macOS and iOS use the same endpoint, response contract, item kinds,
disabled reasons, TTL/revision/cache semantics and current-track resolution;
differences belong in client presentation or reported render capabilities only.
Clients that include `emoji_safe` in `X-DJConnect-Render-Capabilities` may
receive inline `emoji` rich-text segments such as music notes or vibe symbols;
clients should render them inline and ignore unknown segment types safely.
When genre metadata is available, `context.genre_badge.label` gives clients a
compact top-right badge for the VibeCast surface; if the field is absent, hide
the badge.
When the selected backend has artist artwork, VibeCast also returns a proxied
artist shout-out image on `context.artist_image_url` and the `artist_fact`
bubble's `image_url`/`thumbnail_url`, so clients can show the visual without
loading direct external catalog URLs.
Music Discovery feed items aggregate repeated recent-track inputs: clients
should render one item per unique `id`/`uri` and may show `play_count` or
`based_on_count` as compact context instead of repeating the same title.

## Troubleshooting

- If setup says an Assist pipeline is required, configure a Home Assistant Assist
  pipeline with both STT and TTS first.
- If Spotify login does not return to Home Assistant, check that the Spotify
  redirect URI exactly matches the URL shown by DJConnect.
- If Spotify playback fails, reauthorize Spotify and check that the selected
  backend has an active playback target.
- If Ontdek/Music Discovery shows no recommendations, enable debug logging for
  DJConnect and look for `DJConnect Music Discovery` lines. They show whether
  feed/refresh/play requests arrive, whether Music DNA is disabled, whether a
  cached feed was used and how many sections/items were generated.
- If a local device cannot pair, make sure Home Assistant and the client are on
  the same LAN and that the 6-digit pairing code is still current.
- If the integration icon stays generic, redownload DJConnect in HACS, restart
  Home Assistant and refresh the browser/app cache.
- If diagnostics are needed, open the DJConnect integration diagnostics in Home
  Assistant. Diagnostics redact token, password, secret, proof, authorization,
  prompt, history, memory and raw audio fields.

## Documentation

- Client/API contract: [`API_CONTRACT.md`](API_CONTRACT.md)
- Technical design decisions: [`TECHNICAL_DESIGN_DECISIONS.md`](TECHNICAL_DESIGN_DECISIONS.md)
- Voice intent examples: [`VOICE_INTENT_DATA.md`](VOICE_INTENT_DATA.md)
- Development environment: [`DEVELOPMENT_ENVIRONMENT.md`](DEVELOPMENT_ENVIRONMENT.md)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
- Known issues: [`ISSUES.md`](ISSUES.md)
- Roadmap: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Security policy: [`SECURITY.md`](SECURITY.md)

## Licensing

Copyright (c) 2026 Peter van Tol.

DJConnect repositories are MIT-licensed unless a specific third-party dependency
or repository states otherwise. Third-party and open-source dependencies keep
their own licenses; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Spotify is a trademark of Spotify AB. DJConnect is not affiliated with,
endorsed by, or sponsored by Spotify AB.

<details>
<summary>Maintainer release checklist</summary>

Use this checklist for every Home Assistant integration release.

- Confirm the working tree only contains intended changes.
- Check third-party runtime packages, CI tools and local developer tools for
  available updates. Apply safe updates before release; when an update is
  intentionally skipped, record the reason in `HANDOFF.md`.
- Update `custom_components/djconnect/manifest.json` to the target version.
- Update `custom_components/djconnect/const.py` to the same target version.
- Update touched documentation, including `README.md`, `CHANGELOG.md`,
  `AGENTS.md`, `HANDOFF.md`, `TODO.md`, `ISSUES.md`, `SYNC_PROMPTS.md`,
  `PRODUCT_ROADMAP.md`, `TECHNICAL_DESIGN_DECISIONS.md`,
  `CHAT_BOOTSTRAP.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `info.md` and
  relevant files under `examples/` where applicable.
- Update and JSON-validate `examples/djconnect.postman_collection.json`
  whenever HTTP endpoints, auth headers, request payloads or response shapes
  change.
- Keep `examples/ask_dj_e2e_cases.json` current for Ask DJ client-visible
  intents.
- Always review all five supported translations: English, Dutch, German,
  French and Spanish. Keep them complete, natural and current for config-flow,
  options-flow, repair-flow, entity, service, endpoint and client-facing text,
  even when the change looks mostly API/docs/client-contract related.
- Re-run security/diagnostics redaction checks when payloads, logs,
  diagnostics, Ask DJ history, memory, push registration or token handling
  changes.
- Add or update tests for new behavior paths, regression risks, translations
  and edge cases.
- Verify `custom_components/djconnect/brand/` contains `icon.png`,
  `icon@2x.png` and `logo.png`.
- Verify `LICENSE`, [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the
  dependency inventory in `TECHNICAL_DESIGN_DECISIONS.md` stay current after
  dependency or tool changes.
- Run the lightweight tests:

```bash
python3 -m unittest discover -s tests
```

For focused contract checks:

```bash
python3 -m unittest tests.test_translations
python3 -m unittest tests.test_ask_dj_e2e_contract
python3 -m unittest tests.test_postman_collection
```

Release helper:

```bash
./release.sh X.Y.Z
./release.sh X.Y.Z --dry-run
```

After publishing, verify HACS install/redownload, restart Home Assistant, add or
reload DJConnect, complete pairing/OAuth, open options, check icon/logo and run
the core developer actions.

</details>
