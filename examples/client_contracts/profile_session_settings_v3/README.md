# Shared settings3 and target-aware speech3 — local producer checkpoint

Source pin: `187d2cd126c5db1a2791e1d47d80d803aafc5cc1` (unpublished).
[Actual transport evidence](connected-ha-transport.json) pins all 156 relevant
Python source/helper hashes before/after the same isolated HA run.

Six fields: Persona, provider-bound voice, qualified gender, Mood, Presence,
`announcement_output`. HTTP and paired TLS iOS/macOS protocol surfaces use the
same canonical Profile/Session values. These are synthetic identities, not
physical Apple apps. Existing case labels containing `all_five` are retained raw
runner labels; `shared_parameters` and actual response fields explicitly contain six.

The 120.049-second run made 351 owner reads and two actual TLS reconnects,
with identical settings/session/operation row counts before/after. Other-Profile
invalidation events: zero. Actual HA Cloud entities/inventory, Runtime, SQLite,
HA media-player services and constrained media-fetch HTTP routes are real.
External music knowledge, waveform bytes and speaker sink are explicit fixtures.

One manual speaker replay produces one mediafetch despite operation retry.
One actual new Session opening produces one automatic mediafetch, including
lowercase HTTP authorization. Reads and output switches produce zero catch-up.
Text-only and Session end deny old fetches with404. Queued does not prove audible
playback. No native, installed, physical speaker or joint acceptance is claimed.

Use settings contract3 on existing GET/PATCH/operation routes and paired settings
subscription/update. A prepare3 request selects `intent` and `target`; local
uses `/speech/prepare`. Manual speaker/both uses existing
`/transport/operation`, operation `session/speech/play`, exact live
`{session_id,moment_id}`. Automatic speaker effects are Core-publication-only;
clients cannot manufacture them. Keep the returned per-target outcomes separate.

The speaker grant never appears in client results/shared projections. It lives
inside the existing private byte owner, expires on both UTC and monotone30s,
allows at most four fetches and revalidates source, pairing, settings and target.
Existing paired POST audio assets are not exposed by legacy GET audio.

Treat revisions/bindings/UUIDs as historical examples, not reusable credentials.
Schema7→8 preserves existing choices and immutable receipts; old contract2
acceptance does not establish output consent. Initial migration review requires
six explicit choices. Existing schema1 exports remain unchanged and do not back
up shared defaults; the unpublished schema2 export prototype is retired, and its
restore is rejected. Chat/DNA portability remains parked.

[Canonical contract](../../../docs/product/PROFILE_SESSION_SETTINGS_CONSOLIDATION_V1.md).
Final candidate review, source publication/protected delivery and separate
Finalization are still required. No consumer writer or native work is started.
