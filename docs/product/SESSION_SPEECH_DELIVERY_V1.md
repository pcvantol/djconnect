# Session speech delivery and replay v1

Design-first companion to [Session narration/live Persona](SESSION_SPEECH_PERSONA_V1.md).
One existing contribution and one accepted text; audio is a presentation resource,
never a new DJMoment or conversation turn. Implementation pending.

## Optional owner projection and explicit preparation

`session_speech` contract1 is an optional private-owner capability. Existing
Ask DJ accepted responses and owner Moment/history projections may attach a
speech descriptor. Ordinary GETs/open/search/reconnect never synthesize or
refresh a deadline. Unknown optional schema keeps text/actions usable.

Descriptor: `schema_version`, contribution `source_kind`/`source_id`, optional
`session_id`, immutable `text_revision`, `presentation_revision`, effective
`persona`/`persona_revision`, `locale`, ordered exact `segments`, `state`,
`reason`, original `expires_at`, independent `manual_allowed` and new-publication
`autoplay_eligible`, allowed `processors`, source attribution and `cache_policy`.
States: available,unavailable,expired,withdrawn. A source/audience/processor denial
has no executable text/audio grant. Machine codes stay untranslated; client
copy and accessibility labels require all five languages.

`POST /api/djconnect/v1/speech/prepare` uses normal paired device/Profile owner,
contract1 and exactly one existing target: published
`session_id`+`moment_id`, or retained `session_id`+`entry_id`, or an accepted `turn_id` in the existing
bounded dialogue frame. The latter includes private non-archived early replies;
its original rights/deadline/frame generation apply, without a second store or
archival promotion. Common Ask DJ uses `reference:{turn_id}` consistently on
both screens, including responses with a durable message ID; no message-ID lookup
is silently substituted and old history cannot mint a new ephemeral grant.
Preparation selects `processor:local_on_device|ha_configured`
and `voice_preference:default|male|female`; neither is a provider/voice identifier.
No free text, provider
URL, arbitrary voice/engine ID, model prompt or playback instruction. Resolve
through existing dialogue/history/Runtime owners and original source rights.
Live and historical replay have independently qualified admission; no whole
history scan or archive backfill. Unknown/revoked/deleted references fail closed.

Preparation returns the same descriptor with optional temporary managed audio
and effective renderer voice metadata when qualified. Local on-device synthesis
can consume only exact admitted segments and declared local processor. It must
report effective voice/locale or explicit no-matching-voice. Core must not claim
an Apple voice exists before the renderer's actual inventory/acceptance.

