# DJConnect TODO Backlog

## Immediate Validation

- Install the latest HACS release in Home Assistant.
- Restart Home Assistant after installation.
- Open DJConnect options flow and confirm there is no internal server error.
- Before release/build validation, check for updates to third-party libraries, frameworks and build tools; when versions are upgraded, update `THIRD_PARTY_NOTICES.md` and dependency/design documentation, or document skipped upgrades in `HANDOFF.md`.
- Confirm `TECHNICAL_DESIGN_DECISIONS.md` remains current when code patterns, dependencies, licenses or external APIs change.
- Confirm existing paired device remains paired after HA restart when ESP reports `ha_pairing_status=paired`.
- Confirm iOS/macOS/watchOS/Raspberry Pi/Windows paired clients do not show active/available firmware OTA or ESP reboot entities; Raspberry Pi should show only Pi restart/shutdown power buttons.
- Confirm iOS/macOS/watchOS/Raspberry Pi/Windows PTT requests do not create a false Spotify refresh-token repair after the first DJ announcement.
- Confirm HA shows pairing `pending` and retries `/api/device/pair` when a local token exists but ESP has not confirmed pairing.
- Confirm ESP `/status` updates persist the real `djconnect-XXXXXXXXXXXX` device id.
- Confirm ESP `/status` updates persist the real `local_url` when provided.
- Confirm old setup-code entries stop using `djconnect-[6-digit-code].local` after status repair.
- Monitor `/api/djconnect/command`, Ask DJ playback actions, voice processor
  playback and HA playback entities through the DJConnect use-case layer.
  Automated coverage now verifies the shared use-case transport and response
  shapes; field testing should focus on real HA/client rendering.
- Confirm Music Assistant setup on a real HA instance: backend choice skips
  Spotify OAuth, lists usable MA players, stores the selected player, controls
  play/pause/next/previous/volume through HA `media_player` services and keeps
  Spotify repairs quiet. Automated config/options validation now rejects stale,
  missing and non-Music-Assistant `media_player` entities.
- Monitor Music Assistant unsupported capabilities in clients:
  recent-played, top items, recommendations, favorites, advanced queue/library
  profile and Spotify-specific Play Now actions should not show stale artwork,
  scope repair text or phantom controls. Automated backend/config/action-shape
  coverage exists; real Music Assistant client rendering still needs field
  validation.
- Ask DJ profile/recommendation action shaping has been moved further behind
  backend-aware action metadata. Continue monitoring lower-level Spotify Direct
  informational helpers, but do not treat generic Music Assistant playback
  actions as blocked by Spotify URI assumptions.
- Keep backend choice explicit as `Spotify Direct` or `Music Assistant`; do not
  add Auto mode or a large Music Assistant setup flow unless a later product
  decision changes the contract.
- Field-test the options-flow `Muziekbackend wijzigen` action in Home
  Assistant: switching should preserve pairing/device token/history/memory,
  bump `music_backend_revision`, hide Spotify reauthorize while Music Assistant
  is active and mark old backend-specific Ask DJ actions stale.
- Field-test client rendering of backend-aware `playback_actions[]`, stale
  action rejection and `unsupported_backend_capability` errors on both Spotify
  Direct and Music Assistant.
- Live-test the local websocket fast path against Home Assistant before
  enabling it as a product default in Windows or other clients. Cover command,
  Ask DJ message/history/clear/state/idle-suggestion, Track Insight and Music
  DNA profile/settings/clear. Confirm whether the HA websocket auth flow
  requires a separate HA token; do not assume the DJConnect device token
  authenticates `/api/websocket`.

## PTT / Voice

- Test physical PTT end-to-end on the ESP device.
- Confirm ESP uploads raw WAV to `POST /api/djconnect/voice`.
- Confirm HA logs selected Assist pipeline/STT provider metadata without secrets.
- Confirm HA logs WAV metadata: sample rate, channel count, sample width and byte length.
- Confirm selected HA STT provider accepts the WAV metadata on the target HA
  instance. Automated coverage now exercises both HA STT provider object paths,
  including `async_get_speech_to_text_engine(...).async_process_audio_stream(...)`.
