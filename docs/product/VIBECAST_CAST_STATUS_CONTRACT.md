# Cast receiver status contract v1

Owner: Core. Assignment: `DJC-CORE-VIBECAST-CAST-STATUS-V1-20261009`, authorized
by Peter after coordination Core #1101/6088108512 and receiver #10/6088099265.
This additive adapter contract leaves Broadcast snapshot/event v1, owner
handoff authorization and Apple conversation/history/search contracts intact.
It does not reopen #1136/#1137 or qualify a physical device.

## Opt-in and correlation

Use the existing `urn:x-cast:com.djconnect.vibecast.v1` JSON channel and existing
`kind:"vibecast_handoff", version:1, ha_url, session_id, broadcast_token` message.
To request statuses add `status_version:1` and `handoff_id`: exactly 32 lowercase
hex characters, independently randomly generated for each new handoff. Both
fields are required together. CAF supplies the actual `senderId`; it is never
trusted from message JSON. Unsupported status versions or malformed correlation
fail closed. Existing senders omitting both fields retain v1 behavior without
status messages or the new handshake deadline. Status support is not a new
HA authorization grant and never accepts a sender end-grant.

A sender starts its own 15-second deadline when sending a new handoff. A receiver
must advertise the custom namespace as JSON in CAF receiver options, then
install its message listener when `isSystemReady()` / the READY event permits.
CAF connection alone cannot imply HA authentication or presentation. If no
correlated response arrives, the sender reports unavailable/pending, never
"visible on TV". A lost handoff before readiness is retried with the same ID;
an already accepted ID is idempotent. A reconnect/new token uses a **new** ID.

Every response goes only to the current CAF sender, never broadcast:

```json
{"kind":"vibecast_status","version":1,"handoff_id":"0123456789abcdef0123456789abcdef","session_id":"session-id","sequence":4,"state":"presenting","presentation":"silence","lease_ms":15000}
```

The [JSON schema](../../examples/client_contracts/vibecast_cast_status/status.schema.json)
binds the response envelope. The envelope contains only these fields plus an optional fixed `reason` code.
It never includes HA URL, token, Profile, artwork, Moment text/IDs, chat, history
or search results. Sequence increases within one handoff. The sender accepts
only its current receiver/channel, exact version/ID/Session and increasing
sequence; arrival refreshes the maximum 15-second lease using a monotonic local
clock. Changing Profile/Session/receiver invalidates that local correlation
immediately. No response after invalidation can restore the old view/status.

## States and evidence

| State | Meaning |
| --- | --- |
| `receiver_ready` | CAF is ready and the adapter has validated this handoff envelope; HA access is still pending. |
| `connecting` | The renderer is attempting the authorized HA WebSocket; opening it alone grants no success. |
| `snapshot_accepted` | Matching HA snapshot/capability/schema checks passed; presentation is still pending. |
| `presenting` | That snapshot has been applied and the shared DOM render completed; `presentation` is `moment` or `silence`. |
| `recovering` | Transport closed; withdraw presentation success until a fresh accepted snapshot/render. |
| `error` | Terminal handoff, access, compatibility or deadline failure. |
| `ended` | The existing HA Runtime-end/Broadcast-stop event cleared the shared view. |
| `stopped` | Only the receiver view was stopped or superseded; Session/playback are unaffected. |

`presenting` means software presentation, **not** physical visibility, HDMI,
frame rate or hardware acceptance. Silence means there is no currently eligible
visible Moment; it is valid Session presentation, including expiry. Presence of
a Moment is never a connectivity requirement. An active presentation emits a
heartbeat every five seconds, or earlier on presentation change. Network loss
changes status to recovering; a fresh snapshot is required again. Initial or
recovering opt-in handshakes have a 15-second deadline which retries do not
extend. On timeout the receiver clears credentials/content and closes transport.
Terminal states stop the heartbeat. Fixed reasons are `snapshot_timeout`,
`invalid_handoff`, `incompatible_snapshot`, `access_rejected`, `runtime_end`,
`host_stop`, `sender_disconnected` and `superseded`. Raw SDK/server errors are
never forwarded.

New handoffs invalidate old sockets/timers/renderer generation. The receiver
remembers at most 32 retired IDs to ignore recent replay; the sender's own exact
current-ID check remains mandatory. This is correlation, not a replay-resistant
authorization store. Authority still comes from the existing HA Runtime token.
Malformed unrelated sender messages cannot tear down a current view.

## Stop and departure

An opted-in sender can send `kind:"vibecast_stop", version:1, handoff_id,
session_id`. Only the matching actual CAF sender and current correlation may
stop the view. Sender departure, host unload or superseding handoff also stop
that view. No Session-end HTTP call, playback command or extra owner capability
is issued. Explicit local Pi end-grants remain separately server authorized.

## Build and receiving gates

Shared build 1.1.0 declares `cast_status_versions:[1]` in addition to existing
handoff/snapshot capabilities. Import with the matching pinned build verifier,
exact reviewed supplying revision and external manifest digest. Build 1.0.0
remains an immutable historical artifact with its original verifier. Receiver
adoption requires a new pin/delta review; never patch imported HTML or transfer
an old GO to changed bytes. Apple implements the opt-in envelope, lease and
correlation rules under its own existing follow-up writer.

Before integrated acceptance bind Core source/build, receiver import and served
Pages bytes, Apple build, actual installed HA pin/capabilities, trusted HTTPS/WSS
and exact HA origin allowlist in one receipt. The known custom origin is
`https://receiver.djconnect.dev`; App ID is `8EA92910`. HA-dev's last recorded
69315f43 install is not assumed suitable. HA installation/config, Pages/public
promotion, Cast Console and The Frame tests require their own authority.
Native sender → real CAF → authorized HA → visible Moments/reconnect/stop proof
remains separate from modeled tests. No certificate/auth bypass or central relay.

CAF references: [receiver options](https://developers.google.com/cast/docs/reference/web_receiver/cast.framework.CastReceiverOptions),
[context readiness and directed messages](https://developers.google.com/cast/docs/reference/web_receiver/cast.framework.CastReceiverContext).

The presentation heartbeat renews the receiver's applied software state; it is
not an independent HA health ping. Transport closure withdraws success when
WebSocket loss is detected. A half-open connection is not qualified as live HA
freshness by this contract. Integrated network tests must measure actual
closure/recovery; senders cannot label a receiver heartbeat as physical TV proof.
