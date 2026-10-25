# Help artist evidence-first repair — 25 October 2026

## Actual problem and previous execution

The last original qualified Source1336/Final1337 pair delivered the artist JSON
wire correction. Its separate manual run40156643319 completed all100cases and
175reserved/completed model responses:96PASS, fourartistFAIL (en/de/fr/es).
Original artifact12584976209 ZIP SHA256
`c338275cbee0fe1e752d9beb7ece2275c6ed2082fbbcd7afbd3910a314029985`;
report SHA256`d6e97cb5b77a2cee093713ccaea7480c187eccb924870d5e30c1970297d644f5`.
Original independent all100 review SHA256
`c675d08fe90faa4bdb62d6134c6b144afd7f0c294e5914c5733ff3670f3e9d40`
confirms FAILURE. The consumed execution, grant, workflow, runner, content map
and all previous original reports remain unchanged. No unused budget is reused.

The old model sometimes selected unsupported roles/timelines, or returned
malformed negative proof rows. A German positive fragment with empty fact IDs
remains invalid. This change never retroactively rerates those original replies.

## Scoped implementation

Only fetched schema3 interpreted-artist research, excluding interpreted-context
research, uses `artist_evidence_drafts_v1`. Other routes keep their existing ABI.
Core freezes the original full research/qualified context before the first
await. It derives exact Unicode-codepoint ranges inside canonical original
source spans, rejects conflicting derived spans and excerpt hashes, and never
changes, concatenates, normalizes or truncates source text into new facts.

Each internal immutable range commits source hash, evidence ID, start/end,
literal and literal UTF8 SHA256. The full64hex ID is SHA256 over
`DJC_ARTIST_LITERAL_ANCHOR_V1` plus NUL plus canonical JSON of those six fields
(sorted keys, compact separators, ensure_ascii=false). Model input contains only
`{id,literal}` plus the unchanged full original generation evidence. A literal
range is editorial steering, never factual/role/chronology proof. Sentence-like
slices can split abbreviations. Full context remains independently admitted.
Ranges are16..1280UTF8 bytes, at most32 and8192total literal bytes. Oversize ranges
are skipped whole; no context crop. The original24KiB prompt bound still closes
before model I/O if necessary.

The model returns one or two whole draft records with1..3distinct actual anchor
IDs each. All records must validate before any text is considered. Two drafts
need different resolved literal-hash sets, not reordered IDs or paraphrases of
one literal. Core neither quotes the anchors as a local generated story nor
splices, rewrites or salvages a prefix. The existing normalized whole-text
index/SHA receipt binds each independent assessment and selected history entry.

A negative artist review has exactly review_schema, supported:false,
language_ok, style_ok, unsupported_claims, claim_checks:[], temporal_claims:[].
It rejects the whole candidate and cannot admit facts. Its1..3bounded unsupported
strings must be literal substrings of that candidate. A malformed/trailing row
closes the whole batch. Every supported:true factual, relationship, whole-word
coverage, source ID, pronoun, role/count/date/chronology, language/style and
additional biography guard remains unchanged. One existing generation and one
existing independent assessment call serve the batch, after the interpreter;
no extra repair call, retry, lease, budget, expiry or authority is introduced.

## Original public input evidence

Evaluation captures bounded actual public SDK inputs BEFORE its await, including
when a later reply, decoder or assessment fails. It retains only original public
music research and the actual compact literal anchors sent (assessment has[]),
bound to the fixed case, phase, locale and canonical digest. A path-specific
closed schema excludes enclosing questions/history/private authority/headers/
credentials. No reconstructed commitment is labelled as a sent field.

An independent range verifier recomputes the source/span/codepoint/hash
commitments from those actual inputs. Full100 acceptance requires exactly five
original generation plus five original assessment records for the five artist
cases/locales, matching public span corpora and actual model-attempt digests.
Unknown/missing/duplicate/cross-case/phase records fail; capture and final replay
both enforce128KiB/record and4MiBaggregate (under the original8MiBreport limit).
The existing16-member artifact allowlist remains; no private logs are exported.

## Verification and remaining delivery gates

Current causal tests cover the new wire, source-derivative mismatch, literal
hashes/codepoints, unknown/repeated IDs, identical literal sets, whole-batch
failure, closed negatives and unchanged positive fact-ID denial. Actual paired
Store/SQLite tests preserve whole second-answer selection, no unused rejected
history, ordinary status-only effects and original playback/owner boundaries.

All14current isolated actualHA groups pass with the same264product hashes before,
inside and after; own container is verified absent. Source/model/issuer/provider
boundaries in these tests remain explicitly synthetic. Actual SDK-boundary
synthetic-five-artist checks capture all5x2original public inputs with zero
external SDK requests. They are transport evidence, not real content acceptance.
The earlier preliminary derived-span P2 and snapshot schema/size P2s are retained
as original counterexamples; their closures require independent readback.
Whole-source/full-regression/exact-commit review and protected delivery remain
pending at source preparation. No source, installed or catalogue GO is claimed.

## Distinct bounded qualification and publication

The new evidence-first entrypoint is dormant preparation, not another execution
of any consumed source. It requires its own exact reviewed source/Final pair,
original qualification, current actual clean SHA/profile/product pins, setup
without a secret, independent concrete pre-dispatch review and one durable Root
reservation before the single provider dispatch. Maximum100steps/392attempts/
3000outputtokens per attempt/1800seconds; no automatic whole-run retry. Its
once-only original actor/main/run_number1/run_attempt1 and bounded UTC window
cannot be changed to recover a failed execution. A failure is retained as failure.

Only actual100PASS plus independent source/language/routes/effects/editorial
acceptance may begin the separate metadata-only catalogue publication:156exact
leaves (revision/status,14publication flags,70states and70exact original routes).
Questions/IDs/templates/order/contracts/effects/send/rights stay identical. The
new bytes need generation, source/final/original delivery, owning Apple exact-hash
adoption and fresh HAdev acceptance. No old report is repinned to new bytes.
Catalogue is currently draft_not_consumer_qualified/false/70pending.

## Preserved scope

All24requests/ninegates and DJBulletin→ordinary shared VibeCast SessionBroadcast
remain preserved. Existing HAdev264/SQL15 acceptance keeps its own older source
scope; no new install from this repair. HAprod's actual native config check is
pending, APIprod remains previously deployed, and no Pi/provider/APNs/widget/
LiveActivity/key/enrollment/native/user acceptance is inferred. Automation stays
PAUSED; current work is manual. No cleanup, retention expansion or device effect.
