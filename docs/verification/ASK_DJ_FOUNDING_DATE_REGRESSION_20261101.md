# Ask DJ founding-date regression, 1 November 2026

## Reported behavior and bounded change

The user's Dutch question, `Wanneer is de band nirvana opgericht`, was correctly
routed to an informational music request on HA-dev. Wikipedia retrieval
succeeded, but answer qualification returned `claims_unverified` and the shared
research fallback. This is independent of Help catalogue membership and grants
no playback action.

The first actual public-only model observation combined a founding year, place
and founders in one sentence. Its supplied biographical receipt covered the
founding date, not every addition. A second candidate produced the requested
simple date sentence, but its assessor used the five-field work-date object
with the band as `event_anchor`; that remains invalid. Both rejected originals
are retained.

The bounded correction:

- recognizes Dutch completed-passive `is ... opgericht` alongside `werd ...
  opgericht`, retaining the same explicit group, directed event and exact year;
- asks for the requested date in a separate sentence containing only the named
  group/actor, event and year, with additional requested facts separately checked;
- states the exact ten-field `biographical_event_v1` review shape and explicitly
  distinguishes it from work-date `event_anchor` receipts.

There is no new fact lookup, question catalogue, entity/date constant,
receipt reconstruction, extra per-turn model repair or relaxation of source,
semantic, temporal, negation, uncertainty, identity or prefix guards.

## Original observations and verification boundary

The next actual public-only generation/review pair, using the same original
source bytes and expiry, independently attested the original first sentence:
`Nirvana werd opgericht in 1987.` Its unsupported follow-up remains rejected.
The existing common full-answer-or-original-prefix path accepts only that exact
complete prefix. No answer or review was rewritten after assessment.

The public sources were the canonical Wikipedia entity `Q11649`, including
[the English revision](https://en.wikipedia.org/w/index.php?oldid=1382754740) and
[the Dutch revision](https://nl.wikipedia.org/w/index.php?oldid=71336824).
These are evidence for this bounded observation, not permanent runtime facts.

Original evidence is retained under the existing Core dossier:
`nirvana-founding-diagnostic-20261101/`. The first two model observations remain
unqualified; the local import-preflight failure occurred before authentication
or any model attempt and is separately recorded. The exact successful
full-or-prefix replay and independent bounded review are retained separately.
Normal HA conversation-service calls were used; internal provider attempt or
spend counts are not inferred from service-call counts.

The causally failing Dutch-passive unit test precedes its passing correction.
Wrong group/year, uncertain or negated founding and additional event clauses
remain rejected. Legacy work-date receipts still cannot qualify a group date.
All 22 actual isolated HA groups passed with the same 301 product hashes before,
inside and after their runs; all four owned containers were verified absent.
The 20 current evidence aliases are joined to these fresh originals. Previous
alias bytes, raw evidence and the initial failing whole-unit result are retained.

The final complete offline suite accounted for 4,353 tests across four process
workers: all workers exited zero, with seven existing skips, in 68.857 seconds.
The first parallel run exposed two cache-only artwork fixture errors caused by
an ambient HA session stub; the fixture now explicitly owns an inert session.
No product behavior or assertion was relaxed. That original failure and the
ordered-pair control, which already passed in isolation, are retained separately.
Ruff passed for all five changed Python files.

This record describes source preparation and public-model/component evidence.
It does not establish protected delivery, installation, native acceptance or
that the user's currently installed server has this correction. HA-dev remains
on its independently confirmed 277-file/schema18 predecessor following the
separate host-wake update rollback. Push and all retained lane work keep their
own delivery and acceptance gates.
