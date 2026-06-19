# DJConnect Home Assistant Integration Handoff

## Current State

- Repository: `pcvantol/djconnect`.
- Integration domain: `djconnect`.
- Current integration release: `3.1.53`.
- Release status: DJConnect `3.1.53` is the current release target for community/security documentation and prompt naming hygiene.
- Home Assistant integration is HACS-distributed and MIT-licensed.
- DJConnect client and firmware repositories are MIT-licensed unless their own repository metadata states otherwise.
- Public firmware release assets live in `pcvantol/djconnect-firmware`.
- Public product website: `https://djconnect.dev`.
- Cross-repo prompts are consolidated into one canonical `pcvantol/djconnect/SYNC_PROMPTS.md`; old loose prompt files and sibling-repo copies are intentionally removed and must not be reintroduced.
- Product roadmap is consolidated into one canonical `pcvantol/djconnect/PRODUCT_ROADMAP.md`; sibling-repo roadmap copies are intentionally removed and must not be reintroduced.
- Current firmware uses the local ESP API with bearer-token auth and generic playback commands.
- ESP no longer stores Spotify OAuth/client_id/refresh_token or other playback-backend credentials.
- HA integration is the trusted backend for pairing, Spotify OAuth/backend playback, Assist/STT/TTS, OTA and native entities.
- HA integration and ESP firmware must share the same `major.minor` protocol version; patch versions may differ.
- Lightweight tests live in `tests/` and currently pass with `python3 -m unittest discover -s tests`.

## Architecture

```text
DJConnect ESP device
  -> HA /api/djconnect/status, /command, /voice
  -> djconnect integration
  -> HA Assist/STT/TTS + Spotify backend playback
  -> optional /api/device/command or /api/device/dj_response back to ESP
```

### Home Assistant Responsibilities

- Config flow and options flow.
- Optional BLE WiFi provisioning before pairing.
- Device pairing and device-token lifecycle.
- Spotify OAuth PKCE through HA external step.
- Spotify refresh-token rotation and revoked-token repair.
- Backend playback proxy and native HA `media_player`.
- Device settings/entities through ESP `/api/device/command`.
- Raw WAV PTT processing via HA STT/Assist.
- DJ response TTS and temporary WAV/MP3 audio URLs.
- Firmware release discovery and OTA orchestration.
- Diagnostics, repairs and user-facing errors.

### ESP Responsibilities

- Device runtime, display, buttons, LED ring and local audio cues.
- Captive portal / BLE WiFi setup.
- Pairing-code display and local bearer-token storage.
- Status reports to HA.
- Generic playback commands to HA.
- Raw WAV upload to HA for PTT.
- Playback of HA-provided DJ response text/audio locally.
- OTA execution through `POST /api/device/ota`.

## Endpoint Contract

### ESP -> HA

- `POST /api/djconnect/pair`
- `POST /api/djconnect/status`
- `POST /api/djconnect/command`
- `POST /api/djconnect/voice`
- `POST /api/djconnect/event`

All protected ESP -> HA routes use:

- `Authorization: Bearer <device_token>`
- `X-DJConnect-Device-ID: djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX` or `djconnect-esp32-s3-box-3-XXXXXXXXXXXX`

Version contract:

- HA `3.0.z` accepts ESP `3.0.z`; HA `3.1.z` accepts ESP `3.1.z`.
- A different ESP `major.minor` returns HTTP `426` with `error: version_mismatch`.
- `version_mismatch` is a protocol/update requirement, not a stale pairing-token state; do not clear pairing because of it.

### HA -> ESP

- `GET /api/device/info`
- `GET /api/device/pairing-info`
- `POST /api/device/pair`
- `POST /api/device/command`
- `POST /api/device/ota`
- `POST /api/device/reboot`
- `POST /api/device/restart`
- `POST /api/device/shutdown`
- `POST /api/device/forget`
- `POST /api/device/dj_response`

All protected HA -> ESP routes use:

- `Authorization: Bearer <device_token>`

