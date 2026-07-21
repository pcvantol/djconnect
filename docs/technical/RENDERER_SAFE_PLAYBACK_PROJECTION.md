# Renderer-Safe Playback Projection

The Session Runtime owns one ephemeral, backend-neutral playback presentation
projection for Renderer Hosts. Playback backends remain the source of actual
playback and provider-specific observation; Broadcast distributes only the
normalized projection through its existing snapshot and `playback_changed`
event.

The projection contains an optional opaque replacement `item_id`, playback
state, title, artist, album, an existing Home Assistant-proxied artwork URL,
target name, duration and an update timestamp. It never contains provider
URIs, credentials, raw backend payloads, internal entity identifiers, Planner
state or Profile-private data. Empty or unsafe values are omitted. An inactive
projection is `{ "state": "idle" }`.

Every active Runtime starts idle. Existing observation updates the projection
only when its renderer-safe content materially changes; equivalent observations
do not publish duplicate Broadcast events. A paused, stopped or cleared
observation replaces stale playback data. The projection is released with the
Runtime and is never persisted or added to historical projections.

Artwork is optional. When already observed, the server registers the source
with DJConnect's existing Home Assistant image proxy and exposes only that
same-origin proxy URL. Renderer Hosts never receive the external artwork URL,
credentials or provider payload. The projection neither fetches nor caches
artwork; the existing proxy performs the fetch only if a Renderer Host requests
the image. Playback position remains absent because there is no dedicated,
reliable progress-publication contract; this capability does not synthesize it.

No HTTP endpoint, WebSocket channel, polling loop or playback control contract
is introduced. Universal Receiver V1 Capability 3 — Now Playing Experience —
may consume this contract only after this prerequisite is merged and reconciled.
