# DJConnect Chat Bootstrap Prompt

Use this prompt to initialize a fresh AI/Codex chat for this repository.

```text
Werk in repo `/Users/pcvantol/Documents/GitHub/djconnect`.

Lees eerst:
- `AGENTS.md`
- `HANDOFF.md`
- `README.md`
- `CHANGELOG.md`
- `TODO.md`
- `ISSUES.md`
- `SYNC_PROMPTS.md`
- `PRODUCT_ROADMAP.md`
- `TECHNICAL_DESIGN_DECISIONS.md`
- `API_CONTRACT.md`
- `VOICE_INTENT_DATA.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `DEVELOPMENT_ENVIRONMENT.md`
- `info.md`

Belangrijke huidige status:
- Project: DJConnect Home Assistant custom integration, domain `djconnect`.
- Laatste release: `3.2.41`.
- Repo is public en MIT-licensed.
- Alle DJConnect repos zijn MIT-licensed, tenzij een specifieke third-party dependency anders vermeldt.
- `FIRMWARE-LICENSE.md` is verwijderd.
- Community/security docs staan in `CODE_OF_CONDUCT.md` en `SECURITY.md`; security contact is `security@djconnect.dev`.
- DJConnect wordt ontwikkeld en onderhouden met AI-assisted/agentic engineering workflows, inclusief Codex; accepted changes blijven maintainer-reviewed en prompts/logs/issues mogen geen secrets of private data bevatten.
- Fresh-chat promptbestanden heten in alle DJConnect repos `CHAT_BOOTSTRAP.md`.
- HACS/HA integration repo: `pcvantol/djconnect`.
- Firmware repo/source en client repos zijn aparte MIT repos.
- Home Assistant integration blijft verantwoordelijk voor pairing, Spotify OAuth/backend playback, Assist/STT/TTS, OTA, status en diagnostics.
- ESP/app clients bewaren geen Spotify credentials.
- Spotify OAuth gebruikt PKCE met een door de gebruiker aangemaakte Spotify Developer app; setup vraagt om `spotify_client_id` en toont de exacte redirect URI die in Spotify Developer Dashboard geregistreerd moet worden.
- Actieve voice routes gebruiken Home Assistant Assist/TTS, geen directe externe AI/STT/TTS APIs.
- DJConnect exposeert een Home Assistant conversation agent met vaste naam `DJConnect DJ`.
- Initial setup heeft nu 4 opties:
  - `Assist Conversation Agent` zonder client-koppelcode/device token/Client adres.
  - `DJConnect lokaal device koppelen` voor ESP32/Raspberry Pi LAN-only met mDNS en optioneel Client adres fallback;
  - `DJConnect app koppelen` voor iPhone/iPad, Apple Watch, macOS en Windows inbound-only pairing zonder Client adres, met optionele `ha_remote_url` na lokale pairing;
  - `ESP32 device WiFi configureren (via Bluetooth)`.
- ESP32 en Raspberry Pi blijven local-only; iOS, macOS en Windows zijn remote-capable na lokale pairing; watchOS loopt via iPhone/iPad proxy en krijgt geen eigen HA-direct pairingcontract.
- `/api/device/*` is alleen voor ESP32/Raspberry Pi lokale device API. App clients bellen HA via `/api/djconnect/v1/...`; HA probeert app clients niet lokaal terug te bellen.
- De `3.2.x` lijn introduceert `custom_components/djconnect/use_cases.py` als dunne DJConnect use-case laag met `MusicBackend` capabilities. Spotify Direct is de default backend-adapter. Music Assistant is beschikbaar als kleine adapter via een gekozen HA `media_player`, niet als DJConnect-side provider registry, library index, queue engine, grouping/sync engine of Music Assistant light.
- Config-flow kiest nu expliciet `Spotify Direct` of `Music Assistant`, zonder Auto. Spotify Direct gebruikt DJConnect PKCE OAuth en Spotify repairs. Music Assistant vereist geen DJConnect Spotify Client ID/OAuth; Music Assistant beheert provider-auth, DJConnect valideert dat MA beschikbaar is en bewaart de gekozen target player.
- Options-flow heeft expliciet `Muziekbackend wijzigen` / `Change music backend`: wisselen bewaart pairing, device tokens, Ask DJ history, Music DNA en pushregistraties, verhoogt `music_backend_revision`, verbergt Spotify reauthorize bij actieve Music Assistant en maakt oude backend-specifieke pending playback actions stale.
- Pair/status/command responses bevatten backend summary velden: `music_backend`, `music_backend_name`, `music_backend_available`, `music_backend_revision`, `music_backend_capabilities`, `music_target_player` en veilige `music_backend_error`. `playback_actions[]` zijn backend-aware met backend/provider/revision; stale actions geven `stale_backend_action`, unsupported backend features geven `unsupported_backend_capability`.
- Spotify/Music Assistant playback state blijft intern voor DJConnect commands,
  Ask DJ en clients. De HA integration maakt geen losse backend playback
  entities meer aan voor Spotify status, playback availability, queue,
  playlists, outputs, volume, sound output, repeat of shuffle; oude registry
  entries worden bij setup opgeruimd.
