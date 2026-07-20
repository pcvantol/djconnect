# WebSocket API

The machine-readable command inventory is
[`inventory/websocket_commands.json`](inventory/websocket_commands.json).

## Current Implementation

`CONFIRMED_CODE` HA registers websocket commands through
`websocket_api.async_register_command` in
`custom_components/djconnect/websocket_api.py`.

`CONFIRMED_CODE` `djconnect/capabilities` returns:

- `websocket_supported: true`
- stable command list
- feature booleans
- HTTP fallback paths
- platform capabilities
- contract versions
- `transports: {http: true, websocket: true}`

`CONFIRMED_CODE` Websocket command handlers call the same payload handlers as
the HTTP routes for command, Ask DJ, Music DNA, Music Discovery and Track
Insight.

## Client Behavior

`CONFIRMED_CODE` Apple uses `URLSessionWebSocketTask`, requires a Home
Assistant auth token, refuses non-local websocket URLs, refreshes capabilities
with a 60 second cache and backs off after failures.

`CONFIRMED_CODE` Windows uses `ClientWebSocket` and has tests for websocket
capability detection and HTTP fallback behavior.

`CONFIRMED_CODE` Pi uses `WebSocketFastPath`, refreshes capabilities and only
tries websocket when enabled/capable.

## Differences From HTTP

`CONFIRMED_CODE` Pairing, voice upload, TTS binary retrieval, image proxy and
Spotify OAuth callback are HTTP-only in the observed implementation.

`CONFIRMED_CODE` V4-06 adds one persistent Runtime-scoped subscription:
`djconnect/session/broadcast/subscribe`. Its command result is the complete
initial Broadcast State snapshot; later incremental events use
`djconnect/session/broadcast`. See
[`BROADCAST_TRANSPORT.md`](BROADCAST_TRANSPORT.md) for the canonical renderer
integration model and lifecycle.

## Verification Mapping

`CAPABILITY-001..008`, `ASKDJ-*`, `MUSICDNA-*`, `DISCOVER-*`, `TRACK-*`,
`NETWORK-*`.
