# Ask DJ catalogue Golden — actual run and remediation

Decision: **NOT QUALIFIED / OPEN**. Existing sole Core writer, selected Core #1210.
Base `ff1758344a863d2ec897b993c76b9c73a93c1631`; isolated uncommitted
`codex/askdj-example-catalogue-v1`. No candidate deployment, publication or native acceptance.

## First actual paired HA run

All 100 steps completed: 70 exact catalogue questions and 30 five-language
speaker/album/duplicate steps. 122 real HA OpenAI-agent attempts, 121 completed;
one German speaker-continuation stream closed without a terminal event.
43,239 reported input tokens and 9,541 reported output tokens; the incomplete
stream has no reported usage. Model `gpt-6-luna`, maximum700 output tokens.

The original gate is **FAIL**, independently revalidated against its then-current
source hashes before any repair. 41 rows failed and59 passed their original row
checks; this is not a product quality score. Original report SHA256:
`0cb06db6c3d4fcdd877b697acbfea8cea0342175998a95d4e026d04e35ff3fa5`.
Manifest SHA256: `8b36d9a00f4cf863aba8803d1995fe8009c95d1164caff8ff45598a424ffec11`.
Source hashes were unchanged throughout that run. Actual questions, responses,
provider operations, terminal events and token receipts are retained privately,
including a readable all100-answer review document. Never substitute rejected
model proposals for actually returned text.

## Causal classification

- Product findings affect24 rows: activity requests shortcut to an artist search;
  artist stories reduced to identity/genre; English/German explicit album
  continuations missed; accepted full-album responses lose selection receipts
  or use the first track as the album title; narration is rejected as too dry.
  One narration fallback also includes the incomplete provider stream above.
- Ten track-list findings are oracle defects: track action identity was read
  from its album context, and an informational album list was incorrectly
  required to expose playback actions instead of its contained items/observation.
- Five Forecast cases deliberately outlived their stopped observer. Core
  correctly reported expiration. The new fixture must obtain a fresh ordinary
  observation, not reset time, renew a deadline or manufacture a Forecast.
- Two additional output rows have language-only judge failures. The judge
  returned French/Spanish detected_language but language_ok:false despite the
  localized header. Known synthetic device/music names must be neutralized in
  judge input; the original answer/hash remains bound and wrong-language prose
  still fails. Three other language failures overlap product findings above.
- A valid public artist source uses the shared research metadata contract
  (title/provider/license/revision/hash/URL), not an invented subject field.

## Product repairs under verification

The ordinary processor leaves open activity/music subjects to Assist while
preserving literal quoted names and the original request-bound target.
Explicit local album/track/playlist continuations retain the frozen selection;
plain yes, negations and hypothetical requests remain non-authorizing.

Play Now reuses the existing backend acceptance receipt and shared Persona/Mood
playback narrator. The frozen album title and media kind survive even when
readback shows its first recording. Exact output confirmation remains required;
no extra playback retry is introduced. Artwork/source data follow the accepted
response into its assistant-message projection.

The semantic read proposal distinguishes artist identification from artist
story. A validated story resolves the performer locally, then reuses existing
Wikipedia/public research, five-language Persona/Mood generation and independent
factual assessment. Catalog metadata is a lookup identity, never biographical
evidence/model context. At most one interpretation plus generation/assessment
uses three calls; unrelated turns retain two. Expiry, owner/Session and changed
playback fences remain active, with no effect grant. The old genre-profile
story bypass is removed.

Causal source tests include allfive-language actual owner flows, changed-playback
rejection, full-album identity, one dispatch and duplicate replay; these are
explicit provider/model fixtures, not real-model quality acceptance.

## Remaining gates

Fresh actual100-step qualification of the repaired source, independent actual
answer/editorial review, exact candidate review and Apple/native acceptance
remain required. All catalogue locale publication gates stay pending, descriptor
qualified:false. Release blockers remain enforced; neither a local test pass
nor a corrected oracle closes the capability. Installed, speech/hearing and
consumer UI evidence are separate and NOT_RUN for this candidate.

## Second actual run and further product fixes

The first repaired candidate completed100steps/145real model attempts;144
completed and one stream did not. Overall FAIL:19rows fail their strict checks.
Original second-report SHA256:
`877ce955b122ff443a853fbb3a422fae3e1589d6430d61ec37c475fde64c4ec0`.
Manifest and all100exact request texts/statuses were independently read back;
source hashes stayed unchanged during execution. The original report and actual
answers are retained separately from subsequent source edits.

