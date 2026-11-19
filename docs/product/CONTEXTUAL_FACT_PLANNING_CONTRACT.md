# Contextual current-fact planning v1

Assignment: `DJC-CORE-CONTEXTUAL-FACT-PLANNING-V1-20261007`.
Base: `4c30399294b56aff89b962a53b37ea91a2d1762f`.
Source PR #1122 protected merged as `d7a646e0e83a92211875e2f3b45606678e992e76`;
head/merge tree equality and exact-main checks passed. Dedicated
[Finalization](../history/prompts/2026-10-07-contextual-fact-planning-finalization.md)
reconciles this one slice after its protected merge and workspace cleanup.
Extends [the qualified VibeCast contract](VIBECAST_OWNER_REFINEMENTS_CONTRACT.md)
within the existing Runtime → Planner → Knowledge → Moment → Flow → Broadcast.

## Decision policy fixed before implementation

Eligibility precedes scoring: exact current observed playback, qualified
provider/field/rights/attribution, freshness, matching media identity, exact
locale copy, allowed capability and unused source/subject/angle. No relevance
score overrides these gates. Only the five existing producer angles qualify.

Each eligible candidate must fit its unchanged copy's existing 40–90 second
read duration plus five seconds in remaining observed track time. The same
presentation-duration calculation is used for selection and publication.
Discard an oversized candidate individually, then consider fitting candidates;
if none fit, keep silence without consuming a fact.

Rank scores are deterministic, derived from existing producer intents:

| Context | Track | Album | Artist |
| --- | ---: | ---: | ---: |
| Current-item specificity base | 30 | 20 | 10 |
| Discover Strategy OR Exploring Direction | 0 | +20 | +40 |
| Deepening Direction | +20 | +10 | 0 |
| Chill/focus/deep Mood | 0 | +5 | 0 |
| Radio Persona | 0 | +5 | 0 |

Subtract 25 for the last factual type in the bounded four-Moment Flow suffix.
Use the existing Performance Memory, which is derived only from published Flow
items. Stable ties prefer shorter read duration, then angle key, provider,
source URL and exact localized copy; never producer list order. A source with
unknown intent or field cannot be assigned a made-up scope.

Mood/Persona adjust emphasis by at most ten score points and add at most
15 seconds of spacing. Chill/cooling-down or Club/Festival/party/energy uses
50 seconds; other contexts retain the 35-second floor. The existing previous
card read-duration spacing still applies. No fact text, attribution, rights,
immutable Moment or read duration is changed. Strategy/Direction reflect only
current Runtime state; no inferred emotions or new personal inputs.

Selection emits bounded reason codes in the existing Planner decision. Used
state is committed only with actual Flow/Broadcast publication. Existing six
cards per track, generation/seek/pause/source cancellation, no-store,
visual-only, source budget and Runtime disposal boundaries remain unchanged.

## Behaviour scenarios defined before implementation

Same album/recording/artist producer pool: reversing it gives the same Manual
choice (recording), while Discover/Exploring prefers artist. Subsequent
committed Flow types influence variety. With 50 observed seconds remaining,
a long recording credit is skipped for a short eligible alternative; with
44 seconds, no fact fits. Calm context delays the next card until 50 seconds.
Invalid, stale, wrong-language, wrong-rights, disallowed and already delivered
facts remain excluded even under matching Discover relevance. Existing late
result, pause, seek, output/item switch, duplicate, unload and end tests remain
mandatory regressions. Software fixtures use real producer schemas and the
real Runtime ingress; they do not establish live provider or Pi qualification.

Before evidence: four red real-Runtime scenarios (four failures, one invalid
intent exception) recorded before production mutation. On exact original base,
Manual selected Album first, reversed source order selected Artist first,
Discover still selected Album first and the long-first 50-second case emitted
nothing. After: Manual Track→Album→Artist, reversed identical; Discover
Artist→Album→Track; short-fit emits Album; calm second card at 50s instead of
45s. Reason codes and snapshots are in the local ignored software evidence
`artifacts/verification/contextual-fact-planning/runtime-before-after.json`.

An additional four-angle Runtime test proves recent committed type demotion:
Track→Album→Track→Artist, versus Track→Track when demotion is disabled.
Rejected choices leave Flow memory and used state empty. Direction-only
Exploring changes Manual's Track choice to Artist; all five producer locale
copies stay exact. This does not require or create another public endpoint.

The real unchanged browser consumer passed 20 portrait/landscape card frames
for Manual, Discover, calm and short-fit, including exact source links and
no-store. Existing four-fact browser regressions also passed. No live provider,
HA-dev install or physical-hardware acceptance is claimed.
Parked Pi automatic-capture and normal-frame-rate gates remain PARTIAL.
