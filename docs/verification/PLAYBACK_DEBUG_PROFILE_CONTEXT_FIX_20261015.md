# Profile-bound playback DEBUG hotfix — 2026-10-15

Historical local qualification at source94. Current protected delivery and
installed Core HA-dev evidence: [exact readback](PLAYBACK_DEBUG_PROFILE_CONTEXT_SOURCE_READBACK_20261015.md).
The readback separately records Apple's physical iPad retest for the three
repaired screens; broader native acceptance remains open.
Base: `a6d666fea7f30254b20bea015fad8d1fd8d7b059`. Same existing Core writer;
branch `codex/playback-debug-context-hotfix-v1`. Speech PR1177 remains frozen at
533fa48c and retains its own exact merge gate; this urgent maintenance repair
changes no Speech source or reviewed candidate.

Peter authorized forwarding the confirmed physical iPad HTTP500 cause from the
existing Apple lane (human reply01a14101-b0b9-71e2-8850-41b30e938d90). The actual
trace reaches `api_handlers._debug_playback_request` before command dispatch,
then calls `music_backend_metadata(None, runtime)`, whose current Profile-bound
provider resolver correctly rejects missing HA authority. The same mistake
appears in six playback/queue/playlists request/result diagnostics. There is no
basis to reset pairing or merge Profiles.

Diagnostics now use only the existing resolved backend identifier and last
observed availability. Missing availability remains unknown, not inferred from
credentials. Logging does not resolve live providers or perform additional HA,
Profile, network or storage work. The ordinary command dispatcher and metadata
owner keep their original authorization, validation, errors and output; there
is no blanket exception handler or successful empty playback fallback.

[Actual before/after HTTP fixture](../../examples/client_contracts/playback_debug/profile-bound.http.json)
uses ordinary device pairing, loaded real HA entries, real persisted Profile/
account/provider reference and the normal owner HTTP route. Only external
Spotify HTTP I/O/session is fixture; all requests are GET and cannot change
real playback. Baseline DEBUG gives500 for status/queue/playlists; INFO gives200.
Corrected DEBUG and INFO both give200. Missing bearer remains401 with zero extra
provider calls. Removing the real provider runtime yields the same structured
error at INFO/DEBUG, not a swallowed error or a diagnostic500. Device→Profile,
provider entry binding and caller credential separation remain unchanged.

A focused causal test fails at all six debug helpers before the correction and
passes afterward while forbidding any live metadata resolver calls; existing
logging tests still check omission of private titles, artist names, URIs and
secrets.42 logging/Profile owning tests pass; full regression runs1950tests,
with1943passes and7existing skips. All140 executed Core Python hashes are retained
in the fixture; only api_handlers.py differs between baseline and corrected run. Initial harness runs failed during
normal HA network/multicast setup in the networkless container; those are not
product proofs. The successful v3 runs use an explicit external-provider HTTP
session boundary and exit0 normally.

At the original local qualification no runtime was installed/restarted. No
pairing/Profile reset, playback change, Swift
write, deployment or hardware acceptance was claimed by that local qualification.
Subsequent exact independent review, protected delivery and installed/consumer
readback are recorded in the linked report.