Do not use `/api/device/provision_spotify`; it is removed and should not be called.

## Decisions Made

- The previous external message-bus control route is removed and must not be reintroduced.
- ESP is not a Spotify Connect speaker/player.
- HA `media_player.djconnect_playback_proxy` represents backend playback, not ESP speaker audio.
- ESP speaker is only for local cues and DJ/voice response audio.
- ESP stores no Spotify/Sonos/backend credentials.
- Pairing/status responses must never include `spotify_client_id`, `client_id`, `spotify_refresh_token`, `refresh_token` or nested Spotify OAuth secrets.
- Spotify OAuth credentials stay HA-internal.
- Spotify OAuth uses PKCE with a user-owned Spotify Developer app. Setup asks for `spotify_client_id`, shows the exact redirect URI that must be registered in Spotify, strongly recommends a stable Nabu Casa HTTPS external URL, and no longer uses a shared built-in Client ID.
- Spotify access tokens are cached in Home Assistant until shortly before expiry. Normal access-token expiry must refresh on demand and retry once after Spotify API `401`; this must stay invisible to ESP/iOS/macOS/watchOS/Raspberry Pi clients.
- Spotify refresh-token rotation must be handled silently. If Spotify rejects a refresh token, HA must retry any newer stored runtime/config-entry/config refresh token before creating a Repair issue.
- Spotify `invalid_grant` / revoked refresh tokens only produce a user-friendly reauthorize/Repair flow after every known stored refresh token has failed.
- Startup/pairing repair checks must look at both config entry data and options before creating missing Spotify token/client/scope issues, so a newly paired client does not immediately show a false Spotify repair.
- Repair flow must open Spotify OAuth and may only close as fixed after a new/missing refresh token is stored, not merely because an old token exists.
- Options flow also has a “Spotify opnieuw autoriseren” action using the same callback storage path.
- Token sent by HA to ESP in `POST /api/device/pair` must be exactly the token accepted by HA `/status`, `/command` and `/voice`.
- HA -> ESP pairing payload uses required `ha_local_url`; legacy `ha_url` and `ha_remote_url` must not be sent or expected.
- `ha_local_url` must be present and must never be a `*.ui.nabu.casa` cloud URL. Resolve HA Network/internal/source-IP local URL first, prefer a LAN source-IP over `homeassistant.local`, then use `http://homeassistant.local:8123` only as final local fallback.
- Cloud/Nabu Casa URLs are only for the Spotify OAuth config/repair flow, never for device-to-HA status, command or voice traffic.
- HA may call `POST /api/device/pair` only for initial pairing, explicit re-pair/token rotation or stale-pairing recovery. Startup with a stored token, normal status sync, playback commands and settings sync must not call it.
- Setup-code pairing can start with a temporary six-digit identity, but HA must learn and persist only the real model-specific device ID from the first authenticated ESP call. Current ESP IDs are `djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX` and `djconnect-esp32-s3-box-3-XXXXXXXXXXXX`; app/client IDs are `djconnect-ios-XXXXXXXXXXXX`, `djconnect-macos-XXXXXXXXXXXX`, `djconnect-watchos-XXXXXXXXXXXX` and `djconnect-raspberry-pi-XXXXXXXXXXXX`. Legacy `djconnect-XXXXXXXXXXXX` IDs are not accepted.
- `client_type` must match the device-id prefix: `ios` with `djconnect-ios-*`, `macos` with `djconnect-macos-*`, `watchos` with `djconnect-watchos-*`, `raspberry_pi` with `djconnect-raspberry-pi-*`, and `esp32` with ESP model-specific IDs.
- Ask DJ / DJ Memory is server-side in the Home Assistant integration. Apple Watch, iOS and macOS clients remain lightweight and store no DJ Memory. HA keeps runtime session history plus persistent Store data under `djconnect_memory` version `1`, keyed by HA user id when available and otherwise by DJConnect device/client id. Do not store OAuth tokens, bearer tokens, raw audio or full prompts in memory.
- Text chat for app Ask DJ uses `POST /api/djconnect/ask_dj/message`; service `djconnect.ask_dj` remains a developer entrypoint. The backend classifies informational questions separately from playback/device actions, so questions such as "Waarom koos je dit nummer?" must not change playback while requests such as "Volgende nummer" or "Zet rustige muziek op" can execute Spotify/Home Assistant actions and return a DJ response.
- Cross-device Ask DJ history is stored in Home Assistant Store key `djconnect_ask_dj_history` version `1`, scoped by HA user id. iOS, macOS and Apple Watch clients use `GET /api/djconnect/ask_dj/history?since_revision=<number>` and `POST /api/djconnect/ask_dj/history/clear` to reconcile local cache. `client_message_id` dedupes retries; `client_id` and `client_type` are metadata only.
- Ask DJ supports `audio_response:auto|always|never`. Default `auto` keeps informational text chat text-only, generates TTS for playback/hybrid intents, and generates TTS for voice/PTT interactions. `always` lets clients request replayable audio for an informational chat answer; `never` keeps any Ask DJ answer text-only.
- Ask DJ Push-To-Talk for iOS/macOS/watchOS uses `POST /api/djconnect/voice` with `Content-Type: audio/wav`. After server-side STT, route the transcript through the same Ask DJ handler as text chat and return the rich Ask DJ response plus `transcript`/`recognized_text`. Keep ESP32 WAV PTT on the existing command parser flow.
- Pairing/status responses include Ask DJ capability booleans: `ask_dj_supported`, `ask_dj_voice_supported`, `voice_supported` and `ask_dj_audio_response_supported`.
- `personal_music_profile_analysis` is an informational Ask DJ intent for personal listening-profile questions over periods such as today, this week, last month, last 30/90 days or this year. It must never mutate playback. Use only available DJ Memory/playback context and be explicit when there is too little listening history.
- Spotify listening-profile support uses `GET /me/player/recently-played` and `GET /me/top/{artists,tracks}` with `short_term`, `medium_term` and `long_term`; required OAuth scopes are `user-read-recently-played` and `user-top-read`. Store only compact profile snapshots in DJ Memory with a multi-hour TTL, never unlimited raw Spotify listening history.
- Profile-analysis responses should fill `sources[]` with Spotify and DJConnect Memory source names so iOS/macOS/watchOS can show them under the answer.
- `personal_music_recommendations` can return `playback_actions[]` for client Play Now buttons while keeping `action:"none"`. Play Now uses `/api/djconnect/command` with `command:"ask_dj_play_recommendation"` and a Spotify-only recommendation value. Successful plays are stored in DJ Memory as positive recommendation signals.
- Ask DJ clear synchronization is revision-based. A clear increments `clear_revision` and `history_revision` for the HA user. Clients clear local cache when their local clear revision is older than the server value, then reload server history.
- Ask DJ responses can contain `images[]`, `links[]`, `audio_url`, `intent`, `action` and `memory_key`. External image URLs must be proxied through `/api/djconnect/image_proxy/{token}`; links/sources stay in `links[]` and are shown under Sources by clients.
- DJConnect does not initialize external music-knowledge sources for every request. The DJ response prompt prioritizes provided Spotify metadata, DJ Memory/media context and then MusicBrainz, Wikidata, short Wikipedia summaries, Last.fm, Discogs and TheAudioDB when that knowledge is available; trivia must be skipped instead of invented.
- HA and ESP firmware compatibility is strict on `major.minor`: patch versions may differ, but `3.0.z` must not talk to `3.1.z`. HA returns HTTP `426` `version_mismatch` with HA/firmware metadata and keeps pairing intact.
- ESP status payloads can report device settings as top-level fields or nested `settings`, `screen` and `led` objects; HA flattens those aliases for native entities, including `wake_word_enabled` / `wake_word`.
- HA pairing status is `pending` until ESP confirms `ha_pairing_status=paired`; a locally stored token alone is not enough.
- `POST /api/djconnect/command` should return JSON and avoid 503 loops for Spotify auth failures; report backend unavailable without causing ESP to clear pairing.
- Physical PTT uses raw WAV upload to HA; ESP must not authenticate directly to HA Assist WebSocket.
- HA STT/TTS provider selection is driven by the selected Home Assistant Assist pipeline; legacy DJConnect `stt_engine`/`tts_*` options are ignored by runtime paths.
- DJConnect exposes a Home Assistant conversation agent named `DJConnect DJ` for Assist satellites such as Voice Preview Edition. Initial setup can create an Assist Conversation Agent-only entry without a DJConnect client pairing code, device token or Client adres. Its options flow must stay compact and must not show device pairing, Client adres, Assist pipeline, firmware channel, DJ announcement playback toggle or OTA/audio advanced fields.
- The initial config flow chooses setup method only once. The pairing step must not repeat `setup_method`; it only collects discovery/client details. Client type choices are ordered iOS, macOS, Apple Watch, Linux/Raspberry Pi and ESP32.
- Firmware channel is ESP32-only. iOS/macOS/watchOS update through app distribution/TestFlight, and Linux/Raspberry Pi clients update from their own GitHub source/install flow, so those client types must not show or store `firmware_channel`.
- DJ response tone is configured with one free-form `dj_response_prompt`; old fixed `dj_style` / `dj_profile` choices are removed and must not be reintroduced.
- STT fuzzy correction, Spotify intent detection and AI DJ announcement generation use the configured conversation agent when present, otherwise resolve Home Assistant's preferred/default Assist pipeline and use its conversation engine.
- The DJ response prompt must start with DJConnect-specific override instructions so global smart-home conversation-agent instructions do not steer the spoken DJ response.
- Dutch DJ announcement prompts instruct Assist/TTS to pronounce English artist, album and track names in English inside Dutch copy.
- Options flow no longer shows standalone STT/TTS engine, language or voice fields; manage those in Home Assistant Assist.
- Text-only `/api/djconnect/voice` is a DJ response test and must not trigger Spotify playback parsing.
- Raw WAV `/api/djconnect/voice` is the real STT + command + playback path.
- Current-track questions such as `Welk nummer draait er nu?` and `Wat speelt er?`
  read Spotify playback state via the backend status command and generate a DJ
  response without starting new playback. If no track is playing or Spotify is
  unavailable, DJConnect still returns a friendly DJ response.
