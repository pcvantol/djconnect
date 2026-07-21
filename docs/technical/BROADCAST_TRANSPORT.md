# DJ Session Broadcast Transport

## Status

`CONFIRMED_CODE` — V4-06

## Canonical renderer integration model

The Home Assistant authenticated WebSocket is the canonical live transport
for an active DJ Session. It is a Runtime-owned Broadcast subscription, not a
second planner, VibeCast feed, guest transport or Universal Session Receiver.
An owner may also retrieve the same renderer-safe Broadcast snapshot over HTTP
as point-in-time recovery; HTTP does not poll, subscribe or deliver live events.

```text
Broadcast State
  ↓ complete snapshot on subscribe
Incremental Broadcast Events
  ↓ authenticated owner WebSocket
Renderer
```

### Owner HTTP snapshot fallback

`GET /api/djconnect/v1/session/broadcast/{session_id}` returns the existing
owner-authorized Broadcast State projection for the exact active Session. It is
the HTTP recovery fallback for a disconnected owner renderer and is equivalent
to the initial owner WebSocket snapshot. It creates no subscription, callback,
Session, Flow entry or playback action.

The endpoint is snapshot-only. Its snapshot includes the Broadcast-owned
watermark for its current delivery boundary, but it exposes no sequence query,
cursor issuance or validation, replay, Flow delta, deduplication or
ordering-recovery protocol. The bounded Replay Log and owner-scoped Recovery
Cursor remain internal infrastructure. `GET /session/active`
remains a broader owner Runtime resource, not the renderer snapshot contract.

`GET /api/djconnect/v1/capabilities` is the transport discovery surface for
HTTP clients. Its Broadcast declaration is shared with the WebSocket capability
response and reports only this implemented snapshot-recovery contract.

The server remains authoritative:

```text
Profile → Session Runtime → Session Planner → Broadcast Engine → Renderer
```

Renderers do not poll Runtime internals and do not derive planner state.

## DJ Moment projection

The current transport remains the authoritative V4-06 Broadcast State
contract. The canonical presentation model adds immutable DJ Moments to that
state rather than giving renderers creative responsibility:

```text
Session Planner → Knowledge Intent → DJ Moment Engine → DJ Moment → Broadcast → Renderer
```

A Moment is a renderer-safe snapshot with its Presentation Intent already
resolved. A renderer may choose how to display the supplied content for its
surface, but must not rewrite the Persona, Mood, delivery, importance or
follow-up actions. This is architecture and domain modelling only; it does not
add a Moment field, event or WebSocket payload to the current transport.
See [`../product/DJ_PRESENTATION_ARCHITECTURE.md`](../product/DJ_PRESENTATION_ARCHITECTURE.md).

### First production Moment projection

The first bounded Moment slice adds `dj_moments` to Broadcast State and the
incremental `dj_moment_published` event. Each payload is a frozen,
renderer-safe DJ Moment. Owner subscriptions receive their Profile Runtime's
authorized Moment projection. Broadcast Token subscriptions receive only
`session_shared` and `public_broadcast` Moments; `owner_only` Moment snapshots
and events are filtered server-side. Silence remains a Session Flow decision
and is intentionally not emitted as a visual Moment event.

See [`DJ_MOMENT_ENGINE.md`](DJ_MOMENT_ENGINE.md) for the current production
scope and reuse boundary.

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
  During setup, the owner callback is registered once in a pending state before
  the canonical snapshot is built; events produced before the successful result
  are buffered and delivered only after that result. This is setup ordering,
  not replay, sequencing, cursor recovery or duplicate suppression.
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

There is no anonymous transport: owner access requires its existing device
authorization and Receiver access requires the constrained Broadcast Token.
Voice, audience and VibeCast transports remain out of scope.

## Universal Session Receiver access

V4-07 adds a separate ephemeral **Broadcast Token** for the Universal Session
Receiver. The token is cryptographically unpredictable, belongs to exactly one
active Runtime and becomes invalid when that Runtime ends. It is not a device
pairing credential, Profile credential or general DJConnect API token.

An authenticated owner device may obtain its active Runtime's token through the
existing owner authorization chain. A Receiver then uses only that token and
the exact Session ID to open the read-only Broadcast WebSocket. It receives the
same initial snapshot followed by the same incremental Broadcast events.

The server supplies capabilities with every Receiver connection:

```json
{"view_broadcast": true, "like": false, "audience_signals": true, "ask_dj": false, "owner_controls": false}
```

Receiver frames cannot invoke owner commands, playback or Profile state. The
existing bounded `audience_signal` frame may contribute an aggregated audience
signal through the Runtime; it does not grant Planner, playback or owner
controls. Tokens cannot access owner endpoints or another Runtime. Broader
receiver interaction policy remains deferred.

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
