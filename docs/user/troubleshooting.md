# Help with setup

1. **Assist is missing.** Configure an Assist pipeline with an available conversation agent.
   Check the selected or preferred pipeline and its agent. STT and TTS are optional for setup.
2. **Spotify login does not return.** Match the wizard's exact redirect URI in
   Spotify Developer Dashboard. After an external HA URL change, update it and
   reauthorize. Music Assistant and Later/manual do not need Spotify OAuth.
3. **A local client cannot pair.** Check the same LAN, current six-digit code
   and ESP32's 2.4 GHz WiFi. Follow the app's displayed route rather than guessing
   a hostname from a code. Re-open pairing after a code expires.
4. **The HA icon is generic.** Redownload DJConnect through the Marketplace, restart HA and
   refresh the browser/app cache. This does not change which integration version is installed.

For other problems, check the chosen music backend and playback target in options.
Use HA integration diagnostics when reporting a fault; keep private credentials
out of reports. [Report an issue](https://github.com/djconnect-music-dj/djconnect/issues/new/choose).
Administrators can use the [entity/support reference](../technical/ENTITIES_AND_SUPPORT.md)
and [push diagnostics](../technical/PUSH_NOTIFICATIONS.md).

[Setup and languages](README.md) · [Documentation index](../README.md).
