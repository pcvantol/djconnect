# Install and start — stable 3.3.1

This guide is for the published [integration v3.3.1](https://github.com/pcvantol/djconnect/releases/tag/v3.3.1),
not an onboarding package or the 4.0 candidate. Historical source/tag stays unchanged.
[Five-language setup](README.md) · [Candidate guide](installation.md).

1. Install Home Assistant and HACS. Configure an Assist pipeline with **both STT
   and TTS**: the 3.3.1 setup preflight requires them even if your intended client
   use is textual. The 4.0 candidate has a different conversation-agent prerequisite.
2. [Open HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration), or add
   `https://github.com/pcvantol/djconnect` as category **Integration** in Custom repositories.
   Select the integration release, install DJConnect and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → DJConnect**.
4. Choose Assist, local device or app; Bluetooth can provision ESP32 WiFi before pairing.
5. Complete route-specific pairing first; Assist skips pairing. iPhone/Watch
   use QR, macOS uses the shown HA URL and code. Local devices need the same LAN
   and current six-digit code; ESP32 needs 2.4 GHz WiFi.
6. In 3.3.1 the backend comes before the new Profile form. Choose Spotify Direct,
   Music Assistant, or **Later / manual**. Later/manual exists in this version too.
   Spotify Direct needs Premium, your Developer Client ID and external HTTPS;
   copy the wizard's exact redirect URI into the Developer Dashboard. Music
   Assistant needs its configured usable player, with no Spotify Client ID or OAuth.
   Complete the new Profile form. Do not expect the candidate's initial
   existing-Profile chooser in this older flow.
7. Open the connected client to start a DJ session, or select DJConnect DJ for Assist.
   Configure a deferred backend before playback. The older wizard may show retired
   client choices; Windows is retired and must not be newly paired.

[Spotify details](spotify-direct.md) · [Help](troubleshooting.md).
