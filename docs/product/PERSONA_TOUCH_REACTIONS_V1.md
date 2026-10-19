# Explicit Persona touch reactions v1

Status: protected Core source delivered by [PR #1217](https://github.com/pcvantol/djconnect/pull/1217),
in the already selected #1208/#1209 avatar task,
owner addition6251008548; merge`37a574c9e4f6b366ea2335a6c087d649d09afc2d`; not an installed pin or native acceptance.
The [basic avatar contract](DJ_PERSONA_LIVING_AVATAR_V1.md) remains delivered.
This increment fills its demonstrated ephemeral reaction gap without changing
the ordinary Ask DJ, Moment, Flow or transport owners. No consumer is dispatched.

## Bounded user interaction

One explicit semantic request produces one short-lived personal-DJ line. It is
not a chat question or a proactive DJMoment. No Flow entry, history text, lookup,
model call, playback command, Presence change or proactive-budget reset occurs.
The existing current bubble stays authoritative. Apple owns the single transient
centered overlay, gesture arbitration, accessible action, dismissal and native
renderer. A multi-tap sequence must dispatch at most one semantic request.

Content uses the confirmed active Session Persona/Mood and one of en/nl/de/fr/es.
The [actual literal catalog](../../examples/client_contracts/persona_touch_reaction_v1/curated-texts.json)
contains240style/kind cells and480variants. This intentionally uses the owner's
fast curated fallback, with no asserted track/artist facts, invented memories or
consciousness. It does not replace researched/LLM-enriched ordinary DJ stories
or qualify their still-open writing-quality findings. Same-cell repeated new
reactions alternate their clause, without regenerating content on a retry.

## Existing paired operation envelope

Discovery is additive at `active_session_persona.touch_reaction` version1. Only
the ordinary paired operation owner may accept it, through its existing HTTP or
paired WebSocket transport. Discovery is not authority. No new HTTP endpoint,
broadcast activity flag, anonymous media URL, Persona enum or screen grant.

Operation `session/persona/reaction`, payload exactly:

```json
{
  "contract_version": 1,
  "session": {"session_id": "<current>", "generation": "<confirmed>", "revision": 3},
  "kind": "check_in",
  "language": "nl",
  "processor": "local_on_device"
}
```

The outer contract1 envelope requires the current operation epoch and a fresh
UUIDv7 `operation_id`; this ID is also the reaction ID. `session` comes from the
confirmed Settings3 snapshot. Closed kinds are check_in/playful/easter_egg;
they are semantic choices, not Core-owned gesture allocation. Processor is only
local_on_device or ha_configured. No caller text, prompt, Profile, voice, gender,
Mood, Persona or speaker override is accepted. Stale Session generation/revision,
unconfirmed settings and unavailable Session reject before content/synthesis.

The result is `persona_reaction` with original reaction/session identity, exact
literal text, locale/kind/confirmed Persona/Mood, original expiry and dedicated
speech descriptor. `source_kind:core_owned_persona_reaction` is not an accepted
Ask DJ turn or Moment reference. Text/speech stay private/no-store and expire
within30seconds and the original operation deadline, whichever is earlier.
No read/retry/reconnect extends them. A duplicate returns only the original
operation receipt (pending202 or final outcome), never another line or audio.

## Admission, concurrency and cancellation

At most one pending/playing reaction across devices in one Profile/active Session;
no queue. Minimum10seconds between admitted new reactions and maximum6 in a
rolling600seconds, tracked on the server monotonic clock. Cancellation and
settings changes retain those timestamps. Bounded state covers at most64active
Session buckets and reuses the existing64-slot private speech-source limits.
No unexpired evidence is evicted to admit another reaction.

The initiating device alone can explicitly cancel through operation
`session/persona/reaction/cancel`, payload exactly:

```json
{
  "contract_version": 1,
  "session_id": "<original>",
  "reaction_id": "<original UUIDv7>",
  "reason": "dismissed"
}
```

Reasons are completed/dismissed/background/ask_dj_foreground/speech_conflict.
This is a new cancellation intent with its own outer operation ID, not reuse of
the original execution ID with another payload. The cancellation is content-free
and idempotent after expiry, with no history clear, music stop or budget reset.
Another device cannot cancel/read the initiating device's result/audio, but
shares the busy/rate boundary. Lost socket delivery alone retains the existing
single execution; reconnect reads its receipt rather than creating a fresh tap.

Core withdraws pending/held text and byte grants on accepted ordinary Ask DJ,
configured voice preview or accepted manual contribution speech; Session end,
replacement, pairing/Profile/source/settings/provider withdrawal and expiry are
also fenced. An in-flight provider completion cannot return old audio afterward.
Apple still must stop/dismiss its actual renderer and overlay on those events,
background, user dismissal and actual completion. Core expiry does not prove a
native renderer has stopped already-downloaded bytes. Late callbacks are inert.

## Speech and explicit target boundary

`local_on_device` supplies exact accepted segments and renderer_pending; it
requires no configured HA voice and makes no server synthesis call. It does not
override native voice/pitch settings or imply actual audio start. `ha_configured`
reuses the existing HA Assist provider/voice/gender, literal speech preparation,
current Mood prosody policy, private authenticated POST bytes and provider/change
fences. No system/provider fallback, microphone capture or direct external API.
Prepared bytes are available only to the initiating paired device. A missing provider leaves the admitted textual line with typed speech feedback.
A configuration change during admission rejects the stale reaction with a typed
configuration-changed notice and zero synthesis. Neither case produces a false ready/speaking state or a different processor.

Confirmed output governs what is prepared:

| Output | This version's reaction delivery |
| --- | --- |
| client_device | Selected client processor only. |
| text_only | Text only, zero synthesis/audio grants/speaker calls. |
| ha_speaker | Text only, explicit speaker_not_qualified; no substituted client audio. |
| both | Authorized client component plus explicit speaker not_qualified; no speaker call. |

HA-speaker reaction output is deliberately not advertised: an already playing
announcement lacks a separately qualified cancellation/mixing owner that can
stop just this ephemeral reaction without interfering with music. The existing
Moment/retained-speaker and neutral Preview contracts remain unchanged. A later
speaker qualification must prove its own actual cancel/output behavior; an
announcement service acknowledgement is not that proof. The consumer must show
partial/unavailable target feedback rather than claim full output delivery.

Speech preparation/result arrival never drives speaking. Apple binds actual
start/end/interruption to the original reaction/ticket, stops local playback on
expiry/cancel and arbitrates existing speech/capture. Local autoplay controls for
unsolicited Moments do not become a new server autoplay grant. The initiating
explicit gesture and current output policy are both necessary for this reaction.

## Qualification and remaining gates

Core owns paired authority, immutable context, rate/dedup/expiry, source-free
literal content and private audio fencing. Owning regressions exercise these
actual Core owners with synthetic HA/provider boundaries. Exported literal
texts and actual operation outcomes are review material, not native screenshots,
physical hearing or a connected installed qualification. Golden adds this
reaction/cancel chain and retains all previous open findings plus its explicit
native/gesture/audio acceptance step. No existing release gate is cleared.

Native single/double/triple arbitration, accessibility alternatives, one overlay,
no permanent extra card, actual processor playback/stop, background/reconnect,
VoiceOver/Reduced Motion/layout/performance and five-language device acceptance
remain Apple-owned and OPEN. HA-speaker reaction qualification remains OPEN.
Protected source, separate Finalization and any authorized exact development
installation/readback remain separately required. A merge cannot close the
whole avatar function or other lane slices.

## Withdrawal observation and pre-admission cancellation — follow-up candidate

The accepted v1 producer above did not give a native consumer a continuing
withdrawal signal after delivery and forgot cancellation that preceded original
request admission. Apple #127 correctly keeps touch disabled for these gaps.
The following is an additive **source candidate**, not installed discovery or
permission to activate touch. Existing operation payloads and literal catalog
remain v1. Recognize both the nested `withdrawal_contract.version:1` and
`cancel_before_admission:durable_original_uuidv7_fence_until_operation_deadline`
in `active_session_persona.touch_reaction` before using this follow-up.

### Observe before display or playback

Use the existing authenticated `paired_owner_actions` WebSocket at
`/api/djconnect/v1/actions/paired`, authenticated as the same initiating device.
A confirmed durable operation receipt is only an outcome; it never proves
continuing permission to display text or play downloaded audio. Hold the original
reaction privately until this command returns a current `state:valid`:

```json
{"type":"djconnect/persona/reaction/observe","id":1,"contract_version":1,"operation_id":"<original UUIDv7>","operation_epoch":"<original current epoch>","session_id":"<original Session>"}
```

A successful frame uses the existing request/connection correlation envelope:

```json
{"type":"result","id":1,"connection_id":"<paired connection>","success":true,"status":200,"result":{"success":true,"reaction_observation":{"contract_version":1,"observation_id":1,"reaction_id":"<original UUIDv7>","session_id":"<original Session>","state":"valid","expires_at":"<original deadline>","cache_policy":"private,no-store"}}}
```

Validate exact original connection, observation request, reaction, Session and
unchanged expiry before displaying/starting. A queued result is requalified after
the final authority await at actual send: it may already be `state:withdrawn`.
Unknown/foreign/stale source is404 `persona_reaction_unavailable`; wrong epoch
is409 `operation_epoch_changed`; an existing live observer is409
`persona_reaction_observer_busy`. One observer per reaction and one per connection;
there is no unauthenticated subscription or Broadcast announcement.

When current source/provider/settings/Session/authority admission withdraws,
the initiating connection receives one content-free invalidation:

```json
{"type":"event","id":0,"connection_id":"<paired connection>","event":"session/persona/reaction/withdrawn","reaction_observation":{"contract_version":1,"observation_id":1,"reaction_id":"<original UUIDv7>","session_id":"<original Session>","state":"withdrawn","expires_at":"<same original deadline>","cache_policy":"private,no-store"}}
```

Stop playback, dismiss the overlay and purge private text/audio on withdrawal,
connection loss, auth failure, malformed/mismatched observation, local lifecycle
cancellation or the original deadline. Never resume downloaded content from a
confirmed receipt, cached `valid`, HTTP-only execution or a new socket. A source
that lost its observer is withdrawn and is not reattached to continue playing.
A new explicit user intent may be admitted only under the existing cooldown and
busy limits. No retry/reconnect/status read renews the original deadline.

A bounded server-local source guard rechecks every0.25seconds while observed.
This is a guard cadence, **not** a network delivery SLA or proof that an actual
speaker has stopped. Existing connection lease/queue/worker limits are unchanged;
slow consumer/auth loss closes the connection and requires native stop. The
observation contains no text, speech segments, provider credentials or audio.
Actual output callbacks alone drive `speaking`; observation validity is not audio
start. HA speaker reaction output remains explicitly unqualified.

### Cancellation before the original request arrives

The existing `session/persona/reaction/cancel` operation still has its own fresh
outer UUIDv7 and carries the original `reaction_id` and Session. Before reporting
success, Core writes a durable, content-free target fence, even if the original
execution has not reached reservation. The original UUIDv7's five-minute operation
deadline is immutable; the separate reaction source still has its shorter
maximum30second lifetime. Future timestamps outside the existing clock allowance
reject, expired non-executable targets need no new slot, and cancellation does
not reset cooldown or proactive budgets.

The fence binds the initiating device, resolved Profile/binding and original
epoch. Unknown-target fences are device-scoped, so another paired device cannot
preempt an unadmitted intent by naming its UUID. Restart or rebinding cannot
reclassify the old UUID as a new intent. A delayed original returns the cancelled
receipt with409 and no new text/provider/synthesis. A cancelled running intent
cannot be overwritten by late success. A previously confirmed receipt remains
confirmed, but its content grant withdraws; a receipt never substitutes admission.

Tombstones share the journal's256global/64per-owner capacity and original expiry;
unexpired evidence is not evicted. Capacity failure is429, not cancellation
success. A failed/uncertain durable save closes the journal to execution until
recovery, rather than acknowledging an unproven fence. The journal stores only
identity digests/IDs/deadlines/outcomes, never reaction text or audio.

[Actual isolated HA request/results and private receipt digest](../../examples/client_contracts/persona_touch_reaction_v1/withdrawal-outcomes.json)
cover both processors' pre-admission cancellation, foreground Preview withdrawal,
actual HA pipeline change after byte download, unchanged confirmed receipt and
observer disconnect. [Follow-up qualification](../verification/PERSONA_TOUCH_WITHDRAWAL_20261019.md)
keeps source/isolated runtime separate from protected delivery, installed HA,
native stop/gesture and audible acceptance. Apple touch stays disabled until its
producer and native acceptance gates pass.
