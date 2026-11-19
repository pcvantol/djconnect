# Ask DJ catalogue variations v1

Status: conditional generation/execution tooling implemented; actual generation
is blocked until complete current base qualification. No generated corpus,
variation product PASS, native/installed or hearing acceptance is claimed.

## Ordered qualification

1. The ordinary complete catalogue profile must PASS all70 exact questions and
   30speaker/whole-album/duplicate steps, with exact source hashes, catalogue
   manifest, real completed model receipts and matching SDK3000/low settings.
   Failed, selected, incomplete, stale or changed-source evidence causes zero
   generation callbacks. A source test PASS is not this prerequisite.
2. Generate80 question variations through the existing isolated HA conversation
   provider:14 catalogue questions and two frozen-choice acceptances per language.
   Rotate paraphrase, natural spoken wording and one intelligible typo in an
   ordinary word. Preserve proper names, current/selected references, media kind,
   period, scope and explicit playback permission. No generated expected answers,
   URIs or routes. One generation plus one independent meaning review per language:
   at most10calls, no retry or selective replacement.
3. Independently review every proposed question for same intent, same reference,
   same permission and requested language. All four must be actual booleans true.
   The review echoes the digest of the exact original/proposal batch. Missing
   rows, duplicate IDs/JSON keys, changed names, bad fields or changed meaning
   fail the batch. Rejected generation receipts are retained, not executed as
   if they were valid same-meaning regression questions.
4. Freeze the accepted corpus at
   `docs/verification/fixtures/askdj_catalogue_variations_v1.json` once. Do not
   overwrite/regenerate it because product execution fails. Corpus metadata says
   generated/unexecuted and is never itself product qualification. The separate
   execution report supplies that evidence.
5. Compile100 additional ordinary paired Ask DJ steps:70 changed questions,
   10offers reusing their changed catalogue wording,10changed acceptances and
   10exact duplicate requests. Reuse every independent original media/effect/
   permission/locale/source/narration oracle. Duplicate replay has zero new
   effects, model work or provider lookups. No variant ID reaches product routing.
6. The separate required `catalogue_variations` release profile follows the
   complete base profile. Missing/stale corpus or missing/failed actual execution
   fails closed. Its report cannot replace a base report, or vice versa. The
   frozen corpus and exact case questions/receipts have their own manifest hash.
   Keep the existing392attempt/4per-request limits and zero STT/TTS per100steps.
7. Preserve each same-meaning variation that fails in the product. Diagnose the
   ordinary shared owner, repair product code, add a causal regression and rerun
   the same frozen input. Do not relax expectations, conceal failure or replace
   the question to obtain green. A genuinely ambiguous generated proposal fails
   meaning review rather than granting different product authority.

## Existing implementation owners

- `tools/verification/askdj_catalogue_variations.py`: prerequisite, bounded
  generation/review contracts, immutable compilation of independent oracles.
- `scripts/verification/verify_ask_dj_contextual_dialogue_http.py`: existing
  real HA provider, paired HTTP path and actual SDK/usage observation. Evaluation
  input may provide `variation_base_report` to generate only after its complete
  current PASS, or `variation_corpus` for actual product execution. Both are lab
  inputs, never new product API fields. No installed HA state is mounted.
- `scripts/verification/askdj_example_catalogue_golden.py`: common transaction
  execution and receipt checks; distinct base and variation qualification types.
- `tools/verification/run_askdj_release_matrix.py`: required separate variation
  profile, with missing frozen inputs blocked before spending profile credits.

All112single-turn,60historical Help and560proactive cases remain. Generated
questions extend regression coverage; they do not replace native client,
independent editorial or audible TTS qualification. Broad release blockers
remain enforced before paid release profiles.
