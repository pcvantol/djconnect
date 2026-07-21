# Renderer-Safe Playback Projection

The Session Runtime owns one ephemeral, backend-neutral playback presentation
projection for Renderer Hosts. Playback backends remain the source of actual
playback and provider-specific observation; Broadcast distributes only the
normalized projection through its existing snapshot and `playback_changed`
or `playback_progress` event.

The projection contains an optional opaque replacement `item_id`, playback
state, title, artist, album, an existing Home Assistant-proxied artwork URL,
target name, duration, optional position and an update timestamp. It never contains provider
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
the image.

When a backend snapshot safely supplies both a position and a duration while
playback is active, the Session Runtime starts a bounded, server-owned progress
clock. It publishes a renderer-safe `position_ms` replacement at most once per
second through the existing Broadcast stream. The next backend snapshot resets
the anchor and corrects drift. The clock stops immediately on pause, stop,
track replacement, end-of-duration or Runtime disposal. It never polls a
provider, persists progress or delegates clock authority to a Renderer Host.
If either position or duration is unavailable, `position_ms` remains absent and
no counter runs.

No HTTP endpoint, WebSocket channel, provider polling loop or playback control
contract is introduced. The one-second server timer reads no provider and only
advances the already-normalized Runtime projection. Universal Receiver V1
Capability 3 — Now Playing Experience — may consume this contract only after
this prerequisite is merged and reconciled.
