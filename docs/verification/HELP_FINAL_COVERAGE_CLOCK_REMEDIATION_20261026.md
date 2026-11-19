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

## Successor: exact fixture ticks after an original observe failure

Source1365 was protected as `18b9d96d2feb9ef4239aa17aa188f16c1ff55f58`
(reviewed `2f5689aaccb7c442cade9802306d37df27603577`). Its normal main
run40386787989 passed tests and exact-source coverage. Original formal run
40387614437 and durable qualification joined all12 required checks; formal
SHA256 `24d71ef15806a172e3d0f9eec5c6542f577b5e94e4d971cdd93630c10efdea84`,
durable SHA256 `1e0adfef9ddc44a135ffe622b8b69ad5622837cd0a87787a4336fb0dcbe1c85e`.
The automatic paid job was actually cancelled, not a model PASS.

The separate non-blocking TDE observe run40386787940 failed the held genre
producer test:3740 total, one failure,53 skips,383.325 seconds. The new bounded
entry wait exposed an early producer completion instead of hanging. Original
failed-log SHA256 `f0a6388906b454afb02070a8bfb48b59d28ec7e70b7f54f1035e7798d6f183dd`.
Formal qualification does not relabel that failure. Final and installation
were held while investigating it.

A predeclared three-input private probe changed only the target test's clock
initializer. Base824.0 and100.0 passed the complete original test. Base
`math.nextafter(824.0, math.inf)` failed with the same early-return symptom:
the original ledger last-at was1004.0000000000001 and next time1049.0, so
their actual difference was44.999999999999886. The original presenter policy
correctly returned `presence_readable_interval`. The original CI clock value
was not recorded, so this is a confirmed causal fixture defect, not proof
of the exclusive cause or exact clock value of that historical run.

The successor uses100.0 as its deterministic binary-exact business-clock
anchor, preserving the same90+90+45 advances, all publication/history/reopen
assertions, real event-loop clock, bounded entry wait and cleanup. A causal
regression exercises the actual PresenceLedger with both the rounded-short
and exact45-second ticks: short remains denied, exact remains admitted.
There is no production epsilon, shortened interval, guard change, new skip
or paid call. Its owning-test binding alone is added to the existing matrix
step; catalogue/questions/answers/model policy and all271 products stay equal.

## Current delivery boundary

This is source preparation until independent whole/exact review, ordinary CI,
protected delivery and the necessary separate Final/original qualification
complete. No deployment, restart, physical device action, API publication or
push activation follows from this test-only remediation. The existing Help
content receipts, all pending cross-lane work and historical failures remain.
