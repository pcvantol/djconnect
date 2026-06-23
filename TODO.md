# DJConnect TODO Backlog

## Immediate Validation

- Install the latest HACS release in Home Assistant.
- Restart Home Assistant after installation.
- Open DJConnect options flow and confirm there is no internal server error.
- Before release/build validation, check for updates to third-party libraries, frameworks and build tools; when versions are upgraded, update `THIRD_PARTY_NOTICES.md` and dependency/design documentation, or document skipped upgrades in `HANDOFF.md`.
- Confirm `TECHNICAL_DESIGN_DECISIONS.md` remains current when code patterns, dependencies, licenses or external APIs change.
- Confirm existing paired device remains paired after HA restart when ESP reports `ha_pairing_status=paired`.
- Confirm iOS/macOS/watchOS/Raspberry Pi paired clients do not show active/available firmware OTA or ESP reboot entities; Raspberry Pi should show only Pi restart/shutdown power buttons.
- Confirm iOS/macOS/watchOS/Raspberry Pi PTT requests do not create a false Spotify refresh-token repair after the first DJ announcement.
- Confirm HA shows pairing `pending` and retries `/api/device/pair` when a local token exists but ESP has not confirmed pairing.
- Confirm ESP `/status` updates persist the real `djconnect-XXXXXXXXXXXX` device id.
- Confirm ESP `/status` updates persist the real `local_url` when provided.
- Confirm old setup-code entries stop using `djconnect-[6-digit-code].local` after status repair.

## PTT / Voice

- Test physical PTT end-to-end on the ESP device.
- Confirm ESP uploads raw WAV to `POST /api/djconnect/voice`.
- Confirm HA logs selected Assist pipeline/STT provider metadata without secrets.
- Confirm HA logs WAV metadata: sample rate, channel count, sample width and byte length.
- Confirm selected HA STT provider accepts the WAV metadata.
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
- Confirm the DJConnect conversation-agent options dialog only shows the action selector and smart-home context allowlist; DJ response style/prompt controls must stay removed because announcements follow runtime mood/default style.
- Confirm successful DJ announcement TTS creates an `audio_url` using a local Home Assistant URL even when older HA network helpers are unavailable.
- Confirm Dutch DJ announcements pronounce English artist, album and track names naturally in TTS.
- Confirm a new PTT request such as Nirvana does not reuse previous Spotify playback metadata such as Red Hot Chili Peppers in the DJ aankondiging.
- Confirm artist requests that start a concrete Spotify track include that returned track in the generative DJ aankondiging prompt.
- Confirm Ask DJ output/speaker questions render a text list plus `Activeer` actions without old album art.
- Confirm Ask DJ album-list questions render album bullets plus direct Play Now album actions.
- Confirm `Probeer opnieuw` replays the previous retryable playback request and keeps the visible retry bubble in client history.
- Confirm `stop muziek` shows a Resume action and `hervat muziek` starts playback directly.
- Confirm repeated iOS/macOS/watchOS/Raspberry Pi PTT requests reuse or serialize Spotify token refresh without false `invalid_grant` repairs.
- Confirm artist queue/up-next selection does not send invalid Spotify artist offset payloads.
- Confirm friendly DJ fallback response is returned when Spotify playback fails.
- Confirm DJ fallback response follows `device_language` (`nl` or `en`).
- Confirm ESP receives and plays WAV/MP3 `audio_url` when HA TTS generates supported audio.
- Confirm ESP handles text-only DJ aankondiging if HA TTS output is unsupported.

## Spotify Provisioning

- Verify Spotify OAuth still completes through HA external step.
- Verify OAuth scopes include `playlist-read-private`.
- Verify OAuth callback stores latest `spotify_refresh_token` persistently.
- Verify concurrent Spotify API calls after HA restart do not refresh the same old token in parallel.
- Verify stale runtime refresh tokens retry the newer config-entry token before creating a Spotify Repair issue.
- Verify Spotify debug logs show access-token expiry/refresh metadata and refresh-token source names without token values.
- Verify status payload with `spotify_configured=false` does not return Spotify credentials.
- Verify Spotify OAuth credentials stay in Home Assistant and are not sent to ESP.
- Verify no Spotify refresh token value appears in logs or diagnostics.

## Pairing / Discovery

- Test pairing with a fresh ESP in setup mode.
- Test captive-portal WiFi setup followed by BLE screen action `Continue to pairing`.
- Test BLE screen action `Rescan Bluetooth devices`.
- Test BLE screen action `Write WiFi over Bluetooth`.
- Test pairing with Client adres left empty for ESP devices.
- Test pairing with iOS/macOS/watchOS/Raspberry Pi Client adres copied from client Settings.
- Test mDNS discovery through `_djconnect._tcp` for ESP32, iOS, macOS, watchOS and Raspberry Pi.
- Test Raspberry Pi mDNS TXT discovery with `client_type=raspberry_pi`, stable `djconnect-raspberry-pi-XXXXXXXXXXXX` ID and TXT `local_url`.
- Test Raspberry Pi `/api/device/pairing-info` override for Client adres, client type, device name, device ID, pair code, version and paired state.
- Test Raspberry Pi pairing-info failure: Home Assistant should show the translated pairing-info reachability error and allow manual Client adres correction.
- Test duplicate Raspberry Pi discovery: a previously configured stable Pi device ID should not create a second setup-code-based HA entry.
- Test mDNS single-device fallback when only one DJConnect device is visible.
- Test Client adres fallback on a network where mDNS fails.
- Confirm invalid pairing code is rejected with a clear user message.
- Confirm real device id and local URL are persisted after `/pair`.
- Confirm real device id and local URL are persisted after `/status`.

