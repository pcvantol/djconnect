# DJConnect

<p align="center">
  <img src="https://raw.githubusercontent.com/pcvantol/djconnect/main/assets/djconnect/djconnect-logo.svg" alt="DJConnect" width="760">
</p>

DJConnect. Muziekbediening met karakter.

DJConnect is a Home Assistant custom integration for ESP32, iOS, macOS, watchOS, Raspberry Pi and Windows DJConnect clients. Ask for music, let Home Assistant handle Spotify playback, and hear a personal DJ announcement back on the DJConnect device.

Website: [https://djconnect.dev](https://djconnect.dev)

The Home Assistant integration handles pairing, Spotify OAuth, backend playback commands, OTA firmware updates, device status, and voice/AI integration. Spotify credentials stay in Home Assistant; the ESP sends generic playback commands to the integration.

## Current Version

- Home Assistant integration: `3.1.99`
- Domain: `djconnect`
- HACS category: `Integration`
- Device target: DJConnect device
- Firmware mDNS service: `_djconnect._tcp`
- Device ID formats: `djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX` and `djconnect-esp32-s3-box-3-XXXXXXXXXXXX`.
- Legacy `djconnect-XXXXXXXXXXXX` device IDs are not accepted.

## Features

- Pair a DJConnect device with the displayed pairing code or 12-character device suffix.
- Optionally provision WiFi credentials over BLE before normal pairing.
- Provision a per-device bearer token.
- Run Spotify OAuth with PKCE from the Home Assistant config flow.
- Open the Spotify authorization website instead of manually pasting an OAuth result.
- Support a Nabu Casa HTTPS callback at `/api/djconnect/spotify/callback`.
- Keep Spotify OAuth credentials in Home Assistant and use them for backend playback commands.
- Control the paired DJConnect device through its HA-native local API.
- Accept raw WAV voice uploads from the ESP and run HA Assist STT in the integration backend.
- Expose DJConnect as a Home Assistant Assist conversation agent for Assist satellites such as Voice Preview Edition.
- Use Home Assistant Assist/TTS settings with safe defaults.
- Process text commands through the selected/default Assist conversation agent and DJConnect's music parser before sending the resulting intent to Spotify.
- Answer current-track questions such as `Welk nummer draait er nu?` with a DJ response based on Spotify's current playback state, without starting new playback.
- Handle direct DJ playback controls such as `Stop muziek`, `Start muziek`, `Zet harder`, `Zet zachter`, `Volgende nummer` and `Vorig nummer` without running a Spotify search.
- Keep server-side DJ Memory for future `Ask DJ` follow-ups across lightweight iOS, macOS, watchOS, Raspberry Pi and Windows clients.
- Resolve Ask DJ music follow-ups such as `wat speelt er`, `op welk album werd dit nummer uitgebracht`, `speel album`, `speel het album met nummer X van artiest Y` and `van wie is ook alweer het nummer X?` from Spotify playback/search metadata with Play Now context for tracks and albums.
- Answer recent listening-history questions such as `Welke nummers heb ik afgelopen uur afgespeeld?`, `Welke albums heb ik vandaag geluisterd?`, `Welke artiesten hoorde ik net?` and `Welke playlists heb ik afgelopen uur gespeeld?` from Spotify recently played data.
- Generate DJ announcements through the selected/default Assist conversation agent with DJConnect-specific prompt instructions and fallback guardrails.
- Use HA-native Assist/TTS routes in active services and entities.
- Track client status, firmware/client version, last command, last corrected STT, last track and backend playback state.
- Keep Spotify-backed control/status entities in sync with current playback availability, volume, repeat/shuffle, output, queue and playlists when Spotify credentials are available.
- Track ESP-only battery, Wi-Fi RSSI, screen/LED state and firmware updates only for ESP32 clients.
- Provide diagnostics with sensitive values redacted.

## Architecture Decisions

DJConnect intentionally separates Home Assistant orchestration from firmware
runtime behavior. These decisions are part of the integration contract:

- **HA-native Assist/STT/TTS**: microphone audio is transcribed by this integration through Home Assistant's supported `stt.async_process_audio_stream` helper. DJConnect uses the configured Assist pipeline, falls back to Home Assistant's preferred/default pipeline, then the first pipeline with STT. The selected pipeline also supplies TTS for temporary DJ announcement audio. DJConnect uses the selected/default Assist conversation agent for Spotify intent detection, guarded STT correction and DJ announcement generation, with DJConnect-specific prompts that tell the agent to ignore earlier/global smart-home instructions for the DJ response. The ESP uploads raw WAV audio to `POST /api/djconnect/voice` using its DJConnect device token; no Home Assistant websocket token is sent to the ESP.
- **No direct external AI/STT/TTS APIs**: active Home Assistant routes use HA Assist and HA TTS only. OpenAI or other direct external AI/STT/TTS clients are not part of the active voice path.
- **Device speaker for DJ announcements**: DJ announcements are not played through Spotify Connect or a Home Assistant media player. Home Assistant creates a temporary WAV or MP3 URL when possible and posts `text` plus optional `audio_url` to the ESP endpoint `/api/device/dj_response`. Dutch announcement prompts explicitly ask TTS/Assist to pronounce English artist, album and track names in English.
- **Assist satellite conversation agent**: DJConnect also exposes a Home Assistant conversation agent named `DJConnect DJ`. Assist satellites such as Voice Preview Edition can use that agent for wake-word/STT/TTS while DJConnect handles Spotify intent detection, playback and the spoken DJ response. During initial setup, choose `Assist Conversation Agent` when you want this HA-only route without pairing a DJConnect client.
- **Server-side DJ Memory for Ask DJ**: lightweight clients do not store DJ Memory. Home Assistant owns compact `Ask DJ` context through runtime session memory plus Home Assistant Store key `djconnect_memory` version `1`. Memory is scoped first by HA user id when available, then by DJConnect client/device id, so a Watch request such as `Draai iets rustigers` can be followed later from another client with `Waarom koos je dit?`. Stored memory excludes OAuth tokens, bearer tokens, raw audio and full prompts.
- **Music knowledge prompt policy**: DJConnect does not initialize external music sources on every request. The DJ response prompt tells the configured conversation agent to use provided Spotify metadata, DJ Memory and media context first, and only use MusicBrainz, Wikidata, short Wikipedia summaries, Last.fm, Discogs or TheAudioDB when that knowledge is already available to the agent/integration. Trivia must be skipped rather than invented.
- **HA owns backend playback**: the ESP does not store Spotify OAuth credentials and does not call the Spotify Web API directly. It sends generic playback commands to `POST /api/djconnect/command`; Home Assistant translates them to the current backend, currently Spotify.
- **Backend playback controls**: Home Assistant exposes DJConnect buttons, numbers, selects and sensors for the backend playback session. DJConnect no longer creates a native `media_player` proxy; music control stays available through DJConnect commands and the Spotify-backed control entities.
- **Refresh-token rotation aware**: Spotify refresh tokens can rotate. Home Assistant stores the latest token and uses it as the canonical source for HA backend playback. If an older in-memory token is rejected but a newer stored token is available, DJConnect retries silently before creating a Repair issue. Pair/status responses never include Spotify OAuth secrets.
- **Access-token cache**: Home Assistant caches short-lived Spotify access tokens and refreshes them on demand. A normal one-hour Spotify access-token expiry should not open a Repair flow; only a rejected/revoked refresh token after all known stored tokens have been tried should.
- **OAuth through Home Assistant external step**: Spotify OAuth uses PKCE and the Home Assistant external step flow. The callback remains `/api/djconnect/spotify/callback`, with Nabu Casa HTTPS URLs preferred.
- **Pairing over WiFi, BLE only for WiFi credentials**: BLE provisioning writes only WiFi SSID/password to setup-mode devices. Spotify credentials, device tokens and other secrets are never sent over BLE.
- **mDNS first, Client adres as fallback**: ESP runtime prefers the device-reported `local_url`, exact `_djconnect._tcp` mDNS matches, then a single visible DJConnect mDNS device. During setup, Home Assistant also browses `_djconnect._tcp` for iOS/macOS/watchOS/Raspberry Pi/Windows app-like clients, validates `client_type` against the stable device ID, probes `/api/device/pairing-info`, and can prefill the Client adres, client type, device name and pairing code from authoritative pairing-info. Manual Client adres entry remains available when discovery or pairing-info reachability fails.
- **Small setup surface**: compatibility limits, OTA battery thresholds and DJ announcement audio TTL use internal defaults instead of user-facing options. Setup method is chosen only once at the start of the config flow. Firmware device selection is automatic through the public multi-device manifest; only ESP32 clients can choose the OTA firmware channel, `stable` or `beta`.
- **Single Home Assistant device**: sensors, buttons, settings and update entities share one stable device identifier so Home Assistant shows one DJConnect device instead of duplicate device entries.
- **MIT across DJConnect repos**: the Home Assistant integration, DJConnect clients and DJConnect firmware repositories are distributed under the MIT License unless a specific third-party dependency states otherwise.
- **No secrets in diagnostics/logs**: diagnostics redact keys containing `token`, `password` or `secret`; logs avoid full ESP payloads and do not intentionally log Spotify refresh tokens, WiFi passwords or device tokens.
- **Trademark clarity**: Spotify is a trademark of Spotify AB. DJConnect does not claim affiliation, endorsement or sponsorship by Spotify AB.

## Repository Layout

- Home Assistant integration: `3.1.99`
- ESP firmware source: `pcvantol/djconnect-app`
- Public firmware releases: `pcvantol/djconnect-firmware`
- Canonical cross-repo sync prompts live only in this HA repo: [`SYNC_PROMPTS.md`](SYNC_PROMPTS.md)
- Canonical product roadmap lives only in this HA repo: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Technical design decisions and dependency inventory: [`TECHNICAL_DESIGN_DECISIONS.md`](TECHNICAL_DESIGN_DECISIONS.md)
- Contribution guidelines: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Community code of conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- Security policy and private contact: [`SECURITY.md`](SECURITY.md)
- Fresh-chat bootstrap prompt: [`CHAT_BOOTSTRAP.md`](CHAT_BOOTSTRAP.md)

This repository contains the Home Assistant custom integration under `custom_components/djconnect`.

Brand images for the Home Assistant frontend are bundled in `custom_components/djconnect/brand/`.

For local development, Docker Home Assistant installation and restart commands,
see [`DEVELOPMENT_ENVIRONMENT.md`](DEVELOPMENT_ENVIRONMENT.md).
The product/marketing website is maintained outside this integration repository.
Cross-repo sync prompts are consolidated into this repo's `SYNC_PROMPTS.md`; do not re-add old loose prompt files or sibling-repo copies. The product roadmap is centralized in this repo's `PRODUCT_ROADMAP.md`; do not keep sibling-repo roadmap copies. Keep `TECHNICAL_DESIGN_DECISIONS.md` updated when implementation patterns, coding conventions, dependencies, libraries or external API usage change.

## Licensing And Commercial Use

Copyright (c) 2026 Peter van Tol.

- The DJConnect Home Assistant integration is free software under the MIT License. You may use, copy, modify, publish, distribute, sublicense, and sell the integration under the terms in `LICENSE`.
- DJConnect client and firmware repositories are also MIT-licensed unless their own repository files state otherwise.
- DJConnect hardware can be sourced, white-labeled, sold, and resold separately from this integration, subject to any hardware supplier agreements.
- The Home Assistant integration may be bundled, linked, or recommended with DJConnect devices and clients.
- Spotify is a trademark of Spotify AB. DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.
- This integration may depend on open-source Python/Home Assistant components. Their licenses remain with their respective authors. See `THIRD_PARTY_NOTICES.md`.

## Install Through HACS

Before installing, make sure you have:

- Home Assistant with HACS installed.
- A Spotify Premium account.
- A configured Home Assistant Assist pipeline with working STT and TTS. The
  DJConnect setup flow blocks pairing until at least one Assist pipeline has
  both providers configured.
- A DJConnect ESP device, DJConnect iOS/macOS/watchOS app or Raspberry Pi client on the same local network as Home Assistant during pairing.
- For ESP devices: 2.4 GHz WiFi.
- For Spotify OAuth: an external HTTPS Home Assistant URL, preferably Nabu Casa.

1. Open HACS in Home Assistant.
2. Add `https://github.com/pcvantol/djconnect` as a custom repository.
3. Select category `Integration`.
4. Install DJConnect.
5. Restart Home Assistant.
6. Make sure Spotify can be authorized from Home Assistant through the DJConnect
   Spotify OAuth step.
7. Go to **Settings -> Devices & services -> Add integration -> DJConnect**.

HACS deeplink:

```text
https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration
```

## Spotify Developer App

DJConnect uses PKCE with a Spotify Developer app that you create yourself. A
Client Secret is not required, but the Spotify Client ID is required in the
DJConnect config flow.

Spotify Premium is required because DJConnect asks Home Assistant to control Spotify playback devices through Spotify's playback APIs. Spotify OAuth credentials remain in Home Assistant; DJConnect devices and apps never receive the Spotify refresh token or playback credentials.

DJConnect requests these Spotify OAuth scopes:

- `user-read-playback-state`
- `user-modify-playback-state`
- `user-read-currently-playing`
- `user-library-read`
- `user-library-modify`
- `playlist-read-private`
- `playlist-read-collaborative`
- `playlist-modify-private`
- `playlist-modify-public`
- `user-read-recently-played`
- `user-top-read`

`playlist-read-private` is required when Home Assistant lists private or
user-owned playlists for DJConnect backend playback. `playlist-modify-private`
and `playlist-modify-public` are required when Ask DJ saves a generated mix as a
Spotify playlist. `user-library-modify` is required when Ask DJ adds the current
track to the user's Spotify Liked Songs/favorites. `user-read-recently-played`
is required for recent listening-history questions and listening-profile
analysis. `user-top-read` is required for profile analysis based on top
artists/tracks. Existing users who authorized Spotify before these scopes were
added must authorize Spotify again.

Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), copy its Client ID, and add the exact redirect URI shown by the DJConnect setup flow. With Nabu Casa this usually looks like:

