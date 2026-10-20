# Install and start — 4.0.0-rc.1 candidate

**Your music. Your DJ.** DJConnect is your personal music DJ in Home Assistant.
Ask for music, enjoy DJ contributions and choose your session mood.
This guide describes the candidate source, not a public installation claim.
For installed 3.3.1 use the [stable guide](stable-3.3.1.md).
[Other languages](README.md).

## Before you start

- Install Home Assistant and HACS. Configure an Assist pipeline with an available
  conversation agent. An empty choice uses the preferred pipeline; repair an
  unavailable selected agent. STT and TTS are optional for this candidate's setup.
- For speech, configure an available HA speech route or use a client's actually
  offered device route. Text-only remains useful when no speech route is configured.
- Spotify Direct needs Premium, your own Developer Client ID and external HTTPS.
  Nabu Casa is recommended, not required. No Client Secret. [Spotify steps](spotify-direct.md).
- Music Assistant needs a configured installation and usable player, without
  DJConnect Spotify credentials. **Later / manual** defers the music connection.
- Assist needs no separately paired DJConnect device. For local pairing, keep HA
  and the client on the same LAN; ESP32 requires 2.4 GHz WiFi. Use an already
  available DJConnect app or supported device; this is not an app-store release notice.

## Install

1. [Open DJConnect in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration). Alternatively add
   `https://github.com/pcvantol/djconnect` under **Custom repositories**, category
   **Integration**.
2. Install DJConnect and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → DJConnect**.

## Follow the wizard

1. Select Assist, local device, app, or optional ESP32 WiFi setup over Bluetooth.
   Bluetooth writes WiFi only and then continues to local pairing.
2. Pair only when the selected route asks for it; Assist skips pairing. iPhone/Watch show a QR flow;
   macOS uses the displayed HA URL and six-digit code. ESP32/Pi use local discovery
   and the current code. A code is temporary; restart that pairing step when expired.
3. Choose an existing Profile or create a new one. Reuse retains its existing
   music connection: do not create another Spotify app or repeat OAuth just to reuse it.
4. For a new Profile choose Spotify Direct, Music Assistant, or Later/manual.
   Spotify opens authorization after the exact redirect URI and Client ID steps.
   Music Assistant asks for its player; Later does not require Spotify OAuth.
5. Open your connected client and start a DJ session. For Assist, select
   **DJConnect DJ** in Assist. Configure a deferred music connection before playback.
   Backend switching is available later in integration options; Profile reuse
   and switching are different actions.

[Help](troubleshooting.md) · [Stable 3.3.1](stable-3.3.1.md) · [All documentation](../README.md).
