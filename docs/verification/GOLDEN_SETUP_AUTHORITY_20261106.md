# Golden selected-publication setup repair — 6 November 2026

Decision: **SOURCE_REPAIR_TESTED; LIVE_QUALIFICATION_INCOMPLETE**.

The owner requested remediation of the 68 open HA-release Golden findings and
approved one isolated 20-case contextual probe, at most40 gpt-6-luna attempts and
700 output tokens per attempt. This increment corrects failures discovered while
executing that probe. The canonical39 Core findings and29 real-quality steps remain
OPEN; their matrix and release-blocker policy are unchanged.

## Reproductions and correction

1. The real SessionFactsResolver passes `authorize` around its external reads.
   The harness's provider fixture rejected that keyword, so normal exception handling
   yielded no facts and no selected composer Moment. A causal offline regression
   first failed with that exact TypeError. The fixture now accepts and invokes the
   authority callback; withdrawn authority still prevents external fixture I/O.
2. A current selected Moment requires accepted generation and review. The old
   contextual runner could not bind those setup attempts to a case, so it blocked
   them before provider dispatch and could not reach any of the20 questions. Setup
   attempts now have one explicit identity, maximum2, inside the existing total40
   budget. Every question must still execute1–2 bound attempts; a setup call cannot
   replace a question or raise the total limit. Failed setup emits a FAIL receipt
   rather than leaving the run without a result. Normal source/review admission is
   retained; no synthetic public telling is inserted as an accepted publication.
3. Failed model streams were counted but their terminal event and incomplete reason
   disappeared from the compact contextual report. Those existing metadata fields,
   and the configured output limit, now remain in the bounded usage projection.
   Incomplete streams remain rejected; no provider text, prompt or credential is added.

## Validation and bounded live evidence

Thirty gate tests pass, including denied source authority, counted setup attempts,
unknown/missing/incomplete setup receipts, unchanged whole-manifest coverage,
failed setup with no submitted questions, and retained output-limit diagnostics.
Ruff and diff checks pass. The same30 tests execute in the pinned real HA image
with network none. No product files under custom_components/djconnect change.

The original live attempts are preserved externally under
`/Volumes/Shared Data/tmp/pcvantol/golden-68-remediation-20261106/live-approved-40`.
They used the previously installed debug product composition69dcfe054e70cbf7bba3a4990d6d27012a712244,
which contains main98e5c430 plus PR1439 runtime. This source repair branch instead
starts at main98e5c430 and contains only Golden tooling, tests and this report.
It neither merges PR1439 nor changes the installed integration.

The first two setup runs reserved0 calls. After the setup binding correction,
the next run reserved2: the first completed with45 output tokens; the second was
incomplete at the configured700-token limit. Setup therefore failed before any
contextual question could run. A durable external ledger reserves before I/O,
across attempts and restarts; it is not reset. Both reservations remain consumed.
No successful20-case live qualification or editorial/native/audio/APNs acceptance
is claimed. The other38 calls have not been dispatched.

The paid probe is paused. A separate human question requests raising the per-call
output ceiling to3000 while keeping the same total40-attempt grant. Pending that
answer, no further paid attempt is authorized by this report. Next: complete the
bounded live probe under its actual approved parameters, fix observed product
failures, and independently qualify the remaining real-quality/client gates.

This is a reviewable source repair, not closure of all68 or an HA release approval.