- Confirm recognized text reaches DJConnect command processing.
- Confirm the guarded post-STT fuzzy-correction step improves common English artist/track/album names in Dutch sentences without changing correct transcripts.
- Confirm `sensor.djconnect_last_corrected_stt` shows the last changed STT correction and remains stable after sparse runtime updates.
- Confirm Spotify playback action runs when Spotify is idle.
- Confirm current-track questions such as `Welk nummer draait er nu?` return a DJ response without starting new Spotify playback, including no-track and Spotify-unavailable cases.
- Confirm direct playback controls `Stop muziek`, `Start muziek`, `Zet harder`, `Zet zachter`, `Volgende nummer` and `Vorig nummer` execute backend commands without Spotify search and return DJ responses.
- Confirm English direct controls such as `next` and `skip` execute immediately even when the configured/UI language is Dutch.
- Confirm lifecycle phrases such as `Ik ga slapen` pause playback directly and return the localized DJ response.
- Confirm PTT artist, track, album, playlist and default-playlist phrases resolve to the intended Spotify search type.
- Confirm AI DJ announcements use the selected/default HA Assist conversation engine when no DJConnect Assist pipeline is explicitly selected.
- Confirm Voice Preview Edition can select the `DJConnect DJ` conversation agent and receives the generated DJ response through its speaker.
- Confirm initial setup can create an Assist Conversation Agent-only entry without a DJConnect client pairing code.
- Confirm the DJConnect conversation-agent options dialog only shows the action selector; DJ response style/prompt controls must stay removed because announcements follow runtime mood/default style.
- Confirm successful DJ announcement TTS creates an `audio_url` using a local
  Home Assistant URL even when older HA network helpers are unavailable.
  Automated coverage now exercises keyword and positional HA TTS media-source
  generator signatures.
- Confirm Dutch DJ announcements pronounce English artist, album and track names naturally in TTS.
- Confirm a new PTT request such as Nirvana does not reuse previous Spotify playback metadata such as Red Hot Chili Peppers in the DJ aankondiging.
- Confirm artist requests that start a concrete Spotify track include that returned track in the generative DJ aankondiging prompt.
- Confirm Ask DJ output/speaker questions render a text list plus `Activeer` actions without old album art.
- Confirm Ask DJ album-list questions render album bullets plus direct Play Now album actions.
- Confirm `Probeer opnieuw` replays the previous retryable playback request and keeps the visible retry bubble in client history.
- Confirm `stop muziek` shows a Resume action and `hervat muziek` starts playback directly.
- Confirm repeated iOS/macOS/watchOS/Raspberry Pi/Windows PTT requests reuse or serialize Spotify token refresh without false `invalid_grant` repairs.
- Confirm artist queue/up-next selection does not send invalid Spotify artist
  offset payloads. Automated regression coverage exists in
  `tests.test_ask_dj` / `tests.test_spotify_backend`.
- Confirm queue/up-next returns at most 100 real backend items, skipping empty
  backend entries instead of counting them against the limit. Automated
  regression coverage exists in `tests.test_spotify_backend`.
- Confirm friendly DJ fallback response is returned when Spotify playback fails.
- Confirm DJ fallback response follows `device_language` (`nl` or `en`).
- Confirm ESP receives and plays WAV/MP3 `audio_url` when HA TTS generates supported audio.
- Confirm ESP handles text-only DJ aankondiging if HA TTS output is unsupported.

## Spotify Provisioning

- Verify Spotify OAuth still completes through HA external step.
- Verify OAuth scopes include `playlist-read-private`.
- Verify OAuth callback stores latest `spotify_refresh_token` persistently.
- Verify concurrent Spotify API calls after HA restart do not refresh the same old token in parallel.
- Verify stale runtime refresh tokens retry newer config-entry data/options
  tokens before creating a Spotify Repair issue. Automated regression coverage
  exists in `tests.test_spotify_backend`.
