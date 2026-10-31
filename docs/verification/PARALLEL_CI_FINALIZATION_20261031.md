# Parallel offline Core CI: separate Final

## Exact source and decision

[Source PR1399](https://github.com/pcvantol/djconnect/pull/1399) is protected
`addc5772cada1a2e1dedb676f50c3b671f19099c`, reviewed `8242d1c2975afee604d285a3c0b8dbed0b6d1751`,
equal tree `4e342673472f78428c56e11ef4352d1f4c3ebca0`, sole parent
`d081fab06d40ba7d109df429cf4b52195a1565a0`. All nine reviewed blobs match.
All 3,190 other tracked entries and 281 product files remain byte-identical.
Whole-source review `1582aa33862bf8c5eecee0ba2a5ba32fbfeacd30bbe095c1f1b69681d18ab210`
and exact-commit review `80457e2569d87f7a1e2ca2f03887cf030479cdc5c99c5181b7d990e5eb143b81`
preceded normal protected delivery. Premerge 32 checks succeeded with 5 expected
skips. Original Owner Authorization 41191478747 binds the exact candidate/PR;
402B SHA256 `b75b2c76dc7ae26d9281c03bf742fee3105f926b1113dc51f6f90350f510a5c3`.
No bypass, admin merge, automerge or self-review was used.

## Parallel behavior and actual verification

Core inventoried 37 workflows. Independent lint, scans, governance and verification
jobs already overlap. Validate's offline unittest and post-merge coverage, plus
TDE observe coverage, now use four process-isolated module shards. Every worker
rediscovers the same complete suite; unique test-ID accounting rejects omission,
duplication, fixture errors, crashes and incomplete results. Module/class fixtures
remain together. Separate temporary directories, logs and coverage databases keep
independent runs isolated. Coverage validates the exact worker dataset inventory,
readability, nonempty lines and compatible branch modes before combining. The
existing exact-main marker and coverage artifact contract remain intact. External
reusable-workflow consumers keep the serial default unless explicitly opted in.
See [the runner contract](PARALLEL_OFFLINE_CI.md).

The frozen local suite has 3,921 total cases:3,914 pass and 7 existing skips. Serial
execution completed in 140.658s; four-process coverage completed in 56.698s. All four
original databases are retained; the independently read combined database is the
exact union of 208,048 arcs across 588 files. Seven hermetic regressions exercise
real process overlap, temp isolation, class/module fixtures and skips, failures,
crashes, stale reports and missing/corrupt/incompatible coverage. Ruff is clean.

Original Linux CI41191448069 independently ran all 3,921 IDs once in four workers,
with 53 preexisting platform/Python-condition skips and no new runner-test skip.
Its observed worker interval was109.570s. Previous protected main41187643811
ran 3,914 cases serially in 190.021s with the same 53 skips. These are individual
observations, not a guaranteed or identical-source benchmark. Existing test
assertions were preserved while two fixtures were corrected to own their actual
runtime/source moment and required constants rather than earlier modules' state.
Original failed exploratory runs remain failure records, including the stale
runtime/const fixtures, initial coverage retention and namespace collision.

## Own original release evidence

Own main run 41191831125 completed SUCCESS, including exact-SHA coverage.
The separate original hosted worker artifact13039665411 accounts all3,921 cases
with53 existing Linux skips and four exit0 workers in134.845s; provider ZIP
`354eaa45d9e1f0e3daa5b0c283d73f434b587b33d453bf43e5ac1c9540ff588c`
is bound to this same protected source and own main run.
Own release run 41192077707 reconciled successfully. Its automatically
started model/package workflow was cancelled once under the human instruction;
cancellation is not model PASS or proof of zero spend. No manual paid test was
started by this CI optimization.

Original formal2628B SHA256 `345b5f45fa1899fb657a71b4fe4c26f1b5aaca542295b5782205cf6d44f3c70f`,
provider ZIP `ce136363fc32541892a1fd74d434b5cc619905a9b5cb8bef754bb7afb02a9e22`, canonical digest
`ed4189ac599142d48701513add7f1b62c9f01c503149802e8663b1326fb7ea13`. Original durable1812B
asset695045748 SHA256 `a3ea245655b1cd4f3ec32b79fae70be43aedc7e3b0e626ccc6347fe9fd9122b5` validates
all 12 required checks under exact policy ebbb35f038a7a3c7d46c12660968bcd50eb67580.
Own coverage ZIP `591cce61b965c024254cfee263ce84c67a4bd2d41000b95af92e7b0021278146` binds the protected
source marker. Root original join `776887d0f4f8361cb59b240eb50c5793b29a02047f34f208ca41379dc547bc1c`;
independent original closure `959c1c1543097920513ce26a0093247fd1343d65fb6b3f760da887005e20506a`.
Its exclusive count addendum `00389d3b8722b56c8512ff68a975910315c6b890b6f1dcb9c0c7a35cd86f6c3e`
corrects one audit prose typo: the predecessor has 3,914 cases; this source has
3,921. The qualification decision is unchanged.

## Other lanes and retained open work

API owns its separate parallel Validate/native qualification increment and its
own Source/Final/CI evidence; Root's exact source-only review is not deployment
or original release qualification. Apple owns resource/fixture isolation and
parallel CI/build delivery after its actual full parallel pass. Its earlier
performance snapshot and failed runs keep their own scope. No Core approval is
transferred to a later or combined API/Apple tree.

All 24 requests/nine gates remain. Help retains 28 EN/NL qualified textual leaves
and 42 pending DE/FR/ES leaves; five-language UI and free Ask DJ remain. VibeCast
bulletin moments, historical queue preservation/provider semantics, narrative
style acceptance and Pi NOT_RECOVERED remain recorded. The product goal remains
one rich Session widget and one rich Live Activity with playback/artwork/VibeScape.
Original receiving permissions, numeric clock evidence, trusted enrollment,
custody/provider configuration and actual native reception remain separate gates.
No paid/provider/device effect is moved into the parallel offline pool.

HA-dev retains prior 277/schema18 installed scope; this does not install 281 source
files. HA production and its pending configcheck remain separate. No redundant
HA restart, provider redeploy, key operation or physical action is included.

## This Final and next step

This separate Final changes six rolling-record prefixes, this report and one
history entry. All product/source/test/workflow/dependency/release inputs and
old document bodies remain unchanged. Its own whole/exact review, normal CI,
protected merge and original qualification are required; Source1399 does not
qualify this Final. After bounded workspace cleanup, continue the retained open
work with owning lanes and exact source/effect gates.