- Lokale app-clients kunnen optioneel de Home Assistant native websocket API
  gebruiken als fast path met `djconnect/capabilities` en
  `djconnect/command`, Ask DJ message/history/clear/state/idle-suggestion,
  `djconnect/track_insight` en
  `djconnect/music_dna/{profile,settings,clear}`. Dit hergebruikt exact de
  equivalente HTTP contracten inclusief DJConnect device token, `device_id` en
  canoniek `client_type`; HTTP blijft canonical fallback voor remote access,
  pairing, voice uploads, image/TTS URLs, Music DNA import/export en alle
  websocket failures/timeouts.
- Ask DJ Play Now backend metadata loopt via de use-case laag; nieuwe response
  shaping moet backend/provider/revision/value velden daarvandaan halen en niet
  opnieuw Spotify-specifiek in Ask DJ opbouwen.
- Music DNA is first-class en expliciet opt-in. Clients gebruiken
  `POST /api/djconnect/v1/music_dna/profile`, `/settings`, `/clear` en HTTP-only
  `/export`/`/import` voor structured profile data, opt-in/out, wissen en
  backend-gestuurde JSON export/import. Zolang Music DNA disabled is, bouwt HA
  geen nieuwe kennis op uit Ask DJ, listening profiles, recente tracks of
  voorkeuren en import geeft HTTP `409` `music_dna_not_enabled`. Clear behoudt
  de opt-in setting; als enabled waar blijft, begint kennisopbouw daarna
  opnieuw vanaf leeg.
- Diagnostics tonen `music_backend.selected` en capability flags. Voor Music Assistant staat `spotify_oauth.required=false` en worden Spotify OAuth/reauthorization repairs niet aangemaakt.
- Diagnostics/logs redacteren key aliases met `token`, `password`, `secret`,
  `proof`, `authorization`, `prompt`, `history`, `memory` of `raw_audio`; raw
  prompts, raw audio, Ask DJ history en Music DNA dumps mogen niet in logs of
  diagnostics terechtkomen.
- Nieuwe playback/control code mag niet rechtstreeks Spotify helpers aanroepen buiten de backend-adapter; routeer via de use-case laag.
- De `3.2.18` release voegt de premium-ready VibeCast backend feed toe via
  `GET /api/djconnect/v1/vibecast`, met expliciete macOS/iOS parity voor endpoint,
  response contract, item kinds, structured text, disabled reasons en
  polling/cache semantics. Clients die `emoji_safe` adverteren kunnen inline
  `emoji` rich-text segmenten krijgen met 1-3 muziek/vibe-symbolen. Houd de
  publieke `custom_components.djconnect.ask_dj` import compatibel en gebruik de
  provider-neutrale `listening_profile` payloadnaam; `spotify_profile` is alleen
  nog een tijdelijke legacy alias.
- Ask DJ queue/up-next antwoorden dedupliceren herhaalde backend queue-items
  voordat de eerste 10 regels, images en Play Now acties worden teruggegeven.
  Huidige-track antwoorden zoals `wat speelt er` geven generated-text metadata
  en, wanneer HA TTS audio kan maken, `audio_url`/`audio_type` op
  `assistant_message` terug.