```text
https://<your-nabu-casa-id>.ui.nabu.casa/api/djconnect/spotify/callback
```

For local-only development you can use a reachable Home Assistant external URL instead:

```text
http://homeassistant.local:8123/api/djconnect/spotify/callback
```

The redirect URI in Spotify must exactly match the Home Assistant external URL plus `/api/djconnect/spotify/callback`. Nabu Casa is strongly recommended because it provides a stable HTTPS callback URL. If your Home Assistant external URL changes, update the redirect URI in the Spotify Developer Dashboard and reauthorize DJConnect.

## Add DJConnect In Home Assistant

DJConnect checks for an Assist pipeline with both STT and TTS when you start
setup. Spotify playback itself is authorized through DJConnect's Spotify OAuth
step and handled through Spotify's Web API, not through a Home Assistant
Spotify media player entity.

1. Choose whether the DJConnect device is already on WiFi or needs BLE WiFi provisioning.
2. If needed, choose one BLE action: write WiFi over Bluetooth, rescan Bluetooth devices, or continue directly to pairing when WiFi was already configured through the device captive portal.
3. After BLE success or captive-portal WiFi setup, wait for the device to restart and show a pairing code.
4. Enter the pairing code shown on the DJConnect device display. This can be the short 6 digit setup code or the 12-character device suffix, for example `90B70990A994`.
5. Confirm the HTTPS Home Assistant external URL. DJConnect prefills this from Home Assistant's Network external URL when available and falls back to the Nabu Casa/Home Assistant Cloud remote UI URL.
6. Copy the shown redirect URI into your Spotify Developer app and enter that app's Spotify Client ID.
7. Home Assistant opens the Spotify authorization website.
8. Approve access in Spotify.
9. Return to Home Assistant and complete the voice/DJ settings step.

The setup flow no longer shows a manual `oauth_result` field.

BLE WiFi provisioning only writes WiFi credentials to the setup-mode device. It
writes JSON with `ssid` and `password` keys only; `ssid` is required and
`password` may be empty for open networks. The JSON may be fragmented across
multiple BLE writes and does not send Spotify credentials, device tokens or
other secrets over BLE.

## Voice And DJ Settings

The config flow includes safe defaults for optional voice fields. The Assist pipeline is stored so DJConnect knows which Home Assistant STT/TTS setup to use; DJConnect does not run direct external STT/TTS APIs.

- Assist pipeline ID
- Mood-aware DJ announcements: runtime mood from iOS, macOS or Apple Watch automatically adapts the spoken announcement tone; without mood DJConnect uses its hardcoded default style
- ESP device UI language is selected automatically from the Home Assistant language during ESP pairing. iOS, macOS, watchOS, Raspberry Pi and Windows clients determine their own language locally.
- ESP32 firmware updates through the public multi-device manifest and selected firmware channel

Where Home Assistant exposes choices, DJConnect shows populated dropdowns for Assist pipeline. The first setup step chooses one route: Assist Conversation Agent, DJConnect app/device pairing, or WiFi provisioning over Bluetooth. The pairing step does not repeat that setup method choice; it asks for the client details only. Client type choices are ordered for app clients first: iOS, macOS, Apple Watch, Linux/Raspberry Pi, Windows and ESP32. STT/TTS engine, language and voice are managed in Home Assistant Assist, not in DJConnect. Backend playback is handled by Home Assistant through DJConnect commands plus Spotify-backed control/status entities; ESP device settings use the local device command API. The compact options screen used from Assist conversation-agent settings shows only the action selector and smart-home context allowlist; DJ announcement style is no longer a config/option choice because runtime mood drives the final tone when available. Device-only setup fields such as Client adres, Assist pipeline, firmware channel, playlist overrides, Spotify source overrides and OTA/audio compatibility fields are hidden there. Max audio bytes, OTA battery settings and DJ announcement audio TTL use integration defaults and are not user-adjustable in config/options flow. Firmware OTA device selection is ESP32-only and automatic: DJConnect reads the public multi-device firmware manifest and selects the matching `firmwares[]` entry from ESP status/info, falling back to LilyGO only before the ESP has reported a model. iOS/macOS/watchOS clients update through TestFlight/app distribution, and Linux/Raspberry Pi and Windows clients are managed from their own GitHub source/install flow rather than ESP OTA. For ESP devices, the Client adres is normally not needed: DJConnect resolves the device through `_djconnect._tcp` mDNS, uses the device-reported `local_url` when available, and only builds a model-specific hostname such as `http://djconnect-lilygo-t-embed-s3-[device-suffix].local` when the configured ID contains a real 12-character device suffix.

The options flow also includes an action selector. Use `Reauthorize Spotify` to
refresh OAuth from the integration page, `Retry pairing with current code` to
push a fresh device token to the existing ESP, or `Re-pair with new pairing
code` when the ESP shows a new code.


## Security And Diagnostics

- Pairing is unauthenticated by design, but requires the pairing code or 12-character device suffix shown on the DJConnect device.
- After pairing, device endpoints use the per-device bearer token.
- Pairing/status metadata must include `client_type`; ESP firmware sends `esp32`, Apple app clients send `ios`, `macos` or `watchos`, Raspberry Pi clients send `raspberry_pi`, and Windows clients send `windows`. App/client device IDs use `djconnect-ios-XXXXXXXXXXXX`, `djconnect-macos-XXXXXXXXXXXX`, `djconnect-watchos-XXXXXXXXXXXX`, `djconnect-raspberry-pi-XXXXXXXXXXXX` or `djconnect-windows-XXXXXXXXXXXX`, where the suffix is the first 12 alphanumeric characters of the stable install ID.
- Home Assistant keeps pairing status `pending` until the ESP confirms `ha_pairing_status=paired`; a local token alone is not treated as confirmed pairing.
- Home Assistant calls `POST /api/device/pair` only during initial pairing, explicit re-pair/token rotation, or stale-pairing recovery. Normal status, playback and settings updates never trigger a new direct pair callback.
- BLE WiFi provisioning sends only SSID/password to the BLE WiFi characteristic; it does not send Spotify credentials, device tokens or other secrets.
- Diagnostics redact keys containing `token`, `password` or `secret`.
- Logs avoid full event payloads and do not intentionally log Spotify refresh tokens, WiFi passwords or device tokens.
- The Spotify Client ID is not a secret; PKCE is used and no client secret is required. Each user should use their own Spotify Developer app so their exact Home Assistant callback URL can be registered in Spotify.

## Home Assistant Entities

DJConnect creates backend/playback entities for all client types:

- `sensor.djconnect_status`
- `sensor.djconnect_last_command`
- `sensor.djconnect_firmware_version`
- `sensor.djconnect_last_track`
- `sensor.djconnect_queue`
- `sensor.djconnect_playlists`
- `sensor.djconnect_outputs`
- `sensor.djconnect_sound_output`
- `sensor.djconnect_playback_available`
- `sensor.djconnect_spotify_status`
- `sensor.djconnect_ha_pairing_status`
- `select.djconnect_sound_output`
- `button.djconnect_test_dj_voice`
- `button.djconnect_refresh_up_next`
- `button.djconnect_refresh_device_info`

ESP32 clients additionally get ESP-hardware entities:

- `sensor.djconnect_battery`
- `sensor.djconnect_wifi_rssi`
- `sensor.djconnect_screen_state`
- `sensor.djconnect_led_state`
- `number.djconnect_brightness`
- `number.djconnect_screen_timeout`
- `number.djconnect_speaker_volume`
- `switch.djconnect_wake_word`
- ESP device setting selects such as language, auto-off, theme and log level
- `update.djconnect_firmware`
- `button.djconnect_reboot_device`

iOS, macOS, watchOS, Raspberry Pi and Windows clients do not get ESP-only battery, Wi-Fi RSSI,
screen/LED, screen brightness/timeout, speaker volume, device language,
auto-off, theme/log-level, wake word, OTA or reboot entities.

Entity IDs can differ if Home Assistant has renamed the device or entities.

Use `button.djconnect_test_dj_voice` after setup to test the configured HA TTS
engine, voice and language with a short DJ announcement on the DJConnect device
speaker/display. This does not use Spotify Connect or a Home Assistant media
player for DJ announcement audio.

Use `button.djconnect_refresh_up_next` to refresh the backend queue/up-next list
from Spotify/Home Assistant. Use `button.djconnect_refresh_device_info` for the
local ESP device info/status refresh. The sound-output select also refreshes
Spotify output devices when Home Assistant updates the entity, so available
outputs do not depend on a prior manual `devices` command.

