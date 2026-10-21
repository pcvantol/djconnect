# Current recording → Track Insight v1

This additive Core producer is distinct from the unchanged
[explicit Moment detail](MOMENT_TRACK_INSIGHT_DRILLDOWN_V1.md). Apple owns
native request selection, playback identity and response acceptance. Source
implementation, protected delivery, installed readback and native acceptance
are separate gates; this document grants no provider or model authority.

## Choice and response

The existing paired Track Insight endpoint accepts this closed selector:

```json
{"track_insight_subject":{"schema_version":1,"mode":"current"}}
```

Feature detection is `capabilities.current_track_insight_subject_v1: true` and
`contract_versions.current_track_insight_subject: 1`. This is implementation
support, not current provider readiness. Existing device identity, bound Profile,
privacy and transport guards still apply. Ordinary requests without an explicit
Moment selection resolve Now Playing and never inherit the last published Moment.
Existing explicit artist/title requests retain their legacy behavior.

The current selector rejects simultaneous `track_insight_target`,
`conversation_context`, `track`, `playback`, `media`, title/artist/album aliases,
entity/player/backend/provider overrides, `uri` or `media_identity`, including
null values. Client display metadata cannot become recording authority. Language,
normal paired identity and ordinary presentation options remain supported;
client `source` cannot relabel current detail as a Session publication.

A successful response retains the shared Track Insight fields and adds:

```json
{"subject":{"schema_version":1,"mode":"current","media_identity":"spotify:track:aaaaaaaaaaaaaaaaaaaaaa","observation_id":"opaque-runtime-observation","expires_in":29,"expires_at":1792615000.0}}
```

The values above are illustrative synthetic data, not a receipt or grant.
`media_identity` identifies the exact recording/version, not its title.
`observation_id` is an opaque ephemeral observation epoch, not an executable
reference. Normal progress does not change it; observed A→B→A, pause/resume,
backward seek over five seconds, output/source/owner context change or original
deadline expiry does. Even the same recording under a new account/source receives
a new opaque epoch after a fresh actual observation.
An unchanged observation retains its original thirty-second deadline. Original
CC0 source or genre deadlines can only shorten it. A fresh actual observation
after expiry can establish a new epoch; a cached analysis does not establish one.
Responses from a cache use freshly observed metadata and current subject proof,
never cached playback position/state or a previous observation identifier.

Consumers must capture their current playback/request epoch before requesting,
reject completion after a local track/owner/selection change, match the exact
recording identity rather than names and discard expired proof. No current URI
in an older client DTO means that client adoption remains incomplete; titles
alone are not a substitute. Selecting Moment A continues to analyze A even when
B plays, and malformed/unavailable A never falls back to current B.

## Source, lifetime and side effects

Current mode uses the existing read-only Spotify playback observation, with a
bounded three-second read before analysis and another before cache/response
acceptance. It requires a canonical exact track URI and actual playing/paused
metadata. It never uses arbitrary HA entities, another backend, guessed names,
old Runtime playback or a last published contribution as fallback. Active Session
membership is not required. Unsupported current-mode providers return typed
unavailable while their existing legacy detail paths remain intact.

A single ephemeral frame beside the existing Runtime follows accepted normal
playback updates and the existing Session observation owner. It is not another
producer, history, Profile, persistence, scheduler or grant cache. Unrelated
Runtime notifications cannot replay old `last_playback` into the frame. Owner,
account/provider, current Profile/privacy grant, current Session/opportunity
identity/generation and confirmed presentation changes close in-flight work.
Every awaited source/model/final read is followed by the original guard; the
same guard is registered for final transport admission. A late response or
cancellation cannot populate the shared bounded analysis cache. Changes which
have not been observed cannot be claimed detected; clients retain their own
current-playback fence and the proof has a short original lifetime.

The existing exact-artist genre helper may supply display-only `track.genres`.
Its original owner/source deadline remains intact. Catalog identity, names,
artwork and genres do not grant model ingestion. Only the already qualified
current CC0 recording/work-credit context can enter the existing guarded
analysis and independent assessment path. The original Session backend, account,
provider entry and provider account must match the current qualified binding;
reuse the existing source authority before selection and in the retained guard.
Every current Session-CC0 route uses this join, including ordinary requests
without a selector; legacy provider lookup captures it before awaiting status.
Missing/mismatched original source is not repaired by a fresh same-URI playback
read and supplies no model context. Without it, useful actual metadata
is accompanied by `analysis.basis: unmeasured_metadata_only_v1`, null numerical
audio attributes and no model call. No invented energy, BPM or danceability.

The closed current selector changes no playback, output, Session, Moment count,
Profile, Music DNA, conversation history or speech. Ordinary legacy requests
retain their existing normal status path and opt-in-aware empty-record
bookkeeping; they receive no new model/source authority from that path. Existing provider credential refresh
is still owned by the existing adapter; changed credential/source scope may
conservatively refuse an in-flight request rather than transfer its authority.

## Errors and qualification

- `400 invalid_track_insight_subject`: malformed/mixed selector; no provider read.
- `404 current_track_unavailable`: no verified current recording.
- `503 current_track_unavailable`: unsupported provider or failed/timed-out read.
- `409 track_insight_context_changed`: observed source, context or lifetime changed.

Existing pairing/owner/withdrawal failures preserve their original typed status.
New current-mode messages are centralized in all five languages. Existing rate,
cache size, model qualification and explicit Moment admission remain unchanged.
Core causal tests cover exact same-name versions, old published A/current B,
CC0 reuse, cache hit/miss, current and final provider waits, observed A→B→A,
pause/seek/progress, original expiry, owner/account withdrawal and inert reads.
Native installed/client adoption and joint UI/physical acceptance need their
own owning-lane evidence; these fixtures do not establish them.