- Verify refresh endpoint rotations persist to config entry data even when
  runtime memory already holds the rotated token. Automated regression coverage
  exists in `tests.test_spotify_backend`.
- Verify Spotify debug logs show access-token expiry/refresh metadata and refresh-token source names without token values.
- Verify status payload with `spotify_configured=false` does not return Spotify credentials.
- Verify Spotify OAuth credentials stay in Home Assistant and are not sent to ESP.
- Verify no Spotify refresh token value appears in logs or diagnostics.

## Pairing / Discovery

- Test pairing with a fresh ESP in setup mode.
- Test captive-portal WiFi setup followed by BLE screen action `Continue to pairing`.
- Test BLE screen action `Rescan Bluetooth devices`.
- Test BLE screen action `Write WiFi over Bluetooth`.
- Test local-device pairing with Client adres left empty for ESP32/Raspberry Pi.
- Field-test iPhone/iPad, Apple Watch, macOS and Windows app pairing with no Client adres, where the app
  posts locally to `/api/djconnect/pair` and receives optional `ha_remote_url`;
  use `FIELD_TEST_APP_CLIENTS.md` and record the app build/HA version/backend.
  Automated HA contract coverage now verifies inbound pair responses and remote
  playback commands for iOS, macOS and Windows client IDs.
- Field-test mDNS discovery through `_djconnect._tcp` for ESP32, iOS, macOS,
  watchOS, Raspberry Pi and Windows. Automated discovery helper coverage now
  validates stable client-type/device-id matching for these client families.
- Field-test Raspberry Pi mDNS TXT discovery with `client_type=raspberry_pi`,
  stable `djconnect-raspberry-pi-XXXXXXXXXXXX` ID and TXT `local_url`.
  Automated coverage validates TXT parsing.
- Field-test Raspberry Pi `/api/device/pairing-info` override for Client adres,
  client type, device name, device ID, pair code, version and paired state.
  Automated coverage validates the merge/override behavior.
- Field-test Raspberry Pi pairing-info failure on a real network. Automated
  coverage now keeps the mDNS-visible Pi as a marked discovery choice and
  verifies the manual-correction error path.
- Monitor duplicate Raspberry Pi discovery: automated config-flow coverage
  verifies stable Pi IDs do not create setup-code-only duplicate entries.
- Test mDNS single-device fallback when only one DJConnect device is visible.
- Test Client adres fallback on a network where mDNS fails.
- Confirm invalid pairing code is rejected with a clear user message.
- Confirm real device id and local URL are persisted after `/pair`.
- Confirm real device id and local URL are persisted after `/status`.

## Config Flow / Options Flow

- Confirm normal config flow stays small and user-focused.
- Confirm Add integration shows a clear Assist pipeline prerequisite error when Home Assistant has no Assist pipeline with both STT and TTS.
- Confirm setup method is shown only in the first Add integration step and not repeated in normal pairing.
- Confirm app pairing hides Client adres, first offers iPhone/iPad, Apple Watch,
  macOS and Windows, and only then shows client-specific details; confirm
  local-device pairing keeps Client adres fallback and offers ESP32 and
  Raspberry Pi.
- Confirm standalone `stt_engine`, `tts_engine`, `tts_language` and `tts_voice` fields remain hidden; STT/TTS is managed through Home Assistant Assist.
- Confirm internal compatibility/OTA/audio TTL defaults are no longer exposed in config/options flow.
- Confirm firmware channel is visible and stored only for ESP32 clients, not for iOS, macOS, Apple Watch, Linux/Raspberry Pi or Windows clients.
- Confirm Spotify setup requires a user-owned Spotify Developer app Client ID and shows the exact redirect URI to register.
- Confirm Music Assistant setup never asks for Spotify Client ID, never opens
  Spotify OAuth and shows translated errors for unavailable MA or missing
  players.
- Confirm no `spotify_player` field is required in config/options flow.
- Confirm ESP32-only Wake word switch appears only for ESP32 clients and tracks `settings.wake_word_enabled` after ESP reboot/status refresh.
- Confirm all titles, labels and error messages are available in Dutch and English.

