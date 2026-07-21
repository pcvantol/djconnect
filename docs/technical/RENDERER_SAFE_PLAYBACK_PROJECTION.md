# Renderer-Safe Playback Projection

The Session Runtime owns one ephemeral, backend-neutral playback presentation
projection for Renderer Hosts. Playback backends remain the source of actual
playback and provider-specific observation; Broadcast distributes only the
normalized projection through its existing snapshot and `playback_changed`
event.

The projection contains an optional opaque replacement `item_id`, playback
state, title, artist, album, target name, duration and an update timestamp.
It never contains provider URIs, credentials, raw backend payloads, internal
entity identifiers, Planner state or Profile-private data. Empty or unsafe
values are omitted. An inactive projection is `{ "state": "idle" }`.

Every active Runtime starts idle. Existing observation updates the projection
only when its renderer-safe content materially changes; equivalent observations
do not publish duplicate Broadcast events. A paused, stopped or cleared
observation replaces stale playback data. The projection is released with the
Runtime and is never persisted or added to historical projections.

Artwork and playback position are intentionally absent. Existing normalized
artwork references have not been established as renderer-safe external URLs,
and no dedicated reliable progress-publication contract exists. This capability
does not fetch, proxy, cache or synthesize either value.

No HTTP endpoint, WebSocket channel, polling loop or playback control contract
is introduced. Universal Receiver V1 Capability 3 — Now Playing Experience —
may consume this contract only after this prerequisite is merged and reconciled.
