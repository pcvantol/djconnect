# Golden contextual source and review repairs — 6 November 2026

Decision: **SOURCE_REPAIRS_UNDER_LIVE_ITERATION; RELEASE_QUALIFICATION_OPEN**.

The owner requested remediation of the68 open HA-release Golden findings. The
original grant was40 gpt-6-luna calls at700 output tokens. The owner subsequently
approved3000 output tokens and explicitly unrestricted model-call iterations.
The cumulative external ledger is retained across all attempts; no consumed call
is reset. Each semantic answer still uses its existing generation/review bound.
The full contextual probe allows42 calls:20 questions times2, plus2 real
publication-setup calls. Calls use isolated synthetic/public music context; the
installed HA configuration is not mounted into the probe.

The39 Core findings and29 real-quality steps remain OPEN. Existing five-language
UI and the EN/NL-only28-leaf Help publication boundary are preserved;42 pending
DE/FR/ES Help leaves are unchanged.

## Observed defects and repairs

- The SessionFactsResolver fixture now accepts and executes the real `authorize`
  callback. Withdrawal still prevents fixture I/O. Its old signature swallowed a
  TypeError and yielded no usable selected Moment.
- Real publication setup attempts have their own identity and count in the probe
  budget. Failed setup emits a FAIL receipt. Stream terminal events, incomplete
  reasons and configured output limits remain in compact usage evidence.
- Literal quoted short work titles such as “One” no longer fail solely because
  they have fewer than four characters. Short titles must remain quoted in both
  source and answer; year, event, source and precision checks still apply.
- An actual fresh selected playback reference can resolve a partial public artist
  name. Its private track labels and URIs do not become model evidence. Stale,
  cached, withdrawn, expired and ambiguous multi-artist identities remain denied.
- Ordinary source-grounded answers expose the exact admitted composer credit to
  the review with its original ID. Only the canonical normalized credit body can
  use this projection; generated prose and copied credit-like JSON cannot.
- Reviews must return complete atomic factual proof instead of a bare positive
  boolean. Their text segments must reproduce the answer without inserted full
  stops. Temporal receipts use the complete unchanged answer sentence, separately
  from its smaller atomic claim segments. Validators remain fail-closed.
- Generation explicitly distinguishes membership/credits from public fame. A
  source saying someone is a member cannot justify “best known for”.
- The contextual Golden source check now verifies the real Core wire contract:
  provider/host/license, exact public person identity, content hash, original
  fetch/expiry times and generated research basis. It no longer expects a
  `person_biography` field that Core never emits. Original credit attribution
  alone, wrong actors, missing hashes and expired sources remain insufficient.

## Evidence and limitations

External evidence root:
`/Volumes/Shared Data/tmp/pcvantol/golden-68-remediation-20261106`.
Original failed runs are preserved. `live-approved-40/budget.json` is the
cumulative pre-I/O ledger; its historical directory name is not a new limit.

On candidate7a803b2d,371 related unit tests passed. The real English diagnostic
`credit-proof-en-r4` used10 calls and accepted the selected partial-name and
selected-composer questions with original credit and fresh biography sources.
The playback and new-topic questions failed their proof contracts; these failures
motivated the temporal/full-text review instructions above. A subset diagnostic
always records `full_manifest_qualified:false` and cannot claim full-suite PASS.
Through that run,62 total calls were reserved, including failed setup calls.

The most recent26/26 actual-HA protocol run before these later product changes
qualified c0b956ca only. Those old receipts are not current-head qualification;
the final product bytes require new protocol runs and receipt binding.

This source branch starts at Core main98e5c430. It excludes PR1439 runtime
changes and does not modify the HA-dev installation, still the separately
installed debug composition69dcfe05. No official release, merge, physical Apple,
audible playback, announcement or APNs acceptance follows from these results.
Protected current-head checks and separate Finalization remain mandatory.

## Subsequent source iteration and current proof

The later repairs distinguish an underlying-work composer credit from a recording
credit in both ordinary chat and proactive narration. The composer writing task
now has one concise source-bound telling instruction using the shared Persona
and Mood owner; independent factual, work-focus, episode and style checks remain
mandatory. Failed publication still withholds the contribution rather than
publishing an unqualified fallback. Short identity answers are limited to two
short sentences, without an unrequested career arc or chronology. Independent
biography occupations retain their own source scope and faithful translation;
a selected work credit does not become a general occupation.

Actual full20-case results progressed from5/20 on78de5fce (`full-context-r11`)
to13/20 onf54a2edb (`identity-full-r16`) and14/20 on95f90f86
(`concise-full-r19`). The latest run used42 calls; all English and Dutch cases
passed. Six German, French and Spanish cases remain failed. Every earlier failed
setup and suite is preserved separately. These are individual observations, not
a robustness qualification, and the canonical suite verdict remains FAIL.

Two causal test-side defects were reproduced before correction: legitimate
German `Jazztrompeter` and Dutch `jazztrompettist` were treated as missing public
facts. Both compound forms now qualify; their negations remain contradictory,
and an answer omitting the actual trumpet fact still fails. The historical
reports are not retroactively changed to PASS.

The latest related unit run passed374 tests in the pinned offline HA image.
All26 actual-HA protocol harnesses then passed on the exact95f90f86 product
bytes (`actual-ha-95f90f86/results.json`), with matching before/after hashes.
Their25 current receipt projections bind all308 tracked product files; historical
originals and raw earlier failures remain preserved. The26 exact CI receipt
checks also passed after binding. These protocol fixtures use no real model,
Spotify, speech or hardware provider and do not establish product acceptance.

The HA adapter's default reasoning setting is low. A separate external medium
comparison is diagnostic only: it preserves the same model, destination,
synthetic/public context and3000-token ceiling, records the effective setting
per ledger reservation, and cannot report full-manifest qualification. It neither
changes the installed HA settings nor extends the canonical catalogue-only
nonlegacy qualification profiles. See the official
[reasoning parameter documentation](https://developers.openai.com/api/docs/guides/reasoning).
The first218 cumulative reservations are retained before that comparison.

All39 Core findings and29 real-quality steps still remain OPEN. No release or
installed/native/audible/APNs completion is inferred from this source increment.

The first medium diagnostic (`medium-failed-six-r20`) reserved2 further calls,
both completed within3000 tokens. Its generated announcement passed the external
style check but failed Core's independent public-work episode coverage. No
question ran, and no comparative quality improvement is established. Both calls
remain consumed in the cumulative ledger (220 through this diagnostic).