- Direct playback-control phrases such as `Stop muziek`, `Start muziek`,
  `Zet harder`, `Zet zachter`, `Volgende nummer` and `Vorig nummer` bypass
  music search/Assist parsing and call Spotify backend commands directly
  (`pause`, `play`, `set_volume` +/-10 from current volume, `next`,
  `previous`), then generate a DJ response.
- DJ response TTS is returned to ESP as text and optional temporary WAV/MP3 `audio_url`.
- Device setting entities accept firmware aliases such as `brightness`, `screen_brightness`, `cue_volume`, `speaker_volume`, `screen_dim_timeout_ms` and `turn_off_after_ms`.
- `number.djconnect_volume` and other numbers must publish `None/unavailable`, not invalid values outside HA ranges.
- Firmware assets are device-specific, e.g. `djconnect-lilygo-t-embed-s3-vX.Y.Z.bin` and `djconnect-esp32-s3-box-3-vX.Y.Z.bin`. HA selects the matching `firmwares[]` manifest entry and sends that entry's `device` as the OTA target.
- Secrets must not appear in logs, diagnostics or state attributes.
- Spotify trademark/non-affiliation notice remains in docs/UI/diagnostics.

## Current Release Notes

- Current release line is `3.1.x`; only the latest GitHub release/tag should be kept after release cleanup.
- Current latest baseline is `3.1.53`.
- Release workflow expectation: before every release, review and update all repo documentation affected by the change or release, including `README.md`, `CHANGELOG.md`, `AGENTS.md`, `HANDOFF.md`, `TODO.md`, `ISSUES.md`, `SYNC_PROMPTS.md`, `PRODUCT_ROADMAP.md`, `TECHNICAL_DESIGN_DECISIONS.md`, `CHAT_BOOTSTRAP.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `info.md` and relevant `examples/*`. Explicitly decide whether test coverage must be expanded for the change; add coverage for new behavior paths, regression risks, translations and edge cases. After publishing a release, clean up old semver releases/tags with `./cleanup_old_releases.sh --keep 1 --execute` unless multiple releases are intentionally retained.
- Before build/test/release validation, check whether third-party libraries, frameworks and build tools can be safely upgraded. If any version is upgraded, update lockfiles/manifests, `THIRD_PARTY_NOTICES.md` and dependency/design documentation in the same release. If an upgrade is skipped, record the reason here.
- For the current community/security documentation and prompt naming release,
  no third-party library/framework/tool versions were upgraded;
  `THIRD_PARTY_NOTICES.md` remains unchanged.
- AI-assisted/Codex development hygiene is now documented in
  `CONTRIBUTING.md`, `SECURITY.md` and `CHAT_BOOTSTRAP.md`; accepted changes
  remain maintainer-reviewed and prompts/logs/issues must not contain secrets,
  private data or proprietary third-party material.
- Local development environment setup is documented in
  `DEVELOPMENT_ENVIRONMENT.md`, including the Docker Home Assistant config path,
  integration sync command, Core restart command and manual UI validation list.
- Changelog expectation: keep `CHANGELOG.md` as a per-release changelog. Add a new section for each release and do not consolidate old release notes into one current-version block.
- HACS-visible docs now show the public DJConnect website. The external website should use the same setup requirements: Home Assistant, HACS, Spotify Premium, HA Assist pipeline with STT/TTS, local-network pairing, and Nabu Casa/external HTTPS URL for Spotify OAuth.
- `TECHNICAL_DESIGN_DECISIONS.md` documents reverse-engineered code-level design patterns, language-specific coding conventions and the dependency/license/source inventory. Keep it in the release checklist whenever architecture, dependencies, frameworks or external API usage changes.
- Voice/Assist search text such as "ik wil Pearl Jam starten" must resolve to a Spotify artist first; generic free-text PTT search stays artist-first unless the request explicitly names another media type.
- Explicit PTT media words choose the matching Spotify Search type: `nummer`/`liedje`/`track` -> track, `album`/`plaat` -> album, `playlist`/`afspeellijst` -> playlist, and `standaard playlist`/`favorieten`/`liked songs` -> configured default playlist.
- Canonical spoken intent examples live in `examples/voice_intents.json`, with
  the maintenance contract in `VOICE_INTENT_DATA.md`; keep website/client docs
  aligned with those files.
- Local deterministic intent parsing may override stale/generic HA Assist output, so a new request such as `Speel Nirvana` cannot keep using an older artist context such as Red Hot Chili Peppers.
- Spotify playlist browsing may return up to 100 playlists to app-like clients, but HA must page Spotify `/me/playlists` internally with provider-safe pages of at most 50 items to avoid Spotify HTTP 400 `Invalid limit`.
- The native playback proxy media player must cache `playback` snapshots returned by backend commands so current state, album art, volume and selected output update in Home Assistant.
- Use Developer Tools action `djconnect.test_ptt_text` to debug the real PTT route immediately after STT conversion: enter recognized natural-language text, then DJConnect runs the guarded Assist fuzzy-correction step, intent parsing, Spotify search/playback, DJ aankondiging generation, TTS audio creation and delivery to the connected client/device.
- Do not send arbitrary text as `context_uri`, and do not perform broad track/album search for generic artist requests.
- Device DJ responses after successful PTT playback are generated from resolved Spotify/playback metadata and the configured `dj_response_prompt`, not from the generic Assist fallback announcement.
- If a just-executed Spotify command has fresh `resolved_media`, merge any
  concrete current track returned in that same command's `device_response.playback`
  into the DJ announcement media context. Do not use stale
  `runtime.last_playback` as a substitute for current command metadata.
- DJ announcement `audio_url` is optional by contract, but when HA TTS produces
  WAV/MP3 audio HA should build the temporary download URL through the shared
  local HA URL resolver. A device log with `audio_url=none` means HA fell back
  to text-only, usually because TTS audio generation failed, returned an
  unsupported type, or HA could not build a reachable local URL.
- `dj_response_prompt` remains free text in config/options flow, with a separate preset selector for neutral/business, warm/personal and humorous/witty prompts. There is no backwards compatibility for old fixed `dj_style` or `dj_profile` values.
- Parser prompts must be isolated from response prompts so text such as "Noem waar mogelijk..." can never leak into Spotify search queries like `Opdracht Metallica`.
- If Spotify playback fails because there is no active device, refresh `/me/player/devices`, transfer playback to a suitable active/default Spotify device when possible and retry once.
- `spotify_source` and `liked_proxy_playlist_uri` are no longer shown as config/options fields. Runtime support may still tolerate older stored values, but new UI saves do not expose or write those overrides.
- Config flow no longer requires an official Home Assistant Spotify `media_player` entity. DJConnect authorizes Spotify through its own OAuth flow and uses the Spotify Web API for backend playback. Setup still requires Home Assistant to expose at least one Assist pipeline with both STT and TTS before pairing can continue.
- Pairing prevents Nabu Casa/cloud URLs from being sent as `ha_local_url` and falls back to HA network/source-IP local URL discovery, then `http://homeassistant.local:8123`.
- The options-flow “re-pair with new pairing code” field stays empty instead of pre-filling the old stored pairing code; leaving Client adres empty reuses the stored URL for that client.
- Firmware update entity is non-polling. It checks GitHub on add/manual refresh/install and then on a one-hour internal schedule, so HA must not refresh the entity every 10 seconds.
- Firmware channel is a user-facing options-flow dropdown: `stable` uses GitHub `/releases/latest`; `beta` uses the newest prerelease from `pcvantol/djconnect-firmware`. Firmware repo/device remain automatic and hidden.
- Sensor entities are push-only through runtime listeners. `last_command` and `last_track` additionally write HA state only when their cached value or relevant debug attributes actually change.
- Spotify repair OAuth popups use the explicit `authorize` repair external step plus title/description placeholders so Home Assistant does not show a blank dialog when opening the website.
- Strict current ESP device identity is model-specific: `djconnect-lilygo-t-embed-s3-XXXXXXXXXXXX` or `djconnect-esp32-s3-box-3-XXXXXXXXXXXX`; legacy `djconnect-XXXXXXXXXXXX` IDs are not accepted.
- If ESP status/command/voice auth returns `401`, HA must log the received device id, known device id, client type, token-present flag and rejection reason without logging token values.
- HA blocks ESP calls with HTTP `426` `version_mismatch` when HA and ESP firmware `major.minor` differ, while preserving pairing/token state.
- ESP status payloads are merged as partial updates, so sparse heartbeat/status posts do not clear known HA sensor values.
- `/api/djconnect/status` is the only authoritative ESP device-status source. Command, voice, backend playback and local ESP info/command refreshes must never replace the full cached sensor snapshot with empty/unknown values.
- Local ESP `/api/device/command` responses and `/api/device/info` refreshes are merge-only and preserve cached firmware, battery, RSSI, screen/LED, sound output, volume, last track and `ha_pairing_status` when fields are missing or empty.
- Empty Spotify playback snapshots may update backend/playback state, but must not clear cached device sensor fields such as `sound_output`, `volume`, `last_track` or pairing status.
- Command and voice payloads are never authoritative device-status sources; they must not clear sensor values or move `ha_pairing_status` back to `pending` when fields are absent.
- Last-known ESP device status is persisted in config entry data as `last_device_status` and restored on HA reload/startup; never store secrets there.
- `sensor.djconnect_last_track` and `sensor.djconnect_last_command` cache their last non-empty native values at entity level and must not flip to unknown/unavailable because a sparse runtime snapshot omits them.
- ESP status must include `client_type=esp32`; missing client type is surfaced as a visible HA status error.
- Native HA entities include backend playback proxy, queue/up-next, output list, output select, device settings and test/refresh buttons under one HA device. Firmware OTA/update entities are ESP32-only.
- ESP32 clients get ESP-only hardware/update/settings entities: battery, Wi-Fi RSSI, screen state, LED state, screen brightness/timeout, speaker volume, wake word, device language, auto-off, theme/log-level, firmware update and reboot. Wake word reads `settings.wake_word_enabled`, then top-level `wake_word_enabled`, then `wake_word`, and the HA switch sends canonical `{"command":"wake_word","value":true|false}`. iOS, macOS, watchOS and Raspberry Pi clients must not get those ESP-only entities; they keep only client/runtime and backend/playback entities. Raspberry Pi clients additionally get Pi-specific restart and shutdown buttons that call `/api/device/restart` and `/api/device/shutdown`.
- `button.djconnect_refresh_up_next` refreshes Spotify/Home Assistant backend queue data through the `queue` command.
- `command=queue` returns at most 100 real queue items plus top-level `context_uri` / `contextUri` and queue item artwork aliases so ESP/web/app Up Next can use `play_context_at` and show thumbnails.
- `select.djconnect_sound_output` refreshes Spotify output devices itself and accepts `available_outputs`, `outputs`, `devices` and nested `items` aliases.
- Playback proxy exposes album art through `album_image_url`, `media_image_url`, `image_url` and `entity_picture` aliases.
- Voice debug is opt-in via debug logging: when `custom_components.djconnect` debug logging is enabled, HA stores the last raw ESP WAV in memory and exposes it at authenticated URL `/api/djconnect/debug/last_voice.wav`.
- PTT/debug metadata is exposed as attributes on `sensor.djconnect_status`, `sensor.djconnect_last_command` and `sensor.djconnect_last_corrected_stt`, including last STT text, corrected text when changed, Spotify search summary and resolved media metadata.
- Developer Actions use explicit UI field names `command_text` and `dj_response_text`; legacy `text` remains accepted for existing YAML/scripts.
- Developer Actions also register explicit runtime service schemas so Home Assistant Developer Tools keeps the text fields visible after service metadata refreshes.
- If HA Assist treats the DJConnect parsing prompt as a smart-home device command, DJConnect falls back to a simple Spotify search intent instead of raising a websocket script exception.
- `pcvantol/djconnect/SYNC_PROMPTS.md` is the only canonical sync prompt bundle and includes the ESP, HA, Apple app, Raspberry Pi and product website contracts.
- `pcvantol/djconnect/PRODUCT_ROADMAP.md` is the only canonical product roadmap for all DJConnect repos.
- Spotify OAuth callback stores tokens even if an options flow is already closed and `UnknownFlow` occurs.
- Spotify OAuth Repair flow starts an external Spotify OAuth step and does not mark the issue fixed until a new token is stored.
- Backend playback auth failures are returned as user-friendly JSON without forcing ESP pairing reset.
- Device number/select entities accept common firmware status aliases and unit conversions.
- Pairing config-flow browses `_djconnect._tcp` for app-like clients including watchOS and Raspberry Pi. It validates app-like client types against stable IDs such as `djconnect-watchos-XXXXXXXXXXXX` and `djconnect-raspberry-pi-XXXXXXXXXXXX`, accepts TXT `local_url` when present, probes `GET /api/device/pairing-info`, and treats pairing-info as authoritative for Client adres, stable device ID, client type, device name, pair code, version and paired state.
- A single discovered Raspberry Pi client is selected by default but still requires user confirmation. Multiple discovered clients are offered in the `discovered_client` selector.
- Stale/unreachable mDNS clients are hidden from the discovery selector when `/api/device/pairing-info` cannot be reached. Manual Client adres remains the fallback for networks where Bonjour advertises a wrong or blocked URL.
- Raspberry Pi discovery tests now cover TXT acceptance, TXT `local_url`, pairing-info override, stale probe filtering, one-client prefill, multi-client selector, duplicate stable-ID abort behavior and proof that pairing uses the stable discovered Pi device ID instead of `djconnect-{pair_code}`.

## Known Issues / Field Checks

- Validate the Repair “Fix” button in a real HA UI: it should show translated explanatory text and open Spotify OAuth instead of a blank popup or instantly closing.
- Validate options-flow “Spotify opnieuw autoriseren” in a real HA UI.
- Confirm Nabu Casa/external URL is correctly detected or manually editable before OAuth.
- Confirm the Spotify setup step shows the exact redirect URI and requires the user's own Spotify Developer app Client ID.
- Confirm ESP remains paired after first `/api/djconnect/command` following direct pairing.
- Confirm ESP does not clear pairing when Spotify backend is temporarily unavailable.
- Confirm ESP shows update-required state and keeps pairing intact after HA returns `426 version_mismatch`.
- Confirm ESP status payload includes top-level or nested device settings so HA brightness/theme/log-level/speaker-volume entities do not remain unknown/minimum.
- Confirm normal pairing no longer repeats setup method after the first config-flow step.
- Confirm firmware channel is visible/stored only for ESP32 clients and hidden/omitted for iOS, macOS, Apple Watch and Linux/Raspberry Pi clients.
- Confirm physical PTT with selected HA STT provider returns recognized text.
- Confirm HA TTS returns WAV/MP3 or falls back to text-only without crashing.
- Confirm OTA clears updating state after post-boot status.

## Next Tasks

1. Install the latest `3.1.x` release via HACS and restart Home Assistant.
2. Verify the README/HACS banner and `info.md` render the `https://djconnect.dev` link as intended.
3. Update the external product website How To Start page with HACS installation, Spotify Premium requirement, HA Assist pipeline setup, ESP pairing and iOS/macOS/watchOS/Raspberry Pi Client adres steps.
4. Verify `button.djconnect_refresh_up_next` updates `sensor.djconnect_queue` attributes.
5. Verify `select.djconnect_sound_output` populates Spotify outputs without manually calling `devices`.
6. Verify sensors keep last-known values after ESP status, playback command polling, voice tests and local device-info refreshes.
7. Verify `sensor.djconnect_laatste_opdracht` and `sensor.djconnect_laatste_nummer` do not create repeated unchanged history entries during normal runtime refreshes.
8. Verify the firmware update entity does not report a fresh update timestamp every 10 seconds when no firmware/OTA state changed.
9. Test Repair flow for revoked Spotify token.
10. Test options-flow Spotify reauthorize action.
11. Pair a device from scratch and verify token synchronization with required `ha_local_url`.
12. Verify ESP `/status` includes current settings aliases consumed by HA.
13. Run physical PTT end-to-end.
14. Verify native playback proxy media player controls Spotify backend playback and shows album art.
15. Verify no Spotify OAuth secrets are sent to ESP or logged.
16. Pair a Raspberry Pi client from mDNS discovery and verify the form pre-fills Client adres, `client_type=raspberry_pi`, device name, stable device ID and pair code from `/api/device/pairing-info`.
17. Test the Raspberry Pi fallback path by advertising `_djconnect._tcp` while blocking `/api/device/pairing-info`; HA should show the translated pairing-info error and allow manual Client adres correction.
18. Request Nirvana while Spotify currently reports another artist such as Red Hot Chili Peppers and confirm the DJ announcement prompt/media context uses Nirvana.

## Validation Commands

```sh
python3 -m json.tool custom_components/djconnect/strings.json >/tmp/djconnect_strings.json
python3 -m json.tool custom_components/djconnect/translations/en.json >/tmp/djconnect_en.json
python3 -m json.tool custom_components/djconnect/translations/nl.json >/tmp/djconnect_nl.json
python3 -m py_compile custom_components/djconnect/*.py tests/*.py
python3 -m unittest discover -s tests
```
