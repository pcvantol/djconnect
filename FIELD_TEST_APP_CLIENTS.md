# DJConnect app client field test checklist

Use this checklist for real iOS, macOS and Windows validation before a public release.
The automated tests cover the Home Assistant contract; these steps verify the native
client, network and remote-access behavior.

## Preconditions

- Home Assistant has DJConnect installed and configured.
- The entry uses Spotify Direct or Music Assistant and shows backend availability.
- Home Assistant has a local URL and, for remote tests, a HTTPS external/Nabu Casa URL.
- The target client is on the local network for initial pairing.
- No Spotify refresh token, Home Assistant token, device token or raw audio is copied
  into notes, screenshots or logs.

## Inbound Pairing

Run once per client type: `ios`, `macos`, `windows`.

1. Start Add Integration and choose DJConnect app pairing.
2. Confirm the pairing form hides Client address.
3. Pair from the app with:
   - `device_id`: `djconnect-ios-XXXXXXXXXXXX`, `djconnect-macos-XXXXXXXXXXXX` or
     `djconnect-windows-XXXXXXXXXXXX`
   - matching `client_type`
   - current `pair_code`
4. Confirm the Home Assistant response contains:
   - `success: true`
   - `device_token`
   - `api_base: /api/djconnect`
   - `status_path`, `voice_path` and `event_path`
   - `ha_local_url`
   - `ha_remote_url` for iOS, macOS and Windows when a HTTPS external URL is configured
5. Confirm the response does not contain Spotify OAuth credentials, refresh tokens,
   Home Assistant long-lived access tokens, `device_language` or `language`.
6. Confirm the HA device stores the stable app `device_id`, matching `client_type` and
   pairing status `pending` until the app posts status.

## Remote Playback

Run once per paired client type.

1. On LAN, send `/api/djconnect/status` with the returned bearer token.
2. Send `/api/djconnect/command` with `command: status`.
3. Send `/api/djconnect/command` with a playback command such as `play`,
   `set_shuffle`, `set_repeat`, `devices`, `queue` and `playlists`.
4. Leave the LAN and repeat the same command set via `ha_remote_url`.
5. Confirm playback commands return HTTP 200 for successful backend calls and do not
   trigger re-pairing or Spotify reauthorization repairs.
6. Confirm firmware channel, firmware update, reboot and ESP-only settings entities
   are not active for iOS, macOS or Windows.

## Evidence To Record

- Client type and app build.
- Home Assistant version.
- DJConnect integration version.
- Backend: Spotify Direct or Music Assistant.
- Local pairing result.
- Remote command result.
- Any HA Repair issue created during the test.

