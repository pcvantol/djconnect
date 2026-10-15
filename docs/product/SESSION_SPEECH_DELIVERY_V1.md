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
contract1 and exactly one existing target: accepted `message_id`, published
`session_id`+`moment_id`, or retained `session_id`+`entry_id`. No free text, provider
URL, arbitrary voice/engine ID, model prompt or playback instruction. Resolve
through existing dialogue/history/Runtime owners and original source rights.
Live and historical replay have independently qualified admission; no whole
history scan or archive backfill. Unknown/revoked/deleted references fail closed.

Preparation returns the same descriptor with optional temporary managed audio
and effective renderer voice metadata when qualified. Local on-device synthesis
can consume only exact admitted segments and declared local processor. It must
report effective voice/locale or explicit no-matching-voice. Core must not claim
an Apple voice exists before the renderer's actual inventory/acceptance.

For HA synthesis reuse the configured Assist/HA TTS entity and supported voice
inventory; no config-flow mutation, added provider or direct API. Do not infer
male/female from names, pitch or Persona. Where the engine lacks qualified gender
metadata, report that limitation and retain explicit local-renderer alternative.
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

Concrete voice/provider and male/female preference belong to the audio output;
Persona belongs to the Session. Device preferences must not rewrite Profile
or shared Session implicitly. Match actual locale and explicitly available voice;
otherwise expose missing capability. Apply changes to pending/next/replay as a
new voice revision; never relabel cached old-voice bytes. A playing sentence
finishes unless the user explicitly stops it. Native UI exposes effective voice
and accessible Listen/Stop/current unavailability in the active Session.

Autoplay is per device and off does not remove manual listening. Only live newly
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
