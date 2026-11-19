# Artist answer word-reference review

This internal review wire addresses a measured failure: a reviewer copied an
otherwise unchanged Dutch answer with an extra comma. The existing literal
coverage gate correctly rejected that response. Historical failed evidence is
retained; this increment never repairs or reinterprets an old response.

## Original characters and whole-answer review

Only the artist evidence-draft path opts into `source_answer_ids_review_v1`.
Core captures all original normalized drafts before the review await. Each
original record keeps its index, SHA256 and whole text, plus `answer_words`,
a list of `[id, original_word]` pairs. IDs are exactly `d0w0`, `d0w1`, ... for
draft0 and `d1w0`, ... for draft1, without aliases or leading zeros.

The Core tokenizer is Python `re.finditer(r"\S+", original_text)`. A model
claim has exactly `answer_from`, `answer_to`, `kind`, `evidence_ids`. Its first
and last word IDs select one inclusive, contiguous range; Core resolves the
original Python-string slice from the first start through the last end. It
never joins tokens, inserts punctuation, normalizes Unicode, trims a claim or
accepts returned text/offsets/catalogs. Internal original whitespace is kept.
Ranges cover every original word exactly once in order. Only original
whitespace may lie between ranges; cross-draft, duplicate, skipped, overlapping,
out-of-order or noncanonical references reject the complete batch.

All rows must bind original index/SHA/order/count before any verdict is exposed.
The complete new wire is validated before conversion to canonical legacy-shaped
claim objects. Those objects still pass the existing complete coverage, source
quote, actor/role, relationship, whole-sentence scope, temporal, language and
style gates. The model still selects meaningful atomic propositions and attests
source support. Addresses are no truth, source, quality or publication grant.

Positive reviews require `review_schema`, `supported`, `language_ok`, `style_ok`,
`unsupported_claims`, `claim_checks`; only `temporal_claims` is optional. Negative
reviews require all seven fields, one to three exact original unsupported
substrings, and empty claim/temporal arrays. All flags are actual booleans.
No prefix recovery or legacy-schema fallback exists in this opted-in path.
Unchanged legacy callers keep their existing schema and prompt contract.

## Bounds and original SDK receipts

The existing original-draft JSON limit remains8192bytes and one or two drafts.
The address capture permits at most8192original UTF8bytes total,512words per
draft,1024words total and16384compact UTF8catalogbytes total. Review JSON is at
most8192bytes, depth16/nodes1024,24claims per draft,1200characters per resolved
claim, and eight temporal entries with the unchanged temporal schema. Any
excess closes the attempt; it never crops evidence or buys another call.

Model, fixed medium profile,3000output tokens, caller fences and paid budgets
are unchanged. The existing24576byte raw prompt fence remains. More catalog
input can cost capacity or latency; this is not a guarantee that the measured
Spanish incomplete stream will disappear. Capacity evidence must measure both
generation and assessment with full original evidence, all five languages,
and one/two drafts. A bounded snapshot is not a universal capacity claim.

The actual SDK observer records only the original public draft/index/hash/word
catalog before the provider await. Raw returned addresses remain in the actual
model receipt. An independent verifier rebuilds the catalogs from original
characters and crossjoins actual response hashes, indexes, coverage, wire,
case, completion and phase. Both current medium-selected validation and the
current full100 runner require this proof. The new observer is part of exact
content/profile/snapshot hashes; consumed historical runner scopes remain intact.

## Delivery and acceptance

This increment is source preparation. The catalogue remains draft revision1,
70pending, DFAA hash unchanged. A successful genuine new short cycle, full100,
independent editorial review, winning Source plus separate Final, configuration
binding, Apple adoption and installed qualification remain separate gates.
The old target5 failure had3PASS/2FAIL,20reservations/19completions and no valid
strict counter join; these values must never become a pass for this protocol.
No new provider, private key, device, production configuration or native claim.

Validation receipts and final Source review are recorded in the current
completion record when actually available. Failed development checks remain
retained beside subsequent corrected checks.

## Actual bounded source evidence

The final isolated HA run3 passed all14groups with266product files equal
before/inside/after and its owned container verified absent. The artist group
includes the too-many-words case: HTTP502 after two calls, before review or any
provider effect. Original malformed/negative/second-draft/temporal cases remain.
Current12fixture summaries are joined to those original receipts, with previous
fixture bytes and historical receipts preserved.

The final actual SDK-boundary runs5and6 each exercised all five original artist
cases, one and two drafts respectively:20synthetic responses, zero real model
or network calls, strict selected validation, original public source inputs,
and owned containers verified absent. Generation and assessment inputs remain
under24576bytes for these bounded retained-source cases. Twelve independently
mutated actual input/output witnesses are rejected. These are transport proofs,
not paid content or editorial quality results. The512word plus full-source
counterexample closes at the existing prompt fence before any SDK reservation;
no universal capacity claim is made.

Fifteen original legacy prompt variants are byte-equal to protected2942c2d3.
The final complete unit, lint, scanner, immutable Source-file map and independent
review receipts accompany delivery; they must be checked against those exact
bytes. Prior full-suite failures and the first changed-during-test snapshot are
retained as failures, never promoted to acceptance.

No dependencies, tools, manifests or licenses are upgraded in this increment.
The paid execution profile and environment stay pinned for causal comparison;
new dependency upgrades require their own reviewed qualification scope.
