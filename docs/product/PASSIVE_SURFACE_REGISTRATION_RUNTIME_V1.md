# Passive paired registration: first Core runtime increment

The two role-state GETs selected by the [fixed passive contract](AUTOMATIC_PAIRED_SURFACE_REGISTRATION_V1.md)
are registered by normal Core HTTP setup:

- `/api/djconnect/v1/surface_registration/widget_transport/state`
- `/api/djconnect/v1/surface_registration/status_activity_transport/state`

Requests require the exact current ordinary paired device bearer, device ID and
client type. No Profile or active Session is needed. The read compares loaded
ConfigEntry data/options and runtime identity without learning identity, reading
`runtime.config`, creating state, loading/writing a Store or calling a provider.
Query strings, bodies and duplicate critical headers are rejected. Responses are
no-store and contain only the fixed-order
`{"version":1,"state":"UNAVAILABLE"}` negative body. Unsupported methods return405;
malformed requests400, failed authentication401 and mismatched authenticated
scope403. A valid pair returns503 because it is not a push-purpose acknowledgement.

This increment has no affirmative purpose-store acknowledgement, pairing epoch,
original A/B producer, child route, signed response or positive factory. The
pinned contract JSON remains unchanged; its implementation-status text describes
its original publication scope. This note records the newer limited runtime
implementation and leaves the remaining contract unimplemented.

Runtime-owned negative records retire synchronously before token/device changes,
explicit re-pair, temporary entry substitution during central-install rotation,
runtime entry replacement and unload. Failed awaits cannot restore the old
capture or create a new capture on an already retired record. Restored pairing
bytes do not mint an epoch. Duplicate persistence of the same pair does not issue
a new fence, lease or operation. These process-local negative records apply to
the new automatic-registration family. They do not replace the existing Session
surface registry, claim remote withdrawal or erase an OS display. A future
positive producer needs genuine acknowledged store/clock/principal/signing
composition and qualified mutation boundaries. Cancellation qualification beyond
the tested failed-await cases remains separate.

The isolated HA verifier exercises actual registered HTTP, runtime methods,
options repair, temporary entry rotation through failed synthetic device/API
awaits, and failed unload. Synthetic credentials and local test pre-states are
not real enrollment. Network, model, native SDK, provider and installed-runtime
acceptance remain separate. The first presentation remains playback status plus
original observation time, without titles, artwork, progress or an
erasure/currentness promise. Ordinary pairing needs no extra owner or Profile-role
approval screen.
