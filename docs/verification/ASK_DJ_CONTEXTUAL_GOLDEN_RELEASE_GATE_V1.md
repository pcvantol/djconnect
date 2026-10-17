# Ask DJ contextual Golden release gate v1

User-selected corrective verification increment, 2026-10-17. Base
`cc9b49fe9ca5312dd3bf962b3bac319aa25b3f15`; isolated same-writer branch
`codex/askdj-contextual-golden-release-v1`. Existing VibeCast candidate is preserved.

## Observable contract

The user selects a published contribution mentioning Peter Luts and asks
“Wie is Peter?”. Ask DJ resolves the partial name against that contribution,
answers about Peter Luts, and obtains qualified public biographical evidence.
It does not discard the selection, confuse the DJ/user with the subject, invent
an attribution, play music, or change an output. A genuinely unrelated explicit
subject still overrides the selection. Ambiguous names require clarification.

This is an Ask DJ reactive Golden family, not a seventh Session Intelligence
scenario. Existing SI-GOLDEN-001–006 and their deterministic advisory profiles
remain unchanged. The executable cases use the ordinary paired HTTP route and
real HA/Core/Conversation acceptance with real paid model calls. Only external
playback/catalogue/credit boundaries use explicit synthetic fixtures. A synthetic
CC0 credit is not proof of the real record's credits or a fetched biography.

## Release policy

Qualification is fail-closed: missing credentials, zero model calls, a missing
case, transport failure, lost selected context, missing factual source evidence,
forbidden mutation, timeout or malformed receipt are failures, never skips.
The exact Git candidate SHA, case manifest digest, model, usage and result IDs
bind every redacted receipt. No model judge or exact prose matching is used.
A request can consume at most two existing Core model attempts; the paid probe
has an independent hard request cap. Retry a failed CI job explicitly; no
automatic model retry loop or fallback model.

A tag-triggered workflow is a post-tag check, not prevention of tag creation.
The internal integration artifact publisher must await the same reusable paid
gate before its tag/asset publication: GITHUB_TOKEN-created tags do not trigger
a second push workflow. Manual version tags receive the tag-triggered check.
The gate does not install, deploy, sign or grant release authority. Existing
formal reconciliation evidence does not become product qualification by name.

Secrets use the existing authorized test route locally and a dedicated
`DJCONNECT_GOLDEN_OPENAI_API_KEY` CI secret. Do not copy HA keys/configuration to
GitHub implicitly. No PR/fork trigger receives the secret; jobs use read-only
repository permission, an immutable HA image, isolated ephemeral HA storage,
no installed HA mounts and a bounded networked test. Retain only redacted case
outcomes/hashes/usage: no tokens, raw prompts, chat bodies, account identifiers,
provider payloads or local paths in public artifacts.

## Acceptance and current evidence boundary

Twenty cases across five language families cover partial person references from
published CC0 credits and selected playback entries, deictic references and
explicit topic changes. The compact schema checks result coverage and policy;
actual source lookup must be proven by the ordinary Core response, not by
fetching Wikipedia in the test and inserting it into a prompt.

The installed-main partial-name context regression is already reproduced.
Until that production defect and the qualified source-lookup path are fixed,
the affected paid Golden cases must remain RED. A working workflow is not a
claim that the product passed. CI credential admission is separately required.

A qualified fetched biography uses `sources[].claim_scope: person_biography`
with an allowed public source URL. Existing `qualified_credit_only` attribution
does not qualify a biography. This additive evidence requirement is deliberately
not fabricated by the lab; current producer absence fails the release case.
Maximum40real model attempts,700output tokens each,600s wall-clock limit;
model fallback/retries beyond the existing two-attempt Core bound are forbidden.


## Expanded release matrix (user refinement)

The [machine-readable matrix](fixtures/askdj_golden_release_matrix_v1.json)
reuses all112 existing [single-turn Q/A contracts](../../examples/ask_dj_e2e_cases.json)
and names21 conversation families/70 observable steps. These are not70new
independently executed HTTP tests: exact execution classes remain explicit in
the matrix. The owning test suites supply interpretation/transaction fixtures;
the existing paired HA probes supply actual HTTP/runtime/storage boundaries;
`full_golden` supplies real paid multistep dialogue across standalone, active,
paused/Presence-Off, five languages/four Personas, voice, clear/owner races,
deduplication, exact Track Insight, lookup/refinement/selection/play.
`contextual_golden` adds the20named-person regression cases.

All profiles are blocking. Four networkless real-HA probes cover current artist,
previous track, output selection and title listing. Their agent-boundary seed
fixtures are counted separately from zero paid calls. No genuine provider,
STT/TTS, native app or physical playback acceptance is inferred.

The source-of-truth route inventory is extracted from literal `AskDjIntent`
constructors. All46current names must be covered by the existing Q/A contracts
or a named owning test. New unmapped names fail validation. Conversations and
non-LLM functions remain required even when the real model provider is offline.

Maximum paid attempts per release:40person cases +128full-profile attempts,
700output tokens each. Attempts are reserved before I/O and mapped to actual
Core client message identity; missing/partial usage remains a failed run. The
networkless layers receive no real credential. No automatic provider retry or
fallback model is added. Actual usage is retained per case without prompts or
answers in public artifacts.

Frozen minimal person assertions are independently grounded in
[Peter Luts' official biography](https://peterluts.com/),
[Peter Luts Q3376733](https://www.wikidata.org/wiki/Q3376733),
[Miles Davis' official timeline](https://www.milesdavis.com/timeline/) and
[Miles Davis Q93341](https://www.wikidata.org/wiki/Q93341), read2026-10-17.
Only the minimal DJ/producer or trumpet role is checked; birth dates, anecdotes,
family, gender or claims about the currently playing recording are not inferred.
These test expectations are not injected as new model context or source rights.

Independent preliminary review identified and corrected the extra-workflow-run
SHA race, global-only SDK counting, unreserved failed attempts and person-name-only
answer checks. Broader exact technical and content reviews remain required before
publication. No green release/product claim exists at this checkpoint.


### Help admission correction

All60 existing help examples now execute;13 formerly skipped generic templates
have explicit fixture bindings (including three distinct artists in a seed mix).
The product help text stays generic. The live CLI and owning Q/A runner use the
same substitution helper. Unknown/unbound/unused placeholders fail closed.
Exercising the formerly skipped one-word version request exposed a real minimum
word-count restriction: “Geef me10uitvoeringen van Hallelujah door verschillende
artiesten” bypassed the version search. The existing bounded read-only version
route now accepts a nonempty single title word; empty/stopword-only queries
remain denied. Its precise existing route is `track_versions_search`, not the
old unexecuted catalog expectation `track_title_choices`. Explicit fixtures and
single-/multiword regression checks qualify this correction separately from
paid dialogue quality. The original Peter context regression remains open.
