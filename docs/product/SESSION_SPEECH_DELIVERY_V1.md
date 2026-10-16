# Session speech delivery and replay v1

Design-first companion to [Session narration/live Persona](SESSION_SPEECH_PERSONA_V1.md).
One existing contribution and one accepted text; audio is a presentation resource,
never a new DJMoment or conversation turn. Core source is protected delivered
in [PR1177](https://github.com/pcvantol/djconnect/pull/1177) at
`3535c97c3b50e9a126d0f22fcc5ce50d81851499`. Native adoption, installed Speech
and joint audible acceptance remain separate open gates.

## Optional owner projection and explicit preparation

`session_speech` contract1 is an optional private-owner capability. Existing
Ask DJ accepted responses and owner Moment/history projections may attach a
speech descriptor. Ordinary GETs/open/search/reconnect never synthesize or
refresh a deadline. Unknown optional schema keeps text/actions usable.

Descriptor: `schema_version`, contribution `source_kind`/`source_id`, optional
`session_id`, immutable `text_revision`, `presentation_revision`, effective
`persona`/`persona_revision`, `locale`, ordered exact `segments`, `state`,
`reason`, original `expires_at`, independent `manual_allowed` and new-publication
`autoplay_eligible`, allowed preparation-attempt `processors`,
`processor_qualification_required:true`, source attribution and `cache_policy`.
States: available,unavailable,expired,withdrawn. A source/audience/processor denial
has no executable text/audio grant. Available turn, live Moment and retained-entry
descriptors advertise both `local_on_device` and `ha_configured` as permitted
prepare attempts. This list never establishes provider availability, source
processing rights, matching locale/gender, effective voice or ready audio. Those
conditions are checked during explicit paired preparation; a denied route returns
unavailable with `processors:[]`, without fallback. A prepared descriptor keeps
the same list meaning; only its `audio_state:ready` and `effective_voice` establish
that exact prepared resource. Descriptor reads perform no TTS/provider work.
Clients must require the explicitly advertised route before attempting prepare;
legacy descriptors that omit it grant no additional attempt. Machine codes stay untranslated; client
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
and `voice_preference:default|male|female`; neither is a provider identifier.
For `ha_configured` only, optional `voice_id` selects one exact ID from the
current bounded provider inventory returned by voice-options (max64); a removed
or unknown ID is unavailable, without fallback. No free text, provider URL,
arbitrary engine ID, model prompt or playback instruction. Resolve
through existing dialogue/history/Runtime owners and original source rights.
Live and historical replay have independently qualified admission; no whole
history scan or archive backfill. Unknown/revoked/deleted references fail closed.

Preparation returns the same descriptor with optional temporary managed audio
and effective renderer voice metadata when qualified. Local on-device synthesis
can consume only exact admitted segments and declared local processor. It must
report effective voice/locale or explicit no-matching-voice. Core must not claim
an Apple voice exists before the renderer's actual inventory/acceptance.

For HA synthesis use only the Assist pipeline selected in the DJConnect
configuration and its HA TTS provider, language and voice. Use HA's supported
`async_get_pipeline(hass, selected_id)` selector, or its actual preferred pipeline
when no explicit ID is configured; never select an arbitrary first pipeline.
An explicitly selected missing pipeline is unavailable, without fallback.
Providers implementing HA's supported TTS interface share the same adapter;
there is no general Piper/provider-class allowlist. Default uses that exact voice; male
or female requests are unavailable unless explicit qualified metadata matches
that configured voice. A configured engine alone establishes neither local
processing nor permission: qualify its processor identity and each source basis;
source bases not qualified for the configured processing route return unavailable,
without fallback. See [generic HA TTS correction](GENERIC_HA_TTS_V1.md) for the
source/processor matrix, provider-default semantics and audio checks.
Local-on-device preparation returns renderer_pending, not synthesized audio;
its concrete gender/voice selection and audible acceptance remain Apple-owned.
There is no config-flow mutation, added provider or direct API. Do not infer
male/female from names, pitch or Persona. Where the engine lacks qualified gender
metadata, report that limitation. Local reading may remain available, but it
does not enable an unsupported gender selector.
Never silently switch to another voice/engine/cloud route. See [HA TTS voice
contract](https://developers.home-assistant.io/docs/core/entity/tts/).

## Functional runtime provider feedback

Optional version1 `provider_status` and `notification` extend the existing
private owner routes without changing speech/reference authority. Voice-options
reports configuration readiness separately from `not_tested`, `succeeded` or
`failed` synthesis. At most64 private RAM observations expire after300s and bind
to exact entry/Profile, provider incarnation and configuration revision. Reads
and cache hits do not refresh observations or synthesize; expiry means unknown.

Prepare reports unavailable with a safe functional notice for missing pipeline,
unavailable provider, unsupported language/voice, preparation failure or timeout.
Private audio returns JSON409 only when the contribution is still authorized but
its provider configuration changed; normal auth/source denials stay opaque.
Notices preserve the original contribution language and never expose exceptions,
credentials or source bodies. `notification` carries stable `code`, localized
`title`/`message`, `actions`, `retryable`, `retry_after_seconds`,
`preserve_text:true` and `repeat_original_request:false`.

Apple displays this inline in the DJ-session, instructing the user to check the
selected Assist pipeline and its HA TTS provider, language and voice, including
provider access/connection when unavailable. Preserve readable text and controls.
Explicit retry prepares that same reference only, respects current authority and
backoff, and never repeats an Ask DJ/playback action. Refresh on foreground,
reconnect, voice-settings open and preparation; handle runtime audio409 too.
No automatic retry, monitor, APNs or shared provider-health feed. Apple rendering,
localization/accessibility and audible acceptance remain separately qualified.

## Bounds, identity, authority and cancellation

At most one target per request, two concurrent syntheses per existing owner and
bounded deduplicated in-flight/resource slots. Complete20s preparation deadline;
maximum4000accepted answer characters in at most8ordered segments of at most
1200characters each,2MiB audio and original300s resource TTL. Existing Moment
content retains its original1200character bound. No truncation or extra prose.
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

The active DJ-session exposes a localized Voice menu. Concrete voice choice
and optional male/female preference are client-local settings keyed by HA
installation, authorized user/Profile, session_id and device/install-ID.
`preference_context` advertises this scope, runtime mutation and discard-on-end;
`voices` exposes at most64 current supported IDs/names, gender null unless
qualified. Explicit per-prepare choice never changes shared HA pipeline/defaults.
Native local voice IDs are separate and cannot be submitted as HA voice IDs.
Concrete playback belongs to the client audio output; Persona belongs to the Session. Gender UI is conditional on the
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
dialogue frame: eight references of at most4000characters each (ordered exact
segments, at most1200characters per segment), maximum300seconds,
shorter original source/queue/Forecast/choice deadlines. Current playback reads
have at most60seconds from their original read. Scoped expiry removes text and
private audio even without another request. Source/Profile changes latch
invalidation through the existing Profile storage owner; a return to the original
configuration does not revive old grants. Final unload clears scoped resources.

HA synthesis uses the exact selected provider's supported language and configured
voice, including an advertised provider default when no explicit voice is set.
Providers without a voice inventory can use their own default; Core reports that
selection explicitly without inventing a voice name. HA2026.10 Voice exposes ID/name, not gender; provider-qualified metadata
may add gender under [the bounded adapter contract](PROVIDER_VOICE_GENDER_V1.md).
Without that metadata, male/female requests return `voice_gender_unavailable`. No provider or pipeline fallback.
A confirmed current-artist reply may use `spotify_owner_local_read_v1`: only
the exact accepted owner-visible title/artist sentence, its original at-most60s
read deadline and attribution, through an independently qualified local route.
The existing actual installed household Wyoming Piper proof remains one such
local source grant, not a general compatibility requirement for HA TTS providers.
This is local authorized reading, not a model/cloud grant or playback control.
No API/config change adds a new synthesizer. Qualified accepted dialogue,
normalized CC0 and authored Runtime direction may use the configured HA provider,
including OpenAI/Cloud. Only exact accepted speech segments are sent, without
raw provider payload, hidden context or a new archive grant. Other source/processor combinations
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
`available`, actual `values`, and reason. Providers with only voice ID/name advertise gender `available:false`,
`values:[]`; the client hides that optional selector. Qualified Cloud/provider
metadata advertises actual `values` and deterministic `voice_ids` targets.
Inventory inspection is bounded to512 entries, projection to64; configured and
qualified gender target voices take priority within that bound. No name/pitch-to-gender inference. A stored unsupported
preference remains explicitly unavailable with an accessible Use provider
default action (even while the gender selector is hidden); no
silent gender fallback or Persona/Mood/Profile change. Re-read provider support
when opening voice settings or after a provider change. All client labels and
accessibility states follow en/nl/de/fr/es.

## Common post-acceptance presentation disposition

Both Profile Ask DJ screens use the same common service and accepted-reference
presentation path, including early replies, help, model prose and voice-derived
text. Their underlying answer helpers no longer synthesize/activate a speaker
before semantic acceptance. A client opts into the private adapter with
`speech_contract_version:1` on the common Ask DJ request. Other supplied versions,
including booleans and strings, fail400 before a turn/effect. This option is part
of request identity; it cannot mutate the protocol of a replayed request.
WAV/PTT uses `X-DJConnect-Speech-Contract-Version: 1` on the existing paired voice
route; it maps to the same integer payload field. Other header values reject400
after device authentication and before reading audio or invoking STT. Absence
retains the explicit old-client disposition below, not an implicit opt-in.
`audio_delivery:{mode:accepted_reference,state:deferred}` for opted-in clients
keeps text delivery independent of synthesis. Per-device autoplay/manual Listen
uses the one qualified prepare route after acceptance; failure does not resend
the original question or replay a music action. `audio_response:never` retains
manual listening, while always/auto express presentation eligibility and do not
promise a pre-rendered legacy public audio URL. Explicit raw/ESP HA integration
output remains its existing non-chat delivery contract; there is no general-versus-
Session Ask DJ dialogue fork. Apple adoption of the accepted-reference player is
required and remains separately open; old native audio URL handling is not a
qualified new speech player. Private audio never uses the legacy bearer-free URL.

Without that opt-in, accepted private text remains usable. When always or the
existing voice/auto policy requests audio, return `audio_delivery.state:unavailable`,
`reason:client_protocol_upgrade_required`, `required_speech_contract_version:1`,
no `audio_url` and no new autoplay grant. Otherwise state is `not_requested`.
The already accepted reference can be prepared after client adoption; the user
must not resend the original question to repair audio. The existing Apple and
Watch `AVPlayerItem(url:)` path cannot send the paired POST required by the new
private asset. Moving those bytes to its bearer-free GET would weaken authority.
This is an explicit consumer compatibility boundary, not audible parity or an
installed fix for unmodified native clients. Raw/ESP output keeps its own
existing contract; no second general/Session dialogue implementation is added.

Scoped expiry removes the additional speech-reference text/audio, not separately
qualified conversation history or the existing bounded conversational window.
Those retain their own original archive/context rights and independent lifecycle.
No new history copy or historical access right follows from speech eligibility.

## Moment admission refinement

Live references are exactly `session_id`+`moment_id`, resolved only from the
semantically published Broadcast set and its original native-delivery boundary.
Current catalog facts require current-display permission; retained-in-Flow CC0
and authored direction may use active-Flow permission. The original qualified
source expiry applies; authored live direction has a publication-bound1800s
window and Session end. Persona/revision are captured at publication, never
relabelled from the current Session. Private owner snapshots/events may advertise
these descriptors; shared VibeCast never receives private speech references.
Only the actual new Moment publication event marks autoplay eligibility; snapshot,
Flow refresh, Presentation event and replay never do.

Retained references are exactly `session_id`+`entry_id`, using the existing scoped
owner entry query. Only qualified saved DJMoment text or an accepted archived DJ
answer is eligible, never playback observations/user turns. Original retention,
source/account/Profile/clear/purge and dependency admission still apply. Stored
style/locale are used; unknown locale is explicit unavailable and missing old
Persona revision remains null, without backfill. A replay is not new publication.
Existing owner timeline/entry projections attach that speech state to DJMoment
and DJ-answer entries only. Ordinary history reads retain the fixed original
`retained_until` as source expiry and allocate no audio/watch/grant. User turns
and playback observations do not become narration. The same pure descriptor
builder serves reads and explicit preparation; only preparation bounds a new
temporary audio resource to at most300s within that retention/source window.

The existing temporary audio owner holds at most64 callback-only source watches;
no second text/event/history store. Watches exist only while pending audio or
bytes need them, expire on an absolute deadline and unsubscribe when unused.
End/Profile withdrawal and destructive history transactions invalidate their
scoped work before any late synthesis can commit bytes. The configured HA
processor and private paired download are identical for all reference kinds.
Each explicit preparation may create at most300s audio within the still-valid
source/retention window. Cache hits report the actual original asset expiry;
reads cannot extend source, retention or existing audio lifetimes.

Optional presentation refinements in the unpublished candidate:
- Ordered speech segments reuse the existing Presentation Composer schema:
  `ordinal`, `speaker_role:dj`, exact `text`. Joined segments equal the accepted
  text character-for-character; no independent private-role/voice generator.
- Rich current assistant-message projections carry the same descriptor as the
  top-level result, without archiving resource metadata. A deduplicated/recovered
  result has no new autoplay opportunity.
- Accepted turn metadata retains its compact effective style/revision. Retry after
  a Persona change returns that original style, not the new Session style applied
  to old prose. Legacy stored turns lacking style report `style:null` and
  `style_basis:legacy_unknown`; render original text without inventing a Persona.
- Gone/expired private speech references/assets use404, not a pairing failure.
  Genuine device authentication remains401; Profile policy denial remains403.
  Resource disappearance must not clear an otherwise valid device pairing.
- Provider-supported gender gating also applies to local preparation. An actual
  native gender voice alone cannot authorize a server-unsupported preference.