Full-album continuation/receipt, track-list and current Forecast controls now
pass in that actual run. Remaining findings: five activity requests, five
artist stories and nine playback-narration rows. No functional closure follows.

The activity path still sent an unsupported pipeline_id into HA conversation
process, producing no real model attempt and a local artist fallback. The
resolved agent/language now reach that service without pipeline_id; the latter
is retained only as internal trace. Both command parsing and STT correction
share this transport correction. Ordinary HA JSON-in-speech intent responses
are decoded with bounded length, duplicate-safe closed keys/types and no URI
commands. Open music/activity interpretation can retain its semantic playlist
query; explicit named media retain the existing literal stale-target fence.

Playback assessment now uses the accepted dispatch reference, rather than a
generic fact brief that also forbids accepted handovers. Exact roles, state,
placeholders, language and personal style are still mandatory. Artist-selection
replies identify the actual observed/included recording without an extra opaque
administrative noun. Unobserved order and album association remain bounded.

Artist-story generation is constrained to a compact connected account with
concrete supported detail, avoiding unasked dates, reputation and genre-link
inferences. Its review reuses original-paragraph schema3 and the existing strict
source-ID decoder. Locally resolved original quotes still undergo the same
whole-text, atomic relationship and temporal validation; no unsupported prefix
is silently rewritten or accepted. This reduces review wire size within the
same model budget; it does not turn a reviewer boolean into factual proof.

403causal owning/transport/validator tests pass after these repairs. Fresh full
source regression and a new actual run are required before publication.

## Third whole run and targeted causal qualification

Third whole run:100completed steps,175real model attempts, overall FAIL with
16failed narration/story rows. Its observable music-selection, whole-album,
output-transfer, duplicate, track-list and current Forecast checks pass; this
does not qualify the newer source or imply narrative/native acceptance.

Subsequent20-case and5-case development selections are explicitly labelled
REAL_PAIRED_HA_SELECTED_CATALOGUE_CASES_V1. The complete100-step validator rejects
that qualification, missing cases, unexpected selected IDs, wrong token limits
and mismatched reasoning settings. Selected evidence can never replace the
release profile. Their earlier results remain FAIL (9/20 and4/5 failed rows).

The prior lab used700output tokens, whereas the existing HA conversation
subentries actually configure3000tokens and reasoning_effort:low. Reasoning
counts inside that ceiling. Catalogue qualification now matches3000/low,
records the actual SDK settings and validates them; the392attempt/4per-request
limits and zero speech work are unchanged. This changes no installed settings.

Causal diagnostics exposed a product language defect: the internally resolved
artist-story call used an empty payload, allowing the pipeline's English
language to reach the reviewer while the accepted turn generated Dutch, German
or Spanish. The accepted turn language now governs both generation and review.
The five-language owner test asserts that actual review language explicitly.

Original-paragraph selection can prioritize a documented artist episode while
keeping the identity paragraph and exact original offsets. The shared existing
episode focus is reused; it grants no new factual authority. The review is
now instructed to give source-bound names/titles their own factual segments
inside subjective DJ appreciation, preserving complete unchanged coverage.
A causal positive/negative regression proves that an evidence-free work name
fails, its literal factual receipt passes, and an unsourced experimental
modifier still fails. The validator itself is not relaxed.

Playback kind placeholders now carry a localized bare noun plus the explicit
Core-owned kind enum, so the model can supply a fluent article/preposition.
Catalog names remain local. The admitted recording's album relationship is
phrased without bureaucratic associated-with language.

## Latest actual qualification and bounded fixes

The next20-case development selection completed all20cases with78real HA model
calls, source unchanged during the run.14passed and6failed: two Spanish playback
narrations and four non-English artist stories. Source hash and exact actual
SDK3000/low settings are retained. This selection is not a full100-step gate.

Causal rejection replay found two additional product defects:
- Spanish playlist narration could use the faithful Core enum label `lista de
  reproducción`, but restoration recognized only `playlist`. Both closed Core
  labels are now allowed exactly once; multiple/ambiguous labels, changed media
  kinds and literal private catalog names remain rejected. The prompt exposes
  only those Core labels, never catalog names. Independent assessment still runs.
