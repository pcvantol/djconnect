# Catalogue failure checkpoints

The original manual qualification run39980138736 failed on23October2026 at
15:49:42UTC. Artifact12513766840 has exactly four original allowlisted members:
admission, once-reservation, cleanup and summary. Its original ZIP SHA256 is
`3ade3b98921831cea198ee0fd80df3bce36212445ab687b64385fa624a5e3a5d`.
The final `catalogue-golden.json` is absent. Actual model attempts, answers,
case progress and failure cause remain unknown. Cleanup is VERIFIED_ABSENT;
all264 product hashes join the fixed test source1c551. Independent audit
SHA256 `f58247bbc28f9021ff40bcb3e0fc760128c80ba3c6d8f47e48272f83e6a800bf`
confirms those boundaries. An absent report is not a zero-cost or PASS result.

## Evaluation-only change

The exact100 evaluation harness now writes a private bounded checkpoint before
each SDK invocation, after each completed SDK response and completed case, and
at teardown/report/termination. The helper is bound to the exact100 synthetic
case IDs and catalogue manifest. Selected-case and variation runs do not adopt
this exact100 checkpoint. It stores only fixed phase/outcome enums, synthetic
case IDs and bounded counters; no answers, exception text, prompts, URLs,
credentials, source excerpts or household identities.

Each write uses an exclusive private temporary file, file fsync, atomic replace
and parent-directory fsync. First creation is exclusive. Failed checkpoint I/O
closes future calls before the SDK boundary. Every mutator requires the same
healthy RUNNING state, so late callbacks cannot change terminal records. A
teardown or checkpoint error does not mask an earlier failure/cancellation, and
Session cleanup is still attempted after checkpoint failure. A secondary
temporary-file cleanup error cannot mask the primary save error; private
leftovers confer no resume authority.

Reserved SDK attempts are not billing receipts. A killed process, disk failure
or lost response can still leave an incomplete prefix and unknown external
outcome. The helper never claims execution authority or catalogue acceptance;
even a complete checkpoint explicitly says NOT_QUALIFIED. The existing strict
100-case validator remains the gate for actual answer/route/language/effect
evidence, followed by independent editorial review.

## Delivery and execution boundaries

The existing manual workflow, fixed source1c551, grant, run-number/attempt guard,
once reservation and artifact upload allowlist are unchanged. The consumed
original workflow therefore does not execute or upload this new helper. Its
private `/lab/catalogue-progress.json` is not an approved public artifact.
Source hashing includes the helper when it exists while preserving the exact
historical1c source map when it does not.

This increment does not recover the lost original report, prove its cause,
reset the budget, create a replacement workflow or authorize another paid
call. A future execution requires a separate explicit human budget decision,
independently qualified pinned source/runner and separately reviewed closed
diagnostic publication contract. Do not widen upload to private logs/work.

The catalogue remains `qualified:false` with70 pending examples. All264 product
files, release inputs, client fixtures and HA installed bytes remain unchanged;
no installation/restart, provider/key/native effect or push/VibeCast acceptance
is included.

## Cost-free validation

Fault injection covers pre-SDK write failure and no dispatch, lost response,
exclusive restart denial, schema/canary rejection, all100 observations surviving
teardown failure, primary-versus-secondary exception precedence, cancellation,
cleanup after checkpoint failure, and exact terminal-byte immutability. These
are synthetic evaluations with no real credentials, model or provider calls.