## Services

DJConnect registers these services:

- `djconnect.test_parse`
- `djconnect.test_tts`
- `djconnect.test_command`
- `djconnect.test_ptt_text`
- `djconnect.ask_dj`
- `djconnect.clear_ask_dj_history`
- `djconnect.ask_dj_history_state`
- `djconnect.start_spotify_oauth`

Spotify OAuth credentials stay in Home Assistant. They are never provisioned to the ESP device; the old ESP `/api/device/provision_spotify` endpoint is no longer used.

`djconnect.test_parse` and `djconnect.test_command` use this flow:

```text
text -> HA Assist conversation pipeline -> DJConnect intent -> Spotify -> ESP DJ announcement
```

`djconnect.test_command` accepts `command_text` and optional `play`. The legacy `text` key is still accepted for existing YAML/scripts. With `play: false`, it uses the same command parser path without starting Spotify playback.
`djconnect.test_parse` also accepts `command_text`; `djconnect.test_tts` accepts `dj_response_text` and keeps legacy `text` as a compatibility alias.
`djconnect.test_ptt_text` starts exactly after STT conversion: enter the
recognized natural-language sentence and DJConnect first runs the same guarded
Assist fuzzy-correction step used by physical PTT, then Spotify intent parsing,
Spotify search/playback, DJ announcement generation, TTS audio creation and
delivery back to the connected DJConnect device/client.

`djconnect.ask_dj` is the backend text entrypoint for developer tools. App
clients use `POST /api/djconnect/ask_dj/message` so the server can store both
the user message and assistant answer in the user-scoped Ask DJ history.
Requests accept `text`, optional `client_message_id`, `client_id`, `mood`,
`dj_style`, `audio_response`, `client_type`, `device_id` and `device_name`, then route as
informational, playback/device action or hybrid. Informational questions do not
change playback; action and hybrid requests can call Spotify/Home Assistant
backend actions and still return a natural DJ answer. Responses include
`user_message`, `assistant_message`, canonical `messages[]` in render order,
`history_revision`, `clear_revision` and the same rich fields as the Ask DJ
answer: `success`, `text`/`dj_text`/`message`, optional `audio_url`, `images[]`,
`links[]`, `sources[]`, `playback_actions[]`, `intent` and `action`. Current
servers add shared `exchange_id` plus `exchange_order` (`0` for the user
question, `1` for the assistant answer), so clients can keep the question above
the answer during HTTP/push/history timing races.
The informational intent `personal_music_profile_analysis` answers questions
such as "Omschrijf eens waar ik zoal naar luisterde de afgelopen maand" or
"Make a profile of my music taste this year". It never starts, pauses, queues,
skips, likes or moves playback. It uses only available DJ Memory/playback
context, defaults to the last 30 days when no period is named, and says clearly
when there is too little listening history for a reliable profile.
Privacy-oriented questions such as "Wat weet je nu over mij?" use the narrower
`personal_memory_summary` intent instead. That response is based on server-side
DJ Memory only, with `sources:[{"source":"djconnect_memory"}]`, no `images[]`
and no `playback_actions[]`.
Ask DJ also supports read-only technical track analysis prompts such as
"Analyseer dit nummer". Those return `intent.intent:"technical_track_analysis"`,
`action:"track_analysis"`, Spotify playback/audio-analysis sources when
available, and no playback mutation. The provider-neutral v2 contract adds
client-ready `analysis.sections[]`, `analysis.timeline[]` and
`analysis.dj_tips[]` next to the original measured/inferred/limitations data, so
apps can render rhythm, energy, build-up, instrumentation, musical
interpretation, caveats and DJ usage advice without parsing prose. v2 remains
local-first: it works without a DJConnect central backend by combining current
playback metadata, Home Assistant conversation context where available, and
measured provider data only when the user's own installation can access it.
DJConnect can also enrich the analysis with free online MusicBrainz and
ListenBrainz metadata/context, using compact per-runtime caching and rate-limit
protection. That metadata can add release, genre/tag and public ListenBrainz
context, but it is not waveform/stem/BPM analysis and is always labelled with
limitations. `analysis.providers[]` reports the provider plug-in status for
Spotify measured analysis, MetaBrainz metadata, HA Conversation inference and
local fallback without exposing secrets, raw audio or provider-private payloads.
Use
[`examples/ask_dj_track_analysis_v2_response.json`](examples/ask_dj_track_analysis_v2_response.json)
and
[`examples/ask_dj_track_analysis_v2_unavailable.json`](examples/ask_dj_track_analysis_v2_unavailable.json)
as client golden fixtures.
`djconnect.clear_ask_dj_history` clears persistent Ask DJ chat history for the
selected Home Assistant user when called as a developer service. The app HTTP
clear route uses the same HA-user scoped history store and increments
`clear_revision` as the authoritative full-clear marker for that user/context.
`djconnect.ask_dj_history_state` returns the current revisions and
`ask_dj_clear_required` so another client can clear its local cache before
rendering the Ask DJ screen.

If command processing or Spotify playback fails, DJConnect still sends a
friendly DJ announcement to the ESP device when possible, so the user hears or sees
what went wrong instead of only receiving an HTTP error. This fallback text uses
the ESP32 language provisioned during pairing, or the client/default language
for app-like clients, and distinguishes Assist pipeline failures from Spotify
playback failures.
When HA Assist provides a DJ announcement, DJConnect asks it to include one
short fun fact about the artist and/or the song. After Spotify resolves and
starts the request, DJConnect prefers the resolved track, artist, album or
playlist metadata plus the current mood-zone/default announcement style to
generate the spoken device response, so the device response is specific to what
actually started playing.

If HA Assist returns a generic smart-home answer such as "I cannot play music",
DJConnect does not use that sentence as the DJ announcement. It keeps the
Spotify search intent based on the original command and falls back to the
DJConnect DJ announcement text unless Assist returns explicit `djconnect` data.
Plain voice/search commands such as "ik wil Pearl Jam starten" are resolved
through Spotify Search before playback starts. Generic spoken music requests
remain artist-first, so "speel Nirvana" starts the artist context instead of
picking an arbitrary track. Explicit media words select a more specific Spotify
Search type. Current-track questions and direct playback-control phrases are
handled by Home Assistant before Spotify search and do not require Spotify
credentials or playback-backend logic in DJConnect clients:

- Current track: "Welk nummer draait er nu?", "Welk nummer speelt er nu?", "Wat draait er?", "Wat speelt er?", "What song is playing?", "What's playing?".
- Playback control: "Stop muziek", "Start muziek", "Zet harder", "Zet zachter", "Volgende nummer", "Vorig nummer", "Stop music", "Start music", "Turn it up", "Turn it down", "Next song", "Previous song".
- Current track favorite toggle: "zet huidig nummer in favorieten", "haal huidig nummer uit favorieten", "voeg dit nummer toe aan favorieten", "save this track to liked songs", "remove this track from liked songs". Current-track Ask DJ responses can also include a `command:"set_current_track_favorite"` control action with `toggle:true`, `toggle_state`, `favorite_status`, boolean `value` and `client_prompt` (`Zet huidig nummer in favorieten` or `Haal huidig nummer uit favorieten`); Now Playing clients may send the same command directly to `/api/djconnect/command`.
- Artist: "ik heb zin in Pearl Jam", "ik wil Metallica horen", "Nirvana wil ik wel horen", "artiest Nirvana", "band Pearl Jam", "speel maar af Above & Beyond", "I feel like Fleetwood Mac".
- Track: "speel nummer Black van Pearl Jam", "speel nummer Lithium van artiest Nirvana", "speel artiest Nirvana met nummer Lithium", "nummer Lithium", "start het liedje Everlong", "zet track Nothing Else Matters van Metallica op", "play song Paranoid Android by Radiohead".
- Album: "speel album Ten van Pearl Jam", "album Nevermind", "start het album Nevermind", "zet de plaat OK Computer van Radiohead op", "play album In Rainbows by Radiohead".
- Playlist: "speel playlist Roadtrip", "start mijn playlist Rustig wakker worden", "zet afspeellijst Dinner Jazz op", "play playlist Workout".
- Default playlist: "speel standaard playlist", "start mijn favorieten", "zet liked songs op", "play default playlist".

If Spotify reports that no active playback device exists for an Ask DJ playback
intent, DJConnect refreshes available Spotify speakers and returns a follow-up
choice list instead of a dead-end playback failure. The response uses
`error:"no_active_output"`, `action:"select_output"` and `playback_actions[]`
with `kind:"output"` plus `command:"ask_dj_play_request_on_output"`. Clients
post the chosen action value back unchanged; Home Assistant sets that output and
replays the original Ask DJ playback request server-side.

Developer action overview:

- `djconnect.test_parse`: test only the HA Assist conversation parser and return the DJConnect intent; no playback and no DJ announcement delivery.
- `djconnect.test_tts`: send a DJ announcement text to the DJConnect device; Home Assistant tries to generate a temporary WAV or MP3 URL, otherwise the ESP shows text only.
- `djconnect.test_command`: test the complete ESP text-command route with `command_text` and `play`; set `play: false` to avoid starting Spotify playback while still sending the DJ announcement.
- `djconnect.test_ptt_text`: test the real PTT flow immediately after STT by entering recognized text; it always attempts Spotify playback and sends the generated DJ announcement text/audio to the connected device.
- `djconnect.test_apns_push`: inspect APNs readiness for an iOS, macOS or Apple Watch client. By default this is a dry-run diagnostic; set `send: true` to attempt a privacy-safe test push through the central relay.
- `djconnect.start_spotify_oauth`: generate a Spotify PKCE authorization URL for manual reauthorization/debugging.

Developer actions return response data where Home Assistant supports it. Enable
debug logging for `custom_components.djconnect` when you want to inspect the
selected Assist/STT/TTS route metadata, OAuth redirect URI, DJ announcement result, or
command-processing result. Spotify refresh tokens and device tokens are not
logged. DJConnect registers explicit runtime service schemas for these actions
so Home Assistant Developer Tools keeps the text input fields visible after
service metadata refreshes.
For PTT/voice debugging, inspect the attributes on `sensor.djconnect_status` or
`sensor.djconnect_last_command`, or pin `sensor.djconnect_last_corrected_stt`
directly: `last_stt_text` shows the text recognized by STT, `last_corrected_text`
shows the corrected command text when the guarded Assist correction step changed
it, `last_spotify_search` shows the Spotify Search query/type, selected result
and a small candidate list, and `last_resolved_media` shows the media metadata
used for the spoken DJ announcement.

Example developer action data:

```yaml
action: djconnect.test_command
data:
  command_text: "Stop muziek"
  play: false
```

Example post-STT PTT flow test:

```yaml
action: djconnect.test_ptt_text
data:
  command_text: "Wat speelt er?"
```

Example APNs dry-run diagnostic:

```yaml
action: djconnect.test_apns_push
data:
  client_type: macos
  send: false
```

Example APNs relay test:

```yaml
action: djconnect.test_apns_push
data:
  client_type: macos
  event_type: ask_dj_confirm
  send: true
```

