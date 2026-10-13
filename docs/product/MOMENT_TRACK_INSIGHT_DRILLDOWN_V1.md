# Moment → Track Insight drilldown v1

Directed addition to `DJC-CORE-ASKDJ-CONTEXTUAL-DIALOGUE-V1-20261013`, owner
[decision6146489526](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6146489526)
and [full requirement6145985084](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6145985084).
Direct owner approval in the existing Core session confirms design, implementation,
tests and ACK; exact candidate publication and Finalization remain separate gates.
Connected Core implementation is under qualification. Native adoption and
protected delivery remain separate; this document does not claim either.

## Owners and publication

The existing Runtime → Planner → Knowledge → Moment → Flow/Broadcast chain can
attach one inert navigation offer to an eligible existing Track contribution.
The qualified contribution remains useful without the offer: no empty promotion,
new scheduler, Moment type, analyzer or extra publication budget. Presence,
pacing, source expiry, publication transaction and suppression in flight retain
their existing owners. A semantic publication counts once; reading, opening and
retrying the detail never create another Moment or consume a narrative opportunity.

Only an actually published, owner-visible, qualified Track contribution with an
exact canonical track URI authorizes a target. A title/artist match cannot
substitute for recording/version identity. Proposals, Silence, expired or
unqualified contributions do not qualify. Display/source rights are not archive
or model-processing rights. The teaser preserves existing qualified music meaning;
no invented instrumentation or “analysis ready” claim.

## Closed navigation contract

An additive `navigation_actions` list contains only versioned
`kind: navigation`, `target: track_insight`, `schema_version: 1` actions with
`action_id`, a five-language label and a server-resolved reference
`{schema_version: 1, session_id, moment_id, action_id}`. The immutable
action ID is `insight-{moment_id}`. The producer retains exact media identity, publication
and original deadlines. No arbitrary URL, playback command, mutable client track
metadata or generic executable-action admission. Consumer support is required
before rendering a button. Existing clients can ignore the list; shared VibeCast
without detail support renders the contribution without a dead button. Receiving
an offer never supplies an automatic `open_screen` effect.

A user-selected action resolves through the existing authorized owner route to
one TrackInsightService. The same resolver serves explicit general/Session Ask DJ,
including STT. Screen origin does not choose business logic. A scoped target is
distinct from ordinary current-playback targeting. A → B before or during fetch
never retargets A. Invalid A produces typed unavailable/expired/forbidden state,
not a fallback to B.

## Shared detail, rights and cache

Full detail retains `track`, `analysis`, `visual_profile`, `mood_context` and
`cache`. Exact media/version, backend/account ownership, language, confirmed
Persona/Mood and visual-profile version qualify the cache identity. Reuse valid
analysis across surfaces, with existing bounded rates and duplicate admission;
no per-screen analyzer/cache. A cache miss prepares analysis only after explicit
choice, with loading/error/retry. Render, scroll, read, poll and reconnect do not
fetch or call models.

Resolve owner/source/privacy/original deadline before work and again before
private response/cache acceptance. End, source withdrawal and foreign ownership
close the live action. Historical text rights do not extend its grant. Model
interpretation is labelled separately from measured audio and normalized credits;
only independently qualified necessary input is admissible. Catalog/artwork
viewing alone grants no model ingestion or durable retention. With insufficient
qualified content, retain the useful contribution and omit an unusable offer.

## Consumer experience and acceptance

Apple explicit-subject mode keeps A pinned while playback advances to B. Back
returns to the same Flow/scroll/search position and composer draft. Opening
changes no playback, queue, Session, microphone or TTS. Native adoption, installed
and joint acceptance remain separately Planned/open until Apple-owned evidence.

Core proof uses ordinary pairing, actual publication, target resolution and the
shared service/cache. Only external provider boundaries may be fixtures. Test
A → B before/during fetch, same-name versions, cache hit/miss, styles/locales/
visual-profile, failure/retry, expiry/revocation/foreign ownership/end, presence
Off/in-flight and inert reads with unchanged Moment counts. Exact producer/action/
detail/error fixtures go to existing Apple #87, without consumer WIP expansion.


## Exact owner transport and presentation lifecycle

The additive capability is `moment_track_insight_navigation_v1`, contract version1.
`native_delivery.admissions[].navigation_actions` is a dynamic admission projection;
`executable_actions` stays empty. The legacy semantic `actions` list omits this
navigation type, so old Apple/Pi/Cast clients never receive an automatic-open or
unusable action. `moment_navigation.py` owns the closed lightweight DTO and labels;
target resolution imports existing owners and never adds another publication bus.

`POST /api/djconnect/v1/track_insight` accepts the reference under
`track_insight_target`. Normal paired device/Profile authority is mandatory; the
Broadcast renderer token does not authorize this private detail. The response has
`subject.mode: explicit`, the original reference/media identity and remaining
lifetime. The deadline is the earlier of original publication+600seconds and source
expiry, never renewed by cache hit, poll or reconnect. Source/owner/end refusal is
403/410; malformed reference400; confirmed style change during fetch409. None of
these states silently substitutes current playback. An explicit other title/artist
keeps its existing subject precedence when no target was requested.

Only normalized MusicBrainz/Wikidata CC0 credit data enters the target model prompt.
Verified credit, labelled interpretation/listening suggestions and unknown measured
audio fields remain separate. Playback metadata, artwork, artist IDs and provider
payloads are local display context. Demo and deterministic fake measurements cannot
override qualified detail. Full detail and reduced Session narrative are separate
cache variants; exact case-sensitive media identity, owner/source epoch, language,
confirmed Persona/Mood, response style and visual option bind the existing64-entry
TTL cache and existing6calls/minute+8second same-variant debounce. No new cache owner.
The last owner/style/source fence follows every await before cache or private response.

Only genuinely useful qualified existing Track-Moments receive an offer; no new
card, required quota or hidden analysis on publication. Source-poor cases retain
existing alternatives or Silence. Presence-Off blocks new offers and leaves explicit
questions/detail reads available. Opening, repeating or returning leaves publication
counts, music, Session and other native navigation state untouched by Core. Apple
owns the actual pinned detail component and preserved Flow/scroll/search/draft state;
its source/installed/joint proof remains open.
