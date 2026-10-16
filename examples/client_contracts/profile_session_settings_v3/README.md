# Shared settings3 and target-aware speech3 — local producer checkpoint

Source pin: `b58644bcc843d191aa95c87ec2e14cc9c099454b` (unpublished).
[Actual transport evidence](connected-ha-transport.json) pins all 158 relevant
Python source/helper hashes before/after the same isolated HA run.

Six fields: Persona, provider-bound voice, qualified gender, Mood, Presence,
`announcement_output`. HTTP and paired TLS iOS/macOS protocol surfaces use the
same canonical Profile/Session values. These are synthetic identities, not
physical Apple apps. Existing case labels containing `all_five` are retained raw
runner labels; `shared_parameters` and actual response fields explicitly contain six.

The 120.9-second run made 354 owner reads and two actual TLS reconnects,
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

The ordinary paired legacy Session start without Mood, Ask DJ1, prepare1 and settings read are exercised before activation. Unknown Mood remains null in the settings projection with a full-selection requirement; the long help contribution returns the existing typed `source_processor_not_qualified`, not synthesized audio. Owning tests separately qualify legacy speech, full six-field activation and the first real Mood interval without inventing earlier coverage.

[Four browser receipts](browser-compatibility.json) qualify both shared builds in portrait/landscape through reconnect, original expiry and end, with no private speech/settings leak. CAF remains modeled. Historical source187/source620 fixtures are preserved under history/.