The APNs diagnostic response is privacy-safe. It reports booleans such as
`central_api_configured`, `install_token_present`, `bootstrap_proof_present`,
the push-policy `decision`, known `push_statuses`, `sent` and `error`, but never
returns APNs tokens, bearer tokens, `bootstrap_proof` values or `djci_` install
tokens. Common `error` values are `missing_bootstrap_proof`,
`missing_install_token`, `push_relay_unavailable`, `rate_limited`,
`client_recently_active` and `event_not_pushable`.

Example DJ announcement test:

```yaml
action: djconnect.test_tts
data:
  dj_response_text: "Here we go. DJConnect is paired, the voice works, and I am ready for your next track."
```

DJ announcement audio flow:

```text
dj_text -> HA TTS backend -> temporary WAV/MP3 URL -> POST /api/device/dj_response -> ESP speaker/display
```

DJ announcement failure handling:

| Failure | ESP/user feedback |
| --- | --- |
| HA Assist pipeline cannot process the command | Localized DJ announcement asks the user to check the selected Assist pipeline. |
| Spotify playback cannot start | Localized DJ announcement asks the user to check Spotify playback device availability. |
| HA TTS cannot generate WAV or MP3 | ESP receives text-only DJ announcement without `audio_url`. |
| HA can generate WAV/MP3 but no local HA URL can be resolved | ESP receives text-only DJ announcement without `audio_url`; check Home Assistant internal/network URL settings. |
| HA TTS returns unknown audio | ESP receives text-only DJ announcement without `audio_url`; this is logged only as a debug fallback. |
| ESP `/api/device/dj_response` fails | Voice command returns a controlled `command_failed` JSON response and keeps the original Assist/Spotify error in runtime state. |
| Temporary audio URL is unknown or expired | `GET /api/djconnect/tts/{token}.wav` or `.mp3` returns `404` or `410`; trigger the DJ announcement again. |

Home Assistant posts this payload to the paired DJConnect device:

```json
{
  "text": "Here we go.",
  "audio_url": "http://homeassistant.local:8123/api/djconnect/tts/<token>.mp3"
}
```

`audio_url` is optional. If HA TTS cannot produce WAV or MP3 audio, DJConnect
sends only `text` and the ESP displays the response without speech. When HA TTS
does produce WAV or MP3 audio, DJConnect builds the temporary URL from the local
Home Assistant URL resolver so the device can fetch it over the LAN. The ESP
decides whether the temporary URL is WAV, MP3 or unknown based on content type
and/or file header. DJConnect does not send Opus or M4A URLs.

During pairing, DJConnect sends only non-secret client settings, such as
`device_token`, `ha_local_url`, `assist_pipeline_id` and `client_type`.
For ESP32 clients only, Home Assistant also sends `device_language` and
`language`; iOS, macOS, watchOS, Raspberry Pi and Windows clients always determine their own UI
language locally. `client_type` identifies the paired DJConnect client runtime;
current values are `esp32`, `ios`, `macos`, `watchos`, `raspberry_pi` and `windows`, with `esp32` as
the default for ESP firmware. Device-to-Home Assistant traffic
always uses `ha_local_url`; cloud/Nabu Casa URLs are not sent to devices and
are only used by the Spotify OAuth config/repair flow. Spotify OAuth
credentials stay in Home Assistant and are used only by the HA playback backend.
Pair/status payloads must not contain `ha_url`, `refresh_token`,
`ha_remote_url`, `spotify_refresh_token`, `client_id` or a `spotify` OAuth object.
`ha_local_url` is resolved from Home Assistant's internal/network URL or LAN
source IP and must never be a `*.ui.nabu.casa` URL. When Home Assistant reports
`homeassistant.local` but a LAN source IP is available, DJConnect sends the LAN
IP URL instead. If no LAN URL can be discovered, `http://homeassistant.local:8123`
is the final local fallback.

`/api/djconnect/status`, `/api/djconnect/command` and `/api/djconnect/voice`
may include optional Ask DJ memory hints: `mood` as an integer `0`-`100`,
`dj_style` as a short string and `memory_key` as a client-suggested key.
Home Assistant may normalize or override `memory_key`; responses can include the
resolved `memory_key`. Clients should treat DJ Memory as server-side state and
must not store Spotify credentials, Home Assistant tokens or DJ Memory locally.
Apple Watch, iOS and backend callers all use the same server-side mood-zone
mapping when a numeric mood is provided: `0`-`24` is `Chill`, `25`-`59` is
`Groove`, `60`-`84` is `Energy` and `85`-`100` is `Party`. Clients can keep
sending only the numeric `mood`; DJConnect derives `mood_zone` internally and
uses the zone name plus persona hint in Ask DJ prompts, recommendations, spoken
DJ announcements and debug/status context. Missing or unknown mood values keep
the existing default Ask DJ and announcement behavior.

| Numeric mood | Zone | Ask DJ persona hint |
| --- | --- | --- |
| `0`-`24` | Chill | Quiet, warm, low tempo and not too busy. |
| `25`-`59` | Groove | Flowing, rhythmic, social and medium energy. |
| `60`-`84` | Energy | More drive, uptempo and active. |
| `85`-`100` | Party | Maximum energy, festive, recognizable and momentum-focused. |

Spotify refresh tokens can rotate after OAuth. DJConnect stores newly returned refresh tokens immediately and treats that latest stored value as canonical for HA backend playback. If Spotify rejects an older in-memory refresh token, DJConnect checks the latest runtime/config-entry/config sources and retries a newer stored token before showing a reauthorization Repair. If the ESP later reports `spotify_configured=false`, Home Assistant treats this as a compatibility/status hint, not as a request to send OAuth credentials to the ESP.

Spotify access tokens are short-lived and normally expire after about an hour. DJConnect caches the access token in Home Assistant until shortly before expiry, refreshes it on demand, and retries once if Spotify returns an API `401` for an expired access token. A Home Assistant Repair issue should only appear when Spotify rejects every known refresh token itself, for example `invalid_grant` or `Refresh token revoked`. Debug logging records expiry timing, refresh attempts and token source names only; it never logs refresh-token values.

Provisioning fields sent to the ESP can include:

```json
{
  "device_token": "<per-device-token>",
  "ha_local_url": "http://192.168.1.x:8123",
  "assist_pipeline_id": "...",
  "client_type": "esp32",
  "device_language": "nl",
  "language": "nl",
  "backend_available": true
}
```

`ha_local_url` must be present. ESP32 firmware should prefer `device_language`
over `language` and store it as `provision.language`. App-like clients should
ignore HA language provisioning because their language is client-owned.

## Home Assistant HTTP Endpoints

The integration exposes these endpoints:

```text
POST /api/djconnect/pair
POST /api/djconnect/voice
POST /api/djconnect/ask_dj
POST /api/djconnect/ask_dj/message
GET  /api/djconnect/ask_dj/history
POST /api/djconnect/ask_dj/history/clear
POST /api/djconnect/push/register
POST /api/djconnect/push/unregister
POST /api/djconnect/command
POST /api/djconnect/status
POST /api/djconnect/event
GET  /api/djconnect/tts/{token}.wav
GET  /api/djconnect/image_proxy/{token}
GET  /api/djconnect/spotify/callback
```

See `API_CONTRACT.md` for the compact client-facing Ask DJ contract, including
mood-zone mapping, history retention, Apple push registration and smart-home
context rules.

A Postman collection for these HTTP endpoints lives at
[`examples/djconnect.postman_collection.json`](examples/djconnect.postman_collection.json).
Keep it aligned with endpoint, auth header, payload and response-shape changes.

The ESP should send status updates to:

```text
POST /api/djconnect/status
```

Authenticated device requests use the provisioned bearer token and can include `X-DJConnect-Device-ID`.
Status and pairing payloads use canonical `client_type` metadata so Home
Assistant can distinguish ESP32 devices from iOS/macOS/watchOS app clients, Raspberry Pi clients and Windows clients.
ESP JSON payloads must include `client_type`.

BLE setup-mode devices are matched by service UUID:

```text
7f705000-9f8f-4f1a-9b5f-570071fd0001
```

WiFi credentials are written as UTF-8 JSON to characteristic
`7f705001-9f8f-4f1a-9b5f-570071fd0001`; status is read from
`7f705002-9f8f-4f1a-9b5f-570071fd0001`. The write payload is
`{"ssid":"MyWiFi","password":"wifi-password"}` and may be split over multiple
BLE writes for firmware-side reassembly.

The voice endpoint accepts raw WAV audio from paired ESP32, iOS, macOS and
watchOS clients:

```text
POST /api/djconnect/voice
POST /api/djconnect/command
Authorization: Bearer <device_token>
Header: X-DJConnect-Device-ID: djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX
Content-Type: audio/wav
```

The integration runs HA Assist/STT internally, processes the recognized text,
starts Spotify playback, creates a DJ announcement, and returns text plus an
optional temporary WAV/MP3 `audio_url`:

```json
{
  "success": true,
  "text": "Daar gaan we...",
  "dj_text": "Daar gaan we...",
  "audio_url": "http://homeassistant.local:8123/api/djconnect/tts/token.mp3",
  "audio_type": "mp3"
}
```

JSON/text-only requests remain supported for ESP web tests and diagnostics
through `X-DJConnect-Text` or `{ "text": "Test" }`. They simulate the DJ
response path directly and do not parse a Spotify playback command. Raw WAV PTT
uploads continue through STT, command parsing, Spotify playback and DJ announcement.

For app-like clients with voice support (`ios`, `macos`, `watchos`, `windows`), raw WAV
uploads to `/api/djconnect/voice` are treated as Ask DJ voice input after STT.
Raspberry Pi Ask DJ is text-only unless a future Pi capability explicitly
advertises voice support. Optional headers `X-DJConnect-Mood`, `X-DJConnect-DJ-Style` and
`X-DJConnect-Memory-Key` are folded into the same Ask DJ memory/context path as
text chat. The response keeps the Ask DJ rich shape and includes both
`transcript` and legacy `recognized_text` so clients can show the actual
recognized user text. STT failures for app Ask DJ voice return a clear
`stt_failed` error with HTTP `422`. Raw audio is not stored by default; debug WAV
retention is opt-in through debug logging and temporary.

Status/pairing responses advertise:

```json
{
  "ask_dj_supported": true,
  "ask_dj_voice_supported": true,
  "voice_supported": true,
  "ask_dj_audio_response_supported": true,
  "push_supported": true,
  "push_registered": false,
  "push_environment": "sandbox"
}
```

Apple push notifications are optional and best-effort for iOS, macOS and
watchOS clients. Clients register APNs tokens with
`POST /api/djconnect/push/register` and unregister with
`POST /api/djconnect/push/unregister`, both using the existing DJConnect bearer
token. Home Assistant does not store APNs tokens and never needs the platform
`.p8` key. It forwards registrations and wake/sync events to the central
`djconnect-api` push relay through `https://api.djconnect.dev` using a secret
per-install token that starts with `djci_`. Home Assistant requests this token
automatically from `/v1/install/token` with its generated `ha_install_id` plus a
short-lived pairing/bootstrap proof supplied by an Apple push client (`ios`,
`macos` or `watchos`), then stores the returned token in the config entry.
HACS never
contains a global relay secret and does not mint install tokens without a proof.
Users do not need to see, copy or enter this token. If no proof is available yet
or the central API is temporarily unavailable, push stays disabled without
breaking Ask DJ, playback or status flows and the integration retries on the
next central API use after a fresh proof is supplied. ESP32, Raspberry Pi, Windows and
Assist-agent-only entries do not need this proof because they do not use APNs
push.

