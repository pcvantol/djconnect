## Rich Session surface contract — 30 October 2026

[Source #1395](https://github.com/pcvantol/djconnect/pull/1395) is originally qualified; [delivery evidence](docs/verification/RICH_SESSION_SURFACE_CONTRACT_FINALIZATION_20261030.md).
One rich widget and Live Activity remains the product goal; native push is not yet accepted.
The contract and all280 product files are unchanged by this documentary Final.
This Final needs its own release qualification; no installation is needed.

## Current closed custody source delivery

Source1393 is protected `6cae8540a83a880c4bcb37dd302320336f7e15cb` and independently
ORIGINAL_QUALIFIED. [The separate documentary Final record](docs/verification/INSTALLATION_CUSTODY_ONCE_FINALIZATION_20261029.md)
records its original main/coverage/formal/durable evidence and preserved limits.
The coordinator remains unused, with required independent owners and two fixed
synchronous ports; no actual custodian, key/signing operation, route or factory.
All280 product bytes and release inputs remain unchanged by this Final; HA-dev
retains actual277/schema18. All24 requests/nine gates, Help EN/NL/free Ask DJ,
VibeCast and separate provider/native/production/Pi work remain preserved.
This Final requires its own protected delivery and original qualification.
Complete earlier bodies below retain their historical scope.

## Closed custody orchestration source preparation — 29 October 2026

[The unused custody coordinator](docs/product/INSTALLATION_CUSTODY_ONCE_ORCHESTRATION_V1.md)
composes original SQL19 reservation ACKs with two required synchronous ports and
independent owner validation. It adds no concrete custodian, key/signing operation,
startup/route/factory or operational push permission. Existing279 product bytes,
public records, release inputs and installed HA-dev277/schema18 remain unchanged.
Normal whole/exact review, protected Source and separate Final are still required.
All24 requests/nine gates, Help EN/NL/free Ask DJ and VibeCast remain preserved.
Complete earlier bodies below retain their historical scope.

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

Help examples in English and Dutch use your connected server’s current availability. You can always ask in your own words. See [Help scope and release evidence](docs/verification/HELP_EN_NL_LIVE_PUBLICATION_20261026.md).

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