## OTA / Firmware Updates

- Verify firmware release discovery from `pcvantol/djconnect-firmware`.
- Verify `firmware_manifest.json` is parsed even if GitHub serves it as `application/octet-stream`.
- Verify update entity displays firmware asset, manifest URL, target device, sha256 and min HA integration.
- Verify OTA payload sends manifest `device`, currently `lilygo-t-embed-s3`.
- Verify ESP no longer rejects OTA with `Wrong device target`.
- Verify OTA errors are shown clearly in HA.
- Verify firmware channel and firmware OTA update entity are not added and remain unavailable for `client_type=ios`, `client_type=macos`, `client_type=watchos`, `client_type=raspberry_pi` and `client_type=windows`.
- Verify ESP reboot entity is not added for `client_type=ios`, `client_type=macos`, `client_type=watchos`, `client_type=raspberry_pi` and `client_type=windows`; verify Raspberry Pi restart/shutdown entities are added only for `client_type=raspberry_pi`.

## Developer Services

- Test `djconnect.test_parse`.
- Test `djconnect.test_command` with `play: false`.
- Test `djconnect.test_command` with `play: true`.
- Test `djconnect.test_ptt_text` with a natural-language post-STT sentence and confirm Spotify playback plus DJ aankondiging text/audio delivery.
- Test `djconnect.test_apns_push` with `send:false` and `send:true` on iOS,
  macOS and watchOS. Confirm the response shows `central_api_configured`,
  `install_token_present`, `bootstrap_proof_present`, `decision`,
  `push_statuses`, `sent` and an actionable `error`, while never exposing APNs
  tokens, bearer tokens, bootstrap proofs or `djci_` token values.
- Test `djconnect.test_tts` and confirm response is sent to ESP, not HA media player.
- Test Spotify backend playback after OAuth refresh-token rotation.
- Test Spotify backend playback with simultaneous status/play/queue calls after OAuth refresh-token rotation.
- Update service documentation if any response payload changes.

## Ask DJ

- Monitor Ask DJ server history trimming at 1000 messages per HA user. Automated
  coverage verifies `history_limit`, `history_trimmed_before`,
  `history_trimmed_count` and retention system-message behavior; client field
  testing should verify local cache pruning UX.
- Confirm iOS, macOS and watchOS remove local chat messages older than `history_trimmed_before` after the next history sync.
- Monitor Ask DJ history clear sync. Automated HTTP/websocket coverage verifies
  `clear_revision`/`history_revision`; iOS, macOS, watchOS, Raspberry Pi and
  Windows still need local-cache field validation.
- Monitor `Goedemorgen` personalized morning suggestions. Automated coverage
  verifies Ja/Nee controls and no direct playback; field testing should verify
  button rendering and push/sync UX.
- Monitor `ask_dj_followup_response` pending-action behavior. Automated coverage
  verifies Yes/No/no-pending paths; field testing should focus on cross-device
  timing and expired pending follow-ups.
- Confirm follow-up confirmation buttons work cross-device, for example Ask DJ asks on iPhone/iPad and the user answers on macOS or Apple Watch.
- Confirm Ask DJ playback requests with no active Spotify output return speaker `playback_actions[]` and that `ask_dj_play_request_on_output` sets the selected output before replaying the original request.
- Monitor obvious gibberish and sandbox/prompt-injection-like prompts. Automated
  coverage verifies neutral fallback without Spotify search, HA device lookup,
  prompt disclosure or playback mutation.
- Confirm Play Now and recommendation flows still store only compact positive signals in Music DNA and never raw prompts, bearer tokens, OAuth tokens or raw audio.
- Monitor recent-played Ask DJ questions for tracks, albums, artists and
  playlists. Automated coverage verifies compact item payloads and no playback
  mutation; app clients still need rendering field validation.
- Confirm Watch/iOS mood values map to the canonical DJConnect zones: Chill `0`-`24`, Groove `25`-`59`, Energy `60`-`84` and Party `85`-`100`.