The central `djconnect-api` service owns APNs provider-token auth, topics,
sandbox/production selection and invalid-token handling. Push is only a
wake/attention signal: when the user opens the app, the client must still sync
through authenticated APIs, especially `GET /api/djconnect/ask_dj/history`.
Token rotation uses the central `/v1/install/rotate` endpoint and only replaces
the local token after a successful response.
Push is sent only for user-visible Ask DJ attention events: an explicit user Ask
DJ response, or an Ask DJ response that contains `confirmation_actions` and is
waiting for a choice. DJConnect does not push for track changes, playback
changes, queue changes, volume changes, mood changes, idle suggestions, ambient
system messages, status refreshes or Spotify progress updates. If the source
client reports foreground/recent-active state, HA suppresses pushes back to that
active client. HA also rate-limits Ask DJ pushes per user/device to one push per
30 seconds and five pushes per ten minutes. Central API event payloads contain
only `ha_install_id`, optional `ha_user_hash`, `event_type`, `history_revision`,
optional `client_message_id`, optional `open_target` and optional
`client_types`. They never include Spotify tokens, Home Assistant tokens, raw
prompts, raw LLM context, full memory/history or assistant responses. The
`djci_` install token is internal and must never be pasted into issues or logs.

APNs troubleshooting:

- `sensor.djconnect_apns_registration` shows `registered`, `unregistered`,
  `disabled`, `error`, `unsupported` or `not_applicable`. Its attributes include
  `central_api_configured`, `registered_count`, `push_environment`,
  `last_push_error` and privacy-safe per-client registration summaries.
- `disabled` means HA does not currently have a valid per-install central relay
  token. Normal Ask DJ, status and playback flows should still work.
- `error` with `last_push_error: missing_bootstrap_proof` means HA has not yet
  received a fresh Apple-client bootstrap proof that can mint a `djci_` install
  token.
- `error` with `last_push_error: missing_install_token` means token minting did
  not return a valid install token.
- `error` with `last_push_error: push_relay_unavailable` means the central relay
  request failed temporarily.
- Use Developer Tools -> Actions -> `djconnect.test_apns_push` for detailed
  diagnostics. Leave `send` off for a dry-run, or set `send: true` to attempt a
  real test push. The response intentionally exposes only flags and redacted
  status, never APNs tokens, bearer tokens, bootstrap proofs or `djci_` tokens.

App/display clients should use `POST /api/djconnect/ask_dj/message` for text
chat. This contract applies to iOS, macOS, Apple Watch, Raspberry Pi and Windows. ESP32
does not get Ask DJ chat/history; ESP32 keeps the existing PTT/playback command
flow. The backend is the source of truth for Ask DJ history per Home Assistant user; iOS,
macOS, Apple Watch and Raspberry Pi may cache locally, but must reconcile from
`GET /api/djconnect/ask_dj/history?since_revision=<number>`. The request body
can contain top-level identity fields or an `identity` object:

```json
{
  "client_message_id": "uuid-from-client",
  "client_id": "watch_peter",
  "identity": {
    "client_type": "watchos",
    "device_id": "djconnect-watchos-8F3A2C91B45D",
    "device_name": "Apple Watch van Peter"
  },
  "text": "Waarom koos je dit nummer?",
  "memory_key": "optional-client-key",
  "mood": 42,
  "mood_zone": "groove",
  "dj_style": "warm_radio_dj",
  "audio_response": "auto"
}
```

`mood_zone` in examples is informational; clients may omit it. The backend
derives the canonical lowercase zone from `mood` so older clients remain
compatible.

The response is uniform across iOS, macOS, Apple Watch, Raspberry Pi and Windows:

```json
{
  "success": true,
  "history_revision": 43,
  "clear_revision": 7,
  "history_limit": 1000,
  "history_trimmed_before": null,
  "history_trimmed_count": 0,
  "user_message": {
    "id": "server-user-message-id",
    "client_message_id": "uuid-from-client",
    "role": "user",
    "text": "Waarom koos je dit nummer?",
    "created_at": "2026-06-19T12:34:56Z",
    "exchange_id": "uuid-from-client",
    "exchange_order": 0
  },
  "assistant_message": {
    "id": "server-assistant-message-id",
    "role": "assistant",
    "text": "Omdat dit mooi aansluit op je rustige stemming.",
    "created_at": "2026-06-19T12:34:57Z",
    "exchange_id": "uuid-from-client",
    "exchange_order": 1,
    "images": [],
    "links": [],
    "sources": [],
    "audio_url": "/api/djconnect/tts/token.mp3",
    "playback_actions": []
  },
  "messages": [
    {
      "id": "server-user-message-id",
      "role": "user",
      "text": "Waarom koos je dit nummer?",
      "exchange_id": "uuid-from-client",
      "exchange_order": 0
    },
    {
      "id": "server-assistant-message-id",
      "role": "assistant",
      "text": "Omdat dit mooi aansluit op je rustige stemming.",
      "exchange_id": "uuid-from-client",
      "exchange_order": 1
    }
  ],
  "text": "Omdat dit mooi aansluit op je rustige stemming.",
  "dj_text": "Omdat dit mooi aansluit op je rustige stemming.",
  "audio_url": "/api/djconnect/tts/token.mp3",
  "images": [
    {
      "url": "/api/djconnect/image_proxy/abc123",
      "thumbnail_url": "/api/djconnect/image_proxy/abc123",
      "title": "Album cover",
      "subtitle": "Artist - Album",
      "kind": "album_art",
      "source": "spotify"
    }
  ],
  "links": [
    {
      "url": "https://musicbrainz.org/...",
      "title": "MusicBrainz",
      "kind": "source",
      "source": "source"
    }
  ],
  "sources": [
    {"source": "spotify_recently_played", "title": "spotify recently played", "kind": "source"},
    {"source": "djconnect_memory", "title": "DJConnect Memory", "kind": "source"}
  ],
  "playback_actions": [
    {
      "id": "spotify:track:123",
      "title": "Track Title",
      "subtitle": "Artist Name",
      "uri": "spotify:track:123",
      "context_uri": "spotify:album:456",
      "offset_uri": "spotify:track:123",
      "kind": "track",
      "image_url": "/api/djconnect/image_proxy/def456",
      "reason": "Past bij je recente voorkeur voor melodische opbouw."
    },
    {
      "id": "ask_dj_followup_yes",
      "title": "Ja",
      "kind": "confirmation",
      "action_style": "confirmation",
      "response_value": "yes",
      "command": "ask_dj_followup_response"
    }
  ],
  "confirmation_actions": [
    {
      "id": "ask_dj_followup_yes",
      "title": "Ja",
      "kind": "confirmation",
      "action_style": "confirmation",
      "response_value": "yes",
      "command": "ask_dj_followup_response"
    },
    {
      "id": "ask_dj_followup_no",
      "title": "Nee",
      "kind": "confirmation",
      "action_style": "confirmation",
      "response_value": "no",
      "command": "ask_dj_followup_response"
    }
  ],
  "intent": {"category": "informational", "name": "ask_music_info"},
  "action": null,
  "memory_key": "user:abc123"
}
```

Before routing a text message, the backend loads recent Ask DJ history for the
same Home Assistant user context and classifies the latest turn as a
conversation follow-up, clarification/correction, informational intent,
playback intent or hybrid intent. Short human replies such as `Geeft niet`,
`Dank je`, `Laat maar`, `Prima` or `Jammer` are answered naturally with
`intent: conversational_followup`, `action: none` and no Spotify/Home Assistant
playback mutation. These replies are text-only in `audio_response: auto`; clients
can still request audio with `audio_response: "always"`. Short corrections such
as `alleen tussen 1980 en 1990` are combined with the previous user request
before the normal Ask DJ routing continues.

Confirmation-style follow-up questions use `playback_actions[]` entries with
`kind:"confirmation"`, `action_style:"confirmation"` and
`command:"ask_dj_followup_response"`; the same entries are also exposed as
`confirmation_actions[]` for clients that want to render them separately from
Play Now cards. Clients answer by sending `/api/djconnect/command` with
`command:"ask_dj_followup_response"` and `value.response_value` as `yes` or
`no`. The backend stores the pending follow-up in DJ Memory for about ten
minutes, scoped to the HA user/memory context. `yes` executes the stored
proposed action, `no` does nothing, and both outcomes append a normal assistant
message to server-side Ask DJ history. Expired follow-ups return a friendly
message asking the user to ask again.

Morning startup is a special confirmation flow. If a client opens Ask DJ in the
morning without active playback, it may send `text:"Goedemorgen"` or
`"Good morning"` plus metadata such as `trigger:"morning_startup"`,
`reason:"app_started_without_active_playback"`, `has_active_now_playing:false`,
`local_date` and `local_hour`. DJConnect answers with a friendly morning
suggestion such as `Goedemorgen! Zal ik ... voor je aanzetten?`, uses DJ Memory
and Spotify listening profile data where available, and does not start playback
until the user taps `Ja`. Sleep phrases such as `ik ga slapen` are treated as a
clear playback-control request and pause music immediately.

Album-discography questions such as `Welke albums hebben Radiohead uitgebracht`
and contextual follow-ups such as `Welke albums bracht deze artiest uit?` use
Spotify artist search plus artist album data when Spotify is configured. The
response keeps playback unchanged, returns `source: spotify_artist_albums`, and
includes proxied album covers in chronological album order where Spotify exposes
artwork. Similar-artist questions such as `Welke artiesten maken vergelijkbare
muziek als wat nu speelt?` resolve the current playback artist or recent
conversation artist and use Spotify related artists when that endpoint is
available for the user's Spotify app. Genre/style questions such as `Wat voor
muziek maakt artiest X?` use Spotify artist profile genre tags and phrase them
as a natural description, for example a mix of one style with a touch of another.
Concert-agenda questions such as `Wanneer speelt artiest X in Nederland?` or
`Heeft deze artiest binnenkort concerten?` are informational and non-mutating.
DJConnect looks up upcoming public web agenda data through Bandsintown when
available and returns a neatly formatted list with date, location and URL; the
same URLs are also returned in `links[]` with `source: bandsintown` so clients
can show them as clickable sources.

Ask DJ also has a few structured utility responses that clients should render
directly from the returned fields:

- `help`, `hulp`, `wat kun je?` and `welke commando's?` return a text-only,
  categorized list of prompt examples.
- `wat weet je nu over mij?`, `wat staat er in mijn DJ Memory?` and similar
  memory-summary questions return a text-only `intent:"personal_memory_summary"`
  answer from DJ Memory only. The backend does not use live Spotify playback,
  does not fetch Spotify profile enrichment and returns no artwork or Play Now
  actions for this intent.
- `welke speakers zijn er?`, `wissel van uitvoer` and similar output requests
  return a text intro plus `playback_actions[]` with `kind:"output"` and
  `Activeer`/`Actief` labels for the available Spotify Connect devices.
- Album list questions return bullets plus `kind:"album"` Play Now actions.
- Recent listening-history questions such as `welke nummers heb ik afgelopen uur afgespeeld?`, `welke albums heb ik vandaag geluisterd?`, `welke artiesten hoorde ik net?` and `welke playlists heb ik afgelopen uur gespeeld?` return `intent:"recently_played_history"` plus `items[]` for `tracks`, `albums`, `artists` or `playlists`.
- `stop muziek` / `pauzeer muziek` pauses playback and can return a
  `kind:"control"`, `command:"play"`, `label:"Resume"` action.
