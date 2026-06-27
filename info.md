# DJConnect

<p align="center">
  <img src="custom_components/djconnect/brand/logo.png" alt="DJConnect" width="160">
</p>

DJConnect. Muziekbediening met karakter.

Website: [https://djconnect.dev](https://djconnect.dev)

DJConnect lets you ask for music from a dedicated ESP32, iOS, macOS, watchOS, Raspberry Pi or Windows client and hear a personal DJ announcement back on the device. Home Assistant handles pairing, Spotify OAuth, backend playback, Assist/STT/TTS, server-side Music DNA, Ask DJ history and device status while playback credentials stay safely inside Home Assistant.

Use it when you want a voice/PTT music remote that can start playback, show queue/status data, answer Ask DJ music questions, list available speakers, offer Play Now actions and deliver mood-aware DJ announcements through the DJConnect client instead of a generic speaker. ESP32 and Raspberry Pi stay local-only; iOS, macOS and Windows can use a Home Assistant remote URL after local pairing.

With Spotify Direct, Ask DJ can answer recent Spotify listening questions for tracks, albums, artists and playlist contexts with compact artwork/icon lists. Spotify-backed Home Assistant control/status entities reflect playback availability, volume, output, repeat, shuffle, queue and playlists when Spotify is authorized. With Music Assistant, DJConnect controls one configured Music Assistant player and leaves provider login, library, queues and grouping/sync to Music Assistant. DJConnect no longer creates a native playback proxy media player.

DJConnect supports an explicit options-flow backend switch between Spotify Direct and Music Assistant. The switch keeps pairing, device tokens, Ask DJ history, Music DNA and push registrations while clients use `music_backend_revision` to discard stale backend-specific playback actions. Pair/status/command responses include a safe backend summary and capabilities so clients can render About/debug and recover from unsupported backend features without extra endpoints. Music Assistant does not require a Spotify Client ID or DJConnect Spotify OAuth.

Apple push registration for iOS, macOS and watchOS clients is optional and relay-only through the central DJConnect API with a per-install token bootstrapped from a short-lived Apple-client proof; Home Assistant never stores APNs provider keys and only sends strict Ask DJ wake/sync hints.

For APNs troubleshooting, use the `APNs registratie` diagnostic sensor and the `djconnect.test_apns_push` developer action. The action can run as a dry-run or send one test event, returning relay/config flags and actionable errors such as `missing_bootstrap_proof` without exposing APNs tokens, bearer tokens, bootstrap proofs or `djci_` install tokens.

## Requirements

- Home Assistant with HACS.
- A working Home Assistant Assist pipeline with STT and TTS.
- A DJConnect ESP32, iOS, macOS, watchOS, Raspberry Pi or Windows client on the same local network during pairing.
- For ESP32 clients: 2.4 GHz WiFi.
- For Spotify Direct: Spotify Premium, a user-owned Spotify Developer app Client ID and an external HTTPS Home Assistant URL, preferably Nabu Casa.
- For Music Assistant: Music Assistant installed/configured in Home Assistant with at least one usable player. DJConnect does not ask for Spotify OAuth on this route.

## Install

1. Add `https://github.com/pcvantol/djconnect` to HACS as a custom repository with category `Integration`.
2. Install DJConnect from HACS.
3. Restart Home Assistant.
4. Go to **Settings -> Devices & services -> Add integration -> DJConnect**.
5. Choose `Spotify Direct`, `Music Assistant`, a local device, an app client or the `Assist Conversation Agent` route in the setup flow.

HACS deeplink:

```text
https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration
```

Spotify is a trademark of Spotify AB. DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.