## Config Flow / Options Flow

- Confirm normal config flow stays small and user-focused.
- Confirm Add integration shows a clear Assist pipeline prerequisite error when Home Assistant has no Assist pipeline with both STT and TTS.
- Confirm setup method is shown only in the first Add integration step and not repeated in normal pairing.
- Confirm `client_type` and Client adres are visible in normal pairing, with client type choices ordered iOS, macOS, Apple Watch, Linux/Raspberry Pi and ESP32.
- Confirm standalone `stt_engine`, `tts_engine`, `tts_language` and `tts_voice` fields remain hidden; STT/TTS is managed through Home Assistant Assist.
- Confirm internal compatibility/OTA/audio TTL defaults are no longer exposed in config/options flow.
- Confirm firmware channel is visible and stored only for ESP32 clients, not for iOS, macOS, Apple Watch or Linux/Raspberry Pi clients.
- Confirm Spotify setup requires a user-owned Spotify Developer app Client ID and shows the exact redirect URI to register.
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
- Verify firmware channel and firmware OTA update entity are not added and remain unavailable for `client_type=ios`, `client_type=macos` and `client_type=raspberry_pi`.
- Verify ESP reboot entity is not added for `client_type=ios`, `client_type=macos` and `client_type=raspberry_pi`; verify Raspberry Pi restart/shutdown entities are added only for `client_type=raspberry_pi`.

## Developer Services

- Test `djconnect.test_parse`.
- Test `djconnect.test_command` with `play: false`.
- Test `djconnect.test_command` with `play: true`.
- Test `djconnect.test_ptt_text` with a natural-language post-STT sentence and confirm Spotify playback plus DJ aankondiging text/audio delivery.
- Test `djconnect.test_tts` and confirm response is sent to ESP, not HA media player.
- Test Spotify backend playback after OAuth refresh-token rotation.
- Test Spotify backend playback with simultaneous status/play/queue calls after OAuth refresh-token rotation.
- Update service documentation if any response payload changes.

## Ask DJ

- Confirm Ask DJ server history trims at 1000 messages per HA user, returns `history_limit`, `history_trimmed_before` and `history_trimmed_count`, and appends one `history_retention` system message without audio.
- Confirm iOS, macOS and watchOS remove local chat messages older than `history_trimmed_before` after the next history sync.
- Confirm `POST /api/djconnect/ask_dj/history/clear` still increments `clear_revision` and clears local cache across iOS, macOS and watchOS.
- Confirm `Goedemorgen` returns a personalized morning suggestion with Ja/Nee controls and does not start playback until the user confirms.
- Confirm `ask_dj_followup_response` executes a pending Yes action, declines a No action and returns a friendly expired/no-pending message after the pending follow-up TTL.
- Confirm follow-up confirmation buttons work cross-device, for example Ask DJ asks on iPhone and the user answers on macOS or Apple Watch.
- Confirm obvious gibberish and sandbox/prompt-injection-like prompts return the neutral unknown-intent fallback and do not trigger Spotify search, HA device lookup, prompt disclosure or playback mutation.
- Confirm Play Now and recommendation flows still store only compact positive signals in DJ Memory and never raw prompts, bearer tokens, OAuth tokens or raw audio.
- Confirm recent-played Ask DJ questions for tracks, albums, artists and playlists render as compact item lists with art/icons and do not mutate playback or invent Play Now buttons.
- Confirm Watch/iOS mood values map to the canonical DJConnect zones: Chill `0`-`24`, Groove `25`-`59`, Energy `60`-`84` and Party `85`-`100`.
- Confirm smart-home-aware Ask DJ prompts only include explicitly shared `smart_home_context_entities`, never arbitrary HA states, and still require Ja/Nee confirmation before playback starts.

## Security / Privacy

- Re-run diagnostics and confirm redaction for keys containing `token`, `password` or `secret`.
- Confirm no device token, HA token, Spotify refresh token or WiFi password appears in logs.
- Confirm BLE provisioning only sends WiFi SSID/password.
- Confirm no Spotify/device credentials are sent via BLE.
- Confirm `THIRD_PARTY_NOTICES.md` remains accurate after dependency changes.

## Documentation

- Update `README.md` after any architecture/API change.
- Update `AGENTS.md` after any durable project decision.
- Keep `DEVELOPMENT_ENVIRONMENT.md` current when local HA Docker paths, sync commands, restart flow or manual validation workflow changes.
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
- Maintain a How To Start page covering HACS install, Spotify Premium, HA Assist pipeline STT/TTS setup, Spotify OAuth, ESP pairing and iOS/macOS/watchOS/Raspberry Pi Client adres pairing.
- Add real product photos/screenshots when final hardware imagery is available.
- Keep requirements clear: Spotify Premium, Home Assistant, HACS, HA Assist pipeline, 2.4 GHz WiFi and mDNS/Nabu Casa recommendations.
- Keep `PRODUCT_ROADMAP_IDEAS.md` current when adding product ideas, killer features, production must-haves or premium feature concepts.

## Release Workflow

- Run `python3 -m unittest discover -s tests` before release.
- Run `./release.sh X.Y.Z --dry-run` before publishing when changes are non-trivial.
- Run `./release.sh X.Y.Z` for release.
- Refresh HACS update info in Home Assistant.
- Install new release from HACS.
- Restart Home Assistant.
- Run `./cleanup_old_releases.sh --keep 1 --execute` after successful release unless multiple releases are intentionally retained for support/testing.
- Clean up old completed GitHub Actions workflow runs after every release, keeping only the newest release/tag validation and newest `main` validation unless debugging requires more history.
- Keep the CI Postman collection validator aligned with `examples/djconnect.postman_collection.json` whenever API examples change.