- `hervat muziek` and `start muziek` execute playback immediately.
- `Probeer opnieuw` replays the previous retryable playback request server-side.

Clients must not reuse artwork or metadata from the previous bubble when the new
response is text-only or contains a different action type. For example, a
speaker/output list should never show old album art, and a help response should
not show a music card. Recent listening-history responses should be rendered as
a compact vertical list with the returned art or a local fallback icon, not as
one oversized media card. They are read-only and should not show Play Now
buttons unless `playback_actions[]` is explicitly present.

Runtime mood from Apple clients can shape DJ announcement style. Clients send a
numeric `mood` from `0` to `100`; Home Assistant maps it to `chill`, `groove`,
`energy` or `party` and adds that style context to the generated DJ response.
If no mood is available, DJConnect uses the default announcement style. DJ
announcements may also use compact DJ Memory and explicitly shared smart-home
context for a short personal opening line, such as welcoming the user back or
referencing the daypart. If the user shared weather or temperature entities in
DJConnect options, the intro may mention that context, for example that it is a
warm day and time to swing. DJConnect never uses arbitrary Home Assistant state
for this; only entities listed under `Shared smart-home entities` are included.

DJConnect can also add ambient Ask DJ messages without a user question when the
Spotify backend observes that playback moved to another artist/album
combination. These messages are text-only fun facts in the Ask DJ history with
`intent: ambient_music_fact`, `action: none`, `message_kind: system` and
`origin: spotify_playback_context`; three tracks from the same artist and album
produce at most one message until the artist or album changes. Clients can use
`message_kind` to render these bubbles differently from normal answers to a user
question.

DJConnect can include selected Home Assistant entity state in Ask DJ context for
future smart-home aware prompts such as `het regent buiten`, `het is 20 graden
in de woonkamer`, `de droger is klaar`, `de auto is opgeladen`, `de koffie is
klaar` or `de woonkamer staat op scene Y; wil je nu X horen?`. This is explicit
and read-only: configure `Shared smart-home entities` / `Gedeelde smart-home
entiteiten` in DJConnect options to choose the weather, sensor, appliance, scene
or helper entities DJConnect may see. The integration does not expose all Home
Assistant states to Ask DJ and does not use this context to mutate smart-home
devices; it only summarizes the selected entity states in the Ask DJ prompt. If
Ask DJ proposes music because of a smart-home event, it should use the existing
confirmation-style `playback_actions[]` / `confirmation_actions[]` with Ja/Nee
buttons before starting playback.

Example shared entity list:

```text
sensor.outdoor_rain
sensor.living_room_temperature
sensor.dryer_status
sensor.car_battery
input_select.living_room_scene
```

Only the current state and a small set of safe display attributes are summarized
for Ask DJ. Tokens, full prompts, raw audio and arbitrary HA state snapshots are
not stored in DJ Memory or chat history.

External image URLs are registered behind `GET /api/djconnect/image_proxy/{token}`
so clients only need to fetch Home Assistant/DJConnect URLs. `audio_url` is
also a Home Assistant/DJConnect URL when TTS audio is available.
Ask DJ audio responses are policy-driven through `audio_response`:
`auto`, `always` or `never`. In `auto`, ordinary informational text chat is
text-only for speed, playback/hybrid intents receive TTS when Home Assistant TTS
is available, and voice/PTT input receives TTS because the interaction is
already auditory. Clients can request `always` for replayable audio on an
informational message or `never` for text-only behavior.

For `personal_music_profile_analysis`, Ask DJ combines DJConnect Memory with
Spotify Web API profile snapshots from `GET /me/player/recently-played` and
`GET /me/top/{artists,tracks}` for `short_term`, `medium_term` and `long_term`.
The integration caches only compact summaries in Home Assistant Store, such as
recent track ids/artists, top artists/tracks by range, inferred genres,
mood/energy summary and `last_profile_refresh`. It does not store unlimited raw
Spotify listening history. Responses include `sources[]` entries such as
`spotify_recently_played`, `spotify_top_tracks_short_term`,
`spotify_top_artists_medium_term` and `djconnect_memory` so clients can show
where the profile came from.

For `recently_played_history`, Ask DJ uses Spotify recently-played data directly
and returns display-ready item rows in both top-level `items[]` and
`assistant_message.items[]`. Track, album and artist rows include Spotify URI
and artwork when Spotify exposes them. Playlist rows are based on recent-played
context; Spotify may expose only a playlist URI, so the display title can fall
back to `Spotify playlist` until richer playlist metadata is available.

For `personal_music_recommendations`, Ask DJ can return concrete playable
recommendations in `playback_actions[]` without changing playback. Clients show
those as Play Now actions. When the user taps Play Now, send
`command:"ask_dj_play_recommendation"` to `/api/djconnect/command` with the
selected action as `value`. DJConnect accepts only Spotify `track`, `album`,
`artist`, `playlist` and DJConnect `track_mix` actions. Track actions can
include `context_uri` plus `offset_uri`; album, artist and playlist actions
start their Spotify context. Successful Play Now responses include `dj_text`,
`dj_response` and optional `audio_url`/`audio_type`, so clients should render the
normal DJ announcement immediately. Ambient DJ facts are separate system
messages and must not replace the Play Now announcement. `track_mix` actions include a bounded `uris[]`
array of Spotify track URIs, which DJConnect starts as one explicit mix.
Successful Play Now commands are stored as compact positive personalization
signals in DJ Memory. Phrases such as `Speel wat anders` are treated as
personal recommendation requests: DJConnect looks at DJ Memory, Spotify recently
played items and Spotify top tracks/artists, returns random Play Now candidates,
and does not immediately change playback. Play Now actions include proxied
`image_url` artwork whenever Spotify/DJ Memory provides album, artist, playlist
or media art. DJ Memory also stores compact listening-time context such as hour,
weekday, weekday/weekend and daypart, so recommendation prompts and Play Now
reasons can become time-aware without clients storing local memory.

Ask DJ can also compose a seed-based mix from 1..n artists, tracks or genres,
for example `Stel een playlist samen op basis van Radiohead, Massive Attack en
Portishead`, `Ik wil een playlist obv tracks Reckoner, Teardrop` or `Ik wil een
playlist in genre ambient, techno`; broad genre/vibe prompts such as `maak een
90s dance mix` are treated as genre seeds instead of artist names. Contextual
requests such as `maak playlist obv huidig nummer` and `ik wil meer van deze
muziek horen` or `heb je meer nummers die hierop lijken` use the current Spotify
track URI as the seed, so they still work when the queue contains only one
track. DJConnect resolves up to five Spotify seeds and uses Spotify
recommendations to return Play Now track rows plus a `track_mix` action. Clients
should render the rows as list items with their own Play Now buttons and the
final `track_mix` action as the whole-mix queue action.
Explicit requests such as `ik wil vergelijkbare tracks` or `speel vergelijkbare
nummers` immediately queue the recommendation list and return the first 10 new
queue items as Play Now rows; question-style prompts such as `heb je meer
nummers die hierop lijken` remain preview-only.
After the user taps Play Now, the DJ response asks whether the mix should be
saved. Follow-up requests such as `Sla deze mix op als Spotify playlist` create
a private Spotify playlist and add the generated tracks, provided the OAuth
token has `playlist-modify-private`/`playlist-modify-public`.

To synchronize local chat cache and clear state:

```text
GET  /api/djconnect/ask_dj/history?since_revision=42
POST /api/djconnect/ask_dj/history/clear
POST /api/djconnect/ask_dj/idle_suggestion
```

If the user removes the last DJConnect integration entry from Home Assistant,
DJConnect clears server-side DJ Memory and Ask DJ history. Deleted clients should
not remain paired just because they still have a Keychain/local token or cached
chat bubbles. When a previously paired client receives `401`/`403`,
`not_configured` or stale-pairing from Home Assistant, clear the local paired
state and local Ask DJ cache for that HA installation.

When a client opens Ask DJ and Spotify is idle, it can call
`POST /api/djconnect/ask_dj/idle_suggestion` with the same client identity as
Ask DJ message requests. The backend appends one assistant-only system message
with `message_kind:"system"` and `origin:"idle_suggestion"` to the user-scoped
history. If DJConnect Memory or Spotify recently played/top profile data yields
a concrete candidate, the message includes a Play Now `playback_actions[]`
entry.

History responses contain `user_id`, `history_revision`, `clear_revision`,
`history_limit`, `history_trimmed_before`, `history_trimmed_count`, bounded
`messages[]` and `server_time`. The backend keeps at most the latest 1000
messages per HA user. When adding a message would exceed that limit, DJConnect
removes the oldest messages, increments `history_revision`, stores trim
metadata, and appends one assistant-only system message with
`message_kind:"system"`, `origin:"history_retention"`,
`intent:{"category":"system","intent":"history_limit_reached"}`,
`action:"none"` and `audio_url:null`. Clients should delete local Ask DJ
messages older than `history_trimmed_before` and may use
`history_trimmed_count` for diagnostics; they should not parse the system
message text to detect retention. To avoid chat spam, DJConnect emits at most
one retention system message per trim operation and suppresses repeated
retention messages for about an hour.

`history/clear` clears the DJConnect app chat history for the authenticated HA
user/context, increments `clear_revision`, resets trim metadata and returns an
empty `messages[]`. Clients compare their local `clear_revision` before
rendering; if the server revision is higher, wipe local cache and reload server
history for that HA installation/user.
`client_message_id` makes retried `message` posts idempotent for the same HA
user.

Home Assistant must have an Assist pipeline with STT and TTS configured.
DJConnect setup only asks you to choose the Assist pipeline; STT provider, TTS engine,
language and voice are managed in Home Assistant's Assist settings. For example,
choose an Assist pipeline that uses OpenAI STT and Piper/Nabu Casa TTS in Home
Assistant, then select that pipeline in DJConnect. If a stored pipeline was
removed, DJConnect falls back to the preferred/default pipeline. If no pipeline
STT provider can be resolved, it falls back to the first available Home
Assistant `stt.*` entity, for example `stt.openai_stt`. It resolves direct STT
providers through Home Assistant's supported
`stt.async_get_speech_to_text_engine` API and calls the provider audio stream
processor. As a final fallback it uses Home Assistant's official
`assist_pipeline.async_pipeline_from_audio_stream` helper from stage `stt` to
`stt`, which lets Home Assistant resolve the default pipeline internally. At
startup and for WAV uploads the integration logs the selected Assist/STT route
metadata without tokens or API keys. If no STT provider is found,
`/api/djconnect/voice` returns `503` with the checked option keys.

## ESP -> HA Command Endpoint

Firmware sends backend playback commands to Home Assistant instead of storing Spotify credentials locally:

```text
POST /api/djconnect/command
```

