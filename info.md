# DJConnect

DJConnect. Muziekbediening met karakter.

Website: [https://djconnect.dev](https://djconnect.dev)

DJConnect lets you ask for music from a dedicated ESP32, iOS, macOS, watchOS or Raspberry Pi client and hear a personal DJ announcement back on the device. Home Assistant handles pairing, Spotify OAuth, backend playback, Assist/STT/TTS, server-side Ask DJ memory/history and device status while playback credentials stay safely inside Home Assistant.

Use it when you want a local voice/PTT music remote that can start Spotify playback, show queue/status data, answer Ask DJ music questions, list available speakers, offer Play Now recommendations and deliver mood-aware DJ announcements through the DJConnect client instead of a generic speaker.

Apple push registration for iOS, macOS and watchOS clients is optional and relay-only through the central DJConnect API with a per-install token bootstrapped from a short-lived Apple-client proof; Home Assistant never stores APNs provider keys and only sends strict Ask DJ wake/sync hints.

Requires Home Assistant, HACS, Spotify Premium and a working Home Assistant Assist pipeline with STT/TTS.
