# Entities, backend switching and support

DJConnect keeps backend playback state in the integration and clients. It does
not create a separate native playback-proxy media player. Entity names can change
when Home Assistant renames a device or entity.

Depending on client/capabilities, administrator surfaces include status,
last-command and corrected-STT sensors; voice-test and refresh-info actions;
ESP32 firmware/settings entities; supported Raspberry Pi lifecycle actions; and
Apple APNs readiness diagnostics. ESP-specific hardware controls do not imply
that other clients possess that hardware. [Push diagnostics](PUSH_NOTIFICATIONS.md).

The options-flow switch between Spotify Direct and Music Assistant retains
pairing, device tokens, Ask DJ history, Music DNA and push registrations. A
monotonic `music_backend_revision` lets clients discard stale backend-specific
actions. Pair/status/command responses expose a safe backend/capability summary.
Music Assistant owns provider login, library, queues and grouping/sync; DJConnect
controls the configured player and does not ask for Spotify OAuth on that route.
The authoritative response/switch contract is in [API_CONTRACT](../../API_CONTRACT.md#backend-independent-response-shapes).

Music Discovery is a recommendation feed, not a listening-history list. Its
server-owned section rendering, daily wake hint and hourly refresh remain in
[Music Discovery](../../API_CONTRACT.md#music-discovery-contract). Clients do not
rebuild recommendations from raw recent tracks or local DNA.

For ordinary setup use [user help](../user/troubleshooting.md). Deeper diagnostics
must retain secret/history/audio redaction. A backend switch, readable status or
dry-run is not installed, native, speech, or physical-hardware acceptance.