- Music Discovery dedupliceert herhaalde recente tracks als recommendation
  basis en geeft `play_count`/`based_on_count` mee, zodat clients één
  based-on item met compacte herhaalcontext tonen in plaats van dubbele regels.
- Compacte conversation-agent options-flow toont alleen actie; DJ response stijl/prompt is geen user-facing optie meer en volgt runtime client mood of de hardcoded default.
- Verwijderde opties:
  - Spotify source override;
  - Standaard playlist override;
  - DJ aankondiging op apparaat afspelen toggle uit conversation-agent options.
- User-facing label `Client API URL` is overal hernoemd naar `Client adres`.
- Spotify OAuth repair popup fix zit in release.
- Conversation agent gebruikt Assist conversation agent voor Spotify intent bepaling en DJ response generatie, met DJConnect prompt override.
- DJ response prompts moeten artiest, album en nummer noemen waar bekend.
- Config flow blokkeert niet meer op officiële Spotify media_player; DJConnect gebruikt eigen Spotify OAuth en Spotify Web API.
- Ask DJ is server-side en cross-device voor iOS, macOS, watchOS en Raspberry Pi: deze clients gebruiken `/api/djconnect/v1/ask_dj/message`, `/history`, `/history/clear`, `/idle_suggestion` en `/api/djconnect/v1/command` voor Play Now/follow-up acties. ESP32 krijgt geen Ask DJ chat UI/history en blijft op de bestaande PTT/playback command flow.
- Ask DJ history export is HTTP-only via `POST /api/djconnect/v1/ask_dj/history/export`, geeft een backend-built `djconnect.ask_dj.history.export` envelope terug en ondersteunt geen import.
- `/api/djconnect/v1/ask_dj/message` responses bevatten canonical `messages[]` in render-volgorde plus gedeelde `exchange_id` en `exchange_order` (`0` user, `1` assistant). Clients gebruiken dit om vraag altijd boven antwoord te houden bij HTTP/push/history timing races.
- Ask DJ history is HA-user scoped, max 1000 berichten, met retention system messages en `history_limit`, `history_trimmed_before`, `history_trimmed_count` metadata voor client cache cleanup.
- Ask DJ mood-zones worden server-side uit Apple client `mood` afgeleid: `0`-`24` chill, `25`-`59` groove, `60`-`84` energy, `85`-`100` party. Spoken DJ announcements gebruiken die mood-zone.
- Apple push bootstrap metadata staat in HA pairing/status/command responses:
  `ha_install_id`, `integration_version` en alleen bij echte pairingcontext
  optioneel `pairing_session_id`. Dit is niet geheim en is bedoeld voor Apple
  clients die zelf bij Central `/v1/pairing/bootstrap-proof` aanroepen; HA geeft
  daarbij nooit APNs tokens, install tokens, bearer tokens of bootstrap proofs
  aan clients terug.