- English `producing` and Spanish `produciendo`/`grabando` were missing from the
  existing activity-equivalence guards. A faithful French/Spanish translation
  could therefore fail despite an original explicit production/recording act.
  Causal positive tests now admit that act; guest guitar/recording alone still
  cannot supply a production claim. The unchanged formerly rejected French
  answer passes offline replay; that is causal evidence, not fresh-model PASS.

A proposed positive chronology witness was removed before publication: a work
name plus an original before/after phrase did not establish the candidate's
actor/activity/direction. Adversarial tests include invented earlier-band
departure and reversed joining/recording order. Existing unbound chronology and
relative-year guards remain fail-closed. No generic timeline exemption ships.

A fresh four-case selection after these fixes completed16real HA model calls,
all terminal events received, source unchanged:1PASS/3FAIL. Spanish quiet-playlist
narration now passes. Spanish cooking narration reaches independent assessment
but is rejected for style. New French/Spanish artist proposals introduce
unsupported leadership/initial-invitation or career-start wording and are
correctly withheld; their actually returned fallbacks remain recorded. These
new answers differ from prior proposals. Do not aggregate selections or present
an old proposal's offline acceptance as fresh generative qualification.

Final source verification:2692tests PASS,7existing skips;411owning tests PASS.
Ruff, generated catalogue and source inventory checks pass. Raw failures, exact
actual delivered texts, attempts/settings and source hashes remain preserved.
Exact-candidate review, complete fresh100-step qualification, independent
editorial review and Apple/native acceptance remain open. All locale publication
flags stay pending. No candidate commit/push/merge/deployment or actual speech
acceptance has occurred in this remediation pass.

## Continuation: conditional variation coverage

A later20-case real selection on revised narration instructions completed76real
model attempts:14PASS/6FAIL. Failures distinguish a Dutch Core-label synonym
(`afspeellijst`) missing from structural restoration, a read-none proposal for
a contextual artist introduction, style rejection and incomplete external
streams. Both the Dutch label and semantic interpretation instructions are
repaired without introducing phrase-specific product dispatch. A subsequent
three-case Dutch selection completes12real calls with3PASS, unchanged source
during that run. Selected evidence remains insufficient for the full base gate.

At the initial variation-tooling checkpoint:2699tests PASS/7existing skips.83focused contract and
validator tests PASS; Ruff and diff checks pass. The current full100-step real
basis subsequently finished100steps/174calls with8failing rows (see the
current remediation below). The new variation prerequisite has also been exercised against
the actual failed report:EXPECTED_BLOCK,0generation calls, no generated text.

The new required variation profile is separately blocked until a complete
current base PASS permits generation and independent meaning review. Inventory at that checkpoint:
40families/267steps/58reports and35open blockers (13Core,22real quality),
including the new actual-variation requirement. No existing failed input or
open requirement has been removed. See ASK_DJ_CATALOGUE_VARIATIONS_V1.md.


## Current remediation: raw credits are not a personal DJ story

The new screenshot reproduces the original instrument/producer/vocalist
fallback template. Its title/recording identity is absent, so no exact Nirvana
recording qualification is claimed. Read-only comparison of the installed
HA-dev narration files matches mainff175834; those files do not contain this
WIP. This is a scoped file comparison, not a fresh whole-install/runtime pin.

The existing expression owner now gives researchable artist/album/producer
stories one40second allowance for original source requests and two model calls.
The same live owner/settings/source/playback-fit guards remain. A registered
researchable contribution needs sealed source/style acceptance; rejection no
longer publishes/counts/persists its raw seed and consumes that fact once,
without spending again each observer tick. A producer additionally needs a
named-work Wikipedia evidence receipt and an independent documented-activity
verdict. Fetching a biography alone does not establish a rich answer.

The observed generative failures informed the instructions: tell the actual
musical contribution to a named work, rather than placing a title next to an
unrelated anecdote. State the complete selected name in the recording-credit
clause so the existing conservative scope condition is explicit. Two or three
short sentences allow a present personal viewpoint without new factual claims.
The source, relationship, role, chronology and style guards are unchanged.

Actual producer expression diagnostics, kept separately from the100-step gate:

| Run suffix | Outcome | Actual receipt boundary |
| --- | --- | --- |
| p20_0ngm | Setup assertion failed before expression report | Receipt missing; no expression PASS |
| _s47rmoe | Obsolete setup-Moment report field failed | Receipt missing; no expression PASS |
| e158n3j7 | Two researched expressions rejected |6model calls including setup; source unchanged |
| zzf4mjcy | Chill rejected for style; Party lacked explicit complete identity in its recording-credit receipt |6model calls including setup; source unchanged |
| t8z__6qe | Preparation stopped at MusicBrainz HTTP503 |2setup model calls; zero expression cases; source unchanged |