Required headers are `Authorization: Bearer <device_token>`, `X-DJConnect-Device-ID` and `Content-Type: application/json`. Supported commands include `status`, `devices`, `queue`, `playlists`, `pause`, `play`, `next`, `previous`, `seek_relative`, `start_liked_proxy`, `start_playlist`, `play_context_at`, `ask_dj_play_recommendation`, `set_shuffle`, `set_repeat`, `set_output`, `set_volume`, `volume_delta`, `save_current_track` and `set_current_track_favorite`. `seek_relative` accepts an integer millisecond offset for Apple app skip-forward/skip-back controls; positive values seek forward and negative values seek backward. `set_shuffle` accepts a boolean value; `set_repeat` accepts `off`, `track` or `context`; `volume_delta` accepts an integer relative volume step; `save_current_track` saves the current Spotify track to the user's Liked Songs/favorites through Spotify's library API and remains a legacy alias. `set_current_track_favorite` accepts a boolean `value`: `true` saves the current Spotify track to Liked Songs/favorites and `false` removes it. `play_context_at` accepts a context URI and track offset URI for Up Next playback. `ask_dj_play_recommendation` accepts a Play Now recommendation value with Spotify `uri`, optional `uris[]` for `track_mix`, optional `context_uri`/`offset_uri`, `kind`, `title`, `subtitle`, `reason` and `memory_key`. Responses are generic JSON shapes with `playback`, `devices`, `queue` or `playlists`, so future backends such as Sonos or Home Assistant media players can be added without firmware changes. `status` responses include `backend_available`, `ha_version`, `ha_major_minor` and a valid `playback` object even when no Spotify playback is active. Current playback can include `is_liked`/`favorite_status` when Spotify library status is available, so clients can render the favorite toggle state. `queue` responses include at most 100 items, top-level `context_uri` / `contextUri` when known and per-item artwork aliases such as `album_image_url` and `image_url`; `playlists` responses include Spotify playlists with `name`, `title`, `display_title`, `uri`, `value`, `playlist_uri`, `owner`, `subtitle`, `image_url`, `entity_picture` and artwork aliases such as `album_image_url`, `album_art_url` and `media_image_url`. HA returns playlist lists as top-level `playlists` and `items`, plus `data.playlists`, `data.items`, `result.playlists`, `result.items` and `count` for stricter clients. ESP32 `playlists` requests may send `limit`; HA caps ESP32 responses at 20 items and returns up to 100 for app-like clients while paging Spotify's `/me/playlists` API internally with provider-safe pages of at most 50 items. A successful `playlists` response returns `backend_available:true` even when Spotify playback is idle; backend failures still return a non-empty JSON body with `success:false`, `backend_available:false` and empty playlist aliases. Logs never include device tokens, Spotify tokens or backend credentials.

HA and ESP firmware must share the same `major.minor` protocol version. Patch
versions may differ, so HA `3.0.x` can talk to ESP `3.0.y`, but HA `3.1.x`
rejects ESP `3.0.y` and vice versa. When a mismatch is detected on
`/api/djconnect/status`, `/api/djconnect/command`, `/api/djconnect/voice` or
`/api/djconnect/event`, Home Assistant returns HTTP `426` with
`error: "version_mismatch"` and includes both major/minor values in the JSON
response.

## Native Home Assistant Entities

The integration exposes native Home Assistant entities for device status, DJ announcement tests and backend playback control. ESP32 clients additionally get firmware OTA, reboot and ESP hardware state such as battery, Wi-Fi RSSI and screen/LED status. Raspberry Pi clients get Pi-specific restart and shutdown buttons, but no ESP OTA or ESP hardware entities. iOS, macOS, watchOS and Windows clients only get client/runtime and backend/playback entities, so Home Assistant does not show irrelevant ESP hardware sensors for app-like clients. DJConnect no longer exposes a native `media_player` proxy; backend music control is available through DJConnect buttons, volume, output, repeat, shuffle, queue, playlist and playback availability entities plus `/api/djconnect/command`. Music plays on the selected Spotify/output device; the DJConnect speaker/client is used for local cues and DJ/voice responses.
DJConnect persists the last known ESP status in the Home Assistant config entry,
so ESP battery, firmware, pairing status, screen/LED state and sound output
remain visible after a Home Assistant restart or integration reload while
waiting for the next authenticated ESP `/api/djconnect/status` post.

## Voice Intent Examples

The post-STT PTT route uses deterministic local parsing as a guardrail around
HA Assist. Explicit media words select the Spotify search type: `nummer`,
`liedje` or `track` selects tracks; `album` or `plaat` selects albums;
`playlist` or `afspeellijst` selects playlists; generic phrases such as
`Speel Nirvana` remain artist-first. The current shared example data for the
website and client teams is in
[`examples/voice_intents.json`](examples/voice_intents.json), with the
maintenance contract in [`VOICE_INTENT_DATA.md`](VOICE_INTENT_DATA.md).

## ESP Device Endpoints

Home Assistant expects the firmware to expose:

```text
POST /api/device/ota
POST /api/device/dj_response
POST /api/device/command
GET /api/device/info
GET /api/device/pairing-info
POST /api/device/reboot
POST /api/device/restart
POST /api/device/shutdown
POST /api/device/forget
GET  /api/device/info
```

`/api/device/reboot` is ESP-specific. `/api/device/restart` and `/api/device/shutdown` are Raspberry Pi-specific local client actions.

ESP wake word is off by default. When ESP firmware reports `wake_word_enabled`
or `wake_word` in status, Home Assistant mirrors it as
`switch.djconnect_wake_word`. Toggling the switch sends the canonical local
device command:

```json
{"command":"wake_word","value":true}
```

The integration uses the device `local_url` from pairing/status when provided. During setup it discovers visible `_djconnect._tcp` clients, probes `/api/device/pairing-info`, and can prefill pairing fields for reachable iOS, macOS, watchOS, Raspberry Pi, Windows and ESP devices. Stale Bonjour records that no longer answer pairing-info are hidden from the selector; use the manual Client adres field if mDNS is visible but the advertised URL is wrong. If the stored field is empty at runtime, it resolves the `_djconnect._tcp` mDNS service for the paired device. When the setup code is only 6 digits, DJConnect can also use the single visible DJConnect mDNS service on the network. Fallback hostnames are only generated for real 12-character device suffixes as model-specific hostnames, for example `djconnect-lilygo-t-embed-s3-90B70990A994.local`. `djconnect-[6-digit-code].local` and legacy `djconnect-90B70990A994.local` fallbacks are intentionally ignored.

When the ESP status payload reports `spotify_configured=false`, Home Assistant treats that as a compatibility/status hint. Spotify OAuth credentials stay in Home Assistant and are not returned in status responses.

## Firmware OTA Releases

Firmware builds come from the MIT-licensed `djconnect-app` repo and are published to the MIT-licensed `djconnect-firmware` repo.

Expected release assets:

```text
djconnect-lilygo-t-embed-s3-vX.Y.Z.bin
djconnect-esp32-s3-box-3-vX.Y.Z.bin
```

Expected manifest:

```text
firmware_manifest.json
```

Example manifest:

```json
{
  "version": "3.1.99",
  "version_tag": "v3.1.99",
  "channel": "stable",
  "min_ha_integration": "3.1.99",
  "firmwares": [
    {
      "board": "t_embed_cc1101",
      "device": "lilygo-t-embed-s3",
      "asset": "djconnect-lilygo-t-embed-s3-v3.1.99.bin",
      "url": "https://github.com/pcvantol/djconnect-firmware/releases/download/v3.1.99/djconnect-lilygo-t-embed-s3-v3.1.99.bin",
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "size": 2113136
    },
    {
      "board": "esp32_s3_box3",
      "device": "esp32-s3-box-3",
      "asset": "djconnect-esp32-s3-box-3-v3.1.99.bin",
      "url": "https://github.com/pcvantol/djconnect-firmware/releases/download/v3.1.99/djconnect-esp32-s3-box-3-v3.1.99.bin",
      "sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
      "size": 2113136
    }
  ]
}
```

For ESP32 clients, the firmware channel option controls which GitHub firmware release track is used:
`stable` reads GitHub's latest non-prerelease firmware release, while `beta`
reads the newest prerelease from `pcvantol/djconnect-firmware`.

The manifest-level `version` / `version_tag` is used for update comparison.
Home Assistant selects the matching `firmwares[]` entry for the configured ESP
device type and sends that entry's `device`, `asset`, `url` and `sha256` to
`POST /api/device/ota`. Top-level `device`, `asset`, `sha256` and `size`
fallbacks are intentionally not used.

The firmware version is injected through PlatformIO build flags from the Git tag.

Recommended firmware source release helper:

```bash
./release.sh 3.1.99
```

In the separate `djconnect-app` repository, the firmware release script should
validate the semantic version, update firmware version metadata, run the
PlatformIO builds, rename firmware binaries to device-specific assets such as
`djconnect-lilygo-t-embed-s3-vX.Y.Z.bin`, calculate SHA256, update
`firmware_manifest.json`, commit, tag and push.

Preview the firmware release flow without changing files:

```bash
./release.sh 3.1.99 --dry-run
```

When publishing to the public firmware repository, use the firmware script's
public-repo option if available:

```bash
./release.sh 3.1.99 --publish-firmware-repo ../djconnect-firmware
```

The public `djconnect-firmware` repository should contain only the release
binary, `firmware_manifest.json`, release metadata and non-secret documentation.
Do not publish firmware source code, NVS secrets, device tokens, Spotify refresh
tokens or Home Assistant tokens.

## HACS Release Workflow

Use this checklist for every Home Assistant integration release.

Pre-release checklist:

