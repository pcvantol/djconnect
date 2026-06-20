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
- `VOICE_INTENT_DATA.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `DEVELOPMENT_ENVIRONMENT.md`
- `info.md`

Belangrijke huidige status:
- Project: DJConnect Home Assistant custom integration, domain `djconnect`.
- Laatste release: `3.1.65`.
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
- Initial setup heeft nu 3 opties:
  - `Assist Conversation Agent` zonder client-koppelcode/device token/Client adres.
  - `DJConnect app of device koppelen`;
  - `ESP32 device WiFi configureren (via Bluetooth)`.
- Compacte conversation-agent options-flow toont alleen actie + DJ response stijl/prompt.
- Verwijderde opties:
  - Spotify source override;
  - Standaard playlist override;
  - DJ aankondiging op apparaat afspelen toggle uit conversation-agent options.
- User-facing label `Client API URL` is overal hernoemd naar `Client adres`.
- Spotify OAuth repair popup fix zit in release.
- Conversation agent gebruikt Assist conversation agent voor Spotify intent bepaling en DJ response generatie, met DJConnect prompt override.
- DJ response prompts moeten artiest, album en nummer noemen waar bekend.
- Config flow blokkeert niet meer op officiële Spotify media_player; DJConnect gebruikt eigen Spotify OAuth en Spotify Web API.
- Ask DJ is server-side en cross-device: app-clients gebruiken `/api/djconnect/ask_dj/message`, `/history`, `/history/clear`, `/idle_suggestion` en `/api/djconnect/command` voor Play Now/follow-up acties.
- Ask DJ history is HA-user scoped, max 200 berichten, met retention system messages en `history_limit`, `history_trimmed_before`, `history_trimmed_count` metadata voor client cache cleanup.
- Cross-device clear/trim is backend-authoritative: clients vergelijken `clear_revision`, `history_revision` en trim metadata; niet op system-message tekst parsen.
- Ask DJ gebruikt `playback_actions[]` voor Play Now en confirmation buttons; `confirmation_actions[]` bevat dezelfde Ja/Nee confirmation actions voor clients die die apart willen renderen.
- `command:"ask_dj_followup_response"` handelt Ja/Nee follow-ups af via server-side pending state in DJ Memory; pending follow-ups verlopen na ongeveer 10 minuten.
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
- Lokale HA dev-omgeving draait in Docker op `localhost:8123`; zie `DEVELOPMENT_ENVIRONMENT.md` voor sync/restart commands.
- Release met `./release.sh X.Y.Z`; cleanup oude releases met `./cleanup_old_releases.sh --keep 1 --execute`.
- Houd docs en vertalingen actueel bij UI/config-flow/options-flow wijzigingen.
- Geen secrets/tokens/wachtwoorden loggen of committen.
```
