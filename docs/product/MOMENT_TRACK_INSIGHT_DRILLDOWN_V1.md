# Moment → Track Insight drilldown v1

Directed addition to `DJC-CORE-ASKDJ-CONTEXTUAL-DIALOGUE-V1-20261013`, owner
[decision6146489526](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6146489526)
and [full requirement6145985084](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6145985084).
Direct owner approval in the existing Core session confirms design, implementation,
tests and ACK; exact candidate publication and Finalization remain separate gates.
This is the addition's pre-implementation design, not a delivery claim.

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
`{session_id, moment_id}`. The producer retains exact media identity, publication
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