For HA synthesis use only the currently configured Assist/HA TTS entity and
voice, with its actual supported inventory. Default uses that exact voice; male
or female requests are unavailable unless explicit qualified metadata matches
that configured voice. A configured engine alone establishes neither local
processing nor permission: qualify its processor identity and each source basis;
unknown/cloud-unqualified processors return unavailable, without fallback.
Local-on-device preparation returns renderer_pending, not synthesized audio;
its concrete gender/voice selection and audible acceptance remain Apple-owned.
There is no config-flow mutation, added provider or direct API. Do not infer
male/female from names, pitch or Persona. Where the engine lacks qualified gender
metadata, report that limitation. Local reading may remain available, but it
does not enable an unsupported gender selector.
Never silently switch to another voice/engine/cloud route. See [HA TTS voice
contract](https://developers.home-assistant.io/docs/core/entity/tts/).

## Bounds, identity, authority and cancellation

At most one target per request, two concurrent syntheses per existing owner and
bounded deduplicated in-flight/resource slots. Complete20s preparation deadline;
maximum1200characters/8ordered segments,2MiB audio and original300s resource TTL.
Negative backoff60s. Cache key includes owner/source/contribution, exact text and
presentation revision, locale, effective real voice/provider and qualified style.
Reads/reconnect/cachehits never slide original source/resource deadlines.

Existing temporary audio owner holds bytes in RAM only; no audio/provider object
or long-lived deliverytoken in history. New private speech bytes require normal
paired authorization and exact Profile/source/contribution authority; an opaque
asset ID alone is not a grant. Do not break legacy ESP delivery while adding this
narrow owner-bound route. Recheck rights after every external await and at final
response/byte delivery. Withdrawal, clear/purge/retention, Session end or Profile
change invalidates scoped work and grants; cancellation cannot publish late bytes.
No provider work, original Ask DJ execution or playback effect on replay.

## Renderer-local voice and autoplay

Concrete playback and optional male/female preference belong to the client
audio output; Persona belongs to the Session. Gender UI is conditional on the
configured server Assist pipeline/provider advertising qualified support. Query
the private read-only voice-options route; absent/unsupported metadata hides the
selector and presents provider default. A previously selected now-unsupported
preference is explicitly unavailable; never silently relabel another voice.
Actual native inventory must also match before playback and cannot independently
enable server-unsupported gender options. Device preferences must not rewrite Profile
or shared Session implicitly. Match actual locale and explicitly available voice;
otherwise expose missing capability. Apply changes to pending/next/replay as a
new voice revision; never relabel cached old-voice bytes. An ordinary voice-preference change may let the playing sentence finish.
Authority withdrawal, Profile change, source expiry, Session end or explicit Stop
takes precedence: stop running audio and discard pending audio immediately;
never finish a sentence under a withdrawn grant. Native UI exposes effective voice
and accessible Listen/Stop/current unavailability in the active Session.

Autoplay is per device and off does not remove manual listening. An explicit
`audio_response:never` excludes autoplay eligibility while preserving manual
listening. Joined/deduplicated responses never open another autoplay opportunity. Only live newly
accepted intended publications are eligible once under original contribution ID;
history/open/read/recovery/reconnect are never new eligibility. Maintain one
bounded local playback queue and discard withdrawn/expired/superseded entries.
Stop/mute cancels pending local work. Device A off stays silent when B opts in.
No automatic global speaker call or music-output transfer; multiple explicitly
opted-in local outputs are independent, HA-speaker routing is a separate explicit
existing action and never an implied effect of preparing/listening.

## Transport and test contract

Normal owner pairing, Profile authorization and no-store apply. Keep private
Ask DJ/reference/text/voice state out of VibeCast/widgets/notifications/diagnostics.
Public Presentation keeps renderer-neutral approved content/roles; no concrete
provider/voice/secret or private owner speech resource in shared Broadcast.
Bubble text and speech refer to the same semantic contribution/revisions.

Test general+Session early replies and common model path; never/auto/always,
manual after never, unsupported voice, exact voice/locale cache separation,
expiry/source rights, stop/cancel/in-flight, clear/end/Profile change and ordinary
replay with zero semantic/counter/effect changes. Prove real HA routing/storage/
Runtime/Planner/Flow/Broadcast; fixtures only external provider/synthesizer edges.
Deliver early exact contract and real sanitized fixtures/checksums to Apple87.
Native Mac/iPhone/iPad audible quality, interruptions and per-device autoplay
require that existing Apple writer's own tests; Core fixtures do not certify them.

## Qualified local implementation boundary

The first connected producer uses `reference:{turn_id}` for common Ask DJ on both
screens. Accepted private early/current replies stay only in the existing bounded
dialogue frame: eight references of at most1200characters each, maximum300seconds,
shorter original source/queue/Forecast/choice deadlines. Current playback reads
have at most60seconds from their original read. Scoped expiry removes text and
private audio even without another request. Source/Profile changes latch
invalidation through the existing Profile storage owner; a return to the original
configuration does not revive old grants. Final unload clears scoped resources.

HA synthesis currently qualifies only the actual existing Wyoming Piper entity
on a literal private/loopback endpoint, matching configured locale and configured
voice in its supported inventory. A generic Wyoming entity or engine name is
insufficient. HA2026.10 Voice exposes ID/name, not gender; male/female requests on
this HA route return `voice_gender_unavailable`. No provider or pipeline fallback.
A confirmed current-artist reply may use `spotify_owner_local_read_v1`: only
the exact accepted owner-visible title/artist sentence, its original at-most60s
read deadline and attribution, through this qualified household Piper route.
This is local authorized reading, not a model/cloud grant or playback control.
No API/config change adds a new synthesizer. Other source/processor combinations
remain unavailable until independently qualified. Client male/female choice remains optional and provider-gated; native rendering
also requires real matching voice-inventory/audible evidence.

Prepared HA audio is private RAM data in the existing TTS resource owner, at most
eight resources per Profile/64 total, two concurrent preparations per Profile,
20seconds per preparation,2MiB per resource. Exact cache identity includes accepted
text/presentation revision, configured real voice/locale and owner. Failed attempts
have bounded60second backoff. `POST /speech/audio` requires ordinary paired owner
identity plus asset reference; the old bearer-free ESP audio route cannot read
these resources. Stop/cancellation/withdrawal cannot create late deliverable bytes.
Neither these early connected routes nor a nonempty WAV qualifies complete Moment
family adoption, actual Apple voice quality, autoplay or joint acceptance.

## Optional gender-setting readback (owner clarification)

`POST /api/djconnect/v1/speech/voice-options` accepts only normal paired
client_type/device_id and contract_version1. It reads the currently configured
HA Assist pipeline/provider without synthesis, media/provider lookup, model,
playback or Session/Profile mutation. `speech_voice_options` has an unordered
equality `revision`, provider-default availability and optional `gender_selection`:
`available`, actual `values`, and reason. Current HA/Piper metadata exposes only
voice ID/name, so gender `available:false`, `values:[]`; the client hides that
optional selector. No name/pitch-to-gender inference. A stored unsupported
preference remains explicitly unavailable with an accessible Use provider
default action (even while the gender selector is hidden); no
silent gender fallback or Persona/Mood/Profile change. Re-read provider support
when opening voice settings or after a provider change. All client labels and
accessibility states follow en/nl/de/fr/es.
