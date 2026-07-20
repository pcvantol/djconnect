# DJ Session Broadcast Transport

## Status

`CONFIRMED_CODE` — V4-06

## Canonical renderer integration model

The Home Assistant authenticated WebSocket is the one canonical live transport
for an active DJ Session. It is a Runtime-owned Broadcast subscription, not a
second planner, polling endpoint, VibeCast feed, guest transport or Universal
Session Receiver.

```text
Broadcast State
  ↓ complete snapshot on subscribe
Incremental Broadcast Events
  ↓ authenticated owner WebSocket
Renderer
```

The server remains authoritative:

```text
Profile → Session Runtime → Session Planner → Broadcast Engine → Renderer
```

Renderers do not poll Runtime internals and do not derive planner state.

## Subscription contract

After completing the normal Home Assistant WebSocket authentication, an owner
renderer sends `djconnect/session/broadcast/subscribe` with its existing
DJConnect identity/token fields and the active `session_id`.

- The server resolves `authenticated device → server-owned device binding →
  bound Profile → requested active Session → Session owner_profile_id`.
- Only the bound Profile's active Runtime may be subscribed to. A supplied
  `profile_id`, HA-user hint, room, area or fallback Profile never selects a
  Broadcast owner.
- Multiple devices bound to that same Profile may subscribe. Devices bound to
  another Profile, unknown devices and explicitly unbound devices are rejected.
- The transport never exposes a list of Profiles.
- The command result contains a full `snapshot` of the current canonical
  Broadcast State.
- The initial snapshot is always delivered before later incremental events.
- Later events use the stable Home Assistant event type
  `djconnect/session/broadcast` and contain `event_type`, `session_id` and an
  incremental `payload`.
- The existing Broadcast vocabulary is preserved, including
  `runtime_created`, `runtime_ended`, `planner_updated`,
  `session_flow_updated`, `broadcast_started` and `broadcast_stopped`.
- When a Runtime ends, subscribers receive `runtime_ended` and
  `broadcast_stopped`; the server then releases all Runtime subscriptions.
- When a WebSocket closes, its subscription is unregistered without changing
  Broadcast State.

There is deliberately no anonymous, guest, receiver, voice, audience or
VibeCast transport in this contract.

## Renderer behavior

A renderer applies the complete snapshot first, then applies each incremental
event to the displayed Broadcast State. A temporary socket interruption may
reconnect and subscribe again using the same active Session ID; the new
snapshot becomes authoritative. A rejected subscription because no active
Runtime remains means the renderer returns to its idle Session state.

## Security

The transport reuses both existing Home Assistant WebSocket authentication and
DJConnect Runtime device authorization. Its Profile authorization uses only
the existing server-side device binding. It does not expose an anonymous
subscription endpoint and does not broaden the established owner privacy
boundary. Broadcast State exposes only renderer-safe Session, Planner, Flow
and safe backend context metadata; it excludes Music DNA, preferences, session
history and conversation history.