## Security / Privacy

- Re-run diagnostics and confirm redaction for keys containing `token`,
  `password`, `secret`, `proof`, `authorization`, `prompt`, `history`,
  `memory` or `raw_audio`.
- Confirm no device token, HA token, Spotify refresh token, WiFi password, raw
  prompt, raw audio, Ask DJ history or Music DNA dump appears in logs.
- Confirm BLE provisioning only sends WiFi SSID/password.
- Confirm no Spotify/device credentials are sent via BLE.
- Confirm `THIRD_PARTY_NOTICES.md` remains accurate after dependency changes.

## Documentation

- Update `README.md` after any architecture/API change.
- Update `AGENTS.md` after any durable project decision.
- Keep `DEVELOPMENT_ENVIRONMENT.md` current when local HA Docker paths, sync commands, restart flow, ngrok tunnel setup, Home Assistant network URL/proxy config or manual validation workflow changes.
- Keep `CHANGELOG.md` as a per-release changelog. Add a new section for each release and keep previous release sections.
- Keep `HANDOFF.md` current after major debugging sessions.
- Keep `TODO.md` and `ISSUES.md` current after field testing.
- Keep `VOICE_INTENT_DATA.md` aligned with `examples/voice_intents.json` and processor/music parser behavior.
- Before every release, review all documentation files in this repo: `README.md`, `CHANGELOG.md`, `AGENTS.md`, `HANDOFF.md`, `TODO.md`, `ISSUES.md`, `SYNC_PROMPTS.md`, `PRODUCT_ROADMAP.md`, `TECHNICAL_DESIGN_DECISIONS.md`, `CHAT_BOOTSTRAP.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `info.md` and relevant `examples/*`.
- Before every release, explicitly check whether tests need to be expanded for the change; add coverage for new behavior paths, regression risks, translations and edge cases.
- Keep cross-repo sync prompts only in `pcvantol/djconnect/SYNC_PROMPTS.md`; do not re-add retired loose prompt files or sibling-repo copies.
- Keep product roadmap only in `pcvantol/djconnect/PRODUCT_ROADMAP.md`; do not re-add sibling-repo roadmap copies.
- Document known HA restart requirement after HACS custom integration updates.

## Website / Marketing

- Keep product/marketing website work in the external website location, not this HA integration repo.
- Keep the public website link visible in HACS-facing docs: `https://djconnect.dev`.
- Maintain a How To Start page covering HACS install, Spotify Premium, HA Assist pipeline STT/TTS setup, Spotify OAuth, ESP/Raspberry Pi local-device pairing and iPhone/iPad, Apple Watch, macOS and Windows inbound app pairing.
- Add real product photos/screenshots when final hardware imagery is available.
- Keep requirements clear: Spotify Premium, Home Assistant, HACS, HA Assist pipeline, 2.4 GHz WiFi and mDNS/Nabu Casa recommendations.
- Keep `PRODUCT_ROADMAP_IDEAS.md` current when adding product ideas, killer features, production must-haves or premium feature concepts.

## Release Workflow

- Run `python3 -m unittest tests.test_ask_dj_e2e_contract`, the Ask DJ no-active-output regressions and `python3 -m unittest discover -s tests` before release.
- Run `./release.sh X.Y.Z --dry-run` before publishing when changes are non-trivial.
- Run `./release.sh X.Y.Z` for release.
- Keep branch-protection/admin override manual and explicit; do not automate
  required-review disablement or protection changes in `release.sh`.
- Refresh HACS update info in Home Assistant.
- Install new release from HACS.
- Restart Home Assistant.
- Release/tag cleanup after v3.2.5 is done; `./cleanup_old_releases.sh --keep 1 --execute` should keep only `v3.2.5` when cleanup is run for this release line.
- Clean up old completed GitHub Actions workflow runs after every release, keeping only the newest release/tag validation and newest `main` validation unless debugging requires more history.
- Keep the CI Postman collection validator aligned with `examples/djconnect.postman_collection.json` whenever API examples change.
