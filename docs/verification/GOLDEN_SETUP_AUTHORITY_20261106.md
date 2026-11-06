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
