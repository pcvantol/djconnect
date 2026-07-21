# Universal Receiver V1 — Server Architecture

## Status

Accepted server architecture and current-contract boundary. Capabilities 1 and
2 are complete: the minimal operational browser renderer and its Session Flow
timeline use only existing Broadcast projections. Neither capability adds a
frontend framework, authentication redesign, Runtime behaviour, transport model
or persistence.

## Purpose

The Universal Receiver is the browser-capable **Web Renderer Host** for an
active DJConnect Session. It consumes the same server-owned Broadcast
projections as every other Renderer Host. It is disposable presentation
infrastructure, not a Session Runtime or a second intelligence pipeline.

```text
Home Assistant
  Profile → Session Runtime → Planner / Knowledge / Moment Engine
          → Session Flow → Broadcast
                         ↓
              Apple / Windows / Pi / Voice / Universal Receiver
```

The browser renders an authorized projection. It does not compute, infer,
repair or recreate Session meaning.

## Ownership

| Owner | Owns | The Universal Receiver does not own |
| --- | --- | --- |
| Session Runtime | Active Session lifecycle and playback-facing orchestration | Browser connection lifetime |
| Planner | Planning, approval and Flow ordering | Browser scheduling or intent selection |
| Knowledge Engine | Knowledge preparation, validation and resolution | Browser knowledge retrieval or caching |
| DJ Moment Engine | Immutable DJMoment realization | Browser text or Moment generation |
| Session Flow | Canonical semantic order | Browser-local history authority |
| Broadcast | Authorized snapshots and incremental distribution | Browser synchronization protocol |
| Universal Receiver | Temporary presentation state and renderer lifecycle | Any server business state |

Disconnecting, refreshing or closing a Receiver must only remove its Broadcast
subscription. It never ends, pauses, replans or otherwise changes the active
Session.

## Renderer-safe presentation contract

The Receiver may render only the existing Broadcast projection:

- active Session state and safe backend/playback context already exposed by
  Broadcast;
- current and historical renderer-safe DJMoments allowed for its subscription;
- canonical Session Flow projection;
- Broadcast lifecycle and incremental events; and
- existing Runtime controls only through their separately authorized existing
  APIs.

The Receiver must not receive or derive Planner state, Planning Window,
candidate slots, Planned Intents, readiness evaluations, Prepared Knowledge,
Performance Memory internals, Knowledge Engine internals, provider credentials,
raw provider payloads, Profile-private data or server ownership state.

The Broadcast Token contract is view-scoped. It does not grant owner controls,
Ask DJ, likes or Profile access. Existing aggregated audience-signal handling
remains the only Receiver-originated frame currently permitted by that
contract; it does not create Receiver planning or playback authority.

## Transport and lifecycle

The Universal Receiver reuses the existing Broadcast transport; it introduces
no browser-specific synchronization model.

1. An authenticated owner obtains the active Runtime's ephemeral Broadcast
   Token through the existing owner-authorized server path.
2. The Receiver supplies that token and exact active Session identifier to the
   existing read-only Broadcast WebSocket.
3. The server validates the token against that active Runtime and returns one
   complete, renderer-safe snapshot before incremental Broadcast events.
4. The Receiver renders the snapshot and applies subsequent events as supplied.
5. On disconnect the server unregisters only that Receiver subscription.
6. When the Runtime ends, Broadcast emits its existing end events, releases its
   subscriptions and the token becomes unusable with the Runtime.

Receiver reconnect uses the existing Broadcast semantics: a new valid
subscription receives a fresh authoritative snapshot. Owner cursor recovery is
an existing owner-only Broadcast capability; V1 does not grant the Receiver a
new cursor, replay protocol, local event log or persistence requirement.

## Capability 1 — Broadcast Connection and Session Rendering

**Status: COMPLETE.**

The operational Receiver is served as presentation infrastructure at
`/djconnect/receiver`. It accepts only the existing `session_id` and
`broadcast_token` URL parameters and opens only the existing read-only
Broadcast WebSocket. The page itself is not a data API and introduces no new
transport endpoint or polling path.

It holds an in-memory projection only. The initial snapshot replaces that
projection; permitted incremental Broadcast events update it; a reconnect opens
a new subscription and receives a fresh snapshot. A Runtime-ended event clears
the projection and leaves the Receiver idle. Refreshing the page reconstructs
the display from the server snapshot and never uses browser persistence.

The deliberately minimal page renders only Session status, current playback,
the current DJMoment, Session Flow and connection state. It has no controls,
Planner or Knowledge view, artwork, queue, diagnostics, Session chooser or
client-derived Runtime state.

## Capability 2 — Session Flow Timeline Rendering

**Status: COMPLETE.**

The Receiver renders `session_flow.items` as the complete current semantic
timeline exactly in the order supplied by the Broadcast snapshot or
`session_flow_updated` event. Each renderer-safe item displays its published
relative position, item type and label; a DJ Moment item also displays its
published Moment type. The browser never sorts, synthesizes, filters or keeps
a separate timeline history.

An incoming snapshot replaces the complete in-memory timeline, including after
a reconnect or Session reset. A `session_flow_updated` event likewise replaces
the current timeline with the Runtime-published projection. A
`dj_moment_published` event updates the existing current-Moment presentation;
it does not append an inferred timeline entry. Runtime termination clears the
timeline. Consequently, completed, active and future semantics remain defined
solely by the server-published Flow item attributes.

## Multi-renderer model

Multiple Renderer Hosts may consume one active Broadcast concurrently. Apple,
Windows, Pi, Voice and the Universal Receiver receive projections appropriate
to their existing authorization. No Renderer Host is authoritative over another
host, Session Flow, planner output or playback.

The Receiver's Broadcast Token subscription excludes `owner_only` DJMoments
server-side. Renderer-specific layout, navigation and temporary UI selection
remain local presentation concerns and cannot alter Broadcast State.

## Security boundary

The Runtime-scoped Broadcast Token is cryptographically generated by the
server, bound to exactly one active Session and discarded with that Runtime. It
is neither a device-pairing credential, a Profile credential nor a general API
token. The Receiver never receives a provider credential or reusable server
authority.

The server remains responsible for token validation, Session binding,
owner-only Moment filtering, capability enforcement and subscription cleanup.
The browser treats every server snapshot as authoritative and retains no
durable Session or planning state.

## Deferred capabilities

- Advanced browser presentation, layout, themes, animations and responsive
  optimization.
- Browser authentication redesign or independent Receiver identity.
- Receiver-owned playback, Planner or Knowledge controls.
- Receiver cursor replay, browser persistence, offline synchronization and
  browser-side recovery logic.
- Renderer-specific diagnostics and any new control surface.

## Canonical references

- [DJ Presentation Architecture](../product/DJ_PRESENTATION_ARCHITECTURE.md)
- [Broadcast Transport](BROADCAST_TRANSPORT.md)
- [WebSocket API](WEBSOCKET_API.md)
- [DJ Session Transport Architecture](../../DJ_SESSION_TRANSPORT_ARCHITECTURE.md)
