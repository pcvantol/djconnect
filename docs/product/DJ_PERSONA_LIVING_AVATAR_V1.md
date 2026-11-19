# DJ Persona Living Avatar v1


19October touch source is now protected-delivered by [#1217](https://github.com/pcvantol/djconnect/pull/1217),
merge`37a574c9e4f6b366ea2335a6c087d649d09afc2d`. The separate touch contract is source-qualified;
installed discovery, native gesture/audio and HA-speaker acceptance remain OPEN.
Earlier local/basic-signal notes below retain their original stage boundary.


19October continuation: the selected explicit touch addition is implemented in
the separate local [touch producer candidate](PERSONA_TOUCH_REACTIONS_V1.md).
The original gap/proposal below describes the protected basic-source baseline;
the new contract separately qualifies its exact wire, limits and local speech.
It is not an installed/native/HA-speaker touch acceptance or whole-function close.

Status: basic Core design/source delivered by [PR #1215](https://github.com/pcvantol/djconnect/pull/1215),
merge `d19dc33d27d799b8c1a868fc57164872e1e67ed8`. Existing-signal
qualification is separate from touch-producer implementation. Touch wire/limits
remain NOT_FROZEN / NOT_IMPLEMENTED until their own producer qualification.
Owner inputs: [Core #1208](https://github.com/pcvantol/djconnect/issues/1208),
[Core #1209](https://github.com/pcvantol/djconnect/issues/1209),
[touch addition6251008548](https://github.com/pcvantol/djconnect/issues/1209#issuecomment-6251008548),
[headphone/inner-glyph refinement6252444250](https://github.com/pcvantol/djconnect/issues/1209#issuecomment-6252444250);
[Apple #126](https://github.com/pcvantol/djconnect-app/issues/126)/
[#127](https://github.com/pcvantol/djconnect-app/issues/127).
These overlapping issues describe one product demand, not two source writers.
No issue/function is closed and no installation, release or native PASS follows.

## Product invariants

The permanent Session Pulse is the user's DJ, integrated INSIDE the one existing
current-card bubble immediately below album artwork. No new persistent bubble,
new Persona value, Moment type, player visualization or ambient background task.
The current owner refinement supersedes the earlier broken-ring reference: a
complete circular Pulse ring, outside headphone headband and two rounded earcups
remain the stable Apple-owned vector/SwiftUI identity. The dark inner core uses
a contextual waveform/microphone/chat/note/dots symbol; Mood tint is independent.
The same simplified static headphone/Pulse mark replaces the DJ Session menu
opticaldisc symbol. Missing album-art turntable remains intact.
The transient touch overlay described below is the explicit exception to the
no-extra-bubble rule; it never becomes another permanent card.

Identity, activity, selected Mood and Presence are independent. Existing four
Persona values remain home_dj/radio_dj/club_dj/festival_dj. Existing confirmed
Mood is chill/groove/energy/party. Presence2 remains exactly music_only,
occasional, balanced, presenter. Artwork tint never becomes selected DJ Mood.

## Observed producer and consumer mapping

| Meaning | Existing authority / data | Consumer disposition |
| --- | --- | --- |
| Session identity/lifecycle | DJBroadcastState.session_id/runtime_state; ordinary owner snapshot/recovery | Bind all asynchronous work to current install/Profile/Session/connection generation; replacement/withdrawal invalidates old work. |
| Mood | selected_mood + mood_revision in Runtime/Broadcast and confirmed settings3 | Only current authorized revision can recolor; unknown uses neutral stable identity. |
| Persona | dj_persona + persona_revision | Behavioral/text identity, no inferred TTS voice or new Persona selection. |
| Presence | selected_presence + presence_revision; capability2/four policies | music_only prevents proactive substantive Moments; explicit Ask DJ and permitted replay continue without policy/budget reset. |
| Intentional Silence | native_delivery.current_silence_moment_id, matching admission qualification intentional_silence and current Session | Rest unless a genuine user interaction or actual speech currently has priority. Distinct from empty Moment, outage and music_only. |
| Current contribution | native_delivery.current_moment_id + actual admitted immutable Moment and original display/source deadlines | Preserve text/actions/art/attribution/history. A visual card alone never means speech. |
| Ordering/recovery | delivery_sequence, existing recovery cursor and admitted owner snapshot | Existing replay/snapshot reconciliation; never mint renewed content or speech grants from reconnect. |
| Listening | actual Apple microphone capture/recognition lifecycle | Local presentation only; never infer an open microphone from Session/music/pending server text. |
| Thinking | actual pending owner request/known local preparation, bound to its operation generation | Stop on completion/cancel/error/deadline; do not claim unobserved Core planner/model activity. |
| Speaking | actual playback-start/playing/end/interruption evidence at the audio renderer | Audio preparation, returned text, ready bytes and service acceptance are insufficient. |

Basic avatar display/state mapping does NOT demonstrate a need for a new Core
endpoint, broadcast activity state, heartbeat, timer-based Moment or server
animation field. Existing private owner transport already carries the Session,
Mood/Persona/Presence, current Moment/Silence and ordering/recovery semantics.
Broadcast-token receiver rights never authorize Apple owner actions or Ask DJ.

## Actual source findings requiring Apple owning follow-up

Inspected Apple baseline: `c012e5456d0b1eabbb390fc4d5b42ffb9cd13170`.
At that committed baseline, `NativeSessionMomentsView.currentCard` has unavailable/recovering,
paused, MomentCard and quiet/empty branches, all under the existing
`session-current-card`. Each branch must keep that one permanent home and preserve
its current recovery controls and accessibility. `SessionTimelineScreen.currentHeader`
is the integration anchor. At that baseline `DJConnectFeatureSymbols.djSession` maps to
`opticaldisc` in DJConnectRootView. The owning Apple writer has since begun local graphics WIP. That WIP is not
consumer/native acceptance, and Core has not edited Apple source.

Both current speech flags are too early to prove actual avatar speech:
`DJConnectAppleSpeechRenderer.speak` sets isSpeaking/onStateChange(true) before
AVSpeechSynthesizer.speak, without a didStart confirmation. The HA-client-audio
runtime sets .playing before services.play. They are request/admission signals,
not physical output evidence. Apple must add/use renderer start/end/interruption
callbacks with utterance/playback ticket identity, and qualify real outputs.
Do not simply bind avatar speaking to those existing optimistic flags.
HA-speaker service acknowledgement likewise must not pretend observed audio;
unobserved remote output cannot drive a synchronized speaking animation.

## Presentation reducer requirements (Apple owned)

First enforce owner/install/Session/connection/lifecycle validity. Preserve visible
outage/recovery/paused messages; neutral/rest does not hide transport failure.
Among current admitted activities, explicit capture/request and actual speech
have priority over proactive preparation and Silence-derived rest. Existing
audio focus/cancellation resolves conflicting capture versus speech; never claim
both based on independent stale flags. Text-only responses may return directly
from thinking to rest. End, replacement, background, cancel, provider failure,
revocation and stale callback return to the authorized neutral/rest baseline.

Animation/glow uses bounded native rendering and actual sound envelope only if
available; otherwise no fake lip sync. Local animation/dismissal timers do not
claim inference, microphone activity or a new publication. Keep per-frame work
inside the avatar subview, never the whole Flow/timeline. Preserve VoiceOver,
Dynamic Type, Reduce Motion/Transparency, contrast, low-power/thermal behavior,
scroll/hit targets and iPhone/iPad/Mac layouts; assess Watch within its actual
native surface. Widget/ActivityKit/Island passive rights are separate.

## Contextual inner glyph - existing typed evidence only

The outer identity remains anchored. Apple confirms its deterministic local
precedence against actual activity owners, with no new server avatar enum:

| Inner meaning | Required evidence | Exclusions |
| --- | --- | --- |
| Waveform/rest | Authorized neutral/default; also explicit Silence or music_only when no genuine foreground interaction takes priority | No implied open mic, pending work or proactivity. |
| Microphone/listening | Actual authorized voice capture currently running | Voice request arrival, STT preparation and old recording flags are insufficient. |
| Three dots/preparing | Current valid accepted operation or actual local speech preparation remains pending | No thinking timer during Silence or idle snapshot reads. |
| Music note/announcement | Same-Session, currently admitted immutable music-announcement contribution with original source/display deadlines | A generic track story or artwork alone is not an announcement. |
| Microphone/speaking | Actual admitted ordinary speech renderer start, bound to its original turn/Moment/ticket; clears on end/interruption/error | Ready audio bytes, text arrival, dispatch flags and HA speaker service acknowledgement are insufficient. |
| Chat/text | Accepted current text Ask DJ response, not superseded by actual capture/work/audio | Do not infer a new response from historical cards or copy their media. |

For the existing observed-playback announcement, the public Moment has
`type:track`, `knowledge_intent.type:track_context`,
`generation_metadata.context_source:observed_playback`, and
`source_references:[spotify_playback_status]`. These typed values describe its
provenance only. They must match the current immutable Moment and its current
`native_delivery.current_moment_id`/qualified admission, owning Session and
original display/source deadlines. `type:track` alone also covers factual track
stories and cannot select announcement behavior. Forged metadata, expired source,
revoked owner, pause/end or replacement Session cannot retain a current note.
This classification grants neither playback authority nor additional TTS rights.

The owner precedence is genuine voice capture, then valid pending work, then an
accepted current music-announcement contribution, then other actual speech,
then text response, otherwise waveform/rest. Crucially, bind content precedence
to the contribution/turn actually being presented or played. An older retained
current-card Moment cannot mask a newer explicit Ask DJ interaction. A spoken
music announcement may keep its note for that same contribution, avoiding
note/microphone flicker; a different ordinary Ask DJ speech ticket is distinct.
Apple owns arbitration and must qualify these bindings against its real reducer.
Unknown or conflicting provenance falls back safely without hiding recovery UI.

Only the inner glyph morphs/crossfades; the outer ring/headphones stay anchored.
Reduced Motion uses a static transition. An actual audio envelope may drive a
bounded effect; absent an envelope, never imply synchronized lip movement.
No current/backend flag proves physical audibility. Touch overlays retain the
separate admission/output/lifecycle requirements below.

## Touch reactions — demonstrated separate producer gap

The source audit found no dedicated admitted persona-touch operation/capability,
no reaction-specific one-pending/cooldown policy and no qualified ephemeral
reaction-output contract. Existing ordinary Ask DJ may create conversation/Flow
history. A hidden fabricated chat question is not proof of the touch contract.
Do not create a fake DJMoment solely to gain speech or HA-speaker permission.
Until this gap is qualified, the consumer must not dispatch a server reaction or
promise spoken touch behavior. Keep a safe non-requesting/disabled representation.

Candidate design to review, NOT an implemented/frozen wire:
reuse the existing paired operation/journal path for a bounded semantic reaction
operation rather than create another HTTP transport. Bind exact initiating
Profile/device/active Session generation and confirmed Persona/Mood/settings
revisions; use existing UUIDv7 conflict/expiry/owner/admission rules. Accept only
closed reaction kinds after Apple gesture arbitration. Never accept caller
speech text, forged facts, prompts, destination or replacement Persona/Mood.
A distinct advertised capability and actual producer fixture must precede live
consumer use; unknown/absent capability denies the reaction.

One single/double/triple gesture sequence produces at most one semantic request
and one visible/audible result. No single+double+triple cascade. Accessible action
must expose the same available fun behavior without requiring triple tap.
Only one pending/playing reaction per owner Session; no queue. Proposed initial
limits for review are a minimum10s between new reactions and maximum6 per
rolling10min per Profile/Session, with exact duplicates retaining original
receipt/deadline and never new synthesis/generation. These numeric limits are a
proposal, not an advertised current policy or a user-configurable extra setting.

Use the existing bounded accepted-reply/speech owners where qualified. The text
is ephemeral private feedback, not a proactive Moment or durable extra Flow
card. No prompts, audio, private context or text body in durable dedup receipts.
Reuse literal accepted text for replay; never generate a new joke on retry.
Use the active confirmed Persona/Mood and one of the five existing languages.
Curated localized playful fallback may be fast and varied; optional genuinely
contextual realization must use the existing HA conversation agent, bounded
calls/cost, admitted facts and ordinary semantic/source checks. No invented
artist/song facts, fabricated memories or consciousness claims, no new web/model
calls on rest, ambient animation, snapshot/reconnect or background.

The existing speech prepare contract can read accepted turn_id replies on the
initiating device using local_on_device or HA-prepared client audio. Any reaction
integration must actually qualify its accepted source/ref lifecycle. Existing
HA-speaker play support is Moment/qualified retained-entry scoped; an ephemeral
reaction is not automatically covered. Speaker/both output needs explicit
producer qualification or truthful text-only feedback, never an invented Moment
or silent destination substitution. text_only policy forbids reaction audio too.
No microphone use, abrupt music interruption, new volume override or automatic
fallthrough between processors. Actual playback start alone permits speaking.

music_only does not suppress an explicitly admitted reaction, as with Ask DJ,
but does not acquire that admission merely from a tap. Never change Presence,
reset proactive ledgers or publish an unsolicited Moment. Dismiss overlay and
cancel its owned pending/play work on background, Session/owner change, dismiss,
Ask DJ foreground, speech conflict, failure or expiry. Late callbacks are inert.
The overlay is centered/short-lived/nonmodal, respects safe areas/rotation and
controls, has dismissal/accessibility parity and never appends itself to history.

## Required qualification and honest closure

1. Basic producer trace: current Moment -> explicit Silence -> empty -> paused/
   recovery, original source expiry and owner revocation; same Session revisions
   and no extra Moment/publication/transport side effect.
2. music_only + explicit Ask DJ actual capture -> pending -> actual playback ->
   rest, plus text-only/error/cancel; unchanged Presence/ledger and no proactive
   publication. Do not infer this whole chain from isolated existing unit tests.
3. Older Session/operation/settings/Persona/Mood response, reconnect gaps and
   complete snapshot: no stale recolor, speech restart or card resurrection.
4. Gesture cardinality, accessible alternatives, cooldown/dedup/capacity,
   concurrent devices, caller cancellation, repeated unknown outcome and
   revocation; zero duplicate model/lookup/synthesis/playback effects.
5. Four Persona x four Mood x five locales: actual returned reaction texts,
   provenance/safety, recognizable varied style, original speech segments,
   text-only and both available client audio processors. Speaker/both remains
   an explicit target-qualification gate.
6. Inner glyph qualification: Silence/music_only -> waveform, actual capture vs
   non-recording, pending work vs playback, same spoken announcement keeps note,
   ordinary speech -> microphone, accepted text -> chat, cancellation/reconnect/
   successor Session -> safe waveform. No older contribution masks a new turn.
7. Exactly one permanent bubble below artwork through every branch, preserved
   contribution/art/actions/scroll, matching static navigation glyph, unchanged
   missing-art fallback. Reduced-motion/contrast/VoiceOver/locales and measured
   per-frame/RSS/thermal/native screenshots/real-device audio acceptance.
8. Independent review, scoped regressions, actual ordinary paired producer
   fixtures if changed, protected source and separate Finalization, exact-main
   and installed readback where selected. DESIGN_CANONICAL, SOURCE_DELIVERED,
   INSTALLED and NATIVE_ACCEPTED stay separate. No function closes from merge.

Qualification results must name the exact source/fixture boundary. Existing test
names alone are inventory, never native avatar or touch-route PASS. Protected
source and separate Finalization do not close the function: installed rendering,
actual audio, touch admission and cross-platform acceptance remain independently
OPEN. No consumer work, release, deployment or new assignment is dispatched by
this document.
