# Help release coverage: bounded test-clock remediation

This increment remediates the test harness for the existing Help release. It
does not change the catalogue, runtime product, provider policy or push rights.
All 271 product files remain byte-identical to protected Source1363 and
Final1364. EN/NL content qualification is retained; no paid content run is needed.

## Original observation and diagnosis

Protected Final1364 `adb97d358a77f556af405fb95ca813072a7ce50e` had a hanging
post-merge coverage job in run40339311425. Peter explicitly approved cancelling
only that run for diagnosis. Its original terminal result is CANCELLED, not PASS.
The original complete log ZIP, job log and coverage-step bytes are preserved.
The other nine completed jobs remained successful. This increment cannot relabel
the cancelled run or substitute local coverage for original release evidence.

The last original progress was the pending genre-transition test waiting for
model entry. That test globally patched `time.monotonic` and used an asyncio
timeout while its simulated clock was stationary. A separate bounded Linux
Python3.11.17 diagnostic proves that the patch also freezes asyncio's timeout
clock. Keeping a captured real monotonic callable for the event loop restores
the timeout without changing application-clock observations.

The precise reason the original model-entry event did not arrive is not proven.
The original selected test, both alone and after the complete discovery import
graph, passed under Python3.11.17/coverage7.16.2. A guarded original-order prefix
also passed that target, but the stripped diagnostic image lacked Node and the
prefix ended with five other fixture errors and58 skips. That prefix is retained
as FAILED diagnostic evidence, never as full qualification or a reproduced hang.

## Repair and preserved assertions

- The business-clock fixture captures the real `time.monotonic` callable before
  patching. It keeps `loop.time` real while the original simulated application
  clock and its225-second progression remain unchanged. Saving only a bound
  `loop.time` method would still read the globally patched function.
- The held-model checkpoint waits for either the entry event or producer
  completion. A producer exception is surfaced; an empty early result or a
  two-real-second missing event fails the test instead of hanging indefinitely.
- A `finally` block releases the held model and cancels/joins any remaining
  producer task. All original expression, single-publication, replay and stored
  history/reopen assertions are preserved. No model/type/source guard is relaxed.
- Two causal regressions check that real timeouts remain live during simulated
  business time and that failed/empty producers cannot strand the checkpoint.
  Both are bound to the existing durable-runtime-expression release-matrix
  step; question/answer text, model policy and catalogue content are unchanged.
- The existing post-merge coverage job has a ten-minute job limit, including
  dependency installation. No new job, secret, paid call or workflow is added.

The initial local edit misplaced the final stored-history test block. Its two
NameError failures are retained separately; the complete block was restored
inside its original test before validation. Those failures are not runtime or
catalogue failures and are not relabelled as passes.

The first complete local check also correctly refused two unregistered release-
matrix method names. Their bindings were added to the existing transition step;
all questions, expected answers, model policies and other matrix content remain
unchanged. The failed check is retained independently of its successor.

## Delivery boundary

This is source preparation until independent whole/exact review, ordinary CI,
protected delivery and the necessary separate Final/original qualification
complete. No deployment, restart, physical device action, API publication or
push activation follows from this test-only remediation. The existing Help
content receipts, all pending cross-lane work and historical failures remain.
