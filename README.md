## Current Help answer-reference review — 2026-10-26

The artist review now has an explicit original-word address wire under validation;
all source/semantic/date/role/style and budget fences remain. It is not a catalogue
release: revision1/DFAA/70pending and historical paid failures are retained.
See [the bounded contract](docs/verification/HELP_ARTIST_ANSWER_WORD_REVIEW_20261026.md).
Current exact Source, CI, editorial and installed gates remain separate.

> Help artist short cycle — 26 October 2026. The manual development policy adds
> `target5_artist_v4`: the five original artist questions in en/nl/de/fr/es,
> capped at 25 attempts, 3,000 output tokens and 600 seconds. Existing selected
> modes and full100 remain unchanged. The previous original full100 completed
> 98 PASS/2 FAIL (German/Spanish artist style), with 175 complete responses.
> This controller change supplies earlier feedback; it does not fix or waive
> style acceptance. All runtime product bytes, catalogue questions and draft
> publication state remain unchanged. See
> `docs/verification/HELP_ARTIST_FIVE_LANGUAGE_SHORT_CYCLE_20261026.md`.
> Full content acceptance, winning Source/Final, configuration, Apple adoption
> and installed acceptance remain separate.

# DJConnect

<img src="https://raw.githubusercontent.com/pcvantol/djconnect/7e14e5970b3f68d33d243ae6bab2b281fad59bb2/assets/djconnect/brand-v2/mark-128.png" alt="DJConnect" width="64" height="64">

**Your music. Your DJ.**

Your personal music DJ in Home Assistant. Ask for music and enjoy DJ contributions
from an available DJConnect app, supported device or Home Assistant Assist.

**[Open DJConnect in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration)**

[English](docs/user/installation.md) · [Nederlands](docs/user/nl.md) ·
[Deutsch](docs/user/de.md) · [Français](docs/user/fr.md) · [Español](docs/user/es.md)

> This branch describes **4.0.0-rc.1**, a candidate, not an installed-release claim.
> Installed **3.3.1**? Follow the [stable setup guide](docs/user/stable-3.3.1.md).
> Check your installed version in HACS before following the wizard steps.

## Make it your session

- Ask for music without searching through menus.
- Let your DJ share music stories and announcements.
- Choose the DJ Persona and mood for your session.

## What you need

- **Home Assistant and HACS**, plus a configured Assist pipeline. The 4.0 candidate
  needs an available conversation agent; STT/TTS are optional for setup. Stable
  3.3.1 needs a pipeline with both STT and TTS: see its versioned guide.
- **Choose a music route:** Spotify Direct needs Spotify Premium, your own Spotify
  Developer app Client ID and an external HTTPS Home Assistant URL; Nabu Casa is
  recommended. Music Assistant needs a configured installation and usable player.
  You can also choose **Later / manual** without Spotify login.
- **Choose how to connect:** use an available DJConnect app/device, or use Assist
  without pairing one. Pair local devices on the same LAN; ESP32 needs 2.4 GHz WiFi.
  Speech availability depends on the selected route and actual client capabilities.

## Install

1. [Open HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration). If needed, use
   **Custom repositories**, add `https://github.com/pcvantol/djconnect` and select
   category **Integration**.
2. Install **DJConnect** from HACS.
3. **Restart Home Assistant.**
4. Go to **Settings → Devices & services → Add integration → DJConnect**.

## Start your first session

1. Choose **Assist**, a **local device** or an **app** in the wizard.
2. Follow the pairing screen when applicable (Assist skips pairing): iPhone/Watch use a QR flow;
   macOS uses the shown Home Assistant URL and code. ESP32/Pi use local pairing.
   Optional Bluetooth setup only supplies ESP32 WiFi.
3. On 4.0, choose an existing **Profile** or create one. Reusing a Profile keeps
   its music connection; a new Profile can choose Spotify Direct, Music Assistant
   or Later. Stable 3.3.1 asks for the backend before creating its Profile.
4. Open the connected client and start a DJ session, or select **DJConnect DJ**
   in your Assist configuration. A deferred music route must be configured before playback.

[Step-by-step setup](docs/user/installation.md) ·
[Spotify Direct](docs/user/spotify-direct.md) · [Help](docs/user/troubleshooting.md)

## Need a hand?

- **Assist missing:** configure the prerequisites for your installed version.
- **Spotify login does not return:** copy the exact redirect URI from the wizard
  into Spotify Developer Dashboard; update it and reauthorize after an external URL change.
- **Local pairing fails:** check the LAN and use the current six-digit code.
- **Generic HA icon:** redownload in HACS, restart HA and refresh the frontend cache.

[More help](docs/user/troubleshooting.md) · [Documentation](docs/README.md) ·
[Website](https://djconnect.dev) · [Source](https://github.com/pcvantol/djconnect)

DJConnect repositories are MIT-licensed; this HA integration may be distributed
separately for DJConnect devices. Copyright (c) 2026 Peter van Tol.
Third-party dependencies keep their own licenses: [notices](THIRD_PARTY_NOTICES.md).
Spotify is a trademark of Spotify AB. DJConnect is not affiliated with, endorsed
by, or sponsored by Spotify AB. [License](LICENSE).