- Confirm the working tree only contains intended changes.
- Update `custom_components/djconnect/manifest.json` to the target version.
- Update `custom_components/djconnect/const.py` to the same target version.
- Update all repo documentation touched by the change or release: at minimum `README.md`, `CHANGELOG.md`, `AGENTS.md`, `HANDOFF.md`, `TODO.md`, `ISSUES.md`, `SYNC_PROMPTS.md`, `PRODUCT_ROADMAP.md`, `TECHNICAL_DESIGN_DECISIONS.md`, `CHAT_BOOTSTRAP.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `info.md` and relevant files under `examples/`.
- Update and JSON-validate `examples/djconnect.postman_collection.json` whenever HTTP endpoints, auth headers, request payloads or response shapes change.
- Keep the automated Postman collection validator current; CI runs `python -m unittest tests.test_postman_collection` to check schema, placeholder secrets, auth headers and client identity examples.
- Keep `examples/ask_dj_e2e_cases.json` current for Ask DJ client-visible intents; CI and `release.sh` run `python -m unittest tests.test_ask_dj_e2e_contract` to validate offline Ask DJ E2E response contracts.
- Update `README.md` current version, examples, endpoints, HACS instructions and release workflow.
- Update `CHANGELOG.md` with a new section for each release. Keep previous release sections; do not consolidate the changelog into one current-version block.
- Keep `AGENTS.md` aligned with the current version and release expectations.
- Keep `HANDOFF.md`, `TODO.md`, `ISSUES.md` and `CHAT_BOOTSTRAP.md` aligned with release status, known checks, remaining field validation and fresh-chat initialization guidance.
- Keep this repo's `SYNC_PROMPTS.md` current when cross-repo contracts, client types, endpoints or pairing/discovery behavior change, including when the change originates in another DJConnect repo.
- Keep this repo's `PRODUCT_ROADMAP.md` current when product ideas, production must-haves, shipped roadmap items or premium feature candidates change, including when the change originates in another DJConnect repo.
- Keep `info.md` and HACS-facing copy current for users.
- Review and update all Dutch and English translations for changed config-flow,
  options-flow, repair-flow, entity and service strings.
- Explicitly decide whether test coverage needs to be expanded for the change; add tests for new behavior paths, regression risks, translations and edge cases. Documentation-only changes may rely on existing tests.
- Verify `custom_components/djconnect/brand/` contains `icon.png`, `icon@2x.png` and `logo.png`.
- Verify `LICENSE` covers this repository and that related DJConnect repositories keep their MIT license metadata aligned.
- Before build/test/release validation, check for available updates to third-party libraries, frameworks and build tools. Apply safe upgrades as reviewable changes and update lockfiles/manifests, `THIRD_PARTY_NOTICES.md` and `TECHNICAL_DESIGN_DECISIONS.md`. When dependency, framework or tool versions are upgraded, updating third-party notices and dependency/design documentation is mandatory; document skipped upgrades in `HANDOFF.md`.
- Run the lightweight tests:

```bash
python3 -m unittest discover -s tests
```

For Ask DJ client contract changes, the focused offline E2E check is:

```bash
python3 -m unittest tests.test_ask_dj_e2e_contract
```

For Postman-only contract changes, the focused local check is:

```bash
python3 -m unittest tests.test_postman_collection
```

Tag and publish:

One-liner:

```bash
./release.sh 3.1.99
```

The script updates the integration version in `manifest.json`, `const.py`,
`README.md`, `CHANGELOG.md`, `AGENTS.md` and relevant example metadata before
staging and committing. It does not replace the manual documentation review
above.

Preview without executing git/gh commands:

```bash
./release.sh 3.1.99 --dry-run
```

Manual equivalent:

```bash
git add .
git commit -m "Release DJConnect v3.1.99"
git tag v3.1.99
git push origin main
git push origin v3.1.99
gh release create v3.1.99 --title "DJConnect v3.1.99" --notes-file CHANGELOG.md
```

After every release, clean up old completed GitHub Actions workflow runs. Keep
only the newest release/tag validation and the newest `main` validation unless a
specific debugging reason requires retaining more:

```bash
gh run list --limit 100
for id in $(gh run list --limit 100 --json databaseId --jq '.[2:][].databaseId'); do gh run delete "$id"; done
```

Release cleanup helper:

```bash
./cleanup_old_releases.sh --keep 1
./cleanup_old_releases.sh --keep 1 --execute
```

The cleanup helper keeps the newest semantic-version GitHub release/tag by
default and deletes older `vX.Y.Z` releases/tags only when `--execute` is used.
DJConnect releases should normally keep only the latest release/tag unless a
specific test or support reason requires retaining more.

Home Assistant / HACS verification:

1. Open HACS in Home Assistant.
2. Open DJConnect.
3. Choose **Redownload** or refresh HACS update information.
4. Select and install the new release from HACS.
5. Restart Home Assistant.
6. Go to **Settings -> Devices & services**.
7. Add DJConnect again, or remove and re-add the DJConnect integration if needed.
8. Complete pairing and Spotify OAuth in the DJConnect config flow.
9. Open DJConnect options and verify there is no internal server error.
10. Verify the integration icon/logo appears after browser/app cache refresh.
11. Run `djconnect.test_parse`, `djconnect.test_command` and `djconnect.test_tts`.
12. Verify device status, last command, last track and firmware update entities.

Firmware release cross-check, when publishing firmware as well:

- Build firmware from the separate `djconnect-app` repository.
- Prefer the firmware repo one-liner: `./release.sh X.Y.Z`.
- Use `./release.sh X.Y.Z --dry-run` before publishing when in doubt.
- Publish binaries to the public `djconnect-firmware` repository.
- Publish device-specific release assets such as `djconnect-lilygo-t-embed-s3-vX.Y.Z.bin` and `djconnect-esp32-s3-box-3-vX.Y.Z.bin`.
- Update `firmware_manifest.json` with manifest-level `version`, `version_tag`, `channel`, `min_ha_integration` and a `firmwares[]` entry per supported device.
- Confirm each `firmwares[]` entry includes `device`, `asset`, `url`, `sha256` and `size`.
- Confirm OTA discovers the new firmware through the Home Assistant update entity.

## Tests

Run the lightweight unit tests with:

```bash
python3 -m unittest discover -s tests
```

These tests use local stubs for Home Assistant imports and focus on pure DJConnect helpers, OAuth URL building, Assist response mapping, app/Raspberry Pi mDNS discovery, config-flow prefill/selection behavior and translation coverage.

## Troubleshooting

- If Spotify login does not return to Home Assistant, verify the Spotify redirect URI in the Spotify Developer Dashboard exactly matches the Nabu Casa or external Home Assistant URL shown by DJConnect.
- If Add integration shows that an Assist pipeline is required, configure a
  Home Assistant Assist pipeline with both STT and TTS before adding DJConnect.
- If the config flow does not load, restart Home Assistant and check that HACS installed `custom_components/djconnect`.
- If Home Assistant discovery still shows an old `spotify_dj` / `SpotifyDJ` card next to DJConnect, remove the old custom integration from Home Assistant: delete `/config/custom_components/spotify_dj`, remove any old HACS custom repository for SpotifyDJ, clear ignored/discovered SpotifyDJ entries from Settings -> Devices & services where needed, and restart Home Assistant. DJConnect itself only ships the `djconnect` integration domain; the old card means Home Assistant is still loading stale SpotifyDJ integration files or stale firmware/discovery from an ESP that has not been renamed yet.
- If the integration icon stays white or generic, update/re-download the HACS integration, restart Home Assistant, and refresh the browser/app cache. Home Assistant 2026.3+ reads custom integration brand images from `custom_components/djconnect/brand/`.
- If opening DJConnect options returns an internal server error, update to this release or newer; older builds assigned HA's read-only `config_entry` property.
- If OTA cannot start, make sure the device has reported `local_url` or can be reached as `http://[device_id].local`.
- If OTA is blocked, check battery level and USB power.
- If the firmware update entity reports a GitHub rate limit, wait for GitHub's API limit to reset; DJConnect keeps the entity loaded and records the temporary error in its attributes. The firmware update entity is non-polling and checks GitHub on add/manual refresh/install plus an internal one-hour schedule, not every few seconds.
- If Spotify playback fails, reauthorize Spotify in Home Assistant and check that the selected backend has an active playback target.
- If Spotify fails only after about an hour of idle time, update to this release or newer; normal access-token expiry is handled by HA with a cached token and one refresh retry.
- If Spotify returns `invalid_grant` or `Refresh token revoked`, Spotify revoked the stored OAuth token. Open Home Assistant Repairs and choose `Fix` for the DJConnect authorization issue to run Spotify OAuth again.
- If an options-flow Spotify OAuth callback reports an empty failure after Spotify approved access, update to this release or newer; the callback now keeps the stored token even when the options dialog was already closed.
- If the ESP logs `HA playback HTTP 503` immediately after pairing, update to this release or newer; playback backend failures are now returned as JSON without invalidating HA pairing.
- If provisioning says `local_url is unknown`, make sure the device advertises `_djconnect._tcp` mDNS or enter the Client adres, for example `http://djconnect-lilygo-t-embed-s3-90B70990A994.local`.
- If Home Assistant sees a Raspberry Pi/iOS/macOS/watchOS client through mDNS but pairing shows a pairing-info reachability error, verify that the Client adres shown in the pairing form opens `/api/device/pairing-info` from the Home Assistant network. Correct the Client adres manually if Bonjour advertised a hostname or port that Home Assistant cannot reach.
- If Home Assistant added the integration but the ESP still shows a pairing code, check `sensor.djconnect_ha_pairingstatus`: `pending` means HA has a local token but the ESP has not confirmed `/api/device/pair` yet. Verify the device URL/mDNS reachability and wait for the next pairing retry or re-pair from the config flow.
- If the ESP briefly shows Home Assistant paired and then returns to a pairing code after the first command, update to this release or newer; DJConnect now accepts the real model-specific device ID after setup-code based direct pairing and logs token/device mismatch reasons without exposing token values.
- If the ESP logs `HA status response: 401` while HA can still reboot the device, update to this release or newer and re-pair if needed. Status/command/voice auth now accepts `djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX` and `djconnect-esp32-s3-box-3-XXXXXXXXXXXX` with the stored token, learns the current id, and keeps `ha_pairing_status` stable.
- If ESP logs show repeated `Home Assistant direct pairing stored` during normal next/previous/volume/status commands, update to this release or newer; startup and playback paths no longer call `/api/device/pair` when HA already has a stored device token.
- If the pairing token is stale, open DJConnect options and choose `Retry pairing with current code`. If the device shows a new code, choose `Re-pair with new pairing code`.
- If brightness, speaker volume or timeout entities stay at defaults, make sure the ESP firmware sends these settings in its periodic Home Assistant status payload; DJConnect accepts common aliases such as `brightness`, `cue_volume`, `screen_dim_timeout` and `turn_off_after_ms`.
- If `/api/djconnect/voice` returns `No STT provider configured`, configure an Assist pipeline with STT/TTS such as OpenAI STT plus Piper/Nabu Casa TTS, select that pipeline in DJConnect options, or clear the stale DJConnect pipeline option so the integration can use Home Assistant's preferred/default Assist pipeline.
- If `/api/djconnect/voice` returns `HA Assist STT did not return recognized text`, enable debug logging for `custom_components.djconnect`, trigger one ESP voice request, then open `/api/djconnect/debug/last_voice.wav` while logged in to Home Assistant. DJConnect only keeps this last raw ESP WAV in memory while debug logging is enabled; use it to check for clear speech, clipped audio, silence, wrong sample rate or noise.
- If WiFi/pairing works but Spotify does not, reauthorize Spotify in Home Assistant; pair/status payloads must not contain Spotify OAuth secrets.
- If Home Assistant cannot find a private `DJConnect Liked Proxy` playlist, reauthorize Spotify so the refresh token includes `playlist-read-private`.
- If a PTT command cannot start Spotify playback, the ESP should receive a friendly DJ announcement; check that Spotify is authorized in Home Assistant and that the backend has a reachable playback target.
- If `/api/djconnect/voice` returns `missing_text`, send raw WAV audio for PTT or a developer test text through `X-DJConnect-Text`.
- If `spoken=false`, HA did not provide a compatible WAV/MP3 URL or the ESP could not play it; the text response should still be displayed.
- If HA TTS returns MP3, DJConnect can send the MP3 `audio_url` to ESP firmware that supports MP3 DJ announcement playback.
- If the ESP logs `audio_url=none`, Home Assistant sent text-only. Check that `DJ aankondiging op apparaat afspelen` is enabled, the selected Home Assistant Assist pipeline has working TTS, and the Home Assistant internal URL is reachable from the DJConnect device network.
- If Home Assistant reports `Invalid value for number.djconnect_volume: -1.0`, update to this release or newer; DJConnect treats unknown device volume as unavailable instead of publishing an out-of-range value.
- If the ESP reports `401` for `/api/device/dj_response`, pair the device again so the device token is refreshed.
- If `/api/djconnect/tts/{token}.wav` or `.mp3` returns `404` or `410`, the token is unknown or expired; trigger the DJ announcement again.
- If the ESP cannot download the temporary audio URL, make sure the Home Assistant internal URL is reachable from the DJConnect device network.
- Diagnostics are available from the Home Assistant integration page and redact token/password/secret fields.
