# Active Session Mood v1

Assignment: `DJC-CORE-ACTIVE-SESSION-MOOD-V1-20261011`.
Admission base: `72598682010683b9276a8bec2a76a0f33bbb9a2b`.
Sole source branch: `codex/active-session-mood-v1`.

This contract is pinned before producer changes. The existing Runtime has
`async_update_mood` and `mood_changed`, but no production client ingress. Its
same-value update currently publishes another event. Actual native Session
start choices are `chill`, `groove`, `energy`, `party`; these existing symbolic
values are independent of Persona, start strategy/direction, Profile preferences
and the legacy Watch numeric mood zones. No new taxonomy or conversion is added.

## Narrow owner transport

`POST /api/djconnect/v1/session/mood`, JSON body:

```json
{
  "contract_version": 1,
  "client_type": "ios",
  "device_id": "djconnect-ios-ABCDEF123456",
  "session_id": "session-example",
  "selected_mood": "energy",
  "expected_mood_revision": 0
}
```

Use the ordinary paired device bearer in `Authorization` and the matching
`X-DJConnect-Device-ID`. Capability discovery advertises version, path, symbolic
catalogue and ordering. Discovery is not authority. No URL credentials, new
pairing, HA/admin token, VibeCast receiver token, service command or general
mutation engine is introduced. The paired-live websocket remains read-only.

The request targets only the exact active Session of the current server-bound
device Profile. No guest/Profile/room fallback or client-selected owner.
Type/version/revision validation is exact: booleans, floats, numbers for mood,
unknown values and implicit default normalization are rejected. The current
registered runtime/entry, enabled/loaded state, device identity/token, lifecycle
generation and server-bound Profile are rechecked under the existing Runtime
lock immediately before any mutation; no await separates that check and commit.

## Ordering and acknowledgement

`mood_revision` starts at zero for each new Session, and increases once for each
accepted different value. A request must supply the currently expected revision.
Under the existing Runtime lock, stale revision is `409 mood_revision_conflict`
with the authorized current `{session_id, selected_mood, mood_revision}`.
Identical value at the current revision succeeds with `changed:false` and creates
no event, Moment or revision. Repeating an earlier request after its accepted
write can therefore return conflict; it cannot undo a newer accepted change.
Two clients using the same expected revision cannot both change the Session.

Success acknowledges one atomic server state, for example:

```json
{"success":true,"contract_version":1,"session_id":"session-example","selected_mood":"energy","mood_revision":1,"changed":true}
```

Same Session value/revision appears together in the ordinary Runtime and
Broadcast snapshot and existing `mood_changed` event/recovery. Clients retain
the highest confirmed revision for that Session. A late response or replay
must not replace a newer revision. On lost response, read the authorized active
Session/snapshot or reconnect through existing paired-live recovery; do not
restart, replay an old setting blindly or infer acceptance from a local picker.
Revision comparison is scoped to Session ID; a new Session starts a new scope.
An acknowledgement or conflict for a previous Session must not change the
currently displayed replacement Session, even with a higher revision. On `409`,
refresh/show the authoritative current choice before a new deliberate action;
do not automatically resubmit the stale intent.

Errors include `invalid_request`, `unsupported_contract_version`,
`invalid_selected_mood`, `invalid_mood_revision`, existing device/Profile auth
errors, `active_session_not_found`, `unauthorized` and `mood_revision_conflict`.
No current private Session state is returned after authority is lost. Responses
are `no-store`/`no-referrer`. Historical/ended Sessions remain readonly.

## Runtime, future Moments and readonly consumers

Only selected mood and its revision change. Session ID/start time/initial mood,
Persona, strategy, playback, queue, backend, history and immutable existing
Moments/presentations remain unchanged. No Moment, provider call or TTS is forced
by a mood setting. Existing eligibility, dosing, opportunities and Silence apply.

A candidate takes its mood/revision at the existing locked planning decision.
If mood changes while asynchronous Knowledge/coordinator work is in flight,
discard that candidate before merging working state, consuming a fact/opportunity
or persisting/publishing. Compare revisions, including ABA changes, rather than
only the final mood string. Work wholly under the lock completes before a queued
mood change. Future independently eligible candidates use the new mood, and
presentation composition uses the same frozen decision context as its Moment.

Shared VibeCast receives only its existing renderer-safe Session mood plus an
additive revision. It gets no owner identity, private question/archive or mood
control. Pi/browser and static renderer both consume the same projection; no
receiver HTML hand patch, renderer fork, Pages rollout or physical PASS.

## Verification and handoff boundary

Capture the actual missing route/capability and duplicate internal event before
producer edits. Qualify ordinary pairing → owner route → accepted update →
snapshot/event → later eligible Moment → reconnect through actual isolated HA.
Include same-value, rapid/two-client CAS, invalid/anonymous/revoked/other-Profile
and Session-end races, delayed replies and readonly receiver refusal; verify
zero rejected-request playback/history mutation. Cover both in-flight candidate
paths and following valid publication, original Moments and Silence.

Send an early exact producer/contract/real-receipt pin to Apple #87's existing
`codex/apple-session-newest-first` pickup. Apple owns native controls and native
acceptance. Artwork comment6108892390 is a separate dependency. Preserve Windows
retirement/provider ownership, Apple text/voice/history/search/live auth, Pi/ESP
and Cast1.1. Native/installed/hardware acceptance and each source/Finalization
publication grant remain separate. Stop after this one Core delivery.


## Ask DJ uses confirmed Mood without setting it

[Shared Ask DJ dialogue](ASK_DJ_CONTEXTUAL_DIALOGUE_CONTRACT_V1.md) consumes the confirmed symbolic value for relevant Session-context answers in one common style projection. It does not convert that value into legacy numeric mood or change settings, playback, Session or immutable Moments. Standalone numeric/Profile Mood retains its own documented source. Temporary conversational refinement is not a Mood update; an explicit setting remains on this existing authorized route. Presence-Off continues to allow explicit answers without proactive publication or history-summary Moment increments.