- Apple push in de HACS-integratie is relay-only via de centrale DJConnect API met een per-install `djci_` token. HACS bevat geen globale relay secret, bewaart geen APNs tokens en bevat geen APNs `.p8` provider key of directe Apple push delivery. iOS/macOS/watchOS clients leveren waar nodig een short-lived `bootstrap_proof` bij push registration; ESP32, Raspberry Pi en Assist-agent-only entries hebben die proof niet nodig. Push is alleen voor expliciete Ask DJ response/confirm attention events, met foreground suppression en rate limiting; nooit voor track/playback/status/idle updates.
- Cross-device clear/trim is backend-authoritative: clients vergelijken `clear_revision`, `history_revision` en trim metadata; niet op system-message tekst parsen.
- Ask DJ gebruikt `playback_actions[]` voor Play Now en confirmation buttons; `confirmation_actions[]` bevat dezelfde Ja/Nee confirmation actions voor clients die die apart willen renderen.
- Music DNA-summary vragen zoals `wat weet je nu over mij?` gebruiken intent `personal_music_dna_summary` en zijn Music DNA-only. Render ze tekst-only met source `djconnect_music_dna`; geen oude album art, geen TTS/playback-knop en geen Play Now-knoppen reconstrueren.
- Ask DJ Track Insight-vragen zoals `Geef Track Insight voor dit nummer`, `Analyseer dit nummer`, `Tell me about this track`, `What is special about this song?` en `What is the vibe of this track?` gebruiken het gedeelde `track_insight` contract met `track_insight{track,analysis,visual_profile,cache}`, geen apart technical-analysis pad en geen Music DNA per-track match score/label/reason.
- Ask DJ recent-played vragen zoals `welke nummers heb ik afgelopen uur afgespeeld?`, `welke albums heb ik vandaag geluisterd?`, `welke artiesten hoorde ik net?` en `welke playlists heb ik afgelopen uur gespeeld?` gebruiken bij Spotify Direct Spotify `/me/player/recently-played`, blijven informatief en muteren playback niet. Responses gebruiken intent `recently_played_history`, `intent.item_type` (`tracks`, `albums`, `artists`, `playlists`), `items[]`, `assistant_message.items[]`, `images[]` en source `spotify_recently_played`. Als de gekozen backend deze capability niet heeft, geeft Ask DJ een backend-capability fallback zonder Spotify-scope repairtekst.
- Clients renderen `recently_played_history` als compacte lijst met art/icon links en titel/subtitel/tijd rechts. Niet als grote losse mediakaart renderen, geen oude artwork hergebruiken, en geen Play Now-knoppen toevoegen tenzij de backend expliciet `playback_actions[]` meestuurt.
- `command:"ask_dj_followup_response"` handelt Ja/Nee follow-ups af via server-side pending state in Music DNA; pending follow-ups verlopen na ongeveer 10 minuten.
- `Goedemorgen`/`Good morning` met `trigger:"morning_startup"` en geen actieve playback geeft een ochtend-suggestie met Ja/Nee knoppen zonder automatisch te starten; `ik ga slapen` pauzeert muziek direct.
- Ask DJ fallback is gehard tegen gibberish, sandbox escape en prompt-injectionachtige input; die geeft tekstueel `Sorry, ik begrijp niet wat je bedoelt.` zonder conversation-agent of playback route.
- Directe playbackwoorden zoals `next` en `skip` blijven directe next-commands, ook bij Nederlandse UI-taal.
- `VOICE_INTENT_DATA.md` en `examples/voice_intents.json` zijn de canonieke bron voor website/client voorbeelden; werk beide bij bij nieuwe intents.
- HACS icon issue: assets zitten in deze repo, en er is lokaal werk gestart voor een PR naar `home-assistant/brands` met `custom_integrations/djconnect/icon.png`, `icon@2x.png`, `logo.png`. Als dat vervolg nodig is: check `/tmp/home-assistant-brands-djconnect`.

Werkstijl:
- Gebruik `rg` voor zoeken.
- Gebruik `apply_patch` voor handmatige edits.
- Niet ongevraagd unrelated changes terugdraaien.
- Run minimaal `python3 -m unittest discover -s tests` voor release/codewijzigingen.
- Lokale HA dev-omgeving draait in Docker op `localhost:8123`; zie `DEVELOPMENT_ENVIRONMENT.md` voor sync/restart commands en optionele stap `28` voor een persistente free-tier ngrok tunnel met HA external/internal URL plus trusted proxy configuratie.
- Release met `./release.sh X.Y.Z`; cleanup oude releases met `./cleanup_old_releases.sh --keep 1 --execute`.
- Gedeelde DJConnect CI workflows en security rulesets staan in deze repo; zie `CI_BASELINE.md`. Andere DJConnect repos kunnen reusable workflows uit `.github/workflows/djconnect-*.yml` gebruiken.
- `main` is beschermd; releasewerk gaat via PR. HACS/hassfest validatie verwacht geldige repo topics, `hacs.json` zonder verouderde `domains` key, gesorteerde `manifest.json` keys en geen letterlijke URLs in translation strings.
- Houd docs en vertalingen actueel bij UI/config-flow/options-flow wijzigingen.
- Geen secrets/tokens/wachtwoorden loggen of committen.
```