These use a synthetic playback binding and actual public source retrieval,
then a common captured corpus for two Mood expressions. They are not runtime
Moment publication, installed Flow, native client or audible qualification.
The two missing-report failures are retained, not silently converted to PASS.
No external source outage is counted as a product quality PASS.

Final local source checks:2703tests PASS/7existing skips after all prompt and
document-byte repairs;96focused contracts PASS and61producer tests PASS.
Ruff, catalogue generator, inventory and current-document DAG checks pass.
The exact receipts and source hashes are retained in the restart checkpoint.
A current semantic avatar derivative was regenerated from the real runtime
trace, preserving the immutable historical receipt. Bulk storage testing now
explicitly isolates a nonresearchable CC0 contributor; the existing researched
producer commit/reopen/replay case retains its stronger typed acceptance.

The latest complete base run finished100steps/174actual calls with8failures:
artist playback DE/ES, quiet playlist FR, contextual artist EN/DE/FR, speaker
acceptance NL and whole-album acceptance NL. It is an earlier source snapshot,
not proof of the current candidate. Its original report and actually delivered
HTTP answers are preserved. The conditional variant controller refused that
failed/stale base before key access or generation:0calls, no generated corpus.
No selected run, changed expectation or source test substitutes for full PASS.

Current inventory:40families/268steps/59reported issues, with36release blockers
(14Core findings,22real-quality steps). All112single-turn,60historical Help and
560proactive cases remain. All locale catalogue publication pins stay pending.
Core1210/Apple128 remain PARTIAL/OPEN. Next: qualify the repaired story owner
when its source is available, resolve all eight catalogue findings, qualify the
complete current100steps, then generate/review/freeze/execute variations with
unchanged independent oracles. Exact-candidate/editorial/client/audio acceptance
still precedes protected delivery; no merge or installation is claimed here.

## 19 October: composer-credit regression remains open for real quality

The reported static composition credit is now bound to nine owning source
regressions and the release runner schedules the fact owner. The local repair
reuses the exact work/composer identity and existing researched expression owner;
registered unqualified seeds cannot masquerade as stories. Actual paid source
preparation failed on MusicBrainz503 before composer generation. Two setup calls,
zero composer rows; no model-quality or installed acceptance. Current inventory:
40families/270steps/61reports and39release blockers (16Core/23quality). The earlier
full catalogue FAIL and zero generated variants remain unchanged. See
[composer evidence](COMPOSER_STORY_20261019.md).

## 19 October: artist descriptor and spotlight image regression

New bound scenario rejects a dry Wikidata descriptor and requires the original
exact artist media target in active and reopened Flow. Local correction reuses
the reciprocal MB artist Spotify link when WD P1902 is absent; no formation date,
name search or cover substitution. Registered unbound artist seeds do not publish.
External image/model fixtures qualify source only. Real prose/provider photo,
installed and native proof stay open. Current40families/271steps/62reports,
41release blockers (17Core/24quality). Earlier failed catalogue and zero generated
variants remain unchanged. Full evidence is in ARTIST_DESCRIPTION_SPOTLIGHT_20261019.

## 19 October: licensed non-Spotify band-photo scenario

Explicit media2 now selects exact performer context, using licensed Commons only
for a missing Spotify image. Source tests cover rights, actual decode and
active/history/version/source fences; real public adapter separately obtained a
small licensed Nirvana stage photo. Consumer2/pin/review/installed/native gates
remain OPEN. Current40families/272steps/63reports,43release blockers
(18Core/25quality); earlier catalogue FAIL and zero generated variants remain.
See SESSION_ARTIST_PHOTO_V2_20261019 evidence and SESSION_ARTIST_PHOTO_V2 contract.


19 October same-band follow-up: Golden adds the four-observed-track story-variety
sequence and twelve source regressions. Current inventory: 40 families / 273 steps
/ 64 issues; 45 blockers (19 Core / 26 real quality). Actual public Wikipedia
source selection is separate from generated prose/installed/native acceptance.
Earlier full catalogue FAIL and zero generated variations remain. See
`docs/verification/SESSION_STORY_VARIETY_20261019.md`.
